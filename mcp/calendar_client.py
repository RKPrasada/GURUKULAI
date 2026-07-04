import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
OFFLINE_DIR = Path("data/calendar_offline")


class CalendarClient:
    def __init__(self):
        self.offline_mode = not os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON")
        if self.offline_mode:
            logger.warning("CalendarClient running in offline mode — no credentials")
            OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
        else:
            self._init_real_client()

    def _init_real_client(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds_json = json.loads(os.environ["GOOGLE_CALENDAR_CREDENTIALS_JSON"])
            creds = service_account.Credentials.from_service_account_info(
                creds_json, scopes=["https://www.googleapis.com/auth/calendar"]
            )
            self._service = build("calendar", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Calendar init failed: {e}. Falling back to offline mode.")
            self.offline_mode = True

    def create_study_events(self, student_id: str, plan_json: str) -> dict:
        plan = json.loads(plan_json) if isinstance(plan_json, str) else plan_json
        event_ids = []
        if self.offline_mode:
            offline_path = OFFLINE_DIR / f"{student_id}_schedule.json"
            existing = json.loads(offline_path.read_text()) if offline_path.exists() else []
            for item in plan:
                event_id = f"offline_evt_{student_id}_{item.get('date', '')}_{item.get('topic', '').replace(' ', '_')}"
                existing.append({**item, "event_id": event_id, "timezone": "Asia/Kolkata"})
                event_ids.append(event_id)
            offline_path.write_text(json.dumps(existing, indent=2))
            return {"event_ids": event_ids, "count": len(event_ids)}

        for item in plan:
            date_str = item.get("date", datetime.now(IST).strftime("%Y-%m-%d"))
            time_str = item.get("time", "09:00")
            duration = item.get("duration_minutes", 60)
            start_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00").astimezone(IST)
            end_dt = start_dt + timedelta(minutes=duration)
            event = {
                "summary": f"VidyaBot: {item.get('topic', 'Study Session')}",
                "description": f"Exam: {item.get('exam', '').upper()} | VidyaBot study session",
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
            }
            result = self._service.events().insert(calendarId="primary", body=event).execute()
            event_ids.append(result["id"])
        return {"event_ids": event_ids, "count": len(event_ids)}

    def as_tool(self):
        try:
            from google.adk.tools import FunctionTool
            return FunctionTool(self.create_study_events)
        except ImportError:
            return self.create_study_events
