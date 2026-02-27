"""TrailBuilder for constructing decision trails from events and records.

This module provides TrailBuilder class that aggregates DecisionRecord and
AgentEvent objects by run_id to construct DecisionTrail instances with
chronological ordering and causal chain reconstruction.
"""

import logging
from typing import Dict, List, Optional

from tradingagents.observability.models.agent_event import AgentEvent
from tradingagents.observability.models.decision_record import DecisionRecord
from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore
from tradingagents.observability.trail.models import DecisionTrail, TrailEdge, TrailNode

logger = logging.getLogger(__name__)


class TrailBuilder:
    """Builds decision trails from stored events and records.

    TrailBuilder orchestrates data retrieval from SQLite and constructs
    timeline/causal graph representations of agent decision flow.

    Example:
        >>> store = SQLiteDecisionStore("./data/observability.db")
        >>> builder = TrailBuilder(store)
        >>> trail = builder.build_trail(run_id="abc123")
        >>> print(f"Trail has {len(trail.nodes)} nodes and {len(trail.edges)} edges")
    """

    def __init__(self, store: SQLiteDecisionStore):
        """Initialize TrailBuilder with storage backend.

        Args:
            store: SQLiteDecisionStore for data retrieval
        """
        self.store = store
        logger.debug("TrailBuilder initialized")

    def build_trail(self, run_id: str) -> DecisionTrail:
        """Build a complete decision trail for a run.

        Aggregates all DecisionRecord and AgentEvent objects for the given
        run_id, constructs chronological timeline, and reconstructs causal
        chain from state transitions.

        Args:
            run_id: Run identifier grouping related events

        Returns:
            DecisionTrail with chronological nodes and causal edges
        """
        logger.debug(f"Building trail for run_id: {run_id}")

        # Fetch all events and records for this run_id
        record_dicts = self.store.get_decision_records_by_run_id(run_id)
        event_dicts = self.store.get_agent_events_by_run_id(run_id)

        # Convert dicts to model objects
        records = [
            DecisionRecord.from_dict(rec) for rec in record_dicts
        ]
        events = [
            AgentEvent.from_dict(evt) for evt in event_dicts
        ]

        # Handle empty runs gracefully
        if not records and not events:
            logger.debug(f"No data found for run_id: {run_id}")
            return DecisionTrail(
                run_id=run_id,
                ticker="UNKNOWN",
                trade_date="2026-01-01",
                nodes=[],
                edges=[],
            )

        # Extract metadata from first record
        first_record = records[0] if records else None
        ticker = first_record.ticker if first_record else "UNKNOWN"
        trade_date = first_record.trade_date if first_record else "2026-01-01"

        # Build nodes and edges
        nodes = self._build_nodes_from_records(records)
        edges = self._build_edges_from_events(events)

        # Enhance edges with causal chain reconstruction
        self._reconstruct_causal_chain(nodes, edges)

        # Determine timeline bounds
        timestamps = [node.timestamp for node in nodes] + [edge.timestamp for edge in edges]
        started_at = min(timestamps) if timestamps else None
        completed_at = max(timestamps) if timestamps else None

        trail = DecisionTrail(
            run_id=run_id,
            ticker=ticker,
            trade_date=trade_date,
            nodes=nodes,
            edges=edges,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.debug(
            f"Trail built: {len(nodes)} nodes, {len(edges)} edges, "
            f"duration={trail.get_duration_seconds():.2f}s"
        )

        return trail

    def _build_nodes_from_records(self, records: List[DecisionRecord]) -> List[TrailNode]:
        """Build TrailNode list from DecisionRecord objects.

        Args:
            records: List of DecisionRecord objects

        Returns:
            List of TrailNode objects
        """
        nodes = []

        for record in records:
            # Truncate reasoning to 200 chars for display
            reasoning_summary = record.reasoning[:200] if record.reasoning else ""

            node = TrailNode(
                agent_name=record.agent_name,
                agent_type=record.agent_type,
                decision=record.decision,
                confidence=record.confidence,
                reasoning=reasoning_summary,
                timestamp=record.timestamp,
                node_type="decision",
            )
            nodes.append(node)

        return nodes

    def _build_edges_from_events(self, events: List[AgentEvent]) -> List[TrailEdge]:
        """Build TrailEdge list from AgentEvent objects.

        Filters for state_transition events and creates causal links.

        Args:
            events: List of AgentEvent objects

        Returns:
            List of TrailEdge objects
        """
        edges = []

        for event in events:
            if event.event_type == "state_transition":
                # Create edge from state transition
                if event.from_state and event.to_state:
                    edge = TrailEdge(
                        source=event.from_state,
                        target=event.to_state,
                        timestamp=event.timestamp,
                        agent_name=event.agent_name,
                        edge_type="state_transition",
                    )
                    edges.append(edge)

        return edges

    def _reconstruct_causal_chain(self, nodes: List[TrailNode], edges: List[TrailEdge]) -> None:
        """Reconstruct causal chain by adding output_influences edges.

        Enhances the edge list with "influences" relationships that show
        how agent outputs influence subsequent agent decisions.

        For each state_transition edge where target is an agent_name in nodes:
        - Find source node with agent_name == edge.source
        - If found, create additional TrailEdge with edge_type="output_influences"

        Args:
            nodes: List of TrailNode objects (modified in-place not needed)
            edges: List of TrailEdge objects (modified in-place)
        """
        # Build agent_name -> node lookup
        agent_nodes = {node.agent_name: node for node in nodes}

        # Add output_influences edges
        for edge in edges:
            if edge.edge_type == "state_transition":
                # Check if target is an agent in our nodes
                if edge.target in agent_nodes:
                    # Check if source is also an agent
                    if edge.source in agent_nodes:
                        # Create output_influences edge
                        influence_edge = TrailEdge(
                            source=edge.source,
                            target=edge.target,
                            timestamp=edge.timestamp,
                            agent_name=edge.agent_name,
                            edge_type="output_influences",
                        )
                        edges.append(influence_edge)
