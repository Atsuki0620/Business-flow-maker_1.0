"""
Tests for BPMN 2.0 converter functionality.

This test suite verifies:
- Basic conversion functionality
- XML schema validity
- Coordinate calculation
- Edge cases (single task, no gateways, complex flows)
- Different scale flows (tiny, small, medium)
"""

import json
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from src.core.bpmn_converter import convert_to_bpmn, load_flow_json
from src.core.bpmn_layout import calculate_layout
from src.core.bpmn_validator import validate_bpmn


# BPMN namespaces
BPMN_NS = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
BPMNDI_NS = "{http://www.omg.org/spec/BPMN/20100524/DI}"
DC_NS = "{http://www.omg.org/spec/DD/20100524/DC}"
DI_NS = "{http://www.omg.org/spec/DD/20100524/DI}"


@pytest.fixture
def sample_tiny_01():
    """Load sample-tiny-01.json for testing."""
    return load_flow_json(Path("samples/expected/sample-tiny-01.json"))


@pytest.fixture
def minimal_flow():
    """Create a minimal flow for edge case testing."""
    return {
        "metadata": {"id": "minimal", "title": "Minimal Flow"},
        "actors": [{"id": "actor_1", "name": "Actor 1", "type": "human"}],
        "phases": [{"id": "phase_1", "name": "Phase 1"}],
        "tasks": [
            {
                "id": "task_1",
                "name": "Task 1",
                "actor_id": "actor_1",
                "phase_id": "phase_1",
                "handoff_to": [],
            }
        ],
        "gateways": [],
        "flows": [],
        "issues": [],
    }


@pytest.fixture
def flow_with_gateway():
    """Create a flow with exclusive gateway."""
    return {
        "metadata": {"id": "gateway_test", "title": "Gateway Test"},
        "actors": [{"id": "actor_1", "name": "Actor 1", "type": "human"}],
        "phases": [
            {"id": "phase_1", "name": "Phase 1"},
            {"id": "phase_2", "name": "Phase 2"},
        ],
        "tasks": [
            {
                "id": "task_1",
                "name": "Task 1",
                "actor_id": "actor_1",
                "phase_id": "phase_1",
                "handoff_to": [],
            },
            {
                "id": "task_2",
                "name": "Task 2",
                "actor_id": "actor_1",
                "phase_id": "phase_2",
                "handoff_to": [],
            },
            {
                "id": "task_3",
                "name": "Task 3",
                "actor_id": "actor_1",
                "phase_id": "phase_2",
                "handoff_to": [],
            },
        ],
        "gateways": [
            {
                "id": "gateway_1",
                "name": "Decision",
                "type": "exclusive",
            }
        ],
        "flows": [
            {"id": "flow_1", "from": "task_1", "to": "gateway_1"},
            {"id": "flow_2", "from": "gateway_1", "to": "task_2", "condition": "Yes"},
            {"id": "flow_3", "from": "gateway_1", "to": "task_3", "condition": "No"},
        ],
        "issues": [],
    }


