from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import cast, List, Any
from .meddy_reponses import meddy_reply
import logging
import sys


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

        results = []
        for msg in messages:
            parts = msg.get("parts", []) or []
            # accept either 'content' or 'text' inside parts
            text_parts = [p.get("content") or p.get("text") or "" for p in parts]
            text_content = " ".join([t for t in text_parts if t])
            reply = meddy_reply(text_content)
            results.append({"reply": reply})

        return JSONResponse(
            status_code=200,
            content={"jsonrpc": "2.0", "id": body.get("id"), "result": results},
        )

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
