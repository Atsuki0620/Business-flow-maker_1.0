"""
BPMN 2.0準拠のレイアウト計算モジュール（v0.42 全面改訂版）。

レイアウトエンジンの設計方針：
- 固定座標を一切使用せず、JSON構造から動的に計算
- 構造レベル（レーン/ランク割り当て）と幾何レベル（座標計算）を分離
- 直交（マンハッタン）ルーティングでエッジを描画
- phases がある場合は phases の順序、ない場合はトポロジカルソートで列を決定
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================================
# レイアウト中間モデル
# ============================================================================


@dataclass
class LayoutNode:
    """レイアウト計算用のノード中間モデル。"""

    node_id: str
    kind: str  # "task" | "gateway" | "start" | "end"
    label: str
    actor_id: str  # 所属するactor（レーン）
    phase_id: Optional[str] = None  # 所属するphase（なくてもよい）

    # 構造レベルの情報
    lane_index: int = 0  # レーン番号（0,1,2,...）
    rank_index: int = 0  # ランク（列）番号（0,1,2,...）
    order_in_rank: int = 0  # 同ランク内での順序（0,1,2,...）

    # 幾何レベルの情報
    width: float = 0.0
    height: float = 0.0
    x: float = 0.0
    y: float = 0.0


@dataclass
class LayoutEdge:
    """レイアウト計算用のエッジ中間モデル。"""

    edge_id: str
    from_node: str
    to_node: str
    condition: Optional[str] = None
    waypoints: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class LayoutLane:
    """レイアウト計算用のレーン（スイムレーン）情報。"""

    lane_index: int
    actor_id: str
    label: str
    y: float = 0.0
    height: float = 0.0


@dataclass
class LayoutRank:
    """レイアウト計算用のランク（列）情報。"""

    rank_index: int
    phase_id: Optional[str] = None
    label: Optional[str] = None
    x: float = 0.0
    width: float = 0.0


@dataclass
class BPMNNodeLayout:
    """BPMN変換用のノードレイアウト情報（後方互換性のため保持）。"""

    node_id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    kind: str
    lane_id: str


@dataclass
class BPMNLaneLayout:
    """BPMN変換用のレーンレイアウト情報（後方互換性のため保持）。"""

    lane_id: str
    label: str
    x: float
    y: float
    width: float
    height: float


# ============================================================================
# レイアウトエンジン
# ============================================================================


class BPMNLayoutEngine:
    """
    BPMN 2.0準拠のレイアウトエンジン（v0.42全面改訂版）。

    設計方針：
    1. 構造レベルのレイアウト：レーン割り当て、ランク割り当て、ノード順序決定
    2. 幾何レベルのレイアウト：ノードサイズ推定、レーン/ランク幅高さ計算、座標割り当て
    3. エッジルーティング：直交（マンハッタン）ルーティングで中継点を計算
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

        # レイアウト用の中間データ
        self.nodes: Dict[str, LayoutNode] = {}
        self.edges: List[LayoutEdge] = []
        self.lanes: List[LayoutLane] = []
        self.ranks: List[LayoutRank] = []

        # パラメータ（フロー規模に応じて調整）
        total_nodes = len(self.tasks) + len(self.gateways)
        self.params = {
            "margin_x": 50,
            "margin_y": 50,
            "lane_header_width": 180,
            "task_base_width": 180,
            "task_base_height": 80,
            "gateway_size": 60,
            "rank_spacing": 100,  # ランク間のスペース
            "node_spacing_y": 20,  # 同レーン内のノード間スペース
            "lane_min_height": 150,
            "lane_padding_y": 30,
        }

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

    # ========================================================================
    # 構造レベル：ノード中間モデルの構築
    # ========================================================================

    def _build_nodes(self) -> None:
        """ノード中間モデルを構築する。"""
        # タスクノードの作成
        for task in self.tasks:
            node = LayoutNode(
                node_id=task["id"],
                kind="task",
                label=task.get("name", task["id"]),
                actor_id=task.get("actor_id", ""),
                phase_id=task.get("phase_id", None),
            )
            self.nodes[task["id"]] = node

        # ゲートウェイノードの作成
        for gateway in self.gateways:
            # ゲートウェイの actor_id は隣接ノードから推測
            actor_id = self._infer_gateway_actor(gateway["id"])
            # ゲートウェイの phase_id も隣接ノードから推測
            phase_id = self._infer_gateway_phase(gateway["id"])

            node = LayoutNode(
                node_id=gateway["id"],
                kind="gateway",
                label=gateway.get("name", ""),
                actor_id=actor_id,
                phase_id=phase_id,
            )
            self.nodes[gateway["id"]] = node

    def _infer_gateway_actor(self, gateway_id: str) -> str:
        """ゲートウェイの所属 actor を隣接ノードから推測する。"""
        # 入力元のノードの actor を優先
        predecessors = self.reverse_graph.get(gateway_id, [])
        for pred_id in predecessors:
            for task in self.tasks:
                if task["id"] == pred_id:
                    return task.get("actor_id", "")

        # 出力先のノードの actor を次善
        successors = self.graph.get(gateway_id, [])
        for succ_id in successors:
            for task in self.tasks:
                if task["id"] == succ_id:
                    return task.get("actor_id", "")

        # デフォルト：最初の actor
        return self.actors[0]["id"] if self.actors else ""

    def _infer_gateway_phase(self, gateway_id: str) -> Optional[str]:
        """ゲートウェイの所属 phase を隣接ノードから推測する。"""
        # 入力元のノードの phase を優先
        predecessors = self.reverse_graph.get(gateway_id, [])
        for pred_id in predecessors:
            for task in self.tasks:
                if task["id"] == pred_id:
                    return task.get("phase_id", None)

        # 出力先のノードの phase を次善
        successors = self.graph.get(gateway_id, [])
        for succ_id in successors:
            for task in self.tasks:
                if task["id"] == succ_id:
                    return task.get("phase_id", None)

        return None

    # ========================================================================
    # 構造レベル：レーン割り当て
    # ========================================================================

    def _assign_lanes(self) -> None:
        """各ノードにレーン番号を割り当てる。"""
        # actors の順序から lane_index を決定
        actor_to_lane: Dict[str, int] = {}
        for idx, actor in enumerate(self.actors):
            actor_to_lane[actor["id"]] = idx

        # 各ノードに lane_index を設定
        for node in self.nodes.values():
            node.lane_index = actor_to_lane.get(node.actor_id, 0)

        # LayoutLane リストを作成
        self.lanes = []
        for idx, actor in enumerate(self.actors):
            self.lanes.append(
                LayoutLane(
                    lane_index=idx,
                    actor_id=actor["id"],
                    label=actor.get("name", actor["id"]),
                )
            )

    # ========================================================================
    # 構造レベル：ランク割り当て
    # ========================================================================

    def _assign_ranks(self) -> None:
        """各ノードにランク（列）番号を割り当てる。"""
        # phases に関わらず、常にトポロジカルソートでランクを決定
        # （phase は後でグループ化に使用可能だが、レイアウトは時系列を優先）
        self._assign_ranks_by_topological_sort()

    def _assign_ranks_by_phases(self) -> None:
        """phases の順序でランクを割り当てる。"""
        phase_to_rank: Dict[str, int] = {}
        for idx, phase in enumerate(self.phases):
            phase_to_rank[phase["id"]] = idx

        # 各ノードに rank_index を設定
        for node in self.nodes.values():
            if node.phase_id and node.phase_id in phase_to_rank:
                node.rank_index = phase_to_rank[node.phase_id]
            else:
                # phase_id がない、または存在しない phase の場合は最初のランク
                node.rank_index = 0

        # LayoutRank リストを作成
        self.ranks = []
        for idx, phase in enumerate(self.phases):
            self.ranks.append(
                LayoutRank(
                    rank_index=idx,
                    phase_id=phase["id"],
                    label=phase.get("name", phase["id"]),
                )
            )

    def _assign_ranks_by_topological_sort(self) -> None:
        """トポロジカルソートでランクを割り当てる。"""
        # BFS でレベルを決定
        all_node_ids = set(self.nodes.keys())
        in_degree = {nid: len(self.reverse_graph.get(nid, [])) for nid in all_node_ids}

        rank_assignment: Dict[str, int] = {}
        queue: deque = deque()

        # 入次数0のノードから開始
        for nid in all_node_ids:
            if in_degree[nid] == 0:
                queue.append(nid)
                rank_assignment[nid] = 0

        while queue:
            current = queue.popleft()
            current_rank = rank_assignment[current]

            for successor in self.graph.get(current, []):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    # 後続ノードのランクは現在のランク + 1
                    rank_assignment[successor] = current_rank + 1
                    queue.append(successor)

        # 循環がある場合の処理（残りのノードを最後のランクに配置）
        max_rank = max(rank_assignment.values()) if rank_assignment else 0
        for nid in all_node_ids:
            if nid not in rank_assignment:
                rank_assignment[nid] = max_rank + 1

        # 各ノードに rank_index を設定
        for nid, rank in rank_assignment.items():
            self.nodes[nid].rank_index = rank

        # LayoutRank リストを作成（ランク数だけ）
        max_rank = max(node.rank_index for node in self.nodes.values()) if self.nodes else 0
        self.ranks = []
        for idx in range(max_rank + 1):
            self.ranks.append(
                LayoutRank(
                    rank_index=idx,
                    phase_id=None,
                    label=f"列{idx+1}",
                )
            )

    # ========================================================================
    # 構造レベル：同ランク内のノード順序決定
    # ========================================================================

    def _order_nodes_in_rank(self) -> None:
        """同じランク内でのノード順序を決定する。"""
        # ランクごとにノードをグループ化
        nodes_by_rank: Dict[int, List[LayoutNode]] = defaultdict(list)
        for node in self.nodes.values():
            nodes_by_rank[node.rank_index].append(node)

        # 各ランク内でノードをソート（lane_index 順、次にトポロジカル順）
        for rank_idx, nodes_in_rank in nodes_by_rank.items():
            # lane_index でソート
            sorted_nodes = sorted(nodes_in_rank, key=lambda n: (n.lane_index, n.node_id))

            # order_in_rank を設定
            for order, node in enumerate(sorted_nodes):
                node.order_in_rank = order

    # ========================================================================
    # 幾何レベル：ノードサイズ推定
    # ========================================================================

    def _calculate_node_sizes(self) -> None:
        """各ノードのサイズ（幅・高さ）を計算する。"""
        for node in self.nodes.values():
            if node.kind == "gateway":
                node.width = self.params["gateway_size"]
                node.height = self.params["gateway_size"]
            else:  # task
                # ラベル長から幅を推定（日本語は全角換算で1文字≒10px程度）
                label_len = len(node.label)
                estimated_width = max(
                    self.params["task_base_width"],
                    min(300, 80 + label_len * 10),
                )
                node.width = estimated_width
                node.height = self.params["task_base_height"]

    # ========================================================================
    # 幾何レベル：ランク幅の計算
    # ========================================================================

    def _calculate_rank_widths(self) -> None:
        """各ランクの幅を、そのランクに含まれるノードの最大幅から計算する。"""
        # ランクごとの最大ノード幅を集計
        rank_max_width: Dict[int, float] = {}
        for node in self.nodes.values():
            rank_idx = node.rank_index
            if rank_idx not in rank_max_width:
                rank_max_width[rank_idx] = 0
            rank_max_width[rank_idx] = max(rank_max_width[rank_idx], node.width)

        # 各ランクに幅を設定
        for rank in self.ranks:
            rank.width = rank_max_width.get(rank.rank_index, self.params["task_base_width"])

    # ========================================================================
    # 幾何レベル：レーン高さの計算
    # ========================================================================

    def _calculate_lane_heights(self) -> None:
        """各レーンの高さを、そのレーンに含まれるノード数と高さから計算する。"""
        # レーンごとのノード数と最大ノード高さを集計
        lane_node_counts: Dict[int, int] = defaultdict(int)
        lane_max_height: Dict[int, float] = defaultdict(float)

        for node in self.nodes.values():
            lane_idx = node.lane_index
            lane_node_counts[lane_idx] += 1
            lane_max_height[lane_idx] = max(lane_max_height[lane_idx], node.height)

        # 各レーンに高さを設定
        for lane in self.lanes:
            node_count = lane_node_counts.get(lane.lane_index, 0)
            max_node_height = lane_max_height.get(lane.lane_index, self.params["task_base_height"])

            if node_count == 0:
                lane.height = self.params["lane_min_height"]
            else:
                # レーン高さ = ノード高さの最大値 × ノード数 + 間隔 + パディング
                total_content_height = (
                    max_node_height * node_count
                    + self.params["node_spacing_y"] * max(0, node_count - 1)
                )
                lane.height = max(
                    self.params["lane_min_height"],
                    total_content_height + self.params["lane_padding_y"] * 2,
                )

    # ========================================================================
    # 幾何レベル：座標の計算
    # ========================================================================

    def _calculate_coordinates(self) -> None:
        """各ノードとレーン・ランクの座標を計算する。"""
        # ランクのX座標を累積的に計算
        current_x = self.params["margin_x"] + self.params["lane_header_width"]
        for rank in sorted(self.ranks, key=lambda r: r.rank_index):
            rank.x = current_x
            current_x += rank.width + self.params["rank_spacing"]

        # レーンのY座標を累積的に計算
        current_y = self.params["margin_y"]
        for lane in sorted(self.lanes, key=lambda l: l.lane_index):
            lane.y = current_y
            current_y += lane.height

        # ノードの座標を計算
        for node in self.nodes.values():
            # X座標：ランクの中央に配置
            rank = next((r for r in self.ranks if r.rank_index == node.rank_index), None)
            if rank:
                node.x = rank.x + (rank.width - node.width) / 2
            else:
                node.x = self.params["margin_x"]

            # Y座標：レーン内で縦方向に配置
            lane = next((l for l in self.lanes if l.lane_index == node.lane_index), None)
            if lane:
                # レーン内の同ランクのノード一覧を取得
                nodes_in_same_rank_lane = [
                    n for n in self.nodes.values()
                    if n.rank_index == node.rank_index and n.lane_index == node.lane_index
                ]
                nodes_in_same_rank_lane.sort(key=lambda n: n.order_in_rank)

                # レーン内での垂直位置を計算
                total_nodes = len(nodes_in_same_rank_lane)
                node_index = nodes_in_same_rank_lane.index(node)

                # レーン中央から上下に配置
                total_height = (
                    sum(n.height for n in nodes_in_same_rank_lane)
                    + self.params["node_spacing_y"] * max(0, total_nodes - 1)
                )
                start_y = lane.y + (lane.height - total_height) / 2

                offset_y = 0
                for i, n in enumerate(nodes_in_same_rank_lane):
                    if i == node_index:
                        node.y = start_y + offset_y
                        break
                    offset_y += n.height + self.params["node_spacing_y"]
            else:
                node.y = self.params["margin_y"]

    # ========================================================================
    # エッジルーティング：直交（マンハッタン）ルーティング
    # ========================================================================

    def _route_edges(self) -> None:
        """エッジの経路（waypoints）を計算する。"""
        self.edges = []

        for flow_data in self.flows_data:
            from_id = flow_data.get("from", "")
            to_id = flow_data.get("to", "")

            if from_id not in self.nodes or to_id not in self.nodes:
                # ノードが見つからない場合はスキップ（警告を出す方が良いが、ここでは無視）
                continue

            from_node = self.nodes[from_id]
            to_node = self.nodes[to_id]

            # エッジの開始点・終了点
            # 開始点：ノードの右端中央
            start_x = from_node.x + from_node.width
            start_y = from_node.y + from_node.height / 2

            # 終了点：ノードの左端中央
            end_x = to_node.x
            end_y = to_node.y + to_node.height / 2

            # waypoints を計算（直交ルーティング）
            waypoints = self._calculate_orthogonal_waypoints(
                start_x, start_y, end_x, end_y, from_node, to_node
            )

            edge = LayoutEdge(
                edge_id=flow_data.get("id", f"flow_{from_id}_{to_id}"),
                from_node=from_id,
                to_node=to_id,
                condition=flow_data.get("condition", None),
                waypoints=waypoints,
            )
            self.edges.append(edge)

        # デバッグ用：作成されたエッジ数を確認
        # print(f"DEBUG: Created {len(self.edges)} edges from {len(self.flows_data)} flows")

    def _calculate_orthogonal_waypoints(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        from_node: LayoutNode,
        to_node: LayoutNode,
    ) -> List[Tuple[float, float]]:
        """
        直交（マンハッタン）ルーティングで waypoints を計算する。

        基本方針：
        - 同レーン・隣接ランク: ほぼ水平の直線
        - レーン跨ぎ: 水平→垂直→水平の折れ線
        """
        waypoints = [(start_x, start_y)]

        # 同じレーンかつ隣接ランクの場合
        if (
            from_node.lane_index == to_node.lane_index
            and abs(from_node.rank_index - to_node.rank_index) <= 1
        ):
            # 単純な水平線
            waypoints.append((end_x, end_y))
        else:
            # レーン跨ぎまたはランクが離れている場合
            # 中継点を挿入して直交ルーティング

            # 中継点1: 開始点から水平に進む
            mid_x = (start_x + end_x) / 2
            waypoints.append((mid_x, start_y))

            # 中継点2: 垂直に移動
            waypoints.append((mid_x, end_y))

            # 終了点
            waypoints.append((end_x, end_y))

        return waypoints

    # ========================================================================
    # メイン処理：レイアウト計算の実行
    # ========================================================================

    def calculate_layout(self) -> Tuple[Dict[str, BPMNNodeLayout], List[BPMNLaneLayout]]:
        """
        レイアウト全体を計算する。

        Returns:
            (ノードレイアウト辞書, レーンレイアウトリスト)
        """
        # ステップ1: 構造レベルのレイアウト
        self._build_nodes()
        self._assign_lanes()
        self._assign_ranks()
        self._order_nodes_in_rank()

        # ステップ2: 幾何レベルのレイアウト
        self._calculate_node_sizes()
        self._calculate_rank_widths()
        self._calculate_lane_heights()
        self._calculate_coordinates()

        # ステップ3: エッジルーティング
        self._route_edges()

        # 後方互換性のため、BPMNNodeLayout / BPMNLaneLayout 形式に変換
        node_layouts: Dict[str, BPMNNodeLayout] = {}
        for node in self.nodes.values():
            node_layouts[node.node_id] = BPMNNodeLayout(
                node_id=node.node_id,
                label=node.label,
                x=node.x,
                y=node.y,
                width=node.width,
                height=node.height,
                kind=node.kind,
                lane_id=node.actor_id,
            )

        lane_layouts: List[BPMNLaneLayout] = []
        total_width = self.calculate_diagram_size()[0]
        for lane in self.lanes:
            lane_layouts.append(
                BPMNLaneLayout(
                    lane_id=lane.actor_id,
                    label=lane.label,
                    x=self.params["margin_x"],
                    y=lane.y,
                    width=total_width - 2 * self.params["margin_x"],
                    height=lane.height,
                )
            )

        return node_layouts, lane_layouts

    def calculate_diagram_size(self) -> Tuple[int, int]:
        """
        BPMN図全体のサイズを計算する。

        Returns:
            (幅, 高さ)
        """
        if not self.ranks or not self.lanes:
            return 800, 600

        # 幅：margin + lane_header + 全ランク幅 + ランク間スペース + margin
        total_rank_width = sum(rank.width for rank in self.ranks)
        total_spacing = self.params["rank_spacing"] * max(0, len(self.ranks) - 1)
        width = (
            self.params["margin_x"] * 2
            + self.params["lane_header_width"]
            + total_rank_width
            + total_spacing
        )

        # 高さ：margin + 全レーン高さ + margin
        total_lane_height = sum(lane.height for lane in self.lanes)
        height = self.params["margin_y"] * 2 + total_lane_height

        return int(width), int(height)

    def get_edge_waypoints(self, edge_id: str) -> List[Tuple[float, float]]:
        """
        指定されたエッジの waypoints を取得する。

        Args:
            edge_id: エッジID（flow_id）

        Returns:
            waypoints のリスト
        """
        for edge in self.edges:
            if edge.edge_id == edge_id:
                return edge.waypoints
        return []

    def get_edge_waypoints_by_nodes(self, from_node: str, to_node: str) -> List[Tuple[float, float]]:
        """
        fromとtoノードを指定してwaypointsを取得する。

        Args:
            from_node: 開始ノードID
            to_node: 終了ノードID

        Returns:
            waypoints のリスト
        """
        for edge in self.edges:
            if edge.from_node == from_node and edge.to_node == to_node:
                return edge.waypoints
        return []
