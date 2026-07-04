import os
import logging

logger = logging.getLogger(__name__)

class YouTubeClient:
    def __init__(self):
        self.offline_mode = not os.getenv("YOUTUBE_API_KEY")
        if self.offline_mode:
            logger.warning("YouTubeClient running in offline mode — no API key")
        else:
            from googleapiclient.discovery import build
            self._service = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])

    def search_videos(self, query: str, exam: str = "general", max_results: int = 5) -> list[dict]:
        if self.offline_mode:
            return []
        try:
            response = self._service.search().list(
                q=f"{query} {exam.upper()} exam India",
                part="snippet",
                maxResults=max_results,
                type="video",
                relevanceLanguage="en",
                regionCode="IN",
            ).execute()
            return [
                {
                    "title": item["snippet"]["title"],
                    "video_id": item["id"]["videoId"],
                    "url": f"https://youtu.be/{item['id']['videoId']}",
                    "channel": item["snippet"]["channelTitle"],
                    "duration": "",
                    "thumbnail_url": item["snippet"]["thumbnails"]["medium"]["url"],
                }
                for item in response.get("items", [])
            ]
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []

    def as_tool(self):
        try:
            from google.adk.tools import FunctionTool
            return FunctionTool(self.search_videos)
        except ImportError:
            return self.search_videos
