from __future__ import annotations


async def search_tool(query: str) -> str:
    """Stub search tool.

    In a real deployment you would call an external search API here.
    For the demo we just echo the query.
    """
    return f"(Search results for: {query})"
