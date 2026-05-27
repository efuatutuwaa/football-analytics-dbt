import smtplib
import sys
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def send_report(subject: str, body_text: str) -> None:
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("TRIAGE_RECIPIENT_EMAIL", gmail_user)

    if not gmail_user or not gmail_password:
        print("Email skipped — GMAIL_USER or GMAIL_APP_PASSWORD not set.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient

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
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipient, msg.as_string())

    print(f"Report sent to {recipient}")


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "dbt Triage Report"
    body = sys.stdin.read()
    send_report(subject, body)
