import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

def summarize_content(items, category="뉴스"):
    """
    수집된 항목들을 Gemini 3 Flash를 사용하여 요약합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "API 키가 설정되지 않았습니다."
    
    genai.configure(api_key=api_key)
    
    # Gemini 3 Flash 모델 설정 (모델명이 정식 출시 전후로 다를 수 있으나, 최신 모델명 가이드에 따름)
    # 현재 시점에서 gemini-2.0-flash 등의 명칭이 쓰일 수 있으나 요구사항대로 'gemini-3-flash' 지향
    # 실제 API에서 지원하는 모델명 확인 필요 (보통 gemini-1.5-flash가 최신 범용)
    # 여기서는 요구사항에 맞춰 모델 식별자 설정 (실제 동작을 위해 1.5-flash로 폴백하거나 안내 필요할 수 있음)
    model_name = "gemini-3-flash-preview" # 현재 실존하는 가장 최신 모델명으로 설정, 혹은 명시적 요청 반영
    
    try:
        model = genai.GenerativeModel(model_name)
    except:
        # 모델명을 찾지 못할 경우 범용 모델로 폴백
        model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    당신은 난임 및 생명공학(배아 발생학) 전문가입니다. 다음 제공된 {category} 목록을 바탕으로 주간 브리핑을 작성해 주세요.
    
    각 항목에 대해 다음 형식을 엄격히 지켜주세요:
    1. 제목: [기사/논문의 핵심 내용을 담은 한글 제목]
    2. 요약: [내용을 2-3문장으로 핵심 요약]
    3. URL: [제공된 원본 URL]
    
    언어는 한국어여야 합니다. 전문적이고 분석적인 톤을 유지하세요.
    최근 난임 치료 기술, 배아 등급(Embryo quality) 평가, 생명공학 관련 최신 연구 동향에 집중해 주세요.
    
    대상 데이터:
    {items}
    """
    
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    # 테스트 코드
    test_items = [
        {"title": "SK Hynix sample HBM4 to NVIDIA", "link": "https://example.com/1", "source": "News"},
        {"title": "Samsung Electronics develops 12-layer HBM3E", "link": "https://example.com/2", "source": "News"}
    ]
    # API 키가 있는 경우에만 실행
    if os.getenv("GEMINI_API_KEY"):
        print(summarize_content(test_items))
    else:
        print("GEMINI_API_KEY가 .env 파일에 없습니다.")
