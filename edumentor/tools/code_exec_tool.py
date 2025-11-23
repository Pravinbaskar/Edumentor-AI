from __future__ import annotations

import math


def code_exec_tool(code: str) -> str:
    """Very small, restricted math execution helper.

    This is *not* safe for arbitrary code; it is intentionally limited and
    intended purely for demo usage.
    """
    allowed_names = {"math": math}
    try:
        result = eval(code, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as exc:  # pragma: no cover - demo friendly
        return f"Error executing code: {exc}"
