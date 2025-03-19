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

    async def back(seconds=30):
        await asyncio.sleep(seconds)
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
        voice=voice_control.Voice(c.devices_name,c.custom_devices,c,s,config["apikeys"]["wit_token"],config["apikeys"]["genai"],config["url"]["server_url"])
        c.yomiage=voice.yomiage
        s.yomiage=voice.yomiage
        voice.words.extend(["電気","天気","再生","停止","止めて","ストップ","音","スキップ","戻","飛ばし","早送り","早戻し","秒","分","教","何","ですか","なに","とは","について","ますか"])
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
                if voice.text!=text and voice.reply!="" and not "わかりません"in voice.reply:
                    talk_text.value=voice.text
                    reply.value=voice.reply
                    text=voice.text
                    for name in ["ライト","テレビ"]:
                        if name in voice.reply:
                            page.go("/device_control")
                            break
                    else:
                        page.go("/voice")
                    page.update()
                    if task:
                        task.cancel()
                    else:
                        task=asyncio.create_task(back(30))
                await asyncio.sleep(1)
    def voice_screen(e):
        if page.window.full_screen==False:
            page.window.full_screen=True
        else:
            page.window.full_screen=False
    def control():
        icon=""
        color=""
        device_name=""
        action=""
        if "ライト" in voice.reply:
            icon=flet.Icons.LIGHTBULB
            device_name=["ライト"]
        if "テレビ" in voice.reply:
            icon=flet.Icons.TV
            device_name=["テレビ"]
        if "エアコン" in voice.reply:
            icon=flet.Icons.THERMOSTAT
            device_name=["エアコン"]
        if "オン" in voice.reply:
            color=flet.Colors.BLUE
            action="turnOff"
        if "オフ" in voice.reply:
            color=flet.Colors.RED
            action="turnOn"
        return icon,color,device_name,action
    def device_control(device_name,action):
        c.custom_device_control(device_name,action)
        c.switchbot_device_control(device_name,action)
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
                                            flet.ElevatedButton("フルスクリーン解除", on_click=voice_screen),
                                        ]))
        if page.route=="/device_control":
            icon,color,device_name,action=control()
            page.views.append(flet.View("/device_control",[flet.ElevatedButton("ホーム",on_click=lambda e:page.go("/")),
                                                           flet.Container(content=flet.IconButton(icon,icon_size=100,on_click=lambda e:device_control(device_name,action),icon_color=color,expand=True,alignment=flet.alignment.center),alignment=flet.alignment.center),
                                        ]))
        page.update()
    def test(e):
        page.go("/test")

    page.on_route_change=route
    page.on=menu

    page.run_task(time_update)
    page.run_task(listen)
    page.run_task(always_on_voice)
    page.window.full_screen=True
    page.go(page.route)
flet.app(target=main)