import asyncio
import webbrowser
import websockets
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from plugin import BasePlugin
from commands import VoiceCommand


EMOTION_KEYWORDS = {
    # 基本的な感情表情
    "happy": ["嬉", "喜", "幸", "楽", "笑", "愉", "歓", "快", "欣", "悦", "慶", "祝", "福", "吉", "朗", "明", "晴", "爽", "華", "輝",
              "うれしい", "たのしい", "よろこび", "しあわせ", "わらい", "ハッピー", "やった", "わーい", "いえい", "よっしゃ",
              "最高", "サイコー", "さいこう", "いいね", "よかった", "よし", "ナイス", "グッド", "素晴らしい", "すばらしい", "すごい", "すげー",
              "楽しい", "たのしい", "面白い", "おもしろい", "ワクワク", "わくわく", "ウキウキ", "うきうき", "ルンルン", "るんるん",
              "ありがとう", "感謝", "嬉しい", "うれしい", "幸せ", "しあわせ", "ラッキー", "らっきー", "ついてる", "やったー"],

    "sad": ["悲", "哀", "憂", "愁", "寂", "淋", "泣", "涙", "辛", "苦", "痛", "切", "侘", "寥", "憐", "惨", "凄", "慟", "嘆", "悼",
            "かなしい", "つらい", "さびしい", "せつない", "くるしい", "いたい", "むなしい", "わびしい", "さみしい",
            "悲しい", "辛い", "寂しい", "淋しい", "残念", "ざんねん", "がっかり", "ショック", "しょっく", "ダメ", "だめ",
            "落ち込", "おちこ", "凹", "へこ", "ブルー", "ぶるー", "憂鬱", "ゆううつ", "メランコリー", "めらんこりー",
            "泣き", "なき", "涙", "なみだ", "号泣", "ごうきゅう", "しくしく", "えーん", "うぅ", "ううっ",
            "哀しい", "あわれ", "可哀想", "かわいそう", "不幸", "ふこう", "不運", "ふうん", "ついてない"],

    "angry": ["怒", "憤", "激", "腹", "憎", "恨", "忿", "瞋", "忌", "嫌", "厭", "悪", "癇", "鬱", "苛", "憤", "憮", "慨", "憾", "恚",
              "おこ", "いか", "むか", "はら", "にく", "うら", "きら", "いや", "いらいら", "むかむか", "かっか", "ぷんぷん",
              "怒", "おこ", "腹立", "はらた", "イライラ", "いらいら", "ムカつく", "むかつく", "ムカムカ", "むかむか",
              "許せない", "ゆるせない", "激怒", "げきど", "憤り", "いきどお", "憤慨", "ふんがい", "激昂", "げっこう",
              "うざい", "ウザい", "うっとうしい", "鬱陶しい", "煩わしい", "わずらわしい", "面倒", "めんどう", "めんどくさい",
              "嫌", "いや", "嫌い", "きらい", "憎い", "にくい", "恨", "うら", "ちくしょう", "くそ", "クソ", "畜生", "ちきしょう",
              "カチン", "かちん", "ブチ切れ", "ぶちぎれ", "キレ", "きれ", "プンプン", "ぷんぷん", "カンカン", "かんかん"],

    "surprised": ["驚", "愕", "呆", "唖", "茫", "然", "震", "戦", "慄", "栗", "仰", "天", "絶", "句", "瞠", "目", "眼", "瞼", "瞠", "瞪",
                  "おどろ", "びっくり", "ビックリ", "どっきり", "ドッキリ", "ぎょっ", "ギョッ", "あっ", "アッ", "おっ", "オッ",
                  "驚", "おどろ", "びっくり", "ビックリ", "衝撃", "しょうげき", "ショック", "しょっく",
                  "まさか", "マジ", "まじ", "本当", "ほんとう", "ほんと", "マジで", "まじで", "嘘", "うそ", "ウソ",
                  "えっ", "エッ", "えー", "エー", "はっ", "ハッ", "わっ", "ワッ", "うわっ", "ウワッ", "おおっ", "オオッ",
                  "信じられない", "しんじられない", "ありえない", "あり得ない", "想定外", "そうていがい", "予想外", "よそうがい",
                  "なんと", "ナント", "なんだって", "ナンダッテ", "そんな", "ソンナ", "まじか", "マジカ", "うっそー", "ウッソー"],

    "relaxed": ["安", "穏", "静", "平", "和", "泰", "寧", "閑", "悠", "緩", "鎮", "凪", "癒", "憩", "休", "息", "眠", "夢", "楽", "適",
                "やすらぎ", "おだやか", "しずか", "へいわ", "のんびり", "ゆったり", "まったり", "ほっこり", "ふわふわ",
                "リラックス", "りらっくす", "落ち着", "おちつ", "穏やか", "おだやか", "安心", "あんしん", "平穏", "へいおん",
                "ゆったり", "ユッタリ", "のんびり", "ノンビリ", "まったり", "マッタリ", "ゆるゆる", "ユルユル",
                "平和", "へいわ", "静か", "しずか", "静寂", "せいじゃく", "穏やか", "おだやか", "安らか", "やすらか",
                "癒", "いや", "癒し", "いやし", "ヒーリング", "ひーりんぐ", "リフレッシュ", "りふれっしゅ",
                "ほっ", "ホッ", "ふぅ", "フゥ", "はぁ", "ハァ", "ほー", "ホー", "ふー", "フー"],

    "neutral": ["普", "通", "常", "標", "準", "平", "凡", "並", "通", "例", "定", "型", "基", "本", "原", "初", "元", "素", "無", "空",
                "ふつう", "つうじょう", "へいぼん", "なみ", "いつも", "ひょうじゅん", "きほん", "もと", "もとどおり",
                "通常", "つうじょう", "普通", "ふつう", "ニュートラル", "にゅーとらる", "リセット", "りせっと",
                "標準", "ひょうじゅん", "デフォルト", "でふぉると", "初期", "しょき", "元", "もと", "元に戻", "もとにもど",
                "平常", "へいじょう", "通常通り", "つうじょうどおり", "いつも通り", "いつもどおり", "普段", "ふだん",
                "無表情", "むひょうじょう", "無感情", "むかんじょう", "クール", "くーる", "冷静", "れいせい",
                "戻", "もど", "元通り", "もとどおり", "クリア", "くりあ", "消", "け", "オフ", "おふ"],

    # 口の形(母音)
    "aa": ["あ", "ア", "ああ", "アア", "アー", "あー", "あぁ", "アァ", "ぁ"],
    "ee": ["い", "イ", "いい", "イイ", "イー", "いー", "いぃ", "イィ", "ぃ"],
    "ih": ["い", "イ", "ぃ", "ィ"],
    "oh": ["お", "オ", "おお", "オオ", "オー", "おー", "おぉ", "オォ", "ぉ"],
    "ou": ["う", "ウ", "うう", "ウウ", "ウー", "うー", "うぅ", "ウゥ", "ぅ"],

    # まばたき
    "blink": ["瞬", "瞬き", "まばたき", "マバタキ", "ウィンク", "うぃんく", "ぱちぱち", "パチパチ", "ぱち", "パチ", "瞬", "またた"],
    "blinkLeft": ["左", "左目", "左眼", "左ウィンク", "左まばたき", "レフト", "れふと", "ひだり"],
    "blinkRight": ["右", "右目", "右眼", "右ウィンク", "右まばたき", "ライト", "らいと", "みぎ"],

    # 視線方向
    "lookUp": ["上", "上を見", "見上げ", "上方", "天", "天井", "空", "上向き", "アップ", "あっぷ", "うえ", "うわ"],
    "lookDown": ["下", "下を見", "見下ろ", "下方", "地", "足元", "床", "下向き", "ダウン", "だうん", "した", "しも"],
    "lookLeft": ["左", "左を見", "左方", "左側", "左向き", "レフト", "れふと", "ひだり", "さ"],
    "lookRight": ["右", "右を見", "右方", "右側", "右向き", "ライト", "らいと", "みぎ", "う"]
}