class TestBasicConversion:
    """Test basic conversion functionality."""

    def test_convert_minimal_flow(self, minimal_flow):
        """Test conversion of minimal flow (single task)."""
        bpmn_xml = convert_to_bpmn(minimal_flow)

        assert bpmn_xml is not None
        assert "definitions" in bpmn_xml
        assert "process" in bpmn_xml
        assert "Task 1" in bpmn_xml

    def test_convert_sample_tiny_01(self, sample_tiny_01):
        """Test conversion of sample-tiny-01.json."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)

        assert bpmn_xml is not None
        assert "営業部" in bpmn_xml
        assert "総務部" in bpmn_xml
        assert "備品ニーズ確認" in bpmn_xml
        assert "10万円判定" in bpmn_xml

    def test_convert_with_gateway(self, flow_with_gateway):
        """Test conversion with gateway."""
        bpmn_xml = convert_to_bpmn(flow_with_gateway)

        assert bpmn_xml is not None
        assert "exclusiveGateway" in bpmn_xml
        assert "Decision" in bpmn_xml
        assert "Yes" in bpmn_xml or "No" in bpmn_xml


class TestXMLStructure:
    """Test XML structure and BPMN 2.0 compliance."""

    def test_root_element(self, sample_tiny_01):
        """Test root element is definitions."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        assert root.tag.endswith("definitions")
        assert "id" in root.attrib
        assert "targetNamespace" in root.attrib

    def test_namespaces(self, sample_tiny_01):
        """Test required namespaces are present."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        # Check namespace URIs are in attributes
        attrib_values = root.attrib.values()
        assert "http://www.omg.org/spec/BPMN/20100524/MODEL" in attrib_values
        assert "http://www.omg.org/spec/BPMN/20100524/DI" in attrib_values
        assert "http://www.omg.org/spec/DD/20100524/DC" in attrib_values
        assert "http://www.omg.org/spec/DD/20100524/DI" in attrib_values

    def test_collaboration_structure(self, sample_tiny_01):
        """Test collaboration and participant structure."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        collaboration = root.find(f"{BPMN_NS}collaboration")
        assert collaboration is not None
        assert "id" in collaboration.attrib

        participants = collaboration.findall(f"{BPMN_NS}participant")
        assert len(participants) > 0
        for participant in participants:
            assert "id" in participant.attrib
            assert "name" in participant.attrib
            assert "processRef" in participant.attrib

    def test_process_elements(self, sample_tiny_01):
        """Test process elements are created."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        processes = root.findall(f"{BPMN_NS}process")
        assert len(processes) > 0

        for process in processes:
            assert "id" in process.attrib
            assert "isExecutable" in process.attrib

    def test_task_elements(self, sample_tiny_01):
        """Test task elements are created correctly."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        # Find all tasks across all processes
        all_tasks = []
        for process in root.findall(f"{BPMN_NS}process"):
            all_tasks.extend(process.findall(f"{BPMN_NS}userTask"))
            all_tasks.extend(process.findall(f"{BPMN_NS}serviceTask"))

        assert len(all_tasks) > 0

        for task in all_tasks:
            assert "id" in task.attrib
            assert "name" in task.attrib

    def test_gateway_elements(self, sample_tiny_01):
        """Test gateway elements are created correctly."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        # Find all gateways across all processes
        all_gateways = []
        for process in root.findall(f"{BPMN_NS}process"):
            all_gateways.extend(process.findall(f"{BPMN_NS}exclusiveGateway"))
            all_gateways.extend(process.findall(f"{BPMN_NS}parallelGateway"))
            all_gateways.extend(process.findall(f"{BPMN_NS}inclusiveGateway"))

        assert len(all_gateways) > 0

        for gateway in all_gateways:
            assert "id" in gateway.attrib
            assert "name" in gateway.attrib

    def test_sequence_flow_elements(self, sample_tiny_01):
        """Test sequence flow elements are created correctly."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        # Find all sequence flows across all processes
        all_flows = []
        for process in root.findall(f"{BPMN_NS}process"):
            all_flows.extend(process.findall(f"{BPMN_NS}sequenceFlow"))

        assert len(all_flows) > 0

        for flow in all_flows:
            assert "id" in flow.attrib
            assert "sourceRef" in flow.attrib
            assert "targetRef" in flow.attrib


