from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.llm import get_llm_provider
from services.prompt import build_prompt
from memory.vector import add_memory
from emotion.engine import emotion
from tools.executor import execute_if_tool

router = APIRouter()

conversation_history: list[dict] = []


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    prompt = build_prompt(req.message, conversation_history)
    llm    = get_llm_provider()

    async def generate():
        full_response = ""
        async for chunk in llm.stream(prompt):
            full_response += chunk
            yield chunk

        # Check for tool calls in the response
        clean_response, tool_result = execute_if_tool(full_response)

        if tool_result:
            yield f"\n[Tool result: {tool_result}]"

        conversation_history.append({"role": "user",      "content": req.message})
        conversation_history.append({"role": "assistant", "content": clean_response})
        add_memory(f"User said: {req.message}", category="event")
        emotion.apply_event("positive_interaction")

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/emotion")
async def get_emotion():
    return emotion.to_dict()