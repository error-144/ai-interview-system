import random
from utils.llm_call import get_response_from_llm, parse_json_response, MAX_TOKENS_DEFAULT
from utils.prompts import basic_details


def extract_resume_info_using_llm(resume_content):
    """
    Extract candidate name and highlights from resume using LLM
    
    Returns:
        tuple: (name, resume_highlights)
    
    Raises:
        ValueError: If extraction fails or response is invalid
    """
    if not resume_content or len(resume_content.strip()) == 0:
        raise ValueError("Resume content is empty")
    
    # Truncate resume content to save input tokens (keep first 2000 chars)
    truncated_content = resume_content[:2000] if len(resume_content) > 2000 else resume_content
    
    try:
        final_prompt = basic_details.format(resume_content=truncated_content)
        print(f"[Resume Extraction] Calling LLM with prompt length: {len(final_prompt)}")
        
        # Use token limit for extraction (should be concise JSON)
        raw_response = get_response_from_llm(final_prompt, max_tokens=MAX_TOKENS_DEFAULT)
        
        if not raw_response:
            raise ValueError("Empty response from LLM")
        
        print(f"[Resume Extraction] Raw LLM response: {raw_response[:200]}...")
        
        response = parse_json_response(raw_response)
        
        if not response:
            raise ValueError(f"Failed to parse JSON response from LLM. Raw response: {raw_response[:500]}")
        
        print(f"[Resume Extraction] Parsed JSON keys: {list(response.keys())}")
        
        if "name" not in response:
            raise ValueError(f"Missing 'name' field in LLM response. Available fields: {list(response.keys())}")
        if "resume_highlights" not in response:
            raise ValueError(f"Missing 'resume_highlights' field in LLM response. Available fields: {list(response.keys())}")
        
        # Handle cases where LLM returns list instead of string
        def normalize_field(value):
            """Convert field to string, handling lists and other types"""
            if isinstance(value, list):
                # Join list items with spaces or newlines
                return " ".join(str(item) for item in value).strip()
            elif isinstance(value, str):
                return value.strip()
            else:
                # Convert other types to string
                return str(value).strip()
        
        name = normalize_field(response["name"])
        resume_highlights = normalize_field(response["resume_highlights"])
        
        if not name:
            raise ValueError("Extracted name is empty")
        if not resume_highlights:
            raise ValueError("Extracted resume highlights are empty")
        
        return name, resume_highlights
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error extracting resume info: {str(e)}")


ai_greeting_messages = [
    lambda name, interviewer_name: f"Hi {name}, welcome to this AI interview! My name is {interviewer_name} and I'll be your interviewer today. Let's get started!\n\nCan you tell me a bit about yourself and what you're looking for in a job?",
    lambda name, interviewer_name: f"Hi {name}, welcome to this AI interview! My name is {interviewer_name} and I'll be your interviewer today. Let's get started!\n\nCan you give me a quick overview of your background and experience?",
    lambda name, interviewer_name: f"Hi {name}, welcome to this AI interview! My name is {interviewer_name} and I'll be your interviewer today. Let's get started!\n\nCan you tell me a little bit about your goals and aspirations?",
    lambda name, interviewer_name: f"Hi {name}, welcome to this AI interview! My name is {interviewer_name} and I'll be your interviewer today. Let's get started!\n\nCan you briefly introduce yourself and tell me about your achievements and skills?",
]


final_thanks_for_taking_interview_msgs = [
    lambda name: f"Thanks for taking the time to chat today, {name}. I really enjoyed our conversation. Wishing you all the best in your career!",
    lambda name: f"It was great speaking with you, {name}. I hope the interview was a valuable experience for you. Good luck moving forward!",
    lambda name: f"Appreciate your time today, {name}. Best of luck with the rest of your job applications and interviews!",
    lambda name: f"Thank you for the engaging conversation, {name}. I wish you success in your job hunt and future endeavors!",
    lambda name: f"It was a pleasure talking to you, {name}. I hope the interview helped clarify your goals. All the best!",
    lambda name: f"Thanks again for your time, {name}. I hope you found the interview insightful. Good luck on your journey ahead!",
]


def get_ai_greeting_message(name, interviewer_name="Alex"):
    return random.choice(ai_greeting_messages)(name, interviewer_name)


def get_final_thanks_message(name):
    return random.choice(final_thanks_for_taking_interview_msgs)(name)
