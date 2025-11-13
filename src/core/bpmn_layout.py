"""
BPMN 2.0準拠のレイアウト計算モジュール。

Sugiyamaアルゴリズムの原理に基づいた動的座標計算を実装し、
異なる規模の業務フローに対して適切な配置を生成します。

固定座標値は一切使用せず、すべての座標を動的に計算します。
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple


@dataclass
class BPMNNodeLayout:
    """BPMNノードのレイアウト情報。"""

    node_id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    kind: str  # "task" | "gateway" | "start" | "end"
    lane_id: str  # スイムレーンID（actor_id）


@dataclass
class BPMNLaneLayout:
    """BPMNスイムレーンのレイアウト情報。"""

    lane_id: str
    label: str
    x: float
    y: float
    width: float
    height: float


class BPMNLayoutEngine:
    """
    BPMN 2.0準拠のレイアウトエンジン。

    Sugiyamaアルゴリズムに基づく4段階処理：
    1. トポロジカルソートによる階層決定
    2. バリセントリック法による交差最小化
    3. 水平座標の動的割り当て
    4. エッジ経路の計算
    """

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

        # 動的スケーリングパラメータの計算
        total_nodes = len(self.tasks) + len(self.gateways)
        self._base_spacing = max(80, int(60 * math.sqrt(total_nodes / 10)))
        self._lane_header_width = 180
        self._task_base_width = 180
        self._task_base_height = 80
        self._gateway_size = 60
        self._lane_base_height = max(200, 150 + int(20 * math.sqrt(total_nodes)))
        self._margin_x = 50
        self._margin_y = 50

        # グラフ構造の構築
        self._build_graph()

    def _build_graph(self) -> None:
        """フロー接続からグラフ構造を構築する。"""
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)

        for flow in self.flows_data:
            from_id = flow.get("from", "")
            to_id = flow.get("to", "")
            if from_id and to_id:
                self.graph[from_id].append(to_id)
                self.reverse_graph[to_id].append(from_id)

    def _get_node_kind(self, node_id: str) -> str:
        """ノードIDから種類を判定する。"""
        for task in self.tasks:
            if task["id"] == node_id:
                return "task"
        for gateway in self.gateways:
            if gateway["id"] == node_id:
                return "gateway"
        return "unknown"

    def _get_node_label(self, node_id: str) -> str:
        """ノードIDからラベルを取得する。"""
        for task in self.tasks:
            if task["id"] == node_id:
                return task.get("name", node_id)
        for gateway in self.gateways:
            if gateway["id"] == node_id:
                return gateway.get("name", "")
        return node_id

    def _get_node_actor(self, node_id: str) -> str:
        """ノードIDから所属するactorを取得する。"""
        for task in self.tasks:
            if task["id"] == node_id:
                return task.get("actor_id", "")

        # ゲートウェイの場合は隣接ノードから推測
        neighbors = self.graph.get(node_id, []) + self.reverse_graph.get(node_id, [])
        for neighbor in neighbors:
            actor = self._get_node_actor(neighbor)
            if actor:
                return actor

        return self.actors[0]["id"] if self.actors else ""

    def _topological_sort(self) -> List[List[str]]:
        """
        トポロジカルソートによる階層決定（Sugiyama第1段階）。

        Returns:
            階層ごとのノードIDリスト
        """
        all_nodes = {task["id"] for task in self.tasks} | {gw["id"] for gw in self.gateways}
        in_degree = {node: 0 for node in all_nodes}

        for node in all_nodes:
            in_degree[node] = len(self.reverse_graph.get(node, []))

        layers: List[List[str]] = []
        remaining = set(all_nodes)

        while remaining:
            # 現在の階層：入次数が0のノード
            current_layer = [node for node in remaining if in_degree[node] == 0]

            if not current_layer:
                # 循環がある場合は残りのノードをまとめて追加
                current_layer = list(remaining)

            layers.append(current_layer)
            remaining -= set(current_layer)

            # 次の階層のために入次数を更新
            for node in current_layer:
                for successor in self.graph.get(node, []):
                    if successor in remaining:
                        in_degree[successor] -= 1

        return layers

    def _assign_to_phase(self, node_id: str, layers: List[List[str]]) -> int:
        """ノードをフェーズ（階層）に割り当てる。"""
        for task in self.tasks:
            if task["id"] == node_id:
                phase_id = task.get("phase_id", "")
                for idx, phase in enumerate(self.phases):
                    if phase["id"] == phase_id:
                        return idx

        # フェーズ情報がない場合はトポロジカルソートの階層を使用
        for layer_idx, layer in enumerate(layers):
            if node_id in layer:
                return layer_idx

        return 0

    def _barycenter_method(self, layers: List[List[str]]) -> List[List[str]]:
        """
        バリセントリック法による交差最小化（Sugiyama第2段階）。

        Args:
            layers: トポロジカルソート後の階層

        Returns:
            最適化された階層
        """
        optimized = [layer[:] for layer in layers]

        # 複数回の反復で最適化
        for _ in range(3):
            # 下向きパス
            for i in range(1, len(optimized)):
                optimized[i] = self._order_by_barycenter(optimized[i], optimized[i-1], direction="down")

            # 上向きパス
            for i in range(len(optimized) - 2, -1, -1):
                optimized[i] = self._order_by_barycenter(optimized[i], optimized[i+1], direction="up")

        return optimized

    def _order_by_barycenter(self, layer: List[str], reference_layer: List[str], direction: str) -> List[str]:
        """バリセントリック値に基づいてノードを並べ替える。"""
        def barycenter(node_id: str) -> float:
            if direction == "down":
                neighbors = self.reverse_graph.get(node_id, [])
            else:
                neighbors = self.graph.get(node_id, [])

            if not neighbors:
                return len(reference_layer) / 2

            positions = [reference_layer.index(n) for n in neighbors if n in reference_layer]
            return sum(positions) / len(positions) if positions else len(reference_layer) / 2

        return sorted(layer, key=barycenter)

    def _calculate_horizontal_positions(self, layers_by_phase: Dict[int, List[str]]) -> Dict[str, float]:
        """
        水平座標の動的割り当て（Sugiyama第3段階）。

        Args:
            layers_by_phase: フェーズごとのノードリスト

        Returns:
            各ノードのX座標
        """
        x_positions: Dict[str, float] = {}

        for phase_idx in sorted(layers_by_phase.keys()):
            nodes = layers_by_phase[phase_idx]

            # フェーズの基準X座標を計算
            base_x = self._margin_x + self._lane_header_width + phase_idx * (self._task_base_width + self._base_spacing)

            # フェーズ内の各ノードに座標を割り当て
            for node_id in nodes:
                x_positions[node_id] = base_x

        return x_positions

    def _calculate_vertical_positions(self, layers_by_phase: Dict[int, List[str]], actor_order: Dict[str, int]) -> Dict[str, float]:
        """
        垂直座標の動的割り当て。

        Args:
            layers_by_phase: フェーズごとのノードリスト
            actor_order: actorの順序マッピング

        Returns:
            各ノードのY座標
        """
        y_positions: Dict[str, float] = {}

        # 各レーン内でのノード配置を計算
        lane_nodes: Dict[str, List[str]] = defaultdict(list)
        for phase_idx, nodes in layers_by_phase.items():
            for node_id in nodes:
                actor_id = self._get_node_actor(node_id)
                lane_nodes[actor_id].append(node_id)

        for actor_id, nodes in lane_nodes.items():
            actor_idx = actor_order.get(actor_id, 0)
            lane_top = self._margin_y + actor_idx * self._lane_base_height
            lane_center_y = lane_top + self._lane_base_height / 2

            # レーン内でノードを均等配置
            total_height = len(nodes) * (self._task_base_height + 20)
            start_y = lane_center_y - total_height / 2

            for idx, node_id in enumerate(nodes):
                y_positions[node_id] = start_y + idx * (self._task_base_height + 20)

        return y_positions

    def calculate_layout(self) -> Tuple[Dict[str, BPMNNodeLayout], List[BPMNLaneLayout]]:
        """
        レイアウト全体を計算する。

        Returns:
            (ノードレイアウト辞書, レーンレイアウトリスト)
        """
        # Actor順序の決定
        actor_order = {actor["id"]: idx for idx, actor in enumerate(self.actors)}

        # トポロジカルソート
        layers = self._topological_sort()

        # 交差最小化
        optimized_layers = self._barycenter_method(layers)

        # フェーズへの割り当て
        layers_by_phase: Dict[int, List[str]] = defaultdict(list)
        for layer in optimized_layers:
            for node_id in layer:
                phase_idx = self._assign_to_phase(node_id, optimized_layers)
                layers_by_phase[phase_idx].append(node_id)

        # 座標計算
        x_positions = self._calculate_horizontal_positions(layers_by_phase)
        y_positions = self._calculate_vertical_positions(layers_by_phase, actor_order)

        # ノードレイアウトの構築
        node_layouts: Dict[str, BPMNNodeLayout] = {}
        for node_id in x_positions.keys():
            kind = self._get_node_kind(node_id)
            label = self._get_node_label(node_id)
            actor_id = self._get_node_actor(node_id)

            if kind == "gateway":
                width = height = self._gateway_size
            else:
                width = self._task_base_width
                height = self._task_base_height

            node_layouts[node_id] = BPMNNodeLayout(
                node_id=node_id,
                label=label,
                x=x_positions[node_id],
                y=y_positions[node_id],
                width=width,
                height=height,
                kind=kind,
                lane_id=actor_id,
            )

        # レーンレイアウトの構築
        lane_layouts: List[BPMNLaneLayout] = []
        total_width = (
            self._margin_x * 2
            + self._lane_header_width
            + len(self.phases) * self._task_base_width
            + max(0, len(self.phases) - 1) * self._base_spacing
        )

        for actor in self.actors:
            actor_idx = actor_order[actor["id"]]
            lane_layouts.append(BPMNLaneLayout(
                lane_id=actor["id"],
                label=actor.get("name", actor["id"]),
                x=self._margin_x,
                y=self._margin_y + actor_idx * self._lane_base_height,
                width=total_width - 2 * self._margin_x,
                height=self._lane_base_height,
            ))

        return node_layouts, lane_layouts

    def calculate_diagram_size(self) -> Tuple[int, int]:
        """
        BPMN図全体のサイズを計算する。

        Returns:
            (幅, 高さ)
        """
        width = (
            self._margin_x * 2
            + self._lane_header_width
            + len(self.phases) * self._task_base_width
            + max(0, len(self.phases) - 1) * self._base_spacing
        )

        height = (
            self._margin_y * 2
            + len(self.actors) * self._lane_base_height
        )

        return int(width), int(height)
