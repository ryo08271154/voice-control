import os
import asyncio
import vosk
import pyaudio
import json
import subprocess
import threading
import requests
import datetime
import time
import unicodedata
import numpy as np
from google import genai
import re
import webrtcvad
import fastmcp
from faster_whisper import WhisperModel
from plugin import PluginManager
from commands import VoiceCommand
dir_name = os.path.dirname(__file__)


class VoiceRecognizer:
    mute = False

    def __init__(self):
        self.sample_rate = 16000
        self.p = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(2)
        self.frame_duration = 30  # ms
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        self.frame_bytes = self.frame_size * 2  # 16-bit audio
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=self.sample_rate,  # 16kHz に変更
                                  input=True,
                                  frames_per_buffer=self.frame_size)  # バッファサイズを適切に設定
        self.end_of_speech = True
        self.speech_end_time = time.time()

    def listen_vosk(self, model_path):
        model = vosk.Model(model_path)
        recognizer = vosk.KaldiRecognizer(model, self.sample_rate)
        recognizer.SetPartialWords(False)
        while True:
            try:
                data = self.stream.read(
                    self.frame_size, exception_on_overflow=False)
                if len(data) != self.frame_bytes:
                    continue  # フレーム長が正しくない場合スキップ
                is_speech = self.vad.is_speech(data, self.sample_rate)
                if is_speech:
                    self.end_of_speech = False
                    print("聞き取り中", end="\r")
                    self.speech_end_time = time.time() + 3  # 3秒無音で終了とみなす
                elif not is_speech and time.time() > self.speech_end_time:
                    self.end_of_speech = True
                    print("音声待機中", end="\r")
                if self.end_of_speech == False and self.mute == False:
                    if recognizer.AcceptWaveform(data):
                        self.text = json.loads(recognizer.Result())["text"]
                        if self.text != "":
                            print("ユーザー:", self.text)
                            self.end_of_speech = True
                            threading.Thread(
                                target=self.command, args=(self.text,)).start()
            except KeyboardInterrupt:
                break

    def listen_whisper(self, model_size_or_path, device, compute_type, language):
        frames = []
        model = WhisperModel(model_size_or_path,
                             device=device, compute_type=compute_type)
        while True:
            try:
                data = self.stream.read(
                    self.frame_size, exception_on_overflow=False)
                audio_float = np.frombuffer(
                    data, dtype=np.int16).astype(np.float32) / 32768.0
                is_speech = self.vad.is_speech(data, self.sample_rate)
                if self.mute:
                    is_speech = False
                    frames.clear()
                    self.end_of_speech = True
                    print("音声待機中", end="\r")
                if is_speech and self.mute == False:
                    frames.extend(audio_float)
                    self.end_of_speech = False
                    print("聞き取り中", end="\r")
                    self.speech_end_time = time.time() + 3  # 3秒無音で終了とみなす
                elif not is_speech and time.time() > self.speech_end_time or len(frames) >= self.sample_rate * 5:
                    self.end_of_speech = True
                    audio_data = np.array(frames, dtype=np.float32)
                    segments, info = model.transcribe(
                        audio_data, beam_size=3, vad_filter=True, language=language)
                    frames.clear()
                    text = "".join(segment.text for segment in segments)
                    self.text = text
                    if self.text != "":
                        print("ユーザー:", self.text)
                        threading.Thread(target=self.command,
                                         args=(self.text,)).start()
                    print("音声待機中", end="\r")
            except KeyboardInterrupt:
                break


