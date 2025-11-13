"""
Business-flow-maker用のBPMN 2.0 XMLコンバーター。

このモジュールはJSONフロードキュメントをBPMN 2.0準拠のXML形式に変換します。
Layer2機能を実装：JSON → BPMN 2.0 XML (.bpmn)

マッピング:
- actors → participant + lane要素（スイムレーン構造）
- tasks → userTaskまたはserviceTask要素（actor_typeで決定）
- gateways → exclusiveGateway、parallelGateway、inclusiveGateway
- flows → sequenceFlow要素（条件式付き）
- phases → タスク順序として反映（BPMNの直接的な対応要素なし）
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

# BPMN 2.0 名前空間定義
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"

# XML生成用の名前空間プレフィックス
NSMAP = {
    "bpmn2": BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "dc": DC_NS,
    "di": DI_NS,
}


def register_namespaces():
    """適切なプレフィックス生成のためにXML名前空間を登録する。"""
    try:
        from xml.etree import ElementTree as ET
        for prefix, uri in NSMAP.items():
            ET.register_namespace(prefix, uri)
    except Exception as e:
        logger.warning(f"Failed to register namespaces: {e}")


def _ns(prefix: str, tag: str) -> str:
    """名前空間付きタグを生成する。"""
    return f"{{{NSMAP[prefix]}}}{tag}"


def load_flow_json(path: Path) -> Dict[str, Any]:
    """フローJSONファイルを読み込む。"""
    return json.loads(path.read_text(encoding="utf-8"))


def convert_to_bpmn(flow: Dict[str, Any]) -> str:
    """
    フローJSONをBPMN 2.0 XML文字列に変換する。

    Args:
        flow: フロードキュメント辞書

    Returns:
        BPMN 2.0 XML文字列
    """
    register_namespaces()

    # レイアウト計算
    node_positions, edge_waypoints, lane_heights = calculate_layout(flow)
    actor_order = {actor["id"]: idx for idx, actor in enumerate(flow.get("actors", []))}
    diagram_width, diagram_height = calculate_diagram_bounds(node_positions, lane_heights, actor_order)

    # ルートdefinitions要素を作成
    definitions = Element(
        _ns("bpmn2", "definitions"),
        attrib={
            "id": f"Definitions_{flow.get('metadata', {}).get('id', 'flow')}",
            "targetNamespace": "http://bpmn.io/schema/bpmn",
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": "http://www.omg.org/spec/BPMN/20100524/MODEL BPMN20.xsd",
        },
    )

    # コラボレーション（スイムレーン構造）を追加
    collaboration = SubElement(
        definitions,
        _ns("bpmn2", "collaboration"),
        attrib={"id": f"Collaboration_{flow.get('metadata', {}).get('id', 'flow')}"},
    )

    # メインプロセスを参照する単一の参加者を追加
    SubElement(
        collaboration,
        _ns("bpmn2", "participant"),
        attrib={
            "id": f"Participant_{flow.get('metadata', {}).get('id', 'flow')}",
            "name": flow.get('metadata', {}).get('title', 'Business Process'),
            "processRef": f"Process_{flow.get('metadata', {}).get('id', 'flow')}",
        },
    )

    # レーンで整理されたすべてのタスク、ゲートウェイ、フローを含む単一プロセスを追加
    _add_single_process(definitions, flow, node_positions, edge_waypoints, actor_order)

    # BPMNダイアグラムを追加
    _add_bpmn_diagram(definitions, flow, node_positions, edge_waypoints, lane_heights, actor_order, diagram_width, diagram_height)

    # 整形されたXML文字列に変換
    return _prettify_xml(definitions)


def _add_single_process(
    definitions: Element,
    flow: Dict[str, Any],
    node_positions: Dict[str, BPMNNodeLayout],
    edge_waypoints: List[BPMNEdgeLayout],
    actor_order: Dict[str, int],
) -> None:
    """各アクターのレーンを持つ単一のプロセス要素を追加する。"""
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

    # レーンセットを追加
    lane_set = SubElement(process, _ns("bpmn2", "laneSet"), attrib={"id": f"LaneSet_{process_id}"})

    # 各アクターのレーンを作成
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

        # このアクターのすべてのノードIDを収集
        actor_node_ids = [
            node.node_id for node in node_positions.values() if node.actor_id == actor_id
        ]

        # flowNodeRef要素を追加
        for node_id in actor_node_ids:
            SubElement(lane, _ns("bpmn2", "flowNodeRef")).text = node_id

    # すべてのタスクを追加（レーン外）
    for task in flow.get("tasks", []):
        # このタスクのアクターを取得
        actor_id = task.get("actor_id")
        actor = next((a for a in flow.get("actors", []) if a["id"] == actor_id), {})
        _add_task_element(process, task, actor)

    # すべてのゲートウェイを追加
    for gateway in flow.get("gateways", []):
        _add_gateway_element(process, gateway)

    # すべてのシーケンスフローを追加
    for flow_def in flow.get("flows", []):
        _add_sequence_flow(process, flow_def)


def _add_task_element(process: Element, task: Dict[str, Any], actor: Dict[str, Any]) -> None:
    """プロセスにタスク要素を追加する。"""
    task_type = "serviceTask" if actor.get("type") == "system" else "userTask"

    task_elem = SubElement(
        process,
        _ns("bpmn2", task_type),
        attrib={
            "id": task["id"],
            "name": task.get("name", task["id"]),
        },
    )

    # notesが存在する場合はドキュメントを追加
    if task.get("notes"):
        doc = SubElement(task_elem, _ns("bpmn2", "documentation"))
        doc.text = task["notes"]


def _add_gateway_element(process: Element, gateway: Dict[str, Any]) -> None:
    """プロセスにゲートウェイ要素を追加する。"""
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

    # notesが存在する場合はドキュメントを追加
    if gateway.get("notes"):
        doc = SubElement(gateway_elem, _ns("bpmn2", "documentation"))
        doc.text = gateway["notes"]


def _add_sequence_flow(process: Element, flow_def: Dict[str, Any]) -> None:
    """プロセスにシーケンスフロー要素を追加する。"""
    flow_attrib = {
        "id": flow_def["id"],
        "sourceRef": flow_def["from"],
        "targetRef": flow_def["to"],
    }

    if flow_def.get("name"):
        flow_attrib["name"] = flow_def["name"]

    flow_elem = SubElement(process, _ns("bpmn2", "sequenceFlow"), attrib=flow_attrib)

    # conditionが存在する場合は条件式を追加
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
    """視覚情報を持つBPMNダイアグラムを追加する。"""
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

    # 参加者（レーン）のシェイプを追加
    _add_participant_shapes(plane, flow, lane_heights, actor_order, diagram_width)

    # タスクとゲートウェイのシェイプを追加
    for node in node_positions.values():
        _add_node_shape(plane, node)

    # シーケンスフローのエッジを追加
    for edge in edge_waypoints:
        _add_edge_shape(plane, edge)


def _add_participant_shapes(
    plane: Element,
    flow: Dict[str, Any],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
    diagram_width: float,
) -> None:
    """参加者とレーンのBPMNShape要素を追加する。"""
    from src.core.bpmn_layout import BPMN_MARGIN

    # 単一参加者の合計高さを計算
    total_height = sum(lane_heights.get(actor["id"], 150) for actor in flow.get("actors", []))

    # すべてのレーンを包含する単一の参加者シェイプを追加
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

    # 参加者内のレーンシェイプを追加
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
    """タスクまたはゲートウェイのBPMNShape要素を追加する。"""
    shape = SubElement(
        plane,
        _ns("bpmndi", "BPMNShape"),
        attrib={
            "id": f"BPMNShape_{node.node_id}",
            "bpmnElement": node.node_id,
        },
    )

    # ゲートウェイの位置を調整（ダイヤモンドを中央揃え）
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
    """シーケンスフローのBPMNEdge要素を追加する。"""
    edge_elem = SubElement(
        plane,
        _ns("bpmndi", "BPMNEdge"),
        attrib={
            "id": f"BPMNEdge_{edge.flow_id}",
            "bpmnElement": edge.flow_id,
        },
    )

    # ウェイポイントを追加
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
    """適切な名前空間宣言を持つ整形されたXML文字列を返す。"""
    from xml.etree import ElementTree as ET

    # すべての名前空間が登録されていることを確認
    for prefix, uri in NSMAP.items():
        ET.register_namespace(prefix, uri)

    # conditionExpression用のXSI名前空間を追加
    ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Python 3.9+のElementTreeの組み込み整形機能（indent()）を使用
    try:
        # Python 3.9+にはET.indent()がある
        ET.indent(elem, space="  ", level=0)
        xml_string = ET.tostring(elem, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_string}'
    except AttributeError:
        # 古いPythonバージョン用のフォールバック - 手動インデント
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
    BPMNダイアグラムのSVG可視化を生成する。

    Args:
        flow: フロードキュメント辞書
        node_positions: 計算されたノード位置
        edge_waypoints: 計算されたエッジウェイポイント
        lane_heights: 計算されたレーン高さ
        actor_order: アクター順序
        diagram_width: ダイアグラム全体の幅
        diagram_height: ダイアグラム全体の高さ

    Returns:
        SVG文字列
    """
    from xml.etree.ElementTree import Element, SubElement, tostring
    from src.core.bpmn_layout import BPMN_MARGIN

    # SVGルート要素を作成
    svg = Element(
        "svg",
        attrib={
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {diagram_width} {diagram_height}",
            "width": str(int(diagram_width)),
            "height": str(int(diagram_height)),
        },
    )

    # スタイル定義を追加
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

    # 矢印マーカーを追加
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

    # スイムレーンを描画
    cumulative_y = BPMN_MARGIN
    for actor in sorted(flow.get("actors", []), key=lambda a: actor_order.get(a["id"], 0)):
        actor_id = actor["id"]
        height = lane_heights.get(actor_id, 150)

        # レーン背景
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

        # レーンラベル（左側に回転）
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

    # タスクを描画
    for node in node_positions.values():
        if node.kind == "task":
            # タスクタイプを決定するためにタスク詳細を検索
            task_def = next((t for t in flow.get("tasks", []) if t["id"] == node.node_id), {})
            actor_id = task_def.get("actor_id")
            actor = next((a for a in flow.get("actors", []) if a["id"] == actor_id), {})
            is_service_task = actor.get("type") == "system"

            # タスク矩形を描画
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

            # タスクラベルを描画（必要に応じてテキスト折り返し）
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
            # ゲートウェイタイプを決定するためにゲートウェイ詳細を検索
            gateway_def = next((g for g in flow.get("gateways", []) if g["id"] == node.node_id), {})
            gateway_type = gateway_def.get("type", "exclusive")

            # ゲートウェイダイヤモンドを描画
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

            # ゲートウェイマーカーを描画
            if gateway_type == "exclusive":
                # Xマーカー
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
                # +マーカー
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
                # ○マーカー
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

            # ゲートウェイラベル（下側）
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

    # シーケンスフローを描画
    for edge in edge_waypoints:
        # フローラインを描画
        if len(edge.waypoints) >= 2:
            # パスを作成
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

            # 条件ラベルが存在する場合は描画
            if edge.condition:
                # 中点にラベルを配置
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

    # 文字列に変換
    svg_string = tostring(svg, encoding="unicode", method="xml")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{svg_string}'


