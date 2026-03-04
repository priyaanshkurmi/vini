from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.llm import get_llm_provider
from services.prompt import build_prompt
from memory.vector import add_memory
from emotion.engine import emotion
from tools.executor import execute_if_tool
import asyncio
import logging
import re

router = APIRouter()
logger = logging.getLogger("vini.chat")

conversation_history: list[dict] = []
MAX_HISTORY = 50

# Map emotion tags → engine events
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
    match = re.search(r'<emotion>(.*?)</emotion>', text)
    return match.group(1).strip() if match else None


def strip_emotion_tag(text: str) -> str:
    return re.sub(r'\n?<emotion>.*?</emotion>', '', text).strip()


class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_must_be_valid(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty.")
        if len(v) > 2000:
            raise ValueError("Message too long. Max 2000 characters.")
        return v


@router.post("/chat")
async def chat(req: ChatRequest):
    # Detect greeting
    greeting_words = ["hello", "hi", "hey", "good morning", "good evening"]
    if any(w in req.message.lower() for w in greeting_words):
        emotion.apply_event("greeting")

    try:
        prompt = build_prompt(req.message, conversation_history)
        llm    = get_llm_provider()
    except Exception as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialise LLM.")

    async def generate():
        full_response = ""
        try:
            async with asyncio.timeout(30):
                async for chunk in llm.stream(prompt):
                    full_response += chunk
                    # Stream only — don't stream the emotion tag
                    if '<emotion>' not in full_response:
                        yield chunk
                    else:
                        # Stream up to where emotion tag starts
                        tag_start = full_response.find('<emotion>')
                        already_streamed = len(full_response) - len(chunk)
                        if tag_start > already_streamed:
                            yield chunk[:tag_start - already_streamed]
        except asyncio.TimeoutError:
            yield "\n[Vini timed out. Please try again.]"
            return
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield "\n[Something went wrong. Please try again.]"
            return

        # Parse and apply emotion
        emotion_tag = parse_emotion_tag(full_response)
        clean_response = strip_emotion_tag(full_response)

        if emotion_tag and emotion_tag in EMOTION_TAG_MAP:
            event = EMOTION_TAG_MAP[emotion_tag]
            emotion.apply_event(event)
            logger.info(f"Emotion event: {emotion_tag} → {event}")

            # Broadcast emotion change to avatar immediately
            try:
                from api.websocket import broadcast
                await broadcast({
                    "type":      "heartbeat",
                    "emotion":   emotion.to_dict(),
                    "animation": emotion_tag if emotion_tag in ["excited","surprised"] else "idle",
                })
            except Exception:
                pass

        # Tool execution
        try:
            tool_response, tool_result = execute_if_tool(clean_response)
            if tool_result:
                yield f"\n[Tool result: {tool_result}]"
        except Exception as e:
            logger.error(f"Tool error: {e}")

        # Store history
        conversation_history.append({"role": "user",      "content": req.message})
        conversation_history.append({"role": "assistant", "content": clean_response})
        if len(conversation_history) > MAX_HISTORY:
            del conversation_history[:2]

        add_memory(f"User said: {req.message}", category="event")

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/emotion")
async def get_emotion():
    return emotion.to_dict()


@router.get("/history")
async def get_history():
    return {"count": len(conversation_history), "history": conversation_history[-10:]}


@router.delete("/history")
async def clear_history():
    conversation_history.clear()
    return {"status": "History cleared."}