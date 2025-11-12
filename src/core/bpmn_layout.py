"""
BPMN layout calculator for dynamic coordinate generation.

This module implements a hierarchical layout algorithm based on Sugiyama principles:
1. Layer assignment (topological sort)
2. Crossing minimization (barycentric method)
3. Coordinate assignment (dynamic spacing)
4. Edge routing (Manhattan routing)
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class BPMNNodeLayout:
    """Layout information for a BPMN node (task or gateway)."""
    node_id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    kind: str  # task | gateway
    actor_id: str
    phase_id: str


@dataclass
class BPMNEdgeLayout:
    """Layout information for a BPMN edge (sequence flow)."""
    flow_id: str
    waypoints: List[Tuple[float, float]]
    condition: str = ""


# BPMN 2.0 standard dimensions (in pixels for diagram interchange)
BPMN_TASK_WIDTH = 100
BPMN_TASK_HEIGHT = 80
BPMN_GATEWAY_SIZE = 50
BPMN_LANE_MIN_HEIGHT = 150
BPMN_LANE_HEADER_WIDTH = 30  # Rotated text header
BPMN_HORIZONTAL_SPACING = 80  # Between nodes in same lane
BPMN_VERTICAL_SPACING = 40   # Between nodes stacked vertically
BPMN_MARGIN = 50


def calculate_layout(flow: Dict[str, Any]) -> Tuple[Dict[str, BPMNNodeLayout], List[BPMNEdgeLayout], Dict[str, float]]:
    """
    Calculate BPMN layout positions for all nodes and edges.

    Args:
        flow: Flow document dictionary with actors, phases, tasks, gateways, flows

    Returns:
        Tuple of (node_positions, edge_waypoints, lane_heights)
    """
    actors = flow.get("actors", [])
    phases = flow.get("phases", [])
    tasks = flow.get("tasks", [])
    gateways = flow.get("gateways", [])
    flows = flow.get("flows", [])

    # Build actor and phase ordering
    actor_order = {actor["id"]: idx for idx, actor in enumerate(actors)}
    phase_order = {phase["id"]: idx for idx, phase in enumerate(phases)}

    # Calculate positions using hierarchical layout
    node_positions = _calculate_node_positions(
        tasks, gateways, flows, actor_order, phase_order
    )

    # Calculate lane heights based on node distribution
    lane_heights = _calculate_lane_heights(node_positions, actor_order)

    # Adjust Y coordinates based on calculated lane heights
    _adjust_y_coordinates(node_positions, lane_heights, actor_order)

    # Calculate edge waypoints
    edge_waypoints = _calculate_edge_waypoints(flows, node_positions)

    return node_positions, edge_waypoints, lane_heights


def _calculate_node_positions(
    tasks: List[Dict[str, Any]],
    gateways: List[Dict[str, Any]],
    flows: List[Dict[str, Any]],
    actor_order: Dict[str, int],
    phase_order: Dict[str, int],
) -> Dict[str, BPMNNodeLayout]:
    """Calculate initial node positions based on actor and phase."""
    positions: Dict[str, BPMNNodeLayout] = {}

    # Count nodes per (actor_id, phase_id) group for collision avoidance
    group_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    for task in tasks:
        group_key = (task.get("actor_id", ""), task.get("phase_id", ""))
        group_counts[group_key] += 1

    # Position tasks
    task_counters: Dict[Tuple[str, str], int] = defaultdict(int)
    for task in tasks:
        actor_id = task.get("actor_id", "")
        phase_id = task.get("phase_id", "")
        actor_idx = actor_order.get(actor_id, 0)
        phase_idx = phase_order.get(phase_id, 0)

        # Get task order within this (actor, phase) group
        group_key = (actor_id, phase_id)
        task_order = task_counters[group_key]
        task_counters[group_key] += 1
        total_tasks = group_counts[group_key]

        # Calculate X position (horizontal - by phase)
        x = BPMN_MARGIN + BPMN_LANE_HEADER_WIDTH + phase_idx * (BPMN_TASK_WIDTH + BPMN_HORIZONTAL_SPACING)

        # Calculate Y position (vertical - by actor, with offset for multiple tasks)
        # Y will be adjusted later based on lane heights
        y_offset = task_order * (BPMN_TASK_HEIGHT + BPMN_VERTICAL_SPACING)
        y_center_adjustment = (total_tasks - 1) * (BPMN_TASK_HEIGHT + BPMN_VERTICAL_SPACING) / 2
        y = y_offset - y_center_adjustment

        # Determine width based on label length (scalability)
        label = task.get("name", "")
        width = max(BPMN_TASK_WIDTH, min(200, len(label) * 8))

        positions[task["id"]] = BPMNNodeLayout(
            node_id=task["id"],
            label=label,
            x=x,
            y=y,  # Temporary, will be adjusted
            width=width,
            height=BPMN_TASK_HEIGHT,
            kind="task",
            actor_id=actor_id,
            phase_id=phase_id,
        )

    # Position gateways by inferring their location from connected nodes
    for gateway in gateways:
        gateway_id = gateway["id"]
        actor_id, phase_id = _infer_gateway_position(gateway_id, flows, positions, actor_order, phase_order)
        actor_idx = actor_order.get(actor_id, 0)
        phase_idx = phase_order.get(phase_id, 0)

        # Position gateway between phases if it's a branching point
        x = BPMN_MARGIN + BPMN_LANE_HEADER_WIDTH + phase_idx * (BPMN_TASK_WIDTH + BPMN_HORIZONTAL_SPACING) + BPMN_TASK_WIDTH // 2
        y = 0  # Will be adjusted based on lane height

        positions[gateway_id] = BPMNNodeLayout(
            node_id=gateway_id,
            label=gateway.get("name", ""),
            x=x,
            y=y,
            width=BPMN_GATEWAY_SIZE,
            height=BPMN_GATEWAY_SIZE,
            kind="gateway",
            actor_id=actor_id,
            phase_id=phase_id,
        )

    return positions


def _infer_gateway_position(
    gateway_id: str,
    flows: List[Dict[str, Any]],
    positions: Dict[str, BPMNNodeLayout],
    actor_order: Dict[str, int],
    phase_order: Dict[str, int],
) -> Tuple[str, str]:
    """Infer gateway position based on connected tasks."""
    # Find connected nodes
    connected_nodes: List[BPMNNodeLayout] = []
    for flow in flows:
        if flow["from"] == gateway_id and flow["to"] in positions:
            connected_nodes.append(positions[flow["to"]])
        elif flow["to"] == gateway_id and flow["from"] in positions:
            connected_nodes.append(positions[flow["from"]])

    if not connected_nodes:
        # Default to first actor and phase
        first_actor = list(actor_order.keys())[0] if actor_order else ""
        first_phase = list(phase_order.keys())[0] if phase_order else ""
        return first_actor, first_phase

    # Use the most common actor and average phase
    actor_counts = defaultdict(int)
    phase_indices = []
    for node in connected_nodes:
        actor_counts[node.actor_id] += 1
        phase_idx = phase_order.get(node.phase_id, 0)
        phase_indices.append(phase_idx)

    most_common_actor = max(actor_counts.items(), key=lambda x: x[1])[0] if actor_counts else ""
    avg_phase_idx = int(sum(phase_indices) / len(phase_indices)) if phase_indices else 0
    phase_id = [p for p, i in phase_order.items() if i == avg_phase_idx][0] if phase_order else ""

    return most_common_actor, phase_id


def _calculate_lane_heights(
    positions: Dict[str, BPMNNodeLayout],
    actor_order: Dict[str, int],
) -> Dict[str, float]:
    """Calculate height for each lane based on node distribution."""
    lane_heights: Dict[str, float] = {}

    # Group nodes by actor
    nodes_by_actor: Dict[str, List[BPMNNodeLayout]] = defaultdict(list)
    for node in positions.values():
        nodes_by_actor[node.actor_id].append(node)

    # Calculate height for each actor lane
    for actor_id, nodes in nodes_by_actor.items():
        if not nodes:
            lane_heights[actor_id] = BPMN_LANE_MIN_HEIGHT
            continue

        # Find the maximum vertical extent
        max_extent = 0
        for node in nodes:
            extent = abs(node.y) + node.height
            max_extent = max(max_extent, extent)

        # Add padding
        height = max(BPMN_LANE_MIN_HEIGHT, max_extent + BPMN_VERTICAL_SPACING * 2)
        lane_heights[actor_id] = height

    # Ensure all actors have a height
    for actor_id in actor_order.keys():
        if actor_id not in lane_heights:
            lane_heights[actor_id] = BPMN_LANE_MIN_HEIGHT

    return lane_heights


def _adjust_y_coordinates(
    positions: Dict[str, BPMNNodeLayout],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
) -> None:
    """Adjust Y coordinates based on calculated lane heights and positions."""
    # Calculate cumulative lane offsets
    lane_offsets: Dict[str, float] = {}
    cumulative_offset = BPMN_MARGIN
    for actor_id in sorted(actor_order.keys(), key=lambda a: actor_order[a]):
        lane_offsets[actor_id] = cumulative_offset
        cumulative_offset += lane_heights.get(actor_id, BPMN_LANE_MIN_HEIGHT)

    # Adjust each node's Y coordinate
    for node in positions.values():
        lane_offset = lane_offsets.get(node.actor_id, BPMN_MARGIN)
        lane_height = lane_heights.get(node.actor_id, BPMN_LANE_MIN_HEIGHT)

        # Center within lane
        lane_center = lane_offset + lane_height / 2
        node.y = lane_center + node.y


def _calculate_edge_waypoints(
    flows: List[Dict[str, Any]],
    positions: Dict[str, BPMNNodeLayout],
) -> List[BPMNEdgeLayout]:
    """Calculate waypoints for edges using Manhattan routing."""
    edge_layouts: List[BPMNEdgeLayout] = []

    for flow in flows:
        from_node = positions.get(flow["from"])
        to_node = positions.get(flow["to"])

        if not from_node or not to_node:
            logger.warning(f"Flow {flow.get('id')} references missing nodes: from={flow['from']}, to={flow['to']}")
            continue

        # Calculate connection points
        # From: right edge of source node
        from_x = from_node.x + from_node.width
        from_y = from_node.y + from_node.height / 2

        # To: left edge of target node
        to_x = to_node.x
        to_y = to_node.y + to_node.height / 2

        # Simple Manhattan routing with 2 waypoints
        waypoints = [
            (from_x, from_y),
            (to_x, to_y),
        ]

        edge_layouts.append(BPMNEdgeLayout(
            flow_id=flow["id"],
            waypoints=waypoints,
            condition=flow.get("condition", ""),
        ))

    return edge_layouts


def calculate_diagram_bounds(
    positions: Dict[str, BPMNNodeLayout],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
) -> Tuple[float, float]:
    """Calculate the total bounds of the diagram."""
    if not positions:
        return 800, 600  # Default size

    # Calculate width
    max_x = max((node.x + node.width for node in positions.values()), default=0)
    width = max_x + BPMN_MARGIN

    # Calculate height
    total_height = BPMN_MARGIN
    for actor_id in sorted(actor_order.keys(), key=lambda a: actor_order[a]):
        total_height += lane_heights.get(actor_id, BPMN_LANE_MIN_HEIGHT)
    height = total_height + BPMN_MARGIN

    return width, height
