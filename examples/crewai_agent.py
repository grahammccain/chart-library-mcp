"""
CrewAI Agent with Chart Library MCP

Uses CrewAI to build a small crew with a Market Analyst agent that
pulls data from Chart Library MCP tools to write a morning brief.

Prerequisites:
    pip install crewai crewai-tools

Environment variables:
    OPENAI_API_KEY      Your OpenAI API key
    CHART_LIBRARY_KEY   Your Chart Library API key (https://chartlibrary.io/developers)

Note:
    CrewAI's MCP integration uses MCPServerAdapter to wrap MCP tools
    as CrewAI-compatible tools. See CrewAI docs for the latest API.
"""

import os

from crewai import Agent, Crew, Task
from crewai_tools import MCPServerAdapter


def main():
    # Ensure API keys are set
    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("Set OPENAI_API_KEY environment variable")
    if not os.environ.get("CHART_LIBRARY_KEY"):
        raise EnvironmentError("Set CHART_LIBRARY_KEY environment variable")

    # Connect to Chart Library MCP server and load tools
    with MCPServerAdapter(
        server_params={
            "command": "chartlibrary-mcp",
            "args": [],
            "env": {
                "CHART_LIBRARY_KEY": os.environ["CHART_LIBRARY_KEY"],
            },
        }
    ) as mcp:
        tools = mcp.tools
        print(f"Loaded {len(tools)} Chart Library tools")

        # Define a Market Analyst agent
        analyst = Agent(
            role="Market Analyst",
            goal=(
                "Analyze today's top chart pattern picks and produce a concise "
                "morning report with actionable insights."
            ),
            backstory=(
                "You are a quantitative analyst who specializes in historical "
                "chart pattern analysis. You use Chart Library's database of "
                "24M+ pattern embeddings to find statistically significant "
                "setups and present them in plain English."
            ),
            tools=tools,
            verbose=True,
        )

        # Define the analysis task
        morning_report = Task(
            description=(
                "1. Fetch today's top 5 discover picks using get_discover_picks.\n"
                "2. For each pick, check regime-adjusted win rates with get_regime_win_rates.\n"
                "3. Check overall signal crowding with get_crowding.\n"
                "4. Write a brief morning report (under 300 words) covering:\n"
                "   - Top picks and their historical win rates\n"
                "   - Current market regime context\n"
                "   - Any crowding or degradation warnings\n"
                "   - One-sentence recommendation for each pick"
            ),
            expected_output="A concise morning market brief with data-backed recommendations.",
            agent=analyst,
        )

        # Run the crew
        crew = Crew(
            agents=[analyst],
            tasks=[morning_report],
            verbose=True,
        )

        result = crew.kickoff()
        print("\n--- Morning Report ---")
        print(result)


if __name__ == "__main__":
    main()
