"""
BPMN 2.0 XML converter for Business-flow-maker.

This module converts JSON flow documents to BPMN 2.0 compliant XML format.
It implements Layer2 functionality: JSON → BPMN 2.0 XML (.bpmn)

Mapping:
- actors → participant + lane elements (swimlane structure)
- tasks → userTask or serviceTask elements (determined by actor_type)
- gateways → exclusiveGateway, parallelGateway, or inclusiveGateway
- flows → sequenceFlow elements (with conditional expressions)
- phases → reflected as task ordering (no direct BPMN equivalent)
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom

from src.core.bpmn_layout import (
    calculate_layout,
    calculate_diagram_bounds,
    BPMNNodeLayout,
    BPMNEdgeLayout,
)

logger = logging.getLogger(__name__)

# BPMN 2.0 namespace definitions
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"

# Namespace prefixes for XML generation
NSMAP = {
    "bpmn2": BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "dc": DC_NS,
    "di": DI_NS,
}


def register_namespaces():
    """Register XML namespaces for proper prefix generation."""
    try:
        from xml.etree import ElementTree as ET
        for prefix, uri in NSMAP.items():
            ET.register_namespace(prefix, uri)
    except Exception as e:
        logger.warning(f"Failed to register namespaces: {e}")


def _ns(prefix: str, tag: str) -> str:
    """Generate namespaced tag."""
    return f"{{{NSMAP[prefix]}}}{tag}"


def load_flow_json(path: Path) -> Dict[str, Any]:
    """Load flow JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def convert_to_bpmn(flow: Dict[str, Any]) -> str:
    """
    Convert flow JSON to BPMN 2.0 XML string.

    Args:
        flow: Flow document dictionary

    Returns:
        BPMN 2.0 XML string
    """
    register_namespaces()

    # Calculate layout
    node_positions, edge_waypoints, lane_heights = calculate_layout(flow)
    actor_order = {actor["id"]: idx for idx, actor in enumerate(flow.get("actors", []))}
    diagram_width, diagram_height = calculate_diagram_bounds(node_positions, lane_heights, actor_order)

    # Create root definitions element
    definitions = Element(
        _ns("bpmn2", "definitions"),
        attrib={
            "id": f"Definitions_{flow.get('metadata', {}).get('id', 'flow')}",
            "targetNamespace": "http://bpmn.io/schema/bpmn",
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": "http://www.omg.org/spec/BPMN/20100524/MODEL BPMN20.xsd",
        },
    )

    # Add collaboration (swimlane structure)
    collaboration = SubElement(
        definitions,
        _ns("bpmn2", "collaboration"),
        attrib={"id": f"Collaboration_{flow.get('metadata', {}).get('id', 'flow')}"},
    )

    # Add a single participant that references the main process
    SubElement(
        collaboration,
        _ns("bpmn2", "participant"),
        attrib={
            "id": f"Participant_{flow.get('metadata', {}).get('id', 'flow')}",
            "name": flow.get('metadata', {}).get('title', 'Business Process'),
            "processRef": f"Process_{flow.get('metadata', {}).get('id', 'flow')}",
        },
    )

    # Add a single process with all tasks, gateways, and flows organized by lanes
    _add_single_process(definitions, flow, node_positions, edge_waypoints, actor_order)

    # Add BPMN diagram
    _add_bpmn_diagram(definitions, flow, node_positions, edge_waypoints, lane_heights, actor_order, diagram_width, diagram_height)

    # Convert to pretty-printed XML string
    return _prettify_xml(definitions)


