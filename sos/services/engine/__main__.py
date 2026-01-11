from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("SOS_ENGINE_HOST", "127.0.0.1")
    port = int(os.getenv("SOS_ENGINE_PORT", "8000"))
    uvicorn.run(
        "sos.services.engine.app:app",
        host=host,
        port=port,
        log_level=os.getenv("SOS_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()

