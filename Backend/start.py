# start.py
import os
from uvicorn import run
from main import app

port = int(os.environ.get("PORT", 80))
run(app, host="0.0.0.0", port=port)
