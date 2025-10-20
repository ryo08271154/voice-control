from release_checker import ReleaseChecker
import flet as ft
import datetime
import asyncio
import voice_control
import os
import threading
import time
import pychromecast
import lyricsgenius
import locale
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

locale.setlocale(locale.LC_TIME, "")

# 定数定義


class Constants:
    MAIN_CLOCK_SIZE = 100
    SMALL_CLOCK_SIZE = 20
    TALK_TEXT_SIZE = 50
    REPLY_TEXT_SIZE = 100
    MEDIA_INFO_SIZE = 30
    LYRICS_SIZE = 40
    MENU_TEXT_SIZE = 30
    HELP_TEXT_SIZE = 20

    BACK_DELAY_SECONDS = 60
    CHROMECAST_UPDATE_INTERVAL = 30
    PLAYBACK_UPDATE_INTERVAL = 1
    LYRICS_UPDATE_INTERVAL = 0.8

    MEDIA_ICON_SIZE = 150
    DEVICE_ICON_SIZE = 40
    CONTROL_ICON_SIZE = 100
    BUTTON_ICON_SIZE = 60

    PROGRESS_BAR_WIDTH = 600
    GRID_SPACING = 10
    GRID_RUNS_COUNT = 2
    MENU_GRID_RUNS_COUNT = 3


@dataclass
class MediaState:
    """メディア再生状態を管理するデータクラス"""
    is_playing: bool = False
    current_time: float = 0
    max_time: float = 0
    title: str = ""
    artist: str = ""
    image_url: str = ""


class ChromecastController:
    """Chromecast操作を管理するクラス"""

    def __init__(self):
        self.chromecasts, self.browser = pychromecast.get_chromecasts()
        self.media_state = MediaState()

    def get_active_cast(self) -> Optional[Any]:
        """アクティブなChromecastを取得"""
        for cast in self.chromecasts:
            cast.wait()
            if cast.status.app_id is not None:
                return cast
        return None

    def update_status(self) -> MediaState:
        """Chromecastの状態を更新"""
        try:
            cast = self.get_active_cast()
            if cast:
                mc = cast.media_controller
                mc.block_until_active()

                self.media_state.is_playing = mc.status.player_is_playing
                self.media_state.current_time = mc.status.adjusted_current_time
                self.media_state.max_time = mc.status.duration
                self.media_state.title = mc.status.title
                self.media_state.artist = mc.status.artist
                self.media_state.image_url = mc.status.images[0].url if mc.status.images else ""
            else:
                self.media_state = MediaState()
        except Exception as e:
            print(f"Chromecast状態更新エラー: {e}")
            self.media_state = MediaState()

        return self.media_state

    def control_playback(self, action: str) -> bool:
        """再生コントロール"""
        try:
            cast = self.get_active_cast()
            if not cast:
                return False

            mc = cast.media_controller
            mc.block_until_active()

            actions = {
                "play": lambda: (mc.play(), setattr(self.media_state, 'is_playing', True)),
                "pause": lambda: (mc.pause(), setattr(self.media_state, 'is_playing', False)),
                "stop": lambda: (mc.stop(), setattr(self.media_state, 'is_playing', False)),
                "rewind": lambda: self._seek(mc, -10),
                "forward": lambda: self._seek(mc, 10),
                "previous": lambda: (mc.queue_prev(), time.sleep(1), self.update_status()),
                "next": lambda: (mc.queue_next(), time.sleep(1), self.update_status()),
            }

            if action in actions:
                actions[action]()
                return True
            return False
        except Exception as e:
            print(f"再生コントロールエラー: {e}")
            return False

    def _seek(self, mc, offset: int):
        """シーク処理"""
        self.media_state.current_time += offset
        mc.seek(self.media_state.current_time)


