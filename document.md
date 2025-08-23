# Hero Skill Data Processor - Specification Document (v9.0)

## 1. プロジェクト概要

### 1.1. 目的
CUIベースの解析エンジンと、WebベースのGUI補助ツール、そしてそれらを繋ぐAPIサーバーを構築する。
最終的な目的は、**「Python製のAIが生成した『解析の下書き』を、人間が、専用のGUIツール上で、効率的にレビュー、修正、そして完成させるための、持続可能なコンテンツ管理パイプラインを確立する」**ことである。

### 1.2. 主要な成果物
-   **APIサーバー**: FastAPIで構築され、Render上でホスティングされる。ヒーローデータの読み取りと検索機能を提供する。
-   **GUI補助ツール**: HTML/CSS/JavaScript(Alpine.js)で構築された、ローカルまたはRender上で動作するシングルページアプリケーション。APIサーバーと通信し、データの閲覧とキュレーションを行う。
-   **最終データ出力**: CUIツールによって生成・管理される各種CSVおよびJSONファイル。これらは、最終的なAstro.js製HeroDBのデータソースとなる。

### 1.3. Gitリポジトリ
-   **[HeroDB_Project (GitHub)](https://github.com/birksgone/HeroDB_Project)**

## 2. アーキテクチャ概要
このプロジェクトは、3つの主要なコンポーネントが連携して動作する、モダンなWebアーキテクチャを採用している。
-   `parser_engine` (CUI): ローカルでのデータ一括生成・更新を担当。
-   `api_server` (バックエンド): 生成されたデータを、Web APIとして提供する。
-   `editing_gui` (フロントエンド): APIと通信し、人間がデータを閲覧・分析するためのインターフェースを提供する。

## 3. コンポーネント詳細

### 3.1. `parser_engine/` (解析エンジン)
-   **役割**: 全てのヒーローデータを解析し、`debug_hero_data.json`などの、構造化された中間データファイルを生成する、プロジェクトの心臓部。
-   **主要ファイル**:
    -   `hero_main.py`: CUIとしての実行エントリーポイント。
    -   `hero_parser.py`: 全パーサーが共通で利用するヘルパー関数群。
    -   `parsers/`: スキルタイプごとの、独立した専門家パーサーを格納するパッケージ（プラグイン・アーキテクチャ）。

### 3.2. `api_server/` (APIサーバー)
-   **役割**: `parser_engine`が生成したデータを、Web APIとして世界に公開する。
-   **フレームワーク**: FastAPI
-   **ホスティング**: Render (Web Service)
-   **URL**: **[https://herodb-project.onrender.com/](https://herodb-project.onrender.com/)**
-   **主要エンドポイント**:
    -   `GET /api/hero/{hero_id}`: 特定ヒーローの生データを返す。
    -   `GET /api/query`: `key`と`keyword`を元に、全ヒーローのデータからスキルブロックを検索する。
    -   `GET /api/lang/super_search`: `id`, `en`, `ja`の各テキストに、複合キーワードで高度な検索を行う。

### 3.3. `editing_gui/` (GUI補助ツール)
-   **役割**: APIサーバーと通信し、人間がデータを快適に閲覧・分析するためのUIを提供する。
-   **技術スタック**: HTML, CSS, JavaScript (Alpine.js)
-   **ホスティング**: Render (Static Site)
-   **URL**: **[https://editing-gui.onrender.com/](https://editing-gui.onrender.com/)**
-   **主要機能**:
    -   APIターゲットの切り替え（Local / Render）。
    -   ヒーロースキルブロックと、言語データベースの、複合検索機能。
    -   検索結果のテーブル/JSON表示と、「Share with AI」URL生成機能。

### 3.4. `tools/` (開発支援ツール)
-   **役割**: 開発プロセスを補助するための、独立したスクリプトを格納する。
-   **主要ファイル**:
    -   `extract_learning_data.py`: 特定のスキルを持つヒーローのデータだけを抽出し、AIの分析（学習）のためのデータセットを作成する。

## 4. ファイルリスト (Raw URLs)
-   **hero_main.py**: 
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_main.py`
-   **hero_parser.py**: 
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/parser_engine/hero_parser.py`
-   **api_server/main.py**:
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/api_server/main.py`
-   **editing_gui/index.html**:
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/packages/editing_gui/index.html`
-   **document.md**:
    -   `https://raw.githubusercontent.com/birksgone/HeroDB_Project/refs/heads/main/document.md`