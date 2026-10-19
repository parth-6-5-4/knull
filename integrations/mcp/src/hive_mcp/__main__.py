"""Launch Hive MCP with isolated dependencies; protocol output owns stdout."""
import argparse
import os

import uvicorn

from hive_mcp.server import create_http_app, create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP adapter for a separately running local Hive API")
    parser.add_argument("--api-url", default=os.environ.get("HIVE_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP MCP loopback binding")
    parser.add_argument("--port", type=int, default=8765, help="HTTP MCP port")
    args = parser.parse_args()
    try:
        server = create_server(args.api_url)
        if args.transport == "streamable-http":
            if not 1 <= args.port <= 65535:
                raise ValueError("HTTP MCP port must be between 1 and 65535")
            app = create_http_app(server, os.environ.get("HIVE_MCP_TOKEN", ""), args.host)
    except ValueError as exc:
        parser.error(str(exc))
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
