"""
Run Manager for Business-flow-maker.

実行履歴の自動管理機能を提供します：
- タイムスタンプ付き実行ディレクトリの作成
- 入力ファイルのコピー
- info.md による実行情報の記録
- 実行履歴の一覧取得
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def create_run_dir(input_path: Path, base_dir: Path = Path("runs")) -> Path:
    """
    タイムスタンプ付き実行ディレクトリを作成する。

    Args:
        input_path: 入力ファイルのパス
        base_dir: 実行履歴を格納する基底ディレクトリ（デフォルト: runs/）

    Returns:
        作成された実行ディレクトリのパス（例: runs/20251110_123456_sample-small-01/）

    Example:
        >>> run_dir = create_run_dir(Path("samples/input/sample-small-01.md"))
        >>> print(run_dir)
        runs/20251110_123456_sample-small-01
    """
    # タイムスタンプ生成（YYYYMMDD_HHMMSS形式）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 入力ファイル名（拡張子なし）を取得
    input_stem = input_path.stem

    # 実行ディレクトリ名を生成
    run_dir_name = f"{timestamp}_{input_stem}"
    run_dir = base_dir / run_dir_name

    # ディレクトリ作成（親ディレクトリも含む）
    run_dir.mkdir(parents=True, exist_ok=True)

    # output サブディレクトリを作成
    output_dir = run_dir / "output"
    output_dir.mkdir(exist_ok=True)

    return run_dir


def copy_input_file(src: Path, run_dir: Path) -> None:
    """
    入力ファイルを実行ディレクトリにコピーする。

    Args:
        src: 入力ファイルのパス
        run_dir: 実行ディレクトリのパス

    Example:
        >>> copy_input_file(Path("samples/input/sample-small-01.md"), run_dir)
    """
    if not src.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {src}")

    # 入力ファイルをコピー
    dest = run_dir / src.name
    shutil.copy2(src, dest)


def _calculate_file_hash(file_path: Path) -> str:
    """ファイルのSHA-256ハッシュを計算する。"""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_info_md(run_dir: Path, info: Dict[str, Any]) -> None:
    """
    info.md を生成する。

    Args:
        run_dir: 実行ディレクトリのパス
        info: 記録する情報（dict形式）

    Expected keys in info:
        - execution_id: 実行ID
        - execution_time: 実行日時
        - command: 実行コマンド
        - input_file: 入力ファイルパス
        - input_size: 入力ファイルサイズ
        - input_hash: 入力ファイルのSHA-256
        - model: LLMモデル名（オプション）
        - provider: LLMプロバイダ（オプション）
        - elapsed_time: 実行時間（オプション）
        - output_files: 出力ファイルのリスト（オプション）

    Example:
        >>> save_info_md(run_dir, {"execution_id": "20251110_123456_sample", ...})
    """
    info_path = run_dir / "info.md"

    lines = ["# 実行情報", ""]

    # 基本情報
    lines.append("## 基本情報")
    lines.append(f"- **実行ID**: {info.get('execution_id', 'N/A')}")
    lines.append(f"- **実行日時**: {info.get('execution_time', 'N/A')}")
    lines.append(f"- **実行コマンド**: `{info.get('command', 'N/A')}`")
    lines.append("")

    # 入力
    lines.append("## 入力")
    lines.append(f"- **元ファイルパス**: `{info.get('input_file', 'N/A')}`")
    lines.append(f"- **サイズ**: {info.get('input_size', 0)} bytes")
    lines.append(f"- **SHA-256**: `{info.get('input_hash', 'N/A')}`")
    lines.append("")

    # 生成設定
    if "model" in info or "provider" in info:
        lines.append("## 生成設定")
        if "model" in info:
            lines.append(f"- **LLMモデル**: {info['model']}")
        if "provider" in info:
            lines.append(f"- **プロバイダ**: {info['provider']}")
        if "elapsed_time" in info:
            lines.append(f"- **実行時間**: {info['elapsed_time']:.2f}秒")
        lines.append("")

    # 出力ファイル
    if "output_files" in info:
        lines.append("## 出力ファイル")
        for file_info in info["output_files"]:
            lines.append(f"- `{file_info['path']}` ({file_info['size']} bytes)")
        lines.append("")

    info_path.write_text("\n".join(lines), encoding="utf-8")


def update_info_md(run_dir: Path, updates: Dict[str, Any]) -> None:
    """
    既存の info.md に情報を追記する。

    Args:
        run_dir: 実行ディレクトリのパス
        updates: 追記する情報（dict形式）

    Expected keys in updates:
        - json_validation: JSON検証結果（dict）
          - actors_count: actors数
          - phases_count: phases数
          - tasks_count: tasks数
          - flows_count: flows数
          - gateways_count: gateways数
          - issues_count: issues数
        - review_checklist: レビューチェックリスト（list of dict）
          - label: チェック項目のラベル
          - status: OK/NG
        - output_files: 追加の出力ファイル（list of dict）
          - path: ファイルパス
          - size: ファイルサイズ

    Example:
        >>> update_info_md(run_dir, {"json_validation": {...}, "review_checklist": [...]})
    """
    info_path = run_dir / "info.md"

    if not info_path.exists():
        raise FileNotFoundError(f"info.md が見つかりません: {info_path}")

    # 既存の内容を読み込む
    existing_content = info_path.read_text(encoding="utf-8")
    lines = [existing_content]

    # JSON検証結果
    if "json_validation" in updates:
        validation = updates["json_validation"]
        lines.append("\n## JSON検証結果")
        lines.append(f"- **actors**: {validation.get('actors_count', 0)}件")
        lines.append(f"- **phases**: {validation.get('phases_count', 0)}件")
        lines.append(f"- **tasks**: {validation.get('tasks_count', 0)}件")
        lines.append(f"- **flows**: {validation.get('flows_count', 0)}件")
        lines.append(f"- **gateways**: {validation.get('gateways_count', 0)}件")
        lines.append(f"- **issues**: {validation.get('issues_count', 0)}件")

    # 追加の出力ファイル
    if "output_files" in updates:
        lines.append("\n## 追加出力ファイル")
        for file_info in updates["output_files"]:
            lines.append(f"- `{file_info['path']}` ({file_info['size']} bytes)")

    # レビューチェックリスト
    if "review_checklist" in updates:
        lines.append("\n## レビューチェックリスト")
        for item in updates["review_checklist"]:
            status = "✓" if item["status"] == "OK" else "✗"
            lines.append(f"- [{status}] {item['label']}")

    info_path.write_text("\n".join(lines), encoding="utf-8")


def get_latest_run(base_dir: Path = Path("runs")) -> Optional[Path]:
    """
    最新の実行ディレクトリを返す（タイムスタンプソート）。

    Args:
        base_dir: 実行履歴を格納する基底ディレクトリ（デフォルト: runs/）

    Returns:
        最新の実行ディレクトリのパス。存在しない場合は None。

    Example:
        >>> latest = get_latest_run()
        >>> print(latest)
        runs/20251110_123456_sample-small-01
    """
    if not base_dir.exists():
        return None

    # タイムスタンプでソート（降順）
    run_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True
    )

    return run_dirs[0] if run_dirs else None


def list_runs(base_dir: Path = Path("runs"), limit: int = 10) -> List[Path]:
    """
    実行履歴一覧を返す（新しい順）。

    Args:
        base_dir: 実行履歴を格納する基底ディレクトリ（デフォルト: runs/）
        limit: 取得する最大件数（デフォルト: 10）

    Returns:
        実行ディレクトリのパスのリスト

    Example:
        >>> runs = list_runs(limit=5)
        >>> for run in runs:
        ...     print(run)
        runs/20251110_123456_sample-small-01
        runs/20251110_120000_sample-medium-01
    """
    if not base_dir.exists():
        return []

    # タイムスタンプでソート（降順）
    run_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True
    )

    return run_dirs[:limit]
