import io
import asyncio
import logging
import uuid
import numpy as np
import scipy.io.wavfile as wav
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from services.stt import transcribe
from services.tts import synthesize, extract_amplitude_frames
from services.llm import get_llm_provider
from services.prompt import build_prompt
from memory.vector import add_memory
from memory.conversation import save_conversation, load_conversation_history
from emotion.engine import emotion
from tools.executor import execute_if_tool

voice_router = APIRouter()
logger       = logging.getLogger("vini.voice")

conversation_history: list[dict] = []
current_session_id: str = str(uuid.uuid4())
MAX_HISTORY = 50

FALLBACK_TEXT = "Sorry, I had trouble with that. Could you try again?"

# Load history on startup
conversation_history = load_conversation_history(MAX_HISTORY)


class SpeakRequest(BaseModel):
    text: str


@voice_router.post("/speak")
async def speak(req: SpeakRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        audio_bytes = synthesize(req.text)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")


@voice_router.post("/voice")
async def voice_chat(audio: UploadFile = File(...)):
    # Read and decode audio
    try:
        contents  = await audio.read()
        sr, data  = wav.read(io.BytesIO(contents))
        audio_arr = data.astype(np.float32) / 32768.0
    except Exception as e:
        logger.error(f"Audio read error: {e}")
        raise HTTPException(status_code=400, detail="Could not read audio file.")

    # Transcribe
    try:
        user_text = transcribe(audio_arr, sample_rate=sr)
    except Exception as e:
        logger.error(f"STT error: {e}")
        return Response(content=synthesize(FALLBACK_TEXT), media_type="audio/wav")

    if not user_text:
        return Response(content=synthesize(FALLBACK_TEXT), media_type="audio/wav")

    logger.info(f"Transcribed: {user_text}")

    # Notify avatar — listening state
    try:
        from api.websocket import broadcast
        await broadcast({"type": "listening", "animation": "listening"})
    except Exception:
        pass

    # LLM response
    try:
        prompt        = build_prompt(user_text, conversation_history)
        llm           = get_llm_provider()
        response_text = ""
        async with asyncio.timeout(30):
            async for chunk in llm.stream(prompt):
                response_text += chunk
    except asyncio.TimeoutError:
        response_text = "I'm thinking slowly right now. Try asking me again."
    except Exception as e:
        logger.error(f"LLM error: {e}")
        response_text = FALLBACK_TEXT

    # Tool execution
    try:
        clean_response, tool_result = execute_if_tool(response_text)
        if tool_result:
            logger.info(f"Tool result: {tool_result}")
    except Exception as e:
        logger.error(f"Tool error: {e}")
        clean_response = response_text

    # Synthesize audio
    try:
        audio_bytes = synthesize(clean_response)
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")

    # Broadcast amplitude frames to avatar for lip sync
    try:
        frames = extract_amplitude_frames(audio_bytes)
        from api.websocket import broadcast
        await broadcast({"type": "amplitude", "frames": frames})
    except Exception as e:
        logger.error(f"Amplitude broadcast error: {e}")

    # Store in memory and database
    try:
        save_conversation("user", user_text, current_session_id)
        save_conversation("assistant", clean_response, current_session_id)
        conversation_history.append({"role": "user",      "content": user_text})
        conversation_history.append({"role": "assistant", "content": clean_response})
        if len(conversation_history) > MAX_HISTORY:
            del conversation_history[:2]
        add_memory(f"User said: {user_text}", category="event")
        emotion.apply_event("positive_interaction")
    except Exception as e:
        logger.error(f"Memory error: {e}")

    return Response(content=audio_bytes, media_type="audio/wav")