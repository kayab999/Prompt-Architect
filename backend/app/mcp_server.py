import logging
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from . import db
from .config import settings
from .mcp_adapter import run_refinement

mcp_logger = logging.getLogger("mcp_server")

# Initialize FastMCP Server
mcp = FastMCP("PromptArchitect")


@mcp.tool()
def list_prompts() -> list[str]:
    try:
        prompts = db.list_prompts(limit=1000)
        return [p["name"] for p in prompts]
    except Exception:
        return []


@mcp.tool()
def get_prompt_by_name(name: str) -> dict:
    try:
        rows = db.list_prompts(limit=1000)
        for row in rows:
            p = db.parse_prompt_row(row)
            if p["template"] == name:
                return p
        return {}
    except Exception:
        return {}


@mcp.tool()
async def refine_prompt(prompt: str, flavor: str = "technical") -> dict:
    """
    Refines a prompt using the Kayab Sovereign Neuro-Symbolic Pipeline.

    Uses the shared mcp_adapter.run_refinement() to ensure MCP and REST
    invoke the exact same pipeline code (no duplication).

    Args:
        prompt: The raw instruction or draft prompt.
        flavor: The ruleset to apply ('technical', 'creative'). Defaults to 'technical'.

    Returns:
        A dictionary containing the refined prompt, cognitive trace, and success status.
    """
    try:
        result = await run_refinement(
            user_input=prompt,
            model="deepseek-r1:1.5b",
            flavor=flavor,
            groq_api_key=settings.GROQ_API_KEY,
            max_iterations=3,
            profile_key="mcp-tool",
        )

        return {
            "refined_content": result["response"],
            "status": result["success"],
            "iterations": result["iterations"],
            "critical_check": result["full_trace"]["success_gate"][
                "critical_rules_status"
            ],
        }
    except Exception as e:
        return {"error": str(e), "status": False}


if __name__ == "__main__":
    mcp_logger.info("Starting MCP Server (stdio transport)...")
    db.init_db()
    mcp.run(transport="stdio")
