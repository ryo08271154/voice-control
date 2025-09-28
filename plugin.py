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


class BasePlugin(NotificationManager):
    name: str = ""
    description: str = ""
    version: str = "v1.0.0"
    is_plugin_mode = False
    keywords: list = []
    devices: list = []
    scenes: list = []
    required_config: list = []
    config_dir: str = os.path.join(dir_name, "config")

    def __init__(self, voice_control=None):
        super().__init__()
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

    def command(self, text: str, action_type: str = "plugin_command") -> VoiceCommand:
        command = self.voice_control.command(
            VoiceCommand(text, action_type=action_type))
        return command

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

    def device_control(self, device_name: str, action: str) -> VoiceCommand:
        action_text = action_text = "オン" if action == "turnOn" else "オフ" if action == "turnOff" else ""
        command = self.execute(VoiceCommand(
            f"{device_name} {action_text}", action_type="device_control"))
        return command

    def scene_control(self, scene_name: str) -> VoiceCommand:
        command = self.execute(VoiceCommand(
            f"{scene_name} 実行", action_type="scene_control"))
        return command

    def get_plugin_mode(self) -> bool:
        return self.is_plugin_mode

    def set_plugin_mode(self, mode: bool) -> None:
        self.is_plugin_mode = mode

    def add_notification(self, message: str, message_type="info", timestamp: float = time.time()):
        plugin_name = self.name
        return super().add_notification(plugin_name, message, message_type, timestamp)
