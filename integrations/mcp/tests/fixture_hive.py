"""Disposable real Hive routes in the application's original Python environment."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ["DEBUG"] = "false"

from fastapi import FastAPI
import uvicorn

import app.api.routes_hive as hive_api
from app.hive import agents
from app.hive.store import HiveStore
from app.llm import LLMRouter, set_router
from tests.test_hive import fake_search, make_handler, routed_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fd", type=int, required=True)
    args = parser.parse_args()
    hive_api._store = HiveStore(os.environ["HIVE_MCP_TEST_DB"])
    agents.default_search = fake_search
    set_router(LLMRouter(routed_config(), mock_handler=make_handler()))
    app = FastAPI()
    app.include_router(hive_api.router)

    @app.get("/health")
    async def health():
        return {"status": "healthy", "fixture": True}

    try:
        uvicorn.run(app, fd=args.fd, host="127.0.0.1", log_level="error", access_log=False)
    finally:
        hive_api._store.db.close()
        set_router(None)


if __name__ == "__main__":
    main()
