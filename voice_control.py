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
dir_name=os.path.dirname(__file__)
class Voice:
    def __init__(self,devices_name,custom_devices,control,service,wit_token):
        self.words=[]
        self.devices_name=devices_name
        self.custom_devices_name=[i["deviceName"] for i in custom_devices["deviceList"]]
        self.words.extend(self.devices_name)
        self.words.extend(self.custom_devices_name)
        self.control=control
        self.service=service
        self.wit_token=wit_token
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
                        frames_per_buffer=4000)  # バッファサイズを適切に設定
        while True:
            try:
                if self.mute==False:
                    data=stream.read(4000,exception_on_overflow=False)
                    if self.recognizer.AcceptWaveform(data):
                        self.text=json.loads(self.recognizer.Result())["text"]
                        if self.text!="":
                            print(self.text)
                            threading.Thread(target=self.command,args=(self.text,)).start()
            except KeyboardInterrupt:
                break

    def judge(self,text):
        action=None
        client=wit.Wit(self.wit_token)
        r=client.message(text)
        if r['intents']:
            if r['entities']:
                if r['intents'][0]['name'] in ['turnOn','turnOff']:
                    action=r['intents'][0]["name"]
                    device_name=[i["value"] for i in r["entities"]["device_name:device_name"]]
                    self.control.custom_device_control(device_name,action)
                    self.control.switchbot_device_control(device_name,action)
            if r['intents'][0]['name']=='weather':
                if r["entities"]:
                    action=datetime.datetime.fromisoformat(r["entities"]["wit$datetime:datetime"][0]["value"])
                self.service.weather(action)
            if r['intents'][0]['name']=='Play':
                self.control.media_control("Play")
            if r['intents'][0]['name']=='Pause':
                self.control.media_control("Pause")
            if r['intents'][0]['name']=='Stop':
                self.control.media_control("Stop")
            if r['intents'][0]['name']=='volume_up':
                self.control.volume_control("volume_up",r["entities"].get("wit$number:number",[{}])[0].get("value",1))
            if r['intents'][0]['name']=='volume_down':
                self.control.volume_control("volume_down",r["entities"].get("wit$number:number",[{}])[0].get("value",1))
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
        if self.reply=="":
            self.reply="よくわかりませんでした"
    def yomiage(self,text=""):
        start=""
        self.reply=text
        self.mute=True
        if "実行" in text:
            start="execute"
        if "オン" in text:
            start="on"
        if "オフ" in text:
            start="off"
        if start!="":
            text=""
        requests.post("http://192.168.1.2:5000/tts/",json={"message":text,"start":start,"end":""})
        self.mute=False
class Control:
    def __init__(self,switchbotdevices,switchbotscenes,customdevices,customscenes,friendly_names=[],yomiage=None):
        self.devices=switchbotdevices
        self.scenes=switchbotscenes
        self.custom_devices=customdevices
        self.custom_scenes=customscenes
        self.devices_name=[i["deviceName"] for i in self.devices["body"]["infraredRemoteList"]]
        self.yomiage=yomiage
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
        for cast in self.chromecasts:
            cast.wait()
            mc=cast.media_controller
            if cast.status.app_id!=None:
                mc.block_until_active(timeout=10)
                print(cast)
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
class Services:
    def __init__(self,weatherapikey=None,location=None,yomiage=None):
        self.weatherapikey=weatherapikey
        self.location=location
        self.yomiage=yomiage
    def weather(self,date):
        tenki=""
        if not date:
            tenki="いつの天気を教えてほしいかわかりませんでした"
        elif datetime.datetime.now().day==date.day:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={self.location['latitude']}&lon={self.location['longitude']}&lang=ja&units=metric&appid={self.weatherapikey}").json()
            tenki=f"今日の気温は{weather_json['main']['temp']}℃ 天気は{weather_json['weather'][0]['description']}です"
        else:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={self.location['latitude']}&lon={self.location['longitude']}&lang=ja&units=metric&appid={self.weatherapikey}").json()
            get_date=datetime.datetime.strftime(date,"%Y-%m-%d")
            for i in range(1,len(weather_json["list"])):
                if weather_json["list"][i]["dt_txt"]==f"{get_date} 09:00:00":
                    tenki=f'{date.day}日の９時の気温は{weather_json["list"][i]["main"]["temp"]}℃ 天気は{weather_json["list"][i]["weather"][0]["description"]} '
                    tenki+=f'１２時の気温は{weather_json["list"][i+1]["main"]["temp"]}℃ 天気は{weather_json["list"][i+1]["weather"][0]["description"]} '
                    tenki+=f'１５時の気温は{weather_json["list"][i+2]["main"]["temp"]}℃ 天気は{weather_json["list"][i+2]["weather"][0]["description"]}でしょう'
                    break
        print(tenki)
        reply=f"{tenki}"
        self.yomiage(reply)
def run():
    custom_scenes=json.load(open(os.path.join(dir_name,"custom_scenes.json")))
    custom_devices=json.load(open(os.path.join(dir_name,"custom_devices.json")))
    config=json.load(open(os.path.join(dir_name,"config.json")))
    c=Control(switchbot.devices,switchbot.scenes,custom_devices,custom_scenes,config["chromecasts"]["friendly_names"])
    s=Services(config["apikeys"]["weather_api_key"],config["location"])
    voice=Voice(c.devices_name,c.custom_devices,c,s,config["apikeys"]["wit_token"])
    c.yomiage=voice.yomiage
    s.yomiage=voice.yomiage
    voice.words.extend(["電気","天気","再生","停止","止めて","音"])
    voice.always_on_voice()
if __name__=="__main__":
    run()