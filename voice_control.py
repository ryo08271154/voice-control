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
devices=switchbot.devices
scenes=switchbot.scenes
custom_scenes=json.load(open("./custom_scenes.json"))
last_text=""
def always_on_voice():
    global last_text
    model = vosk.Model("model")
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
    action=None
    text=text.replace(" ","")
    for i in custom_scenes["sceneList"]:
        if i["sceneName"] in text:
            command=i["command"].split(" ")
            print("カスタム")
            subprocess.run(command)
            return
    for i in devices["body"]["infraredRemoteList"]:
        if i["deviceName"] in text:
            client=wit.Wit(os.getenv("WIT_TOKEN"))
            r=client.message(text)
            if r['intents']:action=r['intents'][0]["name"]
            print(action)
            if action:switchbot.commands(i["deviceName"],action)
            return
    for i in scenes["body"]:
        if i["sceneName"] in text:
            switchbot.scene(i["sceneName"])
            return
if __name__=="__main__":
    asyncio.run(always_on_voice())