import io
import re
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

conversation_history = load_conversation_history(MAX_HISTORY)

# ── EMOTION TAG HELPERS ───────────────────────────────────────────────────────
EMOTION_TAG_MAP = {
    "positive":   "positive_interaction",
    "excited":    "exciting_news",
    "sad":        "sad_topic",
    "surprised":  "surprise",
    "frustrated": "user_frustrated",
    "fun":        "joke_or_fun",
    "neutral":    "positive_interaction",
}

def parse_emotion_tag(text: str) -> str | None:
    match = re.search(r'<emotion>(.*?)</emotion>', text, re.IGNORECASE)
    return match.group(1).strip().lower() if match else None

def strip_emotion_tag(text: str) -> str:
    return re.sub(r'\n?<emotion>.*?</emotion>', '', text, flags=re.IGNORECASE).strip()

# ── GREETING DETECTION ────────────────────────────────────────────────────────
GREETING_WORDS = ["hello", "hi", "hey", "good morning", "good evening", "what's up"]

async def fire_emotion(tag: str):
    """Apply emotion event and immediately broadcast to avatar."""
    event = EMOTION_TAG_MAP.get(tag, "positive_interaction")
    emotion.apply_event(event)
    logger.info(f"Emotion fired: {tag} → {event} | state: {emotion.to_dict()}")
    try:
        from api.websocket import broadcast
        await broadcast({
            "type":      "heartbeat",
            "emotion":   emotion.to_dict(),
            "animation": tag if tag in ["excited", "surprised", "thinking"] else "idle",
        })
    except Exception as e:
        logger.warning(f"Broadcast failed: {e}")


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

    # ── READ AUDIO ────────────────────────────────────────────────────────────
    try:
        contents  = await audio.read()
        sr, data  = wav.read(io.BytesIO(contents))
        audio_arr = data.astype(np.float32) / 32768.0
    except Exception as e:
        logger.error(f"Audio read error: {e}")
        raise HTTPException(status_code=400, detail="Could not read audio file.")

    # ── TRANSCRIBE ────────────────────────────────────────────────────────────
    try:
        user_text = transcribe(audio_arr, sample_rate=sr)
    except Exception as e:
        logger.error(f"STT error: {e}")
        return Response(content=synthesize(FALLBACK_TEXT), media_type="audio/wav")

    if not user_text:
        return Response(content=synthesize(FALLBACK_TEXT), media_type="audio/wav")

    logger.info(f"Transcribed: {user_text}")

    # Greeting detection
    if any(w in user_text.lower() for w in GREETING_WORDS):
        await fire_emotion("positive")

    # ── NOTIFY AVATAR: THINKING ───────────────────────────────────────────────
    try:
        from api.websocket import broadcast
        await broadcast({"type": "thinking", "animation": "thinking"})
    except Exception:
        pass

    # ── LLM ───────────────────────────────────────────────────────────────────
    try:
        prompt        = build_prompt(user_text, conversation_history)
        llm           = get_llm_provider()
        raw_response  = ""
        async with asyncio.timeout(30):
            async for chunk in llm.stream(prompt):
                raw_response += chunk
    except asyncio.TimeoutError:
        raw_response = "I'm thinking slowly right now. Try asking me again.<emotion>neutral</emotion>"
    except Exception as e:
        logger.error(f"LLM error: {e}")
        raw_response = FALLBACK_TEXT

    logger.info(f"Raw LLM response: {raw_response[:120]}...")

    # ── PARSE EMOTION TAG (before anything else touches the text) ─────────────
    emotion_tag = parse_emotion_tag(raw_response)
    logger.info(f"Emotion tag found: {emotion_tag}")

    # ── STRIP EMOTION TAG from text ───────────────────────────────────────────
    text_no_emotion = strip_emotion_tag(raw_response)

    # ── TOOL EXECUTION ────────────────────────────────────────────────────────
    try:
        clean_response, tool_result = execute_if_tool(text_no_emotion)
        if tool_result:
            logger.info(f"Tool result: {tool_result}")
    except Exception as e:
        logger.error(f"Tool error: {e}")
        clean_response = text_no_emotion

    # ── NUCLEAR STRIP — remove ALL tags before TTS ────────────────────────────
    import re
    clean_response = re.sub(r'<tool>.*?</tool>', '', clean_response, flags=re.DOTALL).strip()
    clean_response = re.sub(r'<emotion>.*?</emotion>', '', clean_response, flags=re.DOTALL).strip()
    clean_response = re.sub(r'<[^>]+>', '', clean_response).strip()  # any remaining tags
    if not clean_response:
        clean_response = "Done."

    # ── FIRE EMOTION → AVATAR (before TTS so avatar reacts as Vini speaks) ───
    if emotion_tag and emotion_tag in EMOTION_TAG_MAP:
        await fire_emotion(emotion_tag)
    else:
        # Fallback: infer from content keywords if LLM forgot the tag
        lower = clean_response.lower()
        if any(w in lower for w in ["sorry", "sad", "unfortunate", "oh no"]):
            await fire_emotion("sad")
        elif any(w in lower for w in ["wow", "amazing", "incredible", "exciting"]):
            await fire_emotion("excited")
        elif any(w in lower for w in ["haha", "funny", "joke", "laugh"]):
            await fire_emotion("fun")
        else:
            await fire_emotion("positive")

    # ── NOTIFY AVATAR: TALKING ────────────────────────────────────────────────
    try:
        from api.websocket import broadcast
        await broadcast({"type": "talking", "animation": "talking"})
    except Exception:
        pass

    # ── SYNTHESIZE ────────────────────────────────────────────────────────────
    try:
        audio_bytes = synthesize(clean_response)
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")

    # ── BROADCAST AMPLITUDE FRAMES async (non-blocking) ───────────────────────
    try:
        frames = extract_amplitude_frames(audio_bytes)
        from api.websocket import broadcast

        async def stream_frames():
            await broadcast({"type": "talking", "animation": "talking"})
            for frame in frames:
                await broadcast({
                    "type":      "amplitude",
                    "amplitude": float(frame),
                    "animation": "talking"
                })
                await asyncio.sleep(0.02)
            await broadcast({"type": "idle", "animation": "idle"})

        # Fire and forget — runs concurrently while audio plays on client
        asyncio.create_task(stream_frames())

    except Exception as e:
        logger.error(f"Amplitude broadcast error: {e}")

    # ── MEMORY ────────────────────────────────────────────────────────────────
    try:
        save_conversation("user",      user_text,      current_session_id)
        save_conversation("assistant", clean_response, current_session_id)
        conversation_history.append({"role": "user",      "content": user_text})
        conversation_history.append({"role": "assistant", "content": clean_response})
        if len(conversation_history) > MAX_HISTORY:
            del conversation_history[:2]
        add_memory(f"User said: {user_text}", category="event")
    except Exception as e:
        logger.error(f"Memory error: {e}")

    return Response(content=audio_bytes, media_type="audio/wav")