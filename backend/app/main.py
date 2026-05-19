from __future__ import annotations

import logging
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import argparse

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.runtime import llm_gateway
from app.settings_bridge import apply_structured_settings, normalize_structured_settings
from app.store import store


app = FastAPI(
    title="Agent Playground API",
    description="Backend service for agent/workflow/trace playground demos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    store.seed_defaults()
    stored_settings = store.get_app_settings_payload()
    if stored_settings:
        normalized = normalize_structured_settings(stored_settings)
        apply_structured_settings(stored_settings, normalized)
        llm_gateway.refresh_client()


app.include_router(router)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Playground Backend")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=8011, help="Bind port (default: 8011)")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        factory=False,
    )
