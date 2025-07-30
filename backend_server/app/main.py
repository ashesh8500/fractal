# Main FastAPI application entry point

from fastapi import FastAPI
from backend_server.app.routes import api_router

app = FastAPI(title="Portfolio Backend Server")

# Register API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio Backend API!"}

