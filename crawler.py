import feedparser
import arxiv
from datetime import datetime, timedelta
import urllib.parse
from newspaper import Article, Config
from googlenewsdecoder import gnewsdecoder
import logging
import requests
import nltk
import xml.etree.ElementTree as ET
import time
import random

# NLTK 리소스 다운로드 (GitHub Actions 등 클린 환경 대응)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

# newspaper4k 설정 (타임아웃 등)
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
config.request_timeout = 10

# newspaper4k 로그 레벨 조정 (불필요한 로그 방지)
logging.getLogger('newspaper').setLevel(logging.ERROR)

def resolve_google_news_url(url):
    """
    Google 뉴스 RSS URL을 디코딩하여 원본 기사 주소를 반환합니다.
    """
    try:
        # 1. googlenewsdecoder 시도
        result = gnewsdecoder(url)
        if result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
        
        # 2. 실패 시 requests로 리디렉션 추적 (일부 케이스 대응)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
        if response.url and "google.com" not in response.url:
            return response.url
            
        return url
    except Exception as e:
        print(f"URL 디코딩 실패: {e}")
        return url

def get_article_image(url, retries=2, delay=1.5):
    """
    newspaper4k 및 메타데이터를 사용하여 기사 URL에서 주요 이미지 URL을 추출합니다.
    실패 시 재시도 로직을 포함합니다.
    """
    for attempt in range(retries + 1):
        try:
            if "google.com" in url and "rss/articles" not in url:
                return None
                
            article = Article(url, language='ko', config=config)
            article.download()
            
            # 다운로드 실패 시 재시도
            if not article.html or len(article.html) < 200:
                raise Exception("HTML 내용이 너무 짧거나 비어 있음")
                
            article.parse()
            
            # 1. newspaper4k의 기본 top_image 시도
            image = article.top_image
            
            # 2. 실패 시 OpenGraph 또는 Twitter 메타데이터 직접 확인
            if not image or "googleusercontent.com" in image or "gstatic.com" in image:
                image = article.meta_data.get('og', {}).get('image')
                if not image:
                    image = article.meta_data.get('twitter', {}).get('image')
            
            # 3. 절대 경로 확인 및 구글 서버 이미지 필터링
            if image:
                if not image.startswith('http'):
                    from urllib.parse import urljoin
                    image = urljoin(url, image)
                    
                if "googleusercontent.com" in image or "gstatic.com" in image:
                    return None
                
                # 이미지 URL이 유효한지 가볍게 확인 (헤더만)
                try:
                    img_check = requests.head(image, headers={'User-Agent': config.browser_user_agent, 'Referer': url}, timeout=5)
                    if img_check.status_code != 200:
                        # 404 등의 경우 다시 한 번 GET 시도 (일부 서버 대응)
                        img_check = requests.get(image, headers={'User-Agent': config.browser_user_agent, 'Referer': url}, timeout=5, stream=True)
                        if img_check.status_code != 200:
                            image = None
                except:
                    pass
            
            if image:
                return image
            
            # 이미지를 찾지 못한 경우 잠시 대기 후 재시도
            if attempt < retries:
                time.sleep(delay)
                
        except Exception as e:
            if attempt < retries:
                time.sleep(delay * (attempt + 1)) # 점진적 대기
                continue
            print(f"이미지 추출 최종 실패 ({url}): {e}")
            
    return None

def get_google_news(keywords="난임", days=7, max_results=10):
    """
    구글 뉴스 RSS를 통해 키워드 관련 뉴스를 가져옵니다.
    """
    base_url = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    # 최근 n일간의 검색 결과 필터링 (when:7d 방식)
    query = f"{keywords} when:{days}d"
    encoded_query = urllib.parse.quote(query)
    rss_url = base_url.format(query=encoded_query)
    
    feed = feedparser.parse(rss_url)
    results = []
    
    for entry in feed.entries[:max_results]:
        # 뉴스 기사의 실제 원본 URL을 찾기 위해 처리
        decoded_url = resolve_google_news_url(entry.link)
        
        # 기사별 처리 사이에 랜덤한 지연 추가 (서버 부하 분산 및 봇 탐지 회피)
        time.sleep(random.uniform(1.0, 2.5))
        
        image_url = get_article_image(decoded_url)
        
        results.append({
            "title": entry.title,
            "link": decoded_url,
            "published": entry.published,
            "source": "Google News",
            "image_url": image_url
        })
    return results

def get_pubmed_papers(keywords="Embryo quality", max_results=5):
    """
    PubMed E-utilities API를 통해 관련 논문을 가져옵니다.
    """
    # 1. Search for IDs
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": keywords,
        "retmax": max_results,
        "retmode": "json",
    }
    
    try:
        response = requests.get(search_url, params=search_params)
        id_list = response.json().get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            return []

        # 2. Fetch details for IDs
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        
        details_response = requests.get(fetch_url, params=fetch_params)
        result_data = details_response.json().get("result", {})
        
        results = []
        for uid in id_list:
            item = result_data.get(uid)
            if item:
                results.append({
                    "title": item.get("title"),
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                    "published": item.get("pubdate"),
                    "summary": f"Authors: {', '.join([a['name'] for a in item.get('authors', [])])}", # PubMed Summary API는 초록을 제공하지 않으므로 저자 정보 등으로 대체
                    "source": "PubMed"
                })
        return results
    except Exception as e:
        print(f"PubMed API Error: {e}")
        return []

if __name__ == "__main__":
    # 간단한 테스트
    print("--- Google News Test (난임) ---")
    news = get_google_news("난임", days=7)
    for n in news[:3]:
        print(f"[{n['published']}] {n['title']}\nURL: {n['link']}\n")
        
    print("\n--- arXiv Paper Test (High Bandwidth Memory) ---")
    papers = get_pubmed_papers("Embryo quality", max_results=3)
    for p in papers:
        print(f"[{p['published']}] {p['title']}\nURL: {p['link']}\n")


