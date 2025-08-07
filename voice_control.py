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
from plugin import PluginManager
from commands import VoiceCommand
dir_name=os.path.dirname(__file__)
class VoiceRecognizer:
    mute=False
    def always_on_voice(self,model_path):
        sample_rate = 16000
        model=vosk.Model(model_path)
        recognizer=vosk.KaldiRecognizer(model, sample_rate)
        recognizer.SetPartialWords(False)
        # PyAudioの設定
        p = pyaudio.PyAudio()
        vad = webrtcvad.Vad(2)
        frame_duration = 30  # ms
        frame_size = int(sample_rate * frame_duration / 1000)
        frame_bytes = frame_size * 2  # 16-bit audio
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=sample_rate,  # 16kHz に変更
                        input=True,
                        frames_per_buffer=frame_size)  # バッファサイズを適切に設定
        end_of_speech = True
        speech_end_time = time.time()
        while True:
            try:
                data=stream.read(frame_size,exception_on_overflow=False)
                if len(data) != frame_bytes:
                    continue  # フレーム長が正しくない場合スキップ
                is_speech = vad.is_speech(data,sample_rate)
                if is_speech:
                    end_of_speech = False
                    print("聞き取り中",end="\r")
                    speech_end_time = time.time() + 3  # 3秒無音で終了とみなす
                elif not is_speech and time.time() > speech_end_time:
                    end_of_speech = True
                    print("音声待機中",end="\r")
                if end_of_speech==False:
                    if recognizer.AcceptWaveform(data):
                        if self.mute==False:
                            self.text=json.loads(recognizer.Result())["text"]
                            if self.text!="":
                                print("ユーザー:",self.text)
                                end_of_speech = True
                                threading.Thread(target=self.command,args=(self.text,)).start()
            except KeyboardInterrupt:
                break
