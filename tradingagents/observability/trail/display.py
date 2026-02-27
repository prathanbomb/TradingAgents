"""Text-based decision trail visualization for timeline and causal chain display.

This module provides TrailRenderer class for formatting and displaying decision
trails in terminal/CLI environments without requiring graphical UI.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from tradingagents.observability.trail.models import DecisionTrail, TrailEdge, TrailNode

logger = logging.getLogger(__name__)


class TrailRenderer:
    """Text-based renderer for decision trail visualization.

    Provides formatted output of decision trails showing chronological timeline
    and causal chain relationships between agent decisions.

    Example:
        >>> renderer = TrailRenderer(show_full_reasoning=False)
        >>> trail = builder.build_trail(run_id="abc123")
        >>> print(renderer.render_trail(trail))
    """

    def __init__(
        self,
        show_full_reasoning: bool = False,
        max_reasoning_length: int = 200,
    ) -> None:
        """Initialize trail renderer with display preferences.

        Args:
            show_full_reasoning: If True, display full reasoning text.
                If False, truncate to max_reasoning_length.
            max_reasoning_length: Maximum characters of reasoning to display
                when show_full_reasoning is False.
        """
        self.show_full_reasoning = show_full_reasoning
        self.max_reasoning_length = max_reasoning_length
        logger.debug(
            f"TrailRenderer initialized: show_full_reasoning={show_full_reasoning}, "
            f"max_reasoning_length={max_reasoning_length}"
        )

    def render_timeline(self, trail: DecisionTrail) -> str:
        """Render chronological decision timeline.

        Args:
            trail: DecisionTrail to render

        Returns:
            Formatted string showing chronological decision flow
        """
        lines = []

        # Header
        duration = self._format_duration(trail.started_at, trail.completed_at)
        lines.append(f"Decision Trail for {trail.ticker} on {trail.trade_date}")
        lines.append(f"Duration: {duration} | Run ID: {trail.run_id}")
        lines.append("=" * 80)
        lines.append("")

        # Nodes
        for node in trail.nodes:
            lines.append(self._format_node(node))
            lines.append("-" * 80)

        # Footer
        lines.append("")
        lines.append(f"Total decisions: {len(trail.nodes)}")

        return "\n".join(lines)

    def _format_node(self, node: TrailNode) -> str:
        """Format individual trail node with indentation and separators.

        Args:
            node: TrailNode to format

        Returns:
            Formatted string representation of the node
        """
        lines = []

        # Parse timestamp for display
        try:
            ts = datetime.fromisoformat(node.timestamp.replace("Z", "+00:00"))
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            ts_str = node.timestamp

        # Agent info
        lines.append(f"[{ts_str}] {node.agent_name} ({node.agent_type})")
        lines.append(f"  Decision: {node.decision}")

        # Confidence
        if node.confidence is not None:
            confidence_pct = node.confidence * 100
            lines.append(f"  Confidence: {confidence_pct:.1f}%")
        else:
            lines.append("  Confidence: N/A")

        # Reasoning (truncated if needed)
        reasoning = node.reasoning or ""
        if not self.show_full_reasoning and len(reasoning) > self.max_reasoning_length:
            reasoning = reasoning[: self.max_reasoning_length] + "..."
        lines.append(f"  Reasoning: {reasoning}")

        return "\n".join(lines)

    def _format_duration(self, started_at: str, completed_at: str) -> str:
        """Calculate duration between timestamps and format human-readable string.

        Args:
            started_at: ISO timestamp string of start
            completed_at: ISO timestamp string of completion

        Returns:
            Human-readable duration string (e.g., "12.5s", "2m 15s")
        """
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            duration_seconds = (end - start).total_seconds()

            if duration_seconds < 60:
                return f"{duration_seconds:.1f}s"
            else:
                minutes = int(duration_seconds // 60)
                seconds = duration_seconds % 60
                return f"{minutes}m {seconds:.0f}s"
        except (ValueError, AttributeError):
            return "Unknown"

    def render_causal_chain(self, trail: DecisionTrail) -> str:
        """Render causal chain showing agent-to-agent influence.

        Args:
            trail: DecisionTrail to render

        Returns:
            Formatted string showing causal flow between agents
        """
        lines = []

        # Header
        lines.append("Causal Chain: How Decisions Emerged")
        lines.append("=" * 80)
        lines.append("")

        if not trail.edges:
            lines.append("No causal edges found in this trail.")
            return "\n".join(lines)

        # Group edges by target to show multiple inputs
        grouped_edges = self._group_edges_by_target(trail.edges)

        # Get unique agents for final decision highlighting
        unique_agents = set(node.agent_name for node in trail.nodes)
        final_agents = {
            "portfolio_manager",
            "risk_judge",
        }

        # Display edges grouped by target
        for target, incoming_edges in grouped_edges.items():
            # Check if this is a final decision node
            is_final = any(edge.target.lower() in final_agents for edge in incoming_edges)
            marker = "*** " if is_final else ""

            lines.append(f"{marker}{target}")

            for edge in incoming_edges:
                indent = "    " if is_final else "  "
                lines.append(f"{indent}via: {edge.agent_name}")
                lines.append(f"{indent}type: {edge.edge_type}")

                # Show source for state transitions
                if edge.edge_type == "state_transition":
                    lines.append(f"{indent}from: {edge.source} → {edge.target}")

                lines.append("")

        return "\n".join(lines)

    def _group_edges_by_target(self, edges: List[TrailEdge]) -> Dict[str, List[TrailEdge]]:
        """Group incoming edges for each target node.

        Args:
            edges: List of TrailEdge objects

        Returns:
            Dict mapping target node name to list of incoming edges
        """
        grouped: Dict[str, List[TrailEdge]] = {}

        for edge in edges:
            target = edge.target
            if target not in grouped:
                grouped[target] = []
            grouped[target].append(edge)

        return grouped

    def render_trail(self, trail: DecisionTrail) -> str:
        """Render complete trail combining timeline and causal views.

        Args:
            trail: DecisionTrail to render

        Returns:
            Formatted string with timeline, causal chain, and summary
        """
        sections = []

        # Header
        sections.append(f"Decision Trail Report")
        sections.append(f"Ticker: {trail.ticker} | Date: {trail.trade_date}")
        sections.append(f"Run ID: {trail.run_id}")
        sections.append("=" * 80)
        sections.append("")

        # Timeline section
        sections.append(self.render_timeline(trail))
        sections.append("")
        sections.append("")

        # Separator
        sections.append("=" * 80)
        sections.append("")

        # Causal chain section
        sections.append(self.render_causal_chain(trail))
        sections.append("")

        # Summary footer
        stats = self._get_summary_stats(trail)
        sections.append("=" * 80)
        sections.append("Summary")
        sections.append(f"  Total Nodes: {stats['total_nodes']}")
        sections.append(f"  Total Edges: {stats['total_edges']}")
        sections.append(f"  Unique Agents: {stats['unique_agents']}")
        sections.append(f"  Duration: {stats['duration']}")

        return "\n".join(sections)

    def render_trail_markdown(self, trail: DecisionTrail) -> str:
        """Render trail as Markdown document for export.

        Args:
            trail: DecisionTrail to render

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append(f"# Decision Trail: {trail.ticker} on {trail.trade_date}")
        lines.append("")
        lines.append(f"**Run ID:** `{trail.run_id}`")
        lines.append(f"**Duration:** {self._format_duration(trail.started_at, trail.completed_at)}")
        lines.append("")

        # Timeline section
        lines.append("## Timeline")
        lines.append("")

        for node in trail.nodes:
            lines.append(f"### {node.agent_name} ({node.agent_type})")

            try:
                ts = datetime.fromisoformat(node.timestamp.replace("Z", "+00:00"))
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                ts_str = node.timestamp

            lines.append(f"**Time:** {ts_str}")
            lines.append(f"**Decision:** {node.decision}")

            if node.confidence is not None:
                confidence_pct = node.confidence * 100
                lines.append(f"**Confidence:** {confidence_pct:.1f}%")

            reasoning = node.reasoning or ""
            if not self.show_full_reasoning and len(reasoning) > self.max_reasoning_length:
                reasoning = reasoning[: self.max_reasoning_length] + "..."

            lines.append(f"**Reasoning:** {reasoning}")
            lines.append("")

        # Causal chain section
        lines.append("## Causal Chain")
        lines.append("")

        if trail.edges:
            grouped_edges = self._group_edges_by_target(trail.edges)

            for target, incoming_edges in grouped_edges.items():
                lines.append(f"### {target}")
                lines.append("")

                for edge in incoming_edges:
                    lines.append(f"- **via:** {edge.agent_name}")
                    lines.append(f"  **type:** {edge.edge_type}")
                    if edge.edge_type == "state_transition":
                        lines.append(f"  **from:** {edge.source} → {edge.target}")
                    lines.append("")

        # Summary section
        stats = self._get_summary_stats(trail)
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Decisions:** {stats['total_nodes']}")
        lines.append(f"- **Causal Links:** {stats['total_edges']}")
        lines.append(f"- **Unique Agents:** {stats['unique_agents']}")
        lines.append(f"- **Duration:** {stats['duration']}")

        return "\n".join(lines)

    def _get_summary_stats(self, trail: DecisionTrail) -> Dict[str, Any]:
        """Compute summary statistics for the trail.

        Args:
            trail: DecisionTrail to analyze

        Returns:
            Dict with total_nodes, total_edges, unique_agents, duration
        """
        unique_agents = set(node.agent_name for node in trail.nodes)
        duration = self._format_duration(trail.started_at, trail.completed_at)

        return {
            "total_nodes": len(trail.nodes),
            "total_edges": len(trail.edges),
            "unique_agents": len(unique_agents),
            "duration": duration,
        }
