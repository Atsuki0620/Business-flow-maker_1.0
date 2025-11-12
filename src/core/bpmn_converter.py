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
from typing import Any, Dict, List
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


def save_bpmn(bpmn_xml: str, output_path: Path) -> None:
    """Save BPMN XML to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(bpmn_xml, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert Business-flow-maker JSON to BPMN 2.0 XML"
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
        help="Output BPMN file path (default: output/flow.bpmn)",
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

    logger.info("Converting to BPMN 2.0 XML")
    bpmn_xml = convert_to_bpmn(flow)

    logger.info(f"Saving BPMN to {args.output}")
    save_bpmn(bpmn_xml, args.output)

    logger.info("Conversion complete")

    if args.validate:
        logger.info("Validating BPMN")
        from src.core.bpmn_validator import validate_bpmn
        is_valid, errors = validate_bpmn(args.output)
        if is_valid:
            logger.info("✓ BPMN validation passed")
        else:
            logger.error("✗ BPMN validation failed:")
            for error in errors:
                logger.error(f"  - {error}")


if __name__ == "__main__":
    main()