class VoiceControl(VoiceRecognizer):
    def __init__(self,custom_devices,custom_routines,control,config):
        self.words=["教","何","ですか","なに","とは","について","ますか","して","開いて","送","する","どこ","いつ","なんで","なぜ","どうして","調","通知","お知らせ"]
        self.words.extend(["teach", "what", "is", "about", "how", "tell", "show", "open", "send", "do", "make", "explain", "help", "please", "can", "you", "me", "this", "that", "create", "give","where","when","why","how","notification","notify"]) # 英語対応用
        self.custom_devices_name=[i["deviceName"] for i in custom_devices["deviceList"]]
        self.words.extend(self.custom_devices_name)
        self.control=control
        self.config=config
        self.genai_client=genai.Client(api_key=config["genai"]["apikey"])
        self.mcp_servers=config.get("mcpServers")
        self.url=config["server"]["url"]
        self.reply=""
        self.text=""
        self.plugin_manager=PluginManager()
        self.plugins=self.plugin_manager.load_plugins()
        self.custom_routines=custom_routines
        self.routine_list=[routine for routine in self.custom_routines["routineList"]]
        self.notifications=[]
        threading.Thread(target=self.watch_notifications,daemon=True).start()
    def judge(self,command):
        text=command.user_input_text
        action=None
        response=""
        if "つけ" in text or "付け" in text or "オン" in text:
            device_name=[ i for i in self.custom_devices_name if i in text]
            if device_name:
                action="turnOn"
        if "消し" in text or "けし" in text or "決して" in text or "オフ" in text:
            device_name=[ i for i in self.custom_devices_name if i in text]
            if device_name:
                action="turnOff"
        if ("今" in text or "現在" in text) and ("時" in text) and not "天気" in text:
            action="now_time"
        if "今日" in text and "何日" in text:
            action="now_day"
        if "通知" in text or "お知らせ" in text or "notification" in text or "notify" in text:
            action="notification"
        if action==None:
            action="ai"
            entities_replace=[]
        if action in ['turnOn','turnOff']:
            response+=self.control.custom_device_control(device_name,action)
        if action=='ai':
            response=self.ask_gemini(text,entities_replace)
        if action=='now_time':
            response=datetime.datetime.now().strftime("%H時%M分です")
        if action=='now_day':
            response=datetime.datetime.now().strftime("%Y年%m月%d日です")
        if action=="notification":
            notification_count=len(self.notifications)
            if notification_count>0:
                response="".join([f"{notification.plugin_name}からです{notification.message}" for notification in self.notifications])
                self.notifications=[]
            else:
                response="新しい通知はありません"
        command.reply_text=response
        command.action_type=action
        return command
    def command(self,text):
        self.reply=""
        text=text.replace(" ","")
        text=unicodedata.normalize("NFKC",text)
        commands=[]
        for routine in self.routine_list:
            if routine["routineName"] in text:
                self.execute_routine(routine["routineName"])
                break
        else:
            for plugin in self.plugins:
                command=VoiceCommand(text)
                if plugin.can_handle(text) or plugin.is_plugin_mode:
                    try:
                        command=plugin.execute(command)
                        if command.reply_text!="":
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
        if commands or self.reply!="":
            self.yomiage(commands)
    def ask_gemini(self,text,entities):
        print("AIが回答します")
        for name in entities:
            for e in entities[name]:
                text=text.replace(e["body"],f'{e["body"]}({str(e["value"])})')
        try:
            async def generate_content(text,tools):
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
                    tools=[mcp_client.session]
                    response = await generate_content(text,tools)
                    return response
            if self.mcp_servers:
                genai_response=asyncio.run(mcp_generate_content(text))
            else:
                genai_response=asyncio.run(generate_content(text,[]))
            reply_text=genai_response.text.replace("\n","")
        except Exception as e:
            reply_text=f"エラーが発生しました"
            print(e)
        return reply_text
    def execute_routine(self,routine_name):
        for routine in self.routine_list:
            if routine["routineName"]==routine_name:
                for command in routine["commands"]:
                    self.command(command)
                break
    def watch_notifications(self):
        while True:
            notifications=self.check_notification()
            if notifications:
                self.yomiage([VoiceCommand(user_input_text="",action_type="notification",reply_text="新しい通知があります")])
                self.notifications.extend(notifications)
            time.sleep(1)
    def check_notification(self):
        notifications=[]
        for plugin in self.plugins:
            plugin_notifications=plugin.get_active_notifications()
            notifications.extend(plugin_notifications)
            plugin.clear_notifications()
        return notifications
    def yomiage(self,commands):
        for command in commands:
            text=command.reply_text
            print(text)
            action=command.action_type
            self.mute=True
            try:
                response=requests.post(self.url,json={self.config["server"]["reply_text"]:text,self.config["server"]["action"]:action})
                if response.status_code!=200:
                    print("読み上げサーバーへの接続に失敗しました")
            except:
                print("読み上げサーバーへの接続に失敗しました")
            self.mute=False
class Control:
    def __init__(self,customdevices,customscenes):
        self.custom_devices=customdevices
        self.custom_scenes=customscenes
    def custom_device_control(self,text,action):
        reply=""
        for i in self.custom_devices["deviceList"]:
            if i["deviceName"] in text:
                if action:
                    command=i[action].split(" ")
                    if action=="turnOn":
                        reply+=f"{i['deviceName']}をオンにします"
                    else:
                        reply+=f"{i['deviceName']}をオフにします"
                    subprocess.run(command)
                else:
                    reply="なにをするかわかりませんでした"
        return reply
    def custom_scene_control(self,text):
        reply=""
        for i in self.custom_scenes["sceneList"]:
            if i["sceneName"] in text:
                command=i["command"].split(" ")
                for _ in range(text.count(i["sceneName"])):
                    reply+=f"{i['sceneName']}を実行します"
                    subprocess.run(command)
        return reply
def run():
    custom_scenes=json.load(open(os.path.join(dir_name,"config","custom_scenes.json")))
    custom_devices=json.load(open(os.path.join(dir_name,"config","custom_devices.json")))
    custom_routines=json.load(open(os.path.join(dir_name,"config","custom_routines.json")))
    config=json.load(open(os.path.join(dir_name,"config","config.json")))
    c=Control(custom_devices,custom_scenes)
    voice=VoiceControl(c.custom_devices,custom_routines,c,config)
    voice.always_on_voice(config["vosk"]["model_path"])
if __name__=="__main__":
    run()
