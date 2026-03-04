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
    이미지 URL이 포함된 경우 <img> 태그를 삽입합니다.
    """
    import re

    def process_summary(text):
        # 1. Image URL 패턴을 더 유연하게 찾기 (4. Image: 또는 그냥 URL)
        processed = []
        # 뉴스 항목들을 분리 (번호로 시작하거나 빈 줄로 구분된 경우 대응)
        items = re.split(r'\n\s*\n|\n(?=\d+\.\s*제목:)', text)
        
        for item in items:
            if not item.strip(): continue
            
            # 이미지 URL 추출 (4. Image: URL 또는 텍스트 내의 URL 추출)
            # 이미지 URL 추출 (4. Image: 또는 Image: 형식 모두 대응)
            img_match = re.search(r'(?:\d+\.\s*)?Image:\s*(https?://\S+)', item, re.IGNORECASE)
            if not img_match:
                # 일반적인 URL 검색 (구글 서버 제외)
                img_urls = re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?\S+)?', item, re.IGNORECASE)
                img_url = next((u for u in img_urls if "googleusercontent.com" not in u and "gstatic.com" not in u), None)
            else:
                img_url = img_match.group(1).strip()
                if "None" in img_url or "googleusercontent.com" in img_url:
                    img_url = None

            item_html = item.replace('\n', '<br>')
            # 형식 태그 제거 (번호 등 모든 Image 라인 제거)
            item_html = re.sub(r'(<br>)?(?:\d+\.\s*)?Image:.*', '', item_html, flags=re.IGNORECASE)
            
            if img_url:
                item_html = f"""
                <div class="item-content">
                    <div class="item-image">
                        <a href="{img_url}" target="_blank">
                            <img src="{img_url}" alt="News Image">
                        </a>
                    </div>
                    <div class="item-text">
                        {item_html}
                    </div>
                </div>
                """
            else:
                item_html = f'<div class="item-text">{item_html}</div>'
                
            processed.append(f'<div class="item">{item_html}</div>')
        
        return "\n".join(processed)

    news_html = process_summary(news_summary)
    paper_html = process_summary(paper_summary)

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f0f2f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 30px; background: #fff; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
            h1 {{ color: #1a365d; border-bottom: 4px solid #3182ce; padding-bottom: 15px; text-align: center; font-size: 2.2em; letter-spacing: -1px; }}
            h2 {{ color: #2d3748; margin-top: 40px; border-left: 6px solid #3182ce; padding-left: 15px; font-size: 1.5em; }}
            
            .item {{ margin-bottom: 25px; border: 1px solid #e1e8ed; border-radius: 10px; overflow: hidden; background-color: #ffffff; transition: transform 0.2s; }}
            .item:hover {{ border-color: #3182ce; box-shadow: 0 4px 12px rgba(49, 130, 206, 0.1); }}
            
            .item-content {{ display: flex; align-items: flex-start; gap: 20px; padding: 20px; }}
            .item-image {{ flex: 0 0 200px; max-width: 200px; }}
            .item-image img {{ width: 100%; height: 140px; object-fit: cover; border-radius: 8px; border: 1px solid #eee; }}
            .item-text {{ flex: 1; font-size: 0.95em; color: #4a5568; }}
            
            .footer {{ margin-top: 60px; font-size: 0.85em; color: #718096; text-align: center; border-top: 2px solid #edf2f7; padding-top: 30px; }}
            
            @media (max-width: 600px) {{
                .item-content {{ flex-direction: column; }}
                .item-image {{ flex: 0 0 auto; max-width: 100%; }}
                .item-image img {{ height: auto; max-height: 250px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 주간 난임 & 배아 연구 동향 뉴스레터</h1>
            <p style="text-align: center; color: #718096; font-size: 1.1em; margin-bottom: 40px;">DeepMind Gemini 3 Flash 기반 선별 브리핑</p>
            
            <h2>📰 주요 뉴스 (Core News)</h2>
            {news_html}

            <h2>📚 주요 논문 (Research Papers)</h2>
            {paper_html}

            <div class="footer">
                <strong>© 2026 Tech Trends Weekly</strong><br>
                AI 분석 및 자동 생성 리포트 | 수신거부: 설정 페이지
            </div>
        </div>
    </body>
    </html>
    """
    return html
