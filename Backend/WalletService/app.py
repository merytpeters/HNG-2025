from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse
from user.routes import router as auth_router
from apikey.apikey_routes import router as apikey_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(apikey_router)

__all__ = ["router"]


app = FastAPI(
    title="Wallet Service",
    description="Wallet service for Paystack deposits, transfers, and history, secured with JWT and API keys.",
)

app.include_router(router, prefix="")


@app.get("/", response_class=HTMLResponse)
async def welcome_message():
    return HTMLResponse("<h2>Welcome to wallet service</h2>")
