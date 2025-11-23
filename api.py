from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import tempfile
import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
import websockets
import asyncio

# Load environment variables from .env file
project_root = Path(__file__).parent
load_dotenv(dotenv_path=project_root / ".env")

from utils import (
    extract_resume_info_using_llm,
    get_ai_greeting_message,
    get_final_thanks_message,
    analyze_candidate_response_and_generate_new_question,
    get_feedback_of_candidate_response,
    get_overall_evaluation_score,
    save_interview_data,
)

app = FastAPI(title="AI Interview System API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for interview sessions (in production, use a database)
interview_sessions = {}

# OpenAI client for LLM calls
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Speechmatics API configuration
SPEECHMATICS_API_KEY = os.environ.get("SPEECHMATICS_API_KEY")
# Agent ID from Speechmatics Portal (found in agent settings)
# Format: wss://eu2.rt.speechmatics.com/v1/agent/{AGENT_ID}/ws
SPEECHMATICS_AGENT_ID = os.environ.get("SPEECHMATICS_AGENT_ID", "5a14d0ec-bec2-41a7-8307-34cb13d452f8")
# Region: eu2 (EU region 2) - adjust if your agent is in a different region
SPEECHMATICS_REGION = os.environ.get("SPEECHMATICS_REGION", "eu2")


class ResumeUpload(BaseModel):
    job_description: str
    max_questions: int = 5
    ai_voice: str = "Alex (Male)"


class StartInterviewRequest(BaseModel):
    session_id: str


@app.get("/")
async def root():
    return {"message": "AI Interview System API"}


@app.post("/api/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = "",
    max_questions: int = 5,
    ai_voice: str = "Alex (Male)"
):
    """Upload resume and extract information"""
    print(f"[API] Upload resume request received: {file.filename}")
    tmp_file_path = None
    try:
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Extract resume content
        from PyPDF2 import PdfReader
        import io
        
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            resume_content = ""
            for page in pdf_reader.pages:
                resume_content += page.extract_text()
            
            if not resume_content or len(resume_content.strip()) == 0:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF. Please ensure the PDF contains readable text.")
        except Exception as pdf_error:
            raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(pdf_error)}")
        
        # Extract resume info using LLM
        print(f"[API] Extracting resume info using LLM (content length: {len(resume_content)})")
        print(f"[API] Resume content preview: {resume_content[:200]}...")
        try:
            name, resume_highlights = extract_resume_info_using_llm(resume_content)
            print(f"[API] Resume extracted - Name: {name}, Highlights length: {len(resume_highlights)}")
            
            # Validate extracted data
            if not name or not name.strip():
                raise HTTPException(status_code=500, detail="Could not extract candidate name from resume. Please ensure your resume contains a name field.")
            if not resume_highlights or not resume_highlights.strip():
                raise HTTPException(status_code=500, detail="Could not extract resume highlights. Please ensure your resume contains work experience or skills.")
        except HTTPException:
            raise
        except ValueError as ve:
            print(f"[API] Validation error in resume extraction: {ve}")
            raise HTTPException(status_code=500, detail=f"Resume extraction failed: {str(ve)}")
        except Exception as llm_error:
            print(f"[API] LLM extraction error: {llm_error}")
            import traceback
            traceback.print_exc()
            error_msg = str(llm_error)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise HTTPException(status_code=500, detail="OpenAI API key not configured or invalid. Please check your .env file.")
            raise HTTPException(status_code=500, detail=f"Error extracting resume information: {error_msg}")
        
        # Create session
        session_id = f"session_{datetime.now().timestamp()}"
        interview_sessions[session_id] = {
            "name": name,
            "resume_highlights": resume_highlights,
            "job_description": job_description,
            "max_questions": max_questions,
            "ai_voice": ai_voice,
            "qa_index": 0,
            "conversations": [],
            "messages": [],
            "interview_started": False,
            "interview_completed": False,
        }
        
        print(f"[API] Session created: {session_id} for {name}")
        return {
            "session_id": session_id,
            "name": name,
            "resume_highlights": resume_highlights,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload resume error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")
    finally:
        # Clean up temp file
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass


@app.post("/api/start-interview")
async def start_interview(request: StartInterviewRequest):
    """Start the interview session - Speechmatics Flow API will handle the greeting"""
    print(f"[API] Starting interview for session {request.session_id}")
    try:
        session_id = request.session_id
        if session_id not in interview_sessions:
            print(f"[API] ERROR: Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = interview_sessions[session_id]
        session["interview_started"] = True
        session["qa_index"] = 1
        
        # No OpenAI greeting - Speechmatics Flow API agent will handle the conversation start
        print(f"[API] Interview started successfully for {session['name']} - Speechmatics agent will initiate conversation")
        return {
            "message": "Interview started. Connecting to Speechmatics agent...",
            "question_index": session["qa_index"],
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ERROR in start_interview: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-answer")
async def process_answer(
    session_id: str,
    transcript: str,
    question_index: int
):
    """Process candidate's answer and generate next question or feedback"""
    print(f"[API] Processing answer for session {session_id}, question {question_index}")
    print(f"[API] Transcript length: {len(transcript)}")
    try:
        if session_id not in interview_sessions:
            print(f"[API] ERROR: Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = interview_sessions[session_id]
        print(f"[API] Session found: {session['name']}")
        
        if session["interview_completed"]:
            print(f"[API] ERROR: Interview already completed")
            raise HTTPException(status_code=400, detail="Interview already completed")
        
        # Add candidate's answer to messages
        session["messages"].append({
            "role": "user",
            "content": transcript,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Get current question (last assistant message)
        current_question = None
        for msg in reversed(session["messages"]):
            if msg["role"] == "assistant":
                current_question = msg["content"]
                break
        
        if not current_question:
            current_question = "Tell me about yourself and your experience."
        
        # Check if this is the last question
        is_last_question = session["qa_index"] >= session["max_questions"]
        
        if is_last_question:
            # Generate only feedback
            print(f"Generating final feedback for session {session_id}")
            feedback = await get_feedback_of_candidate_response(
                current_question,
                transcript,
                session["job_description"],
                session["resume_highlights"],
            )
            print(f"Feedback generated: {feedback}")
            
            # Store conversation
            session["conversations"].append({
                "Question": current_question,
                "Candidate Answer": transcript,
                "Evaluation": float(feedback["score"]),
                "Feedback": feedback["feedback"],
            })
            
            # Mark interview as completed
            session["interview_completed"] = True
            session["qa_index"] += 1
            
            # Generate thanks message
            thanks_message = get_final_thanks_message(session["name"])
            session["messages"].append({
                "role": "assistant",
                "content": thanks_message,
                "timestamp": datetime.now().isoformat(),
            })
            
            # Calculate overall score
            overall_score = get_overall_evaluation_score(session["conversations"])
            
            # Save interview data
            now = datetime.now().isoformat() + "Z"
            interview_data = {
                "name": session["name"],
                "createdAt": now,
                "updatedAt": now,
                "id": 1,
                "job_description": session["job_description"],
                "resume_highlights": session["resume_highlights"],
                "conversations": session["conversations"],
                "overall_score": round(overall_score, 2),
            }
            save_interview_data(interview_data, candidate_name=session["name"])
            
            return {
                "feedback": feedback,
                "next_question": None,
                "thanks_message": thanks_message,
                "interview_completed": True,
                "overall_score": overall_score,
                "conversations": session["conversations"],
            }
        else:
            # Generate next question and feedback
            print(f"Generating next question and feedback for session {session_id}")
            next_question, feedback = await analyze_candidate_response_and_generate_new_question(
                current_question,
                transcript,
                session["job_description"],
                session["resume_highlights"],
            )
            print(f"Next question generated: {next_question[:50]}...")
            
            # Store conversation
            session["conversations"].append({
                "Question": current_question,
                "Candidate Answer": transcript,
                "Evaluation": float(feedback["score"]),
                "Feedback": feedback["feedback"],
            })
            
            # Add next question to messages
            session["messages"].append({
                "role": "assistant",
                "content": next_question,
                "timestamp": datetime.now().isoformat(),
            })
            
            session["qa_index"] += 1
            
            print(f"[API] Successfully generated response for session {session_id}")
            return {
                "feedback": feedback,
                "next_question": next_question,
                "question_index": session["qa_index"],
                "interview_completed": False,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ERROR in process_answer: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")


@app.get("/api/interview-status/{session_id}")
async def get_interview_status(session_id: str):
    """Get current interview status"""
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = interview_sessions[session_id]
    return {
        "session_id": session_id,
        "name": session["name"],
        "qa_index": session["qa_index"],
        "max_questions": session["max_questions"],
        "interview_started": session["interview_started"],
        "interview_completed": session["interview_completed"],
        "messages": session["messages"],
        "conversations": session["conversations"],
    }


@app.get("/api/interview-results/{session_id}")
async def get_interview_results(session_id: str):
    """Get final interview results"""
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = interview_sessions[session_id]
    
    if not session["interview_completed"]:
        raise HTTPException(status_code=400, detail="Interview not completed yet")
    
    overall_score = get_overall_evaluation_score(session["conversations"])
    
    return {
        "name": session["name"],
        "overall_score": overall_score,
        "conversations": session["conversations"],
        "messages": session["messages"],
    }


@app.get("/api/speechmatics-credentials/{session_id}")
async def get_speechmatics_credentials(session_id: str):
    """Get Speechmatics API credentials for direct frontend connection"""
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not SPEECHMATICS_API_KEY:
        raise HTTPException(status_code=500, detail="Speechmatics API key not configured")
    
    if not SPEECHMATICS_AGENT_ID:
        raise HTTPException(status_code=500, detail="Speechmatics Agent ID not configured")
    
    # Return proxy WebSocket URL (backend handles authentication)
    # Frontend connects to backend proxy, which forwards to Speechmatics Flow API with auth headers
    # Use ws:// for localhost, wss:// for production
    import socket
    hostname = socket.gethostname()
    # For local development, use localhost; for production, use actual hostname
    proxy_host = "localhost" if "localhost" in hostname.lower() else "0.0.0.0"
    proxy_ws_url = f"ws://{proxy_host}:8000/api/speechmatics-proxy/{session_id}"
    
    # Use template_id if available (includes :latest), otherwise use agent_id
    template_id = os.environ.get("SPEECHMATICS_TEMPLATE_ID", SPEECHMATICS_AGENT_ID)
    if template_id and ":" not in template_id:
        template_id = f"{template_id}:latest"
    
    return {
        "api_key": SPEECHMATICS_API_KEY,  # Keep for reference, but proxy uses it
        "agent_id": SPEECHMATICS_AGENT_ID,
        "template_id": template_id,  # Include template_id for frontend
        "region": SPEECHMATICS_REGION,  # Keep for reference
        "ws_url": proxy_ws_url
    }


@app.websocket("/api/speechmatics-proxy/{session_id}")
async def websocket_speechmatics_proxy(websocket: WebSocket, session_id: str):
    """
    WebSocket proxy that adds Authorization header for Speechmatics Flow API.
    Browser WebSocket API doesn't support custom headers, so we proxy through backend.
    """
    await websocket.accept()
    print(f"[Proxy] Frontend connected for session {session_id}")
    
    if session_id not in interview_sessions:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    if not SPEECHMATICS_API_KEY or not SPEECHMATICS_AGENT_ID:
        await websocket.close(code=1011, reason="Speechmatics credentials not configured")
        return
    
    # Construct Speechmatics Flow API WebSocket URL
    # Flow API endpoint: wss://flow.api.speechmatics.com/
    speechmatics_url = "wss://flow.api.speechmatics.com/"
    
    try:
        # Connect to Speechmatics with Authorization header
        async with websockets.connect(
            speechmatics_url,
            additional_headers=[("Authorization", f"Bearer {SPEECHMATICS_API_KEY}")]
        ) as speechmatics_ws:
            print(f"[Proxy] Connected to Speechmatics Flow API: {speechmatics_url}")
            
            # Forward messages bidirectionally
            async def forward_to_speechmatics():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            await speechmatics_ws.send(data["bytes"])
                        elif "text" in data:
                            await speechmatics_ws.send(data["text"])
                except WebSocketDisconnect:
                    print("[Proxy] Frontend disconnected")
                except Exception as e:
                    print(f"[Proxy] Error forwarding to Speechmatics: {e}")
            
            async def forward_to_frontend():
                try:
                    while True:
                        message = await speechmatics_ws.recv()
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception as e:
                    print(f"[Proxy] Error forwarding to frontend: {e}")
            
            # Run both forwarding tasks concurrently
            await asyncio.gather(
                forward_to_speechmatics(),
                forward_to_frontend(),
                return_exceptions=True
            )
            
    except Exception as e:
        print(f"[Proxy] Error connecting to Speechmatics: {e}")
        import traceback
        traceback.print_exc()
        await websocket.close(code=1011, reason=f"Failed to connect to Speechmatics: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
