# Hero Skill Data Processor - Specification Document (v8.1)

## 1. プロジェクト概要

### 1.1. 目的
CUIベースの解析エンジンと、WebベースのGUI補助ツール、そしてそれらを繋ぐAPIサーバーを構築する。
最終的な目的は、**「Python製のAIが生成した『解析の下書き』を、人間が、専用のGUIツール上で、効率的にレビュー、修正、そして完成させるための、持続可能なコンテンツ管理パイプラインを確立する」**ことである。

### 1.2. 主要な成果物
-   **APIサーバー**: FastAPIで構築され、Render上でホスティングされる。ヒーローデータの読み取りと検索機能を提供する。
-   **GUI補助ツール**: HTML/CSS/JavaScript(Alpine.js)で構築された、ローカルで動作するシングルページアプリケーション。APIサーバーと通信し、データの閲覧とキュレーションを行う。
-   **最終データ出力**: ツールによって生成・管理される各種CSVおよびJSONファイル。これらは、最終的なAstro.js製HeroDBのデータソースとなる。

### 1.3. Gitリポジトリ
-   **[HeroDB_Project (GitHub)](https://github.com/birksgone/HeroDB_Project)**

## 2. ファイル構成 (`HeroDB_Project/`)

### 2.1. `packages/`
-   **`parser_engine/` (解析エンジン)**
    -   **`hero_main.py`**: CUIとしての実行エントリーポイント。
    -   **`hero_data_loader.py`**: 全ての入力データ（ゲームデータ、ルールCSV）を読み込む。
    -   **`hero_parser.py`**: 全てのパーサーが共通で利用する、基本的なヘルパー関数 (`find_best_lang_id`など) を提供する。
    -   **`parsers/`**: スキルタイプごとの、独立した専門家パーサーを格納するパッケージ。
-   **`api_server/` (APIサーバー)**
    -   **`main.py`**: FastAPIアプリケーションの本体。データ読み込み、認証、APIエンドポイントの定義を行う。
-   **`editing_gui/` (GUI補助ツール)**
    -   **`index.html`**: UIの骨格。
    -   **`style.css`**: ダークモードのスタイル定義。
    -   **`app.js`**: Alpine.jsを使った、UIの全ロジック。
-   **`tools/` (補助ツール)**
    -   **`extract_learning_data.py`**: 特定の条件に合うスキルブロックを`debug_hero_data.json`から抽出するための、開発支援ツール。

### 2.2. `data/`
-   Gitの追跡対象外 (`.gitignore`)。
-   全てのゲーム生データ (`characters.json`など) と、スクリプトの出力ファイル (`debug_hero_data.json`など) を格納する。

### 2.3. ファイルリスト (Raw URLs)
-   **hero_main.py**: 
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_main.py`
-   **hero_data_loader.py**: 
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_data_loader.py`
-   **hero_parser.py**: 
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_parser.py`
-   **`parsers/`**:
    -   `parse_chain_strike.py`: `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_chain_strike.py`
    -   `parse_clear_buffs.py`: `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_clear_buffs.py`
    -   `parse_familiars.py`: `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_familiars.py`
    -   `parse_passive_skills.py`: `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_passive_skills.py`
    -   `parse_properties.py`: `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_properties.py`
    -   `parse_status_effects.py`: `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/parsers/parse_status_effects.py`
-   **document.md**:
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/document.md`

## 3. APIサーバー (`packages/api_server/main.py`)

-   **フレームワーク**: FastAPI
-   **ホスティング**: Render (Web Service) - **[https://herodb-project.onrender.com/](https://herodb-project.onrender.com/)**
-   **認証**: Basic認証
-   **データソース**: サーバー起動時に`debug_hero_data.json`と`English.csv`/`Japanese.csv`をメモリにロードする。
-   **主要エンドポイント**:
    -   `GET /api/hero/{hero_id}`: 特定ヒーローの、解決済みの完全な生データを返す。
    -   `GET /api/query`: `key`と`keyword`を元に、全ヒーローのデータから、条件に合うスキルブロックを検索・抽出する。
    -   `GET /api/lang/super_search`: `id`, `en`, `ja`の各テキストに、複数のキーワード（AND/OR）で、高度な検索を行う。

## 4. GUI補助ツール (`packages/editing_gui/`)

-   **技術スタック**: HTML, CSS, JavaScript (Alpine.js)
-   **実行環境**: ローカルのWebブラウザ（サーバー不要）。`index.html`を直接開いて使用する。
-   **主要機能**:
    -   APIターゲットの切り替え（Local / Render）。
    -   localではユーザーののWidnowsローカル、Rebderは、https://dashboard.render.com/を使用。切り替えてどちらも使用できる。
    -   API認証情報の入力と、ブラウザの`localStorage`への保存。
    -   ヒーロースキルブロックのキーワード検索機能。
    -   言語データベースの、複合キーワード検索機能。
    -   検索結果の、テーブル形式と生JSON形式での、表示切り替え。
    -   

## 5. 開発・運用フロー

1.  **データ更新**: `data/`フォルダ内のゲーム生データを更新する。
2.  **CUI実行**: `hero_main.py`を実行し、`data/output/debug_hero_data.json`を最新の状態に更新する。
3.  **APIサーバー起動**: ローカルで`uvicorn`コマンドを使い、APIサーバーを起動する。
4.  **GUIツール起動**: `packages/editing_gui/index.html`をブラウザで開く。
5.  **データキュレーション**: GUIツールを使い、API経由でデータを検索・分析する。
6.  **デプロイ**: コードの変更（APIサーバー、GUIツール、解析エンジン）を`git push`すると、Renderが自動でAPIサーバーを再デプロイする。