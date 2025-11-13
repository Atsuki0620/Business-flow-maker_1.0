"""
BPMN変換機能の包括的なテスト。
"""

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.core.bpmn_converter import BPMNConverter, BPMNSVGGenerator, convert_json_to_bpmn
from src.core.bpmn_layout import BPMNLayoutEngine
from src.core.bpmn_validator import BPMNValidator, validate_bpmn


# テスト用のサンプルデータ
SAMPLE_FLOW = {
    "actors": [
        {"id": "actor_1", "name": "営業部", "type": "human"},
        {"id": "actor_2", "name": "総務部", "type": "human"},
    ],
    "phases": [
        {"id": "phase_1", "name": "準備"},
        {"id": "phase_2", "name": "承認"},
    ],
    "tasks": [
        {"id": "task_1", "name": "タスク1", "actor_id": "actor_1", "phase_id": "phase_1", "handoff_to": []},
        {"id": "task_2", "name": "タスク2", "actor_id": "actor_2", "phase_id": "phase_2", "handoff_to": []},
    ],
    "gateways": [
        {"id": "gateway_1", "name": "判定", "type": "exclusive"},
    ],
    "flows": [
        {"id": "flow_1", "from": "task_1", "to": "gateway_1"},
        {"id": "flow_2", "from": "gateway_1", "to": "task_2", "condition": "承認"},
    ],
    "issues": [],
    "metadata": {"id": "test-flow", "title": "テストフロー"},
}


class TestBPMNLayoutEngine:
    """BPMNLayoutEngineのテスト。"""

    def test_layout_calculation(self):
        """レイアウト計算の基本動作確認。"""
        engine = BPMNLayoutEngine(SAMPLE_FLOW)
        node_layouts, lane_layouts = engine.calculate_layout()

        # ノードレイアウトが生成されている
        assert len(node_layouts) > 0
        assert "task_1" in node_layouts
        assert "task_2" in node_layouts
        assert "gateway_1" in node_layouts

        # レーンレイアウトが生成されている
        assert len(lane_layouts) == 2

        # 座標が正の値である
        for layout in node_layouts.values():
            assert layout.x >= 0
            assert layout.y >= 0
            assert layout.width > 0
            assert layout.height > 0

    def test_diagram_size_calculation(self):
        """図全体のサイズ計算。"""
        engine = BPMNLayoutEngine(SAMPLE_FLOW)
        width, height = engine.calculate_diagram_size()

        assert width > 0
        assert height > 0

    def test_empty_flow(self):
        """空のフローでもエラーが発生しない。"""
        empty_flow = {
            "actors": [],
            "phases": [],
            "tasks": [],
            "gateways": [],
            "flows": [],
            "issues": [],
            "metadata": {},
        }
        engine = BPMNLayoutEngine(empty_flow)
        node_layouts, lane_layouts = engine.calculate_layout()

        assert len(node_layouts) == 0
        assert len(lane_layouts) == 0


