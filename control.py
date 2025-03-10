import flet
import datetime
import asyncio
import switchbot
import voice_control
import os
import threading
devices=switchbot.devices
scenes=switchbot.scenes
def main(page:flet.Page):
    def menu(e):
        page.go("/menu")
    page.theme_mode=flet.ThemeMode.DARK
    page.title="音声操作"
    nowtime = flet.Text(datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S"), size=100,text_align=flet.TextAlign.CENTER)
    talk_text=flet.Text("",size=50)
    reply=flet.Text("", size=100,text_align=flet.TextAlign.CENTER)
    async def time_update():
        while True:
            nowtime.value =datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S")
            page.update()
            await asyncio.sleep(1)

    async def back():
        await asyncio.sleep(30)
        page.go("/")
    async def listen():
        import json
        dir_name=os.path.dirname(__file__)
        global voice,c
        custom_scenes=json.load(open(os.path.join(dir_name,"custom_scenes.json")))
        custom_devices=json.load(open(os.path.join(dir_name,"custom_devices.json")))
        config=json.load(open(os.path.join(dir_name,"config.json")))
        c=voice_control.Control(switchbot.devices,switchbot.scenes,custom_devices,custom_scenes,config["chromecasts"]["friendly_names"])
        s=voice_control.Services(config["apikeys"]["weather_api_key"],config["location"])
        voice=voice_control.Voice(c.devices_name,c.custom_devices,c,s,config["apikeys"]["wit_token"])
        c.yomiage=voice.yomiage
        s.yomiage=voice.yomiage
        voice.words.extend(["電気","天気","再生","停止","止めて","音"])
        def run():
            voice.always_on_voice()
        try:
            await asyncio.to_thread(run)
        except:pass
    async def always_on_voice():
        global voice
        text=""
        task=None
        while True:
                if voice.text!=text and voice.reply!="":
                    page.go("/voice")
                    talk_text.value=voice.text
                    reply.value=voice.reply
                    text=voice.text
                    page.update()
                    if not "わかりません" in reply.value:
                        await asyncio.sleep(30)
                    if task:
                        task.cancel()
                    task=asyncio.create_task(back())
                await asyncio.sleep(1)
    def route(e):
        page.views.clear()

        if page.route=="/":
            reply.value=""
            page.views.append(flet.View("/",[
                                            flet.Container(content=nowtime,expand=True,alignment=flet.alignment.center,on_click=menu)
                                            ],))
        if page.route=="/voice":
            page.views.append(flet.View("/voice",[flet.ElevatedButton("ホーム", on_click=lambda e:page.go("/")),
                                talk_text,
                                flet.Container(content=reply,expand=True,alignment=flet.alignment.center)

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
    page.run_task(listen)
    page.run_task(always_on_voice)
    page.go(page.route)
flet.app(target=main,port=5000)