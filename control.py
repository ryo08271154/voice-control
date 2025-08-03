import flet
import datetime
import asyncio
import voice_control
import os
import threading
import random
import time
import pychromecast
import lyricsgenius
voice=None
l=None
chromecasts, browser = pychromecast.get_chromecasts()
def main(page:flet.Page):
    def listen():
        try:
            import json
            dir_name=os.path.dirname(__file__)
            global voice,c,l
            custom_scenes=json.load(open(os.path.join(dir_name,"config","custom_scenes.json")))
            custom_devices=json.load(open(os.path.join(dir_name,"config","custom_devices.json")))
            config=json.load(open(os.path.join(dir_name,"config","config.json")))
            c=voice_control.Control(custom_devices,custom_scenes)
            voice=VoiceControl(c.custom_devices,c,config)
            voice.words.extend(["教","何","ですか","なに","とは","について","ますか","して","開いて"])
            def run(config):
                voice.always_on_voice(config["vosk"]["model_path"])
            run(config)
        except Exception as e:
            print(f"音声認識の初期化中にエラーが発生しました: {e}")
    def menu(e):
        page.go("/menu")
    page.theme_mode=flet.ThemeMode.DARK
    page.title="音声操作"
    nowtime = flet.Text(datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S"), size=100, text_align=flet.TextAlign.CENTER)
    talk_text=flet.Text("",size=50)
    reply=flet.Text("", size=100,text_align=flet.TextAlign.CENTER,expand=True)
    async def update_time():
        while True:
            nowtime.value =datetime.datetime.now().strftime("%Y/%m/%d\n%H:%M:%S")
            if page.route=="/":
                page.update()
            await asyncio.sleep(1)

    async def back(seconds=30):
        try:
            await asyncio.sleep(seconds)
            if current_time>0:
                page.go("/media")
            else:
                page.go("/")
        except asyncio.CancelledError:
            pass
    def get_chromecast_status():
        global is_playing,current_time,max_time,media_icon,media_info_text,playing_title,playing_artist,lyrics_text_list
        try:
            for cast in chromecasts:
                cast.wait()
                if cast.status.app_id != None:
                    mc=cast.media_controller
                    mc.block_until_active()
                    is_playing=mc.status.player_is_playing
                    current_time=mc.status.adjusted_current_time
                    max_time=mc.status.duration
                    media_icon.src=mc.status.images[0].url if mc.status.images else ""
                    playing_title=mc.status.title
                    playing_artist=mc.status.artist
                    media_info_text.value= f"{mc.status.title} - {mc.status.artist}"
                    if page.route=="/media":
                        page.update()
                    break
            else:
                is_playing=False
                current_time=0
                max_time=0
                media_icon.src=""
                media_info_text.value=""
                if page.route=="/media":
                    page.update()
                    page.go("/")
        except:
            pass
    async def update_chromecast_status():
        global media_icon,media_info_text,current_time,max_time,is_playing,lyrics_text_list,playing_title,playing_artist
        media_icon=flet.Image(width=150, height=150, fit=flet.ImageFit.CONTAIN)
        media_info_text=flet.Text(size=30, text_align=flet.TextAlign.CENTER,bgcolor=flet.Colors.BLACK)
        lyrics_text_list=flet.ListView(auto_scroll=True)
        playing_title=""
        playing_artist=""
        while True:
            get_chromecast_status()
            await asyncio.sleep(30)
    async def playback_progress_update():
        global current_time, playback_progress,playback_progress_time,is_playing,lyrics
        playback_progress = flet.ProgressBar(width=600, value=0)
        while True:
            if is_playing==True:
                current_time+=1
            else:
                await asyncio.sleep(1)
                continue
            if current_time is None or max_time is None:
                await asyncio.sleep(1)
                continue
            if current_time > max_time:
                current_time = 0
                get_chromecast_status()
            playback_progress_time= current_time / max_time if current_time > 0  and max_time > 0 else 0
            playback_progress.value=playback_progress_time
            if page.route=="/media":
                page.update()
            await asyncio.sleep(1)
    def get_lyrics():
        global lyrics_text_list
        if playing_artist and playing_title:
            try:
                token=voice.config.get("genius",{}).get("token")
                genius=lyricsgenius.Genius(token)
                song=genius.search_song(playing_title,playing_artist)
                if song:
                    return song.lyrics.splitlines()
                else:
                    return ["歌詞が見つかりませんでした"]
            except:
                return ["エラーが発生しました"]
        else:
            return ["歌詞を取得できません"]
    async def update_lyrics():
        global lyrics_text_list,lyrics
        def update():
            global lyrics_text_list
            lyrics_text_list.controls.clear()
            lyrics=get_lyrics()
            if len(lyrics)==1: #取得できなかったとき
                interval=0.1
            else:
                interval = max_time / len(lyrics) -0.5
            temp_playing_title=playing_title
            return lyrics,temp_playing_title,interval
        lyrics,temp_playing_title,interval=update()
        line=0
        while True:
            if temp_playing_title!=playing_title:
                lyrics,temp_playing_title,interval=update()
                line=0
            while current_time // interval > len(lyrics_text_list.controls) and line < len(lyrics):
                lyrics_text=flet.Text(size=40, text_align=flet.TextAlign.CENTER, color=flet.Colors.WHITE54)
                lyrics_text.value = lyrics[line]
                lyrics_text_list.controls.append(lyrics_text)
                line+=1
            while current_time // interval < len(lyrics_text_list.controls):
                line-=1
                lyrics_text_list.controls.pop(-1)
            if page.route=="/media":
                page.update()
            await asyncio.sleep(0.8)
    class VoiceControl(voice_control.VoiceControl):
        def yomiage(self, commands):
            result(commands[0])
            super().yomiage(commands)
            page.run_task(back)
    def result(v):
        global voice
        talk_text.value=v.user_input_text
        reply.value=v.reply_text
        voice.reply=v.reply_text
        for name in ["をオン","をオフ"]:
            if name in v.reply_text:
                page.go("/device_control")
                break
        else:
            page.go("/voice")
    def voice_screen(e):
        if page.window.full_screen==False:
            page.window.full_screen=True
            page.window.skip_task_bar=True
        else: # フルスクリーンを解除する場合
            page.window.full_screen=False
            page.window.skip_task_bar=True
    def control():
        icon=flet.Icons.DEVICE_UNKNOWN
        color=""
        device_name=["不明なデバイス"]
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
        if "オン" in voice.reply:
            color=flet.Colors.BLUE
            action="turnOff"
        if "オフ" in voice.reply:
            color=flet.Colors.RED
            action="turnOn"
        return icon,color,device_name,action
    def device_control(device_name,action):
        global voice
        page.go("/") # デバイス操作後、ホーム画面に戻る
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
        data = None
        commands = ["ライトをオン", "ライトをオフ","テレビをオン","テレビをオフ","エアコンをオン","エアコンをオフ","今日の天気は","明日の天気は","再生","停止","早送り","早戻し","プログラミングについて教えて","今日のニュースは","最新のニュースを教えて","現在の時刻は","今日の日付は","今の気温は","湿度はどれくらい？","カレンダーの予定を教えて","為替レートを教えて","今日の運勢は？","今の風速は？","今日の日の出時間は？","今日の日の入り時間は？","今の気圧は？","明日の気温は？","今週の天気予報は？","今の月の満ち欠けは？","最新のスポーツニュースを教えて","今日の株価は？","ビットコインの価格は？","今日のおすすめの映画は？","今の交通情報を教えて","近くのレストランを教えて","現在の電車の遅延情報は？","今日の祝日は？","次の祝日は？","今日の記念日は？","今日の歴史的な出来事を教えて","有名人の誕生日は？","今日の名言を教えて","最新の技術ニュースは？","今日の為替変動は？","人気の音楽ランキングは？","最新のゲーム情報は？","近くのイベントを教えて","今の海水温は？","おすすめの観光地を教えて","今の紫外線指数は？","最新のファッションニュースは？","今日のおすすめの本は？","最近の宇宙ニュースは？","今日の星座占いは？","今日のラッキーカラーは？","最新の医療ニュースは？","今日の献立のおすすめは？","近くの病院を教えて","現在の飛行機の運航状況は？","今日の月齢は？","話題のアニメを教えて","今の地震情報は？"] # 例示コマンドリスト
        data = flet.GridView(
            runs_count=1,
            max_extent=150,
            child_aspect_ratio=1.0,
            spacing=1,
            run_spacing=1,
            controls=[]
        )
        random_list = random.sample(commands, 51)
        for i in random_list:
            data.controls.append(flet.ElevatedButton(i, on_click=lambda e, cmd=i: command(cmd)))
        return data
    def device_control_panel():
            devices = []
            for device in voice.custom_devices_name:
                devices.append({"name": device, "icon": flet.Icons.DEVICES})
            from plugins.switchbot import switchbot
            for i in switchbot.devices["body"]["infraredRemoteList"]:
                device_name=i["deviceName"]
                icon=flet.Icons.DEVICE_UNKNOWN
                if "ライト" in device_name or "電気" in device_name:
                    icon=flet.Icons.LIGHTBULB
                elif "テレビ" in device_name:
                    icon=flet.Icons.TV
                elif "エアコン" in device_name:
                    icon=flet.Icons.THERMOSTAT
                devices.append({"name": device_name, "icon": icon})
            for i in switchbot.scenes["body"]:
                devices.append({"name": i["sceneName"], "icon": flet.Icons.DEVICES_OTHER})
            grid = flet.GridView(
                expand=True,
                runs_count=2,
                max_extent=200,  # カードの最大幅を増やす
                child_aspect_ratio=1.2,  # アスペクト比を調整
                spacing=10,
                run_spacing=10
            )
            for device in devices:
                grid.controls.append(
                    flet.Card(
                        content=flet.Container(
                            content=flet.Column(
                                [
                                    flet.Icon(device["icon"], size=40),
                                    flet.Text(
                                        device["name"],
                                        size=16,
                                        text_align=flet.TextAlign.CENTER,
                                        width=180,  # テキストの最大幅を設定
                                        max_lines=2,  # 最大2行まで表示
                                        overflow=flet.TextOverflow.ELLIPSIS  # 長すぎる場合は省略
                                    ),
                                    flet.Row(
                                        [
                                            flet.ElevatedButton(
                                                "ON",
                                                width=70,  # ボタンの幅を固定
                                                on_click=lambda e, d=device: command(f"{d['name']}をオン")
                                            ),
                                            flet.ElevatedButton(
                                                "OFF",
                                                width=70,  # ボタンの幅を固定
                                                on_click=lambda e, d=device: command(f"{d['name']}をオフ")
                                            )
                                        ],
                                        alignment=flet.MainAxisAlignment.CENTER,
                                        spacing=10
                                    )
                                ],
                                horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                                spacing=10
                            ),
                            padding=15
                        )
                    )
                )
            return grid
    def media_control_action(action):
        global current_time,is_playing
        try:
            for cast in chromecasts:
                cast.wait()
                if cast.status.app_id != None:
                    mc=cast.media_controller
                    mc.block_until_active()
                    if action=="play":
                        mc.play()
                        is_playing=True
                    elif action=="pause":
                        mc.pause()
                        is_playing=False
                    elif action=="stop":
                        mc.stop()
                        is_playing=False
                    elif action=="rewind":
                        current_time-=10
                        mc.seek(current_time)
                    elif action=="forward":
                        current_time+=10
                        mc.seek(current_time)
                    elif action=="previous":
                        mc.queue_prev()
                        time.sleep(1)
                        get_chromecast_status()
                    elif action=="next":
                        mc.queue_next()
                        time.sleep(1)
                        get_chromecast_status()
                    break
        except:
            pass
    def route(e):
        page.views.clear()

        if page.route=="/":
            reply.value=""
            nowtime.size=100
            page.views.append(flet.View("/",[
                                            flet.Container(content=nowtime,expand=True,alignment=flet.alignment.center,on_click=menu)
                                            ],))
        if page.route=="/voice":
            page.views.append(flet.View("/voice",[flet.ElevatedButton("ホーム", on_click=lambda e:page.go("/")),
                                                  flet.Container(content=talk_text, expand=True, alignment=flet.alignment.center),
                                                  flet.Container(content=reply,expand=True,alignment=flet.alignment.center)

                                ],scroll=flet.ScrollMode.HIDDEN))
        if page.route=="/menu":
            page.views.append(flet.View("/menu",[
                flet.ElevatedButton("ホーム",on_click=lambda e:page.go("/")),
                flet.ElevatedButton("デバイス一覧", on_click=lambda e: page.go("/devices")),
                flet.ElevatedButton("メディア操作", on_click=lambda e: page.go("/media")), # メディア操作ボタンを追加
                flet.ElevatedButton("ヘルプ", on_click=lambda e: page.go("/help")),
                flet.ElevatedButton("設定", on_click=lambda e: page.go("/settings")),
                menu_list(),
            ],scroll=flet.ScrollMode.HIDDEN))
        if page.route=="/device_control":
            icon,color,device_name,action=control()
            page.views.append(flet.View("/device_control",[flet.ElevatedButton("ホーム",on_click=lambda e:page.go("/")),
                flet.Container(content=flet.IconButton(icon,icon_size=100,on_click=lambda e:device_control(device_name,action),icon_color=color,expand=True,alignment=flet.alignment.center),alignment=flet.alignment.center),
            ]))
        if page.route == "/devices":
            page.views.append(
                flet.View("/devices",
                    [
                        flet.ElevatedButton("ホーム", on_click=lambda e: page.go("/")),
                        flet.Text("デバイス一覧", size=30, weight=flet.FontWeight.BOLD),
                        device_control_panel()
                    ]
                )
            )
        if page.route == "/help":
            page.views.append(
                flet.View(
                    "/help",
                    [
                        flet.ElevatedButton("ホーム", on_click=lambda e: page.go("/")),
                        flet.Text("使い方", size=30, weight=flet.FontWeight.BOLD),
                        flet.Text("1. 画面をタップしてメニューを開く\n2. 音声コマンドを話すか、メニューから選択\n3. 「ライトをオン」などの機器操作\n4. 「今日の天気は」などの質問\n5. 「〇〇について教えて」などの会話", size=20),
                        flet.Text("コマンド例", size=30, weight=flet.FontWeight.BOLD),
                        flet.Text("・機器操作: ライト/テレビ/エアコン + オン/オフ\n・情報取得: 天気、時刻、ニュース\n・会話: プログラミング、技術、スポーツなど", size=20),
                    ],
                )
            )

        if page.route == "/settings":
            page.views.append(
                flet.View(
                    "/settings",
                    [
                        flet.ElevatedButton("ホーム", on_click=lambda e: page.go("/")),
                        flet.Text("設定", size=30, weight=flet.FontWeight.BOLD),
                        flet.Switch(label="フルスクリーンモード", value=page.window.full_screen, on_change=voice_screen),
                    ],
                )
            )
        # メディア操作画面を追加
        if page.route == "/media":
            nowtime.size=20
            page.views.append(
            flet.View(
                "/media",
                [
                    flet.ElevatedButton("ホーム", on_click=lambda e: page.go("/")),
                    nowtime,
                    flet.Stack(
                        controls=[
                            # 上中央に固定する部分
                            flet.Container(
                                content=flet.Column(
                                    [
                                        media_icon,
                                        media_info_text,
                                        flet.Container(height=120),
                                    ],
                                    horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                                    spacing=5,
                                ),
                                alignment=flet.alignment.top_center,
                                padding=flet.padding.only(top=20),
                            ),

                            # 残りのスクロール可能なメインコンテンツ
                            flet.Container(
                                content=flet.Column(
                                    [
                                        flet.Container(height=200),  # 上のアイコン表示分のスペースを空ける
                                        flet.Container(
                                            content=lyrics_text_list,
                                            expand=True,
                                            alignment=flet.alignment.center,
                                        ),
                                        flet.Container(
                                            content=playback_progress,
                                            padding=flet.padding.symmetric(vertical=10)
                                        ),
                                        flet.Container(
                                            content=flet.Row(
                                                [
                                                    flet.IconButton(icon=flet.Icons.PLAY_ARROW, icon_size=60, on_click=lambda e: media_control_action("play")),
                                                    flet.IconButton(icon=flet.Icons.PAUSE, icon_size=60, on_click=lambda e: media_control_action("pause")),
                                                    flet.IconButton(icon=flet.Icons.STOP, icon_size=60, on_click=lambda e: media_control_action("stop")),
                                                    flet.IconButton(icon=flet.Icons.FAST_REWIND, icon_size=60, on_click=lambda e: media_control_action("rewind")),
                                                    flet.IconButton(icon=flet.Icons.FAST_FORWARD, icon_size=60, on_click=lambda e: media_control_action("forward")),
                                                    flet.IconButton(icon=flet.Icons.SKIP_PREVIOUS, icon_size=60, on_click=lambda e: media_control_action("previous")),
                                                    flet.IconButton(icon=flet.Icons.SKIP_NEXT, icon_size=60, on_click=lambda e: media_control_action("next")),
                                                ],
                                                alignment=flet.MainAxisAlignment.CENTER,
                                                spacing=30
                                            ),
                                            alignment=flet.alignment.bottom_center,
                                            padding=flet.padding.only(bottom=20)
                                        )
                                    ],
                                    alignment=flet.MainAxisAlignment.START,
                                    horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                                    expand=True
                                ),
                                expand=True,
                                padding=flet.padding.symmetric(horizontal=20)
                            )
                        ],
                        expand=True
                    )
                ],
                vertical_alignment=flet.MainAxisAlignment.START,
                horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                scroll=None
            )
            )

        # page.scroll=flet.ScrollMode.ALWAYS
        page.update()
    global l
    if not l:
        l=threading.Thread(target=listen,daemon=True)
        l.start()
    else:
        return page.window.destroy()
    while not voice:
        time.sleep(1)
    # イベントハンドラの登録
    page.on_route_change=route
    page.on_click=menu # 画面クリックでメニューに遷移
    page.run_task(update_time) # 時刻更新タスクを開始
    page.run_task(update_chromecast_status)
    global current_time,max_time,is_playing
    current_time=0
    max_time=0
    is_playing=False
    page.run_task(playback_progress_update)
    page.run_task(update_lyrics)  # 歌詞更新タスクを開始
    page.go(page.route)
flet.app(target=main)