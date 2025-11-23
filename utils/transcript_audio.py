import os
from deepgram import DeepgramClient


def transcribe_with_deepgram(audio_path, transcription_language="en"):
    """Transcribe audio using Deepgram API (batch transcription) - SDK v5.x"""
    # Temporarily use OpenAI Whisper as Deepgram SDK v5.x API structure needs fixing
    # TODO: Fix Deepgram SDK v5.x integration
    print("[Deepgram] Using OpenAI Whisper as fallback (Deepgram SDK v5.x API needs fixing)")
    return transcribe_with_openai(audio_path, transcription_language)
    
    # Original Deepgram code (commented out until SDK structure is clarified):
    # api_key = os.environ.get("DEEPGRAM_API_KEY")
    # if not api_key:
    #     return "Transcription failed: No Deepgram API key"
    # 
    # try:
    #     deepgram = DeepgramClient(api_key=api_key)
    #     # ... rest of implementation


# Keep OpenAI function for backward compatibility (can be removed later)
def transcribe_with_openai(audio_path, transcription_language="en"):
    """Transcribe audio using OpenAI Whisper API (kept for backward compatibility)"""
    from openai import OpenAI
    
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return "Transcription failed: No API key"

    try:
        # Create OpenAI client
        client = OpenAI(api_key=api_key)

        # Check if file exists and has content
        if not os.path.exists(audio_path):
            return f"Audio file not found: {audio_path}"

        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            return "No audio recorded"

        # Transcribe audio using Whisper API
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=transcription_language if transcription_language != "en" else None,
            )

        full_transcript = transcript.text.strip()
        print(f"OpenAI Transcript: {full_transcript}")
        return full_transcript if full_transcript else "No speech detected in audio"

    except Exception as e:
        return f"Transcription failed: {str(e)}"