def save_bpmn(bpmn_xml: str, output_path: Path) -> None:
    """BPMNXMLをファイルに保存する。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(bpmn_xml, encoding="utf-8")


def save_svg(svg_content: str, output_path: Path) -> None:
    """SVGをファイルに保存する。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")


def determine_output_paths(input_path: Path, output_arg: Path, svg_output_arg: Path = None) -> Tuple[Path, Path]:
    """
    BPMNとSVGファイルの出力パスを決定する。

    入力がruns/構造内の場合、同じrunディレクトリに出力する。
    それ以外の場合は、指定された出力パスを使用する。

    Args:
        input_path: 入力JSONファイルパス
        output_arg: CLI引数からのBPMN出力パス
        svg_output_arg: CLI引数からのSVG出力パス（オプション）

    Returns:
        (bpmn_path, svg_path)のタプル
    """
    input_path = input_path.resolve()

    # 入力がruns/構造内かチェック
    if "runs" in input_path.parts:
        # runディレクトリを検索
        run_dir = None
        for i, part in enumerate(input_path.parts):
            if part == "runs" and i + 1 < len(input_path.parts):
                run_dir = Path(*input_path.parts[:i+2])
                break

        if run_dir and run_dir.exists():
            # runs/YYYYMMDD_HHMMSS_name/output/に出力
            output_dir = run_dir / "output"
            bpmn_path = output_dir / "flow.bpmn"
            svg_path = output_dir / "flow-bpmn.svg"
            return bpmn_path, svg_path

    # デフォルト動作: 指定された出力パスを使用
    bpmn_path = output_arg
    if svg_output_arg:
        svg_path = svg_output_arg
    else:
        # BPMNパスに基づくデフォルトSVGパス
        svg_path = bpmn_path.parent / f"{bpmn_path.stem}-bpmn.svg"

    return bpmn_path, svg_path


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する。"""
    parser = argparse.ArgumentParser(
        description="Business-flow-maker JSONをSVG可視化付きBPMN 2.0 XMLに変換"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="入力JSONファイルパス",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/flow.bpmn"),
        help="出力BPMNファイルパス (デフォルト: output/flow.bpmn、またはruns/から自動検出)",
    )
    parser.add_argument(
        "--svg-output",
        type=Path,
        default=None,
        help="出力SVGファイルパス (デフォルト: BPMNと同じディレクトリに-bpmn.svg接尾辞)",
    )
    parser.add_argument(
        "--no-svg",
        action="store_true",
        help="SVG生成を無効化",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="生成後にBPMNを検証",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグログを有効化",
    )
    return parser.parse_args()


def main() -> None:
    """メインエントリーポイント。"""
    args = parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Loading flow from {args.input}")
    flow = load_flow_json(args.input)

    # 出力パスを決定（runs/構造の自動検出を処理）
    bpmn_path, svg_path = determine_output_paths(args.input, args.output, args.svg_output)

    logger.info("Converting to BPMN 2.0 XML")
    bpmn_xml = convert_to_bpmn(flow)

    logger.info(f"Saving BPMN to {bpmn_path}")
    save_bpmn(bpmn_xml, bpmn_path)

    # 無効化されていない場合はSVGを生成
    svg_generated = False
    if not args.no_svg:
        logger.info("Generating BPMN SVG visualization")
        # レイアウト計算（変換から再利用）
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

    # 要求された場合はBPMNを検証
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

    # runs/構造内の場合はinfo.mdを更新
    input_path = args.input.resolve()
    if "runs" in input_path.parts:
        # runディレクトリを検索
        run_dir = None
        for i, part in enumerate(input_path.parts):
            if part == "runs" and i + 1 < len(input_path.parts):
                run_dir = Path(*input_path.parts[:i+2])
                break

        if run_dir and run_dir.exists() and (run_dir / "info.md").exists():
            try:
                from src.utils import run_manager

                # 出力ファイル情報を準備
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

                # BPMN変換情報を準備
                bpmn_info = {
                    "svg_generated": svg_generated,
                }
                if validation_passed is not None:
                    bpmn_info["validation_passed"] = validation_passed

                # info.mdを更新
                run_manager.update_info_md(run_dir, {
                    "bpmn_conversion": bpmn_info,
                    "output_files": output_files,
                })

                logger.info(f"Updated execution info in {run_dir / 'info.md'}")
            except Exception as e:
                logger.warning(f"Failed to update info.md: {e}")


if __name__ == "__main__":
    main()
