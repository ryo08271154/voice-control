import flet
import datetime
import time
import speech_recognition as sr
import pyaudio
import asyncio
import json
import switchbot
devices=switchbot.devices
scenes=switchbot.scenes
def main(page:flet.Page):
    def menu(e):
        page.go("/menu")
        print("menu")
    page.theme_mode=flet.ThemeMode.DARK
    page.title="test"
    nowtime = flet.Text(datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S"), size=100,text_align=flet.TextAlign.CENTER)
    talk_text=flet.Text("", size=100,text_align=flet.TextAlign.CENTER)
    async def time_update():
        while True:
            nowtime.value =datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S")
            page.update()
            await asyncio.sleep(1)
    
    def voice(e):
        page.go("/voice")
        talk_text.value="聞き取り中"
        page.update()
        r=sr.Recognizer()
        with sr.Microphone()as source:
            print("聞き取り")
            data=r.listen(source)
            text=json.load(r.recognize_vosk(data))
            talk_text.value=text["text"]
            if text["text"]!="":
                control(text["text"])
                page.update()
            page.update()
        time.sleep(10)
        page.go("/")
    async def control(name):
        action=None
        for i in devices["body"]["infraredRemoteList"]:
            if i["deviceName"] in name:
                if "つけ" in name :action="turnOn"
                if "決し" in name:action="turnOff"
                print(action)
                if action:switchbot.commands(i["deviceName"],action)
                return
            pass
        for i in scenes["body"]:
            if i["sceneName"] in name:
                switchbot.scene(i["sceneName"])
                return
    async def back():
        await asyncio.sleep(5)
        page.go("/")
    async def always_on_voice():
        
        while True:
            
            r=sr.Recognizer()
            with sr.Microphone()as source:
                print("聞き取り")
                r.adjust_for_ambient_noise(source)
                data=await asyncio.to_thread(r.listen,source)
                text=json.loads(await asyncio.to_thread(r.recognize_vosk,data,"ja"))
                if text["text"]!="":
                    await control(text["text"])
                    page.go("/voice")
                    talk_text.value=text["text"]
                    page.update()
                    task=asyncio.create_task(back())
    def route(e):
        page.views.clear()

        if page.route=="/":
            talk_text.value=""
            page.views.append(flet.View("/",[flet.ElevatedButton("テストページへ移動", on_click=test),
                                            flet.Row([flet.TextButton("音声認識",on_click=voice)]),
                                            flet.Container(content=nowtime,expand=True,alignment=flet.alignment.center,on_click=menu)

                                            ],))
            
        if page.route=="/voice":
            
            page.views.append(flet.View("/voice",[flet.ElevatedButton("ホーム", on_click=lambda e:page.go("/")),
                                flet.Container(content=talk_text,expand=True,alignment=flet.alignment.center)

                                ],))
        if page.route=="/menu":
            page.views.append(flet.View("/menu",[flet.ElevatedButton("ホーム",on_click=lambda e:page.go("/")),
                                        ]))
        page.update()
    def test(e):
        page.go("/test")

    page.on_route_change=route
    page.on=menu

    page.run_task(time_update)
    page.run_task(always_on_voice)

    page.go(page.route)


flet.app(target=main,port=5000)