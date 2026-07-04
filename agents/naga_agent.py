import logging
import uuid
import re
from datetime import datetime
from models.student import StudentProfile
from models.mentor import Question, MeetingRequest, MeetingRequestStatus
from models.ui_schema import CardType, tag

logger = logging.getLogger(__name__)

class NagaAgent:
    def __init__(self):
        # In a real system, these would interact with a database
        self.pending_questions = []
        self.meeting_requests = []

    def _extract_intent(self, text: str) -> dict:
        text_lower = text.lower()
        if "1 on 1" in text_lower or "one on one" in text_lower or "meeting" in text_lower or "schedule" in text_lower:
            return {"type": "meeting", "message": text}
        elif "doubt" in text_lower or "question" in text_lower or "ask naga" in text_lower:
            # Simple extraction for demo
            return {"type": "question", "topic": "General", "content": text}
        return {"type": "unknown", "message": text}

    def handle_meeting_request(self, student: StudentProfile, message: str) -> dict:
        req = MeetingRequest(
            request_id=str(uuid.uuid4()),
            student_id=student.student_id,
            student_name=student.google_sub or "Student",
            student_email="student@example.com",
            message=message,
            status=MeetingRequestStatus.PENDING,
            created_at=datetime.utcnow()
        )
        self.meeting_requests.append(req)
        logger.info(f"Meeting request created for {student.student_id}")
        
        return tag({
            "message": "I have submitted your request for a 1-on-1 session to Naga. You will receive an RSVP link soon.",
            "request_id": req.request_id
        }, CardType.NAGA_INTERACTION)

    def handle_question(self, student: StudentProfile, topic: str, content: str) -> dict:
        q = Question(
            question_id=str(uuid.uuid4()),
            student_id=student.student_id,
            student_name=student.google_sub or "Student",
            subject="General", # Ideally extracted from NLP
            topic=topic,
            content=content,
            created_at=datetime.utcnow()
        )
        self.pending_questions.append(q)
        logger.info(f"Question submitted for Naga approval by {student.student_id}")
        
        return tag({
            "message": "Your doubt has been submitted to the Q&A board! Naga will review and answer it shortly.",
            "question_id": q.question_id
        }, CardType.NAGA_INTERACTION)

    async def run(self, student: StudentProfile, message: str) -> dict:
        intent = self._extract_intent(message)
        
        if intent["type"] == "meeting":
            return self.handle_meeting_request(student, intent["message"])
        elif intent["type"] == "question":
            return self.handle_question(student, intent["topic"], intent["content"])
        else:
            return tag({
                "message": "I can help you schedule a 1-on-1 with Naga or submit a doubt for him to review. How can I assist?"
            }, CardType.NAGA_INTERACTION)
