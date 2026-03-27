# Project Tasks
## Citizens Advice AI Chatbot

**Status key:** `[ ]` not started · `[~]` in progress · `[x]` done

---

## Codebase Snapshot (read this before any task)

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, CORS, routers
│   ├── api/
│   │   ├── auth.py                # POST /api/auth/login
│   │   ├── chat.py                # POST /api/chat/, /stream, DELETE /{id}
│   │   └── documents.py           # POST /upload, DELETE /{name}
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (DATABASE_URL, ANTHROPIC_API_KEY, etc.)
│   │   ├── security.py            # verify_password, get_password_hash, create_access_token, decode_token, bearer_scheme
│   │   └── deps.py                # get_current_user, require_role(*roles)
│   ├── db/
│   │   ├── models.py              # UserRecord, SessionRecord, AuditLogRecord (SQLModel tables)
│   │   ├── engine.py              # engine, AsyncSessionLocal, init_db(), get_session()
│   │   ├── crud.py                # all DB query functions
│   │   └── seed.py                # seed_initial_users()
│   ├── models/
│   │   ├── chat.py                # Pydantic: Message, SourceChunk, ChatRequest, ChatResponse, Session
│   │   └── user.py                # Pydantic: User, UserInDB, TokenResponse, LoginRequest
│   ├── services/
│   │   ├── vector_store.py        # VectorStoreService (ChromaDB), vector_store singleton
│   │   └── llm_service.py         # LLMService (Anthropic Claude), llm_service singleton
│   └── utils/
│       └── document_processor.py  # ingest_file(), chunk_text()
├── data/
│   ├── app.db                     # SQLite (created at runtime)
│   └── chroma_db/                 # ChromaDB persistent store
└── requirements.txt
```

### Key type signatures (memorise these)

```python
# deps.py
async def get_current_user(...) -> UserRecord          # raises 401 if invalid
def require_role(*roles: str) -> Callable              # raises 403 if wrong role

# crud.py — sessions
async def get_or_create_session(session, session_id, user_id, case_category) -> SessionRecord
async def get_session_history(session, session_id) -> list[dict]   # raw dicts
async def append_messages_to_session(session, session_id, new_messages: list[dict]) -> None
async def delete_session(session, session_id) -> None

# crud.py — users
async def get_user_by_username(session, username) -> UserRecord | None
async def get_user_by_id(session, user_id) -> UserRecord | None
async def create_user(session, username, email, password, role) -> UserRecord

# crud.py — audit
async def write_audit_log(session, user_id, event_type, session_id=None, depth_mode=None, document_name=None) -> None

# vector_store.py
def retrieve(query, depth) -> list[SourceChunk]        # depth: "quick"|"standard"|"deep"
def add_documents(texts, metadatas, ids) -> None
def delete_document(source_name) -> None

# llm_service.py
def generate(history, user_message, sources, depth) -> str
async def stream(history, user_message, sources, depth) -> AsyncGenerator[str, None]
```

### SQLModel table schemas

```python
# UserRecord  (table="users")
id: str PK, username: str UNIQUE INDEX, email: str UNIQUE,
role: str DEFAULT "advisor", hashed_password: str,
is_active: bool DEFAULT True, created_at: datetime

# SessionRecord  (table="sessions")
id: str PK (caller-supplied UUID), user_id: str FK→users.id INDEX,
title: str|None, case_category: str|None,
history_json: str DEFAULT "[]"  ← JSON-serialised List[Message dict]
created_at: datetime, updated_at: datetime

