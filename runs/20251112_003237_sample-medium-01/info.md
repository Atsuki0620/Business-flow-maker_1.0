# 実行情報

## 基本情報
- **実行ID**: 20251112_003237_sample-medium-01
- **実行日時**: 2025-11-12 00:32:59
- **実行コマンド**: `C:\Users\atsuk\OneDrive\ドキュメント\Coding Agent\2511_Business-flow-maker\src\core\generator.py --input samples/input/sample-medium-01.md --model gpt-4o-mini`

## 入力
- **元ファイルパス**: `samples\input\sample-medium-01.md`
- **サイズ**: 927 bytes
- **SHA-256**: `be423b0805d8bd72f4f67b1011dbe3928c921f28d7f2ac1ae94333622366a233`

## 生成設定
- **LLMモデル**: gpt-4o-mini
- **プロバイダ**: openai
- **実行時間**: 21.89秒

## 出力ファイル
- `output\flow.json` (3691 bytes)


## JSON検証結果
- **actors**: 4件
- **phases**: 3件
- **tasks**: 8件
- **flows**: 7件
- **gateways**: 0件
- **issues**: 1件

## 追加出力ファイル
- `output\flow.html` (4873 bytes)
- `output\flow.svg` (3788 bytes)

## レビューチェックリスト
- [✓] actors/phases/tasks/flows/issues をすべて保持している
- [✓] issues に曖昧点や未決事項が列挙されている
- [✓] gateway を含む場合は flows で参照漏れがない
- [✓] tasks の handoff_to が必ず存在する

## 追加出力ファイル
- `output\flow.mmd` (821 bytes)