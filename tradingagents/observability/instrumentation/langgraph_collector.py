"""LangGraph event collector for non-blocking observability.

This module provides LanggraphCollector for capturing execution events
via LangGraph's astream_events API without blocking the trading pipeline.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from langgraph.graph import StateGraph

from tradingagents.observability.models import AgentEvent

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured JSON logger for observability events."""

    @staticmethod
    def _format_log(record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_dict = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra context if present
        if hasattr(record, "event_type"):
            log_dict["event_type"] = record.event_type
        if hasattr(record, "agent_name"):
            log_dict["agent_name"] = record.agent_name
        if hasattr(record, "run_id"):
            log_dict["run_id"] = record.run_id

        return json.dumps(log_dict)

    @classmethod
    def setup_handler(cls, logger_instance: logging.Logger):
        """Configure structured JSON handler for logger."""
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))

        class JSONFilter(logging.Filter):
            def filter(self, record):
                record.msg = cls._format_log(record)
                return True

        handler.addFilter(JSONFilter())
        logger_instance.addHandler(handler)


# Set up structured logging for this module
StructuredLogger.setup_handler(logger)


class LanggraphCollector:
    """Collects LangGraph execution events via astream_events.

    Non-invasive event capture that doesn't modify agent code.
    Uses async streaming to avoid blocking the trading pipeline.

    Example:
        ```python
        collector = LanggraphCollector()

        async for event in collector.collect_events(graph, input_state):
            # Process event as it arrives
            print(f"Event: {event.event_type} from {event.agent_name}")
        ```
    """

    # Events to capture (filtered to avoid information overload)
    RELEVANT_EVENTS = [
        "on_chat_model_start",
        "on_chat_model_end",
        "on_tool_start",
        "on_tool_end",
        "on_chain_start",
        "on_chain_end",
    ]

    def __init__(self, run_id: Optional[str] = None):
        """Initialize the collector.

        Args:
            run_id: Optional run identifier for grouping events.
                    If not provided, generates a UUID.
        """
        self.run_id = run_id or str(uuid.uuid4())
        self.events: List[AgentEvent] = []
        logger.debug(
            f"Initialized LanggraphCollector with run_id: {self.run_id}",
            extra={"run_id": self.run_id}
        )

    async def collect_events(
        self,
        graph: StateGraph,
        input_state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[AgentEvent]:
        """Stream events from graph execution.

        Yields AgentEvent objects as they occur.
        Non-blocking async implementation.

        Args:
            graph: LangGraph StateGraph instance
            input_state: Input state for graph execution
            config: Optional configuration dict for graph execution

        Yields:
            AgentEvent objects as they occur during graph execution

        Example:
            ```python
            async for event in collector.collect_events(graph, state):
                # Process event
                pass
            ```
        """
        config = config or {}
        config.setdefault("run_name", f"observability_{self.run_id}")

        logger.info(
            f"Starting event collection for run_id: {self.run_id}",
            extra={"run_id": self.run_id}
        )

        try:
            # Stream events from graph execution
            async for event in graph.astream_events(
                input_state,
                version="v1",  # Required for astream_events
                config=config,
            ):
                # Filter relevant events (don't capture everything)
                if event["event"] in self.RELEVANT_EVENTS:
                    agent_event = self._parse_langgraph_event(event)
                    if agent_event:
                        self.events.append(agent_event)
                        logger.debug(
                            f"Captured event: {agent_event.event_type} "
                            f"from {agent_event.agent_name or 'unknown'}",
                            extra={
                                "event_type": agent_event.event_type,
                                "agent_name": agent_event.agent_name,
                                "run_id": self.run_id,
                            }
                        )
                        yield agent_event

        except Exception as e:
            logger.error(
                f"Error during event collection: {e}",
                extra={"run_id": self.run_id},
                exc_info=True
            )
            # Don't raise - allow trading pipeline to continue

        logger.info(
            f"Event collection complete for run_id: {self.run_id}. "
            f"Captured {len(self.events)} events.",
            extra={
                "run_id": self.run_id,
                "event_count": len(self.events),
            }
        )

    def _parse_langgraph_event(self, event: Dict[str, Any]) -> Optional[AgentEvent]:
        """Parse LangGraph event into AgentEvent model.

        Args:
            event: Raw event from LangGraph astream_events

        Returns:
            AgentEvent if event is relevant, None otherwise
        """
        try:
            event_type = event["event"]
            event_data = event.get("data", {})
            event_metadata = event.get("metadata", {})

            # Extract agent name from metadata
            agent_name = event_metadata.get("name") or event_metadata.get(
                "langgraph_node"
            )

            # Build base AgentEvent
            agent_event = AgentEvent(
                event_type=event_type.replace("on_", "").replace("_", " "),
                agent_name=agent_name,
                run_id=self.run_id,
                data=event_data,
                metadata=event_metadata,
            )

            # Extract token counts for LLM events
            if event_type == "on_chat_model_end":
                output = event_data.get("output", {})
                if hasattr(output, "response_metadata"):
                    response_metadata = output.response_metadata
                    agent_event.prompt_tokens = response_metadata.get("prompt_tokens")
                    agent_event.completion_tokens = response_metadata.get(
                        "completion_tokens"
                    )
                    agent_event.total_tokens = response_metadata.get("total_tokens")

                # Extract LLM output content
                if hasattr(output, "content"):
                    agent_event.data["output"] = output.content

            # Extract tool information
            elif event_type == "on_tool_start":
                agent_event.tool_name = event_data.get("name")
                agent_event.tool_input = event_data.get("input")

            elif event_type == "on_tool_end":
                agent_event.tool_name = event_data.get("name")
                agent_event.tool_output = event_data.get("output")

            return agent_event

        except Exception as e:
            logger.warning(f"Failed to parse event: {e}", exc_info=True)
            return None

    def get_events(
        self,
        agent_name: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[AgentEvent]:
        """Get collected events with optional filtering.

        Args:
            agent_name: Filter by agent name
            event_type: Filter by event type

        Returns:
            List of matching AgentEvent objects
        """
        filtered_events = self.events

        if agent_name:
            filtered_events = [
                e for e in filtered_events if e.agent_name == agent_name
            ]

        if event_type:
            filtered_events = [
                e for e in filtered_events if e.event_type == event_type
            ]

        return filtered_events

    def get_token_count(self) -> Dict[str, int]:
        """Get total token usage for this run.

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens
        """
        totals = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        for event in self.events:
            if event.prompt_tokens:
                totals["prompt_tokens"] += event.prompt_tokens
            if event.completion_tokens:
                totals["completion_tokens"] += event.completion_tokens
            if event.total_tokens:
                totals["total_tokens"] += event.total_tokens

        return totals

    def clear(self) -> None:
        """Clear collected events."""
        self.events.clear()
        logger.debug(f"Cleared events for run_id: {self.run_id}")