# AuditLogRecord  (table="audit_logs")
id: int PK autoincrement, timestamp: datetime INDEX,
user_id: str INDEX (HMAC-SHA256 anonymised),
event_type: str, session_id: str|None,
depth_mode: str|None, document_name: str|None
```

### Import conventions (always use these)

```python
from sqlmodel.ext.asyncio.session import AsyncSession   # NOT sqlalchemy's AsyncSession
from app.db.engine import AsyncSessionLocal, get_session
from app.db.crud import ...
from app.db.models import UserRecord, SessionRecord, AuditLogRecord
from app.core.deps import get_current_user, require_role
```

---

## What's Already Built

- [x] FastAPI backend skeleton (routing, CORS, config, lifespan)
- [x] ChromaDB vector store with sentence-transformer embeddings
- [x] Full RAG pipeline (ingest → chunk → embed → retrieve → generate)
- [x] Anthropic Claude LLM service (streaming + non-streaming)
- [x] SQLite + SQLModel: `users`, `sessions`, `audit_logs` tables
- [x] JWT login (`POST /api/auth/login`)
- [x] `get_current_user` + `require_role` FastAPI dependencies
- [x] RBAC: advisors for chat, admin for documents
- [x] UK GDPR audit logging (HMAC-anonymised user IDs, no raw query text)
- [x] Seeded users: `admin / ChangeMe123!` and `advisor1 / password123`

---

## Backend Tasks

### B1 · Relevance Score Filtering

**Why:** The spec requires filtering out retrieved chunks with `relevance_score < 0.45` before passing to the LLM. Currently all top-K results are passed regardless of score, which can inject irrelevant context.

**File to edit:** `backend/app/services/vector_store.py`

**Exact change:** In `VectorStoreService.retrieve()`, add a filter line immediately before `return chunks` (currently line 46):

```python
    # existing code that builds chunks list ends here
    chunks = [c for c in chunks if c.relevance_score >= 0.45]
    return chunks
```

The full `retrieve()` method after the change:

```python
def retrieve(self, query: str, depth: str = "standard") -> List[SourceChunk]:
    top_k = DEPTH_TOP_K.get(depth, 5)
    results = self.collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    if not results["documents"] or not results["documents"][0]:
        return chunks
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            SourceChunk(
                document_name=meta.get("source", "Unknown"),
                page=meta.get("page"),
                section=meta.get("section"),
                excerpt=doc,
                relevance_score=round(1 - dist, 4),
            )
        )
    chunks = [c for c in chunks if c.relevance_score >= 0.45]
    return chunks
```

**Verification:** Upload a document and query something completely unrelated — the response should say no sources were found rather than citing irrelevant chunks.

---

### B2 · Session Title Auto-Generation

**Why:** `SessionRecord.title` is always `null`. The frontend sidebar displays titles; without them all sessions appear untitled.

**Rule:** When a session's `history_json` is still `"[]"` (first ever message), set `title` to the first 60 characters of the user's message, stripped of leading/trailing whitespace.

**File 1 — `backend/app/db/crud.py`:** Add this function after `delete_session`:

```python
async def update_session_title(
    session: AsyncSession,
    session_id: str,
    title: str,
) -> None:
    """Sets title on a session only if it has not already been set."""
    record = await session.get(SessionRecord, session_id)
    if record and record.title is None:
        record.title = title[:60].strip()
        session.add(record)
        await session.commit()
```

**File 2 — `backend/app/api/chat.py`:** In **both** `chat()` and `chat_stream()`, after the `get_or_create_session(...)` call, add:

```python
    # Auto-generate title from first message
    raw_history = await get_session_history(db, request.session_id)
    if not raw_history:
        await update_session_title(db, request.session_id, request.message)
```

Note: in `chat()`, `raw_history` is already fetched on the next line — reorder so the title update uses that same fetch. In `chat_stream()`, `raw_history` is also fetched next — same applies. The combined block looks like:

```python
    await get_or_create_session(db, request.session_id, current_user.id, request.case_category)
    raw_history = await get_session_history(db, request.session_id)
    if not raw_history:
        await update_session_title(db, request.session_id, request.message)
    history = [Message(**m) for m in raw_history]
