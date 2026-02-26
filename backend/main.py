from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.router import router
from api.voice_router import voice_router

load_dotenv()

app = FastAPI(title="Vini Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(voice_router)


@app.get("/")
async def root():
    return {"status": "Vini is alive"}