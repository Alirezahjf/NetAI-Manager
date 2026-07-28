from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.ai_engine import ai_engine

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7


class ReplyRequest(BaseModel):
    message_text: str = Field(..., min_length=1)
    platform: str = ""
    chat_context: str = ""
    extra_instructions: str = ""


@router.post("/generate")
async def generate(body: GenerateRequest):
    try:
        text = await ai_engine.generate(
            body.prompt,
            system=body.system,
            model=body.model,
            temperature=body.temperature,
        )
    except Exception as exp:
        raise HTTPException(400, detail=str(exp)) from exp
    return {"text": text}


@router.post("/reply")
async def smart_reply(body: ReplyRequest):
    try:
        text = await ai_engine.reply_to_message(
            body.message_text,
            platform=body.platform,
            chat_context=body.chat_context,
            extra_instructions=body.extra_instructions,
        )
    except Exception as exp:
        raise HTTPException(400, detail=str(exp)) from exp
    return {"reply": text}


@router.get("/models")
async def list_models():
    """List models available via AvalAI (or configured provider)."""
    try:
        models = await ai_engine.list_models()
    except Exception as exp:
        raise HTTPException(400, detail=str(exp)) from exp
    return {"count": len(models), "models": models}
