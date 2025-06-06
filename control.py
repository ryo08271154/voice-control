import flet
import datetime
import asyncio
import voice_control
import os
import threading
import random
voice=None
def main(page:flet.Page):
    def listen():
        import json
        dir_name=os.path.dirname(__file__)
        global voice,c
        custom_scenes=json.load(open(os.path.join(dir_name,"config","custom_scenes.json")))
        custom_devices=json.load(open(os.path.join(dir_name,"config","custom_devices.json")))
        config=json.load(open(os.path.join(dir_name,"config","config.json")))
        c=voice_control.Control(custom_devices,custom_scenes)
        voice=VoiceControl(c.custom_devices,c,config)
        voice.words.extend(["教","何","ですか","なに","とは","について","ますか"])
        def run(config):
            voice.always_on_voice(config["vosk"]["model_path"])
        try:
            run(config)
        except:pass
    def menu(e):
        page.go("/menu")
    page.theme_mode=flet.ThemeMode.DARK
    page.title="音声操作"
    nowtime = flet.Text(datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S"), size=100, text_align=flet.TextAlign.CENTER)
    talk_text=flet.Text("",size=50)
    reply=flet.Text("", size=100,text_align=flet.TextAlign.CENTER,expand=True)
    async def time_update():
        while True:
            nowtime.value =datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S")
            page.update()
            await asyncio.sleep(1)

    async def back(seconds=30):
        try:
            await asyncio.sleep(seconds)
            page.go("/")
        except asyncio.CancelledError:
            pass
    class VoiceControl(voice_control.VoiceControl):
        def yomiage(self, text=""):
            super().yomiage(text)
            result()
            page.run_task(back)
    def result():
        global voice
        talk_text.value=voice.text
        reply.value=voice.reply
        for name in ["をオン","をオフ"]:
            if name in voice.reply:
                page.go("/device_control")
                break
        else:
            page.go("/voice")
    def voice_screen(e):
        if page.window.full_screen==False:
            page.window.full_screen=True
            page.window.skip_task_bar=True
        else:
            page.window.full_screen=False
            page.window.skip_task_bar=True
    def control():
        icon=""
        color=""
        device_name=""
        action=""
        if "ライト" in voice.reply:
            icon=flet.Icons.LIGHTBULB
            device_name=["ライト"]
        elif "テレビ" in voice.reply:
            icon=flet.Icons.TV
            device_name=["テレビ"]
        elif "エアコン" in voice.reply:
            icon=flet.Icons.THERMOSTAT
            device_name=["エアコン"]
        else:
            icon=flet.Icons.DEVICE_UNKNOWN
        if "オン" in voice.reply:
            color=flet.Colors.BLUE
            action="turnOff"
        if "オフ" in voice.reply:
            color=flet.Colors.RED
            action="turnOn"
        return icon,color,device_name,action
    def device_control(device_name,action):
        global voice
        page.go("/")
        if action=="turnOn":
            set_action=device_name[0]+"オン"
        else:
            set_action=device_name[0]+"オフ"
        voice.command(set_action)
    def command(text):
        print(text)
        voice.text=text
        voice.command(text)
    def menu_list():
        data=None
        commands=["ライトをオン","ライトをオフ","テレビをオン","テレビをオフ","エアコンをオン","エアコンをオフ","今日の天気は","明日の天気は","再生","停止","早送り","早戻し","プログラミングについて教えて","今日のニュースは","最新のニュースを教えて","現在の時刻は","今日の日付は","今の気温は","湿度はどれくらい？","カレンダーの予定を教えて","為替レートを教えて","今日の運勢は？","今の風速は？","今日の日の出時間は？","今日の日の入り時間は？","今の気圧は？","明日の気温は？","今週の天気予報は？","今の月の満ち欠けは？","最新のスポーツニュースを教えて","今日の株価は？","ビットコインの価格は？","今日のおすすめの映画は？","今の交通情報を教えて","近くのレストランを教えて","現在の電車の遅延情報は？","今日の祝日は？","次の祝日は？","今日の記念日は？","今日の歴史的な出来事を教えて","有名人の誕生日は？","今日の名言を教えて","最新の技術ニュースは？","今日の為替変動は？","人気の音楽ランキングは？","最新のゲーム情報は？","近くのイベントを教えて","今の海水温は？","おすすめの観光地を教えて","今の紫外線指数は？","最新のファッションニュースは？","今日のおすすめの本は？","最近の宇宙ニュースは？","今日の星座占いは？","今日のラッキーカラーは？","最新の医療ニュースは？","今日の献立のおすすめは？","近くの病院を教えて","現在の飛行機の運航状況は？","今日の月齢は？","話題のアニメを教えて","今の地震情報は？"]
        data=flet.GridView(runs_count=1,max_extent=150,child_aspect_ratio=1.0,spacing=1,run_spacing=1)
        random_list=random.sample(commands,51)
        for i in random_list:
            data.controls.append(flet.ElevatedButton(i,on_click=lambda e, cmd=i: command(cmd)))
        return data
    def route(e):
        page.views.clear()

        if page.route=="/":
            reply.value=""
            page.views.append(flet.View("/",[
                                            flet.Container(content=nowtime,expand=True,alignment=flet.alignment.center,on_click=menu)
                                            ],))
        if page.route=="/voice":
            page.views.append(flet.View("/voice",[flet.ElevatedButton("ホーム", on_click=lambda e:page.go("/")),
                                                  flet.Container(content=talk_text, expand=True, alignment=flet.alignment.center),
                                                  flet.Container(content=reply,expand=True,alignment=flet.alignment.center)

                                ],scroll=flet.ScrollMode.HIDDEN))
        if page.route=="/menu":
            page.views.append(flet.View("/menu",[flet.ElevatedButton("ホーム",on_click=lambda e:page.go("/")),
                                            flet.ElevatedButton("フルスクリーン切り替え", on_click=voice_screen),
                                            menu_list(),
                                        ],scroll=flet.ScrollMode.HIDDEN))
        if page.route=="/device_control":
            icon,color,device_name,action=control()
            page.views.append(flet.View("/device_control",[flet.ElevatedButton("ホーム",on_click=lambda e:page.go("/")),
                                                           flet.Container(content=flet.IconButton(icon,icon_size=100,on_click=lambda e:device_control(device_name,action),icon_color=color,expand=True,alignment=flet.alignment.center),alignment=flet.alignment.center),
                                        ]))
        page.scroll=flet.ScrollMode.ALWAYS
        page.update()
    def test(e):
        page.go("/test")

    page.on_route_change=route
    page.on=menu
    page.run_task(time_update)
    # page.run_task(listen)
    l=threading.Thread(target=listen,daemon=True)
    l.start()
    page.window.skip_task_bar=True
    page.go(page.route)
flet.app(target=main,port=8000,view=flet.FLET_APP_WEB)