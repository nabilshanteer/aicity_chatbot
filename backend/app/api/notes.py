import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import anthropic
from app.database import get_db
from app.models import Case
from app.core.config import settings

router = APIRouter(prefix="/api/notes", tags=["notes"])


class SuggestRequest(BaseModel):
    fragments: list[str]
    context: str = ""


class NoteSuggestion(BaseModel):
    fragment: str
    suggestion: str | None
    full: str


class SuggestResponse(BaseModel):
    suggestions: list[NoteSuggestion]


class SaveNotesRequest(BaseModel):
    notes: list[str]


def _anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


@router.post("/suggest", response_model=SuggestResponse)
def suggest_notes(payload: SuggestRequest):
    """
    Takes short note fragments jotted during a call and uses Grok to suggest
    what each one likely refers to in a Citizens Advice case context.
    """
    if not payload.fragments:
        return SuggestResponse(suggestions=[])

    fragments_list = "\n".join(
        f"{i + 1}. \"{f}\"" for i, f in enumerate(payload.fragments)
    )

    context_line = f"Case context: {payload.context}\n\n" if payload.context else ""

    prompt = f"""{context_line}A Citizens Advice caseworker is taking rapid notes during a phone call. \
They have jotted down these short fragments:

{fragments_list}

For each fragment, suggest the most likely completing phrase (1–3 words) that makes the note clear \
in a Citizens Advice housing, benefits, employment, or family law context.

Return ONLY a valid JSON array — no markdown, no explanation. Each object must have:
- "fragment": the original fragment exactly as given
- "suggestion": 1–3 completing words (null if the fragment is already clear on its own)
- "full": the complete phrase (fragment + suggestion, or just fragment if suggestion is null)

Example: [{{"fragment": "2 years", "suggestion": "tenancy", "full": "2 years tenancy"}}]"""

    try:
        client = _anthropic_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=(
                "You are a helpful assistant for Citizens Advice caseworkers. "
                "You return ONLY valid JSON arrays, never markdown or extra text."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if Claude adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        suggestions = [
            NoteSuggestion(
                fragment=item["fragment"],
                suggestion=item.get("suggestion"),
                full=item["full"],
            )
            for item in data
        ]
        return SuggestResponse(suggestions=suggestions)
    except Exception as e:
        # Return fragments as-is if Grok fails
        return SuggestResponse(
            suggestions=[
                NoteSuggestion(fragment=f, suggestion=None, full=f)
                for f in payload.fragments
            ]
        )


@router.get("/{chat_id}")
def get_notes(chat_id: str, db: Session = Depends(get_db)):
    chat = db.query(Case).filter(Case.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = json.loads(chat.notes) if chat.notes else []
    return {"notes": notes}


@router.put("/{chat_id}")
def save_notes(chat_id: str, payload: SaveNotesRequest, db: Session = Depends(get_db)):
    chat = db.query(Case).filter(Case.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Case not found")
    chat.notes = json.dumps(payload.notes)
    db.commit()
    return {"ok": True}
