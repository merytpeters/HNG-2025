from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import cast, List, Any, Optional
from .meddy_reponses import meddy_reply
import logging
import sys
from uuid import uuid4
from datetime import datetime, timezone
from .schema import JSONRPCMessage


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


@app.post("/a2a/{agentId}")
async def a2a_endpoint(agentId: str, body: JSONRPCMessage):
    """Telex-compatible endpoint for Meddy location finder."""
    try:
        body_dict = body.dict()

        if body_dict.get("jsonrpc") != "2.0" or "id" not in body_dict:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body_dict.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc must be '2.0' and id is required",
                    },
                },
            )

        method = body_dict.get("method")
        params = body_dict.get("params", {}) or {}
        messages: List[Any] = []

        if method == "message/send":
            msg = params.get("message")
            messages = [msg] if msg else params.get("messages", []) or []
        elif method == "execute":
            messages = params.get("messages", []) or []
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body_dict.get("id"),
                    "error": {"code": -32601, "message": "Method not found"},
                },
            )

        user_message = messages[-1] if messages else None
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body_dict.get("id"),
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: no message provided",
                    },
                },
            )

        parts = user_message.get("parts", []) or []
        text_parts = [
            p.get("content") or p.get("text")
            for p in parts
            if p.get("content") or p.get("text")
        ]
        text_content = " ".join(text_parts)

        reply_text = await meddy_reply(text_content)

        task_id = str(uuid4())
        message_id = str(uuid4())
        artifact_id = str(uuid4())
        context_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        workflow_id = (
            params.get("workflowId")
            or params.get("workflow_id")
            or user_message.get("workflowId")
            or user_message.get("workflow_id")
            or context_id
        )

        print(f"Using workflow_id: {workflow_id}")

        response = {
            "jsonrpc": "2.0",
            "id": body_dict.get("id"),
            "result": {
                "id": task_id,
                "contextId": context_id,
                "workflowId": workflow_id,
                "status": {
                    "state": "completed" if reply_text else "input-required",
                    "timestamp": timestamp,
                    "message": {
                        "messageId": message_id,
                        "role": "agent",
                        "parts": [{"kind": "text", "text": reply_text}],
                        "kind": "message",
                        "taskId": task_id,
                    },
                },
                "artifacts": [
                    {
                        "artifactId": artifact_id,
                        "name": "service-list",
                        "parts": [{"kind": "text", "text": reply_text}],
                    }
                ],
                "history": messages,
                "kind": "task",
            },
        }

        return JSONResponse(status_code=200, content=response)

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": getattr(body, "id", None),
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)},
                },
            },
        )
