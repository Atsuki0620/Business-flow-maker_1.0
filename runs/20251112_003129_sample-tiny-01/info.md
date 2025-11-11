# 実行情報

## 基本情報
- **実行ID**: 20251112_003129_sample-tiny-01
- **実行日時**: 2025-11-12 00:31:46
- **実行コマンド**: `C:\Users\atsuk\OneDrive\ドキュメント\Coding Agent\2511_Business-flow-maker\src\core\generator.py --input samples/input/sample-tiny-01.md --model gpt-4o-mini`

## 入力
- **元ファイルパス**: `samples\input\sample-tiny-01.md`
- **サイズ**: 1213 bytes
- **SHA-256**: `7f1bcf9969166233e15501f31bfd2b0f27fa071983f23a460d2c9834bd8ad5eb`

## 生成設定
- **LLMモデル**: gpt-4o-mini
- **プロバイダ**: openai
- **実行時間**: 17.30秒

## 出力ファイル
- `output\flow.json` (3316 bytes)


## JSON検証結果
- **actors**: 2件
- **phases**: 3件
- **tasks**: 6件
- **flows**: 7件
- **gateways**: 1件
- **issues**: 0件

## 追加出力ファイル
- `output\flow.html` (4535 bytes)
- `output\flow.svg` (3519 bytes)

## レビューチェックリスト
- [✗] actors/phases/tasks/flows/issues をすべて保持している
- [✗] issues に曖昧点や未決事項が列挙されている
- [✓] gateway を含む場合は flows で参照漏れがない
- [✓] tasks の handoff_to が必ず存在する

## 追加出力ファイル
- `output\flow.mmd` (735 bytes)