class LyricsManager:
    """歌詞管理クラス"""

    def __init__(self, genius_token: Optional[str] = None):
        self.genius_token = genius_token
        self.current_lyrics: List[str] = []
        self.current_title: str = ""
        self.current_artist: str = ""

    def fetch_lyrics(self, title: str, artist: str) -> List[str]:
        """歌詞を取得"""
        if not title or not artist:
            return ["歌詞を取得できません"]

        if "YouTube" in title or "YouTube" in artist:
            return ["歌詞を取得できません"]

        if not self.genius_token:
            return ["Genius APIトークンが設定されていません"]

        try:
            genius = lyricsgenius.Genius(self.genius_token)
            song = genius.search_song(title, artist)

            if song and song.lyrics:
                self.current_lyrics = song.lyrics.splitlines()
                self.current_title = title
                self.current_artist = artist
                return self.current_lyrics
            else:
                return ["歌詞が見つかりませんでした"]
        except Exception as e:
            print(f"歌詞取得エラー: {e}")
            return ["エラーが発生しました"]


class DeviceMapper:
    """デバイス名とアイコンのマッピング"""

    DEVICE_ICONS = {
        "ライト": ft.Icons.LIGHTBULB,
        "電気": ft.Icons.LIGHTBULB,
        "照明": ft.Icons.LIGHTBULB_OUTLINE,
        "テレビ": ft.Icons.TV,
        "エアコン": ft.Icons.THERMOSTAT,
        "加湿器": ft.Icons.WATER_DROP,
        "除湿器": ft.Icons.DEW_POINT,
        "空気清浄機": ft.Icons.AIR,
        "カーテン": ft.Icons.BLINDS,
        "窓": ft.Icons.WINDOW,
        "給湯器": ft.Icons.WATER,
        "お風呂": ft.Icons.BATHTUB,
        "鍵": ft.Icons.LOCK,
        "防犯": ft.Icons.SECURITY,
        "カメラ": ft.Icons.CAMERA_ALT,
        "スピーカー": ft.Icons.SPEAKER,
        "音楽": ft.Icons.MUSIC_NOTE,
        "プラグ": ft.Icons.POWER,
        "コンセント": ft.Icons.POWER,
    }

    @classmethod
    def get_icon(cls, device_name: str) -> str:
        """デバイス名からアイコンを取得"""
        for keyword, icon in cls.DEVICE_ICONS.items():
            if keyword in device_name:
                return icon
        return ft.Icons.DEVICE_UNKNOWN

    @classmethod
    def get_device_info(cls, reply_text: str) -> Tuple[str, str, List[str], str]:
        """音声返答からデバイス情報を抽出"""
        icon = ft.Icons.DEVICE_UNKNOWN
        color = ""
        device_name = ["不明なデバイス"]
        action = ""

        if "ライト" in reply_text or "電気" in reply_text:
            icon = ft.Icons.LIGHTBULB
            device_name = ["ライト"]
        elif "テレビ" in reply_text:
            icon = ft.Icons.TV
            device_name = ["テレビ"]
        elif "エアコン" in reply_text:
            icon = ft.Icons.THERMOSTAT
            device_name = ["エアコン"]

        if "オン" in reply_text:
            color = ft.Colors.BLUE
            action = "turnOff"
        elif "オフ" in reply_text:
            color = ft.Colors.RED
            action = "turnOn"

        return icon, color, device_name, action


