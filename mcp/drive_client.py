import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
OFFLINE_DIR = Path("data/drive_offline")


class DriveClient:
    def __init__(self):
        self.offline_mode = not os.getenv("GOOGLE_DRIVE_CREDENTIALS_JSON")
        if self.offline_mode:
            logger.warning("DriveClient running in offline mode — no credentials found")
            OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
        else:
            self._init_real_client()

    def _init_real_client(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds_json = json.loads(os.environ["GOOGLE_DRIVE_CREDENTIALS_JSON"])
            creds = service_account.Credentials.from_service_account_info(
                creds_json, scopes=["https://www.googleapis.com/auth/drive.file"]
            )
            self._service = build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Drive init failed: {e}. Falling back to offline mode.")
            self.offline_mode = True

    def save_study_notes(self, student_id: str, topic: str, content: str, exam: str = "general") -> dict:
        title = f"VidyaBot — {topic} ({exam.upper()})"
        if self.offline_mode:
            safe_topic = topic.replace(" ", "_").replace("/", "-")
            path = OFFLINE_DIR / student_id
            path.mkdir(parents=True, exist_ok=True)
            file_path = path / f"{safe_topic}.md"
            file_path.write_text(f"# {title}\n\n{content}")
            return {
                "url": f"file://{file_path.resolve()}",
                "file_id": f"offline_{student_id}_{safe_topic}",
                "title": title,
            }
        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(content.encode(), mimetype="text/markdown")
        file_meta = {"name": f"{title}.md", "mimeType": "text/markdown"}
        result = self._service.files().create(body=file_meta, media_body=media, fields="id,webViewLink").execute()
        return {"url": result["webViewLink"], "file_id": result["id"], "title": title}

    def list_student_notes(self, student_id: str) -> list[dict]:
        if self.offline_mode:
            path = OFFLINE_DIR / student_id
            if not path.exists():
                return []
            return [{"title": f.stem, "url": f"file://{f.resolve()}", "file_id": f.stem} for f in path.glob("*.md")]
        results = self._service.files().list(
            q=f"name contains 'VidyaBot'", fields="files(id,name,webViewLink)"
        ).execute()
        return [{"title": f["name"], "url": f["webViewLink"], "file_id": f["id"]} for f in results.get("files", [])]

    def as_tool(self):
        try:
            from google.adk.tools import FunctionTool
            return FunctionTool(self.save_study_notes)
        except ImportError:
            return self.save_study_notes
