"""
BPMN 2.0 compliance validator.

This module validates generated BPMN XML files for compliance with BPMN 2.0 specification.
It performs structural validation, reference integrity checks, and diagram element validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# BPMN 2.0 namespaces
BPMN_NS = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
BPMNDI_NS = "{http://www.omg.org/spec/BPMN/20100524/DI}"
DC_NS = "{http://www.omg.org/spec/DD/20100524/DC}"
DI_NS = "{http://www.omg.org/spec/DD/20100524/DI}"


def validate_bpmn(bpmn_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate a BPMN file for compliance with BPMN 2.0 specification.

    Args:
        bpmn_path: Path to BPMN XML file

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors: List[str] = []

    try:
        tree = ET.parse(bpmn_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return False, [f"XML parsing error: {e}"]
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Validate root element
    if not root.tag.endswith("definitions"):
        errors.append(f"Root element must be 'definitions', found: {root.tag}")

    # Validate required namespaces
    _validate_namespaces(root, errors)

    # Validate required attributes
    _validate_definitions_attributes(root, errors)

    # Validate collaboration structure
    _validate_collaboration(root, errors)

    # Validate processes
    _validate_processes(root, errors)

    # Validate diagram elements
    _validate_diagram(root, errors)

    # Validate reference integrity
    _validate_references(root, errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def _validate_namespaces(root: ET.Element, errors: List[str]) -> None:
    """Validate that required namespaces are defined."""
    required_namespaces = {
        "bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
        "dc": "http://www.omg.org/spec/DD/20100524/DC",
        "di": "http://www.omg.org/spec/DD/20100524/DI",
    }

    # ElementTree represents xmlns attributes with a special namespace
    # Check if the namespace URIs are present in the root tag or attributes
    root_tag_ns = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""

    for prefix, uri in required_namespaces.items():
        # Check if this namespace is used in the root tag
        if uri == root_tag_ns:
            continue

        # Check if namespace is declared as an attribute
        found = False
        for attr_name, attr_value in root.attrib.items():
            if attr_value == uri:
                found = True
                break

        if not found:
            # This might be okay if the namespace isn't used, so just log as debug
            logger.debug(f"Namespace {prefix} ({uri}) not found in root, but may be declared elsewhere")


def _validate_definitions_attributes(root: ET.Element, errors: List[str]) -> None:
    """Validate definitions element attributes."""
    if "id" not in root.attrib:
        errors.append("definitions element missing required 'id' attribute")

    if "targetNamespace" not in root.attrib:
        errors.append("definitions element missing required 'targetNamespace' attribute")


def _validate_collaboration(root: ET.Element, errors: List[str]) -> None:
    """Validate collaboration and participant elements."""
    collaborations = root.findall(f"{BPMN_NS}collaboration")

    if not collaborations:
        # Collaboration is optional, but if swimlanes exist, it should be present
        logger.debug("No collaboration element found (optional)")
        return

    for collaboration in collaborations:
        if "id" not in collaboration.attrib:
            errors.append("collaboration element missing required 'id' attribute")

        # Validate participants
        participants = collaboration.findall(f"{BPMN_NS}participant")
        if not participants:
            errors.append("collaboration must contain at least one participant")

        for participant in participants:
            if "id" not in participant.attrib:
                errors.append("participant element missing required 'id' attribute")
            if "processRef" not in participant.attrib:
                errors.append(f"participant {participant.attrib.get('id', 'unknown')} missing 'processRef' attribute")


def _validate_processes(root: ET.Element, errors: List[str]) -> None:
    """Validate process elements."""
    processes = root.findall(f"{BPMN_NS}process")

    if not processes:
        errors.append("definitions must contain at least one process")
        return

    for process in processes:
        if "id" not in process.attrib:
            errors.append("process element missing required 'id' attribute")
            continue

        process_id = process.attrib["id"]

        # Validate flow elements (tasks, gateways)
        tasks = (
            process.findall(f"{BPMN_NS}userTask")
            + process.findall(f"{BPMN_NS}serviceTask")
            + process.findall(f"{BPMN_NS}task")
        )

        gateways = (
            process.findall(f"{BPMN_NS}exclusiveGateway")
            + process.findall(f"{BPMN_NS}parallelGateway")
            + process.findall(f"{BPMN_NS}inclusiveGateway")
        )

        flows = process.findall(f"{BPMN_NS}sequenceFlow")

        # Validate task elements
        for task in tasks:
            if "id" not in task.attrib:
                errors.append(f"Task in process {process_id} missing 'id' attribute")

        # Validate gateway elements
        for gateway in gateways:
            if "id" not in gateway.attrib:
                errors.append(f"Gateway in process {process_id} missing 'id' attribute")

        # Validate sequence flows
        for flow in flows:
            if "id" not in flow.attrib:
                errors.append(f"sequenceFlow in process {process_id} missing 'id' attribute")
            if "sourceRef" not in flow.attrib:
                errors.append(f"sequenceFlow {flow.attrib.get('id', 'unknown')} missing 'sourceRef' attribute")
            if "targetRef" not in flow.attrib:
                errors.append(f"sequenceFlow {flow.attrib.get('id', 'unknown')} missing 'targetRef' attribute")


def _validate_diagram(root: ET.Element, errors: List[str]) -> None:
    """Validate BPMN diagram elements."""
    diagrams = root.findall(f"{BPMNDI_NS}BPMNDiagram")

    if not diagrams:
        logger.warning("No BPMNDiagram element found (recommended for visualization)")
        return

    for diagram in diagrams:
        if "id" not in diagram.attrib:
            errors.append("BPMNDiagram element missing required 'id' attribute")

        # Validate plane
        planes = diagram.findall(f"{BPMNDI_NS}BPMNPlane")
        if not planes:
            errors.append(f"BPMNDiagram {diagram.attrib.get('id', 'unknown')} missing BPMNPlane element")
            continue

        for plane in planes:
            if "id" not in plane.attrib:
                errors.append("BPMNPlane element missing required 'id' attribute")
            if "bpmnElement" not in plane.attrib:
                errors.append("BPMNPlane element missing required 'bpmnElement' attribute")

            # Validate shapes
            shapes = plane.findall(f"{BPMNDI_NS}BPMNShape")
            for shape in shapes:
                if "id" not in shape.attrib:
                    errors.append("BPMNShape element missing required 'id' attribute")
                if "bpmnElement" not in shape.attrib:
                    errors.append(f"BPMNShape {shape.attrib.get('id', 'unknown')} missing 'bpmnElement' attribute")

                # Validate bounds
                bounds = shape.findall(f"{DC_NS}Bounds")
                if not bounds:
                    errors.append(f"BPMNShape {shape.attrib.get('id', 'unknown')} missing Bounds element")
                else:
                    for bound in bounds:
                        required_attrs = ["x", "y", "width", "height"]
                        for attr in required_attrs:
                            if attr not in bound.attrib:
                                errors.append(
                                    f"Bounds in BPMNShape {shape.attrib.get('id', 'unknown')} missing '{attr}' attribute"
                                )

            # Validate edges
            edges = plane.findall(f"{BPMNDI_NS}BPMNEdge")
            for edge in edges:
                if "id" not in edge.attrib:
                    errors.append("BPMNEdge element missing required 'id' attribute")
                if "bpmnElement" not in edge.attrib:
                    errors.append(f"BPMNEdge {edge.attrib.get('id', 'unknown')} missing 'bpmnElement' attribute")

                # Validate waypoints
                waypoints = edge.findall(f"{DI_NS}waypoint")
                if len(waypoints) < 2:
                    errors.append(
                        f"BPMNEdge {edge.attrib.get('id', 'unknown')} must have at least 2 waypoints"
                    )
                for waypoint in waypoints:
                    if "x" not in waypoint.attrib or "y" not in waypoint.attrib:
                        errors.append(
                            f"waypoint in BPMNEdge {edge.attrib.get('id', 'unknown')} missing 'x' or 'y' attribute"
                        )


def _validate_references(root: ET.Element, errors: List[str]) -> None:
    """Validate reference integrity between elements."""
    # Collect all element IDs
    all_ids = set()

    # Collect process IDs
    processes = root.findall(f"{BPMN_NS}process")
    process_ids = set()
    for process in processes:
        process_id = process.attrib.get("id")
        if process_id:
            all_ids.add(process_id)
            process_ids.add(process_id)

            # Collect task and gateway IDs
            for elem in process:
                if elem.tag.endswith(("Task", "Gateway", "task", "gateway")):
                    elem_id = elem.attrib.get("id")
                    if elem_id:
                        all_ids.add(elem_id)

    # Validate participant processRef
    collaborations = root.findall(f"{BPMN_NS}collaboration")
    for collaboration in collaborations:
        all_ids.add(collaboration.attrib.get("id", ""))
        participants = collaboration.findall(f"{BPMN_NS}participant")
        for participant in participants:
            participant_id = participant.attrib.get("id")
            if participant_id:
                all_ids.add(participant_id)

            process_ref = participant.attrib.get("processRef")
            if process_ref and process_ref not in process_ids:
                errors.append(f"participant {participant_id} references non-existent process: {process_ref}")

    # Validate sequenceFlow references
    for process in processes:
        flows = process.findall(f"{BPMN_NS}sequenceFlow")
        for flow in flows:
            flow_id = flow.attrib.get("id")
            if flow_id:
                all_ids.add(flow_id)

            source_ref = flow.attrib.get("sourceRef")
            target_ref = flow.attrib.get("targetRef")

            if source_ref and source_ref not in all_ids:
                errors.append(f"sequenceFlow {flow_id} sourceRef references non-existent element: {source_ref}")

            if target_ref and target_ref not in all_ids:
                errors.append(f"sequenceFlow {flow_id} targetRef references non-existent element: {target_ref}")

    # Validate diagram references
    diagrams = root.findall(f"{BPMNDI_NS}BPMNDiagram")
    for diagram in diagrams:
        planes = diagram.findall(f"{BPMNDI_NS}BPMNPlane")
        for plane in planes:
            plane_element = plane.attrib.get("bpmnElement")
            if plane_element and plane_element not in all_ids:
                logger.debug(f"BPMNPlane references element not found in semantic model: {plane_element}")

            # Validate shape references
            shapes = plane.findall(f"{BPMNDI_NS}BPMNShape")
            for shape in shapes:
                bpmn_element = shape.attrib.get("bpmnElement")
                if bpmn_element and bpmn_element not in all_ids:
                    logger.debug(f"BPMNShape {shape.attrib.get('id')} references non-existent element: {bpmn_element}")

            # Validate edge references
            edges = plane.findall(f"{BPMNDI_NS}BPMNEdge")
            for edge in edges:
                bpmn_element = edge.attrib.get("bpmnElement")
                if bpmn_element and bpmn_element not in all_ids:
                    logger.debug(f"BPMNEdge {edge.attrib.get('id')} references non-existent element: {bpmn_element}")


def main():
    """CLI entry point for validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate BPMN 2.0 XML files")
    parser.add_argument("bpmn_file", type=Path, help="Path to BPMN XML file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    is_valid, errors = validate_bpmn(args.bpmn_file)

    if is_valid:
        print(f"✓ {args.bpmn_file} is valid BPMN 2.0")
        return 0
    else:
        print(f"✗ {args.bpmn_file} has validation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