class VoiceControlUI:
    """音声コントロールUI管理クラス"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.voice: Optional[Any] = None
        self.voice_thread: Optional[threading.Thread] = None
        self.chromecast_controller = ChromecastController()
        self.lyrics_manager: Optional[LyricsManager] = None
        self.custom_view: Optional[ft.Control] = None
        self.last_activity_time = time.time()  # 追加: 最終操作時刻

        # UI要素
        self.current_datetime_text = self._create_datetime_text()
        self.current_time_text = self._create_time_text()
        self.talk_text = ft.Text("", size=Constants.TALK_TEXT_SIZE)
        self.reply_text = ft.Text("", size=Constants.REPLY_TEXT_SIZE,
                                  text_align=ft.TextAlign.CENTER, expand=True)
        self.media_icon = ft.Image(width=Constants.MEDIA_ICON_SIZE,
                                   height=Constants.MEDIA_ICON_SIZE,
                                   fit=ft.ImageFit.CONTAIN)
        self.media_info_text = ft.Text(size=Constants.MEDIA_INFO_SIZE,
                                       text_align=ft.TextAlign.CENTER,
                                       bgcolor=ft.Colors.BLACK)
        self.lyrics_list = ft.ListView(auto_scroll=True)
        self.playback_progress = ft.ProgressBar(
            width=Constants.PROGRESS_BAR_WIDTH, value=0)

    def _create_datetime_text(self) -> ft.Text:
        """日時表示テキストを作成"""
        return ft.Text(
            datetime.datetime.now().strftime("%Y/%m/%d(%a)\n%H:%M:%S"),
            size=Constants.MAIN_CLOCK_SIZE,
            text_align=ft.TextAlign.CENTER
        )

    def _create_time_text(self) -> ft.Text:
        """時刻表示テキストを作成"""
        return ft.Text(
            datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S"),
            size=Constants.SMALL_CLOCK_SIZE,
            text_align=ft.TextAlign.CENTER
        )

    def setup_voice_control(self):
        """音声コントロールのセットアップ"""
        try:
            import json
            dir_name = os.path.dirname(__file__)

            config_files = {
                "custom_scenes": "custom_scenes.json",
                "custom_devices": "custom_devices.json",
                "custom_routines": "custom_routines.json",
                "config": "config.json"
            }

            configs = {}
            for key, filename in config_files.items():
                path = os.path.join(dir_name, "config", filename)
                with open(path, 'r') as f:
                    configs[key] = json.load(f)

            control = voice_control.Control(
                configs["custom_devices"],
                configs["custom_scenes"]
            )

            self.voice = self.VoiceControlExtended(
                control.custom_devices,
                configs["custom_routines"],
                control,
                configs["config"],
                self
            )

            # 歌詞マネージャーの初期化
            genius_token = configs["config"].get("genius", {}).get("token")
            self.lyrics_manager = LyricsManager(genius_token)

            # リスニングスレッドの起動
            if not self.voice_thread:
                self.voice_thread = threading.Thread(
                    target=self._listen,
                    args=(configs["config"],),
                    daemon=True
                )
                self.voice_thread.start()

        except Exception as e:
            print(f"音声認識の初期化中にエラーが発生しました: {e}")

    def _listen(self, config: Dict[str, Any]):
        """音声認識リスニング"""
        if config.get("vosk"):
            self.voice.listen_vosk(config["vosk"]["model_path"])
        elif config.get("whisper"):
            whisper_config = config["whisper"]
            self.voice.listen_whisper(
                whisper_config["model_size_or_path"],
                whisper_config["device"],
                whisper_config["compute_type"],
                whisper_config["language"]
            )

    class VoiceControlExtended(voice_control.VoiceControl):
        """拡張された音声コントロールクラス"""

        def __init__(self, custom_devices, custom_routines, control, config, ui):
            super().__init__(custom_devices, custom_routines, control, config)
            self.ui = ui

        def yomiage(self, commands):
            if self.ui.page.route == "/voice":
                self.ui.page.go("/")
                time.sleep(0.5)
            self.ui.handle_voice_result(commands[0])
            super().yomiage(commands)
            self.ui.page.run_task(self.ui.schedule_back)

    def handle_voice_result(self, result):
        """音声認識結果の処理"""
        self.talk_text.value = result.user_input_text
        self.reply_text.value = result.reply_text
        self.voice.reply = result.reply_text
        self.custom_view = result.flet_view

        # ルーティング判定
        if "をオン" in result.reply_text or "をオフ" in result.reply_text:
            self.page.go("/device_control")
        elif result.action_type == "notification":
            self.page.go("/notifications")
        else:
            self.page.go("/voice")

    def update_last_activity(self):
        """ユーザーの最終操作時刻を更新"""
        self.last_activity_time = time.time()

    async def schedule_back(self, seconds: int = Constants.BACK_DELAY_SECONDS):
        """無操作時にホーム画面に戻る"""
        try:
            while True:
                await asyncio.sleep(1)
                elapsed_time = time.time() - self.last_activity_time

                if elapsed_time >= seconds:
                    if self.page.route in ["/voice", "/notifications", "/device_control"]:
                        if self.chromecast_controller.media_state.current_time > 0:
                            self.page.go("/media")
                        else:
                            self.page.go("/")
                    self.update_last_activity()  # タイマーをリセット
        except asyncio.CancelledError:
            pass

    async def update_time(self):
        """時刻表示の更新"""
        while True:
            now = datetime.datetime.now()
            self.current_datetime_text.value = now.strftime(
                "%Y/%m/%d(%a)\n%H:%M:%S")
            self.current_time_text.value = now.strftime("%H:%M:%S")

            if self.page.route in ["/", "/menu", "/voice"]:
                self.page.update()

            await asyncio.sleep(1)

    async def update_chromecast_status(self):
        """Chromecast状態の更新"""
        while True:
            media_state = self.chromecast_controller.update_status()

            # UI更新
            self.media_icon.src = media_state.image_url
            self.media_info_text.value = f"{media_state.title} - {media_state.artist}"

            if self.page.route == "/media":
                self.page.update()
            elif self.page.route == "/" and media_state.current_time == 0:
                self.page.update()

            await asyncio.sleep(Constants.CHROMECAST_UPDATE_INTERVAL)

    async def update_playback_progress(self):
        """再生進捗の更新"""
        while True:
            media_state = self.chromecast_controller.media_state

            if media_state.is_playing:
                media_state.current_time += 1

            if media_state.current_time and media_state.max_time:
                if media_state.current_time > media_state.max_time:
                    media_state.current_time = 0
                    self.chromecast_controller.update_status()

                progress = media_state.current_time / media_state.max_time
                self.playback_progress.value = progress

                if self.page.route == "/media":
                    self.page.update()

            await asyncio.sleep(Constants.PLAYBACK_UPDATE_INTERVAL)

    async def update_lyrics(self):
        """歌詞表示の更新"""
        if not self.lyrics_manager:
            return

        lyrics = []
        current_title = ""
        interval = 0.1
        line = 0

        while True:
            media_state = self.chromecast_controller.media_state

            # 曲が変わったら歌詞を再取得
            if current_title != media_state.title:
                self.lyrics_list.controls.clear()
                lyrics = self.lyrics_manager.fetch_lyrics(
                    media_state.title,
                    media_state.artist
                )
                current_title = media_state.title
                line = 0

                if len(lyrics) > 1 and media_state.max_time:
                    interval = media_state.max_time / len(lyrics) - 0.5
                else:
                    interval = 0.1

            # 歌詞の表示/非表示を制御
            if lyrics and interval > 0:
                target_line = int(media_state.current_time // interval)

                # 新しい行を追加
                while len(self.lyrics_list.controls) < target_line and line < len(lyrics):
                    lyrics_text = ft.Text(
                        lyrics[line],
                        size=Constants.LYRICS_SIZE,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.WHITE54
                    )
                    self.lyrics_list.controls.append(lyrics_text)
                    line += 1

                # 不要な行を削除
                while len(self.lyrics_list.controls) > target_line:
                    line -= 1
                    self.lyrics_list.controls.pop(-1)

            if self.page.route == "/media":
                self.page.update()

            await asyncio.sleep(Constants.LYRICS_UPDATE_INTERVAL)

    def create_device_grid(self) -> ft.GridView:
        """デバイス一覧グリッドを作成"""
        devices = []

        # カスタムデバイスを追加
        for device_name in self.voice.custom_devices_name:
            devices.append({
                "name": device_name,
                "icon": ft.Icons.DEVICES
            })

        # プラグインデバイスを追加
        for plugin in self.voice.plugins:
            for device in plugin.devices:
                devices.append({
                    "name": device.device_name,
                    "icon": DeviceMapper.get_icon(device.device_name)
                })

            # プラグインシーンを追加
            for scene in plugin.scenes:
                devices.append({
                    "name": scene,
                    "icon": ft.Icons.DEVICES_OTHER
                })

        grid = ft.GridView(
            expand=True,
            runs_count=Constants.GRID_RUNS_COUNT,
            max_extent=200,
            child_aspect_ratio=1.2,
            spacing=Constants.GRID_SPACING,
            run_spacing=Constants.GRID_SPACING
        )

        for device in devices:
            card = self._create_device_card(device)
            grid.controls.append(card)

        return grid

    def _create_device_card(self, device: Dict[str, Any]) -> ft.Card:
        """デバイスカードを作成"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(device["icon"],
                                size=Constants.DEVICE_ICON_SIZE),
                        ft.Text(
                            device["name"],
                            size=16,
                            text_align=ft.TextAlign.CENTER,
                            width=180,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "ON",
                                    width=70,
                                    on_click=lambda _, d=device: self.execute_command(
                                        f"{d['name']}をオン"
                                    )
                                ),
                                ft.ElevatedButton(
                                    "OFF",
                                    width=70,
                                    on_click=lambda _, d=device: self.execute_command(
                                        f"{d['name']}をオフ"
                                    )
                                )
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                padding=15
            )
        )

    def create_menu_grid(self) -> ft.GridView:
        """メニューグリッドを作成"""
        menu_items = [
            ("デバイス一覧", lambda: self.page.go("/devices"),
             ft.Icons.DEVICES_OTHER_OUTLINED),
            ("メディア操作", lambda: self.page.go("/media"),
             ft.Icons.PLAY_CIRCLE_OUTLINE),
            ("タイマー", lambda: self.page.go("/set_timer"),
             ft.Icons.TIMER),
            ("天気", lambda: self.execute_command("今日の天気"),
             ft.Icons.CLOUD_OUTLINED),
            ("ニュース", lambda: self.execute_command("ニュース"),
             ft.Icons.FEED_OUTLINED),
            ("予定", lambda: self.execute_command("今日の予定"),
             ft.Icons.CALENDAR_TODAY_OUTLINED),
            ("通知", lambda: self.page.go("/notifications"),
             ft.Icons.NOTIFICATIONS_OUTLINED),
            ("ヘルプ", lambda: self.page.go("/help"),
             ft.Icons.HELP_OUTLINE),
            ("設定", lambda: self.page.go("/settings"),
             ft.Icons.SETTINGS_OUTLINED),
        ]

        grid = ft.GridView(
            expand=True,
            runs_count=Constants.MENU_GRID_RUNS_COUNT,
            max_extent=180,
            child_aspect_ratio=1.1,
            spacing=Constants.GRID_SPACING,
            run_spacing=Constants.GRID_SPACING,
            controls=[]
        )

        for text, cmd, icon in menu_items:
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(icon, size=Constants.DEVICE_ICON_SIZE),
                            ft.Text(text, size=16,
                                    text_align=ft.TextAlign.CENTER)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    on_click=lambda _, c=cmd: c(),
                    padding=15,
                    border_radius=ft.border_radius.all(10)
                )
            )
            grid.controls.append(card)

        return grid

    def create_routine_list(self) -> ft.GridView:
        """カスタムルーチン一覧を作成"""
        routines = [
            routine["routineName"]
            for routine in self.voice.custom_routines["routineList"]
        ]

        grid = ft.GridView(
            runs_count=1,
            max_extent=150,
            child_aspect_ratio=1.0,
            spacing=1,
            run_spacing=1,
            controls=[]
        )

        for routine in routines:
            button = ft.ElevatedButton(
                routine,
                on_click=lambda _, cmd=routine: self.execute_command(cmd)
            )
            grid.controls.append(button)

        return grid

    def create_notifications_panel(self) -> ft.Control:
        """通知パネルを作成"""
        if len(self.voice.notifications) == 0:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_OFF, size=100),
                        ft.Text(
                            "新しい通知はありません",
                            size=30,
                            text_align=ft.TextAlign.CENTER
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                alignment=ft.alignment.center,
                expand=True
            )

        lv = ft.ListView(spacing=10, padding=20, expand=True)
        for notification in self.voice.notifications:
            lv.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"{notification.plugin_name} - {notification.message}"
                    ),
                    bgcolor=ft.Colors.WHITE10,
                    padding=10,
                    border_radius=5
                )
            )

        return lv

    def execute_command(self, text: str):
        """コマンドを実行"""
        print(f"コマンド実行: {text}")
        self.voice.text = text
        self.voice.command(text)

    def toggle_fullscreen(self, e):
        """フルスクリーン切り替え"""
        self.page.window.full_screen = e.control.value
        self.page.window.skip_task_bar = True
        self.page.update()


