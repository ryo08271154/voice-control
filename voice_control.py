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
custom_scenes=json.load(open("custom_scenes.json"))
custom_devices=json.load(open("custom_devices.json"))
last_text=""
reply=""
def always_on_voice():
    global last_text
    model = vosk.Model("model_2")
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
                
def control(text):
    global reply
    reply=""
    text=text.replace(" ","")
    def judge():
        action=None
        client=wit.Wit(os.getenv("WIT_TOKEN"))
        r=client.message(text)
        if r['intents'] and r['entities']:
            if r['intents'][0]['name']=='turnOn' or 'turnOff':
                action=r['intents'][0]["name"]
            if r['intents'][0]['name']=='weather' and r["entities"]:
                action=datetime.datetime.fromisoformat(r["entities"]["wit$datetime:datetime"][0]["value"])
        return action
    if "天気" in text:
        action=judge()
        if action:weather(action)
        else:reply="いつの天気を教えてほしいかわかりませんでした"
        return yomiage(reply)
    for i in custom_devices["deviceList"]:
        if i["deviceName"] in text:
            action=judge()
            if action:
                command=i[action].split(" ")
                if action=="turnOn":reply=f"{i['deviceName']}をオンにします"
                else:reply=f"{i['deviceName']}をオフにします"
                print("カスタムデバイス:",command)
                subprocess.run(command)
            else:
                print("わかりませんでした")
                reply="なにをするかわかりませんでした"
            return yomiage(reply)
    for i in custom_scenes["sceneList"]:
        if i["sceneName"] in text:
            command=i["command"].split(" ")
            reply=f"{i['sceneName']}を実行します"
            print("カスタムシーン:",command)
            subprocess.run(command)
            return yomiage(reply)
    for i in devices["body"]["infraredRemoteList"]:
        if i["deviceName"] in text:
            action=judge()
            if action=="turnOn":reply=f"{i['deviceName']}をオンにします"
            else:reply=f"{i['deviceName']}をオフにします"
            print(action)
            if action:
                switchbot.commands(i["deviceName"],action)
            else:
                reply="なにをするかわかりませんでした"
            return yomiage(reply)
    for i in scenes["body"]:
        if i["sceneName"] in text:
            reply=f"{i['sceneName']}を実行します"
            switchbot.scene(i["sceneName"])
            return yomiage(reply)
    reply="よくわかりませんでした"
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
        get_date=datetime.datetime.strftime(date,"%Y-%m-%d 12:00:00")
        for i in range(1,len(weather_json["list"])):
            if weather_json["list"][i]["dt_txt"]==get_date:
                print(float(weather_json["list"][i]["main"]["temp"])-273.15)
                tenki=f'気温は{round((float(weather_json["list"][i]["main"]["temp"])-273.15),1)}℃{weather_json["list"][i]["weather"][0]["description"]}'
                break
    print(tenki,"です")
    reply=f"{tenki}です"
    return weather_json
def yomiage(text=""):
    global reply
    requests.post("http://192.168.1.2:5000/tts/",json={"message":text,"start":"","end":""})
if __name__=="__main__":
    always_on_voice()