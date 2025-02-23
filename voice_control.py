import switchbot
import os
import wit
import asyncio
import speech_recognition as sr
import json
import subprocess
devices=switchbot.devices
scenes=switchbot.scenes
custom_scenes=json.load(open("./custom_scenes.json"))
last_text=""
async def always_on_voice():
    global last_text
    while True:
        r=sr.Recognizer()
        with sr.Microphone()as source:
            print("聞き取り")
            r.adjust_for_ambient_noise(source)
            data=await asyncio.to_thread(r.listen,source)
            text=json.loads(await asyncio.to_thread(r.recognize_vosk,data,"ja"))["text"]
            print(text)
            if text!="":
                await control(text)
                last_text=text
                
async def control(text):
    action=None
    text=text.replace(" ","")
    for i in custom_scenes["sceneList"]:
        if i["sceneName"] in text:
            command=i["command"].split(" ")
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