class VoiceControl(VoiceRecognizer):
    def __init__(self, custom_devices, custom_routines, control, config):
        self.words = ["教", "何", "ですか", "なに", "とは", "について", "ますか", "して", "開いて", "送", "する", "どこ",
                      "いつ", "なんで", "なぜ", "どうして", "調", "通知", "お知らせ", "つけ", "付け", "オン", "けし", "消し", "決して", "オフ"]
        self.words.extend(["teach", "what", "is", "about", "how", "tell", "show", "open", "send", "do", "make", "explain", "help", "please", "can",
                          "you", "me", "this", "that", "create", "give", "where", "when", "why", "how", "notification", "notify", "on", "off", "turn"])  # 英語対応用
        self.custom_devices_name = [i["deviceName"]
                                    for i in custom_devices["deviceList"]]
        self.words.extend(self.custom_devices_name)
        self.control = control
        self.config = config
        self.genai_client = genai.Client(api_key=config["genai"]["apikey"])
        self.mcp_servers = config.get("mcpServers")
        self.url = config["server"]["url"]
        self.reply = ""
        self.text = ""
        self.plugin_manager = PluginManager()
        self.plugins = self.plugin_manager.load_plugins()
        self.custom_routines = custom_routines
        self.routine_list = [
            routine for routine in self.custom_routines["routineList"]]
        self.notifications = []
        threading.Thread(target=self.watch_notifications, daemon=True).start()
        super().__init__()

    def judge(self, command):
        text = command.user_input_text
        action = None
        response = ""
        if "つけ" in text or "付け" in text or "オン" in text:
            device_name = [i for i in self.custom_devices_name if i in text]
            if device_name:
                action = "turnOn"
        if "消し" in text or "けし" in text or "決して" in text or "オフ" in text:
            device_name = [i for i in self.custom_devices_name if i in text]
            if device_name:
                action = "turnOff"
        if ("今" in text or "現在" in text) and ("時" in text) and not "天気" in text:
            action = "now_time"
        if "今日" in text and "何日" in text:
            action = "now_day"
        if "通知" in text or "お知らせ" in text or "notification" in text or "notify" in text:
            action = "notification"
        if action == None:
            action = "ai"
            entities_replace = []
        if action in ['turnOn', 'turnOff']:
            response += self.control.custom_device_control(device_name, action)
        if action == 'ai':
            response = self.ask_gemini(text, entities_replace)
        if action == 'now_time':
            response = datetime.datetime.now().strftime("%H時%M分です")
        if action == 'now_day':
            response = datetime.datetime.now().strftime("%Y年%m月%d日です")
        if action == "notification":
            notification_count = len(self.notifications)
            if notification_count > 0:
                response = "".join(
                    [f"{notification.plugin_name}からです{notification.message}" for notification in self.notifications])
                threading.Thread(target=self.clear_notifications).start()
            else:
                response = "新しい通知はありません"
        command.reply_text = response
        command.action_type = action
        return command

    def command(self, text):
        self.reply = ""
        text = text.replace(" ", "")
        text = unicodedata.normalize("NFKC", text)
        commands = []
        command = VoiceCommand(text)
        for routine in self.routine_list:
            if routine["routineName"] in text:
                self.execute_routine(routine["routineName"])
                return
        if len(text) < 13:
            for plugin in self.plugins:
                command = VoiceCommand(text)
                if plugin.can_handle(text) or plugin.is_plugin_mode:
                    try:
                        command = plugin.execute(command)
                        if command.reply_text != "":
                            commands.append(command)
                    except Exception as e:
                        print(f"プラグイン {plugin.name} の実行中にエラーが発生しました: {e}")
        if not commands:
            for i in self.words:
                if i in text:
                    commands.append(self.judge(command))
                    break
            else:
                self.control.custom_scene_control(text)
        if commands or self.reply != "":
            self.yomiage(commands)
        return commands

    def ask_gemini(self, text, entities):
        def get_plugin_list() -> list:
            """
            These plugins(features) have not been retrieved. Get a list of plugins(features) that have not been retrieved. Required for plugin execution.
            Returns:
                list[dict[str, object]]: A list of plugin dictionaries.
                    Each plugin dictionary contains:
                        - name (str): The plugin name (used with execute_plugin()).
                        - description (str): A short explanation of the plugin.
                        - keywords (list[str]): Keywords related to the plugin,
                                                should be included in the prompt
                                                when using execute_plugin().
            """
            plugins = []
            for plugin in self.plugins:
                name = plugin.name
                description = plugin.description
                keywords = plugin.keywords
                plugins.append(
                    {"name": name, "description": description, "keywords": keywords})
            print("プラグイン一覧を取得しました")
            return plugins

        def execute_plugin(plugin_name: str, prompt: str) -> str:
            """ Execute a plugin(feature) that have not been retrieved using the given prompt.
            Args:
                plugin_name: The name of the plugin to execute. Must be obtained from get_plugin_list().
                prompt: The prompt to use for the plugin. Should include a keyword obtained from get_plugin_list().
            Returns:
                The response from the plugin.
            """
            for plugin in self.plugins:
                if plugin.name == plugin_name:
                    print(f"{plugin_name} を実行します: {prompt}")
                    command = plugin.execute(VoiceCommand(prompt))
                    if command.reply_text != "":
                        return command.reply_text
                    else:
                        return "The plugin did not respond. Please change the prompt and try again."
            return "Plugin not found"

        plugin_tools = [get_plugin_list, execute_plugin,
                        self.get_routine_list, self.execute_routine]
        print("AIが回答します")
        for name in entities:
            for e in entities[name]:
                text = text.replace(
                    e["body"], f'{e["body"]}({str(e["value"])})')
        try:
            async def generate_content(text, tools):
                response = await self.genai_client.aio.models.generate_content(
                    model=self.config["genai"]["model_name"],
                    contents=text,
                    config=genai.types.GenerateContentConfig(
                        temperature=0,
                        tools=tools,
                        system_instruction=self.config["genai"]["system_instruction"],
                    ),
                )
                return response

            async def mcp_generate_content(text):
                mcp_client = fastmcp.Client(self.mcp_servers)
                async with mcp_client:
                    await mcp_client.ping()
                    tools = await mcp_client.list_tools()
                    tools = [*plugin_tools, mcp_client.session]
                    response = await generate_content(text, tools)
                    return response
            if self.mcp_servers:
                genai_response = asyncio.run(mcp_generate_content(text))
            else:
                genai_response = asyncio.run(
                    generate_content(text, [*plugin_tools]))
            reply_text = genai_response.text.replace("\n", "")
        except Exception as e:
            reply_text = f"エラーが発生しました"
            print(e)
        return reply_text

    def get_routine_list(self) -> list:
        """
        Returns a list of available routines.
        Returns:
            list[str]: A list of routine names.
        """
        print("ルーチン一覧を取得しました")
        return self.routine_list

    def execute_routine(self, routine_name: str):
        """Execute a routine by its name.
        Args:
            routine_name: The name of the routine to execute. Must be obtained from get_routine_list().
        """
        for routine in self.routine_list:
            if routine["routineName"] == routine_name:
                print(f"{routine_name}を実行します")
                for command in routine["commands"]:
                    self.command(command)
                break

    def watch_notifications(self):
        while True:
            notifications = self.check_notification()
            if notifications:
                commands = [VoiceCommand(
                    user_input_text="", action_type="notification", reply_text=f"新しい通知があります")]
                commands.extend([VoiceCommand(user_input_text="", action_type="notification",
                                reply_text=f"{notification.message}") for notification in notifications])
                self.yomiage(commands)
            time.sleep(1)

    def check_notification(self):
        notifications = []
        add_notifications = []
        for plugin in self.plugins:
            plugin_notifications = plugin.get_active_notifications()
            for notification in plugin_notifications:
                notifications.append(notification)
                if notification not in self.notifications:
                    add_notifications.append(notification)
        self.notifications = notifications
        return add_notifications

    def clear_notifications(self):
        for plugin in self.plugins:
            plugin.clear_notifications()
        time.sleep(5)
        self.notifications = []

    def yomiage(self, commands):
        for command in commands:
            text = command.reply_text
            print(text)
            action = command.action_type
            self.mute = True
            try:
                response = requests.post(self.url, json={
                                         self.config["server"]["reply_text"]: text, self.config["server"]["action"]: action})
                if response.status_code != 200:
                    print("読み上げサーバーへの接続に失敗しました")
            except:
                print("読み上げサーバーへの接続に失敗しました")
            self.mute = False


