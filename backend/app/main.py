"""Smarter Health AI — FastAPI backend for MedGemma.

Run:  ./run.sh      Docs: http://localhost:8000/docs
"""
import base64
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .db import DatabaseUnavailable, DoctorRepository
from .doctors import Doctor, rank_doctors
from .medgemma_client import LLMError, LLMUnavailable, MedGemmaClient
from .prompts import DEFAULT_IMAGE_QUESTION, SYSTEM_PROMPT
from .safety import EMERGENCY_NOTICE, detect_emergency
from .schemas import ChatRequest, ChatResponse, HealthResponse, ImageInput, Message, RecommendRequest
from .triage import SpecialtyPick, TriageResult, normalize_specialty, triage

settings = get_settings()
# Never log message content or images: they may contain patient health information.
log = logging.getLogger("smarter_health")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = MedGemmaClient(settings.llm_base_url, settings.llm_model, settings.llm_api_key, settings.llm_timeout_s)
    app.state.repo = DoctorRepository(settings.database_url)
    log.info("Using model %s at %s", settings.llm_model, settings.llm_base_url)
    if await app.state.repo.connect():  # API still starts without the DB; doctor routes return 503
        revision = await app.state.repo.migration_revision()
        if revision is None:
            log.error("Database has no schema. Run: .venv/bin/alembic upgrade head")
        else:
            log.info("Doctor database connected at migration %s (%d active doctors)",
                     revision, (await app.state.repo.meta())["count"])
    yield
    await app.state.llm.aclose()
    await app.state.repo.close()


app = FastAPI(
    title="Smarter Health AI API",
    version="1.0.0",
    description="Medical assistant API powered by MedGemma. Not a substitute for professional medical advice.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


# ---------- dependencies & helpers ----------
def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if settings.app_api_key and x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def get_llm(request: Request) -> MedGemmaClient:
    return request.app.state.llm


def get_repo(request: Request) -> DoctorRepository:
    return request.app.state.repo


def require_admin_key(x_admin_key: Optional[str] = Header(default=None)) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Admin API disabled: set ADMIN_API_KEY in backend/.env")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key")


def to_http_error(e: Exception) -> HTTPException:
    if isinstance(e, LLMUnavailable):
        return HTTPException(status_code=503, detail=f"{e}. Is Ollama running? (brew services start ollama)")
    return HTTPException(status_code=502, detail=str(e))


def validate_images(messages: list[Message]) -> None:
    max_bytes = int(settings.max_image_mb * 1024 * 1024)
    for m in messages:
        if len(m.images) > settings.max_images_per_message:
            raise HTTPException(422, f"At most {settings.max_images_per_message} images per message")
        for im in m.images:
            if im.approx_bytes > max_bytes:
                raise HTTPException(413, f"Image larger than {settings.max_image_mb} MB")


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# ---------- routes ----------
@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health(llm: MedGemmaClient = Depends(get_llm), repo: DoctorRepository = Depends(get_repo)):
    try:
        models = await llm.list_models()
        reachable = True
    except (LLMUnavailable, LLMError):
        models, reachable = [], False
    available = any(m == settings.llm_model or m.startswith(settings.llm_model + ":") for m in models)
    db_ok = await repo.ping()
    return HealthResponse(
        status="ok" if reachable and available and db_ok else "degraded",
        database_reachable=db_ok,
        model=settings.llm_model,
        model_server=settings.llm_base_url,
        model_server_reachable=reachable,
        model_available=available,
    )


@app.get("/api/models", dependencies=[Depends(require_api_key)], tags=["system"])
async def models(llm: MedGemmaClient = Depends(get_llm)):
    try:
        return {"default": settings.llm_model, "models": await llm.list_models()}
    except (LLMUnavailable, LLMError) as e:
        raise to_http_error(e)