def _add_single_process(
    definitions: Element,
    flow: Dict[str, Any],
    node_positions: Dict[str, BPMNNodeLayout],
    edge_waypoints: List[BPMNEdgeLayout],
    actor_order: Dict[str, int],
) -> None:
    """Add a single process element with lanes for each actor."""
    process_id = f"Process_{flow.get('metadata', {}).get('id', 'flow')}"

    process = SubElement(
        definitions,
        _ns("bpmn2", "process"),
        attrib={
            "id": process_id,
            "name": flow.get('metadata', {}).get('title', 'Business Process'),
            "isExecutable": "false",
        },
    )

    # Add lane set
    lane_set = SubElement(process, _ns("bpmn2", "laneSet"), attrib={"id": f"LaneSet_{process_id}"})

    # Create a lane for each actor
    for actor in sorted(flow.get("actors", []), key=lambda a: actor_order.get(a["id"], 0)):
        actor_id = actor["id"]
        lane = SubElement(
            lane_set,
            _ns("bpmn2", "lane"),
            attrib={
                "id": f"Lane_{actor_id}",
                "name": actor.get("name", actor_id),
            },
        )

        # Collect all node IDs for this actor
        actor_node_ids = [
            node.node_id for node in node_positions.values() if node.actor_id == actor_id
        ]

        # Add flowNodeRef elements
        for node_id in actor_node_ids:
            SubElement(lane, _ns("bpmn2", "flowNodeRef")).text = node_id

    # Add all tasks (outside of lanes)
    for task in flow.get("tasks", []):
        # Get actor for this task
        actor_id = task.get("actor_id")
        actor = next((a for a in flow.get("actors", []) if a["id"] == actor_id), {})
        _add_task_element(process, task, actor)

    # Add all gateways
    for gateway in flow.get("gateways", []):
        _add_gateway_element(process, gateway)

    # Add all sequence flows
    for flow_def in flow.get("flows", []):
        _add_sequence_flow(process, flow_def)


def _add_task_element(process: Element, task: Dict[str, Any], actor: Dict[str, Any]) -> None:
    """Add a task element to the process."""
    task_type = "serviceTask" if actor.get("type") == "system" else "userTask"

    task_elem = SubElement(
        process,
        _ns("bpmn2", task_type),
        attrib={
            "id": task["id"],
            "name": task.get("name", task["id"]),
        },
    )

    # Add documentation if notes exist
    if task.get("notes"):
        doc = SubElement(task_elem, _ns("bpmn2", "documentation"))
        doc.text = task["notes"]


def _add_gateway_element(process: Element, gateway: Dict[str, Any]) -> None:
    """Add a gateway element to the process."""
    gateway_type_map = {
        "exclusive": "exclusiveGateway",
        "parallel": "parallelGateway",
        "inclusive": "inclusiveGateway",
    }

    gateway_type = gateway_type_map.get(gateway.get("type", "exclusive"), "exclusiveGateway")

    gateway_elem = SubElement(
        process,
        _ns("bpmn2", gateway_type),
        attrib={
            "id": gateway["id"],
            "name": gateway.get("name", gateway["id"]),
        },
    )

    # Add documentation if notes exist
    if gateway.get("notes"):
        doc = SubElement(gateway_elem, _ns("bpmn2", "documentation"))
        doc.text = gateway["notes"]


def _add_sequence_flow(process: Element, flow_def: Dict[str, Any]) -> None:
    """Add a sequence flow element to the process."""
    flow_attrib = {
        "id": flow_def["id"],
        "sourceRef": flow_def["from"],
        "targetRef": flow_def["to"],
    }

    if flow_def.get("name"):
        flow_attrib["name"] = flow_def["name"]

    flow_elem = SubElement(process, _ns("bpmn2", "sequenceFlow"), attrib=flow_attrib)

    # Add condition expression if condition exists
    if flow_def.get("condition"):
        condition = SubElement(
            flow_elem,
            _ns("bpmn2", "conditionExpression"),
            attrib={"xsi:type": "bpmn2:tFormalExpression"},
        )
        condition.text = flow_def["condition"]


def _add_bpmn_diagram(
    definitions: Element,
    flow: Dict[str, Any],
    node_positions: Dict[str, BPMNNodeLayout],
    edge_waypoints: List[BPMNEdgeLayout],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
    diagram_width: float,
    diagram_height: float,
) -> None:
    """Add BPMN diagram with visual information."""
    diagram = SubElement(
        definitions,
        _ns("bpmndi", "BPMNDiagram"),
        attrib={"id": f"BPMNDiagram_{flow.get('metadata', {}).get('id', 'flow')}"},
    )

    plane = SubElement(
        diagram,
        _ns("bpmndi", "BPMNPlane"),
        attrib={
            "id": f"BPMNPlane_{flow.get('metadata', {}).get('id', 'flow')}",
            "bpmnElement": f"Collaboration_{flow.get('metadata', {}).get('id', 'flow')}",
        },
    )

    # Add shapes for participants (lanes)
    _add_participant_shapes(plane, flow, lane_heights, actor_order, diagram_width)

    # Add shapes for tasks and gateways
    for node in node_positions.values():
        _add_node_shape(plane, node)

    # Add edges for sequence flows
    for edge in edge_waypoints:
        _add_edge_shape(plane, edge)


