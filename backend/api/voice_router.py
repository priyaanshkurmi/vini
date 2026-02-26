import io
import numpy as np
import scipy.io.wavfile as wav
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from services.stt import transcribe
from services.tts import synthesize, extract_amplitude_frames
from services.llm import get_llm_provider
from services.prompt import build_prompt
from memory.vector import add_memory
from emotion.engine import emotion
from tools.executor import execute_if_tool

voice_router = APIRouter()

# Shared conversation history with chat router
conversation_history: list[dict] = []


class SpeakRequest(BaseModel):
    text: str


@voice_router.post("/speak")
async def speak(req: SpeakRequest):
    """Convert text to speech — returns WAV audio."""
    audio_bytes = synthesize(req.text)
    return Response(content=audio_bytes, media_type="audio/wav")


@voice_router.post("/voice")
async def voice_chat(audio: UploadFile = File(...)):
    """Accept WAV audio, transcribe, get LLM response, return audio."""

    # Read uploaded audio
    contents  = await audio.read()
    sr, data  = wav.read(io.BytesIO(contents))
    audio_arr = data.astype(np.float32) / 32768.0

    # Transcribe
    user_text = transcribe(audio_arr, sample_rate=sr)
    if not user_text:
        return Response(content=b"", media_type="audio/wav")

    print(f"Transcribed: {user_text}")

    # Get LLM response
    prompt   = build_prompt(user_text, conversation_history)
    llm      = get_llm_provider()
    response_text = ""
    async for chunk in llm.stream(prompt):
        response_text += chunk

    # Handle tool calls
    clean_response, tool_result = execute_if_tool(response_text)

    # Store in memory
    conversation_history.append({"role": "user",      "content": user_text})
    conversation_history.append({"role": "assistant", "content": clean_response})
    add_memory(f"User said: {user_text}", category="event")
    emotion.apply_event("positive_interaction")

    # Synthesize response to audio
    audio_bytes = synthesize(clean_response)
    return Response(content=audio_bytes, media_type="audio/wav")