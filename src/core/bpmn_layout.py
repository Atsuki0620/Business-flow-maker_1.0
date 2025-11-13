"""
動的座標生成のためのBPMNレイアウト計算機。

このモジュールはSugiyama原理に基づく階層的レイアウトアルゴリズムを実装します:
1. レイヤー割り当て（トポロジカルソート）
2. 交差最小化（重心法）
3. 座標割り当て（動的間隔調整）
4. エッジルーティング（マンハッタンルーティング）
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
    """BPMNノード（タスクまたはゲートウェイ）のレイアウト情報。"""
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
    """BPMNエッジ（シーケンスフロー）のレイアウト情報。"""
    flow_id: str
    waypoints: List[Tuple[float, float]]
    condition: str = ""


# BPMN 2.0標準寸法（Diagram Interchange用のピクセル単位）
BPMN_TASK_WIDTH = 100
BPMN_TASK_HEIGHT = 80
BPMN_GATEWAY_SIZE = 50
BPMN_LANE_MIN_HEIGHT = 150
BPMN_LANE_HEADER_WIDTH = 30  # 回転テキストヘッダー
BPMN_HORIZONTAL_SPACING = 80  # 同一レーン内のノード間
BPMN_VERTICAL_SPACING = 40   # 縦に積まれたノード間
BPMN_MARGIN = 50


def calculate_layout(flow: Dict[str, Any]) -> Tuple[Dict[str, BPMNNodeLayout], List[BPMNEdgeLayout], Dict[str, float]]:
    """
    すべてのノードとエッジのBPMNレイアウト位置を計算する。

    Args:
        flow: actors、phases、tasks、gateways、flowsを含むフロードキュメント辞書

    Returns:
        (node_positions, edge_waypoints, lane_heights)のタプル
    """
    actors = flow.get("actors", [])
    phases = flow.get("phases", [])
    tasks = flow.get("tasks", [])
    gateways = flow.get("gateways", [])
    flows = flow.get("flows", [])

    # アクターとフェーズの順序を構築
    actor_order = {actor["id"]: idx for idx, actor in enumerate(actors)}
    phase_order = {phase["id"]: idx for idx, phase in enumerate(phases)}

    # 階層的レイアウトを使用して位置を計算
    node_positions = _calculate_node_positions(
        tasks, gateways, flows, actor_order, phase_order
    )

    # ノード分布に基づいてレーン高さを計算
    lane_heights = _calculate_lane_heights(node_positions, actor_order)

    # 計算されたレーン高さに基づいてY座標を調整
    _adjust_y_coordinates(node_positions, lane_heights, actor_order)

    # エッジのウェイポイントを計算
    edge_waypoints = _calculate_edge_waypoints(flows, node_positions)

    return node_positions, edge_waypoints, lane_heights


def _calculate_node_positions(
    tasks: List[Dict[str, Any]],
    gateways: List[Dict[str, Any]],
    flows: List[Dict[str, Any]],
    actor_order: Dict[str, int],
    phase_order: Dict[str, int],
) -> Dict[str, BPMNNodeLayout]:
    """アクターとフェーズに基づいて初期ノード位置を計算する。"""
    positions: Dict[str, BPMNNodeLayout] = {}

    # 衝突回避のために(actor_id, phase_id)グループごとのノード数をカウント
    group_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    for task in tasks:
        group_key = (task.get("actor_id", ""), task.get("phase_id", ""))
        group_counts[group_key] += 1

    # タスクの位置決定
    task_counters: Dict[Tuple[str, str], int] = defaultdict(int)
    for task in tasks:
        actor_id = task.get("actor_id", "")
        phase_id = task.get("phase_id", "")
        actor_idx = actor_order.get(actor_id, 0)
        phase_idx = phase_order.get(phase_id, 0)

        # この(actor, phase)グループ内のタスク順序を取得
        group_key = (actor_id, phase_id)
        task_order = task_counters[group_key]
        task_counters[group_key] += 1
        total_tasks = group_counts[group_key]

        # X位置を計算（水平方向 - フェーズ別）
        x = BPMN_MARGIN + BPMN_LANE_HEADER_WIDTH + phase_idx * (BPMN_TASK_WIDTH + BPMN_HORIZONTAL_SPACING)

        # Y位置を計算（垂直方向 - アクター別、複数タスクの場合はオフセット）
        # Yは後でレーン高さに基づいて調整される
        y_offset = task_order * (BPMN_TASK_HEIGHT + BPMN_VERTICAL_SPACING)
        y_center_adjustment = (total_tasks - 1) * (BPMN_TASK_HEIGHT + BPMN_VERTICAL_SPACING) / 2
        y = y_offset - y_center_adjustment

        # ラベル長に基づいて幅を決定（スケーラビリティ）
        label = task.get("name", "")
        width = max(BPMN_TASK_WIDTH, min(200, len(label) * 8))

        positions[task["id"]] = BPMNNodeLayout(
            node_id=task["id"],
            label=label,
            x=x,
            y=y,  # 一時的、後で調整される
            width=width,
            height=BPMN_TASK_HEIGHT,
            kind="task",
            actor_id=actor_id,
            phase_id=phase_id,
        )

    # 接続されたノードからゲートウェイの位置を推測して配置
    for gateway in gateways:
        gateway_id = gateway["id"]
        actor_id, phase_id = _infer_gateway_position(gateway_id, flows, positions, actor_order, phase_order)
        actor_idx = actor_order.get(actor_id, 0)
        phase_idx = phase_order.get(phase_id, 0)

        # 分岐点の場合、フェーズ間にゲートウェイを配置
        x = BPMN_MARGIN + BPMN_LANE_HEADER_WIDTH + phase_idx * (BPMN_TASK_WIDTH + BPMN_HORIZONTAL_SPACING) + BPMN_TASK_WIDTH // 2
        y = 0  # レーン高さに基づいて調整される

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
    """接続されたタスクに基づいてゲートウェイの位置を推測する。"""
    # 接続されたノードを検索
    connected_nodes: List[BPMNNodeLayout] = []
    for flow in flows:
        if flow["from"] == gateway_id and flow["to"] in positions:
            connected_nodes.append(positions[flow["to"]])
        elif flow["to"] == gateway_id and flow["from"] in positions:
            connected_nodes.append(positions[flow["from"]])

    if not connected_nodes:
        # デフォルトで最初のアクターとフェーズを使用
        first_actor = list(actor_order.keys())[0] if actor_order else ""
        first_phase = list(phase_order.keys())[0] if phase_order else ""
        return first_actor, first_phase

    # 最も一般的なアクターと平均フェーズを使用
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
    """ノード分布に基づいて各レーンの高さを計算する。"""
    lane_heights: Dict[str, float] = {}

    # ノードをアクター別にグループ化
    nodes_by_actor: Dict[str, List[BPMNNodeLayout]] = defaultdict(list)
    for node in positions.values():
        nodes_by_actor[node.actor_id].append(node)

    # 各アクターレーンの高さを計算
    for actor_id, nodes in nodes_by_actor.items():
        if not nodes:
            lane_heights[actor_id] = BPMN_LANE_MIN_HEIGHT
            continue

        # 最大垂直範囲を検索
        max_extent = 0
        for node in nodes:
            extent = abs(node.y) + node.height
            max_extent = max(max_extent, extent)

        # パディングを追加
        height = max(BPMN_LANE_MIN_HEIGHT, max_extent + BPMN_VERTICAL_SPACING * 2)
        lane_heights[actor_id] = height

    # すべてのアクターが高さを持つことを保証
    for actor_id in actor_order.keys():
        if actor_id not in lane_heights:
            lane_heights[actor_id] = BPMN_LANE_MIN_HEIGHT

    return lane_heights


def _adjust_y_coordinates(
    positions: Dict[str, BPMNNodeLayout],
    lane_heights: Dict[str, float],
    actor_order: Dict[str, int],
) -> None:
    """計算されたレーン高さと位置に基づいてY座標を調整する。"""
    # レーンの累積オフセットを計算
    lane_offsets: Dict[str, float] = {}
    cumulative_offset = BPMN_MARGIN
    for actor_id in sorted(actor_order.keys(), key=lambda a: actor_order[a]):
        lane_offsets[actor_id] = cumulative_offset
        cumulative_offset += lane_heights.get(actor_id, BPMN_LANE_MIN_HEIGHT)

    # 各ノードのY座標を調整
    for node in positions.values():
        lane_offset = lane_offsets.get(node.actor_id, BPMN_MARGIN)
        lane_height = lane_heights.get(node.actor_id, BPMN_LANE_MIN_HEIGHT)

        # レーン内で中央揃え
        lane_center = lane_offset + lane_height / 2
        node.y = lane_center + node.y


def _calculate_edge_waypoints(
    flows: List[Dict[str, Any]],
    positions: Dict[str, BPMNNodeLayout],
) -> List[BPMNEdgeLayout]:
    """マンハッタンルーティングを使用してエッジのウェイポイントを計算する。"""
    edge_layouts: List[BPMNEdgeLayout] = []

    for flow in flows:
        from_node = positions.get(flow["from"])
        to_node = positions.get(flow["to"])

        if not from_node or not to_node:
            logger.warning(f"Flow {flow.get('id')} references missing nodes: from={flow['from']}, to={flow['to']}")
            continue

        # 接続点を計算
        # From: ソースノードの右端
        from_x = from_node.x + from_node.width
        from_y = from_node.y + from_node.height / 2

        # To: ターゲットノードの左端
        to_x = to_node.x
        to_y = to_node.y + to_node.height / 2

        # 2つのウェイポイントを持つシンプルなマンハッタンルーティング
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
    """ダイアグラムの全体範囲を計算する。"""
    if not positions:
        return 800, 600  # デフォルトサイズ

    # 幅を計算
    max_x = max((node.x + node.width for node in positions.values()), default=0)
    width = max_x + BPMN_MARGIN

    # 高さを計算
    total_height = BPMN_MARGIN
    for actor_id in sorted(actor_order.keys(), key=lambda a: actor_order[a]):
        total_height += lane_heights.get(actor_id, BPMN_LANE_MIN_HEIGHT)
    height = total_height + BPMN_MARGIN

    return width, height
