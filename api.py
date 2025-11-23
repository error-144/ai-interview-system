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
import struct

# Load environment variables from .env file
project_root = Path(__file__).parent
load_dotenv(dotenv_path=project_root / ".env")

from utils import (
    extract_resume_info_using_llm,
    get_ai_greeting_message,
    get_final_thanks_message,
    analyze_candidate_response_and_generate_new_question,
    get_feedback_of_candidate_response,
    get_overall_interview_feedback,
    get_overall_evaluation_score,
    save_interview_data,
    transcribe_with_deepgram,
    generate_speech_elevenlabs,
    map_voice_to_elevenlabs,
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

# OpenAI configuration (already initialized above)


# map_voice_to_openai removed - now using ElevenLabs via map_voice_to_elevenlabs in utils/text_to_speech.py


class ResumeUpload(BaseModel):
    job_description: str
    max_questions: int = 5
    ai_voice: str = "alloy"  # Default to OpenAI voice name


class StartInterviewRequest(BaseModel):
    session_id: str


class ProcessAnswerRequest(BaseModel):
    session_id: str
    transcript: str
    question_index: int


@app.get("/")
async def root():
    return {"message": "AI Interview System API"}


@app.post("/api/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = "",
    max_questions: int = 5,
    ai_voice: str = "alloy"
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
        # Store original voice name (will be mapped to ElevenLabs when used)
        interview_sessions[session_id] = {
            "name": name,
            "resume_highlights": resume_highlights,
            "job_description": job_description,
            "max_questions": max_questions,
            "ai_voice": ai_voice,  # Store original, map to ElevenLabs when generating speech
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
    """Start the interview session - OpenAI will handle the greeting"""
    print(f"[API] Starting interview for session {request.session_id}")
    try:
        session_id = request.session_id
        if session_id not in interview_sessions:
            print(f"[API] ERROR: Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = interview_sessions[session_id]
        session["interview_started"] = True
        session["qa_index"] = 1
        
        # Generate greeting message
        greeting_message = get_ai_greeting_message(session["name"], session["job_description"])
        session["messages"].append({
            "role": "assistant",
            "content": greeting_message,
            "timestamp": datetime.now().isoformat(),
        })
        
        print(f"[API] Interview started successfully for {session['name']}")
        return {
            "message": "Interview started. Connecting to OpenAI...",
            "question_index": session["qa_index"],
            "greeting": greeting_message,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ERROR in start_interview: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-answer")
async def process_answer(request: ProcessAnswerRequest):
    """Process candidate's answer and generate next question or feedback"""
    session_id = request.session_id
    transcript = request.transcript
    question_index = request.question_index
    
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
            
            # Generate overall interview feedback
            print(f"Generating overall interview feedback for session {session_id}")
            try:
                overall_feedback = await get_overall_interview_feedback(
                    session["name"],
                    session["conversations"],
                    session["job_description"],
                    session["resume_highlights"],
                    overall_score
                )
                print(f"Overall feedback generated successfully")
            except Exception as e:
                print(f"Error generating overall feedback: {e}")
                import traceback
                traceback.print_exc()
                # Provide fallback feedback if generation fails
                overall_feedback = {
                    "overall_feedback": f"Thank you for completing the interview. Your overall score is {round(overall_score, 2)}/10.",
                    "key_strengths": [],
                    "areas_for_improvement": [],
                    "recommendation": "We appreciate your time and will review your responses carefully."
                }
            
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
                "overall_feedback": overall_feedback,
            }
            save_interview_data(interview_data, candidate_name=session["name"])
            
            return {
                "feedback": feedback,
                "next_question": None,
                "thanks_message": thanks_message,
                "interview_completed": True,
                "overall_score": round(overall_score, 2),
                "conversations": session["conversations"],
                "overall_feedback": overall_feedback,
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


@app.post("/api/transcribe-audio")
async def transcribe_audio(
    file: UploadFile = File(...),
    session_id: str = "",
    question_index: int = 0
):
    """Transcribe audio file using Deepgram"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Transcribe using Deepgram
            transcript = transcribe_with_deepgram(tmp_file_path)
            return {"transcript": transcript}
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error transcribing audio: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")


@app.get("/api/openai-websocket-url/{session_id}")
async def get_openai_websocket_url(session_id: str):
    """Get OpenAI WebSocket URL for real-time transcription and TTS"""
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    # Return WebSocket URL for OpenAI-based real-time API
    import socket
    hostname = socket.gethostname()
    proxy_host = "localhost" if "localhost" in hostname.lower() else "0.0.0.0"
    ws_url = f"ws://{proxy_host}:8000/api/openai-realtime/{session_id}"
    
    return {
        "ws_url": ws_url
    }


@app.websocket("/api/openai-realtime/{session_id}")
async def websocket_openai_realtime(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time transcription and TTS.
    Uses Deepgram for STT and ElevenLabs for TTS.
    Receives audio chunks, transcribes them, processes responses, and streams audio back.
    """
    await websocket.accept()
    print(f"[Deepgram+ElevenLabs] Frontend connected for session {session_id}")
    
    if session_id not in interview_sessions:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    session = interview_sessions[session_id]
    audio_chunks = []
    last_transcription_time = asyncio.get_event_loop().time()
    transcription_interval = 1.0  # Fallback: transcribe every 1 second if no end_audio received
    websocket_connected = True  # Initialize before try block
    
    try:
        # Send greeting if available
        if session.get("messages") and len(session["messages"]) > 0:
            last_message = session["messages"][-1]
            if last_message.get("role") == "assistant":
                greeting_text = last_message.get("content", "")
                if greeting_text:
                    try:
                        print(f"[ElevenLabs] Sending greeting: {greeting_text[:100]}...")
                        await send_text_as_audio(websocket, greeting_text, session.get("ai_voice", "alloy"))
                        print(f"[ElevenLabs] Greeting audio sent successfully")
                    except Exception as e:
                        print(f"[OpenAI Realtime] Error sending greeting: {e}")
                        import traceback
                        traceback.print_exc()
                        # Don't disconnect on greeting error
        
        print("[Deepgram+ElevenLabs] Greeting sent, entering main message loop...")
        print("[Deepgram] Ready to receive audio chunks from frontend...")
        print("[Deepgram] Note: Audio chunks will only be sent when user speaks (above silence threshold)")
        while websocket_connected:
            try:
                # Receive message from frontend
                data = await websocket.receive()
                
                # Check if this is a disconnect message
                if data.get("type") == "websocket.disconnect":
                    print("[Deepgram+ElevenLabs] Frontend disconnected")
                    websocket_connected = False
                    break
                
                if "bytes" in data:
                    # Audio chunk received - just accumulate, don't process until end_audio
                    chunk_size = len(data["bytes"])
                    audio_chunks.append(data["bytes"])
                    
                    # Log first chunk to confirm audio is being received
                    if len(audio_chunks) == 1:
                        print(f"[Deepgram] First audio chunk received ({chunk_size} bytes), buffering...")
                    
                    # Log occasionally to show we're receiving audio
                    if len(audio_chunks) % 50 == 0:
                        total_size = sum(len(chunk) for chunk in audio_chunks)
                        print(f"[Deepgram] Buffering: {len(audio_chunks)} chunks ({total_size} bytes total)")
                    
                    # No timeout processing - only process on end_audio signal
                
                elif "text" in data:
                    # Text message received (e.g., control messages)
                    message = json.loads(data["text"])
                    msg_type = message.get("type")
                    
                    if msg_type == "end_audio":
                        # Process remaining audio chunks when user stops speaking
                        if audio_chunks:
                            total_audio_size = sum(len(chunk) for chunk in audio_chunks)
                            print(f"[Deepgram] end_audio received, processing {len(audio_chunks)} chunks ({total_audio_size} bytes)")
                            await process_audio_chunks(websocket, session_id, audio_chunks)
                            audio_chunks = []
                            # Reset transcription timer to prevent immediate re-processing
                            last_transcription_time = asyncio.get_event_loop().time()
                        else:
                            print("[Deepgram] end_audio received but no audio chunks to process")
                    elif msg_type == "ping":
                        try:
                            await websocket.send_text(json.dumps({"type": "pong"}))
                        except:
                            websocket_connected = False
                            break
                        
            except WebSocketDisconnect:
                print("[Deepgram+ElevenLabs] Frontend disconnected")
                websocket_connected = False
                break
            except RuntimeError as e:
                # Handle "Cannot call receive once a disconnect message has been received"
                error_msg = str(e).lower()
                if "disconnect" in error_msg or ("receive" in error_msg and "disconnect" in error_msg):
                    print("[Deepgram+ElevenLabs] WebSocket disconnected (RuntimeError)")
                    websocket_connected = False
                    break
                else:
                    # Other runtime errors - log and break
                    print(f"[OpenAI Realtime] Runtime error: {e}")
                    import traceback
                    traceback.print_exc()
                    websocket_connected = False
                    break
            except Exception as e:
                # Check if it's a disconnect-related error
                error_msg = str(e).lower()
                if "disconnect" in error_msg or "closed" in error_msg:
                    print("[OpenAI Realtime] WebSocket disconnected")
                    websocket_connected = False
                    break
                
                print(f"[Deepgram+ElevenLabs] Error processing message: {e}")
                import traceback
                traceback.print_exc()
                # Only send error if websocket is still connected
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                except:
                    # WebSocket already closed, exit loop
                    websocket_connected = False
                    break
                
    except Exception as e:
        print(f"[Deepgram+ElevenLabs] Error: {e}")
        import traceback
        traceback.print_exc()
        # Only close if not already closed and still connected
        if websocket_connected:
            try:
                await websocket.close(code=1011, reason=f"Error: {str(e)}")
            except:
                # Already closed, ignore
                pass


def calculate_audio_level(pcm_data, sample_width=2):
    """Calculate RMS (Root Mean Square) audio level to detect if there's actual speech"""
    import struct
    
    # Convert PCM16 bytes to integers
    samples = []
    for i in range(0, len(pcm_data) - sample_width + 1, sample_width):
        sample = struct.unpack('<h', pcm_data[i:i+sample_width])[0]
        # Normalize to -1.0 to 1.0
        normalized = sample / 32768.0
        samples.append(normalized)
    
    if not samples:
        return 0.0
    
    # Calculate RMS
    sum_squares = sum(s * s for s in samples)
    rms = (sum_squares / len(samples)) ** 0.5
    return rms


def create_wav_file(pcm_data, sample_rate=16000, channels=1, sample_width=2):
    """Convert raw PCM data to WAV format"""
    # WAV file header
    num_samples = len(pcm_data) // sample_width
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    data_size = num_samples * block_align
    file_size = 36 + data_size
    
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',           # ChunkID
        file_size,         # ChunkSize
        b'WAVE',           # Format
        b'fmt ',           # Subchunk1ID
        16,                # Subchunk1Size (PCM)
        1,                 # AudioFormat (PCM)
        channels,          # NumChannels
        sample_rate,       # SampleRate
        byte_rate,         # ByteRate
        block_align,       # BlockAlign
        sample_width * 8,  # BitsPerSample
        b'data',           # Subchunk2ID
        data_size          # Subchunk2Size
    )
    
    return wav_header + pcm_data


async def process_audio_chunks(websocket, session_id, audio_chunks):
    """Process accumulated audio chunks: transcribe, process, and respond"""
    try:
        # Combine audio chunks (raw PCM16 data)
        combined_audio = b"".join(audio_chunks)
        
        # Check if we have enough audio data (at least 0.5 seconds)
        min_audio_size = 16000 * 2 * 0.5  # 16kHz * 2 bytes * 0.5 seconds
        if len(combined_audio) < min_audio_size:
            print(f"[Deepgram] Audio too short: {len(combined_audio)} bytes, skipping")
            return
        
        # Check audio level to filter out background noise
        audio_level = calculate_audio_level(combined_audio)
        AUDIO_THRESHOLD = 0.01  # Minimum RMS level to consider as speech
        print(f"[Deepgram] Audio level (RMS): {audio_level:.4f}")
        
        if audio_level < AUDIO_THRESHOLD:
            print(f"[Deepgram] Audio level too low ({audio_level:.4f} < {AUDIO_THRESHOLD}), likely background noise - skipping")
            return
        
        print(f"[Deepgram] Converting {len(combined_audio)} bytes PCM to WAV format (level: {audio_level:.4f})")
        # Convert PCM to WAV format
        wav_data = create_wav_file(combined_audio, sample_rate=16000, channels=1, sample_width=2)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(wav_data)
            tmp_file_path = tmp_file.name
        
        try:
            print(f"[Deepgram] Transcribing audio file: {tmp_file_path}")
            # Transcribe audio using Deepgram
            transcript = transcribe_with_deepgram(tmp_file_path)
            
            # Check for transcription failures - don't process these as answers
            if not transcript:
                print(f"[Deepgram] Empty transcript, skipping processing")
                return
            
            if transcript.startswith("Transcription failed") or transcript == "No speech detected in audio":
                print(f"[Deepgram] Transcription failed or no speech detected: {transcript}")
                print(f"[Deepgram] Skipping processing to avoid treating error as answer")
                return
            
            print(f"[Deepgram] Transcript: {transcript}")
            
            # Send transcript to frontend
            try:
                await websocket.send_text(json.dumps({
                    "type": "transcript",
                    "role": "user",
                    "content": transcript
                }))
            except:
                # WebSocket closed, return early
                return
            
            # Process answer and generate response using OpenAI LLM
            if session_id in interview_sessions:
                print(f"[OpenAI LLM] Processing transcript and generating response...")
                session = interview_sessions[session_id]
                
                # Add user message
                session["messages"].append({
                    "role": "user",
                    "content": transcript,
                    "timestamp": datetime.now().isoformat(),
                })
                
                # Get current question
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
                    # Generate feedback
                    feedback = await get_feedback_of_candidate_response(
                        current_question,
                        transcript,
                        session["job_description"],
                        session["resume_highlights"],
                    )
                    
                    session["conversations"].append({
                        "Question": current_question,
                        "Candidate Answer": transcript,
                        "Evaluation": float(feedback["score"]),
                        "Feedback": feedback["feedback"],
                    })
                    
                    session["interview_completed"] = True
                    session["qa_index"] += 1
                    
                    # Calculate overall score
                    overall_score = get_overall_evaluation_score(session["conversations"])
                    
                    # Generate overall interview feedback
                    print(f"[OpenAI LLM] Generating overall interview feedback...")
                    try:
                        overall_feedback = await get_overall_interview_feedback(
                            session["name"],
                            session["conversations"],
                            session["job_description"],
                            session["resume_highlights"],
                            overall_score
                        )
                        print(f"[OpenAI LLM] Overall feedback generated successfully")
                    except Exception as e:
                        print(f"[OpenAI LLM] Error generating overall feedback: {e}")
                        import traceback
                        traceback.print_exc()
                        # Provide fallback feedback if generation fails
                        overall_feedback = {
                            "overall_feedback": f"Thank you for completing the interview. Your overall score is {round(overall_score, 2)}/10.",
                            "key_strengths": [],
                            "areas_for_improvement": [],
                            "recommendation": "We appreciate your time and will review your responses carefully."
                        }
                    
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
                        "overall_feedback": overall_feedback,
                    }
                    save_interview_data(interview_data, candidate_name=session["name"])
                    
                    # Generate thanks message
                    thanks_message = get_final_thanks_message(session["name"])
                    session["messages"].append({
                        "role": "assistant",
                        "content": thanks_message,
                        "timestamp": datetime.now().isoformat(),
                    })
                    
                    # Send thanks message as audio
                    print(f"[OpenAI Realtime] Generating audio for thanks message")
                    await send_text_as_audio(websocket, thanks_message, session.get("ai_voice", "alloy"))
                    print(f"[ElevenLabs] Thanks audio sent successfully")
                    
                    # Send completion message with overall feedback
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "interview_completed",
                            "message": thanks_message,
                            "overall_score": round(overall_score, 2),
                            "overall_feedback": overall_feedback
                        }))
                    except:
                        # WebSocket closed, ignore
                        pass
                else:
                    # Generate next question using OpenAI LLM
                    print(f"[OpenAI LLM] Analyzing candidate response and generating next question...")
                    print(f"[OpenAI LLM] Current question: {current_question[:100]}...")
                    print(f"[OpenAI LLM] Candidate response: {transcript[:100]}...")
                    next_question, feedback = await analyze_candidate_response_and_generate_new_question(
                        current_question,
                        transcript,
                        session["job_description"],
                        session["resume_highlights"],
                    )
                    print(f"[OpenAI LLM] Generated next question: {next_question[:100]}...")
                    print(f"[OpenAI LLM] Feedback score: {feedback.get('score', 'N/A')}")
                    
                    session["conversations"].append({
                        "Question": current_question,
                        "Candidate Answer": transcript,
                        "Evaluation": float(feedback["score"]),
                        "Feedback": feedback["feedback"],
                    })
                    
                    session["messages"].append({
                        "role": "assistant",
                        "content": next_question,
                        "timestamp": datetime.now().isoformat(),
                    })
                    
                    session["qa_index"] += 1
                    
                    # Send next question as audio
                    print(f"[ElevenLabs] Generating audio for next question: {next_question[:50]}...")
                    await send_text_as_audio(websocket, next_question, session.get("ai_voice", "alloy"))
                    print(f"[ElevenLabs] Audio sent successfully")
                    
                    # Send next question message
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "next_question",
                            "role": "assistant",
                            "content": next_question,
                            "question_index": session["qa_index"]
                        }))
                    except:
                        # WebSocket closed, ignore
                        pass
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        print(f"[OpenAI Realtime] Error processing audio chunks: {e}")
        import traceback
        traceback.print_exc()
        # Send error to frontend but don't disconnect
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error processing audio: {str(e)}"
            }))
        except:
            # WebSocket closed, ignore
            pass


