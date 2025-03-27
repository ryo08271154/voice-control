import switchbot
import os
import wit
import asyncio
import vosk
import pyaudio
import json
import subprocess
import threading
import requests
import datetime
import pychromecast
import time
import unicodedata
import numpy as np
import google.generativeai as genai
import re
dir_name=os.path.dirname(__file__)
class Voice:
    def __init__(self,devices_name,custom_devices,control,service,wit_token,genai_apikey,url=""):
        self.words=[]
        self.devices_name=devices_name
        self.custom_devices_name=[i["deviceName"] for i in custom_devices["deviceList"]]
        self.words.extend(self.devices_name)
        self.words.extend(self.custom_devices_name)
        self.control=control
        self.service=service
        self.wit_client=wit.Wit(wit_token)
        self.genai_apikey=genai_apikey
        genai.configure(api_key=self.genai_apikey)
        self.model = genai.GenerativeModel("gemini-1.5-flash-8b",system_instruction="あなたは3簡潔に文以下で回答する音声アシスタントです",generation_config={"max_output_tokens": 100})
        self.chat=self.model.start_chat(history=[])
        self.url=url
        self.reply=""
        self.text=""
        self.model=vosk.Model(os.path.join(dir_name,"vosk-model-ja"))
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.mute=False
    def always_on_voice(self):
        # PyAudioの設定
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,  # 16kHz に変更
                        input=True,
                        frames_per_buffer=2048)  # バッファサイズを適切に設定
        temp_text="temp"
        temp_text_count=0
        while True:
            try:
                data=stream.read(2048,exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    if temp_text_count<3 and self.mute==False:
                        if self.text!="":
                            print("結果",self.text)
                            threading.Thread(target=self.command,args=(self.text,)).start()
                    temp_text="temp"
                    temp_text_count=0
                    self.mute=False
                    self.text=json.loads(self.recognizer.Result())["text"]
                else:
                    self.text=json.loads(self.recognizer.PartialResult())["partial"]
                    if self.text!="":
                        if self.text==temp_text:
                            temp_text_count+=1
                            data_int16 = np.frombuffer(data, dtype=np.int16) /32768.0
                            if temp_text_count==3 and self.mute==False:
                                if data_int16.max()<0.05:
                                    self.mute=True
                                    self.text=temp_text
                                    print(self.text)
                                    threading.Thread(target=self.command,args=(self.text,)).start()
                                else:
                                    print(data_int16.max())
                                    temp_text_count=0
                        else:
                            temp_text=self.text
                            temp_text_count=0
            except KeyboardInterrupt:
                break

    def judge(self,text):
        action=None
        if "つけ" in text:
            device_name=[i for i in self.devices_name if i in text]
            if device_name:
                action="turnOn"
        if "消し" in text or "けし" in text or "決して" in text:
            device_name=[i for i in self.devices_name if i in text]
            if device_name:
                action="turnOff"
        if "再生" in text:
            action="Play"
        if "一時停止" in text or "止めて" in text:
            action="Pause"
        if "停止" in text:
            action="Stop"
        if "音量" in text:
            volume=re.sub(r"\D","",text)
            if volume=="":
                volume=1
            if "上げ" in text:
                action="volume_up"
            if "下げ" in text:
                action="volume_down"
        if "教え" in text or "ついて" in text or "何" in text or "なに" in text:
            num=re.sub(r"\D","",text)
            if num=="":
                entities_replace=[]
                action="ai"
        if action==None: #判別できなかったとき
            r=self.wit_client.message(text)
            if r['intents']:
                action=r["intents"][0]["name"]
                if r['entities']:
                    if action in ['turnOn','turnOff']:
                        device_name=[i["value"] for i in r["entities"]["device_name:device_name"]]
                    if action=='weather':
                        if r["entities"].get("wit$datetime:datetime"):
                            action=datetime.datetime.fromisoformat(r["entities"]["wit$datetime:datetime"][0]["value"])
                        self.service.weather(action)
                    if action=="volume_up" or action=="volume_down":
                        volume=r["entities"].get("wit$number:number",[{}])[0].get("value",1)
                    if action=='ai':
                        entities_replace=r["entities"]
        if action in ['turnOn','turnOff']:
            self.control.custom_device_control(device_name,action)
            self.control.switchbot_device_control(device_name,action)
        if action in ['Play','Pause','Stop']:
            self.control.media_control(action)
        if action in ['volume_up','volume_down']:
            self.control.volume_control(action,int(volume))
        if action=='Back':
            second=sum(i.get("Second",0)for i in r["entities"].get("wit$duration:duration",[{}]))
            self.control.back_or_skip("Back",second)
        if action=='Skip':
            second=sum(i.get("Second",0)for i in r["entities"].get("wit$duration:duration",[{}]))
            self.control.back_or_skip("Skip",second)
        if action=='ai':
            self.ai(text,entities_replace)
        return action
    def command(self,text):
        self.reply=""
        text=text.replace(" ","")
        text=unicodedata.normalize("NFKC",text)
        for i in self.words:
            if i in text:
                self.judge(text)
                break
        else:
            self.control.custom_scene_control(text)
            self.control.switchbot_scene_control(text)
        if self.reply=="":
            self.reply="よくわかりませんでした"
    def ai(self,text,entities):
        print("AIが回答します")
        for name in entities:
            for e in entities[name]:
                text=text.replace(e["body"],f'{e["body"]}({str(e["value"])})')
        try:
            response = self.chat.send_message(text).text.replace("\n","")
        except:
            response="エラーが発生しました"
        print(response)
        self.yomiage(response)
    def yomiage(self,text=""):
        start=""
        self.reply=text
        if "実行" in text:
            start="execute"
        if "オン" in text:
            start="on"
        if "オフ" in text:
            start="off"
        if start!="":
            text=""
            self.mute=False
        else:
            self.mute=True
        requests.post(self.url,json={"message":text,"start":start,"end":""})
        self.mute=False
class Control(Voice):
    def __init__(self,switchbotdevices,switchbotscenes,customdevices,customscenes,friendly_names=[]):
        self.devices=switchbotdevices
        self.scenes=switchbotscenes
        self.custom_devices=customdevices
        self.custom_scenes=customscenes
        self.devices_name=[i["deviceName"] for i in self.devices["body"]["infraredRemoteList"]]
        self.chromecasts, self.browser = pychromecast.get_listed_chromecasts(friendly_names=friendly_names)
    def custom_device_control(self,text,action):
        for i in self.custom_devices["deviceList"]:
            if i["deviceName"] in text:
                if action:
                    command=i[action].split(" ")
                    if action=="turnOn":reply=f"{i['deviceName']}をオンにします"
                    else:reply=f"{i['deviceName']}をオフにします"
                    print("カスタムデバイス:",command)
                    subprocess.run(command)
                else:
                    print("わかりませんでした")
                    reply="なにをするかわかりませんでした"
                self.yomiage(reply)
    def custom_scene_control(self,text):
        for i in self.custom_scenes["sceneList"]:
            if i["sceneName"] in text:
                command=i["command"].split(" ")
                for _ in range(text.count(i["sceneName"])):
                    reply=f"{i['sceneName']}を実行します"
                    print("カスタムシーン:",command)
                    subprocess.run(command)
                self.yomiage(reply)
    def switchbot_device_control(self,text,action):
        for i in text:
            if i in self.devices_name:
                print(action)
                if action:
                    if action=="turnOn":reply=f"{i}をオンにします"
                    else:reply=f"{i}をオフにします"
                    switchbot.commands(i,action)
                else:
                    reply="なにをするかわかりませんでした"
                self.yomiage(reply)
    def switchbot_scene_control(self,text):
        for i in self.scenes["body"]:
            if i["sceneName"] in text:
                for _ in range(text.count(i["sceneName"])):
                    reply=f"{i['sceneName']}を実行します"
                    switchbot.scene(i["sceneName"])
                self.yomiage(reply)
    def volume_control(self,action,up_down=1):
        print(action,up_down)
        for cast in self.chromecasts:
            cast.wait()
            if cast.status.app_id!=None:
                print(cast)
                volume=cast.status.volume_level
                try:
                    if action=="volume_up":
                        cast.set_volume(volume+(0.01*up_down))
                    if action=="volume_down":
                        cast.set_volume(volume-(0.01*up_down))
                except:
                    print("音量操作できません")
                break
        else:
            for _ in range(up_down):
                if action=="volume_up":
                    switchbot.commands("テレビ","volumeAdd")
                if action=="volume_down":
                    switchbot.commands("テレビ","volumeSub")
    def media_control(self,action):
        print(action)
        for cast in self.chromecasts:
            cast.wait()
            mc=cast.media_controller
            if cast.status.app_id!=None:
                mc.block_until_active(timeout=10)
                try:
                    if action=="Play":
                        mc.play()
                    if action=="Pause":
                        mc.pause()
                    if action=="Stop":
                        mc.stop()
                except:
                    print("メディア操作できません")
                break
        else:
            print("テレビ操作")
            if action=="Play":
                switchbot.scene("再生")
            if action=="Pause":
                switchbot.scene("一時停止")
            if action=="Stop":
                switchbot.scene("停止")
    def back_or_skip(self,action,second=10):
        print(action,second)
        for cast in self.chromecasts:
            cast.wait()
            mc=cast.media_controller
            if cast.status.app_id!=None:
                try:
                    mc.block_until_active(timeout=10)
                    mc.play()
                    time.sleep(1)
                    mc.update_status()
                    current_time=mc.status.current_time
                    mc.pause()
                    if action=="Back":
                        mc.seek(current_time-second)
                    if action=="Skip":
                        mc.seek(current_time+second)
                except:
                    print("メディア操作できません")
                break
        else:
            for _ in range(second//10):
                if action=="Back":
                    switchbot.scene("早戻し")
                if action=="Skip":
                    switchbot.scene("早送り")
class Services(Voice):
    def __init__(self,weatherapikey=None,location=None):
        self.weatherapikey=weatherapikey
        self.location=location
    def weather(self,date):
        tenki=""
        if not date:
            tenki="いつの天気を教えてほしいかわかりませんでした"
        elif datetime.datetime.now().day==date.day:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={self.location['latitude']}&lon={self.location['longitude']}&lang=ja&units=metric&appid={self.weatherapikey}").json()
            tenki=f"現在の気温は{weather_json['main']['temp']}℃ 天気は{weather_json['weather'][0]['description']}です"
        else:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={self.location['latitude']}&lon={self.location['longitude']}&lang=ja&units=metric&appid={self.weatherapikey}").json()
            get_date=datetime.datetime.strftime(date,"%Y-%m-%d")
            for i in range(1,len(weather_json["list"])):
                if weather_json["list"][i]["dt_txt"]==f"{get_date} 09:00:00":
                    tenki=f'{date.day}日の９時の気温は{weather_json["list"][i]["main"]["temp"]}℃ 天気は{weather_json["list"][i]["weather"][0]["description"]} '
                    tenki+=f'１２時の気温は{weather_json["list"][i+1]["main"]["temp"]}℃ 天気は{weather_json["list"][i+1]["weather"][0]["description"]} '
                    tenki+=f'１５時の気温は{weather_json["list"][i+2]["main"]["temp"]}℃ 天気は{weather_json["list"][i+2]["weather"][0]["description"]}でしょう'
                    break
            else:
                tenki="天気情報が見つかりませんでした"
        print(tenki)
        reply=f"{tenki}"
        self.yomiage(reply)
def run():
    custom_scenes=json.load(open(os.path.join(dir_name,"custom_scenes.json")))
    custom_devices=json.load(open(os.path.join(dir_name,"custom_devices.json")))
    config=json.load(open(os.path.join(dir_name,"config.json")))
    c=Control(switchbot.devices,switchbot.scenes,custom_devices,custom_scenes,config["chromecasts"]["friendly_names"])
    s=Services(config["apikeys"]["weather_api_key"],config["location"])
    voice=Voice(c.devices_name,c.custom_devices,c,s,config["apikeys"]["wit_token"],config["apikeys"]["genai"],config["url"]["server_url"])
    voice.words.extend(["電気","天気","再生","停止","止めて","ストップ","音","スキップ","戻","飛ばし","早送り","早戻し","秒","分","教","何","ですか","なに","とは","について","ますか"])
    voice.always_on_voice()
if __name__=="__main__":
    run()