class TestDiagramElements:
    """Test BPMN diagram interchange (DI) elements."""

    def test_diagram_exists(self, sample_tiny_01):
        """Test BPMNDiagram element exists."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        diagram = root.find(f"{BPMNDI_NS}BPMNDiagram")
        assert diagram is not None
        assert "id" in diagram.attrib

    def test_plane_exists(self, sample_tiny_01):
        """Test BPMNPlane element exists."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        diagram = root.find(f"{BPMNDI_NS}BPMNDiagram")
        plane = diagram.find(f"{BPMNDI_NS}BPMNPlane")

        assert plane is not None
        assert "id" in plane.attrib
        assert "bpmnElement" in plane.attrib

    def test_shapes_have_bounds(self, sample_tiny_01):
        """Test all BPMNShape elements have Bounds."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        diagram = root.find(f"{BPMNDI_NS}BPMNDiagram")
        plane = diagram.find(f"{BPMNDI_NS}BPMNPlane")
        shapes = plane.findall(f"{BPMNDI_NS}BPMNShape")

        assert len(shapes) > 0

        for shape in shapes:
            bounds = shape.find(f"{DC_NS}Bounds")
            assert bounds is not None
            assert "x" in bounds.attrib
            assert "y" in bounds.attrib
            assert "width" in bounds.attrib
            assert "height" in bounds.attrib

            # Verify coordinates are valid numbers
            assert float(bounds.attrib["x"]) >= 0
            assert float(bounds.attrib["y"]) >= 0
            assert float(bounds.attrib["width"]) > 0
            assert float(bounds.attrib["height"]) > 0

    def test_edges_have_waypoints(self, sample_tiny_01):
        """Test all BPMNEdge elements have waypoints."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)
        root = ET.fromstring(bpmn_xml)

        diagram = root.find(f"{BPMNDI_NS}BPMNDiagram")
        plane = diagram.find(f"{BPMNDI_NS}BPMNPlane")
        edges = plane.findall(f"{BPMNDI_NS}BPMNEdge")

        assert len(edges) > 0

        for edge in edges:
            waypoints = edge.findall(f"{DI_NS}waypoint")
            assert len(waypoints) >= 2

            for waypoint in waypoints:
                assert "x" in waypoint.attrib
                assert "y" in waypoint.attrib
                # Verify coordinates are valid numbers
                assert float(waypoint.attrib["x"]) >= 0
                assert float(waypoint.attrib["y"]) >= 0


class TestLayoutCalculation:
    """Test layout calculation algorithms."""

    def test_layout_returns_positions(self, sample_tiny_01):
        """Test layout calculation returns node positions."""
        node_positions, edge_waypoints, lane_heights = calculate_layout(sample_tiny_01)

        assert len(node_positions) > 0
        assert len(edge_waypoints) > 0
        assert len(lane_heights) > 0

    def test_no_hardcoded_coordinates(self, sample_tiny_01):
        """Test that coordinates are dynamically calculated."""
        node_positions, _, _ = calculate_layout(sample_tiny_01)

        # Verify positions vary based on content
        x_coords = [node.x for node in node_positions.values()]
        y_coords = [node.y for node in node_positions.values()]

        # Should have multiple distinct positions
        assert len(set(x_coords)) > 1 or len(set(y_coords)) > 1

    def test_scalability_different_sizes(self):
        """Test layout scales with different flow sizes."""
        small_flow = {
            "actors": [{"id": "a1", "name": "A1", "type": "human"}],
            "phases": [{"id": "p1", "name": "P1"}],
            "tasks": [{"id": "t1", "name": "T1", "actor_id": "a1", "phase_id": "p1", "handoff_to": []}],
            "gateways": [],
            "flows": [],
        }

        large_flow = {
            "actors": [
                {"id": f"a{i}", "name": f"Actor {i}", "type": "human"} for i in range(1, 6)
            ],
            "phases": [
                {"id": f"p{i}", "name": f"Phase {i}"} for i in range(1, 6)
            ],
            "tasks": [
                {"id": f"t{i}", "name": f"Task {i}", "actor_id": f"a{(i % 5) + 1}", "phase_id": f"p{(i % 5) + 1}", "handoff_to": []}
                for i in range(1, 26)
            ],
            "gateways": [],
            "flows": [],
        }

        small_positions, _, small_lanes = calculate_layout(small_flow)
        large_positions, _, large_lanes = calculate_layout(large_flow)

        # Large flow should have more nodes
        assert len(large_positions) > len(small_positions)

        # Large flow should have larger dimensions
        small_max_x = max(node.x for node in small_positions.values())
        large_max_x = max(node.x for node in large_positions.values())
        assert large_max_x > small_max_x


