#!/usr/bin/env python3
"""
Game Server Deployments Management Dashboard
Main application module that initializes FastAPI and serves the web application.
"""
import logging
import os
import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import router as api_router
from app.kubernetes import get_k8s_client

# Configure logging - this is important to see our debug messages
logging.basicConfig(
    level=logging.DEB,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Initialize FastAPI app
app = FastAPI(
    title="Game Server Dashboard",
    description="Dashboard for managing game server deployments in Kubernetes",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Include API router
app.include_router(api_router.router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request
):
    """Render the main dashboard page."""
    try:
        # Create the k8s_client explicitly by passing the request
        k8s_client = await get_k8s_client(request)
        games = await k8s_client.get_games()
        return templates.TemplateResponse(
            "index.html", {"request": request, "games": games}
        )
    except Exception as e:
        logging.error(f"Error rendering dashboard: {e}", exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": str(e),
                "error_title": "Error retrieving deployments",
            },
            status_code=500,
        )


@app.get("/game/{game_name}", response_class=HTMLResponse)
async def game_detail(
    request: Request,
    game_name: str,
):
    """Render the game detail page with instance information."""
    try:
        # Create the k8s_client explicitly by passing the request
        k8s_client = await get_k8s_client(request)
        instances = await k8s_client.get_game_instances(game_name)
        return templates.TemplateResponse(
            "game.html",
            {"request": request, "game_name": game_name, "instances": instances},
        )
    except Exception as e:
        logging.error(f"Error rendering game detail: {e}", exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": str(e),
                "error_title": f"Error retrieving game {game_name}",
            },
            status_code=500,
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for the application."""
    return {"status": "ok"}


def start():
    """Start the application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info",  # Set Uvicorn's log level to info
    )


if __name__ == "__main__":
    start()
