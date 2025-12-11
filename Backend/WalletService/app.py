from fastapi import FastAPI, APIRouter, Depends
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse
from WalletService.user.routes import router as auth_router
from WalletService.apikey.apikey_routes import router as apikey_router
from WalletService.userwallet.routes import (
    router as wallet_router,
    public_router as wallet_public_router,
)


auth_scheme = HTTPBearer()
router = APIRouter()
router.include_router(auth_router)
router.include_router(wallet_public_router)
router.include_router(apikey_router, dependencies=[Depends(auth_scheme)])
router.include_router(wallet_router, dependencies=[Depends(auth_scheme)])

__all__ = ["router"]


app = FastAPI(
    title="Wallet Service",
    description="Wallet service for Paystack deposits, transfers, and history, secured with JWT and API keys.",
)

app.include_router(router, prefix="")


@app.get("/", response_class=HTMLResponse)
async def welcome_message():
    return HTMLResponse("<h2>Welcome to wallet service</h2>")
