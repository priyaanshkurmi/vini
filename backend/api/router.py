from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.llm import get_llm_provider
from services.prompt import build_prompt
from memory.vector import add_memory
from memory.conversation import save_conversation, load_conversation_history, clear_conversation_history
from emotion.engine import emotion
from tools.executor import execute_if_tool
import asyncio
import logging
import uuid

router = APIRouter()
logger = logging.getLogger("vini.chat")

conversation_history: list[dict] = []
current_session_id: str = str(uuid.uuid4())
MAX_HISTORY = 50


# Load history on startup
conversation_history = load_conversation_history(MAX_HISTORY)


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
                    yield chunk
        except asyncio.TimeoutError:
            logger.warning("LLM timed out.")
            yield "\n[Vini timed out. Please try again.]"
            return
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield "\n[Something went wrong. Please try again.]"
            return

        # Post-response processing
        try:
            clean_response, tool_result = execute_if_tool(full_response)
            if tool_result:
                yield f"\n[Tool result: {tool_result}]"

            # Save to database and memory
            save_conversation("user", req.message, current_session_id)
            save_conversation("assistant", clean_response, current_session_id)

            # Keep in-memory history capped
            conversation_history.append({"role": "user",      "content": req.message})
            conversation_history.append({"role": "assistant", "content": clean_response})
            if len(conversation_history) > MAX_HISTORY:
                del conversation_history[:2]

            add_memory(f"User said: {req.message}", category="event")
            emotion.apply_event("positive_interaction")
        except Exception as e:
            logger.error(f"Post-processing error: {e}")

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/emotion")
async def get_emotion():
    return emotion.to_dict()




@router.get("/history")
async def get_history():
    return {"count": len(conversation_history), "history": conversation_history[-10:]}


@router.delete("/history")
async def clear_history():
    """Clear conversation history from both memory and database."""
    global conversation_history, current_session_id
    conversation_history.clear()
    clear_conversation_history()
    # Start a new session for future conversations
    current_session_id = str(uuid.uuid4())
    return {"status": "History cleared."}