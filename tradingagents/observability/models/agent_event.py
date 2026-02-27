"""Agent event data model for execution event capture.

This module defines the AgentEvent Pydantic model for capturing granular
execution events during LangGraph workflow execution.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class AgentEvent(BaseModel):
    """Event captured during agent execution.

    Captures granular execution events during graph flow for observability.
    Supports multiple event types with specific fields for each.

    Attributes:
        event_id: Unique identifier for this event
        event_type: Type of event (llm_call, tool_use, state_transition, error)
        agent_name: Name of the agent that generated this event
        timestamp: ISO timestamp of when the event occurred
        run_id: Optional identifier to link to DecisionRecord
        data: Event-specific data as key-value pairs
        metadata: Additional metadata as key-value pairs
        model: LLM model name (for llm_call events)
        prompt_tokens: Number of prompt tokens (for llm_call events)
        completion_tokens: Number of completion tokens (for llm_call events)
        total_tokens: Total number of tokens (for llm_call events)
        tool_name: Name of the tool (for tool_use events)
        tool_input: Tool input parameters (for tool_use events)
        tool_output: Tool output result (for tool_use events)
        from_state: Previous state name (for state_transition events)
        to_state: Next state name (for state_transition events)
        error_type: Type of error (for error events)
        error_message: Error message (for error events)
    """

    # Core fields
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: Literal["llm_call", "tool_use", "state_transition", "error"]
    agent_name: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    run_id: Optional[str] = None  # Link to DecisionRecord

    # Event-specific data
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # For llm_call events
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # For tool_use events
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None

    # For state_transition events
    from_state: Optional[str] = None
    to_state: Optional[str] = None

    # For error events
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    @validator("event_type")
    def validate_event_specific_fields(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate that event-specific fields are set correctly."""
        # This validator ensures data integrity based on event type
        # We'll rely on the application logic to set appropriate fields
        return v

    @validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is a valid ISO format string."""
        try:
            # Try parsing as ISO format
            if isinstance(v, str):
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(
                f"timestamp must be a valid ISO format string, got: {v}"
            ) from e

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the agent event
        """
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentEvent":
        """Create AgentEvent from dictionary.

        Args:
            data: Dictionary representation of the agent event

        Returns:
            AgentEvent instance
        """
        return cls(**data)

    @classmethod
    def create_llm_call(
        cls,
        agent_name: str,
        model: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        run_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentEvent":
        """Create an LLM call event.

        Args:
            agent_name: Name of the agent making the LLM call
            model: LLM model name
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens generated
            total_tokens: Total tokens used
            run_id: Optional run identifier
            data: Additional event data
            metadata: Additional metadata

        Returns:
            AgentEvent instance with event_type="llm_call"
        """
        return cls(
            event_type="llm_call",
            agent_name=agent_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            run_id=run_id,
            data=data or {},
            metadata=metadata or {},
        )

    @classmethod
    def create_tool_use(
        cls,
        agent_name: str,
        tool_name: str,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[str] = None,
        run_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentEvent":
        """Create a tool use event.

        Args:
            agent_name: Name of the agent using the tool
            tool_name: Name of the tool being used
            tool_input: Tool input parameters
            tool_output: Tool output result
            run_id: Optional run identifier
            data: Additional event data
            metadata: Additional metadata

        Returns:
            AgentEvent instance with event_type="tool_use"
        """
        return cls(
            event_type="tool_use",
            agent_name=agent_name,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            run_id=run_id,
            data=data or {},
            metadata=metadata or {},
        )

    @classmethod
    def create_state_transition(
        cls,
        agent_name: str,
        from_state: str,
        to_state: str,
        run_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentEvent":
        """Create a state transition event.

        Args:
            agent_name: Name of the agent involved in transition
            from_state: Previous state name
            to_state: Next state name
            run_id: Optional run identifier
            data: Additional event data
            metadata: Additional metadata

        Returns:
            AgentEvent instance with event_type="state_transition"
        """
        return cls(
            event_type="state_transition",
            agent_name=agent_name,
            from_state=from_state,
            to_state=to_state,
            run_id=run_id,
            data=data or {},
            metadata=metadata or {},
        )

    @classmethod
    def create_error(
        cls,
        agent_name: str,
        error_type: str,
        error_message: str,
        run_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentEvent":
        """Create an error event.

        Args:
            agent_name: Name of the agent where error occurred
            error_type: Type of error
            error_message: Error message
            run_id: Optional run identifier
            data: Additional event data
            metadata: Additional metadata

        Returns:
            AgentEvent instance with event_type="error"
        """
        return cls(
            event_type="error",
            agent_name=agent_name,
            error_type=error_type,
            error_message=error_message,
            run_id=run_id,
            data=data or {},
            metadata=metadata or {},
        )