class ViewBuilder:
    """ビュー構築を担当するクラス"""

    def __init__(self, page: ft.Page, ui: VoiceControlUI):
        self.page = page
        self.ui = ui

    def create_input_field(self) -> ft.Container:
        """入力フィールドとボタンを作成"""
        input_field = ft.TextField(
            label="音声コマンドを入力",
            on_submit=lambda e: self.ui.execute_command(input_field.value),
            expand=True,
            text_align=ft.TextAlign.CENTER,
            text_size=20
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    input_field,
                    ft.IconButton(
                        icon=ft.Icons.SEND,
                        on_click=lambda e: self.ui.execute_command(
                            input_field.value)
                    )
                ]
            )
        )

    def create_home_button(self) -> ft.ElevatedButton:
        """ホームボタンを作成"""
        return ft.ElevatedButton(
            "ホーム",
            on_click=lambda e: self.page.go("/")
        )

    def build_home_view(self) -> ft.View:
        """ホーム画面ビューを構築"""
        self.ui.reply_text.value = ""
        return ft.View(
            "/",
            [
                ft.Container(
                    content=self.ui.current_datetime_text,
                    expand=True,
                    alignment=ft.alignment.center,
                    on_click=lambda e: self.page.go("/menu")
                )
            ]
        )

    def build_voice_view(self, home_button: ft.Control, text_container: ft.Container) -> ft.View:
        """音声コントロール画面ビューを構築"""
        view = self.ui.custom_view if self.ui.custom_view else ft.Column(
            controls=[
                ft.Container(
                    content=self.ui.current_time_text,
                    expand=True,
                    alignment=ft.alignment.center
                ),
                ft.Container(
                    content=self.ui.talk_text,
                    expand=True,
                    alignment=ft.alignment.center
                ),
                ft.Container(
                    content=self.ui.reply_text,
                    expand=True,
                    alignment=ft.alignment.center
                ),
            ],
            scroll=ft.ScrollMode.HIDDEN,
            expand=True
        )
        return ft.View("/voice", [home_button, view, text_container])

    def build_menu_view(self, home_button: ft.Control, text_container: ft.Container) -> ft.View:
        """メニュー画面ビューを構築"""
        return ft.View(
            "/menu",
            [
                home_button,
                ft.Container(
                    content=self.ui.current_time_text,
                    expand=True,
                    alignment=ft.alignment.center
                ),
                ft.Text("メニュー", size=30, weight=ft.FontWeight.BOLD),
                self.ui.create_menu_grid(),
                text_container,
                ft.Text("カスタムルーチン", size=24, weight=ft.FontWeight.BOLD),
                self.ui.create_routine_list(),
            ],
            scroll=ft.ScrollMode.AUTO,
            padding=20
        )

    def build_device_control_view(self, home_button: ft.Control) -> ft.View:
        """デバイス操作画面ビューを構築"""
        icon, color, device_name, action = DeviceMapper.get_device_info(
            self.ui.voice.reply
        )

        def control_device(_):
            self.page.go("/")
            action_text = f"{device_name[0]}オン" if action == "turnOn" else f"{device_name[0]}オフ"
            self.ui.voice.command(action_text)

        return ft.View(
            "/device_control",
            [
                home_button,
                ft.Container(
                    content=ft.IconButton(
                        icon,
                        icon_size=Constants.CONTROL_ICON_SIZE,
                        on_click=control_device,
                        icon_color=color
                    ),
                    expand=True,
                    alignment=ft.alignment.center
                ),
            ]
        )

    def build_devices_view(self, home_button: ft.Control) -> ft.View:
        """デバイス一覧画面ビューを構築"""
        return ft.View(
            "/devices",
            [
                home_button,
                ft.Text("デバイス一覧", size=30, weight=ft.FontWeight.BOLD),
                self.ui.create_device_grid()
            ]
        )

    def build_help_view(self, home_button: ft.Control) -> ft.View:
        """ヘルプ画面ビューを構築"""
        return ft.View(
            "/help",
            [
                home_button,
                ft.Text("使い方", size=30, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "1. 画面をタップしてメニューを開く\n"
                    "2. 音声コマンドを話すか、メニューから選択\n"
                    "3. 「ライトをオン」などの機器操作\n"
                    "4. 「今日の天気は」などの質問\n"
                    "5. 「〇〇について教えて」などの会話",
                    size=20
                ),
                ft.Text("コマンド例", size=30, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "・機器操作: ライト/テレビ/エアコン + オン/オフ\n"
                    "・情報取得: 天気、時刻、ニュース\n"
                    "・会話: プログラミング、技術、スポーツなど",
                    size=20
                ),
            ]
        )

    def build_settings_view(self, home_button: ft.Control) -> ft.View:
        """設定画面ビューを構築"""
        return ft.View(
            "/settings",
            [
                home_button,
                ft.Text("設定", size=30, weight=ft.FontWeight.BOLD),
                ft.Switch(
                    label="フルスクリーンモード",
                    value=self.page.window.full_screen,
                    on_change=self.ui.toggle_fullscreen
                ),
                ft.Switch(
                    label="ミュート",
                    value=self.ui.voice.mute,
                    on_change=lambda e: setattr(
                        self.ui.voice, 'mute', e.control.value)
                ),
            ]
        )

    def build_media_view(self, home_button: ft.Control) -> ft.View:
        """メディア操作画面ビューを構築"""
        return ft.View(
            "/media",
            [
                home_button,
                ft.Stack(
                    controls=[
                        # 上部固定コンテンツ
                        ft.Container(
                            content=ft.Column(
                                [
                                    self.ui.current_time_text,
                                    self.ui.media_icon,
                                    self.ui.media_info_text,
                                    ft.Container(height=120),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=5,
                            ),
                            alignment=ft.alignment.top_center,
                            padding=ft.padding.only(top=20),
                        ),
                        # スクロール可能なメインコンテンツ
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Container(height=230),
                                    ft.Container(
                                        content=self.ui.lyrics_list,
                                        expand=True,
                                        alignment=ft.alignment.center,
                                    ),
                                    ft.Container(
                                        content=self.ui.playback_progress,
                                        padding=ft.padding.symmetric(
                                            vertical=10)
                                    ),
                                    ft.Container(
                                        content=self._create_media_controls(),
                                        alignment=ft.alignment.bottom_center,
                                        padding=ft.padding.only(bottom=20)
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.START,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                expand=True
                            ),
                            expand=True,
                            padding=ft.padding.symmetric(horizontal=20)
                        )
                    ],
                    expand=True
                )
            ],
            scroll=None
        )

    def build_notifications_view(self, home_button: ft.Control) -> ft.View:
        """通知画面ビューを構築"""
        return ft.View(
            "/notifications",
            [
                home_button,
                ft.Text("通知", size=30, weight=ft.FontWeight.BOLD),
                self.ui.create_notifications_panel()
            ]
        )

    def _create_media_controls(self) -> ft.Row:
        """メディアコントロールボタンを作成"""
        controls = [
            ("play", ft.Icons.PLAY_ARROW),
            ("pause", ft.Icons.PAUSE),
            ("stop", ft.Icons.STOP),
            ("rewind", ft.Icons.FAST_REWIND),
            ("forward", ft.Icons.FAST_FORWARD),
            ("previous", ft.Icons.SKIP_PREVIOUS),
            ("next", ft.Icons.SKIP_NEXT),
        ]

        buttons = [
            ft.IconButton(
                icon=icon,
                icon_size=Constants.BUTTON_ICON_SIZE,
                on_click=lambda _, a=action: self.ui.chromecast_controller.control_playback(
                    a)
            )
            for action, icon in controls
        ]

        return ft.Row(
            buttons,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=30
        )

    def build_set_timer_view(self, home_button: ft.Control) -> ft.View:
        """タイマー設定画面ビューを構築"""
        grid = ft.GridView(
            runs_count=1,
            max_extent=150,
            child_aspect_ratio=1.0,
            spacing=1,
            run_spacing=1,
            controls=[]
        )
        for i in [1, 3, 5, 10, 15, 30, 45, 60]:  # 15分刻みで60分まで
            button = ft.ElevatedButton(
                f"{i}分タイマー",
                on_click=lambda _, cmd=f"{i}分タイマー": self.ui.execute_command(
                    cmd)
            )
            grid.controls.append(button)
        return ft.View(
            "/set_timer",
            [
                home_button,
                ft.Text("タイマー設定", size=30, weight=ft.FontWeight.BOLD),
                grid
            ]
        )


