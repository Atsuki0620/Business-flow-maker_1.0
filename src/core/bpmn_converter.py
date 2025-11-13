"""
BPMN 2.0準拠のXML出力・SVG可視化機能の中核モジュール。

JSON形式の業務フローデータからBPMN 2.0 XMLを生成し、
同時に専用ソフトウェアなしでブラウザ上で確認可能なSVG画像を生成します。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from src.core.bpmn_layout import BPMNLayoutEngine, BPMNNodeLayout, BPMNLaneLayout
from src.core.bpmn_validator import validate_bpmn

logger = logging.getLogger(__name__)


class BPMNConverter:
    """JSON形式の業務フローデータをBPMN 2.0 XMLに変換するクラス。"""

    # BPMN 2.0名前空間
    NAMESPACES = {
        'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc': 'http://www.omg.org/spec/DD/20100524/DC',
        'di': 'http://www.omg.org/spec/DD/20100524/DI',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    }

    def __init__(self, flow: Dict[str, Any]):
        """
        Args:
            flow: JSON形式の業務フローデータ
        """
        self.flow = flow
        self.actors = flow.get("actors", [])
        self.phases = flow.get("phases", [])
        self.tasks = flow.get("tasks", [])
        self.gateways = flow.get("gateways", [])
        self.flows_data = flow.get("flows", [])
        self.metadata = flow.get("metadata", {})

        # レイアウトエンジンの初期化
        self.layout_engine = BPMNLayoutEngine(flow)
        self.node_layouts: Dict[str, BPMNNodeLayout] = {}
        self.lane_layouts: List[BPMNLaneLayout] = []

    def convert_to_bpmn(self) -> str:
        """
        JSON形式の業務フローをBPMN 2.0 XMLに変換する。

        Returns:
            BPMN 2.0準拠のXML文字列
        """
        # レイアウト計算
        self.node_layouts, self.lane_layouts = self.layout_engine.calculate_layout()

        # definitions要素（ルート）
        definitions = Element('bpmn2:definitions', attrib={
            'xmlns:bpmn2': self.NAMESPACES['bpmn2'],
            'xmlns:bpmndi': self.NAMESPACES['bpmndi'],
            'xmlns:dc': self.NAMESPACES['dc'],
            'xmlns:di': self.NAMESPACES['di'],
            'xmlns:xsi': self.NAMESPACES['xsi'],
            'id': f"Definitions_{self.metadata.get('id', 'flow')}",
            'targetNamespace': 'http://bpmn.io/schema/bpmn',
            'exporter': 'Business-flow-maker',
            'exporterVersion': '1.0',
        })

        # collaboration要素（スイムレーン構造）
        process_id = f"Process_{self.metadata.get('id', 'main')}"
        if self.actors:
            collaboration = SubElement(definitions, 'bpmn2:collaboration', attrib={
                'id': f"Collaboration_{self.metadata.get('id', 'flow')}",
            })

            for actor in self.actors:
                SubElement(collaboration, 'bpmn2:participant', attrib={
                    'id': f"Participant_{actor['id']}",
                    'name': actor.get('name', actor['id']),
                    'processRef': process_id,
                })

        # process要素
        process = SubElement(definitions, 'bpmn2:process', attrib={
            'id': process_id,
            'name': self.metadata.get('title', 'Business Process'),
            'isExecutable': 'false',
        })

        # laneSet要素
        if self.actors:
            lane_set = SubElement(process, 'bpmn2:laneSet', attrib={
                'id': 'LaneSet_1',
            })

            for actor in self.actors:
                lane = SubElement(lane_set, 'bpmn2:lane', attrib={
                    'id': f"Lane_{actor['id']}",
                    'name': actor.get('name', actor['id']),
                })

                # このレーンに属するノードのIDを列挙
                flow_node_refs = []
                for task in self.tasks:
                    if task.get('actor_id') == actor['id']:
                        flow_node_refs.append(task['id'])

                for node_id in flow_node_refs:
                    SubElement(lane, 'bpmn2:flowNodeRef').text = node_id

        # タスク要素の追加
        self._add_tasks(process)

        # ゲートウェイ要素の追加
        self._add_gateways(process)

        # シーケンスフロー要素の追加
        self._add_sequence_flows(process)

        # 図形情報の追加
        self._add_diagram(definitions)

        # XML文字列に変換（整形あり）
        xml_str = self._prettify_xml(definitions)
        return xml_str

    def _add_tasks(self, process: Element) -> None:
        """タスク要素をprocessに追加する。"""
        for task in self.tasks:
            task_id = task['id']
            task_name = task.get('name', task_id)
            task_type = task.get('type', 'user')

            # タスクタイプに応じて要素を作成
            if task_type == 'service':
                task_elem = SubElement(process, 'bpmn2:serviceTask', attrib={
                    'id': task_id,
                    'name': task_name,
                })
            else:
                task_elem = SubElement(process, 'bpmn2:userTask', attrib={
                    'id': task_id,
                    'name': task_name,
                })

            # ノートがあればdocumentation要素を追加
            if task.get('notes'):
                documentation = SubElement(task_elem, 'bpmn2:documentation')
                documentation.text = task['notes']

    def _add_gateways(self, process: Element) -> None:
        """ゲートウェイ要素をprocessに追加する。"""
        for gateway in self.gateways:
            gw_id = gateway['id']
            gw_name = gateway.get('name', '')
            gw_type = gateway.get('type', 'exclusive').lower()

            # ゲートウェイタイプに応じて要素を作成
            if gw_type == 'parallel':
                gw_elem = SubElement(process, 'bpmn2:parallelGateway', attrib={
                    'id': gw_id,
                    'name': gw_name,
                })
            elif gw_type == 'inclusive':
                gw_elem = SubElement(process, 'bpmn2:inclusiveGateway', attrib={
                    'id': gw_id,
                    'name': gw_name,
                })
            else:  # exclusive (default)
                gw_elem = SubElement(process, 'bpmn2:exclusiveGateway', attrib={
                    'id': gw_id,
                    'name': gw_name,
                })

            # ノートがあればdocumentation要素を追加
            if gateway.get('notes'):
                documentation = SubElement(gw_elem, 'bpmn2:documentation')
                documentation.text = gateway['notes']

    def _add_sequence_flows(self, process: Element) -> None:
        """シーケンスフロー要素をprocessに追加する。"""
        for flow in self.flows_data:
            flow_id = flow.get('id', f"Flow_{flow['from']}_to_{flow['to']}")
            source_ref = flow['from']
            target_ref = flow['to']

            seq_flow = SubElement(process, 'bpmn2:sequenceFlow', attrib={
                'id': flow_id,
                'sourceRef': source_ref,
                'targetRef': target_ref,
            })

            # 条件がある場合はname属性に設定
            if flow.get('condition'):
                seq_flow.attrib['name'] = flow['condition']

    def _add_diagram(self, definitions: Element) -> None:
        """図形情報（BPMNDiagram）を追加する。"""
        diagram = SubElement(definitions, 'bpmndi:BPMNDiagram', attrib={
            'id': f"BPMNDiagram_{self.metadata.get('id', 'flow')}",
        })

        plane = SubElement(diagram, 'bpmndi:BPMNPlane', attrib={
            'id': f"BPMNPlane_{self.metadata.get('id', 'flow')}",
            'bpmnElement': f"Process_{self.metadata.get('id', 'main')}",
        })

        # ノード形状の追加
        for node_id, layout in self.node_layouts.items():
            shape = SubElement(plane, 'bpmndi:BPMNShape', attrib={
                'id': f"Shape_{node_id}",
                'bpmnElement': node_id,
            })

            SubElement(shape, 'dc:Bounds', attrib={
                'x': str(layout.x),
                'y': str(layout.y),
                'width': str(layout.width),
                'height': str(layout.height),
            })

        # エッジの追加
        for flow in self.flows_data:
            flow_id = flow.get('id', f"Flow_{flow['from']}_to_{flow['to']}")
            source_layout = self.node_layouts.get(flow['from'])
            target_layout = self.node_layouts.get(flow['to'])

            if source_layout and target_layout:
                edge = SubElement(plane, 'bpmndi:BPMNEdge', attrib={
                    'id': f"Edge_{flow_id}",
                    'bpmnElement': flow_id,
                })

                # 開始点（ソースの右端中央）
                start_x = source_layout.x + source_layout.width
                start_y = source_layout.y + source_layout.height / 2

                # 終了点（ターゲットの左端中央）
                end_x = target_layout.x
                end_y = target_layout.y + target_layout.height / 2

                SubElement(edge, 'di:waypoint', attrib={
                    'x': str(start_x),
                    'y': str(start_y),
                })

                SubElement(edge, 'di:waypoint', attrib={
                    'x': str(end_x),
                    'y': str(end_y),
                })

    def _prettify_xml(self, elem: Element) -> str:
        """XML要素を整形された文字列に変換する。"""
        rough_string = tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=None)


class BPMNSVGGenerator:
    """BPMN準拠のSVG画像を生成するクラス。"""

    def __init__(self, flow: Dict[str, Any], node_layouts: Dict[str, BPMNNodeLayout], lane_layouts: List[BPMNLaneLayout]):
        """
        Args:
            flow: JSON形式の業務フローデータ
            node_layouts: ノードレイアウト情報
            lane_layouts: レーンレイアウト情報
        """
        self.flow = flow
        self.node_layouts = node_layouts
        self.lane_layouts = lane_layouts
        self.tasks = flow.get("tasks", [])
        self.gateways = flow.get("gateways", [])
        self.flows_data = flow.get("flows", [])

    def generate_svg(self) -> str:
        """
        BPMN準拠のSVG画像を生成する。

        Returns:
            SVG形式の文字列
        """
        # SVG全体のサイズを計算
        width = max(lane.x + lane.width for lane in self.lane_layouts) + 50 if self.lane_layouts else 800
        height = max(lane.y + lane.height for lane in self.lane_layouts) + 50 if self.lane_layouts else 600

        svg = Element('svg', attrib={
            'xmlns': 'http://www.w3.org/2000/svg',
            'viewBox': f'0 0 {int(width)} {int(height)}',
            'width': str(int(width)),
            'height': str(int(height)),
        })

        # スタイル定義
        style = SubElement(svg, 'style')
        style.text = """
            .lane { fill: #f8f8f8; stroke: #000; stroke-width: 1; }
            .lane-label { font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
            .task { fill: #fff; stroke: #000; stroke-width: 2; }
            .service-task { fill: #e1f5ff; stroke: #000; stroke-width: 2; }
            .gateway { fill: #fffacd; stroke: #000; stroke-width: 2; }
            .task-label { font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }
            .flow { stroke: #000; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
            .flow-label { font-family: Arial, sans-serif; font-size: 10px; fill: #666; }
        """

        # 矢印マーカーの定義
        defs = SubElement(svg, 'defs')
        marker = SubElement(defs, 'marker', attrib={
            'id': 'arrowhead',
            'markerWidth': '10',
            'markerHeight': '10',
            'refX': '10',
            'refY': '3',
            'orient': 'auto',
        })
        SubElement(marker, 'path', attrib={
            'd': 'M0,0 L10,3 L0,6 Z',
            'fill': '#000',
        })

        # スイムレーンの描画
        for lane in self.lane_layouts:
            SubElement(svg, 'rect', attrib={
                'class': 'lane',
                'x': str(lane.x),
                'y': str(lane.y),
                'width': str(lane.width),
                'height': str(lane.height),
            })

            # レーンラベル（縦書き風に配置）
            label_x = lane.x + 15
            label_y = lane.y + 30
            SubElement(svg, 'text', attrib={
                'class': 'lane-label',
                'x': str(label_x),
                'y': str(label_y),
            }).text = lane.label

        # フロー（エッジ）の描画（ノードの下に描画するため先に）
        for flow in self.flows_data:
            source_layout = self.node_layouts.get(flow['from'])
            target_layout = self.node_layouts.get(flow['to'])

            if source_layout and target_layout:
                # 開始点と終了点の計算
                start_x = source_layout.x + source_layout.width
                start_y = source_layout.y + source_layout.height / 2
                end_x = target_layout.x
                end_y = target_layout.y + target_layout.height / 2

                SubElement(svg, 'line', attrib={
                    'class': 'flow',
                    'x1': str(start_x),
                    'y1': str(start_y),
                    'x2': str(end_x),
                    'y2': str(end_y),
                })

                # 条件ラベルの描画
                if flow.get('condition'):
                    label_x = (start_x + end_x) / 2
                    label_y = (start_y + end_y) / 2 - 5
                    SubElement(svg, 'text', attrib={
                        'class': 'flow-label',
                        'x': str(label_x),
                        'y': str(label_y),
                        'text-anchor': 'middle',
                    }).text = flow['condition']

        # タスクの描画
        for task in self.tasks:
            layout = self.node_layouts.get(task['id'])
            if not layout:
                continue

            task_type = task.get('type', 'user')
            css_class = 'service-task' if task_type == 'service' else 'task'

            # タスク矩形（角丸）
            SubElement(svg, 'rect', attrib={
                'class': css_class,
                'x': str(layout.x),
                'y': str(layout.y),
                'width': str(layout.width),
                'height': str(layout.height),
                'rx': '8',
                'ry': '8',
            })

            # タスクラベル
            label_x = layout.x + layout.width / 2
            label_y = layout.y + layout.height / 2 + 5
            SubElement(svg, 'text', attrib={
                'class': 'task-label',
                'x': str(label_x),
                'y': str(label_y),
            }).text = layout.label

        # ゲートウェイの描画
        for gateway in self.gateways:
            layout = self.node_layouts.get(gateway['id'])
            if not layout:
                continue

            gw_type = gateway.get('type', 'exclusive').lower()

            # ゲートウェイ菱形
            center_x = layout.x + layout.width / 2
            center_y = layout.y + layout.height / 2
            half_size = layout.width / 2

            points = [
                (center_x, center_y - half_size),  # 上
                (center_x + half_size, center_y),  # 右
                (center_x, center_y + half_size),  # 下
                (center_x - half_size, center_y),  # 左
            ]

            SubElement(svg, 'polygon', attrib={
                'class': 'gateway',
                'points': ' '.join(f'{x},{y}' for x, y in points),
            })

            # ゲートウェイタイプのマーカー
            if gw_type == 'exclusive':
                # × マーク
                offset = half_size * 0.4
                SubElement(svg, 'line', attrib={
                    'x1': str(center_x - offset),
                    'y1': str(center_y - offset),
                    'x2': str(center_x + offset),
                    'y2': str(center_y + offset),
                    'stroke': '#000',
                    'stroke-width': '2',
                })
                SubElement(svg, 'line', attrib={
                    'x1': str(center_x + offset),
                    'y1': str(center_y - offset),
                    'x2': str(center_x - offset),
                    'y2': str(center_y + offset),
                    'stroke': '#000',
                    'stroke-width': '2',
                })
            elif gw_type == 'parallel':
                # + マーク
                offset = half_size * 0.4
                SubElement(svg, 'line', attrib={
                    'x1': str(center_x),
                    'y1': str(center_y - offset),
                    'x2': str(center_x),
                    'y2': str(center_y + offset),
                    'stroke': '#000',
                    'stroke-width': '2',
                })
                SubElement(svg, 'line', attrib={
                    'x1': str(center_x - offset),
                    'y1': str(center_y),
                    'x2': str(center_x + offset),
                    'y2': str(center_y),
                    'stroke': '#000',
                    'stroke-width': '2',
                })
            elif gw_type == 'inclusive':
                # ○ マーク
                radius = half_size * 0.4
                SubElement(svg, 'circle', attrib={
                    'cx': str(center_x),
                    'cy': str(center_y),
                    'r': str(radius),
                    'fill': 'none',
                    'stroke': '#000',
                    'stroke-width': '2',
                })

            # ゲートウェイラベル（下側に配置）
            if layout.label:
                label_y = layout.y + layout.height + 15
                SubElement(svg, 'text', attrib={
                    'class': 'task-label',
                    'x': str(center_x),
                    'y': str(label_y),
                }).text = layout.label

        # XML宣言付きで返す
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += tostring(svg, encoding='unicode')
        return xml_str


def convert_json_to_bpmn(
    json_path: Path,
    bpmn_output: Optional[Path] = None,
    svg_output: Optional[Union[Path, str]] = None,
    validate: bool = True,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    JSON形式の業務フローをBPMN 2.0 XMLとSVGに変換する。

    Args:
        json_path: 入力JSONファイルのパス
        bpmn_output: 出力BPMNファイルのパス（Noneの場合は自動決定）
        svg_output: 出力SVGファイルのパス（Noneの場合は自動決定）
        validate: 生成後に妥当性検証を実行するか
        debug: デバッグ情報を出力するか

    Returns:
        変換結果情報の辞書
    """
    # 入力ファイルの読み込み
    if not json_path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {json_path}")

    with json_path.open('r', encoding='utf-8') as f:
        flow = json.load(f)

    if debug:
        logger.info(f"入力ファイル読み込み完了: {json_path}")
        logger.info(f"  actors: {len(flow.get('actors', []))}")
        logger.info(f"  tasks: {len(flow.get('tasks', []))}")
        logger.info(f"  gateways: {len(flow.get('gateways', []))}")
        logger.info(f"  flows: {len(flow.get('flows', []))}")

    # 出力先の決定（runs構造の検出）
    auto_determine_svg = (svg_output == "auto")  # mainから"auto"が渡される場合のみ自動決定

    if bpmn_output is None or auto_determine_svg:
        resolved_json_path = json_path.resolve()

        # runs/構造の検出
        if "runs" in resolved_json_path.parts:
            run_dir = None
            for i, part in enumerate(resolved_json_path.parts):
                if part == "runs" and i + 1 < len(resolved_json_path.parts):
                    run_dir = Path(*resolved_json_path.parts[:i+2])
                    break

            if run_dir and run_dir.exists():
                output_dir = run_dir / "output"
                output_dir.mkdir(exist_ok=True)

                if bpmn_output is None:
                    bpmn_output = output_dir / "flow.bpmn"
                if auto_determine_svg:
                    svg_output = output_dir / "flow-bpmn.svg"
        else:
            # runs構造ではない場合のデフォルト
            if bpmn_output is None:
                bpmn_output = Path("output") / "flow.bpmn"
            if auto_determine_svg:
                svg_output = Path("output") / "flow-bpmn.svg"

    # BPMN XML変換
    converter = BPMNConverter(flow)
    bpmn_xml = converter.convert_to_bpmn()

    # BPMNファイルの保存
    bpmn_output.parent.mkdir(parents=True, exist_ok=True)
    bpmn_output.write_text(bpmn_xml, encoding='utf-8')

    if debug:
        logger.info(f"BPMN XMLファイル生成完了: {bpmn_output}")

    # 妥当性検証
    validation_result = None
    if validate:
        is_valid, errors, warnings, stats = validate_bpmn(bpmn_xml)
        validation_result = {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'statistics': stats,
        }

        if debug:
            logger.info(f"BPMN妥当性検証結果: {'成功' if is_valid else '失敗'}")
            if errors:
                for error in errors:
                    logger.error(f"  エラー: {error}")
            if warnings:
                for warning in warnings:
                    logger.warning(f"  警告: {warning}")

    # SVG生成
    if svg_output is not None and isinstance(svg_output, Path):
        svg_generator = BPMNSVGGenerator(flow, converter.node_layouts, converter.lane_layouts)
        svg_content = svg_generator.generate_svg()

        # SVGファイルの保存
        svg_output.parent.mkdir(parents=True, exist_ok=True)
        svg_output.write_text(svg_content, encoding='utf-8')

        if debug:
            logger.info(f"SVGファイル生成完了: {svg_output}")

    # runs構造の場合はinfo.mdを更新
    if "runs" in json_path.resolve().parts:
        try:
            from src.utils import run_manager

            run_dir = None
            for i, part in enumerate(json_path.resolve().parts):
                if part == "runs" and i + 1 < len(json_path.resolve().parts):
                    run_dir = Path(*json_path.resolve().parts[:i+2])
                    break

            if run_dir and run_dir.exists() and (run_dir / "info.md").exists():
                # 出力ファイル情報
                output_files = [
                    {"path": str(bpmn_output.relative_to(run_dir)), "size": bpmn_output.stat().st_size},
                ]
                if svg_output is not None and isinstance(svg_output, Path) and svg_output.exists():
                    output_files.append(
                        {"path": str(svg_output.relative_to(run_dir)), "size": svg_output.stat().st_size}
                    )

                update_data: Dict[str, Any] = {"output_files": output_files}

                # 検証結果も追加
                if validation_result:
                    update_data["bpmn_validation"] = validation_result

                run_manager.update_info_md(run_dir, update_data)

                if debug:
                    logger.info(f"実行情報を {run_dir / 'info.md'} に追記しました")
        except Exception as e:
            logger.warning(f"info.md更新に失敗しました: {e}")

    result = {
        'bpmn_path': str(bpmn_output),
        'validation': validation_result,
    }
    if svg_output is not None and isinstance(svg_output, Path):
        result['svg_path'] = str(svg_output)

    return result


def main() -> int:
    """CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(
        description='JSON形式の業務フローをBPMN 2.0 XMLとSVGに変換します。'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='入力JSONファイルのパス',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='出力BPMNファイルのパス（デフォルト: output/flow.bpmn、runs検出時は自動決定）',
    )
    parser.add_argument(
        '--svg-output',
        type=Path,
        help='SVGファイルの出力先（省略時は自動決定）',
    )
    parser.add_argument(
        '--no-svg',
        action='store_true',
        help='SVG生成を無効化',
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='生成後の妥当性検証実行（デフォルト: 有効）',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグ情報出力',
    )

    args = parser.parse_args()

    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='[%(levelname)s] %(message)s',
    )

    try:
        # SVG出力先の決定：--no-svgが指定された場合はNone、指定なしで--svg-outputも指定されていない場合は"auto"
        svg_out = None if args.no_svg else (args.svg_output if args.svg_output else "auto")

        result = convert_json_to_bpmn(
            json_path=args.input,
            bpmn_output=args.output,
            svg_output=svg_out,
            validate=args.validate,
            debug=args.debug,
        )

        print(f"✓ BPMN変換完了: {result['bpmn_path']}")
        if 'svg_path' in result:
            print(f"✓ SVG生成完了: {result['svg_path']}")

        if result.get('validation'):
            val = result['validation']
            if val['is_valid']:
                print("✓ BPMN妥当性検証: 成功")
            else:
                print("✗ BPMN妥当性検証: 失敗")
                for error in val['errors']:
                    print(f"  - {error}")
                return 1

        return 0

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=args.debug)
        return 1


if __name__ == '__main__':
    sys.exit(main())
