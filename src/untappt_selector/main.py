import logging
import uuid
from fastapi import FastAPI, Request
from untappt_selector.core.config import get_settings

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)
app = FastAPI(title="UntapptSelector", version="0.1.0")

@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    logger.info("request_id=%s component=api method=%s path=%s status=%s", request_id, request.method, request.url.path, response.status_code)
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}
