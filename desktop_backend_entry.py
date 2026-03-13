from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("MCUBE_BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("MCUBE_BACKEND_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()