def _add_participant_shapes(
    plane: Element,
    flow: Dict[str, Any],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
    diagram_width: float,
) -> None:
    """Add BPMNShape elements for participants and lanes."""
    from src.core.bpmn_layout import BPMN_MARGIN

    # Calculate total height for the single participant
    total_height = sum(lane_heights.get(actor["id"], 150) for actor in flow.get("actors", []))

    # Add single participant shape that encompasses all lanes
    participant_shape = SubElement(
        plane,
        _ns("bpmndi", "BPMNShape"),
        attrib={
            "id": f"BPMNShape_Participant_{flow.get('metadata', {}).get('id', 'flow')}",
            "bpmnElement": f"Participant_{flow.get('metadata', {}).get('id', 'flow')}",
            "isHorizontal": "true",
        },
    )

    SubElement(
        participant_shape,
        _ns("dc", "Bounds"),
        attrib={
            "x": str(BPMN_MARGIN),
            "y": str(BPMN_MARGIN),
            "width": str(diagram_width - 2 * BPMN_MARGIN),
            "height": str(total_height),
        },
    )

    # Add lane shapes within the participant
    cumulative_y = BPMN_MARGIN
    for actor in sorted(flow.get("actors", []), key=lambda a: actor_order.get(a["id"], 0)):
        actor_id = actor["id"]
        height = lane_heights.get(actor_id, 150)

        lane_shape = SubElement(
            plane,
            _ns("bpmndi", "BPMNShape"),
            attrib={
                "id": f"BPMNShape_Lane_{actor_id}",
                "bpmnElement": f"Lane_{actor_id}",
                "isHorizontal": "true",
            },
        )

        SubElement(
            lane_shape,
            _ns("dc", "Bounds"),
            attrib={
                "x": str(BPMN_MARGIN),
                "y": str(cumulative_y),
                "width": str(diagram_width - 2 * BPMN_MARGIN),
                "height": str(height),
            },
        )

        cumulative_y += height


def _add_node_shape(plane: Element, node: BPMNNodeLayout) -> None:
    """Add BPMNShape element for a task or gateway."""
    shape = SubElement(
        plane,
        _ns("bpmndi", "BPMNShape"),
        attrib={
            "id": f"BPMNShape_{node.node_id}",
            "bpmnElement": node.node_id,
        },
    )

    # Adjust position for gateways (center the diamond)
    x = node.x - node.width / 2 if node.kind == "gateway" else node.x
    y = node.y - node.height / 2 if node.kind == "gateway" else node.y

    bounds = SubElement(
        shape,
        _ns("dc", "Bounds"),
        attrib={
            "x": str(x),
            "y": str(y),
            "width": str(node.width),
            "height": str(node.height),
        },
    )


def _add_edge_shape(plane: Element, edge: BPMNEdgeLayout) -> None:
    """Add BPMNEdge element for a sequence flow."""
    edge_elem = SubElement(
        plane,
        _ns("bpmndi", "BPMNEdge"),
        attrib={
            "id": f"BPMNEdge_{edge.flow_id}",
            "bpmnElement": edge.flow_id,
        },
    )

    # Add waypoints
    for x, y in edge.waypoints:
        SubElement(
            edge_elem,
            _ns("di", "waypoint"),
            attrib={
                "x": str(x),
                "y": str(y),
            },
        )


def _prettify_xml(elem: Element) -> str:
    """Return a pretty-printed XML string with proper namespace declarations."""
    from xml.etree import ElementTree as ET

    # Ensure all namespaces are registered
    for prefix, uri in NSMAP.items():
        ET.register_namespace(prefix, uri)

    # Add XSI namespace for conditionExpression
    ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Use ElementTree's built-in pretty printing via indent() in Python 3.9+
    try:
        # Python 3.9+ has ET.indent()
        ET.indent(elem, space="  ", level=0)
        xml_string = ET.tostring(elem, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_string}'
    except AttributeError:
        # Fallback for older Python versions - manual indentation
        xml_string = ET.tostring(elem, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_string}'


