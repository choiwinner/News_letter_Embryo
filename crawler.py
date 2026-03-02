import requests
import feedparser
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import urllib.parse

def get_google_news(keywords="난임", days=7):
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
    
    for entry in feed.entries:
        results.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "source": "Google News"
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
        
    print("\n--- PubMed Paper Test (Embryo quality) ---")
    papers = get_pubmed_papers("Embryo quality", max_results=3)
    for p in papers:
        print(f"[{p['published']}] {p['title']}\nURL: {p['link']}\n")
