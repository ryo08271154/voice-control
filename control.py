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
        print("menu")
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
        await asyncio.sleep(5)
        page.go("/")
    async def voice():
        try:
            await asyncio.to_thread(voice_control.always_on_voice)
        except:pass
    async def always_on_voice():
        text=""
        while True:
                if voice_control.last_text!=text and voice_control.reply!="":
                    page.go("/voice")
                    talk_text.value=voice_control.last_text
                    reply.value=voice_control.reply
                    text=voice_control.last_text
                    page.update()
                    task=asyncio.create_task(back())
                await asyncio.sleep(1)
    def route(e):
        page.views.clear()

        if page.route=="/":
            reply.value=""
            page.views.append(flet.View("/",[flet.ElevatedButton("テストページへ移動", on_click=test),
                                            flet.Row([flet.TextButton("音声認識",on_click=lambda e:page.go("/voice"))]),
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
    page.run_task(always_on_voice)
    page.run_task(voice)
    page.go(page.route)


flet.app(target=main,port=5000)