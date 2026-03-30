import uuid
import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import anthropic
from app.core.config import settings
from app.models import Case, Message
from app.database import SessionLocal

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseStartRequest(BaseModel):
    user_id: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    depth: str = "standard"


@router.post("/start")
def start_case(request: CaseStartRequest):
    """Create a new case and return case_id"""
    try:
        db = SessionLocal()
        case_id = str(uuid.uuid4())
        user_id = request.user_id or "anonymous"  # Default to anonymous if no user_id provided
        
        new_case = Case(id=case_id, user_id=user_id)
        db.add(new_case)
        db.commit()
        
        print(f"[CASES] Created case: {case_id}")
        return {"case_id": case_id}
    except Exception as e:
        print(f"[ERROR] Failed to create case: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")


@router.post("/{case_id}/query")
def ask_question(case_id: str, request: QueryRequest):
    """Process a question using RAG with Claude"""
    try:
        print(f"[QUERY] Received query for case_id: {case_id}, query: {request.query}")
        
        db = SessionLocal()
        
        # Verify case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            print(f"[ERROR] Case not found: {case_id}")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
        print(f"[QUERY] Case verified: {case_id}")
        
        # Get context from previous messages (simplified - just return answer and sources)
        # In production, you'd load FAISS index and do vector search here
        
        try:
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            # For now, simple Claude response without RAG
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                system="You are a helpful Citizens Advice caseworker. Be clear and cite relevant sources when applicable.",
                messages=[{
                    "role": "user",
                    "content": request.query
                }]
            )
            
            answer = response.content[0].text
            print(f"[QUERY] Generated response for case {case_id}")
            
            # Save message to database
            user_message = Message(
                case_id=case_id,
                role="user",
                content=request.query
            )
            assistant_message = Message(
                case_id=case_id,
                role="assistant",
                content=answer
            )
            db.add(user_message)
            db.add(assistant_message)
            db.commit()
            
            print(f"[QUERY] Saved messages for case {case_id}")
            
            return {
                "answer": answer,
                "sources": [],
                "retrieved_documents": 0,
                "persistent_history_count": 2
            }
            
        except Exception as e:
            print(f"[ERROR] Claude API error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
