import uuid
import json
import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import anthropic
from app.core.config import settings
from app.models import Case, Message
from app.database import SessionLocal
from app import rag

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseStartRequest(BaseModel):
    user_id: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    depth: str = "standard"


@router.post("/start")
def start_case(request: CaseStartRequest, x_user_id: Optional[str] = Header(None)):
    """Create a new case and return case_id"""
    try:
        db = SessionLocal()
        case_id = str(uuid.uuid4())
        advisor_id = request.user_id or x_user_id or None
        new_case = Case(id=case_id, advisor_id=advisor_id)
        db.add(new_case)
        db.commit()
        print(f"[CASES] Created case: {case_id} for advisor: {advisor_id}")
        return {"case_id": case_id}
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create case: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")
    finally:
        db.close()


@router.post("/{case_id}/query")
def ask_question(case_id: str, request: QueryRequest, x_user_id: Optional[str] = Header(None)):
    """Process a question using RAG with Claude"""
    db = SessionLocal()
    try:
        print(f"[QUERY] Received query for case_id: {case_id}, query: {request.query[:100]}..., user: {x_user_id}")
        
        # Verify case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            print(f"[ERROR] Case not found: {case_id}")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
        print(f"[QUERY] Case verified: {case_id}")
        
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            # 1. Vector search — retrieve relevant Citizens Advice chunks
            retrieved = rag.search(request.query, top_k=5)
            sources = list({doc.get("source_url") for doc in retrieved if doc.get("source_url")})
            print(f"[QUERY] RAG retrieved {len(retrieved)} documents, sources: {sources}")

            # Build context block from retrieved chunks
            if retrieved:
                context_parts = [
                    f"[Source: {doc.get('source_url', 'Unknown')}]\n{doc['text']}"
                    for doc in retrieved
                ]
                rag_context = "\n\n".join(context_parts)
            else:
                rag_context = ""

            # 2. Get previous messages for conversation history
            prev_messages = db.query(Message).filter(Message.case_id == case_id).order_by(Message.created_at).all()

            # Build conversation history for Claude
            # DB stores "advisor"/"assistant"; Claude API requires "user"/"assistant"
            messages_for_claude = []
            for msg in prev_messages:
                claude_role = "user" if msg.role == "advisor" else "assistant"
                messages_for_claude.append({"role": claude_role, "content": msg.content})

            # 3. Compose user turn: inject retrieved context before the question
            if rag_context:
                user_turn = (
                    f"Relevant information from Citizens Advice:\n\n{rag_context}"
                    f"\n\n---\n\nUser question: {request.query}"
                )
            else:
                user_turn = request.query

            messages_for_claude.append({"role": "user", "content": user_turn})

            print(f"[QUERY] Sending to Claude with {len(messages_for_claude)} messages, RAG={'yes' if rag_context else 'no'}")

            system_prompt = (
                "You are a professional advisor for Citizens Advice. "
                "Use the provided context from Citizens Advice sources to answer accurately. "
                "Cite source URLs in square brackets when referencing them, e.g. [https://...]. "
                "If the context does not cover the question, say so clearly and give general guidance."
            )

            # 4. Call Claude
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=messages_for_claude,
            )

            answer = response.content[0].text
            print(f"[QUERY] Generated response: {answer[:100]}...")

            # 5. Save the raw user query (not the augmented turn) and the answer
            db.add(Message(case_id=case_id, role="advisor", content=request.query))
            db.add(Message(case_id=case_id, role="assistant", content=answer))
            db.commit()

            print(f"[QUERY] Saved messages for case {case_id}")

            return {
                "answer": answer,
                "sources": sources,
                "retrieved_documents": len(retrieved),
                "persistent_history_count": len(messages_for_claude),
            }
            
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Claude/database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Unhandled exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        db.close()
