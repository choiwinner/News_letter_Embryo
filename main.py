from crawler import get_google_news, get_pubmed_papers
from summarizer import summarize_content
from mailer import send_newsletter, format_as_html
from knowledge_graph import generate_knowledge_graph
import os
from dotenv import load_dotenv
import time

load_dotenv()

def main():
    print("난임 및 배아 연구 동향 리서치 시작...")

    # 1. 뉴스 데이터 수집
    news_items = get_google_news("난임 OR 인공수정 OR 시험관아기 OR 체외수정 OR 난자동결 OR Infertility OR IVF OR Embryo", days=7,max_results=10)

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

    # 60초 대기 (다음 API 호용 전 RPM 제한 회피)
    time.sleep(60)
    # 5. 지식 그래프 생성 (뉴스 요약 후 RPM 대기 시간 활용)
    graph_base64 = generate_knowledge_graph(news_items)

    # 60초 대기 (다음 API 호용 전 RPM 제한 회피)
    time.sleep(60)
    paper_summary = summarize_content(paper_items, category="주요 논문")

    # 6. HTML 뉴스레터 생성
    html_content = format_as_html(news_summary, paper_summary, graph_base64=graph_base64)
    
    # 6. 이메일 발송
    print("이메일 발송 준비 중...")
    success = send_newsletter(html_content)
    
    if success:
        print("전체 프로세스 완료!")
    else:
        print("프로세스 도중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()