def send_character_expression(expression: str, value: float = 1.0) -> bool:
    """キャラクターの表情を変更"""
    global global_websocket_server

    if global_websocket_server is None:
        # WebSocketサーバーが起動していない場合は何もしない
        return False

    try:
        command_data = {
            "command": "setExpression",
            "expression": expression,
            "value": value
        }
        global_websocket_server.send_message(command_data)
        return True
    except Exception as e:
        print(f"表情送信エラー: {e}")
        return False


def send_character_command(command_data: dict) -> bool:
    """キャラクターに任意のコマンドを送信"""
    global global_websocket_server

    if global_websocket_server is None:
        # WebSocketサーバーが起動していない場合は何もしない
        return False

    try:
        global_websocket_server.send_message(command_data)
        return True
    except Exception as e:
        print(f"コマンド送信エラー: {e}")
        return False


def detect_emotion_from_text(text: str) -> str:
    """テキストから感情を自動検出"""
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return emotion
    return ""


class WebSocketServer:

    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None
        self.server_task = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return

        self.loop = asyncio.new_event_loop()

        def run_server():
            asyncio.set_event_loop(self.loop)
            self.server_task = self.loop.create_task(
                self._run_websocket_server())
            self.loop.run_forever()

        websocket_thread = threading.Thread(target=run_server, daemon=True)
        websocket_thread.start()
        self.is_running = True

    async def _run_websocket_server(self):
        async def handler(websocket):
            self.clients.add(websocket)
            try:
                async for message in websocket:
                    await self._handle_client_message(websocket, message)
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.clients.remove(websocket)

        async with websockets.serve(handler, self.host, self.port):
            await asyncio.Future()

    async def _handle_client_message(self, websocket, message):
        try:
            data = json.loads(message)
            print(f"クライアントからのメッセージ: {data}")
        except json.JSONDecodeError:
            print(f"無効なJSONメッセージ: {message}")

    def send_message(self, message_data):
        if not self.clients:
            return

        message = json.dumps(message_data)

        async def broadcast():
            disconnected_clients = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)

            self.clients.difference_update(disconnected_clients)

        if self.loop:
            asyncio.run_coroutine_threadsafe(broadcast(), self.loop)

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop = None
            self.is_running = False

    def get_client_count(self):
        return len(self.clients)


