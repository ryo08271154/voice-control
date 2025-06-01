# 音声制御アプリケーション

## 概要
このプロジェクトは、音声認識を利用してデバイスを制御するアプリケーションです。ユーザーは音声コマンドを使用して、SwitchBotデバイスやカスタムデバイスを操作したり、AIからの応答を受け取ったりすることができます。主な機能には、音声認識、デバイス制御、天気情報の取得、Chromecastメディア制御が含まれています。

## ファイル構成
- `voice_control.py`: 音声制御アプリケーションのメインロジックを含むファイル。
- `control.py`: Fletを使用したGUIアプリケーションのメインファイル。音声認識と連携した視覚的なインターフェースを提供します。
- `switchbot.py`: SwitchBot APIとの通信を行うモジュール。デバイスリストの取得、シーンの実行、デバイスの制御を行います。
- `custom_scenes.json`: カスタムシーンの設定を含むJSONファイル。シーン名や実行するコマンドが定義されています。
- `custom_devices.json`: カスタムデバイスの設定を含むJSONファイル。デバイス名や制御コマンドが定義されています。
- `config.json`: アプリケーションの設定を含むJSONファイル。各種APIキーや位置情報などの設定が含まれています。

## 前提条件
- Python 3.7以上
- マイクロフォンが接続されたデバイス
- Voskの日本語音声認識モデル（`vosk-model-ja`）をプロジェクトディレクトリに配置

## インストール手順
1. リポジトリをクローンします。
   ```bash
   git clone https://github.com/ryo08271154/voice_control.git
   cd voice_control
   ```

2. 必要なライブラリをインストールします。
   ```bash
   pip install pyaudio
   pip install numpy
   pip install vosk
   pip install requests
   pip install wit
   pip install google-generativeai
   pip install pychromecast
   pip install flet
   ```

3. Voskの日本語音声認識モデルをダウンロードし、プロジェクトディレクトリに配置します。
   ```bash
   # モデルをダウンロード（例）
   wget https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip
   unzip vosk-model-ja-0.22.zip
   mv vosk-model-ja-0.22 vosk-model-ja
   ```

4. 以下のJSONファイルを作成し、必要な設定を記述します。

   - **`custom_scenes.json`**: カスタムシーンの設定を記述します。
     ```json
     {
       "sceneList": [
         {
           "sceneName": "シーン名",
           "command": "実行するコマンド"
         }
       ]
     }
     ```

   - **`custom_devices.json`**: カスタムデバイスの設定を記述します。
     ```json
     {
       "deviceList": [
         {
           "deviceName": "デバイス名",
           "turnOn": "オンにするコマンド",
           "turnOff": "オフにするコマンド"
         }
       ]
     }
     ```

   - **`config.json`**: アプリケーションの設定を記述します。
     ```json
     {
       "apikeys": {
         "weather_api_key": "OpenWeatherMap APIキー",
         "wit_token": "Wit.aiトークン",
         "genai": "Google Generative AI APIキー",
         "switchbot_token": "SwitchBot APIトークン",
         "switchbot_secret": "SwitchBot APIシークレット"
       },
       "location": {
         "latitude": "緯度（例: 35.6762）",
         "longitude": "経度（例: 139.6503）"
       },
       "url": {
         "server_url": "音声合成サーバーのURL（オプション）"
       },
       "chromecasts": {
         "friendly_names": ["リビングのChromecast", "寝室のChromecast"]
       },
       "genai": {
         "model_name":"gemini-1.5-flash-8b",
         "system_instruction":"あなたは簡潔に3文以下で回答する音声アシスタントです"
       },
     }
     ```

## 使用方法

### コマンドラインから実行
```bash
python voice_control.py
```

### GUIアプリケーションとして実行
```bash
python control.py
```

### 音声コマンド例

- **デバイスの操作**
  - 「電気をつけて」：電気デバイスの電源をオンにします
  - 「テレビを消して」：テレビの電源をオフにします
  - 「エアコンをつけて」：エアコンをオンにします

- **メディア操作（Chromecast対応）**
  - 「再生して」：メディアの再生を開始します
  - 「一時停止して」：メディアを一時停止します
  - 「停止して」：メディアを停止します
  - 「音量を上げて」：音量を上げます
  - 「音量を下げて」：音量を下げます
  - 「10秒戻して」：10秒巻き戻します
  - 「30秒スキップして」：30秒早送りします

- **時間や日付の確認**
  - 「今何時？」：現在の時刻を教えてくれます
  - 「今日は何日？」：現在の日付を教えてくれます

- **天気情報の取得**
  - 「今日の天気は？」：現在の天気情報を取得します
  - 「明日の天気は？」：翌日の天気情報を取得します

- **AI対話**
  - 「○○とは何ですか？」：様々な質問にAIが回答します

## 必要なAPIキー
- **OpenWeatherMap API**: 天気情報の取得に使用
- **Wit.ai**: 自然言語処理による音声コマンドの解析に使用
- **Google Generative AI (Gemini)**: AI対話機能に使用
- **SwitchBot API**: SwitchBotデバイスの制御に使用

## 対応デバイス
- SwitchBot対応デバイス（ライト、テレビ、エアコンなど）
- Chromecast（メディア再生、音量制御）
- カスタムデバイス（コマンドライン経由で制御可能なデバイス）

## 注意事項
- 音声認識にはVoskライブラリを使用しているため、インターネット接続は必須ではありませんが、各種API機能を使用する場合は接続が必要です
- マイクロフォンへのアクセス許可が必要です
- SwitchBotデバイスを使用する場合は、事前にSwitchBotアプリでデバイス設定を完了してください
