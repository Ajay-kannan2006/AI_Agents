import json
import uuid
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from config.settings import settings
from config.logging_config import logger
from src.agent.state import InterviewState
from src.agent.prompts import (
    RESUME_PARSER_PROMPT,
    QUESTION_GENERATOR_PROMPT,
    EVALUATE_ANSWER_PROMPT,
    FINAL_REPORT_PROMPT
)
from src.agent.tools import parse_resume_text, calculate_interview_score

def get_llm():
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "mock-key-for-testing":
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.3
        )
    return None

def extract_skills_node(state: InterviewState) -> InterviewState:
    logger.info(f"Executing extract_skills_node for session {state['session_id']}")
    llm = get_llm()
    if llm:
        try:
            prompt = RESUME_PARSER_PROMPT.format(
                target_role=state.get("target_role", "Software Engineer"),
                resume_text=state.get("resume_text", "")
            )
            res = llm.invoke(prompt)
            data = json.loads(res.content.strip("`json\n"))
            state["extracted_skills"] = data
        except Exception as e:
            logger.warning(f"LLM skill extraction failed, falling back to tool: {e}")
            state["extracted_skills"] = parse_resume_text.invoke(state.get("resume_text", ""))
    else:
        state["extracted_skills"] = parse_resume_text.invoke(state.get("resume_text", ""))
    
    state["status"] = "skills_extracted"
    return state

def generate_questions_node(state: InterviewState) -> InterviewState:
    logger.info(f"Executing generate_questions_node for session {state['session_id']}")
    llm = get_llm()
    skills = state.get("extracted_skills", {})
    difficulty = state.get("difficulty", "Intermediate")
    role = state.get("target_role", "Software Engineer")
    
    if llm:
        try:
            prompt = QUESTION_GENERATOR_PROMPT.format(
                question_count=5,
                target_role=role,
                difficulty=difficulty,
                skills=json.dumps(skills)
            )
            res = llm.invoke(prompt)
            raw = res.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].strip("json\n")
            questions = json.loads(raw)
            state["questions"] = questions
        except Exception as e:
            logger.warning(f"LLM question generation failed, fallback questions used: {e}")
            state["questions"] = get_fallback_questions(role, difficulty)
    else:
        state["questions"] = get_fallback_questions(role, difficulty)

    state["status"] = "questions_generated"
    return state

def get_fallback_questions(role: str, difficulty: str):
    return [
        {
            "question_id": 1,
            "category": "Behavioral",
            "question_text": "Describe a challenging technical problem you solved recently under tight deadlines.",
            "target_skill": "Problem Solving & Resilience",
            "difficulty": difficulty
        },
        {
            "question_id": 2,
            "category": "Technical",
            "question_text": f"How do you design a scalable microservices architecture for a high-throughput {role} system?",
            "target_skill": "System Architecture",
            "difficulty": difficulty
        },
        {
            "question_id": 3,
            "category": "Technical",
            "question_text": "Explain database indexing, ACID properties, and how you optimize slow SQL queries.",
            "target_skill": "Database Optimization",
            "difficulty": difficulty
        },
        {
            "question_id": 4,
            "category": "Behavioral",
            "question_text": "How do you handle technical disagreements with team members during code reviews?",
            "target_skill": "Communication & Teamwork",
            "difficulty": difficulty
        },
        {
            "question_id": 5,
            "category": "Technical",
            "question_text": "Describe your approach to containerizing applications and setting up CI/CD pipelines.",
            "target_skill": "DevOps & CI/CD",
            "difficulty": difficulty
        }
    ]

def evaluate_answer_node(state: InterviewState) -> InterviewState:
    logger.info(f"Executing evaluate_answer_node for session {state['session_id']}")
    evaluations = state.get("evaluations", [])
    candidate_answers = state.get("candidate_answers", [])
    
    if candidate_answers:
        latest_ans = candidate_answers[-1]
        llm = get_llm()
        if llm:
            try:
                prompt = EVALUATE_ANSWER_PROMPT.format(
                    question_text=latest_ans.get("question_text", ""),
                    target_skill=latest_ans.get("target_skill", "General"),
                    candidate_answer=latest_ans.get("candidate_answer", "")
                )
                res = llm.invoke(prompt)
                raw = res.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1].strip("json\n")
                eval_data = json.loads(raw)
                eval_data["question_id"] = latest_ans.get("question_id", len(evaluations) + 1)
                evaluations.append(eval_data)
            except Exception as e:
                logger.warning(f"LLM answer evaluation failed, using fallback scoring: {e}")
                evaluations.append(get_fallback_evaluation(latest_ans))
        else:
            evaluations.append(get_fallback_evaluation(latest_ans))
            
    state["evaluations"] = evaluations
    state["status"] = "answer_evaluated"
    return state

def get_fallback_evaluation(ans_dict: Dict[str, Any]) -> Dict[str, Any]:
    text_len = len(ans_dict.get("candidate_answer", ""))
    score = min(9.0, max(5.0, round(text_len / 20.0, 1)))
    return {
        "question_id": ans_dict.get("question_id", 1),
        "score": score,
        "technical_accuracy": score,
        "communication_score": min(10.0, score + 0.5),
        "strengths": ["Clear explanation", "Relevant technical concepts mentioned"],
        "weaknesses": ["Could include specific performance metrics", "Edge cases not fully detailed"],
        "improvement_feedback": "Solid response. Consider adding concrete system metrics and failure handling strategy.",
        "suggested_followup_question": "How would your solution scale if traffic increased 10x overnight?"
    }

def generate_report_node(state: InterviewState) -> InterviewState:
    logger.info(f"Executing generate_report_node for session {state['session_id']}")
    evaluations = state.get("evaluations", [])
    skills = state.get("extracted_skills", {})
    candidate_name = skills.get("candidate_name", "Candidate")
    
    llm = get_llm()
    if llm:
        try:
            prompt = FINAL_REPORT_PROMPT.format(
                candidate_name=candidate_name,
                target_role=state.get("target_role", "Software Engineer"),
                evaluations_json=json.dumps(evaluations)
            )
            res = llm.invoke(prompt)
            raw = res.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].strip("json\n")
            report = json.loads(raw)
            state["overall_summary"] = report
        except Exception as e:
            logger.warning(f"LLM report generation failed, using calculation tool: {e}")
            calc = calculate_interview_score.invoke({"evaluations": evaluations})
            state["overall_summary"] = {
                "average_score": calc["average_score"],
                "hiring_recommendation": calc["recommendation"],
                "overall_strengths": ["Good technical baseline", "Articulate communication"],
                "critical_weaknesses": ["Needs deeper dive into edge cases"],
                "summary_narrative": f"Candidate performed with an average score of {calc['average_score']}/10."
            }
    else:
        calc = calculate_interview_score.invoke({"evaluations": evaluations})
        state["overall_summary"] = {
            "average_score": calc["average_score"],
            "hiring_recommendation": calc["recommendation"],
            "overall_strengths": ["Good technical baseline", "Articulate communication"],
            "critical_weaknesses": ["Needs deeper dive into edge cases"],
            "summary_narrative": f"Candidate performed with an average score of {calc['average_score']}/10."
        }

    state["status"] = "report_generated"
    return state

def create_interview_graph():
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("extract_skills", extract_skills_node)
    workflow.add_node("generate_questions", generate_questions_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.set_entry_point("extract_skills")
    workflow.add_edge("extract_skills", "generate_questions")
    workflow.add_edge("generate_questions", END)
    
    return workflow.compile()

interview_graph = create_interview_graph()