def generate_bpmn_svg(
    flow: Dict[str, Any],
    node_positions: Dict[str, BPMNNodeLayout],
    edge_waypoints: List[BPMNEdgeLayout],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
    diagram_width: float,
    diagram_height: float,
) -> str:
    """
    Generate SVG visualization of BPMN diagram.

    Args:
        flow: Flow document dictionary
        node_positions: Calculated node positions
        edge_waypoints: Calculated edge waypoints
        lane_heights: Calculated lane heights
        actor_order: Actor ordering
        diagram_width: Total diagram width
        diagram_height: Total diagram height

    Returns:
        SVG string
    """
    from xml.etree.ElementTree import Element, SubElement, tostring
    from src.core.bpmn_layout import BPMN_MARGIN

    # Create SVG root element
    svg = Element(
        "svg",
        attrib={
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {diagram_width} {diagram_height}",
            "width": str(int(diagram_width)),
            "height": str(int(diagram_height)),
        },
    )

    # Add style definitions
    style = SubElement(svg, "style")
    style.text = """
        .bpmn-lane { fill: #f8f8f8; stroke: #000; stroke-width: 1; }
        .bpmn-lane:nth-of-type(even) { fill: #e8e8e8; }
        .bpmn-task { fill: #fff; stroke: #000; stroke-width: 1.5; }
        .bpmn-service-task { fill: #e1f5fe; stroke: #01579b; stroke-width: 1.5; }
        .bpmn-gateway { fill: #ffffcc; stroke: #ff9800; stroke-width: 2; }
        .bpmn-flow { stroke: #000; stroke-width: 1.5; fill: none; }
        .bpmn-text { font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }
        .bpmn-label { font-family: Arial, sans-serif; font-size: 11px; fill: #666; }
        .bpmn-lane-label { font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
    """

    # Add arrow marker
    defs = SubElement(svg, "defs")
    marker = SubElement(
        defs,
        "marker",
        attrib={
            "id": "arrow",
            "markerWidth": "10",
            "markerHeight": "10",
            "refX": "9",
            "refY": "3",
            "orient": "auto",
            "markerUnits": "strokeWidth",
        },
    )
    SubElement(marker, "path", attrib={"d": "M0,0 L0,6 L9,3 z", "fill": "#000"})

    # Draw swimlanes
    cumulative_y = BPMN_MARGIN
    for actor in sorted(flow.get("actors", []), key=lambda a: actor_order.get(a["id"], 0)):
        actor_id = actor["id"]
        height = lane_heights.get(actor_id, 150)

        # Lane background
        SubElement(
            svg,
            "rect",
            attrib={
                "class": "bpmn-lane",
                "x": str(BPMN_MARGIN),
                "y": str(cumulative_y),
                "width": str(diagram_width - 2 * BPMN_MARGIN),
                "height": str(height),
            },
        )

        # Lane label (rotated on the left)
        text_elem = SubElement(
            svg,
            "text",
            attrib={
                "class": "bpmn-lane-label",
                "x": str(BPMN_MARGIN + 15),
                "y": str(cumulative_y + height / 2),
                "text-anchor": "middle",
                "transform": f"rotate(-90 {BPMN_MARGIN + 15} {cumulative_y + height / 2})",
            },
        )
        text_elem.text = actor.get("name", actor_id)

        cumulative_y += height

    # Draw tasks
    for node in node_positions.values():
        if node.kind == "task":
            # Find task details to determine type
            task_def = next((t for t in flow.get("tasks", []) if t["id"] == node.node_id), {})
            actor_id = task_def.get("actor_id")
            actor = next((a for a in flow.get("actors", []) if a["id"] == actor_id), {})
            is_service_task = actor.get("type") == "system"

            # Draw task rectangle
            SubElement(
                svg,
                "rect",
                attrib={
                    "class": "bpmn-service-task" if is_service_task else "bpmn-task",
                    "x": str(node.x),
                    "y": str(node.y),
                    "width": str(node.width),
                    "height": str(node.height),
                    "rx": "5",
                    "ry": "5",
                },
            )

            # Draw task label (wrapped text if needed)
            text_elem = SubElement(
                svg,
                "text",
                attrib={
                    "class": "bpmn-text",
                    "x": str(node.x + node.width / 2),
                    "y": str(node.y + node.height / 2 + 4),
                },
            )
            text_elem.text = node.label

        elif node.kind == "gateway":
            # Find gateway details to determine type
            gateway_def = next((g for g in flow.get("gateways", []) if g["id"] == node.node_id), {})
            gateway_type = gateway_def.get("type", "exclusive")

            # Draw gateway diamond
            cx = node.x
            cy = node.y
            size = node.width
            points = [
                (cx, cy - size / 2),
                (cx + size / 2, cy),
                (cx, cy + size / 2),
                (cx - size / 2, cy),
            ]
            SubElement(
                svg,
                "polygon",
                attrib={
                    "class": "bpmn-gateway",
                    "points": " ".join(f"{x},{y}" for x, y in points),
                },
            )

            # Draw gateway marker
            if gateway_type == "exclusive":
                # X marker
                marker_size = size * 0.4
                SubElement(
                    svg,
                    "line",
                    attrib={
                        "x1": str(cx - marker_size / 2),
                        "y1": str(cy - marker_size / 2),
                        "x2": str(cx + marker_size / 2),
                        "y2": str(cy + marker_size / 2),
                        "stroke": "#ff9800",
                        "stroke-width": "2",
                    },
                )
                SubElement(
                    svg,
                    "line",
                    attrib={
                        "x1": str(cx + marker_size / 2),
                        "y1": str(cy - marker_size / 2),
                        "x2": str(cx - marker_size / 2),
                        "y2": str(cy + marker_size / 2),
                        "stroke": "#ff9800",
                        "stroke-width": "2",
                    },
                )
            elif gateway_type == "parallel":
                # + marker
                marker_size = size * 0.4
                SubElement(
                    svg,
                    "line",
                    attrib={
                        "x1": str(cx),
                        "y1": str(cy - marker_size / 2),
                        "x2": str(cx),
                        "y2": str(cy + marker_size / 2),
                        "stroke": "#ff9800",
                        "stroke-width": "2",
                    },
                )
                SubElement(
                    svg,
                    "line",
                    attrib={
                        "x1": str(cx - marker_size / 2),
                        "y1": str(cy),
                        "x2": str(cx + marker_size / 2),
                        "y2": str(cy),
                        "stroke": "#ff9800",
                        "stroke-width": "2",
                    },
                )
            elif gateway_type == "inclusive":
                # O marker
                marker_size = size * 0.35
                SubElement(
                    svg,
                    "circle",
                    attrib={
                        "cx": str(cx),
                        "cy": str(cy),
                        "r": str(marker_size / 2),
                        "fill": "none",
                        "stroke": "#ff9800",
                        "stroke-width": "2",
                    },
                )

            # Gateway label (below)
            if node.label:
                text_elem = SubElement(
                    svg,
                    "text",
                    attrib={
                        "class": "bpmn-text",
                        "x": str(cx),
                        "y": str(cy + size / 2 + 15),
                        "font-size": "11",
                    },
                )
                text_elem.text = node.label

    # Draw sequence flows
    for edge in edge_waypoints:
        # Draw the flow line
        if len(edge.waypoints) >= 2:
            # Create path
            path_data = f"M {edge.waypoints[0][0]},{edge.waypoints[0][1]}"
            for x, y in edge.waypoints[1:]:
                path_data += f" L {x},{y}"

            SubElement(
                svg,
                "path",
                attrib={
                    "class": "bpmn-flow",
                    "d": path_data,
                    "marker-end": "url(#arrow)",
                },
            )

            # Draw condition label if exists
            if edge.condition:
                # Position label at midpoint
                mid_idx = len(edge.waypoints) // 2
                label_x = edge.waypoints[mid_idx][0]
                label_y = edge.waypoints[mid_idx][1] - 5

                text_elem = SubElement(
                    svg,
                    "text",
                    attrib={
                        "class": "bpmn-label",
                        "x": str(label_x),
                        "y": str(label_y),
                        "text-anchor": "middle",
                    },
                )
                text_elem.text = edge.condition

    # Convert to string
    svg_string = tostring(svg, encoding="unicode", method="xml")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{svg_string}'


