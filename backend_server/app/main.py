# Main FastAPI application entry point

import sys
import os

# Add portfolio_lib to Python path
portfolio_lib_path = os.path.join(os.path.dirname(__file__), '../../portfolio_lib')
if portfolio_lib_path not in sys.path:
    sys.path.insert(0, portfolio_lib_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import api_router

app = FastAPI(title="Portfolio Backend Server")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio Backend API!"}

