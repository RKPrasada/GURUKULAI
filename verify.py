import asyncio
import os
import sys

# Ensure imports work
sys.path.insert(0, "/Users/aruna/vidyabot")

from models.student import StudentProfile, Language
from agents.orchestrator import OrchestratorAgent

async def main():
    print("Initializing Orchestrator...")
    orchestrator = OrchestratorAgent()
    
    print("\nCreating Student Profile for RRB ALP (not diagnostic done)...")
    student = StudentProfile(
        student_id="test_001",
        google_sub="test_user",
        exam_target="rrb_alp",
        preferred_language=Language.ENGLISH
    )
    
    print("\nSending 'start learning'...")
    res = await orchestrator.handle(student, "start learning")
    print(res)
    
    if "session_id" in res:
        print("\nSubmitting answers (Stage 1)...")
        # Simulating mostly wrong answers to get < 40%
        # All correct_index are 0, so we pass 1 to get wrong
        answers = [1] * res["total"] 
        res2 = orchestrator.diagnostic.submit_answers(student, res["session_id"], answers)
        print(res2)
        print(f"Student done: {student.diagnostic_done}, Stage: {student.diagnostic_stage}")
        
    print("\nSimulating asking NAGA for 1 on 1...")
    res3 = await orchestrator.handle(student, "Can I schedule a 1 on 1 meeting?")
    print(res3)
    
    print("\nSimulating generating schedule...")
    res4 = await orchestrator.handle(student, "Generate my full syllabus schedule")
    print(res4)

if __name__ == "__main__":
    asyncio.run(main())
