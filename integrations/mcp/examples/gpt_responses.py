"""Optional remote-client example. Running this explicitly makes a paid API call.

Requires an OpenAI-enabled client environment and a reachable private MCP endpoint.
This is not part of the server dependencies or the offline test suite.
"""
import os


def main():
    from openai import OpenAI

    response = OpenAI().responses.create(
        model=os.environ["OPENAI_MODEL"],
        input="Inspect Hive service health. Do not submit a research run.",
        tools=[{
            "type": "mcp",
            "server_label": "hive",
            "server_url": os.environ["HIVE_MCP_SERVER_URL"],
            "authorization": os.environ["HIVE_MCP_TOKEN"],
            "allowed_tools": ["hive_health", "hive_get_run"],
            "require_approval": "always",
        }],
    )
    # A tool approval request must be handled by the caller before tool execution.
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