@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)], tags=["chat"])
async def chat(req: ChatRequest, llm: MedGemmaClient = Depends(get_llm)):
    """Full reply in one response. Good for mobile apps and server-to-server calls."""
    validate_images(req.messages)
    emergency = detect_emergency(req.messages[-1].content)
    started = time.perf_counter()
    try:
        result = await llm.chat(
            MedGemmaClient.build_messages(SYSTEM_PROMPT, req.messages),
            temperature=req.temperature if req.temperature is not None else settings.default_temperature,
            max_tokens=req.max_tokens or settings.default_max_tokens,
            model=req.model,
        )
    except (LLMUnavailable, LLMError) as e:
        raise to_http_error(e)
    log.info("chat ok msgs=%d emergency=%s %.1fs", len(req.messages), emergency, time.perf_counter() - started)
    return ChatResponse(
        reply=result["content"],
        model=result["model"],
        emergency=emergency,
        emergency_notice=EMERGENCY_NOTICE if emergency else None,
        usage=result["usage"],
    )


@app.post("/api/chat/stream", dependencies=[Depends(require_api_key)], tags=["chat"])
async def chat_stream(req: ChatRequest, llm: MedGemmaClient = Depends(get_llm)):
    """Server-Sent Events stream. Each event is `data: {json}` with a `type` field:
    `meta` (first: model + emergency flag) → `delta` (text chunks) → `done` (stats) or `error`."""
    validate_images(req.messages)
    emergency = detect_emergency(req.messages[-1].content)
    model = req.model or settings.llm_model
    messages = MedGemmaClient.build_messages(SYSTEM_PROMPT, req.messages)

    async def events():
        yield sse({"type": "meta", "model": model, "emergency": emergency,
                   "emergency_notice": EMERGENCY_NOTICE if emergency else None})
        started, first_token, usage, chars = time.perf_counter(), None, None, 0
        try:
            async for ev in llm.stream(
                messages,
                temperature=req.temperature if req.temperature is not None else settings.default_temperature,
                max_tokens=req.max_tokens or settings.default_max_tokens,
                model=req.model,
            ):
                if "delta" in ev:
                    first_token = first_token or time.perf_counter()
                    chars += len(ev["delta"])
                    yield sse({"type": "delta", "text": ev["delta"]})
                elif "usage" in ev:
                    usage = ev["usage"]
        except (LLMUnavailable, LLMError) as e:
            log.warning("stream failed: %s", e)
            yield sse({"type": "error", "message": str(to_http_error(e).detail)})
            return
        end = time.perf_counter()
        elapsed = end - started
        gen_time = end - first_token if first_token else 0
        n = (usage or {}).get("completion_tokens") or 0
        tps = round((n - 1) / gen_time, 1) if n > 1 and gen_time > 0 else None  # generation speed, excl. prompt/image processing
        ttft = round(first_token - started, 2) if first_token else None
        log.info("stream ok msgs=%d emergency=%s chars=%d %.1fs", len(req.messages), emergency, chars, elapsed)
        yield sse({"type": "done", "usage": usage, "elapsed_s": round(elapsed, 2),
                   "time_to_first_token_s": ttft, "tokens_per_s": tps})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/analyze-image", response_model=ChatResponse, dependencies=[Depends(require_api_key)], tags=["imaging"])
async def analyze_image(
    file: UploadFile = File(..., description="X-ray, CT/MRI slice, skin photo, report scan…"),
    question: str = Form(DEFAULT_IMAGE_QUESTION),
    llm: MedGemmaClient = Depends(get_llm),
):
    """Upload one medical image (multipart/form-data) and get MedGemma's analysis."""
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "File must be an image")
    raw = await file.read()
    if len(raw) > settings.max_image_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {settings.max_image_mb} MB")
    req = ChatRequest(messages=[Message(
        role="user",
        content=question,
        images=[ImageInput(mime_type=file.content_type, data=base64.b64encode(raw).decode())],
    )])
    return await chat(req, llm)