class HTTPServerWrapper:

    def __init__(self, host="localhost", port=8080, static_dir=None):
        self.host = host
        self.port = port
        self.static_dir = static_dir or os.getcwd()
        self.server = None
        self.thread = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return

        class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, directory=None, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

        handler = lambda *args, **kwargs: CustomHTTPRequestHandler(
            *args, directory=self.static_dir, **kwargs
        )

        self.server = HTTPServer((self.host, self.port), handler)

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )
        self.thread.start()
        self.is_running = True

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server = None
            self.is_running = False


global_websocket_server = None
global_http_server = None


class WebSocketPlugin(BasePlugin):
    name = "CharacterControl"
    description = "WebSocket経由でThree.jsキャラクターを制御"
    version = "v1.0.0"
    sample_commands = [
        "キャラクターを笑顔にして",
        "口パクを開始",
        "表情をリセット"
    ]
    keywords = ["キャラクター", "表情", "口パク", "笑顔", "悲し",
                "怒り", "嬉し", "喜", "リラックス", "笑い", "泣く", "驚く"]
    surpported_expressions = [
        "aa",
        "angry",
        "blink",
        "blinkLeft",
        "blinkRight",
        "ee",
        "happy",
        "ih",
        "lookDown",
        "lookLeft",
        "lookRight",
        "lookUp",
        "neutral",
        "oh",
        "ou",
        "relaxed",
        "sad",
        "surprised"
    ]

    def __init__(self, voice_control=None):
        super().__init__(voice_control)

        self.default_config = {
            "websocket_host": "localhost",
            "websocket_port": 8765,
            "http_host": "localhost",
            "http_port": 8080,
            "static_dir": os.path.dirname(os.path.abspath(__file__))
        }

        user_config = self.get_config()
        self.config = {**self.default_config, **user_config}

        self.websocket_server = None
        self.http_server = None

        if voice_control:
            self.start_servers()

    def start_servers(self):
        global global_websocket_server, global_http_server

        try:

            self.websocket_server = WebSocketServer(
                host=self.config['websocket_host'],
                port=self.config['websocket_port']
            )
            self.http_server = HTTPServerWrapper(
                host=self.config['http_host'],
                port=self.config['http_port'],
                static_dir=self.config['static_dir']
            )

            global_websocket_server = self.websocket_server
            global_http_server = self.http_server

            self.http_server.start()

            self.websocket_server.start()

            self.add_notification(
                f"WebSocketサーバーを起動しました: ws://{self.config['websocket_host']}:{self.config['websocket_port']}",
                "info"
            )
            self.add_notification(
                f"HTTPサーバーを起動しました: http://{self.config['http_host']}:{self.config['http_port']}",
                "info"
            )
            webbrowser.open_new(
                f"http://{global_http_server.host}:{global_http_server.port}/web/index.html")
        except Exception as e:
            self.add_notification(f"サーバーの起動に失敗しました: {e}", "error")

    def stop_servers(self):
        global global_websocket_server, global_http_server

        if self.http_server:
            self.http_server.stop()

        if self.websocket_server:
            self.websocket_server.stop()

        global_websocket_server = None
        global_http_server = None

        self.add_notification("サーバーを停止しました", "info")

    def send_command(self, command_data):
        if self.websocket_server.get_client_count() == 0:
            self.add_notification("接続されているクライアントがありません", "warning")
            return

        self.websocket_server.send_message(command_data)

    def execute(self, command: VoiceCommand) -> VoiceCommand:
        text = command.user_input_text

        if "笑顔" in text or "喜び" in text or "嬉しい" in text:
            self.send_command({
                "command": "setExpression",
                "expression": "happy",
                "value": 1.0
            })
            command.reply_text = "笑顔にしました"

        elif "悲しい" in text or "悲しみ" in text:
            self.send_command({
                "command": "setExpression",
                "expression": "sad",
                "value": 1.0
            })
            command.reply_text = "悲しい表情にしました"

        elif "怒り" in text or "怒る" in text:
            self.send_command({
                "command": "setExpression",
                "expression": "angry",
                "value": 1.0
            })
            command.reply_text = "怒った表情にしました"

        elif "リラックス" in text or "落ち着" in text:
            self.send_command({
                "command": "setExpression",
                "expression": "relaxed",
                "value": 1.0
            })
            command.reply_text = "リラックスした表情にしました"

        elif "驚き" in text or "びっくり" in text:
            self.send_command({
                "command": "setExpression",
                "expression": "surprised",
                "value": 1.0
            })
            command.reply_text = "驚いた表情にしました"

        elif "リセット" in text or "通常" in text or "ニュートラル" in text:
            self.send_command({
                "command": "setExpression",
                "expression": "neutral",
                "value": 1.0
            })
            command.reply_text = "表情をリセットしました"

        elif "口パク" in text and "開始" in text:
            # 口パク開始時には軽い笑顔を設定
            self.send_command({
                "command": "setExpression",
                "expression": "happy",
                "value": 0.5
            })
            self.send_command({"command": "startLipSync"})
            command.reply_text = "口パクを開始しました"

        elif "口パク" in text and "停止" in text:
            self.send_command({"command": "stopLipSync"})

            self.send_command({
                "command": "setExpression",
                "expression": "neutral",
                "value": 1.0
            })
            command.reply_text = "口パクを停止しました"

        return command

    def __del__(self):
        self.stop_servers()
