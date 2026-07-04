import logging

from agents.base import call_gemini
from models.question import Question
from models.student import StudentProfile
from models.ui_schema import CardType, tag

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_EN = """You are a friendly, encouraging tutor — like an older sibling helping with exam prep.
A student answered a question incorrectly. Provide:
1. Why their answer was wrong (brief, kind)
2. Step-by-step correct solution
3. Key concept to remember
4. Words of encouragement
5. A simpler analogy to remember the concept

Keep responses concise and warm. No jargon. Exam-focused."""

SYSTEM_PROMPT_HI = """Aap ek friendly, encouraging tutor ho — jaise ek bade bhai/behen jo exam prep mein help kar rahe ho.
Ek student ne galat answer diya. Yeh provide karo (Hinglish mein — Hindi script mein likho, lekin technical words jaise 'Formula', 'Concept', 'Solution' English mein rakho):
1. Galti kyun hui (brief, kind tone mein)
2. Sahi answer ka step-by-step Solution
3. Yaad rakhne wala key Concept
4. Thoda sa encouragement
5. Ek simple example ya trick jo concept pakka kare"""


class FeedbackAgent:
    def explain_wrong_answer(self, student: StudentProfile, question: Question, wrong_index: int) -> dict:
        chosen_option = question.options[wrong_index] if wrong_index < len(question.options) else "Unknown"
        correct_option = question.options[question.correct_index]

        is_hindi = student.preferred_language.value == "hi"
        q_text = question.question_text_hi if (is_hindi and question.question_text_hi) else question.question_text_en
        system = SYSTEM_PROMPT_HI if is_hindi else SYSTEM_PROMPT_EN
        prompt = (
            f"Question: {q_text}\n"
            f"Options: {question.options}\n"
            f"Student chose: option {wrong_index} = '{chosen_option}'\n"
            f"Correct answer: option {question.correct_index} = '{correct_option}'\n"
            f"Topic: {question.subject} → {question.topic}\n"
        )
        response = call_gemini(prompt, system)
        return tag({
            "explanation": response or f"The correct answer is {correct_option}. {question.explanation_en}",
            "concept": question.topic,
            "encouragement": "You're making progress — keep practising!",
        }, CardType.FEEDBACK)

    async def run(self, student: StudentProfile, question: Question, wrong_index: int) -> dict:
        return self.explain_wrong_answer(student, question, wrong_index)