class TestBPMNConverter:
    """BPMNConverterのテスト。"""

    def test_basic_conversion(self):
        """基本的なBPMN XML変換。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        # XML文字列が生成されている
        assert bpmn_xml
        assert "<?xml" in bpmn_xml
        assert "bpmn2:definitions" in bpmn_xml

        # XMLとしてパース可能
        root = ET.fromstring(bpmn_xml)
        assert root is not None

    def test_namespace_declarations(self):
        """名前空間が正しく宣言されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()
        root = ET.fromstring(bpmn_xml)

        # 必須の名前空間が存在
        namespaces = root.attrib
        assert any("bpmn2" in key for key in namespaces)
        assert any("bpmndi" in key for key in namespaces)
        assert any("dc" in key for key in namespaces)
        assert any("di" in key for key in namespaces)

    def test_process_element(self):
        """process要素が生成されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        namespaces = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        root = ET.fromstring(bpmn_xml)
        processes = root.findall('.//bpmn2:process', namespaces)

        assert len(processes) > 0

    def test_tasks_conversion(self):
        """タスクが正しく変換されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        namespaces = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        root = ET.fromstring(bpmn_xml)

        # userTask要素が存在
        user_tasks = root.findall('.//bpmn2:userTask', namespaces)
        assert len(user_tasks) > 0

        # タスクIDと名前が設定されている
        for task in user_tasks:
            assert 'id' in task.attrib
            assert 'name' in task.attrib

    def test_gateways_conversion(self):
        """ゲートウェイが正しく変換されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        namespaces = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        root = ET.fromstring(bpmn_xml)

        # exclusiveGateway要素が存在
        gateways = root.findall('.//bpmn2:exclusiveGateway', namespaces)
        assert len(gateways) > 0

    def test_sequence_flows_conversion(self):
        """シーケンスフローが正しく変換されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        namespaces = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        root = ET.fromstring(bpmn_xml)

        # sequenceFlow要素が存在
        flows = root.findall('.//bpmn2:sequenceFlow', namespaces)
        assert len(flows) == 2

        # sourceRefとtargetRefが設定されている
        for flow in flows:
            assert 'sourceRef' in flow.attrib
            assert 'targetRef' in flow.attrib

    def test_diagram_generation(self):
        """図形情報が生成されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        namespaces = {'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI'}
        root = ET.fromstring(bpmn_xml)

        # BPMNDiagram要素が存在
        diagrams = root.findall('.//bpmndi:BPMNDiagram', namespaces)
        assert len(diagrams) > 0

        # BPMNShape要素が存在
        shapes = root.findall('.//bpmndi:BPMNShape', namespaces)
        assert len(shapes) > 0

        # BPMNEdge要素が存在
        edges = root.findall('.//bpmndi:BPMNEdge', namespaces)
        assert len(edges) > 0


class TestBPMNValidator:
    """BPMNValidatorのテスト。"""

    def test_valid_bpmn(self):
        """正しいBPMN XMLの検証。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        validator = BPMNValidator(bpmn_xml)
        is_valid, errors, warnings = validator.validate()

        # 検証が成功する
        assert is_valid
        assert len(errors) == 0

    def test_statistics(self):
        """統計情報の取得。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        bpmn_xml = converter.convert_to_bpmn()

        validator = BPMNValidator(bpmn_xml)
        stats = validator.get_statistics()

        assert 'tasks' in stats
        assert 'gateways' in stats
        assert 'sequence_flows' in stats
        assert stats['tasks'] > 0
        assert stats['gateways'] > 0
        assert stats['sequence_flows'] > 0

    def test_invalid_xml(self):
        """不正なXMLの検証。"""
        invalid_xml = "これは不正なXMLです"
        validator = BPMNValidator(invalid_xml)
        is_valid, errors, warnings = validator.validate()

        assert not is_valid
        assert len(errors) > 0


class TestBPMNSVGGenerator:
    """BPMNSVGGeneratorのテスト。"""

    def test_svg_generation(self):
        """SVGの基本生成。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        converter.convert_to_bpmn()  # レイアウト計算のため

        generator = BPMNSVGGenerator(SAMPLE_FLOW, converter.node_layouts, converter.lane_layouts)
        svg_content = generator.generate_svg()

        # SVG要素が含まれている
        assert "<svg" in svg_content
        assert "</svg>" in svg_content
        assert "xmlns" in svg_content

    def test_svg_elements(self):
        """SVG要素が正しく生成されている。"""
        converter = BPMNConverter(SAMPLE_FLOW)
        converter.convert_to_bpmn()

        generator = BPMNSVGGenerator(SAMPLE_FLOW, converter.node_layouts, converter.lane_layouts)
        svg_content = generator.generate_svg()

        # タスク矩形が含まれている
        assert "rect" in svg_content

        # ゲートウェイ菱形が含まれている
        assert "polygon" in svg_content

        # フローが含まれている
        assert "line" in svg_content


class TestConvertJsonToBpmn:
    """convert_json_to_bpmn関数のテスト。"""

    def test_file_conversion(self):
        """ファイルからの変換。"""
        # 一時ファイルに保存
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            json_path = temp_path / "test.json"
            json_path.write_text(json.dumps(SAMPLE_FLOW), encoding='utf-8')

            bpmn_output = temp_path / "test.bpmn"
            svg_output = temp_path / "test.svg"

            result = convert_json_to_bpmn(
                json_path=json_path,
                bpmn_output=bpmn_output,
                svg_output=svg_output,
                validate=True,
                debug=False,
            )

            # ファイルが生成されている
            assert bpmn_output.exists()
            assert svg_output.exists()

            # 結果情報が返される
            assert 'bpmn_path' in result
            assert 'svg_path' in result
            assert 'validation' in result

            # 検証が成功している
            assert result['validation']['is_valid']

    def test_validation_failure(self):
        """不正なJSONからの変換。"""
        invalid_flow = {
            "actors": [],
            "phases": [],
            "tasks": [],
            "gateways": [],
            "flows": [
                {"id": "flow_1", "from": "nonexistent", "to": "also_nonexistent"}
            ],
            "issues": [],
            "metadata": {},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            json_path = temp_path / "invalid.json"
            json_path.write_text(json.dumps(invalid_flow), encoding='utf-8')

            bpmn_output = temp_path / "invalid.bpmn"
            svg_output = temp_path / "invalid.svg"

            result = convert_json_to_bpmn(
                json_path=json_path,
                bpmn_output=bpmn_output,
                svg_output=svg_output,
                validate=True,
                debug=False,
            )

            # ファイルは生成されるが検証は失敗
            assert bpmn_output.exists()
            assert result['validation'] is not None


class TestSampleFiles:
    """実際のサンプルファイルを使用したテスト。"""

    @pytest.mark.parametrize("sample_name", [
        "sample-tiny-01",
        "sample-small-01",
        "sample-medium-01",
        "sample-large-01",
    ])
    def test_sample_conversion(self, sample_name):
        """各サンプルファイルの変換テスト。"""
        sample_path = Path(f"samples/expected/{sample_name}.json")

        if not sample_path.exists():
            pytest.skip(f"サンプルファイルが存在しません: {sample_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bpmn_output = temp_path / f"{sample_name}.bpmn"
            svg_output = temp_path / f"{sample_name}.svg"

            result = convert_json_to_bpmn(
                json_path=sample_path,
                bpmn_output=bpmn_output,
                svg_output=svg_output,
                validate=True,
                debug=False,
            )

            # 変換が成功する
            assert bpmn_output.exists()
            assert svg_output.exists()

            # 検証が成功する
            assert result['validation']['is_valid']

            # 統計情報が正しい
            stats = result['validation']['statistics']
            assert stats['tasks'] > 0 or stats['gateways'] > 0
