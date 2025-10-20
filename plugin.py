from google import genai
import importlib
import inspect
import os
import json
import asyncio
from commands import VoiceCommand
import time
dir_name = os.path.dirname(os.path.abspath(__file__))


class PluginManager:
    def __init__(self, voice_control=None, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []
        self.voice_control = voice_control

    def get_plugins(self):
        plugins = []
        for filename in os.listdir(os.path.join(dir_name, self.plugin_dir)):
            try:
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = f"plugins.{filename[:-3]}"
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BasePlugin) and obj != BasePlugin:
                            plugins.append(obj())
            except OSError as e:
                print(f"プラグインファイルの読み込み中にエラーが発生しました: {e}")
            except Exception as e:
                print(f"プラグインの読み込みにエラーが発生しました: {e}")
        return plugins

    def load_plugins(self):
        plugins = []
        enabled_plugins = json.load(
            open(os.path.join(dir_name, "config/config.json"))).get("plugins", {})
        for filename in os.listdir(os.path.join(dir_name, self.plugin_dir)):
            try:
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = f"plugins.{filename[:-3]}"
                    module = importlib.import_module(module_name)
                    for name, cls in inspect.getmembers(module, inspect.isclass):
                        if issubclass(cls, BasePlugin) and cls != BasePlugin:
                            obj = cls(self.voice_control)
                            if obj.name in enabled_plugins:
                                plugins.append(obj)
            except OSError as e:
                print(f"プラグインファイルの読み込み中にエラーが発生しました: {e}")
            except Exception as e:
                print(f"プラグインの読み込みにエラーが発生しました: {e}")
        self.plugins = plugins
        return plugins


class Notification:
    def __init__(self, plugin_name: str, message: str, message_type: str = "info", timestamp: float = time.time()):
        self.plugin_name = plugin_name
        self.message = message
        self.message_type = message_type
        self.timestamp = timestamp


class NotificationManager:
    def __init__(self):
        self.notifications = []

    def add_notification(self, plugin_name: str, message: str, message_type: str = "info", timestamp: float = time.time()) -> None:
        self.notifications.append(Notification(
            plugin_name, message, message_type, timestamp))

    def get_active_notifications(self) -> list:
        active_notifications = []
        for notification in self.notifications:
            if notification.timestamp <= time.time():
                active_notifications.append(notification)
        return active_notifications

    def get_all_notifications(self) -> list:
        return self.notifications

    def clear_notifications(self) -> None:
        active_notifications = self.get_active_notifications()
        for notification in active_notifications:
            self.notifications.remove(notification)

    def notify(self, plugin_name: str, message: str, message_type: str = "info") -> None:
        print(f"{plugin_name}:{message}")
        self.notifications.append(Notification(
            plugin_name, message, message_type))


class Device:
    def __init__(self, device_name: str, device_type: str = "unknown", room: str = "unknown", on_func=None, off_func=None, play_func=None, pause_func=None, stop_func=None, next_func=None, previous_func=None, up_func=None, down_func=None, set_count_func=None, set_speed_func=None, set_mode_func=None):
        self.device_name = device_name
        self.device_type = device_type
        self.status = {"power_state": False, "count": 0, "speed": 0, "mode": 0}
        self.room = room
        self._callbacks = {
            'on': on_func,
            'off': off_func,
            'play': play_func,
            'pause': pause_func,
            'stop': stop_func,
            'next': next_func,
            'previous': previous_func,
            'up': up_func,
            'down': down_func,
            'set_count': set_count_func,
            'set_speed': set_speed_func,
            'set_mode': set_mode_func
        }

    def _execute_callback(self, action: str, *args, **kwargs):
        func = self._callbacks.get(action)
        if func:
            return func(self, *args, **kwargs)
        else:
            return False

    def turn_on(self):
        self.status["power_state"] = True
        return self._execute_callback("on")

    def turn_off(self):
        self.status["power_state"] = False
        return self._execute_callback("off")

    def play(self):
        return self._execute_callback("play")

    def pause(self):
        return self._execute_callback("pause")

    def stop(self):
        return self._execute_callback("stop")

    def next(self):
        return self._execute_callback("next")

    def previous(self):
        return self._execute_callback("previous")

    def up(self, amount: int = 1):
        self.status["count"] += amount
        return self._execute_callback("up", amount)

    def down(self, amount: int = 1):
        self.status["count"] -= amount
        return self._execute_callback("down", amount)

    def set_count(self, count: int):
        self.status["count"] = count
        return self._execute_callback("set_count", count)

    def set_speed(self, speed: int):
        self.status["speed"] = speed
        return self._execute_callback("set_speed", speed)

    def set_mode(self, mode: int):
        self.status["mode"] = mode
        return self._execute_callback("set_mode", mode)

    def get_status(self) -> dict:
        return self.status

    def set_status(self, key: str, value: any):
        self.status[key] = value
        return self.status

    def __str__(self):
        return self.device_name

    def __repr__(self):
        return self.device_name