# ---------- doctors ----------
@app.exception_handler(DatabaseUnavailable)
async def db_unavailable(_: Request, exc: DatabaseUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/api/doctors/meta", dependencies=[Depends(require_api_key)], tags=["doctors"])
async def doctors_meta(repo: DoctorRepository = Depends(get_repo)):
    """Filter options for the UI: specialties, cities and languages of active doctors."""
    return await repo.meta()


@app.get("/api/doctors", response_model=list[Doctor], dependencies=[Depends(require_api_key)], tags=["doctors"])
async def list_doctors(
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    repo: DoctorRepository = Depends(get_repo),
):
    """Browse / search active doctors (by specialty, city, or name / hospital / condition text)."""
    return await repo.search(specialty=specialty, city=city, q=q, limit=max(1, min(limit, 200)))


@app.get("/api/doctors/{doctor_id}", response_model=Doctor, dependencies=[Depends(require_api_key)], tags=["doctors"])
async def get_doctor(doctor_id: str, repo: DoctorRepository = Depends(get_repo)):
    doctor = await repo.get(doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    return doctor


@app.put("/api/doctors/{doctor_id}", response_model=Doctor, dependencies=[Depends(require_admin_key)], tags=["doctors admin"])
async def upsert_doctor(doctor_id: str, doctor: Doctor, repo: DoctorRepository = Depends(get_repo)):
    """Create or update a doctor (admin). Requires header X-Admin-Key."""
    if doctor.id != doctor_id:
        raise HTTPException(422, "id in body must match the URL")
    return await repo.upsert(doctor)


@app.delete("/api/doctors/{doctor_id}", status_code=204, dependencies=[Depends(require_admin_key)], tags=["doctors admin"])
async def delete_doctor(doctor_id: str, repo: DoctorRepository = Depends(get_repo)):
    """Deactivate a doctor (soft delete: kept in the database, never suggested). Requires X-Admin-Key."""
    if not await repo.deactivate(doctor_id):
        raise HTTPException(404, "Doctor not found")


@app.post("/api/recommend-doctors", dependencies=[Depends(require_api_key)], tags=["doctors"])
async def recommend_doctors(
    req: RecommendRequest,
    llm: MedGemmaClient = Depends(get_llm),
    repo: DoctorRepository = Depends(get_repo),
):
    """Suggest doctors from the database for a conversation.

    1. MedGemma triages the conversation into specialties that exist in the database
       (keyword fallback if the model is unavailable).
    2. Matching doctors are fetched from PostgreSQL and ranked deterministically: specialty,
       conditions treated, rating, experience, city, language and availability.
    """
    validate_images(req.messages)
    started = time.perf_counter()
    allowed = await repo.specialties()
    if not allowed:
        raise HTTPException(503, "The doctor directory is empty. Import doctors with scripts/import_doctors.py")
    reused = [n for n in (normalize_specialty(s, allowed) for s in (req.specialties or [])) if n]
    if reused:  # filters changed only: re-rank without calling the model
        result = TriageResult(specialties=[SpecialtyPick(name=n) for n in dict.fromkeys(reused)],
                              conditions=req.conditions, urgency=req.urgency or "routine", source="ai")
        if any(detect_emergency(m.content) for m in req.messages if m.role == "user"):
            result.urgency = "emergency"
    else:
        result = await triage(llm, req.messages, allowed)
    names = [s.name for s in result.specialties]
    candidates = await repo.candidates(names, teleconsult_only=req.teleconsult_only)
    doctors = rank_doctors(candidates, names, result.conditions, city=req.city, language=req.language,
                           teleconsult_only=req.teleconsult_only, limit=req.limit)
    log.info("recommend source=%s specialties=%s urgency=%s results=%d %.1fs", result.source,
             names, result.urgency, len(doctors), time.perf_counter() - started)
    return {
        **result.model_dump(),
        "emergency_notice": EMERGENCY_NOTICE if result.urgency == "emergency" else None,
        "filters": {"city": req.city, "language": req.language, "teleconsult_only": req.teleconsult_only},
        "doctors": [d.model_dump() for d in doctors],
    }
