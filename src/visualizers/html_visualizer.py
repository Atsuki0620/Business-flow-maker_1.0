"""
Layer1 flow visualization and review exporter.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)


LANE_HEIGHT = 140
LANE_HEADER_WIDTH = 150
TASK_WIDTH = 180
TASK_HEIGHT = 48
COLUMN_GAP = 60
MARGIN_X = 40
MARGIN_Y = 40

UTF8_WITH_BOM = "utf-8-sig"
SVG_XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


@dataclass
class NodeLayout:
    node_id: str
    label: str
    x: float
    y: float
    kind: str  # task | gateway
    actor_idx: int
    phase_idx: int


def load_flow(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def determine_orders(flow: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[str, int]]:
    phase_order = {item["id"]: idx for idx, item in enumerate(flow.get("phases", []))}
    actor_order = {item["id"]: idx for idx, item in enumerate(flow.get("actors", []))}
    return actor_order, phase_order


def infer_phase_idx(node_id: str, flow: Dict[str, Any], phase_order: Dict[str, int]) -> int:
    for task in flow.get("tasks", []):
        if task["id"] == node_id:
            return phase_order.get(task.get("phase_id", ""), 0)
    for link in flow.get("flows", []):
        if link["from"] == node_id:
            return infer_phase_idx(link["to"], flow, phase_order)
        if link["to"] == node_id:
            return infer_phase_idx(link["from"], flow, phase_order)
    return 0


def infer_actor_idx(node_id: str, flow: Dict[str, Any], actor_order: Dict[str, int]) -> int:
    for task in flow.get("tasks", []):
        if task["id"] == node_id:
            return actor_order.get(task.get("actor_id", ""), 0)
    neighbour_ids: List[str] = []
    for link in flow.get("flows", []):
        if link["from"] == node_id:
            neighbour_ids.append(link["to"])
        elif link["to"] == node_id:
            neighbour_ids.append(link["from"])
    for neighbour in neighbour_ids:
        idx = infer_actor_idx(neighbour, flow, actor_order)
        if idx is not None:
            return idx
    return 0


def build_layout(flow: Dict[str, Any]) -> Dict[str, NodeLayout]:
    actor_order, phase_order = determine_orders(flow)
    positions: Dict[str, NodeLayout] = {}

    for task in flow.get("tasks", []):
        actor_idx = actor_order.get(task.get("actor_id", ""), 0)
        phase_idx = phase_order.get(task.get("phase_id", ""), 0)
        lane_top = MARGIN_Y + actor_idx * LANE_HEIGHT
        x = MARGIN_X + LANE_HEADER_WIDTH + phase_idx * (TASK_WIDTH + COLUMN_GAP)
        y = lane_top + (LANE_HEIGHT - TASK_HEIGHT) / 2
        positions[task["id"]] = NodeLayout(
            node_id=task["id"],
            label=task["name"],
            x=x,
            y=y,
            kind="task",
            actor_idx=actor_idx,
            phase_idx=phase_idx,
        )

    for gateway in flow.get("gateways", []):
        node_id = gateway["id"]
        actor_idx = infer_actor_idx(node_id, flow, actor_order)
        phase_idx = infer_phase_idx(node_id, flow, phase_order)
        lane_top = MARGIN_Y + actor_idx * LANE_HEIGHT
        x = MARGIN_X + LANE_HEADER_WIDTH + phase_idx * (TASK_WIDTH + COLUMN_GAP) + TASK_WIDTH / 2
        y = lane_top + LANE_HEIGHT / 2
        positions[node_id] = NodeLayout(
            node_id=node_id,
            label=gateway.get("name", ""),
            x=x,
            y=y,
            kind="gateway",
            actor_idx=actor_idx,
            phase_idx=phase_idx,
        )
    return positions


def svg_size(flow: Dict[str, Any]) -> Tuple[int, int]:
    width = (
        MARGIN_X * 2
        + LANE_HEADER_WIDTH
        + max(1, len(flow.get("phases", []))) * TASK_WIDTH
        + max(0, len(flow.get("phases", [])) - 1) * COLUMN_GAP
    )
    height = MARGIN_Y * 2 + max(1, len(flow.get("actors", []))) * LANE_HEIGHT
    return int(width), int(height)


def build_svg(flow: Dict[str, Any]) -> str:
    actor_order, phase_order = determine_orders(flow)
    layout = build_layout(flow)
    width, height = svg_size(flow)

    svg = Element(
        "svg",
        attrib={
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {width} {height}",
            "width": str(width),
            "height": str(height),
        },
    )

    defs = SubElement(svg, "defs")
    marker = SubElement(
        defs,
        "marker",
        attrib={"id": "arrow", "markerWidth": "10", "markerHeight": "10", "refX": "10", "refY": "3", "orient": "auto"},
    )
    SubElement(marker, "path", attrib={"d": "M0,0 L10,3 L0,6 Z", "fill": "#555"})

    # Swimlanes
    for actor in flow.get("actors", []):
        idx = actor_order.get(actor["id"], 0)
        y = MARGIN_Y + idx * LANE_HEIGHT
        SubElement(
            svg,
            "rect",
            attrib={
                "x": str(MARGIN_X),
                "y": str(y),
                "width": str(width - 2 * MARGIN_X),
                "height": str(LANE_HEIGHT),
                "fill": "#f8f8f8" if idx % 2 == 0 else "#f0f0f0",
                "stroke": "#d0d0d0",
            },
        )
        SubElement(
            svg,
            "text",
            attrib={
                "x": str(MARGIN_X + 10),
                "y": str(y + 30),
                "font-size": "16",
                "font-family": "Segoe UI, sans-serif",
            },
        ).text = actor.get("name", actor["id"])

    # Phases header
    for phase in flow.get("phases", []):
        idx = phase_order.get(phase["id"], 0)
        x = MARGIN_X + LANE_HEADER_WIDTH + idx * (TASK_WIDTH + COLUMN_GAP)
        SubElement(
            svg,
            "text",
            attrib={
                "x": str(x + TASK_WIDTH / 2),
                "y": str(MARGIN_Y - 10),
                "font-size": "14",
                "font-family": "Segoe UI, sans-serif",
                "text-anchor": "middle",
            },
        ).text = phase.get("name", phase["id"])

    # Tasks and gateways
    for node in layout.values():
        if node.kind == "task":
            SubElement(
                svg,
                "rect",
                attrib={
                    "x": str(node.x),
                    "y": str(node.y),
                    "width": str(TASK_WIDTH),
                    "height": str(TASK_HEIGHT),
                    "rx": "6",
                    "ry": "6",
                    "fill": "#ffffff",
                    "stroke": "#555555",
                },
            )
            SubElement(
                svg,
                "text",
                attrib={
                    "x": str(node.x + TASK_WIDTH / 2),
                    "y": str(node.y + TASK_HEIGHT / 2 + 5),
                    "font-size": "13",
                    "font-family": "Segoe UI, sans-serif",
                    "text-anchor": "middle",
                },
            ).text = node.label
        else:
            size = TASK_HEIGHT * 0.6
            points = [
                (node.x, node.y - size / 2),
                (node.x + size / 2, node.y),
                (node.x, node.y + size / 2),
                (node.x - size / 2, node.y),
            ]
            SubElement(
                svg,
                "polygon",
                attrib={
                    "points": " ".join(f"{x},{y}" for x, y in points),
                    "fill": "#fff4e6",
                    "stroke": "#d17a22",
                    "stroke-width": "2",
                },
            )
            SubElement(
                svg,
                "text",
                attrib={
                    "x": str(node.x),
                    "y": str(node.y + 5),
                    "font-size": "12",
                    "font-family": "Segoe UI, sans-serif",
                    "text-anchor": "middle",
                },
            ).text = node.label or node.node_id

    # Flows
    for link in flow.get("flows", []):
        start = layout.get(link["from"])
        end = layout.get(link["to"])
        if not start or not end:
            missing_ids = []
            if not start:
                missing_ids.append(f"from={link['from']}")
            if not end:
                missing_ids.append(f"to={link['to']}")
            logger.warning(f"flow {link.get('id', 'unknown')} の参照エラー: {', '.join(missing_ids)} が存在しません。このflowをスキップします。")
            continue
        SubElement(
            svg,
            "line",
            attrib={
                "x1": str(start.x + TASK_WIDTH),
                "y1": str(start.y + TASK_HEIGHT / 2),
                "x2": str(end.x),
                "y2": str(end.y + (0 if end.kind == "gateway" else TASK_HEIGHT / 2)),
                "stroke": "#555",
                "stroke-width": "2",
                "marker-end": "url(#arrow)",
            },
        )
        if link.get("condition"):
            label_x = (start.x + end.x) / 2
            label_y = (start.y + end.y) / 2
            SubElement(
                svg,
                "text",
                attrib={
                    "x": str(label_x),
                    "y": str(label_y - 4),
                    "font-size": "11",
                    "font-family": "Segoe UI, sans-serif",
                    "text-anchor": "middle",
                    "fill": "#444",
                },
            ).text = link["condition"]

    return tostring(svg, encoding="unicode")


def build_html(flow: Dict[str, Any], svg: str) -> str:
    metadata = flow.get("metadata", {})
    issues = flow.get("issues", [])
    actors = flow.get("actors", [])
    phases = flow.get("phases", [])
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <title>{metadata.get("title", "Flow preview")}</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; margin: 24px; background-color: #fafafa; }}
    .panel {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 24px; }}
    h1 {{ font-size: 24px; margin-bottom: 8px; }}
    h2 {{ font-size: 18px; margin-top: 0; }}
    ul {{ margin: 8px 0 0 20px; }}
    svg {{ width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px; background: #fff; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>{metadata.get("title", "Flow preview")}</h1>
    <p>ID: {metadata.get("id", "-")} / Source: {metadata.get("source", "-")} / Last updated: {metadata.get("last_updated", "-")}</p>
  </div>
  <div class="panel">
    <h2>Swimlane view</h2>
    {svg}
  </div>
  <div class="panel">
    <h2>概要</h2>
    <p>Actors: {len(actors)} / Phases: {len(phases)} / Tasks: {len(flow.get("tasks", []))} / Gateways: {len(flow.get("gateways", []))}</p>
    <h3>Issues</h3>
    <ul>
      {''.join(f'<li>{issue.get("note","")}</li>' for issue in issues) or '<li>issues 未登録</li>'}
    </ul>
  </div>
</body>
</html>
"""
    return html




