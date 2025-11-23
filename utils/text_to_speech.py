import os
import tempfile
from elevenlabs import ElevenLabs


def generate_speech_elevenlabs(text, voice_id=None, model="eleven_turbo_v2_5"):
    """
    Generate speech using ElevenLabs TTS API (v2.x SDK)
    
    Args:
        text: Text to convert to speech
        voice_id: Voice ID from ElevenLabs (defaults to first available voice or "21m00Tcm4TlvDq8ikWAM")
        model: Model to use (default: "eleven_turbo_v2_5" for fast, or "eleven_multilingual_v2" for quality)
    
    Returns:
        str: Path to temporary audio file (MP3 format)
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    
    if not api_key:
        raise ValueError("ElevenLabs API key not configured")
    
    try:
        # Initialize ElevenLabs client
        client = ElevenLabs(api_key=api_key)
        
        # If no voice_id provided, use default
        if not voice_id:
            # Default to a good general-purpose voice
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - clear and professional
        
        # Generate speech using the client
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model,
            output_format="mp3_44100_128",
        )
        
        # Collect audio bytes
        audio_bytes = b""
        for chunk in audio_generator:
            audio_bytes += chunk
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
        
        return tmp_file_path
    
    except Exception as e:
        print(f"ElevenLabs TTS Error: {e}")
        print("Text:", text)
        raise


def get_elevenlabs_voices():
    """Get list of available ElevenLabs voices"""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    
    if not api_key:
        return []
    
    try:
        client = ElevenLabs(api_key=api_key)
        voices_response = client.voices.get_all()
        
        return [
            {
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": getattr(voice, "category", "unknown"),
            }
            for voice in voices_response.voices
        ]
    except Exception as e:
        print(f"Error fetching ElevenLabs voices: {e}")
        return []


def map_voice_to_elevenlabs(voice_name):
    """
    Map legacy voice names to ElevenLabs voice IDs
    
    Args:
        voice_name: Legacy voice name (e.g., "Alex (Male)", "alloy", etc.)
    
    Returns:
        str: ElevenLabs voice ID
    """
    # Default voice mapping
    voice_mapping = {
        "alloy": "21m00Tcm4TlvDq8ikWAM",  # Rachel - clear and professional
        "echo": "EXAVITQu4vr4xnSDxMaL",   # Bella - warm and friendly
        "fable": "ErXwobaYiN019PkySvjV",  # Antoni - deep and authoritative
        "onyx": "MF3mGyEYCl7XYWbV9V6O",   # Elli - calm and professional
        "nova": "ThT5KcBeYPX3keUQyHlb",   # Domi - energetic
        "shimmer": "TxGEqnHWrfWFTfGW9XjX", # Josh - male, professional
        "Alex (Male)": "TxGEqnHWrfWFTfGW9XjX",  # Josh
        "Alex": "TxGEqnHWrfWFTfGW9XjX",
        "Female": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "Male": "TxGEqnHWrfWFTfGW9XjX",   # Josh
    }
    
    # Normalize voice name
    normalized = voice_name.strip() if voice_name else "alloy"
    
    # Return mapped voice or default
    return voice_mapping.get(normalized, voice_mapping["alloy"])


def speak_text(text, voice="alloy", rate="+0%", pitch="+0Hz"):
    """
    Generate and play speech using ElevenLabs TTS
    
    Note: rate and pitch parameters are kept for compatibility but not used with ElevenLabs
    """
    import pygame
    
    try:
        # Map voice name to ElevenLabs voice ID
        voice_id = map_voice_to_elevenlabs(voice)
        
        # Generate speech file
        audio_file_path = generate_speech_elevenlabs(text, voice_id=voice_id)
        
        # Play using pygame
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        pygame.mixer.quit()
        
        # Clean up temp file
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
    
    except Exception as e:
        print(f"Error playing speech: {e}")
        print("Text:", text)


# Keep OpenAI function for backward compatibility
def generate_speech_openai(text, voice="alloy", output_format="mp3"):
    """
    Generate speech using OpenAI TTS API (kept for backward compatibility)
    """
    from openai import OpenAI
    
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API key not configured")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Generate speech
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format=output_format,
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}") as tmp_file:
            for chunk in response.iter_bytes():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        return tmp_file_path
    
    except Exception as e:
        print(f"OpenAI TTS Error: {e}")
        print("Text:", text)
        raise
