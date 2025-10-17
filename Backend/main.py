from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from profile.utils import get_cat_fact
from profile.schema import Profile, get_profile
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HNG Profile API",
    description="Returns user profile and a random cat fact.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
def entry_point():
    return {"message": "Welcome to my HNG API endpoint stack"}


@app.get('/health')
def health_check():
    return {"health": "All good, 100%"}


@app.get('/fact')
def get_cat_fact_ninja():
    data = get_cat_fact()
    return data


@app.get('/me')
def me(profile: Profile = Depends(get_profile)):
    if profile is None:
        logger.warning("Profile not found")
        return Profile(
            status="error",
            user={
                "email": "unknown@example.com",
                "name": "Unknown",
                "stack": "None"
            },
            timestamp=datetime.now(timezone.utc),
            fact="No cat fact available."
        )
    logger.info("GET /me called successfully")
    return profile
