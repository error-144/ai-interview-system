from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Find the project root (parent of utils directory)
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
# Default max tokens: 200 for questions, 300 for feedback
MAX_TOKENS_QUESTION = int(os.environ.get("MAX_TOKENS_QUESTION", "200"))
MAX_TOKENS_FEEDBACK = int(os.environ.get("MAX_TOKENS_FEEDBACK", "300"))
MAX_TOKENS_DEFAULT = int(os.environ.get("MAX_TOKENS_DEFAULT", "250"))

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def get_response_from_llm(prompt, max_tokens=None):
    """
    Calls the LLM and returns the response.

    Args:
        prompt (str): The string to prompt the LLM with.
        max_tokens (int, optional): Maximum tokens in response. Defaults to MAX_TOKENS_DEFAULT.

    Returns:
        str: The response from the LLM.
    
    Raises:
        Exception: If API call fails or response is invalid
    """
    if max_tokens is None:
        max_tokens = MAX_TOKENS_DEFAULT
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,  # Limit output tokens to save costs
            temperature=0.7,  # Slightly lower for more focused responses
            response_format={"type": "json_object"},  # Force JSON response
        )
        
        if not response or not response.choices or len(response.choices) == 0:
            raise Exception("Empty response from OpenAI API")
        
        content = response.choices[0].message.content
        if not content:
            raise Exception("No content in OpenAI API response")
        
        return content
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise Exception("OpenAI API key not configured or invalid. Please check your .env file.")
        raise Exception(f"OpenAI API error: {error_msg}")


def parse_json_response(response):
    """
    Parse the JSON response from LLM, handling markdown code blocks.
    
    Args:
        response (str): Raw response string from LLM
        
    Returns:
        dict: Parsed JSON object, or None if parsing fails
    """
    if not response:
        return None
    
    try:
        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # Remove ```json
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]  # Remove ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # Remove trailing ```
        
        cleaned = cleaned.strip()
        
        # Try to parse JSON
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON parse error: {e}")
        print(f"[LLM] Response was: {response[:500]}...")
        return None
