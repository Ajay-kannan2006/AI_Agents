RESUME_PARSER_PROMPT = """You are an expert AI Technical Recruiter.
Extract skills and candidate metadata from the following resume text.

Target Role: {target_role}

Resume Text:
{resume_text}

Return JSON with keys:
- candidate_name: string
- experience_years: number
- primary_skills: list of strings
- secondary_skills: list of strings
- roles_suited: list of strings
"""

QUESTION_GENERATOR_PROMPT = """You are a Principal Software Engineering Hiring Manager.
Based on candidate skills and experience level, generate {question_count} targeted technical and behavioral interview questions.

Target Role: {target_role}
Difficulty Level: {difficulty}
Extracted Skills: {skills}

Generate a JSON array of objects, each containing:
- question_id: integer (1 to {question_count})
- category: "Technical" or "Behavioral"
- question_text: detailed interview question
- target_skill: skill evaluated by this question
- difficulty: {difficulty}
"""

EVALUATE_ANSWER_PROMPT = """You are a Senior Technical Interviewer evaluating a candidate's answer.

Question: {question_text}
Target Skill: {target_skill}
Candidate Answer: {candidate_answer}

Evaluate the response rigorously.
Return JSON with:
- score: float (0.0 to 10.0 overall grade)
- technical_accuracy: float (0.0 to 10.0)
- communication_score: float (0.0 to 10.0)
- strengths: list of strings (key strengths displayed)
- weaknesses: list of strings (areas missing or inadequate)
- improvement_feedback: constructive coaching text
- suggested_followup_question: optional followup string if answer lacked depth
"""

FINAL_REPORT_PROMPT = """You are a VP of Engineering reviewing interview results.
Synthesize the evaluations into a final hiring report.

Candidate Name: {candidate_name}
Target Role: {target_role}
Evaluations: {evaluations_json}

Return JSON with:
- average_score: float
- overall_strengths: list of strings
- critical_weaknesses: list of strings
- hiring_recommendation: "Strong Hire", "Hire", "Weak Hire", or "Do Not Hire"
- summary_narrative: text breakdown of performance
"""
