import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime

from models.student import StudentProfile, Language

logger = logging.getLogger(__name__)

DEV_MODE = not os.getenv("GOOGLE_CLIENT_ID")


def _encrypt(text: str) -> str:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        return text
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.encrypt(text.encode()).decode()
    except Exception:
        return text


def _decrypt(token: str) -> str:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        return token
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.decrypt(token.encode()).decode()
    except Exception:
        return token


class GoogleOAuth:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/callback")
        self._states: dict[str, str] = {}

    def get_authorization_url(self) -> tuple[str, str]:
        state = secrets.token_urlsafe(32)
        from authlib.integrations.requests_client import OAuth2Session
        session = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope="openid email profile",
        )
        url, state = session.create_authorization_url(
            "https://accounts.google.com/o/oauth2/v2/auth",
            state=state,
        )
        self._states[state] = state
        return url, state

    def handle_callback(self, code: str, state: str) -> tuple[str, dict]:
        from authlib.integrations.requests_client import OAuth2Session
        session = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )
        token = session.fetch_token(
            "https://oauth2.googleapis.com/token",
            code=code,
            grant_type="authorization_code",
        )
        user_info = self.get_user_info(token["access_token"])
        return token["access_token"], user_info

    def get_user_info(self, access_token: str) -> dict:
        import httpx
        resp = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()

    def create_or_get_student(
        self,
        user_info: dict,
        exam_target: str = "rrb_ntpc",
        language: str = "en",
    ) -> StudentProfile:
        google_sub = user_info["sub"]
        student_id = hashlib.sha256(google_sub.encode()).hexdigest()
        encrypted_sub = _encrypt(google_sub)
        return StudentProfile(
            student_id=student_id,
            google_sub=encrypted_sub,
            exam_target=exam_target,
            preferred_language=Language(language),
            created_at=datetime.utcnow(),
        )

    def dev_login(
        self,
        exam_target: str = "rrb_ntpc",
        language: str = "en",
        name: str = "Demo Student",
    ) -> StudentProfile:
        dev_sub = f"dev_{name.lower().replace(' ', '_')}"
        student_id = hashlib.sha256(dev_sub.encode()).hexdigest()
        return StudentProfile(
            student_id=student_id,
            google_sub=_encrypt(dev_sub),
            exam_target=exam_target,
            preferred_language=Language(language),
            diagnostic_done=False,
            created_at=datetime.utcnow(),
        )
