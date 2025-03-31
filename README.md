# Voice Control Application

## 概要
このプロジェクトは、音声認識を利用してデバイスを制御するアプリケーションです。ユーザーは音声コマンドを使用して、さまざまなデバイスを操作したり、AIからの応答を受け取ったりすることができます。主な機能には、音声認識、デバイス制御、天気情報の取得が含まれています。

## ファイル構成
- `voice_control.py`: 音声制御アプリケーションのメインロジックを含むファイル。音声認識、デバイス制御、AI応答などの機能を提供するクラス `Voice` と `Control` を定義しています。
- `custom_scenes.json`: カスタムシーンの設定を含むJSONファイル。シーン名や実行するコマンドが定義されています。
- `custom_devices.json`: カスタムデバイスの設定を含むJSONファイル。デバイス名や制御コマンドが定義されています。
- `config.json`: アプリケーションの設定を含むJSONファイル。APIキーや天気に使用する位置情報などの設定が含まれています。

## インストール手順
1. リポジトリをクローンします。
   ```
   git clone https://github.com/ryo08271154/voice_control.git
   ```

2. 必要なライブラリをインストールします。以下のコマンドを使用して、必要なライブラリを個別にインストールしてください
   ```
   pip install pyaudio
   pip install numpy
   pip install vosk
   pip install requests
   pip install wit
   pip install google-generativeai
   ```

3. 以下のJSONファイルを作成し、必要な設定を記述します。

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
         "weather_api_key": "天気APIキー",
         "wit_token": "Wit.aiトークン",
         "genai": "Generative AI APIキー"
       },
       "location": {
         "latitude": "緯度",
         "longitude": "経度"
       },
       "url": {
         "server_url": "サーバーのURL"
       },
       "chromecasts": {
         "friendly_names": ["Chromecastデバイス名"]
       }
     }
     ```

## 使用方法
1. アプリケーションを実行します。
   ```
   python voice_control.py
   ```

2. 音声コマンドを発話してデバイスを制御します。以下は使用例です：

   - **デバイスの操作**
     - 「電気をつけて」：登録されたデバイスの電源をオンにします。
     - 「テレビを消して」：登録されたデバイスの電源をオフにします。

   - **メディア操作**
     - 「再生して」：メディアの再生を開始します。
     - 「一時停止して」：メディアを一時停止します。
     - 「停止して」：メディアを停止します。

   - **音量調整**
     - 「音量を上げて」：音量を上げます。
     - 「音量を下げて」：音量を下げます。

   - **時間や日付の確認**
     - 「今何時？」：現在の時刻を教えてくれます。
     - 「今日は何日？」：現在の日付を教えてくれます。

   - **天気情報の取得**
     - 「今日の天気は？」：現在の天気情報を取得します。
     - 「明日の天気は？」：翌日の天気情報を取得します。
