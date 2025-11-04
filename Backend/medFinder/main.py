from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .meddy_reponses import meddy_reply
from .schema import UserMessage
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


@app.post("/reply", status_code=200)
def meddy_chat(user_message: UserMessage):
    if not user_message.message.strip():
        raise HTTPException(
            status_code=400, detail="The 'message' field cannot be empty."
        )
    reply = meddy_reply(user_message.message)
    return {"reply": reply}