def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=UTF8_WITH_BOM)


def run_export(flow_path: Path, html_path: Path, svg_path: Path) -> None:
    flow = load_flow(flow_path)
    svg_markup = build_svg(flow)
    svg_file_markup = f"{SVG_XML_DECLARATION}{svg_markup}"
    html = build_html(flow, svg_markup)
    save_text(svg_path, svg_file_markup)
    save_text(html_path, html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate HTML/SVG preview from flow JSON.")
    parser.add_argument("--json", type=Path, default=Path("output/flow.json"))
    parser.add_argument("--html", type=Path, default=Path("output/flow.html"))
    parser.add_argument("--svg", type=Path, default=Path("output/flow.svg"))
    return parser.parse_args()


def main() -> None:
    from src.utils import run_manager

    args = parse_args()
    run_export(args.json, args.html, args.svg)
    print("[export] flow.html / flow.svg を生成しました。")

    # runs/構造を検出し、info.mdを更新
    json_path = args.json.resolve()
    if "runs" in json_path.parts:
        # runs/ディレクトリを特定
        run_dir = None
        for i, part in enumerate(json_path.parts):
            if part == "runs" and i + 1 < len(json_path.parts):
                run_dir = Path(*json_path.parts[:i+2])
                break

        if run_dir and run_dir.exists() and (run_dir / "info.md").exists():
            # 出力ファイル情報を追記（絶対パスに変換してから相対化）
            html_abs = args.html.resolve()
            svg_abs = args.svg.resolve()
            run_dir_abs = run_dir.resolve()
            output_files = [
                {"path": str(html_abs.relative_to(run_dir_abs)), "size": html_abs.stat().st_size},
                {"path": str(svg_abs.relative_to(run_dir_abs)), "size": svg_abs.stat().st_size},
            ]

            # レビューチェックリストを作成
            flow = load_flow(args.json)
            checklist = [
                {"label": "actors/phases/tasks/flows/issues をすべて保持している",
                 "status": "OK" if all(len(flow.get(key, [])) > 0 for key in ["actors", "phases", "tasks", "flows", "issues"]) else "NG"},
                {"label": "issues に曖昧点や未決事項が列挙されている",
                 "status": "OK" if len(flow.get("issues", [])) > 0 else "NG"},
                {"label": "gateway を含む場合は flows で参照漏れがない",
                 "status": "OK" if all(gw["id"] in {link.get("from") for link in flow.get("flows", [])} | {link.get("to") for link in flow.get("flows", [])} for gw in flow.get("gateways", [])) else "NG"},
                {"label": "tasks の handoff_to が必ず存在する",
                 "status": "OK" if all("handoff_to" in task for task in flow.get("tasks", [])) else "NG"},
            ]

            run_manager.update_info_md(run_dir, {
                "output_files": output_files,
                "review_checklist": checklist,
            })
            print(f"[export] 実行情報を {run_dir / 'info.md'} に追記しました。")


if __name__ == "__main__":
    main()
