import json
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def get_questions_for_exam(exam_id: str, stage: int = 1, limit: Optional[int] = None) -> List[Dict]:
    """
    Load questions for a given exam_id from JSON data.
    If stage == 1, load broad diagnostic questions.
    If stage == 2, load specific topic questions.
    If stage == 3, load atomic concept questions.
    """
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "question_banks", f"{exam_id}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            
            # Simulate progressive drill down by slicing
            if stage == 1:
                pool = questions
            elif stage == 2:
                pool = questions[len(questions)//3:] if len(questions) > 10 else questions
            else:
                pool = questions[(2*len(questions))//3:] if len(questions) > 10 else questions
                
            if not pool:
                pool = questions
                
            if limit is None:
                limit = 75
                
            # Do not cycle questions if pool is smaller than limit. Just return what we have.
            return pool[:limit]
    except FileNotFoundError:
        logger.error(f"No question bank found for {exam_id} at {file_path}")
        return []
