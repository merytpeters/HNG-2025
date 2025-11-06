
# Meddy / MedFinder

Meddy (also referred to as MedFinder in this repository) is a lightweight FastAPI service that provides two main capabilities:

- A2A (agent-to-agent) JSON-RPC style message handling used by Telex-like agents (endpoint: POST /a2a/{agentId}).
- A small location / place finder that geocodes free-text place names and queries OpenStreetMap (Overpass) for nearby services (pharmacies, clinics, hospitals).

This README documents the architecture, how to run the service locally, request/response shapes, debugging tips, and developer notes.

## Table of contents

- Project overview
- Repository layout
- Requirements
- Quick start (run locally)
- Endpoints and examples
	- A2A JSON-RPC (/a2a/{agentId})
- Location finder (CLI & internals)
- Contributing

## Project overview

Meddy is intended to act as a conversational agent backend that can:

- Receive JSON-RPC style messages from an upstream agent platform (Telex, or other agent routers).
- Parse and validate incoming messages using Pydantic models.
- Extract natural-language queries asking for nearby medical services, geocode them, query OSM, and return structured results.

Design goals:

- Be robust to slightly different JSON shapes from different agent platforms.
- Produce deterministic, testable outputs suitable for unit tests.
- Log raw inbound payloads for forensic debugging when upstream systems report DB integrity errors.

## Repository layout (key files)

- `main.py` — FastAPI application with endpoints and middleware. Contains the A2A handler (`/a2a/{agentId}`)
- `schema.py` — Pydantic models used to validate JSON-RPC messages and registration payloads (e.g., `JSONRPCMessage`, `Message`, `MessagePart`). Models are written to be strict about required fields and accept a few common alias shapes.
- `location_finder.py` — Utilities to geocode a free-text place name (via Nominatim) and query Overpass for nearby services. Can be run as a script to reproduce location lookups.
- `meddy_reponses.py` — Helper functions that format Meddy replies and task result payload structure expected by the caller.

## Requirements

This project uses Python 3.11+ and FastAPI. Dependencies (used during development) are available in the repository's top-level `Backend/requirements.txt` file — install into a virtual environment.

Example (zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r Backend/requirements.txt
```

## Quick start (run locally)

1. Activate your virtual environment (see Requirements).
2. From the `Backend/` folder, run the FastAPI app. Example using Uvicorn (development):

```bash
cd Backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

3. The app will expose endpoints such as:

- POST http://127.0.0.1:8000/a2a/{agentId}

Use the `/docs` path (Swagger UI) to view the OpenAPI docs when the server is running: http://127.0.0.1:8000/docs

## Endpoints and examples

### 1) A2A JSON-RPC: POST /a2a/{agentId}

This endpoint expects a JSON-RPC 2.0-like payload. The service validates requests and returns a structured `TaskResult` object (task id, status, message, artifacts, etc.).

Required shape (minimal example):

```json
{
	"jsonrpc": "2.0",
	"id": "some-request-id",
	"method": "message/send",
	"params": {
		"message": {
			"role": "user",
			"parts": [
				{ "type": "text", "content": "Find pharmacies near Warri" }
			]
		}
	}
}
```

Example curl (replace `meddy` with any agentId string):

```bash
curl -X POST http://127.0.0.1:8000/a2a/meddy \
	-H 'Content-Type: application/json' \
	-d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"type":"text","content":"Find pharmacies near Warri"}]}}}'
```

Behavior notes:

- The service validates `jsonrpc == "2.0"` and requires `id` and `params.message`.
- Messages are split into `parts` and each part is validated for a text-like field (`content` or `text`). The `MessagePart` model provides helper logic to extract user text regardless of aliases.
- If the incoming message appears to be a location query (pharmacy/hospital/clinic), the handler will call into the `location_finder` to geocode and query OSM. External requests to Nominatim and Overpass can be slow or rate-limited; the code has basic error handling and returns a friendly failure message if the external services fail.

JSON-RPC error responses are returned for invalid requests with appropriate JSON-RPC error codes (for example `-32600` invalid request, `-32602` invalid params, `-32601` method not found).

## Location finder (internals & CLI)

`location_finder.py` contains the logic to convert a free-text place into coordinates (using Nominatim) and then query Overpass for nearby amenities. It can be invoked as a script for quick debugging.

Example (from the `Backend/` directory):

```bash
python -m medFinder.location_finder "Lagos"
python Backend/medFinder/location_finder.py Lagos
```

Important notes:

- External dependencies: Nominatim (OpenStreetMap) for geocoding, and Overpass API for place queries. Both services may throttle or return intermittent HTTP 5xx errors. The code catches such errors and returns a friendly message rather than raising an exception to the caller.
- For stable tests, you should mock these external HTTP calls.

How to run a quick programmatic test (example using Python REPL / script):

```python
from fastapi.testclient import TestClient
from medFinder import main

client = TestClient(main.app)
resp = client.post('/a2a/meddy', json={
		'jsonrpc': '2.0',
		'id': '1',
		'method': 'message/send',
		'params': { 'message': { 'role': 'user', 'parts': [{ 'type': 'text', 'content': 'Find pharmacies near Warri' }] } }
})
print(resp.status_code, resp.json())
```

For CI or reproducible unit tests you should mock Nominatim and Overpass responses (for example with `responses` or `httpx_mock`).


## Troubleshooting

- 404 when calling `/a2a/{agentId}` — ensure you are hitting the correct prefix/host/port and that UVicorn is running with the correct working directory. If you are running behind a reverse proxy that sets a path prefix, confirm the prefix is preserved or the service is mounted accordingly.
- Missing results from location queries — check whether Nominatim returned coordinates for the place name, then ensure Overpass query returned amenities.

## Contributing

Feel free to open issues or PRs. Keep changes small and add tests for behavioral changes. If you update Pydantic models or validation behavior, update the example requests in this README and add unit tests illustrating expected request/response shapes.