class TestValidation:
    """Test BPMN validation functionality."""

    def test_valid_bpmn_passes_validation(self, sample_tiny_01):
        """Test that valid BPMN passes validation."""
        bpmn_xml = convert_to_bpmn(sample_tiny_01)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".bpmn", delete=False) as f:
            f.write(bpmn_xml)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validate_bpmn(temp_path)
            if not is_valid:
                print("Validation errors:")
                for error in errors:
                    print(f"  - {error}")
            assert is_valid, f"BPMN validation failed: {errors}"
        finally:
            temp_path.unlink()

    def test_invalid_xml_fails_validation(self):
        """Test that invalid XML fails validation."""
        invalid_xml = "<invalid>not bpmn</invalid>"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".bpmn", delete=False) as f:
            f.write(invalid_xml)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validate_bpmn(temp_path)
            assert not is_valid
            assert len(errors) > 0
        finally:
            temp_path.unlink()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_task_no_flows(self, minimal_flow):
        """Test flow with single task and no flows."""
        bpmn_xml = convert_to_bpmn(minimal_flow)
        assert bpmn_xml is not None
        assert "Task 1" in bpmn_xml

    def test_multiple_tasks_same_cell(self):
        """Test multiple tasks in same (actor, phase) cell."""
        flow = {
            "metadata": {"id": "multi_task", "title": "Multi Task"},
            "actors": [{"id": "actor_1", "name": "Actor 1", "type": "human"}],
            "phases": [{"id": "phase_1", "name": "Phase 1"}],
            "tasks": [
                {"id": "task_1", "name": "Task 1", "actor_id": "actor_1", "phase_id": "phase_1", "handoff_to": []},
                {"id": "task_2", "name": "Task 2", "actor_id": "actor_1", "phase_id": "phase_1", "handoff_to": []},
                {"id": "task_3", "name": "Task 3", "actor_id": "actor_1", "phase_id": "phase_1", "handoff_to": []},
            ],
            "gateways": [],
            "flows": [],
            "issues": [],
        }

        node_positions, _, _ = calculate_layout(flow)

        # Verify all tasks have different Y coordinates (vertically stacked)
        y_coords = [node.y for node in node_positions.values()]
        assert len(set(y_coords)) == 3, "Tasks in same cell should have different Y coordinates"

    def test_gateway_types(self):
        """Test different gateway types."""
        for gateway_type in ["exclusive", "parallel", "inclusive"]:
            flow = {
                "metadata": {"id": f"{gateway_type}_test", "title": f"{gateway_type.title()} Test"},
                "actors": [{"id": "actor_1", "name": "Actor 1", "type": "human"}],
                "phases": [{"id": "phase_1", "name": "Phase 1"}],
                "tasks": [
                    {"id": "task_1", "name": "Task 1", "actor_id": "actor_1", "phase_id": "phase_1", "handoff_to": []}
                ],
                "gateways": [
                    {"id": "gateway_1", "name": "Gateway", "type": gateway_type}
                ],
                "flows": [],
                "issues": [],
            }

            bpmn_xml = convert_to_bpmn(flow)
            assert f"{gateway_type}Gateway" in bpmn_xml

    def test_system_actor_creates_service_task(self):
        """Test that system actor creates serviceTask instead of userTask."""
        flow = {
            "metadata": {"id": "system_actor", "title": "System Actor"},
            "actors": [{"id": "system_1", "name": "System", "type": "system"}],
            "phases": [{"id": "phase_1", "name": "Phase 1"}],
            "tasks": [
                {"id": "task_1", "name": "Task 1", "actor_id": "system_1", "phase_id": "phase_1", "handoff_to": []}
            ],
            "gateways": [],
            "flows": [],
            "issues": [],
        }

        bpmn_xml = convert_to_bpmn(flow)
        assert "serviceTask" in bpmn_xml


class TestIntegration:
    """Integration tests with sample files."""

    def test_all_sample_files(self):
        """Test conversion of all available sample files."""
        sample_dir = Path("samples/expected")
        if not sample_dir.exists():
            pytest.skip("Sample directory not found")

        sample_files = list(sample_dir.glob("*.json"))
        assert len(sample_files) > 0, "No sample files found"

        for sample_file in sample_files:
            print(f"\nTesting {sample_file.name}")
            flow = load_flow_json(sample_file)
            bpmn_xml = convert_to_bpmn(flow)

            # Basic checks
            assert bpmn_xml is not None
            assert "definitions" in bpmn_xml
            assert "process" in bpmn_xml

            # Validation check
            with tempfile.NamedTemporaryFile(mode="w", suffix=".bpmn", delete=False) as f:
                f.write(bpmn_xml)
                temp_path = Path(f.name)

            try:
                is_valid, errors = validate_bpmn(temp_path)
                assert is_valid, f"Validation failed for {sample_file.name}: {errors}"
            finally:
                temp_path.unlink()
