import switchbot
import os
import wit
import asyncio
# import speech_recognition as sr
import vosk
import pyaudio
import json
import subprocess
import threading
import requests
import datetime            
# devices=switchbot.devices
# scenes=switchbot.scenes

dir_name=os.path.dirname(__file__)

# devices_name=[i["deviceName"] for i in devices["body"]["infraredRemoteList"]]
# custom_devices_name=[i["deviceName"] for i in custom_devices["deviceList"]]
class Voice:
    def __init__(self,devices_name,custom_devices,control,service):
        self.words=[]
        self.devices_name=devices_name
        self.custom_devices_name=[i["deviceName"] for i in custom_devices["deviceList"]]
        self.words.extend(self.devices_name)
        self.words.extend(self.custom_devices_name)
        self.control=control
        self.service=service
        self.reply=""
        self.text=""
        self.model=vosk.Model(os.path.join(dir_name,"model_2"))
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
    def always_on_voice(self):
        # PyAudioの設定
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,  # 16kHz に変更
                        input=True,
                        frames_per_buffer=4000)  # バッファサイズを適切に設定
        while True:
            # print("聞き取り")
            try:
                data=stream.read(4000,exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    self.text=json.loads(self.recognizer.Result())["text"]
                    if self.text!="":
                        print(self.text)
                        threading.Thread(target=self.command,args=(self.text,)).start()
            except KeyboardInterrupt:
                exit()

    def judge(self,text):
        action=None
        client=wit.Wit(os.getenv("WIT_TOKEN"))
        r=client.message(text)
        if r['intents']:
            if r['entities']:
                if r['intents'][0]['name'] in ['turnOn','turnOff']:
                    action=r['intents'][0]["name"]
                    device_name=[i["body"] for i in r["entities"]["device_name:device_name"]]
                    self.control.custom_device_control(device_name,action)
                    self.control.switchbot_device_control(device_name,action)
            if r['intents'][0]['name']=='weather':
                if r["entities"]:
                    action=datetime.datetime.fromisoformat(r["entities"]["wit$datetime:datetime"][0]["value"])
                self.service.weather(action)
        return action
    def command(self,text):
        self.reply=""
        text=text.replace(" ","")
        for i in self.words:
            if i in text:
                self.judge(text)
                break
        else:
            self.control.custom_scene_control(text)
            self.control.switchbot_scene_control(text)
        if self.reply!="":
            reply="よくわかりませんでした"
class Control:
    def __init__(self,switchbotdevices,switchbotscenes,customdevices,customscenes):
        self.devices=switchbotdevices
        self.scenes=switchbotscenes
        self.custom_devices=customdevices
        self.custom_scenes=customscenes
        self.devices_name=[i["deviceName"] for i in self.devices["body"]["infraredRemoteList"]]
        # self.custom_devices_name=[i["deviceName"] for i in custom_devices["deviceList"]]
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
                yomiage(reply)
    def custom_scene_control(self,text):
        for i in self.custom_scenes["sceneList"]:
            if i["sceneName"] in text:
                command=i["command"].split(" ")
                reply=f"{i['sceneName']}を実行します"
                print("カスタムシーン:",command)
                subprocess.run(command)
                yomiage(reply)
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
                yomiage(reply)
    def switchbot_scene_control(self,text):
        for i in self.scenes["body"]:
            if i["sceneName"] in text:
                reply=f"{i['sceneName']}を実行します"
                switchbot.scene(i["sceneName"])
                yomiage(reply)
class Services:
    def __init__(self):
        self.weatherapikey=os.getenv("OPENWEATHER_APIKEY")
        self.location=os.getenv("OPENWEATHER")
    def weather(self,date):
        tenki=""
        if not date:
            tenki="いつの天気を教えてほしいかわかりませんでした"
        elif datetime.datetime.now().day==date.day:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/weather?{self.location}&lang=ja&appid={self.weatherapikey}").json()
            tenki=weather_json["weather"][0]["description"]
        else:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/forecast?{self.location}&lang=ja&appid={self.weatherapikey}").json()
            get_date=datetime.datetime.strftime(date,"%Y-%m-%d")
            for i in range(1,len(weather_json["list"])):
                if weather_json["list"][i]["dt_txt"]==f"{get_date} 09:00:00":
                    tenki=f'９時の気温は{round((float(weather_json["list"][i]["main"]["temp"])-273.15),1)}℃ 天気は{weather_json["list"][i]["weather"][0]["description"]}でしょう '
                    tenki+=f'１２時の気温は{round((float(weather_json["list"][i+1]["main"]["temp"])-273.15),1)}℃ 天気は{weather_json["list"][i+1]["weather"][0]["description"]}でしょう '
                    tenki+=f'１５時の気温は{round((float(weather_json["list"][i+2]["main"]["temp"])-273.15),1)}℃ 天気は{weather_json["list"][i+2]["weather"][0]["description"]}'
        print(tenki,"です")
        reply=f"{tenki}です"
        yomiage(reply)
def yomiage(text=""):
    requests.post("http://192.168.1.2:5000/tts/",json={"message":text,"start":"","end":""})
def run():
    custom_scenes=json.load(open(os.path.join(dir_name,"custom_scenes.json")))
    custom_devices=json.load(open(os.path.join(dir_name,"custom_devices.json")))
    c=Control(switchbot.devices,switchbot.scenes,custom_devices,custom_scenes)
    s=Services()
    voice=Voice(c.devices_name,c.custom_devices,c,s)
    voice.words.extend(["電気","天気"])
    voice.always_on_voice()
if __name__=="__main__":
    run()