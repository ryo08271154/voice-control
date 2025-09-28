from plugin import BasePlugin
import datetime
import requests
import schedule
import flet as ft
import time
import threading
from commands import VoiceCommand


class WeatherPlugin(BasePlugin):
    name = "Weather"
    description = "OpenWeatherMapのAPIを使用して天気を取得する"
    keywords = ["天気", "予報", "晴れ", "雨", "くもり", "雪"]
    required_config = ["openweathermap_apikey", "latitude", "longitude"]

    def __init__(self, voice_control=None):
        super().__init__(voice_control)
        threading.Thread(target=self.run_pending_jobs, daemon=True).start()
        schedule.every().day.at("08:00").do(self.weather_notification)

    def run_pending_jobs(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def weather_notification(self):
        message = None
        command = self.execute(VoiceCommand("今日の天気"))
        if "大雨" in command.reply_text:
            message = "今日は大雨が予想されています。外出時は傘を持って出かけて十分に注意してください。"
        elif "雨" in command.reply_text:
            message = "今日は雨が降る可能性があります。外出時は傘を持って出かけてください。"
        elif "雷" in command.reply_text:
            message = "今日は雷雨の可能性があります。外出時は注意してください。"
        elif "雪" in command.reply_text:
            message = "今日は雪が降る可能性があります。外出時は暖かい服装で出かけてください。"
        if message:
            self.add_notification(message)

    def get_date(self, text):
        if "今日" in text:
            date = datetime.datetime.now()
        elif "明日" in text:
            date = datetime.datetime.now()+datetime.timedelta(days=1)
        elif "あさって" in text:
            date = datetime.datetime.now()+datetime.timedelta(days=2)
        else:
            date = None
        return date

    def execute(self, command):
        text = command.user_input_text
        config = self.get_config()
        openweathermap_apikey = config.get("openweathermap_apikey")
        latitude = config.get("latitude")
        longitude = config.get("longitude")
        date = self.get_date(text)
        tenki = ""
        row = ft.Row(alignment=ft.MainAxisAlignment.CENTER,
                     vertical_alignment=ft.MainAxisAlignment.CENTER, expand=True)
        if not openweathermap_apikey or not latitude or not longitude:
            tenki = "天気情報を取得するためのAPIキーまたは位置情報が設定されていません。"
        elif not date:
            tenki = "いつの天気を教えてほしいかわかりませんでした"
        else:
            weather_json = requests.get(
                f"https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&lang=ja&units=metric&appid={openweathermap_apikey}").json()
            for i in range(1, len(weather_json["list"])):
                dt_txt = datetime.datetime.strptime(
                    weather_json["list"][i]["dt_txt"], "%Y-%m-%d %H:%M:%S")
                if dt_txt.day == date.day:
                    row.controls.append(ft.Column(controls=[
                        ft.Text(f"{dt_txt.hour}時", size=20),
                        ft.Image(
                            src=f"http://openweathermap.org/img/wn/{weather_json['list'][i]['weather'][0]['icon']}@2x.png", width=80, height=80),
                        ft.Text(
                            f"{weather_json['list'][i]['main']['temp']}℃", size=20),
                        ft.Text(weather_json['list'][i]
                                ['weather'][0]['description'], size=15)
                    ], expand=True, alignment=ft.MainAxisAlignment.CENTER))
                    if tenki == "":
                        tenki = f'{date.day}日の{dt_txt.hour}時は{weather_json["list"][i]["main"]["temp"]}℃ {weather_json["list"][i]["weather"][0]["description"]} '
                    else:
                        tenki += f'{dt_txt.hour}時は{weather_json["list"][i]["main"]["temp"]}℃ {weather_json["list"][i]["weather"][0]["description"]} '
                elif dt_txt.day > date.day:
                    tenki += "でしょう"
                    command.flet_view = row
                    break
            else:
                tenki = "天気情報が見つかりませんでした"
        command.reply_text = tenki
        return command