def save_bpmn(bpmn_xml: str, output_path: Path) -> None:
    """Save BPMN XML to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(bpmn_xml, encoding="utf-8")


def save_svg(svg_content: str, output_path: Path) -> None:
    """Save SVG to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")


def determine_output_paths(input_path: Path, output_arg: Path, svg_output_arg: Path = None) -> Tuple[Path, Path]:
    """
    Determine output paths for BPMN and SVG files.

    If input is in runs/ structure, output to the same run directory.
    Otherwise, use the provided output paths.

    Args:
        input_path: Input JSON file path
        output_arg: BPMN output path from CLI argument
        svg_output_arg: SVG output path from CLI argument (optional)

    Returns:
        Tuple of (bpmn_path, svg_path)
    """
    input_path = input_path.resolve()

    # Check if input is in runs/ structure
    if "runs" in input_path.parts:
        # Find the run directory
        run_dir = None
        for i, part in enumerate(input_path.parts):
            if part == "runs" and i + 1 < len(input_path.parts):
                run_dir = Path(*input_path.parts[:i+2])
                break

        if run_dir and run_dir.exists():
            # Output to runs/YYYYMMDD_HHMMSS_name/output/
            output_dir = run_dir / "output"
            bpmn_path = output_dir / "flow.bpmn"
            svg_path = output_dir / "flow-bpmn.svg"
            return bpmn_path, svg_path

    # Default behavior: use provided output paths
    bpmn_path = output_arg
    if svg_output_arg:
        svg_path = svg_output_arg
    else:
        # Default SVG path based on BPMN path
        svg_path = bpmn_path.parent / f"{bpmn_path.stem}-bpmn.svg"

    return bpmn_path, svg_path


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert Business-flow-maker JSON to BPMN 2.0 XML with SVG visualization"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input JSON file path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/flow.bpmn"),
        help="Output BPMN file path (default: output/flow.bpmn, or auto-detect from runs/)",
    )
    parser.add_argument(
        "--svg-output",
        type=Path,
        default=None,
        help="Output SVG file path (default: same directory as BPMN with -bpmn.svg suffix)",
    )
    parser.add_argument(
        "--no-svg",
        action="store_true",
        help="Disable SVG generation",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate BPMN after generation",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Loading flow from {args.input}")
    flow = load_flow_json(args.input)

    # Determine output paths (handles runs/ structure auto-detection)
    bpmn_path, svg_path = determine_output_paths(args.input, args.output, args.svg_output)

    logger.info("Converting to BPMN 2.0 XML")
    bpmn_xml = convert_to_bpmn(flow)

    logger.info(f"Saving BPMN to {bpmn_path}")
    save_bpmn(bpmn_xml, bpmn_path)

    # Generate SVG if not disabled
    svg_generated = False
    if not args.no_svg:
        logger.info("Generating BPMN SVG visualization")
        # Calculate layout (reuse from conversion)
        node_positions, edge_waypoints, lane_heights = calculate_layout(flow)
        actor_order = {actor["id"]: idx for idx, actor in enumerate(flow.get("actors", []))}
        diagram_width, diagram_height = calculate_diagram_bounds(node_positions, lane_heights, actor_order)

        svg_content = generate_bpmn_svg(
            flow,
            node_positions,
            edge_waypoints,
            lane_heights,
            actor_order,
            diagram_width,
            diagram_height,
        )

        logger.info(f"Saving SVG to {svg_path}")
        save_svg(svg_content, svg_path)
        svg_generated = True

    logger.info("Conversion complete")

    # Validate BPMN if requested
    validation_passed = None
    if args.validate:
        logger.info("Validating BPMN")
        from src.core.bpmn_validator import validate_bpmn
        is_valid, errors = validate_bpmn(bpmn_path)
        if is_valid:
            logger.info("✓ BPMN validation passed")
            validation_passed = True
        else:
            logger.error("✗ BPMN validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            validation_passed = False

    # Update info.md if in runs/ structure
    input_path = args.input.resolve()
    if "runs" in input_path.parts:
        # Find the run directory
        run_dir = None
        for i, part in enumerate(input_path.parts):
            if part == "runs" and i + 1 < len(input_path.parts):
                run_dir = Path(*input_path.parts[:i+2])
                break

        if run_dir and run_dir.exists() and (run_dir / "info.md").exists():
            try:
                from src.utils import run_manager

                # Prepare output files info
                output_files = []
                if bpmn_path.exists():
                    output_files.append({
                        "path": str(bpmn_path.relative_to(run_dir)),
                        "size": bpmn_path.stat().st_size,
                    })
                if svg_generated and svg_path.exists():
                    output_files.append({
                        "path": str(svg_path.relative_to(run_dir)),
                        "size": svg_path.stat().st_size,
                    })

                # Prepare BPMN conversion info
                bpmn_info = {
                    "svg_generated": svg_generated,
                }
                if validation_passed is not None:
                    bpmn_info["validation_passed"] = validation_passed

                # Update info.md
                run_manager.update_info_md(run_dir, {
                    "bpmn_conversion": bpmn_info,
                    "output_files": output_files,
                })

                logger.info(f"Updated execution info in {run_dir / 'info.md'}")
            except Exception as e:
                logger.warning(f"Failed to update info.md: {e}")


if __name__ == "__main__":
    main()
