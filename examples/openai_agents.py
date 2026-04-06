"""
OpenAI Agents SDK with Chart Library MCP

Uses the OpenAI Agents SDK to create an agent that connects to
Chart Library MCP for stock pattern analysis.

Prerequisites:
    pip install openai-agents

Environment variables:
    OPENAI_API_KEY      Your OpenAI API key
    CHART_LIBRARY_KEY   Your Chart Library API key (https://chartlibrary.io/developers)
"""

import asyncio
import os

from agents import Agent, Runner
from agents.mcp import MCPServerStdio


async def main():
    # Ensure API keys are set
    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("Set OPENAI_API_KEY environment variable")
    if not os.environ.get("CHART_LIBRARY_KEY"):
        raise EnvironmentError("Set CHART_LIBRARY_KEY environment variable")

    # Connect to Chart Library MCP server via stdio
    mcp_server = MCPServerStdio(
        name="Chart Library",
        params={
            "command": "chartlibrary-mcp",
            "args": [],
            "env": {
                "CHART_LIBRARY_KEY": os.environ["CHART_LIBRARY_KEY"],
            },
        },
    )

    # Create the agent with Chart Library tools
    agent = Agent(
        name="Market Analyst",
        instructions=(
            "You are a market analyst that uses chart pattern data to provide "
            "insights. Use the Chart Library tools to look up real historical "
            "pattern matches, anomalies, and regime-adjusted statistics. "
            "Always cite the number of matches and time horizon in your analysis."
        ),
        mcp_servers=[mcp_server],
    )

    query = (
        "Check if TSLA is showing any anomalous patterns and what the "
        "regime-adjusted win rates look like. Also check for signal crowding."
    )
    print(f"Query: {query}\n")

    # Run the agent -- the SDK handles MCP connection lifecycle
    result = await Runner.run(agent, query)

    print("--- Agent Response ---")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
