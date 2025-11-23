import asyncio
from typing import Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from utils.llm_call import get_response_from_llm, parse_json_response, MAX_TOKENS_QUESTION, MAX_TOKENS_FEEDBACK
from utils.prompts import next_question_generation, feedback_generation, overall_feedback_generation

# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=4)

class InterviewAnalysisError(Exception):
    """Custom exception for interview analysis errors"""
    pass

@lru_cache(maxsize=128)
def _cache_key(prompt: str) -> str:
    """Generate cache key for prompt (if you want to implement caching)"""
    return hash(prompt)

async def _make_llm_call_async(prompt: str, max_tokens: int = None) -> Dict[str, Any]:
    """
    Make LLM call asynchronously by running in thread pool
    
    Args:
        prompt: The prompt to send to LLM
        max_tokens: Maximum tokens for response (None uses default)
    """
    try:
        loop = asyncio.get_event_loop()
        # Run the synchronous LLM call in a thread pool with token limit
        response = await loop.run_in_executor(executor, get_response_from_llm, prompt, max_tokens)
        return parse_json_response(response)
    except Exception as e:
        raise InterviewAnalysisError(f"Failed to get LLM response: {str(e)}")

async def get_next_question(
    previous_question: str, 
    candidate_response: str, 
    resume_highlights: str, 
    job_description: str
) -> str:
    """
    Generate next interview question based on previous interaction
    
    Args:
        previous_question: The previous question asked
        candidate_response: Candidate's response to previous question
        resume_highlights: Key highlights from candidate's resume
        job_description: Job description/requirements
        
    Returns:
        str: Next question to ask
        
    Raises:
        InterviewAnalysisError: If question generation fails
    """
    try:
        final_prompt = next_question_generation.format(
            previous_question=previous_question,
            candidate_response=candidate_response,
            resume_highlights=resume_highlights,
            job_description=job_description,
        )
        
        # Use lower token limit for questions (they should be short)
        response = await _make_llm_call_async(final_prompt, max_tokens=MAX_TOKENS_QUESTION)
        
        if "next_question" not in response:
            raise InterviewAnalysisError("Missing 'next_question' in LLM response")
            
        return response["next_question"]
        
    except Exception as e:
        raise InterviewAnalysisError(f"Question generation failed: {str(e)}")

async def get_feedback_of_candidate_response(
    question: str, 
    candidate_response: str, 
    job_description: str, 
    resume_highlights: str
) -> Dict[str, Any]:
    """
    Generate feedback for candidate's response
    
    Args:
        question: The question that was asked
        candidate_response: Candidate's response
        job_description: Job description/requirements
        resume_highlights: Key highlights from candidate's resume
        
    Returns:
        Dict containing feedback and score
        
    Raises:
        InterviewAnalysisError: If feedback generation fails
    """
    try:
        final_prompt = feedback_generation.format(
            question=question,
            candidate_response=candidate_response,
            job_description=job_description,
            resume_highlights=resume_highlights,
        )
        
        # Use moderate token limit for feedback
        response = await _make_llm_call_async(final_prompt, max_tokens=MAX_TOKENS_FEEDBACK)
        
        # Validate response structure
        required_fields = ["feedback", "score"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            raise InterviewAnalysisError(f"Missing fields in response: {missing_fields}")
        
        # Validate score is numeric
        try:
            score = float(response["score"])
            if not (0 <= score <= 10):  # assuming score is 0-10
                print(f"Score {score} is outside expected range 0-10")
        except (ValueError, TypeError):
            raise InterviewAnalysisError(f"Invalid score format: {response['score']}")
        
        return {
            "feedback": response["feedback"],
            "score": response["score"]
        }
        
    except Exception as e:
        raise InterviewAnalysisError(f"Feedback generation failed: {str(e)}")

async def analyze_candidate_response_and_generate_new_question(
    question: str, 
    candidate_response: str, 
    job_description: str, 
    resume_highlights: str,
    timeout: float = 30.0
) -> Tuple[str, Dict[str, Any]]:
    """
    Analyze candidate response and generate next question concurrently
    
    Args:
        question: The question that was asked
        candidate_response: Candidate's response
        job_description: Job description/requirements
        resume_highlights: Key highlights from candidate's resume
        timeout: Maximum time to wait for both operations
        
    Returns:
        Tuple of (next_question, feedback_dict)
        
    Raises:
        InterviewAnalysisError: If analysis fails
        asyncio.TimeoutError: If operations exceed timeout
    """
    try:
        # Run both operations concurrently for better performance
        feedback_task = get_feedback_of_candidate_response(
            question, candidate_response, job_description, resume_highlights
        )
        
        next_question_task = get_next_question(
            question, candidate_response, resume_highlights, job_description
        )
        
        # Wait for both with timeout
        feedback, next_question = await asyncio.wait_for(
            asyncio.gather(feedback_task, next_question_task),
            timeout=timeout
        )
        return next_question, feedback
    except asyncio.TimeoutError:
        raise
    except Exception as e:
        raise InterviewAnalysisError(f"Response analysis failed: {str(e)}")

async def get_overall_interview_feedback(
    candidate_name: str,
    conversations: list,
    job_description: str,
    resume_highlights: str,
    overall_score: float
) -> Dict[str, Any]:
    """
    Generate overall feedback for the entire interview
    
    Args:
        candidate_name: Name of the candidate
        conversations: List of all interview conversations with Q&A and feedback
        job_description: Job description/requirements
        resume_highlights: Key highlights from candidate's resume
        overall_score: Overall evaluation score (0-10)
        
    Returns:
        Dict containing overall feedback, strengths, areas for improvement, and recommendation
        
    Raises:
        InterviewAnalysisError: If feedback generation fails
    """
    try:
        # Format conversations summary
        conversations_summary = ""
        for i, conv in enumerate(conversations, 1):
            conversations_summary += f"\nQuestion {i}: {conv.get('Question', 'N/A')}\n"
            conversations_summary += f"Candidate Answer: {conv.get('Candidate Answer', 'N/A')}\n"
            conversations_summary += f"Score: {conv.get('Evaluation', 0)}/10\n"
            conversations_summary += f"Feedback: {conv.get('Feedback', 'N/A')}\n"
            conversations_summary += "---\n"
        
        final_prompt = overall_feedback_generation.format(
            candidate_name=candidate_name,
            job_description=job_description,
            resume_highlights=resume_highlights,
            total_questions=len(conversations),
            overall_score=round(overall_score, 2),
            conversations_summary=conversations_summary
        )
        
        # Use higher token limit for overall feedback (it's more comprehensive)
        response = await _make_llm_call_async(final_prompt, max_tokens=800)
        
        # Validate response structure
        required_fields = ["overall_feedback", "key_strengths", "areas_for_improvement", "recommendation"]
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            raise InterviewAnalysisError(f"Missing fields in response: {missing_fields}")
        
        return {
            "overall_feedback": response["overall_feedback"],
            "key_strengths": response.get("key_strengths", []),
            "areas_for_improvement": response.get("areas_for_improvement", []),
            "recommendation": response.get("recommendation", "")
        }
        
    except Exception as e:
        raise InterviewAnalysisError(f"Overall feedback generation failed: {str(e)}")