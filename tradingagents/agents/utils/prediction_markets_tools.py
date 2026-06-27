from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_prediction_markets(
    topic: Annotated[
        str,
        "Event topic/keyword, e.g. 'Fed rate cut', 'recession 2026', "
        "'US election', or a sector/company event.",
    ],
    limit: Annotated[int | None, "Max markets to return; omit for a default of 6"] = None,
) -> str:
    """
    Retrieve forward-looking event or market-structure signals from the
    configured ``prediction_markets`` vendor.

    In the default profile this is typically Polymarket. In ``cn_a`` mode the
    same tool name is retained for compatibility, but it returns China
    market-structure signals such as northbound flow, margin financing, and
    broad fund flow.

    Args:
        topic (str): Event keyword(s) to search
        limit (int): Max markets to return; omit for a default of 6

    Returns:
        str: A formatted markdown report of matching forward-looking signals
    """
    return route_to_vendor("get_prediction_markets", topic, limit)
