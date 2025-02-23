import switchbot
import os
import wit
import asyncio
import speech_recognition as sr
import json
devices=switchbot.devices
scenes=switchbot.scenes
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
                
async def control(name):
    action=None
    name=name.replace(" ","")
    for i in devices["body"]["infraredRemoteList"]:
        if i["deviceName"] in name:
            client=wit.Wit(os.getenv("WIT_TOKEN"))
            r=client.message(name)
            if r['intents']:action=r['intents'][0]["name"]
            print(action)
            if action:switchbot.commands(i["deviceName"],action)
            return
    for i in scenes["body"]:
        if i["sceneName"] in name:
            switchbot.scene(i["sceneName"])
            return
if __name__=="__main__":
    asyncio.run(always_on_voice())