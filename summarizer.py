from google import genai
from google.genai import errors
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

import time

# RPM 제한을 위한 마지막 호출 시간 기록
last_call_time = 0

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(errors.ClientError),
    reraise=True
)
def generate_content_with_retry(client, model_name, prompt):
    """
    할당량 초과(429) 시 재시도를 포함하여 콘텐츠를 생성합니다.
    분당 요청 제한(RPM 5)을 위해 호출 전 대기 시간을 가집니다.
    """
    global last_call_time
    
    # 마지막 호출로부터 최소 15초(RPM 4 목표)가 경과했는지 확인
    elapsed = time.time() - last_call_time
    if elapsed < 15:
        wait_time = 15 - elapsed
        print(f"RPM 제한을 위해 {wait_time:.1f}초 대기 중...")
        time.sleep(wait_time)
        
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        last_call_time = time.time() # 성공적으로 호출한 시간 기록
        return response.text
    except errors.ClientError as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"API 할당량 초과. 재시도 중... ({e})")
            raise e
        raise e

def summarize_content(items, category="뉴스"):
    """
    수집된 항목들을 최신 google.genai SDK를 사용하여 요약합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "API 키가 설정되지 않았습니다."
    
    client = genai.Client(api_key=api_key)
    
    # gemini-3-flash는 현재 하루 20회 요청으로 제한이 매우 엄격합니다.
    # 성능이 뛰어나고 할당량(분당 15회)이 더 넉넉한 gemini-2.0-flash를 사용합니다.
    model_name = "gemini-3-flash-preview" 
    # model_name = "gemini-2.5-flash-lite"

    prompt = f"""
    당신은 난임 및 생명공학(배아 발생학) 전문가입니다. 다음 제공된 {category} 목록을 바탕으로 주간 브리핑을 작성해 주세요.
    
    각 항목에 대해 다음 형식을 엄격히 지켜주세요:
    1. 제목: [기사/논문의 핵심 내용을 담은 한글 제목]
    2. 요약: [내용을 2-3문장으로 핵심 요약]
    3. URL: [제공된 원본 URL 링크 그대로. 마크다운 형식을 사용하지 마세요. 예: http://...]
    4. Image: [제공된 image_url이 있다면 그 URL 그대로, 없다면 'None'. 마크다운 형식을 사용하지 마세요.]
    
    주의 사항:
    - URL과 Image 필드에는 오직 URL 텍스트만 포함해야 합니다. [링크명](URL) 형식을 절대 사용하지 마세요.
    - 언어는 한국어여야 합니다. 전문적이고 분석적인 톤을 유지하세요.
    - 최근 난임 치료 기술, 배아 등급(Embryo quality) 평가, 생명공학 관련 최신 연구 동향에 집중해 주세요.
    
    대상 데이터:
    {items}
    """
    
    try:
        return generate_content_with_retry(client, model_name, prompt)
    except Exception as e:
        return f"요약 생성 중 오류 발생: {e}"

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
