"""
BPMN 2.0準拠性バリデーター。

このモジュールは生成されたBPMN XMLファイルがBPMN 2.0仕様に準拠しているかを検証します。
構造検証、参照整合性チェック、ダイアグラム要素検証を実行します。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# BPMN 2.0名前空間
BPMN_NS = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
BPMNDI_NS = "{http://www.omg.org/spec/BPMN/20100524/DI}"
DC_NS = "{http://www.omg.org/spec/DD/20100524/DC}"
DI_NS = "{http://www.omg.org/spec/DD/20100524/DI}"


def validate_bpmn(bpmn_path: Path) -> Tuple[bool, List[str]]:
    """
    BPMNファイルがBPMN 2.0仕様に準拠しているかを検証する。

    Args:
        bpmn_path: BPMN XMLファイルへのパス

    Returns:
        (is_valid, error_messages)のタプル
    """
    errors: List[str] = []

    try:
        tree = ET.parse(bpmn_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return False, [f"XML parsing error: {e}"]
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # ルート要素を検証
    if not root.tag.endswith("definitions"):
        errors.append(f"Root element must be 'definitions', found: {root.tag}")

    # 必須名前空間を検証
    _validate_namespaces(root, errors)

    # 必須属性を検証
    _validate_definitions_attributes(root, errors)

    # コラボレーション構造を検証
    _validate_collaboration(root, errors)

    # プロセスを検証
    _validate_processes(root, errors)

    # ダイアグラム要素を検証
    _validate_diagram(root, errors)

    # 参照整合性を検証
    _validate_references(root, errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def _validate_namespaces(root: ET.Element, errors: List[str]) -> None:
    """必須名前空間が定義されていることを検証する。"""
    required_namespaces = {
        "bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
        "dc": "http://www.omg.org/spec/DD/20100524/DC",
        "di": "http://www.omg.org/spec/DD/20100524/DI",
    }

    # ElementTreeはxmlns属性を特別な名前空間で表現する
    # ルートタグまたは属性に名前空間URIが存在するかチェック
    root_tag_ns = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""

    for prefix, uri in required_namespaces.items():
        # この名前空間がルートタグで使用されているかチェック
        if uri == root_tag_ns:
            continue

        # 名前空間が属性として宣言されているかチェック
        found = False
        for attr_name, attr_value in root.attrib.items():
            if attr_value == uri:
                found = True
                break

        if not found:
            # 名前空間が使用されていない場合は問題ないため、デバッグログに記録
            logger.debug(f"Namespace {prefix} ({uri}) not found in root, but may be declared elsewhere")


def _validate_definitions_attributes(root: ET.Element, errors: List[str]) -> None:
    """definitions要素の属性を検証する。"""
    if "id" not in root.attrib:
        errors.append("definitions element missing required 'id' attribute")

    if "targetNamespace" not in root.attrib:
        errors.append("definitions element missing required 'targetNamespace' attribute")


def _validate_collaboration(root: ET.Element, errors: List[str]) -> None:
    """コラボレーションと参加者要素を検証する。"""
    collaborations = root.findall(f"{BPMN_NS}collaboration")

    if not collaborations:
        # コラボレーションはオプション、スイムレーンが存在する場合は必要
        logger.debug("No collaboration element found (optional)")
        return

    for collaboration in collaborations:
        if "id" not in collaboration.attrib:
            errors.append("collaboration element missing required 'id' attribute")

        # 参加者を検証
        participants = collaboration.findall(f"{BPMN_NS}participant")
        if not participants:
            errors.append("collaboration must contain at least one participant")

        for participant in participants:
            if "id" not in participant.attrib:
                errors.append("participant element missing required 'id' attribute")
            if "processRef" not in participant.attrib:
                errors.append(f"participant {participant.attrib.get('id', 'unknown')} missing 'processRef' attribute")


def _validate_processes(root: ET.Element, errors: List[str]) -> None:
    """プロセス要素を検証する。"""
    processes = root.findall(f"{BPMN_NS}process")

    if not processes:
        errors.append("definitions must contain at least one process")
        return

    for process in processes:
        if "id" not in process.attrib:
            errors.append("process element missing required 'id' attribute")
            continue

        process_id = process.attrib["id"]

        # フロー要素（タスク、ゲートウェイ）を検証
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

        # タスク要素を検証
        for task in tasks:
            if "id" not in task.attrib:
                errors.append(f"Task in process {process_id} missing 'id' attribute")

        # ゲートウェイ要素を検証
        for gateway in gateways:
            if "id" not in gateway.attrib:
                errors.append(f"Gateway in process {process_id} missing 'id' attribute")

        # シーケンスフローを検証
        for flow in flows:
            if "id" not in flow.attrib:
                errors.append(f"sequenceFlow in process {process_id} missing 'id' attribute")
            if "sourceRef" not in flow.attrib:
                errors.append(f"sequenceFlow {flow.attrib.get('id', 'unknown')} missing 'sourceRef' attribute")
            if "targetRef" not in flow.attrib:
                errors.append(f"sequenceFlow {flow.attrib.get('id', 'unknown')} missing 'targetRef' attribute")


def _validate_diagram(root: ET.Element, errors: List[str]) -> None:
    """BPMNダイアグラム要素を検証する。"""
    diagrams = root.findall(f"{BPMNDI_NS}BPMNDiagram")

    if not diagrams:
        logger.warning("No BPMNDiagram element found (recommended for visualization)")
        return

    for diagram in diagrams:
        if "id" not in diagram.attrib:
            errors.append("BPMNDiagram element missing required 'id' attribute")

        # プレーンを検証
        planes = diagram.findall(f"{BPMNDI_NS}BPMNPlane")
        if not planes:
            errors.append(f"BPMNDiagram {diagram.attrib.get('id', 'unknown')} missing BPMNPlane element")
            continue

        for plane in planes:
            if "id" not in plane.attrib:
                errors.append("BPMNPlane element missing required 'id' attribute")
            if "bpmnElement" not in plane.attrib:
                errors.append("BPMNPlane element missing required 'bpmnElement' attribute")

            # シェイプを検証
            shapes = plane.findall(f"{BPMNDI_NS}BPMNShape")
            for shape in shapes:
                if "id" not in shape.attrib:
                    errors.append("BPMNShape element missing required 'id' attribute")
                if "bpmnElement" not in shape.attrib:
                    errors.append(f"BPMNShape {shape.attrib.get('id', 'unknown')} missing 'bpmnElement' attribute")

                # 境界を検証
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

            # エッジを検証
            edges = plane.findall(f"{BPMNDI_NS}BPMNEdge")
            for edge in edges:
                if "id" not in edge.attrib:
                    errors.append("BPMNEdge element missing required 'id' attribute")
                if "bpmnElement" not in edge.attrib:
                    errors.append(f"BPMNEdge {edge.attrib.get('id', 'unknown')} missing 'bpmnElement' attribute")

                # ウェイポイントを検証
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
    """要素間の参照整合性を検証する。"""
    # すべての要素IDを収集
    all_ids = set()

    # プロセスIDを収集
    processes = root.findall(f"{BPMN_NS}process")
    process_ids = set()
    for process in processes:
        process_id = process.attrib.get("id")
        if process_id:
            all_ids.add(process_id)
            process_ids.add(process_id)

            # タスクとゲートウェイIDを収集
            for elem in process:
                if elem.tag.endswith(("Task", "Gateway", "task", "gateway")):
                    elem_id = elem.attrib.get("id")
                    if elem_id:
                        all_ids.add(elem_id)

    # 参加者のprocessRefを検証
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

    # sequenceFlowの参照を検証
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

    # ダイアグラムの参照を検証
    diagrams = root.findall(f"{BPMNDI_NS}BPMNDiagram")
    for diagram in diagrams:
        planes = diagram.findall(f"{BPMNDI_NS}BPMNPlane")
        for plane in planes:
            plane_element = plane.attrib.get("bpmnElement")
            if plane_element and plane_element not in all_ids:
                logger.debug(f"BPMNPlane references element not found in semantic model: {plane_element}")

            # シェイプの参照を検証
            shapes = plane.findall(f"{BPMNDI_NS}BPMNShape")
            for shape in shapes:
                bpmn_element = shape.attrib.get("bpmnElement")
                if bpmn_element and bpmn_element not in all_ids:
                    logger.debug(f"BPMNShape {shape.attrib.get('id')} references non-existent element: {bpmn_element}")

            # エッジの参照を検証
            edges = plane.findall(f"{BPMNDI_NS}BPMNEdge")
            for edge in edges:
                bpmn_element = edge.attrib.get("bpmnElement")
                if bpmn_element and bpmn_element not in all_ids:
                    logger.debug(f"BPMNEdge {edge.attrib.get('id')} references non-existent element: {bpmn_element}")


def main():
    """バリデーション用のCLIエントリーポイント。"""
    import argparse

    parser = argparse.ArgumentParser(description="BPMN 2.0 XMLファイルを検証")
    parser.add_argument("bpmn_file", type=Path, help="BPMN XMLファイルへのパス")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")
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
