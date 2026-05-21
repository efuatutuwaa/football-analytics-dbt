import smtplib
import sys
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("TRIAGE_RECIPIENT_EMAIL", GMAIL_USER)


def send_report(subject: str, body_text: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    html = f"""
    <html><body>
    <h2 style="color:#c0392b;">dbt Triage Report</h2>
    <p style="color:#666;">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    <hr/>
    <pre style="font-family:monospace;font-size:13px;background:#f4f4f4;padding:16px;border-radius:6px;">
{body_text}
    </pre>
    <hr/>
    <p style="color:#999;font-size:11px;">football-analytics-dbt · automated triage</p>
    </body></html>
    """

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())

    print(f"Report sent to {RECIPIENT_EMAIL}")


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "dbt Triage Report"
    body = sys.stdin.read()
    send_report(subject, body)
