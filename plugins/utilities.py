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
            reply_text += f"{rss_title.text} の最新ニュースです "
            for item in items[:5]: #最新5件のニュースを取得
                    reply_text += f"{item.find('title').text} "
        command.reply_text = reply_text
        return super().execute(command)