class Scene:
    def __init__(self, scene_name: str, room: str = "unknown", execute_func=None):
        self.scene_name = scene_name
        self.room = room
        self._execute_func = execute_func

    def execute(self):
        if self._execute_func:
            return self._execute_func(self)
        else:
            return False

    def __str__(self):
        return self.scene_name

    def __repr__(self):
        return self.scene_name


class BasePlugin(NotificationManager):
    name: str = ""
    description: str = ""
    version: str = "v1.0.0"
    sample_commands: list = []
    keywords: list = []
    required_config: list = []
    config_dir: str = os.path.join(dir_name, "config")

    def __init__(self, voice_control=None):
        super().__init__()
        self.is_plugin_mode = False
        self.devices: list = []
        self.scenes: list = []
        self.voice_control = voice_control
        if not self.voice_control:
            return
        self.genai_client = genai.Client(
            api_key=self.voice_control.config["genai"]["apikey"])

    def get_keywords(self) -> list:
        return self.keywords

    def get_config(self) -> dict:
        return json.load(open(os.path.join(dir_name, "config/config.json"))).get("plugins_config", {}).get(self.name, {})

    def can_handle(self, text: str) -> bool:
        return any(keyword in text for keyword in self.keywords)

    def execute(self, command: VoiceCommand) -> VoiceCommand:
        return command

    def command(self, text: str) -> list:
        plugin_mode = self.get_plugin_mode()
        if self.is_plugin_mode:
            self.set_plugin_mode(False)
        commands = self.voice_control.command(text)
        if plugin_mode:
            self.set_plugin_mode(True)
        return commands

    def ask_gemini(self, contents: str, config: genai.types.GenerateContentConfig = genai.types.GenerateContentConfig(), *args, **kwargs) -> genai.types.GenerateContentResponse:
        async def generate_content(contents: str, config: genai.types.GenerateContentConfig, *args, **kwargs) -> genai.types.GenerateContentResponse:
            # ユーザーのシステム命令を設定
            if config.system_instruction is None:
                config.system_instruction = ""
            user_system_instruction = self.voice_control.config["genai"]["system_instruction"]
            config.system_instruction += user_system_instruction
            response = await self.genai_client.aio.models.generate_content(
                model=self.voice_control.config["genai"]["model_name"],
                contents=contents,
                config=config,
                *args,
                **kwargs
            )
            return response
        response = asyncio.run(generate_content(
            contents, config, *args, **kwargs))
        return response

    def get_plugin_mode(self) -> bool:
        return self.is_plugin_mode

    def set_plugin_mode(self, mode: bool) -> None:
        self.is_plugin_mode = mode

    def add_notification(self, message: str, message_type="info", timestamp: float = time.time()):
        plugin_name = self.name
        return super().add_notification(plugin_name, message, message_type, timestamp)

    def add_device(self, device_name: str, device_type: str = "unknown", room: str = "unknown", on_func=None, off_func=None, play_func=None, pause_func=None, stop_func=None, next_func=None, previous_func=None, up_func=None, down_func=None, set_count_func=None, set_speed_func=None, set_mode_func=None) -> None:
        self.devices.append(Device(device_name, device_type, room, on_func, off_func,
                            play_func, pause_func, stop_func, next_func, previous_func, up_func, down_func, set_count_func, set_speed_func, set_mode_func))

    def add_scene(self, scene_name: str, room: str = "unknown", excute_func=None) -> None:
        self.scenes.append(Scene(scene_name, room, excute_func))
