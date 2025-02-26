import switchbot
import os
import wit
import asyncio
import speech_recognition as sr
import vosk
import pyaudio
import json
import subprocess
import threading
import requests
import datetime
devices=switchbot.devices
scenes=switchbot.scenes
dir_name=os.path.dirname(__file__)
custom_scenes=json.load(open(os.path.join(dir_name,"custom_scenes.json")))
custom_devices=json.load(open(os.path.join(dir_name,"custom_devices.json")))
last_text=""
reply=""
def always_on_voice():
    global last_text
    model = vosk.Model(os.path.join(dir_name,"model_2"))
    recognizer = vosk.KaldiRecognizer(model, 16000)
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
            if recognizer.AcceptWaveform(data):
                text=json.loads(recognizer.Result())["text"]
                if text!="":
                    print(text)
                    threading.Thread(target=control,args=(text,)).start()
                    last_text=text
        except KeyboardInterrupt:
            exit()
def judge(text):
    action=None
    client=wit.Wit(os.getenv("WIT_TOKEN"))
    r=client.message(text)
    if r['intents'] and r['entities']:
        if r['intents'][0]['name']=='turnOn' or 'turnOff':
            action=r['intents'][0]["name"]
        if r['intents'][0]['name']=='weather' and r["entities"]:
            action=datetime.datetime.fromisoformat(r["entities"]["wit$datetime:datetime"][0]["value"])
    return action                
def control(text):
    global reply
    reply=""
    text=text.replace(" ","")
    if "天気" in text:
        action=judge(text)
        if action:weather(action)
        else:reply="いつの天気を教えてほしいかわかりませんでした"
        return yomiage(reply)
    custom_device_control(text)
    custom_scene_control(text)
    switchbot_device_control(text)
    switchbot_scene_control(text)
    if reply!="":
        reply="よくわかりませんでした"
def custom_device_control(text):
    action=None
    for i in custom_devices["deviceList"]:
        if i["deviceName"] in text:
            if not action:
                action=judge(text)
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
def custom_scene_control(text):
    for i in custom_scenes["sceneList"]:
        if i["sceneName"] in text:
            command=i["command"].split(" ")
            reply=f"{i['sceneName']}を実行します"
            print("カスタムシーン:",command)
            subprocess.run(command)
            yomiage(reply)
def switchbot_device_control(text):
    action=None
    for i in devices["body"]["infraredRemoteList"]:
        if i["deviceName"] in text:
            if not action:
                action=judge(text)
            if action=="turnOn":reply=f"{i['deviceName']}をオンにします"
            else:reply=f"{i['deviceName']}をオフにします"
            print(action)
            if action:
                switchbot.commands(i["deviceName"],action)
            else:
                reply="なにをするかわかりませんでした"
            yomiage(reply)
def switchbot_scene_control(text):
    for i in scenes["body"]:
        if i["sceneName"] in text:
            reply=f"{i['sceneName']}を実行します"
            switchbot.scene(i["sceneName"])
            yomiage(reply)
def weather(date):
    global reply
    api_key=os.getenv("OPENWEATHER_APIKEY")
    location=os.getenv("OPENWEATHER")
    tenki=""
    if datetime.datetime.now().day==date.day:
        weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/weather?{location}&lang=ja&appid={api_key}").json()
        tenki=weather_json["weather"][0]["description"]
    else:
        weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/forecast?{location}&lang=ja&appid={api_key}").json()
        get_date=datetime.datetime.strftime(date,"%Y-%m-%d")
        for i in range(1,len(weather_json["list"])):
            if weather_json["list"][i]["dt_txt"]==f"{get_date} 09:00:00":
                tenki=f'９時の気温は{round((float(weather_json["list"][i]["main"]["temp"])-273.15),1)}℃ 天気は{weather_json["list"][i]["weather"][0]["description"]}でしょう '
                tenki+=f'１２時の気温は{round((float(weather_json["list"][i+1]["main"]["temp"])-273.15),1)}℃ 天気は{weather_json["list"][i+1]["weather"][0]["description"]}でしょう '
                tenki+=f'１５時の気温は{round((float(weather_json["list"][i+2]["main"]["temp"])-273.15),1)}℃ 天気は{weather_json["list"][i+2]["weather"][0]["description"]}'
    print(tenki,"です")
    reply=f"{tenki}です"
    return weather_json
def yomiage(text=""):
    global reply
    requests.post("http://192.168.1.2:5000/tts/",json={"message":text,"start":"","end":""})
if __name__=="__main__":
    always_on_voice()