class RouteHandler:
    """ルーティング処理を管理するクラス"""

    def __init__(self, page: ft.Page, ui: VoiceControlUI):
        self.page = page
        self.ui = ui
        self.view_builder = ViewBuilder(page, ui)

        # ルートとビルダーメソッドのマッピング
        self.route_map = {
            "/": self._handle_home,
            "/voice": self._handle_voice,
            "/menu": self._handle_menu,
            "/device_control": self._handle_device_control,
            "/devices": self._handle_devices,
            "/help": self._handle_help,
            "/settings": self._handle_settings,
            "/media": self._handle_media,
            "/notifications": self._handle_notifications,
            "/set_timer": self._handle_set_timer,
        }

        # イベントハンドラの登録
        self.page.on_route_change = self.handle_route_change
        self.page.on_click = self._handle_page_interaction

    def _handle_page_interaction(self, e):
        """ページ操作時のイベントハンドラ"""
        self.ui.update_last_activity()
        if self.page.route == "/":
            self.page.go("/menu")

    def handle_route_change(self, e):
        """ルート変更を処理"""
        self.ui.update_last_activity()  # ルート変更時にアクティビティを更新
        self.page.views.clear()

        # 現在のルートに対応するハンドラを実行
        handler = self.route_map.get(self.page.route)
        if handler:
            handler()

        self.page.update()

    def _handle_home(self):
        """ホーム画面を表示"""
        view = self.view_builder.build_home_view()
        self.page.views.append(view)

    def _handle_voice(self):
        """音声コントロール画面を表示"""
        home_button = self.view_builder.create_home_button()
        text_container = self.view_builder.create_input_field()
        view = self.view_builder.build_voice_view(home_button, text_container)
        self.page.views.append(view)

    def _handle_menu(self):
        """メニュー画面を表示"""
        home_button = self.view_builder.create_home_button()
        text_container = self.view_builder.create_input_field()
        view = self.view_builder.build_menu_view(home_button, text_container)
        self.page.views.append(view)

    def _handle_device_control(self):
        """デバイス操作画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_device_control_view(home_button)
        self.page.views.append(view)

    def _handle_devices(self):
        """デバイス一覧画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_devices_view(home_button)
        self.page.views.append(view)

    def _handle_help(self):
        """ヘルプ画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_help_view(home_button)
        self.page.views.append(view)

    def _handle_settings(self):
        """設定画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_settings_view(home_button)
        self.page.views.append(view)

    def _handle_media(self):
        """メディア操作画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_media_view(home_button)
        self.page.views.append(view)

    def _handle_notifications(self):
        """通知画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_notifications_view(home_button)
        self.page.views.append(view)

    def _handle_set_timer(self):
        """タイマー設定画面を表示"""
        home_button = self.view_builder.create_home_button()
        view = self.view_builder.build_set_timer_view(home_button)
        self.page.views.append(view)


# main関数内での使用例
def main(page: ft.Page):
    """メインアプリケーション"""
    page.theme_mode = ft.ThemeMode.DARK
    page.title = "音声操作"

    # UIコントローラーの初期化
    ui = VoiceControlUI(page)
    ui.setup_voice_control()

    # 音声コントロールの初期化を待つ
    while not ui.voice:
        time.sleep(1)

    # ルートハンドラーを作成
    route_handler = RouteHandler(page, ui)

    # イベントハンドラの登録（リファクタリング後）
    page.on_route_change = route_handler.handle_route_change
    page.on_click = route_handler._handle_page_interaction

    # バックグラウンドタスクの開始
    page.run_task(ui.update_time)
    page.run_task(ui.update_chromecast_status)
    page.run_task(ui.update_playback_progress)
    page.run_task(ui.update_lyrics)

    # 初期ルートに移動
    page.go(page.route)


if __name__ == "__main__":
    # アップデートチェック
    checker = ReleaseChecker()
    if checker.check_update():
        checker.gui()

    # アプリケーション起動
    ft.app(target=main)
