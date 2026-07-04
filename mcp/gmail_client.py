import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
OFFLINE_DIR = Path("data/gmail_offline")


class GmailClient:
    def __init__(self):
        self.offline_mode = not os.getenv("GOOGLE_GMAIL_CREDENTIALS_JSON")
        if self.offline_mode:
            logger.warning("GmailClient running in offline mode — no credentials")
            OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
        else:
            self._init_real_client()

    def _init_real_client(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds_json = json.loads(os.environ["GOOGLE_GMAIL_CREDENTIALS_JSON"])
            creds = service_account.Credentials.from_service_account_info(
                creds_json, scopes=["https://www.googleapis.com/auth/gmail.send"]
            )
            self._service = build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"Gmail init failed: {e}. Falling back to offline mode.")
            self.offline_mode = True

    def _build_html(self, student_name: str, summary: dict) -> str:
        weak = ", ".join(summary.get("weak_areas", [])) or "None identified yet"
        topics = ", ".join(summary.get("topics_studied", [])) or "No topics this week"
        return f"""
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#5C35CC">VidyaBot Weekly Progress Report</h2>
<p>Hello <b>{student_name}</b>! Here's your week {summary.get('week','')}: study summary.</p>
<table style="width:100%;border-collapse:collapse">
  <tr style="background:#f0ebff"><td style="padding:10px"><b>Exam Target</b></td><td>{summary.get('exam','').upper()}</td></tr>
  <tr><td style="padding:10px"><b>Topics Studied</b></td><td>{topics}</td></tr>
  <tr style="background:#f0ebff"><td style="padding:10px"><b>Questions Attempted</b></td><td>{summary.get('questions_attempted',0)}</td></tr>
  <tr><td style="padding:10px"><b>Accuracy</b></td><td>{summary.get('accuracy_pct',0):.1f}%</td></tr>
  <tr style="background:#f0ebff"><td style="padding:10px"><b>Study Streak</b></td><td>{summary.get('streak_days',0)} days 🔥</td></tr>
  <tr><td style="padding:10px"><b>Areas to Focus</b></td><td style="color:#e53935">{weak}</td></tr>
</table>
<p style="margin-top:20px;color:#666">Keep it up! Consistency is the key to cracking {summary.get('exam','').upper()}.</p>
<p style="color:#999;font-size:12px">VidyaBot — AI Tutor for Indian Competitive Exams</p>
</body></html>"""

    def send_progress_digest(self, to_email: str, student_name: str, summary: dict) -> bool:
        html = self._build_html(student_name, summary)
        if self.offline_mode:
            safe_id = to_email.replace("@", "_at_").replace(".", "_")
            OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
            (OFFLINE_DIR / f"{safe_id}_digest.html").write_text(html)
            logger.info(f"Offline digest saved for {to_email}")
            return True
        try:
            import base64
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"VidyaBot Weekly Report — {summary.get('week', 'This Week')}"
            msg["To"] = to_email
            msg.attach(MIMEText(html, "html"))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self._service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return True
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return False

    def as_tool(self):
        try:
            from google.adk.tools import FunctionTool
            return FunctionTool(self.send_progress_digest)
        except ImportError:
            return self.send_progress_digest
