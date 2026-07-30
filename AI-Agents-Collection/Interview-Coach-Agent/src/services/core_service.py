import json
import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.logging_config import logger
from src.agent.graph import interview_graph, evaluate_answer_node, generate_report_node
from src.agent.memory import memory_store
from src.db.models import InterviewSessionModel, AnswerEvaluationModel
from src.models.schemas import (
    QuestionGenerationResponse,
    SkillExtractionResult,
    QuestionItem,
    AnswerEvaluationResponse,
    FinalReportResponse
)

class InterviewCoachService:

    @staticmethod
    async def initialize_interview(
        resume_text: str,
        target_role: str,
        difficulty: str,
        question_count: int,
        db: AsyncSession
    ) -> QuestionGenerationResponse:
        session_id = str(uuid.uuid4())
        logger.info(f"Initializing interview session: {session_id}")

        initial_state = {
            "session_id": session_id,
            "resume_text": resume_text,
            "target_role": target_role,
            "difficulty": difficulty,
            "extracted_skills": None,
            "questions": [],
            "current_question_index": 0,
            "candidate_answers": [],
            "evaluations": [],
            "overall_summary": None,
            "status": "initialized",
            "error": None
        }

        # Run state graph
        result_state = interview_graph.invoke(initial_state)
        memory_store.save_state(session_id, result_state)

        # Save to SQLite DB
        skills_data = result_state.get("extracted_skills", {})
        session_db = InterviewSessionModel(
            session_id=session_id,
            candidate_name=skills_data.get("candidate_name", "Candidate"),
            target_role=target_role,
            difficulty=difficulty,
            parsed_skills_json=json.dumps(skills_data)
        )
        db.add(session_db)
        await db.commit()

        skills_obj = SkillExtractionResult(
            candidate_name=skills_data.get("candidate_name", "Candidate"),
            experience_years=skills_data.get("experience_years", 3.0),
            primary_skills=skills_data.get("primary_skills", []),
            secondary_skills=skills_data.get("secondary_skills", []),
            roles_suited=skills_data.get("roles_suited", [target_role])
        )

        questions = [
            QuestionItem(**q) for q in result_state.get("questions", [])
        ]

        return QuestionGenerationResponse(
            session_id=session_id,
            candidate_skills=skills_obj,
            questions=questions
        )

    @staticmethod
    async def evaluate_candidate_answer(
        session_id: str,
        question_id: int,
        question_text: str,
        candidate_answer: str,
        db: AsyncSession
    ) -> AnswerEvaluationResponse:
        logger.info(f"Evaluating answer for session {session_id}, question {question_id}")
        state = memory_store.get_state(session_id)
        if not state:
            state = {
                "session_id": session_id,
                "candidate_answers": [],
                "evaluations": [],
                "extracted_skills": {"candidate_name": "Candidate"},
                "target_role": "Software Engineer"
            }

        candidate_answers = state.get("candidate_answers", [])
        candidate_answers.append({
            "question_id": question_id,
            "question_text": question_text,
            "candidate_answer": candidate_answer,
            "target_skill": "Technical Concept"
        })
        state["candidate_answers"] = candidate_answers

        updated_state = evaluate_answer_node(state)
        memory_store.save_state(session_id, updated_state)

        latest_eval = updated_state["evaluations"][-1]

        # Save evaluation to DB
        eval_db = AnswerEvaluationModel(
            session_id=session_id,
            question_id=question_id,
            question_text=question_text,
            candidate_answer=candidate_answer,
            score=latest_eval.get("score", 7.0),
            technical_accuracy=latest_eval.get("technical_accuracy", 7.0),
            communication_score=latest_eval.get("communication_score", 7.0),
            strengths_json=json.dumps(latest_eval.get("strengths", [])),
            weaknesses_json=json.dumps(latest_eval.get("weaknesses", [])),
            feedback=latest_eval.get("improvement_feedback", "")
        )
        db.add(eval_db)
        await db.commit()

        return AnswerEvaluationResponse(
            session_id=session_id,
            question_id=question_id,
            score=latest_eval.get("score", 7.0),
            technical_accuracy=latest_eval.get("technical_accuracy", 7.0),
            communication_score=latest_eval.get("communication_score", 7.0),
            strengths=latest_eval.get("strengths", []),
            weaknesses=latest_eval.get("weaknesses", []),
            improvement_feedback=latest_eval.get("improvement_feedback", ""),
            suggested_followup_question=latest_eval.get("suggested_followup_question")
        )

    @staticmethod
    async def generate_final_report(session_id: str, db: AsyncSession) -> FinalReportResponse:
        logger.info(f"Generating final report for session {session_id}")
        state = memory_store.get_state(session_id)
        if not state:
            state = {
                "session_id": session_id,
                "extracted_skills": {"candidate_name": "Candidate"},
                "target_role": "Software Engineer",
                "evaluations": []
            }

        updated_state = generate_report_node(state)
        summary = updated_state.get("overall_summary", {})
        evaluations_list = [
            AnswerEvaluationResponse(
                session_id=session_id,
                question_id=e.get("question_id", i+1),
                score=e.get("score", 7.0),
                technical_accuracy=e.get("technical_accuracy", 7.0),
                communication_score=e.get("communication_score", 7.0),
                strengths=e.get("strengths", []),
                weaknesses=e.get("weaknesses", []),
                improvement_feedback=e.get("improvement_feedback", "")
            )
            for i, e in enumerate(updated_state.get("evaluations", []))
        ]

        # Update Session DB overall score
        result = await db.execute(select(InterviewSessionModel).filter_by(session_id=session_id))
        session_db = result.scalars().first()
        if session_db:
            session_db.overall_score = summary.get("average_score", 0.0)
            session_db.hiring_recommendation = summary.get("hiring_recommendation", "Hire")
            await db.commit()

        skills = state.get("extracted_skills", {})

        return FinalReportResponse(
            session_id=session_id,
            candidate_name=skills.get("candidate_name", "Candidate"),
            target_role=state.get("target_role", "Software Engineer"),
            total_questions=len(evaluations_list),
            average_score=summary.get("average_score", 7.5),
            overall_strengths=summary.get("overall_strengths", ["Solid knowledge"]),
            critical_weaknesses=summary.get("critical_weaknesses", ["Needs practical depth"]),
            hiring_recommendation=summary.get("hiring_recommendation", "Hire"),
            detailed_evaluations=evaluations_list
        )
