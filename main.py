from crawler import get_google_news, get_pubmed_papers
from summarizer import summarize_content
from mailer import send_newsletter, format_as_html
import os
from dotenv import load_dotenv
import time

load_dotenv()

def main():
    print("난임 및 배아 연구 동향 리서치 시작...")

    # 1. 뉴스 데이터 수집
    news_items = get_google_news("난임 시험관 아기 인공수정 배아 수정란 Embryo quality ivf infertility biotechnology", days=7,max_results=10)

    print(f"수집된 뉴스 개수: {len(news_items)}")
    
    # 2. 논문 데이터 수집
    paper_items = get_pubmed_papers("Embryo quality ivf infertility biotechnology", max_results=5)
    
    print(f"수집된 논문 개수: {len(paper_items)}")
    
    # 3. 데이터가 없을 경우 처리
    if not news_items and not paper_items:
        print("최근 7일간 새로운 뉴스나 논문이 발견되지 않았습니다.")
        return

    # 4. LLM 요약 (Gemini)
    print("Gemini를 사용해 요약 생성 중...")
    news_summary = summarize_content(news_items, category="주요 뉴스")
    # 60초 동안 프로세스를 중단합니다.
    time.sleep(60)
    paper_summary = summarize_content(paper_items, category="주요 논문")
    
    # 5. HTML 뉴스레터 생성
    html_content = format_as_html(news_summary, paper_summary)
    
    # 6. 이메일 발송
    print("이메일 발송 준비 중...")
    success = send_newsletter(html_content)
    
    if success:
        print("전체 프로세스 완료!")
    else:
        print("프로세스 도중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()
