import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def send_newsletter(content_html, subject="[주간 리포트] 난임 치료 및 배아 연구 동향"):
    """
    구성된 HTML 뉴스레터를 이메일로 발송합니다.
    """
    smtp_server = os.getenv("EMAIL_SMTP_SERVER")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", 587))
    smtp_user = os.getenv("EMAIL_USER")
    smtp_password = os.getenv("EMAIL_PASSWORD")
    recipient_emails = os.getenv("RECIPIENT_EMAILS", "").split(",")

    if not all([smtp_server, smtp_user, smtp_password, recipient_emails]):
        print("이메일 설정이 누락되었습니다. (.env 파일을 확인하세요)")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ", ".join(recipient_emails)
        msg['Subject'] = subject

        msg.attach(MIMEText(content_html, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            
        print(f"이메일 발송 성공: {len(recipient_emails)}명에게 전달되었습니다.")
        return True
    except Exception as e:
        print(f"이메일 발송 실패: {e}")
        return False

def format_as_html(news_summary, paper_summary):
    """
    요약된 내용을 이메일용 HTML로 변환합니다.
    News_html_ex.html의 스타일을 참조하여 가독성이 높고 프리미엄한 디자인을 적용합니다.
    """
    import re
    from datetime import datetime

    current_date = datetime.now().strftime("%Y-%m-%d")

    def process_summary(text):
        processed = []
        # 뉴스 항목들을 분리
        items = re.split(r'\n\s*\n|\n(?=\d+\.\s*제목:)', text)
        
        for item in items:
            if not item.strip(): continue
            
            def clean_url(url_str):
                if not url_str: return None
                match = re.search(r'!?\[.*?\]\((https?://\S+?)\)', url_str)
                if match:
                    return match.group(1).rstrip(')]')
                return url_str.strip('[]() ')

            # 이미지 URL 추출
            img_match = re.search(r'(?:\d+\.\s*)?Image:\s*(\S+)', item, re.IGNORECASE)
            img_url = None
            if img_match:
                img_url = clean_url(img_match.group(1))
                if img_url and ("None" in img_url or "googleusercontent.com" in img_url):
                    img_url = None
            
            if not img_url:
                img_urls = re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?\S+)?', item, re.IGNORECASE)
                if img_urls:
                    img_url = clean_url(img_urls[0])
                    if img_url and ("googleusercontent.com" in img_url or "gstatic.com" in img_url):
                        img_url = None

            # URL 추출 및 본문 내 URL 안내 제거 (번호가 없거나 다른 경우에도 대응)
            url_match = re.search(r'(?:\d+\.\s*)?URL:\s*(\S+)', item, re.IGNORECASE)
            article_url = "#"
            if url_match:
                raw_url = url_match.group(1)
                article_url = clean_url(raw_url)

            # 본문 내 URL 및 '더 알아보기' 문구 제거
            item_html = item.replace('\n', '<br>')
            # 형식 태그 및 URL 라벨 제거 (URL 라벨 줄 전체 제거)
            item_html = re.sub(r'(<br>)?(?:\d+\.\s*)?Image:.*', '', item_html, flags=re.IGNORECASE)
            item_html = re.sub(r'(<br>)?(?:\d+\.\s*)?URL:.*', '', item_html, flags=re.IGNORECASE)
            
            # 본문 내 '더 알아보기' 텍스트 제거 (중복 방지)
            item_html = item_html.replace('더 알아보기', '')
            
            # 불필요한 공백/줄바꿈 정리
            item_html = re.sub(r'(<br>\s*)+', '<br>', item_html).strip('<br> ')
            
            # 카드 레이아웃 (테이블 기반)
            if img_url:
                content_html = f"""
                <tr>
                    <td class="mobile-padding" style="padding: 25px 20px; border-bottom: 1px solid #eeeeee;">
                        <table role="presentation" width="100%">
                            <tr>
                                <td class="stack-column" width="30%" style="vertical-align: top; padding-right: 20px;">
                                    <a href="{article_url}" target="_blank" style="text-decoration: none;">
                                        <img src="{img_url}" alt="News Image" style="width: 100%; height: 140px; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid #f0f0f0;" onerror="this.style.display='none'">
                                    </a>
                                </td>
                                <td class="stack-column" width="70%" style="vertical-align: top;">
                                    <div style="font-size: 15px; color: #4a5568; line-height: 1.6;">
                                        {item_html}
                                    </div>
                                    <div style="margin-top: 15px;">
                                        <a href="{article_url}" style="color: #1a73e8; text-decoration: none; font-size: 14px; font-weight: bold;">더 알아보기 &rarr;</a>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                """
            else:
                content_html = f"""
                <tr>
                    <td class="mobile-padding" style="padding: 25px 20px; border-bottom: 1px solid #eeeeee;">
                        <div style="font-size: 15px; color: #4a5568; line-height: 1.6;">
                            {item_html}
                        </div>
                        <div style="margin-top: 15px;">
                            <a href="{article_url}" style="color: #1a73e8; text-decoration: none; font-size: 14px; font-weight: bold;">더 알아보기 &rarr;</a>
                        </div>
                    </td>
                </tr>
                """
            processed.append(content_html)
        
        return "\n".join(processed)

    news_items_html = process_summary(news_summary)
    paper_items_html = process_summary(paper_summary)

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; background-color: #f8f9fa; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; -webkit-font-smoothing: antialiased; }}
            table {{ border-collapse: collapse; }}
            img {{ display: block; max-width: 100%; }}
            .content-container {{ width: 100%; max-width: 650px; margin: 0 auto; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            
            @media only screen and (max-width: 600px) {{
                .mobile-padding {{ padding: 20px 15px !important; }}
                .stack-column {{ display: block !important; width: 100% !important; padding-right: 0 !important; }}
                .stack-column img {{ height: auto !important; max-height: 200px !important; margin-bottom: 15px; }}
            }}
        </style>
    </head>
    <body>
        <table role="presentation" class="content-container" align="center">
            <!-- 헤더 섹션 -->
                <td style="padding: 40px 20px; text-align: center; background-color: #1a73e8;">
                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; letter-spacing: -1px; font-weight: 800;">🚀주간 난임 & 배아 연구 동향 뉴스레터</h1>
                    <p style="margin: 10px 0 0; color: #e8f0fe; font-size: 14px; opacity: 0.9;">{current_date} | Gemini AI 가 선별한 최신 동향 전문 브리핑</p>
                </td>
            </tr>

            <!-- 뉴스 섹션 -->
            <tr>
                <td style="padding: 30px 20px 10px; background-color: #f1f6ff;">
                    <h2 style="margin: 0; font-size: 20px; color: #1a365d; display: flex; align-items: center;">
                        <span style="font-size: 24px; margin-right: 8px;">📰</span> 7일간 주요 뉴스
                    </h2>
                </td>
            </tr>
            {news_items_html}

            <!-- 논문 섹션 -->
            <tr>
                <td style="padding: 40px 20px 10px; background-color: #f1f6ff;">
                    <h2 style="margin: 0; font-size: 20px; color: #1a365d; display: flex; align-items: center;">
                        <span style="font-size: 24px; margin-right: 8px;">📚</span> 주요 논문 (Research Papers)
                    </h2>
                </td>
            </tr>
            {paper_items_html}

            <!-- 푸터 섹션 -->
            <tr>
                <td style="padding: 40px 20px; background-color: #f8f9fa; text-align: center; border-top: 1px solid #eeeeee;">
                    <p style="margin: 0; font-size: 13px; color: #70757a; font-weight: bold;">© 2026 Tech Trends Weekly</p>
                    <p style="margin: 8px 0 0; font-size: 12px; color: #9aa0a6;">본 메일은 AI(Gemini 3 Flash)를 통해 자동 생성된 주간 기술 리포트입니다.</p>
                    <div style="margin-top: 20px;">
                        <a href="#" style="color: #70757a; text-decoration: underline; font-size: 12px; margin: 0 10px;">수신 거부</a>
                        <a href="#" style="color: #70757a; text-decoration: underline; font-size: 12px; margin: 0 10px;">브라우저에서 보기</a>
                    </div>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html
