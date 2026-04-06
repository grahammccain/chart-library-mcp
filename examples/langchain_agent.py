"""
LangChain ReAct Agent with Chart Library MCP

Uses langchain-mcp-adapters to connect to the Chart Library MCP server
and analyze stock chart patterns using a ReAct agent.

Prerequisites:
    pip install langchain-mcp-adapters langchain-openai langgraph

Environment variables:
    OPENAI_API_KEY      Your OpenAI API key
    CHART_LIBRARY_KEY   Your Chart Library API key (https://chartlibrary.io/developers)
"""

import asyncio
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent


async def main():
    # Ensure API keys are set
    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("Set OPENAI_API_KEY environment variable")
    if not os.environ.get("CHART_LIBRARY_KEY"):
        raise EnvironmentError("Set CHART_LIBRARY_KEY environment variable")

    # Connect to Chart Library MCP server via stdio
    async with MultiServerMCPClient(
        {
            "chartlibrary": {
                "command": "chartlibrary-mcp",
                "args": [],
                "env": {
                    "CHART_LIBRARY_KEY": os.environ["CHART_LIBRARY_KEY"],
                },
            }
        }
    ) as client:
        # Load all MCP tools (search_charts, analyze_pattern, get_discover_picks, etc.)
        tools = client.get_tools()
        print(f"Loaded {len(tools)} Chart Library tools:")
        for tool in tools:
            print(f"  - {tool.name}")

        # Create a ReAct agent with GPT-4o
        llm = ChatOpenAI(model="gpt-4o")
        agent = create_react_agent(llm, tools)

        # Ask the agent to analyze a chart pattern
        query = (
            "Analyze NVDA's chart pattern and tell me what historically "
            "happened after similar setups. Include regime-adjusted win rates."
        )
        print(f"\nQuery: {query}\n")

        # Stream the agent's response
        async for chunk in agent.astream(
            {"messages": [{"role": "user", "content": query}]},
        ):
            # Print agent reasoning and tool calls as they happen
            if "agent" in chunk:
                for msg in chunk["agent"]["messages"]:
                    if hasattr(msg, "content") and msg.content:
                        print(msg.content)
            elif "tools" in chunk:
                for msg in chunk["tools"]["messages"]:
                    print(f"\n[Tool: {msg.name}] returned {len(str(msg.content))} chars")


if __name__ == "__main__":
    asyncio.run(main())