```

**Also add** `update_session_title` to the import in `chat.py`:

```python
from app.db.crud import (
    append_messages_to_session,
    delete_session,
    get_or_create_session,
    get_session_history,
    update_session_title,   # ← add this
    write_audit_log,
)
```

**Verification:** POST a new chat message → query the DB: `SELECT title FROM sessions;` — should show the first 60 chars of the message.

---

### B3 · Session Listing API

**Why:** The frontend sidebar calls this to list past sessions for the logged-in user.

**File 1 — `backend/app/db/crud.py`:** Add after `update_session_title`:

```python
async def get_sessions_for_user(
    session: AsyncSession,
    user_id: str,
) -> list[SessionRecord]:
    result = await session.exec(
        select(SessionRecord)
        .where(SessionRecord.user_id == user_id)
        .order_by(SessionRecord.updated_at.desc())
    )
    return result.all()
```

**File 2 — `backend/app/api/chat.py`:** Add a new route (place it before the `@router.delete` route):

```python
from app.db.crud import (
    ...,
    get_sessions_for_user,   # add to import
)

@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
):
    sessions = await get_sessions_for_user(db, current_user.id)
    return [
        {
            "id": s.id,
            "title": s.title,
            "case_category": s.case_category,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]
```

**Verification:** Login → POST a chat → GET `/api/chat/sessions` with Bearer token → should return a list with the session, including the auto-generated title from B2.

---

### B4 · Document Listing API

**Why:** The admin UI needs to show which documents are currently in the vector store.

**File 1 — `backend/app/services/vector_store.py`:** Add method to `VectorStoreService` after `delete_document`:

```python
def list_documents(self) -> list[str]:
    """Returns sorted list of distinct source document names in the collection."""
    result = self.collection.get(include=["metadatas"])
    sources = set()
    for meta in result.get("metadatas", []):
        if meta and "source" in meta:
            sources.add(meta["source"])
    return sorted(sources)
```

**File 2 — `backend/app/api/documents.py`:** Add route after the imports (before `@router.post("/upload")`):

```python
@router.get("/")
async def list_documents(
    current_user: UserRecord = Depends(require_role("admin")),
):
    return {"documents": vector_store.list_documents()}
```

No `db` dependency needed — this only reads ChromaDB.

**Verification:** Upload a document as admin → GET `/api/documents/` with admin Bearer token → should return `{"documents": ["your_filename.pdf"]}`.

---

### B5 · Message Feedback Endpoint

**Why:** Advisors can rate responses 👍/👎 (rating `1` or `-1`). This surfaces poor retrievals for review and is listed as High priority in the roadmap.

**File 1 — `backend/app/db/models.py`:** Add new table at the end of the file:

```python
class MessageFeedback(SQLModel, table=True):
    __tablename__ = "message_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    message_id: str = Field(index=True)
    user_id: str  # HMAC-anonymised, same as audit_logs
    rating: int   # 1 = positive, -1 = negative
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**File 2 — `backend/app/db/crud.py`:** Add after `write_audit_log`:

```python
async def write_feedback(
    session: AsyncSession,
    session_id: str,
    message_id: str,
    user_id: str,
    rating: int,
) -> None:
    from app.db.models import MessageFeedback
    fb = MessageFeedback(
        session_id=session_id,
        message_id=message_id,
        user_id=_anonymise_user_id(user_id),
        rating=rating,
    )
    session.add(fb)
    await session.commit()
```

**File 3 — `backend/app/models/chat.py`:** Add a new Pydantic request model at the end:

```python
class FeedbackRequest(BaseModel):
    rating: Literal[1, -1]
```

**File 4 — `backend/app/api/chat.py`:** Add to imports:

```python
from app.db.crud import (..., write_feedback)
from app.models.chat import (..., FeedbackRequest)
```

Add the route after `list_sessions`:

```python
@router.post("/{session_id}/messages/{message_id}/feedback", status_code=204)
async def submit_feedback(
    session_id: str,
    message_id: str,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
):
    await write_feedback(db, session_id, message_id, current_user.id, body.rating)
```

The `MessageFeedback` table is created automatically on next startup because `init_db()` calls `SQLModel.metadata.create_all`.

**Verification:** POST a chat → note the `message.id` from the response → POST to `/api/chat/{session_id}/messages/{message_id}/feedback` with `{"rating": 1}` → should return 204 → query DB: `SELECT * FROM message_feedback;`

---

### B6 · Structured Logging with Loguru

**Why:** `loguru` is in requirements but not configured. The spec requires structured JSON logs with request timing. Without this there is no observability.

**File 1 — `backend/app/core/logging.py`** (create new file):

```python
import logging
import sys
from loguru import logger


class InterceptHandler(logging.Handler):
    """Routes stdlib logging (uvicorn, sqlalchemy) through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}",
        serialize=False,  # set True to emit JSON lines in production
    )
    # Intercept uvicorn and sqlalchemy loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False
```

**File 2 — `backend/app/main.py`:** Add imports and setup call:

```python
import time
from loguru import logger
from fastapi import Request
from app.core.logging import setup_logging

# Call inside lifespan, before yield:
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_LEVEL)
    await init_db()
    await seed_initial_users()
    yield

# Add middleware after app.add_middleware(CORSMiddleware, ...):
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)"
    )
    return response
```

**Verification:** Start the server → make any API call → the console should show a timestamped log line like `2026-03-26 13:00:00 | INFO | app.main:XX | POST /api/auth/login → 200 (45.3ms)`.

---

### B7 · User Management APIs

**Why:** There is currently no way to create or deactivate users without directly editing the database. Admins need an API for this.

**File 1 — `backend/app/models/user.py`:** Add new Pydantic models at the end:

```python
class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "advisor"  # advisor | admin | readonly

class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
```

**File 2 — `backend/app/db/crud.py`:** Add after `create_user`:

```python
async def list_users(session: AsyncSession) -> list[UserRecord]:
    result = await session.exec(select(UserRecord).order_by(UserRecord.created_at))
    return result.all()


async def update_user(
    session: AsyncSession,
    user_id: str,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[UserRecord]:
    user = await session.get(UserRecord, user_id)
    if user is None:
        return None
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

**File 3 — `backend/app/api/admin.py`** (create new file):

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.security import verify_password, get_password_hash
from app.db.crud import create_user, list_users, update_user, get_user_by_id
from app.db.engine import get_session
from app.db.models import UserRecord
from app.models.user import (
    CreateUserRequest, UpdateUserRequest, UserResponse, ChangePasswordRequest
)

router = APIRouter()


def _to_response(u: UserRecord) -> UserResponse:
    return UserResponse(
        id=u.id, username=u.username, email=u.email,
        role=u.role, is_active=u.is_active, created_at=u.created_at,
    )


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_role("admin")),
):
    users = await list_users(db)
    return [_to_response(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_new_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_role("admin")),
):
    user = await create_user(db, body.username, body.email, body.password, body.role)
    return _to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_existing_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_role("admin")),
):
    user = await update_user(db, user_id, role=body.role, is_active=body.is_active)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)
```

**File 4 — `backend/app/api/auth.py`:** Add change-password endpoint at the end of the file:

```python
from app.core.deps import get_current_user
from app.models.user import ChangePasswordRequest

@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(body.new_password)
    db.add(current_user)
    await db.commit()
```

**File 5 — `backend/app/main.py`:** Register the admin router:

```python
from app.api import auth, chat, documents
from app.api import admin   # add this import

# Add after existing include_router calls:
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
```

**Verification:**
```bash
# List users (admin token)
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/admin/users

# Create a new advisor
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"newadvisor","email":"new@ca.org","password":"Test1234!","role":"advisor"}' \
  http://localhost:8000/api/admin/users

# Deactivate a user
curl -X PATCH -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"is_active": false}' http://localhost:8000/api/admin/users/{user_id}

# Change password
curl -X POST -H "Authorization: Bearer $ADVISOR_TOKEN" -H "Content-Type: application/json" \
  -d '{"current_password":"password123","new_password":"NewPass456!"}' \
  http://localhost:8000/api/auth/change-password
```

---

### B8 · Session Export Endpoint

**Why:** Advisors need to export session transcripts (e.g. to record case notes). Listed as Medium priority in roadmap.

**File — `backend/app/api/chat.py`:** Add route after `list_sessions`:

```python
from fastapi.responses import PlainTextResponse

@router.get("/{session_id}/export", response_class=PlainTextResponse)
async def export_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
):
    raw_history = await get_session_history(db, session_id)
    if not raw_history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    lines = [f"Session export: {session_id}\n{'='*60}"]
    for msg in raw_history:
        ts = msg.get("timestamp", "")[:19].replace("T", " ")
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        lines.append(f"\n[{ts}] {role}:\n{content}")
    return "\n".join(lines)
```

**Verification:** POST a chat message → GET `/api/chat/{session_id}/export` → response should be plain text with the conversation.

---

### B9 · Update `.env.example`

**Why:** `DATABASE_URL` is now a required setting but is not documented in `.env.example`.

**File — `backend/.env.example`:** Add the following line (exact content of the file — read it first to see current content, then append):

```
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

Also add a comment block near the top explaining the pinned dependency constraints:

```
# Dependency notes (do not change these without testing):
# bcrypt must be ==4.0.1 (passlib 1.7.4 is incompatible with bcrypt>=5.0)
# transformers must be ==4.44.2 (4.45+ requires torch>=2.3; we use torch 2.1.1)
# tf-keras==2.21.0 required by sentence-transformers via transformers.integrations
```

---

### B10 · Backend Test Suite

**Why:** No tests exist. `pytest==8.2.0` and `pytest-asyncio==0.23.7` are already in `requirements.txt`.

**Setup:** Create the directory `backend/tests/` with the following files.

---

**`backend/tests/__init__.py`** — empty.

---

**`backend/tests/conftest.py`:**

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app
from app.db.engine import get_session
from app.core.security import create_access_token

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_client(client):
    """Client with a seeded advisor1 user and a valid token."""
    from app.db.crud import create_user
    async with TestSessionLocal() as session:
        user = await create_user(session, "advisor1", "a@test.com", "password123", "advisor")
        admin = await create_user(session, "admin1", "admin@test.com", "Admin123!", "admin")
    advisor_token = create_access_token({"sub": user.id, "role": "advisor"})
    admin_token = create_access_token({"sub": admin.id, "role": "admin"})
    return client, advisor_token, admin_token, user.id, admin.id
```

---

**`backend/tests/test_auth.py`:**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(seeded_client):
    client, *_ = seeded_client
    resp = await client.post("/api/auth/login", json={"username": "advisor1", "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(seeded_client):
    client, *_ = seeded_client
    resp = await client.post("/api/auth/login", json={"username": "advisor1", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(seeded_client):
    client, *_ = seeded_client
    resp = await client.post("/api/auth/login", json={"username": "nobody", "password": "pass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_token(seeded_client):
    client, *_ = seeded_client
    resp = await client.post("/api/chat/", json={"session_id": "s-1", "message": "hi"})
    assert resp.status_code == 403  # HTTPBearer returns 403 when no header


@pytest.mark.asyncio
async def test_change_password(seeded_client):
    client, advisor_token, *_ = seeded_client
    resp = await client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {advisor_token}"},
        json={"current_password": "password123", "new_password": "NewPass456!"},
    )
    assert resp.status_code == 204
    # Old password no longer works
    resp2 = await client.post("/api/auth/login", json={"username": "advisor1", "password": "password123"})
    assert resp2.status_code == 401
```

---

**`backend/tests/test_chat.py`:**

Note: Tests that call `POST /api/chat/` will fail if `ANTHROPIC_API_KEY` is not set, because `llm_service.generate()` makes a real API call. Use `unittest.mock.patch` to stub it.

```python
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_chat_creates_session_and_audit(seeded_client):
    client, advisor_token, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.retrieve", return_value=[]), \
         patch("app.services.llm_service.llm_service.generate", return_value="Test response"):
        resp = await client.post(
            "/api/chat/",
            headers={"Authorization": f"Bearer {advisor_token}"},
            json={"session_id": "s-test-1", "message": "What is Universal Credit?", "depth": "standard"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "s-test-1"
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "Test response"


@pytest.mark.asyncio
async def test_session_title_set_on_first_message(seeded_client):
    client, advisor_token, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.retrieve", return_value=[]), \
         patch("app.services.llm_service.llm_service.generate", return_value="ok"):
        await client.post(
            "/api/chat/",
            headers={"Authorization": f"Bearer {advisor_token}"},
            json={"session_id": "s-title-test", "message": "Tell me about housing benefit"},
        )
    sessions = await client.get(
        "/api/chat/sessions", headers={"Authorization": f"Bearer {advisor_token}"}
    )
    assert sessions.status_code == 200
    titles = [s["title"] for s in sessions.json()]
    assert "Tell me about housing benefit" in titles


@pytest.mark.asyncio
async def test_session_history_persists(seeded_client):
    client, advisor_token, *_ = seeded_client
    for msg in ["First question", "Follow-up question"]:
        with patch("app.services.vector_store.vector_store.retrieve", return_value=[]), \
             patch("app.services.llm_service.llm_service.generate", return_value="reply"):
            await client.post(
                "/api/chat/",
                headers={"Authorization": f"Bearer {advisor_token}"},
                json={"session_id": "s-persist", "message": msg},
            )
    # History should contain 4 messages (2 user + 2 assistant)
    from app.db.crud import get_session_history
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as session:
        history = await get_session_history(session, "s-persist")
    assert len(history) == 4


@pytest.mark.asyncio
async def test_clear_session(seeded_client):
    client, advisor_token, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.retrieve", return_value=[]), \
         patch("app.services.llm_service.llm_service.generate", return_value="ok"):
        await client.post(
            "/api/chat/",
            headers={"Authorization": f"Bearer {advisor_token}"},
            json={"session_id": "s-clear", "message": "hello"},
        )
    resp = await client.delete(
        "/api/chat/s-clear", headers={"Authorization": f"Bearer {advisor_token}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_feedback_endpoint(seeded_client):
    client, advisor_token, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.retrieve", return_value=[]), \
         patch("app.services.llm_service.llm_service.generate", return_value="ok"):
        chat_resp = await client.post(
            "/api/chat/",
            headers={"Authorization": f"Bearer {advisor_token}"},
            json={"session_id": "s-fb", "message": "test"},
        )
    message_id = chat_resp.json()["message"]["id"]
    resp = await client.post(
        f"/api/chat/s-fb/messages/{message_id}/feedback",
        headers={"Authorization": f"Bearer {advisor_token}"},
        json={"rating": 1},
    )
    assert resp.status_code == 204
```

---

**`backend/tests/test_documents.py`:**

```python
import pytest
from unittest.mock import patch, MagicMock
import io


@pytest.mark.asyncio
async def test_advisor_cannot_upload(seeded_client):
    client, advisor_token, *_ = seeded_client
    resp = await client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {advisor_token}"},
        files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_upload(seeded_client):
    client, _, admin_token, *_ = seeded_client
    with patch("app.utils.document_processor.ingest_file", return_value=(["chunk"], [{"source": "test.txt"}], ["id-1"])), \
         patch("app.services.vector_store.vector_store.add_documents"):
        resp = await client.post(
            "/api/documents/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.txt", io.BytesIO(b"some content"), "text/plain")},
        )
    assert resp.status_code == 200
    assert "Ingested 1 chunks" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_can_delete(seeded_client):
    client, _, admin_token, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.delete_document"):
        resp = await client.delete(
            "/api/documents/some_doc.pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_documents(seeded_client):
    client, _, admin_token, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.list_documents", return_value=["doc_a.pdf", "doc_b.txt"]):
        resp = await client.get(
            "/api/documents/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["documents"] == ["doc_a.pdf", "doc_b.txt"]
```

---

**`backend/tests/test_audit.py`:**

```python
import pytest
import hashlib
from unittest.mock import patch
from app.core.config import settings


@pytest.mark.asyncio
async def test_login_writes_audit_log(seeded_client):
    client, *_ = seeded_client
    await client.post("/api/auth/login", json={"username": "advisor1", "password": "password123"})
    from tests.conftest import TestSessionLocal
    from sqlmodel import select
    from app.db.models import AuditLogRecord
    async with TestSessionLocal() as session:
        result = await session.exec(select(AuditLogRecord).where(AuditLogRecord.event_type == "login"))
        logs = result.all()
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_audit_user_id_is_anonymised(seeded_client):
    client, advisor_token, _, user_id, *_ = seeded_client
    with patch("app.services.vector_store.vector_store.retrieve", return_value=[]), \
         patch("app.services.llm_service.llm_service.generate", return_value="ok"):
        await client.post(
            "/api/chat/",
            headers={"Authorization": f"Bearer {advisor_token}"},
            json={"session_id": "s-audit", "message": "test"},
        )
    from tests.conftest import TestSessionLocal
    from sqlmodel import select
    from app.db.models import AuditLogRecord
    async with TestSessionLocal() as session:
        result = await session.exec(select(AuditLogRecord).where(AuditLogRecord.event_type == "chat"))
        log = result.first()
    assert log is not None
    # user_id must NOT be the raw UUID
    assert log.user_id != user_id
    # user_id must be a 32-char hex string (truncated SHA-256)
    assert len(log.user_id) == 32
    assert all(c in "0123456789abcdef" for c in log.user_id)
    # Verify it matches the expected HMAC
    expected = hashlib.sha256(f"{settings.SECRET_KEY}:{user_id}".encode()).hexdigest()[:32]
    assert log.user_id == expected
```

---

**Run tests:**
```bash
cd backend
pytest tests/ -v
```

If tests fail due to missing `ANTHROPIC_API_KEY`, set a dummy value:
```bash
ANTHROPIC_API_KEY=test pytest tests/ -v
```

---

## Frontend Tasks

### F1 · Project Setup
The frontend is a blank Next.js 14 scaffolding with empty `src/` subdirectories. All subdirectory folders exist but contain no files. `package.json` has all required dependencies already (Next.js 14.2.3, React 18, Axios 1.7.2, Tailwind 3.4.1, Lucide React 0.383.0).

*(Detailed specs to be added)*

---

### F2 · API Service Layer
*(Detailed specs to be added)*

---

### F3 · Authentication
*(Detailed specs to be added)*

---

### F4 · Core Chat Components
*(Detailed specs to be added)*

---

### F5 · Session Management
*(Detailed specs to be added)*

---

### F6 · Chat Hook and Main Page
*(Detailed specs to be added)*

---

### F7 · Admin Document Management
*(Detailed specs to be added)*

---

### F8 · Voice Input (Optional)
*(Detailed specs to be added)*

---

## Infrastructure

### I1 · Docker Compose Setup
*(Detailed specs to be added)*

---

### I2 · Environment Variable Hardening
*(Detailed specs to be added)*

---

### I3 · README Update
*(Detailed specs to be added)*

---

## Evaluation & Quality

### E1 · RAG Evaluation Harness
*(Detailed specs to be added)*

---

### E2 · Performance Profiling
*(Detailed specs to be added)*

---

## Suggested Order of Execution

```
Backend (complete these first — each is independent):
  B1  Relevance score filtering       ~30 min
  B9  Update .env.example             ~10 min
  B2  Session title auto-generation   ~30 min
  B3  Session listing API             ~30 min
  B4  Document listing API            ~20 min
  B5  Feedback endpoint               ~1 hr
  B6  Structured Loguru logging       ~1 hr
  B7  User management APIs            ~2 hr
  B8  Session export endpoint         ~30 min
  B10 Test suite                      ~4 hr

Frontend (build in this order — each depends on the previous):
  F1  Project setup                   ~1 hr
  F2  API service layer               ~2 hr
  F3  Authentication (login page)     ~2 hr
  F4  Core chat components            ~4 hr
  F5  Session management              ~2 hr
  F6  Chat hook + main page           ~3 hr
  F7  Admin document management       ~2 hr
  F8  Voice input (optional)          ~2 hr

Infrastructure & Quality:
  I1  Docker Compose                  ~2 hr
  I2  Env var hardening               ~1 hr
  I3  README update                   ~1 hr
  E1  RAG evaluation harness          ~3 hr
  E2  Performance profiling           ~1 hr
```
