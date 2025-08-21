# Hero Skill Data Processor - Specification Document (v6.0)

## 1. プロジェクト概要

### 1.1. 目的
複数のデータソースを統合・解析し、Astro.js製の新しいHeroデータベースのための、信頼できる構造化データソースを生成する。
このプロジェクトの最終目標は、「100%の完全自動化」という非現実的な理想を追うことではない。
**「標準的なスキルは自動解析し、複雑な例外スキルは、それぞれに特化した『専門家パーサー』を追加開発することで対応できる、拡張性の高い、持続可能なデータパイラインを構築する」**こと、それこそが、私たちの目的である。

### 1.2. 最終成果物
-   **`hero_skill_output_*.csv`**: Google Sheetsでのレビューを目的とした、人間が閲覧するための整形済みテキスト。巨大になる場合は、自動で複数ファイルに分割される。
-   **`hero_skill_output_debug.csv`**: `lang_id`や`params`といった、構造と数値の情報に特化した、軽量なデバッグ用CSV。
-   **`debug_hero_data.json`**: 全てのデータソースを統合した「真実の源」。解析プロセスは、必ず、一度ディスクに書き出された、このファイルを読み込むことから始める。

## 2. ファイル構成 (`packages/parser_engine/`)

### 2.1. コア・モジュール
-   **`hero_main.py` (司令塔):**
    -   処理フロー全体の制御。
    -   各専門家パーサーをインポートし、適切なタイミングで仕事を依頼する。
    -   最終的なファイルの出力を担当する。
-   **`hero_data_loader.py` (データ入力担当):**
    -   全ての入力ファイル（ゲームデータ、ルールCSV）をメモリに読み込む。
-   **`hero_parser.py` (基本ツール置き場 / 統括マネージャー):**
    -   **全ての専門家が共通で利用する**、基本的なヘルパー関数 (`find_best_lang_id`, `generate_description`など) を提供する。
    -   `get_full_hero_data`による、データ統合フェーズの中核を担う。

### 2.2. `parsers/` パッケージ (専門家たちの工房)
-   **設計思想:**
    -   スキルタイプの種類（`properties`, `familiars`など）や、特定の複雑なスキル（`ChainStrike`など）ごとに、**責務が完全に分離された、独立したパーサー**を配置する。
    -   各専門家は、`hero_parser.py`から基本ツールを`import`して利用する。
-   **現在の専門家リスト:**
    -   **`parse_properties.py`**: 標準的なプロパティと、コンテナ型スキルの解析を担当。
    -   **`parse_status_effects.py`**: `statusEffect`の解析を担当。`search_prefix`引数により、`specials.`と`familiar.`の両方の文脈で動作できる。
    -   **`parse_familiars.py`**: `summonedFamiliars`の解析を担当。導入文と、内包する`effects`を、それぞれ適切な専門家と連携して解析する「マネージャー」役を担う。
    -   **`parse_passive_skills.py`**: パッシブスキルの解析を担当。
    -   **`parse_clear_buffs.py`**: `buffToRemove`の解析を担当。
    -   **`parse_chain_strike.py`**: `DifferentExtraHitPowerChainStrike`という、極めて特殊なプロパティの解析だけに特化した、最初の「超・専門家」。
-   
### ファイルリスト
hero_main.py:
https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_main.py
packages/parser_engine/hero_parser.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_parser.py
hero_data_loader.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_data_loader.py
packages/parser_engine/parser/
parse_chain_strike.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_chain_strike.py
parse_clear_buffs.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_clear_buffs.py
parse_familiars.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_familiars.py
parse_passive_skills.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_passive_skills.py
parse_properties.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_properties.py
parse_status_effects.py: https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_status_effects.py

## 3. データ処理アーキテクチャ

### 3.1. 2段階解析プロセス
-   **第一段階：データ統合フェーズ (`phase_one_integrate_data`)**:
    -   `hero_data_loader`と`hero_parser`の`get_full_hero_data`が連携し、全てのID参照を解決した、完全な`debug_hero_data.json`を`data/output/`に生成する。
-   **第二段階：スキル解析フェーズ (`phase_two_parse_skills`)**:
    -   `hero_main.py`が司令塔となり、`debug_hero_data.json`を読み込む。
    -   ヒーローのデータに応じて、`parsers/`パッケージから適切な専門家を呼び出し、スキルの解析を依頼する。
    -   **特殊なスキル**（`ChainStrike`など）は、汎用パーサーに渡される**前**に、司令塔によって検知され、対応する専門家に直接、仕事が振り分けられる。

## 4. スキル解析ロジック

### 4.1. 基本思想：「ハイブリッド・アプローチ」
-   **標準スキル**: `find_best_lang_id`による「プレフィックスフィルタリング＆スコアリング」で、高い精度での自動推測を目指す。
-   **準・特殊スキル**: `parse_familiars`のように、パーサーが「マネージャー」役となり、内部のデータを、他の適切な専門家に再依頼（デリゲーション）することで、複雑な構造を解決する。
-   **超・特殊スキル**: `parse_chain_strike`のように、完全に独立した専門家ファイルを用意し、そのスキルだけの、決め打ちのロジックで、100%の正確性を目指す。

---