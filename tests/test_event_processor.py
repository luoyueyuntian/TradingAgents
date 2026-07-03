"""Tests for streamed graph event processing."""

from __future__ import annotations

from types import SimpleNamespace

from tradingagents.graph.event_processor import ChunkProcessor


def test_get_messages_and_tools_accepts_dict_tool_calls() -> None:
    processor = ChunkProcessor(["market"])
    message = SimpleNamespace(
        id="msg-1",
        content="Fetching market data",
        tool_calls=[{"name": "get_stock_data", "args": {"ticker": "600941.SS"}}],
    )

    messages, tools = processor.get_messages_and_tools({"messages": [message]})

    assert messages == ["Fetching market data"]
    assert tools == ["get_stock_data"]
