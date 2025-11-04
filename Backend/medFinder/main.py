from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import cast, List, Any, Optional
from .meddy_reponses import meddy_reply
from .schema import (
    JSONRPCRequest,
    JSONRPCResponse,
    TaskResult,
    TaskStatus,
    A2AMessage,
    MessagePart,
)
import logging
import sys
from uuid import uuid4


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)
logger.propagate = True

app = FastAPI(
    title="MedFinder",
    description="Helps users find the right healthcare facilities near them based on their need and location, using verified public data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def entry_point():
    return {
        "message": "Hi, I'm Meddy 👋, your smart healthcare assistant!",
        "next_step": "You can tell me what service you need and where. For example: 'I need a pharmacy in Yaba.'",
        "tips": [
            "You can ask for hospitals, clinics, pharmacies, dentists, or labs.",
            "Provide the location (city, state and country) for more accurate results.",
        ],
    }


@app.post("/a2a/meddy")
async def a2a_endpoint(request: Request):
    """Handle incoming JSON-RPC requests for Meddy.

    This endpoint intentionally uses the raw request dict instead of strict
    pydantic models for the incoming body to be tolerant of variations in
    `parts` (e.g., fields named `content` vs `text`). It returns a JSON-RPC
    compatible dict with the meddy replies.
    """
    body = None
    try:
        body = await request.json()

        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc must be '2.0' and id is required",
                    },
                },
            )

        # Attempt to validate/parse into the JSONRPCRequest model
        try:
            rpc_request = JSONRPCRequest(**body)
        except Exception:
            # Fall back to raw parsing for robustness
            method = body.get("method")
            params = body.get("params", {}) or {}
            messages: List[Any] = []
            if method == "message/send":
                msg = params.get("message")
                if msg:
                    messages = [msg]
                else:
                    messages = params.get("messages", []) or []
            elif method == "execute":
                messages = params.get("messages", []) or []
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {"code": -32601, "message": "Method not found"},
                    },
                )

            # extract text content from raw messages
            replies: List[str] = []
            for msg in messages:
                parts = msg.get("parts", []) or []
                text_parts = [p.get("content") or p.get("text") or "" for p in parts]
                text_content = " ".join([t for t in text_parts if t])
                replies.append(meddy_reply(text_content))

            # Return simple result array when we couldn't parse into the model
            return JSONResponse(
                status_code=200,
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": [{"reply": r} for r in replies],
                },
            )

        # If parsing succeeded, use structured models to build a TaskResult
        messages: List[A2AMessage] = []
        context_id: Optional[str] = None
        task_id: Optional[str] = None

        if rpc_request.method == "message/send":
            messages = [rpc_request.params.message]
            config = rpc_request.params.configuration
        elif rpc_request.method == "execute":
            messages = rpc_request.params.messages
            # Execute params may include context/task ids
            if hasattr(rpc_request.params, "contextId"):
                context_id = getattr(rpc_request.params, "contextId")
            if hasattr(rpc_request.params, "taskId"):
                task_id = getattr(rpc_request.params, "taskId")

        # Use last user message
        user_message = messages[-1] if messages else None

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": rpc_request.id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: no message provided",
                    },
                },
            )

        # Extract text from A2AMessage parts
        text_content = ""
        for part in user_message.parts:
            if part.kind == "text" and part.text:
                text_content = part.text
                break

        reply_text = meddy_reply(text_content)

        # Build response message and TaskResult
        ctx_id = context_id or str(uuid4())
        t_id = task_id or str(uuid4())

        # Construct message part using alias keys to be compatible with pydantic config
        response_part = MessagePart(**{"type": "text", "content": reply_text})
        response_message = A2AMessage(
            role="agent",
            parts=[response_part],
            taskId=t_id,
        )

        status = TaskStatus(state="completed", message=response_message)

        result = TaskResult(
            id=t_id,
            contextId=ctx_id,
            status=status,
            artifacts=[],
            history=messages,
        )

        response = JSONRPCResponse(id=rpc_request.id, result=result)
        return response.dict()

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": (
                    body.get("id")
                    if ("body" in locals() and isinstance(body, dict))
                    else None
                ),
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)},
                },
            },
        )
