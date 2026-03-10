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
        # 1. google.com 링크가 아니면 그대로 반환
        if "google.com" not in url:
            return url

        # 2. googlenewsdecoder 시도
        result = gnewsdecoder(url)
        if result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
        
        # 3. 실패 시 requests로 리디렉션 추적
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        # 인증서 검증 무시 (일부 언론사 사이트 대응)
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10, verify=False)
        if response.url and "google.com" not in response.url:
            return response.url
            
        return url
    except Exception as e:
        print(f"URL 디코딩 실패: {e}")
        return url

def get_article_image(url, retries=2, delay=1.5):
    """
    newspaper4k 및 메타데이터를 사용하여 기사 URL에서 주요 이미지 URL을 추출합니다.
    """
    if not url or url == "#":
        return None

    for attempt in range(retries + 1):
        try:
            article = Article(url, language='ko', config=config)
            article.download()
            
            if not article.html:
                raise Exception("HTML 다운로드 실패")
                
            article.parse()
            
            # 1. newspaper4k의 기본 top_image
            image = article.top_image
            
            # 2. 메타데이터 직접 확인
            if not image or "googleusercontent.com" in image or "gstatic.com" in image:
                image = article.meta_data.get('og', {}).get('image')
                if not image:
                    image = article.meta_data.get('twitter', {}).get('image')
            
            if image:
                # 절대 경로 처리
                if not image.startswith('http'):
                    from urllib.parse import urljoin
                    image = urljoin(url, image)
                
                # 원본 URL이 문자열이 아닌 경우(리스트 등) 대응
                if isinstance(image, list) and len(image) > 0:
                    image = image[0]

                # 구글 서버 이미지 필터링
                if any(domain in image for domain in ["googleusercontent.com", "gstatic.com", "google.com"]):
                    image = None
                else:
                    return image
            
            if attempt < retries:
                time.sleep(delay)
                
        except Exception as e:
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
                continue
            print(f"이미지 추출 실패 ({url}): {e}")
            
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


