"""
BPMN 2.0準拠性検証モジュール。

生成されたBPMN XMLがBPMN 2.0仕様に準拠しているかを検証します。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple


class BPMNValidator:
    """BPMN 2.0 XML文書の妥当性検証クラス。"""

    # BPMN 2.0名前空間
    NAMESPACES = {
        'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc': 'http://www.omg.org/spec/DD/20100524/DC',
        'di': 'http://www.omg.org/spec/DD/20100524/DI',
    }

    def __init__(self, xml_content: str):
        """
        Args:
            xml_content: 検証対象のBPMN XML文字列
        """
        self.xml_content = xml_content
        self.errors: List[str] = []
        self.warnings: List[str] = []

        try:
            self.root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            self.errors.append(f"XML解析エラー: {e}")
            self.root = None

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        BPMN 2.0準拠性の検証を実行する。

        Returns:
            (検証成功フラグ, エラーリスト, 警告リスト)
        """
        if self.root is None:
            return False, self.errors, self.warnings

        self._validate_namespaces()
        self._validate_structure()
        self._validate_ids()
        self._validate_references()
        self._validate_diagram()

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_namespaces(self) -> None:
        """名前空間の検証。"""
        required_namespaces = ['bpmn2', 'bpmndi', 'dc', 'di']

        # ElementTreeでは名前空間はxmlns:prefix形式で属性に格納される
        for prefix in required_namespaces:
            expected_uri = self.NAMESPACES[prefix]

            # 2つの方法で名前空間を探す
            actual_uri = self.root.attrib.get(f'{{http://www.w3.org/2000/xmlns/}}{prefix}')
            if actual_uri is None:
                actual_uri = self.root.attrib.get(f'xmlns:{prefix}')

            # ルート要素自体の名前空間もチェック
            if actual_uri is None and prefix == 'bpmn2':
                # ルート要素がbpmn2名前空間にあるか確認
                if self.root.tag.startswith(f'{{{expected_uri}}}'):
                    continue  # OK

            if actual_uri != expected_uri and actual_uri is not None:
                self.errors.append(
                    f"名前空間エラー: xmlns:{prefix} が正しく定義されていません "
                    f"(期待値: {expected_uri}, 実際: {actual_uri})"
                )
            elif actual_uri is None and prefix != 'bpmn2':
                # bpmn2以外は警告のみ
                self.warnings.append(
                    f"名前空間警告: xmlns:{prefix} が見つかりません（期待値: {expected_uri}）"
                )

    def _validate_structure(self) -> None:
        """基本構造の検証。"""
        # definitions要素の確認
        if self.root.tag != f"{{{self.NAMESPACES['bpmn2']}}}definitions":
            self.errors.append("ルート要素はbpmn2:definitions である必要があります")

        # process要素の確認
        processes = self.root.findall('.//bpmn2:process', self.NAMESPACES)
        if not processes:
            self.errors.append("少なくとも1つのbpmn2:process要素が必要です")

        # collaboration要素の確認（スイムレーンを使用する場合）
        collaborations = self.root.findall('.//bpmn2:collaboration', self.NAMESPACES)
        participants = self.root.findall('.//bpmn2:participant', self.NAMESPACES)

        if participants and not collaborations:
            self.errors.append("participantを使用する場合はcollaboration要素が必要です")

    def _validate_ids(self) -> None:
        """ID一意性の検証。"""
        ids_seen = set()

        for elem in self.root.iter():
            elem_id = elem.attrib.get('id')
            if elem_id:
                if elem_id in ids_seen:
                    self.errors.append(f"ID重複エラー: '{elem_id}' が複数回使用されています")
                ids_seen.add(elem_id)

    def _validate_references(self) -> None:
        """参照の整合性検証。"""
        # すべてのIDを収集
        all_ids = {elem.attrib.get('id') for elem in self.root.iter() if 'id' in elem.attrib}

        # sequenceFlowの参照検証
        for flow in self.root.findall('.//bpmn2:sequenceFlow', self.NAMESPACES):
            flow_id = flow.attrib.get('id', 'unknown')
            source_ref = flow.attrib.get('sourceRef')
            target_ref = flow.attrib.get('targetRef')

            if not source_ref:
                self.errors.append(f"sequenceFlow '{flow_id}' にsourceRef属性がありません")
            elif source_ref not in all_ids:
                self.errors.append(f"sequenceFlow '{flow_id}' のsourceRef '{source_ref}' が存在しません")

            if not target_ref:
                self.errors.append(f"sequenceFlow '{flow_id}' にtargetRef属性がありません")
            elif target_ref not in all_ids:
                self.errors.append(f"sequenceFlow '{flow_id}' のtargetRef '{target_ref}' が存在しません")

        # BPMNShapeの参照検証
        for shape in self.root.findall('.//bpmndi:BPMNShape', self.NAMESPACES):
            bpmn_element = shape.attrib.get('bpmnElement')
            if bpmn_element and bpmn_element not in all_ids:
                self.warnings.append(f"BPMNShape のbpmnElement '{bpmn_element}' が存在しません")

        # BPMNEdgeの参照検証
        for edge in self.root.findall('.//bpmndi:BPMNEdge', self.NAMESPACES):
            bpmn_element = edge.attrib.get('bpmnElement')
            if bpmn_element and bpmn_element not in all_ids:
                self.warnings.append(f"BPMNEdge のbpmnElement '{bpmn_element}' が存在しません")

    def _validate_diagram(self) -> None:
        """図形情報の検証。"""
        # BPMNDiagram要素の確認
        diagrams = self.root.findall('.//bpmndi:BPMNDiagram', self.NAMESPACES)
        if not diagrams:
            self.warnings.append("BPMNDiagram要素がありません（可視化情報なし）")
            return

        # BPMNPlane要素の確認
        planes = self.root.findall('.//bpmndi:BPMNPlane', self.NAMESPACES)
        if not planes:
            self.errors.append("BPMNPlane要素が必要です")

        # BPMNShape要素の座標検証
        for shape in self.root.findall('.//bpmndi:BPMNShape', self.NAMESPACES):
            bounds = shape.find('dc:Bounds', self.NAMESPACES)
            if bounds is None:
                shape_id = shape.attrib.get('id', 'unknown')
                self.errors.append(f"BPMNShape '{shape_id}' にdc:Bounds要素がありません")
            else:
                # 必須属性の確認
                for attr in ['x', 'y', 'width', 'height']:
                    if attr not in bounds.attrib:
                        self.errors.append(f"dc:Bounds に{attr}属性がありません")

        # BPMNEdge要素の座標検証
        for edge in self.root.findall('.//bpmndi:BPMNEdge', self.NAMESPACES):
            waypoints = edge.findall('di:waypoint', self.NAMESPACES)
            if len(waypoints) < 2:
                edge_id = edge.attrib.get('id', 'unknown')
                self.errors.append(f"BPMNEdge '{edge_id}' には少なくとも2つのwaypointが必要です")

    def get_statistics(self) -> Dict[str, int]:
        """
        BPMN文書の統計情報を取得する。

        Returns:
            統計情報の辞書
        """
        if self.root is None:
            return {}

        return {
            'tasks': len(self.root.findall('.//bpmn2:userTask', self.NAMESPACES)) +
                     len(self.root.findall('.//bpmn2:serviceTask', self.NAMESPACES)),
            'gateways': len(self.root.findall('.//bpmn2:exclusiveGateway', self.NAMESPACES)) +
                        len(self.root.findall('.//bpmn2:parallelGateway', self.NAMESPACES)) +
                        len(self.root.findall('.//bpmn2:inclusiveGateway', self.NAMESPACES)),
            'sequence_flows': len(self.root.findall('.//bpmn2:sequenceFlow', self.NAMESPACES)),
            'lanes': len(self.root.findall('.//bpmn2:lane', self.NAMESPACES)),
            'participants': len(self.root.findall('.//bpmn2:participant', self.NAMESPACES)),
        }


def validate_bpmn(xml_content: str) -> Tuple[bool, List[str], List[str], Dict[str, int]]:
    """
    BPMN XMLの妥当性検証を実行する便利関数。

    Args:
        xml_content: 検証対象のBPMN XML文字列

    Returns:
        (検証成功フラグ, エラーリスト, 警告リスト, 統計情報)
    """
    validator = BPMNValidator(xml_content)
    is_valid, errors, warnings = validator.validate()
    stats = validator.get_statistics()

    return is_valid, errors, warnings, stats
