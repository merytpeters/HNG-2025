from pydantic import BaseModel
from typing import Any, Dict, Optional


class JSONRPCMessage(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Optional[Dict[str, Any]] = {}