class Control:
    def __init__(self, customdevices, customscenes):
        self.custom_devices = customdevices
        self.custom_scenes = customscenes

    def custom_device_control(self, text, action):
        reply = ""
        for i in self.custom_devices["deviceList"]:
            if i["deviceName"] in text:
                if action:
                    command = i[action].split(" ")
                    if action == "turnOn":
                        reply += f"{i['deviceName']}をオンにします"
                    else:
                        reply += f"{i['deviceName']}をオフにします"
                    subprocess.run(command)
                else:
                    reply = "なにをするかわかりませんでした"
        return reply

    def custom_scene_control(self, text):
        reply = ""
        for i in self.custom_scenes["sceneList"]:
            if i["sceneName"] in text:
                command = i["command"].split(" ")
                for _ in range(text.count(i["sceneName"])):
                    reply += f"{i['sceneName']}を実行します"
                    subprocess.run(command)
        return reply


def run():
    custom_scenes = json.load(
        open(os.path.join(dir_name, "config", "custom_scenes.json")))
    custom_devices = json.load(
        open(os.path.join(dir_name, "config", "custom_devices.json")))
    custom_routines = json.load(
        open(os.path.join(dir_name, "config", "custom_routines.json")))
    config = json.load(open(os.path.join(dir_name, "config", "config.json")))
    c = Control(custom_devices, custom_scenes)
    voice = VoiceControl(c.custom_devices, custom_routines, c, config)
    if config.get("vosk"):
        voice.listen_vosk(config["vosk"]["model_path"])
    elif config.get("whisper"):
        voice.listen_whisper(config["whisper"]["model_size_or_path"], config["whisper"]
                             ["device"], config["whisper"]["compute_type"], config["whisper"]["language"])


if __name__ == "__main__":
    run()
