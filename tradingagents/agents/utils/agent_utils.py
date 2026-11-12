"""Compatibility exports for tools and prompt context."""
from tradingagents.agents.context import *  # noqa: F403 - legacy public re-exports
from tradingagents.agents.tools import *  # noqa: F403 - legacy public re-exports


def create_msg_delete():
    from langchain_core.messages import RemoveMessage
    return lambda state: {"messages": [RemoveMessage(id=m.id) for m in state["messages"]]}