async def send_text_as_audio(websocket, text, voice="alloy"):
    """Generate speech from text and send as audio chunks using ElevenLabs"""
    try:
        # Map voice name to ElevenLabs voice ID
        voice_id = map_voice_to_elevenlabs(voice)
        
        # Generate speech file using ElevenLabs
        audio_file_path = generate_speech_elevenlabs(text, voice_id=voice_id)
        
        # Check if websocket is still connected before sending
        try:
            # Send audio format info first
            await websocket.send_text(json.dumps({
                "type": "audio_start",
                "format": "mp3"
            }))
            
            # Read and send audio in chunks
            chunk_size = 8192  # Larger chunks for MP3
            with open(audio_file_path, "rb") as audio_file:
                while True:
                    chunk = audio_file.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        await websocket.send_bytes(chunk)
                    except:
                        # WebSocket closed, stop sending
                        break
            
            # Send audio end marker (only if still connected)
            try:
                await websocket.send_text(json.dumps({
                    "type": "audio_end"
                }))
            except:
                # WebSocket closed, ignore
                pass
        except:
            # WebSocket closed, just clean up
            pass
        
        # Clean up temp file
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
            
    except Exception as e:
        print(f"[ElevenLabs] Error generating/sending audio: {e}")
        import traceback
        traceback.print_exc()
        # Send error to frontend but don't disconnect
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error generating audio: {str(e)}"
            }))
        except:
            # WebSocket closed, ignore
            pass
        # Don't raise - let the caller handle WebSocket state


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
