"""
Mermaid Flowchart Generator for Business-flow-maker.

This module converts flow.json to Mermaid flowchart (TD format) with markdown code blocks.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict, List


def sanitize_label(text: str) -> str:
    """
    Mermaidのラベルとして安全な文字列に変換する。

    ダブルクォートやその他の特殊文字をエスケープまたは除去する。
    """
    # ダブルクォートをシングルクォートに置換
    text = text.replace('"', "'")
    # 改行を空白に置換
    text = text.replace("\n", " ").replace("\r", " ")
    return text.strip()


def generate_mermaid(flow_data: Dict[str, Any]) -> str:
    """
    flow.json データから Mermaid flowchart TD 形式の文字列を生成する。

    Args:
        flow_data: flow.json の内容（dict形式）

    Returns:
        Mermaid flowchart TD 形式の文字列（markdownコードブロック付き）
    """
    lines: List[str] = []
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("")

    # タスクノードを定義
    tasks = flow_data.get("tasks", [])
    for task in tasks:
        task_id = task["id"]
        task_name = sanitize_label(task["name"])
        # 角丸四角形でタスクを表現
        lines.append(f'    {task_id}["{task_name}"]')

    # ゲートウェイノードを定義（ひし形）
    gateways = flow_data.get("gateways", [])
    for gateway in gateways:
        gw_id = gateway["id"]
        gw_name = sanitize_label(gateway["name"])
        # ひし形でゲートウェイを表現
        lines.append(f'    {gw_id}{{"{gw_name}"}}')

    if tasks or gateways:
        lines.append("")

    # フローを定義
    flows = flow_data.get("flows", [])
    for flow in flows:
        from_id = flow.get("from", "")
        to_id = flow.get("to", "")
        condition = flow.get("condition")

        if not from_id or not to_id:
            continue

        if condition:
            # 条件付きフロー（ラベル付き矢印）
            condition_label = sanitize_label(condition)
            lines.append(f'    {from_id} -->|"{condition_label}"| {to_id}')
        else:
            # 通常のフロー
            lines.append(f'    {from_id} --> {to_id}')

    lines.append("```")
    return "\n".join(lines)


def load_flow_json(json_path: pathlib.Path) -> Dict[str, Any]:
    """
    flow.json ファイルを読み込む。

    Args:
        json_path: flow.json ファイルのパス

    Returns:
        JSONデータ（dict形式）
    """
    return json.loads(json_path.read_text(encoding="utf-8"))


def save_mermaid(mermaid_text: str, output_path: pathlib.Path) -> None:
    """
    Mermaid テキストをファイルに保存する。

    Args:
        mermaid_text: Mermaid flowchart テキスト
        output_path: 出力ファイルパス
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mermaid_text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースする。"""
    parser = argparse.ArgumentParser(
        description="Convert flow.json to Mermaid flowchart format."
    )
    parser.add_argument(
        "--json",
        type=pathlib.Path,
        default=pathlib.Path("output/flow.json"),
        help="入力 flow.json ファイルパス（デフォルト: output/flow.json）",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("output/flow.mmd"),
        help="出力 .mmd ファイルパス（デフォルト: output/flow.mmd）",
    )
    return parser.parse_args()


def main() -> None:
    """メイン処理：flow.json を読み込み、Mermaid 形式に変換して保存する。"""
    from src.utils import run_manager

    args = parse_args()

    # flow.json を読み込み
    flow_data = load_flow_json(args.json)

    # Mermaid 形式に変換
    mermaid_text = generate_mermaid(flow_data)

    # ファイルに保存
    save_mermaid(mermaid_text, args.output)

    print(f"[export] Mermaid flowchart を {args.output} に保存しました。")

    # runs/構造を検出し、info.mdを更新
    json_path = args.json.resolve()
    if "runs" in json_path.parts:
        # runs/ディレクトリを特定
        run_dir = None
        for i, part in enumerate(json_path.parts):
            if part == "runs" and i + 1 < len(json_path.parts):
                run_dir = pathlib.Path(*json_path.parts[:i+2])
                break

        if run_dir and run_dir.exists() and (run_dir / "info.md").exists():
            # 出力ファイル情報を追記
            output_files = [
                {"path": str(args.output.relative_to(run_dir)), "size": args.output.stat().st_size},
            ]

            run_manager.update_info_md(run_dir, {"output_files": output_files})
            print(f"[export] 実行情報を {run_dir / 'info.md'} に追記しました。")


if __name__ == "__main__":
    main()
