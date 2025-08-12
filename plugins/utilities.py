from plugin import BasePlugin

import time
import re

import random
class RandomPlugin(BasePlugin):
    name="Random"
    description="乱数を生成する"
    keywords=["乱数", "ランダム"]
    def execute(self, command):
        min_value = 1
        max_value = 100
        text=command.user_input_text
        text=text.replace("一", "1").replace("二", "2").replace("三", "3").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9").replace("十", "10").replace("百", "100")
        if "から" in command.user_input_text:
            value=command.user_input_text.split("から")
            if len(value)==2:
                min_value = int(re.sub(r"\D","",value[0]))
                max_value = int(re.sub(r"\D","",value[1]))
        random_number = random.randint(min_value, max_value)
        command.reply_text=f"{min_value}から{max_value}で乱数を生成しました。結果は {random_number} です"
        return super().execute(command)
class DicePlugin(BasePlugin):
    name="Dice"
    keywords=["サイコロ", "ダイス"]
    description="サイコロを振る"
    def execute(self, command):
        dice_number = random.randint(1, 6)
        command.reply_text=f"サイコロを振りました。結果は {dice_number} です"
        return super().execute(command)

import xml.etree.ElementTree as ET
import requests
class RSSPlugin(BasePlugin):
    name="RSS"
    description="RSSフィードを読み込む"
    keywords=["ニュース", "RSS"]
    required_config=["rss_urls"]
    def execute(self, command):
        config=self.get_config()
        rss_urls=config.get("rss_urls").split(",")
        if not rss_urls:
            command.reply_text = "RSSフィードのURLが設定されていません。"
            return command
        reply_text=""
        for url in rss_urls:
            rss_feed=requests.get(url)
            root=ET.fromstring(rss_feed.text)
            items=root.findall(".//item")
            rss_title=root.find("./channel/title")
            reply_text += f"{rss_title.text} からです "
            for item in items[:5]: #最新5件のニュースを取得
                    reply_text += f"{item.find('title').text} "
        command.reply_text = reply_text
        return super().execute(command)

import webbrowser
import urllib.parse
class SearchPlugin(BasePlugin):
    name="WebSearch"
    description="Webで検索する"
    keywords=["検索", "ウェブ","開"]
    def execute(self, command):
        text=command.user_input_text
        query=text.replace("検索","").replace("ウェブ","").replace("する","").replace("して","").replace("で","").replace("を","").replace("グーグル","").replace("Google","").replace("ユーチューブ","").replace("ティックトック","").replace("ツイッター","").replace("ウィキペディア","").replace("アマゾン","").replace("スポティファイ","").replace("マップ","").replace("地図","").replace("YouTube","").replace("TikTok","").replace("Twitter","").replace("Wikipedia","").replace("Amazon","").replace("Spotify","")
        search_url=None
        service_name=None
        if "YouTube" in text or "ユーチューブ" in text:
            search_url=f"https://www.youtube.com/results?search_query={query}"
            service_name="YouTube"
        elif "TikTok" in text or "ティックトック" in text:
            search_url=f"https://www.tiktok.com/search?q={query}"
            service_name="TikTok"
        elif "Twitter" in text or "ツイッター" in text:
            search_url=f"https://x.com/search?q={query}"
            service_name="Twitter"
        elif "Wikipedia" in text or "ウィキペディア" in text:
            search_url=f"https://ja.wikipedia.org/wiki/{query}"
            service_name="Wikipedia"
        elif "Amazon" in text or "アマゾン" in text:
            search_url=f"https://www.amazon.co.jp/s?k={query}"
            service_name="Amazon"
        elif "Spotify" in text or "スポティファイ" in text:
            search_url=f"https://open.spotify.com/search/{query}"
            service_name="Spotify"
        elif "マップ" in text or "地図" in text:
            search_url=f"https://www.google.com/maps/search/{query}"
            service_name="Google Maps"
        elif "Google" in text or "グーグル" in text:
            search_url=f"https://www.google.com/search?q={query}"
            service_name="Google"
        if ("開" in text or "ひら" in text):
            if search_url and service_name:
                url=urllib.parse.urlparse(search_url)
                webbrowser.open_new(f"{url.scheme}://{url.netloc}",autoraise=True)
                command.reply_text = f"{service_name}を開きます。"
            self.is_plugin_mode=False
            return super().execute(command)
        else:
            if not query:
                if self.is_plugin_mode==False:
                    command.reply_text="検索するキーワードを教えて下さい"
                    self.is_plugin_mode=True
                else:
                    self.is_plugin_mode=False
                    command.reply_text="検索キーワードが指定されていません。"
                return super().execute(command)
            if search_url is None and service_name is None:
                search_url=f"https://www.google.com/search?q={query}"
                service_name="Google"
            command.reply_text = f"{service_name}で「{query}」を検索します。"
            webbrowser.open_new(search_url,autoraise=True)
            self.is_plugin_mode=False
        return super().execute(command)
import subprocess
class AppLauncherPlugin(BasePlugin):
    name="AppLauncher"
    description="アプリを起動する"
    keywords=["起動", "開", "アプリ"]
    required_config=["apps"]
    def execute(self, command):
        config=self.get_config()
        apps=config.get("apps").split(",")
        text=command.user_input_text
        for app in apps:
            app_config=app.split(":")
            app_name=app_config[0]
            cmd=app_config[1]
            if app_name in text:
                subprocess.Popen(cmd,shell=True)
                command.reply_text=f"{app_name}を起動します。"
                return super().execute(command)
        return super().execute(command)
class TimerPlugin(BasePlugin):
    name="Timer"
    description="タイマーを設定する"
    keywords=["タイマー"]
    def execute(self, command):
        text=command.user_input_text
        if "消" in text or "けし" in text or "キャンセル" in text or "やめ" in text or "終" in text:
            command.reply_text="最後のタイマーをキャンセルしました。"
            self.notifications.pop(-1)
            return super().execute(command)
        elif "あと" in text or "残" in text:
            for notification in self.notifications:
                notification_time=notification.timestamp
                remaining_time=notification_time-time.time()
                command.reply_text+=f"タイマーはあと{int(remaining_time)}秒です。"
            return super().execute(command)
        minutes=0
        seconds=0
        text=text.replace("一", "1").replace("二", "2").replace("三", "3").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9").replace("十", "10").replace("百", "100")
        if "分" in text:
            minutes_match=re.search(r"(\d+)分",text)
            if minutes_match:
                minutes=int(minutes_match.group(1))
        if "秒" in text:
            seconds_match=re.search(r"(\d+)秒",text)
            if seconds_match:
                seconds=int(seconds_match.group(1))
        total_seconds=minutes*60+seconds
        if total_seconds > 0:
            command.reply_text=f"{minutes}分{seconds}秒のタイマーをセットしました。"
            self.add_notification(f"{minutes}分{seconds}秒のタイマーが終了しました。",timestamp=time.time()+total_seconds)
        else:
            if self.is_plugin_mode==False:
                command.reply_text="タイマーの時間を教えて下さい"
                self.is_plugin_mode=True
            else:
                self.is_plugin_mode=False
        return super().execute(command)