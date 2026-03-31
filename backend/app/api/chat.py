from fastapi import APIRouter
from pydantic import BaseModel
import anthropic
from app.core.config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])


class TitleRequest(BaseModel):
    message: str


@router.post("/title")
def generate_title(payload: TitleRequest):
    """
    Summarises the first message of a conversation into a 1-6 word title.
    Falls back gracefully if the API call fails.
    """
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=32,
            system=(
                "You generate ultra-short conversation titles for a Citizens Advice caseworker tool. "
                "Reply with ONLY the title — 1 to 6 words, no punctuation, no quotes, no explanation."
            ),
            messages=[{
                "role": "user",
                "content": f"Summarise this message as a 1-6 word conversation title:\n\n{payload.message[:500]}",
            }],
        )
        title = response.content[0].text.strip().strip('"').strip("'")
        return {"title": title}
    except Exception:
        # Fallback: first 4 words
        words = payload.message.strip().split()
        return {"title": " ".join(words[:4])}
