from plugin import BasePlugin
import datetime
import requests
class WeatherPlugin(BasePlugin):
    name="Weather"
    description="OpenWeatherMapのAPIを使用して天気を取得する"
    keywords=["天気", "予報", "晴れ", "雨", "くもり", "雪"]
    required_config=["openweathermap_apikey", "latitude", "longitude"]
    def get_date(self,text):
        if "今日" in text:
            date=datetime.datetime.now()
        elif "明日" in text:
            date=datetime.datetime.now()+datetime.timedelta(days=1)
        elif "あさって" in text:
            date=datetime.datetime.now()+datetime.timedelta(days=2)
        else:
            date=None
        return date
    def execute(self,command):
        text=command.user_input_text
        config=self.get_config()
        openweathermap_apikey=config.get("openweathermap_apikey")
        latitude=config.get("latitude")
        longitude=config.get("longitude")
        date=self.get_date(text)
        tenki=""
        if not openweathermap_apikey or not latitude or not longitude:
            tenki="天気情報を取得するためのAPIキーまたは位置情報が設定されていません。"
        elif not date:
            tenki="いつの天気を教えてほしいかわかりませんでした"
        elif datetime.datetime.now().day==date.day:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&lang=ja&units=metric&appid={openweathermap_apikey}").json()
            tenki=f"現在の気温は{weather_json['main']['temp']}℃ 天気は{weather_json['weather'][0]['description']}です"
        else:
            weather_json=requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&lang=ja&units=metric&appid={openweathermap_apikey}").json()
            get_date=datetime.datetime.strftime(date,"%Y-%m-%d")
            for i in range(1,len(weather_json["list"])):
                if weather_json["list"][i]["dt_txt"]==f"{get_date} 09:00:00":
                    tenki=f'{date.day}日の９時の気温は{weather_json["list"][i]["main"]["temp"]}℃ 天気は{weather_json["list"][i]["weather"][0]["description"]} '
                    tenki+=f'１２時の気温は{weather_json["list"][i+1]["main"]["temp"]}℃ 天気は{weather_json["list"][i+1]["weather"][0]["description"]} '
                    tenki+=f'１５時の気温は{weather_json["list"][i+2]["main"]["temp"]}℃ 天気は{weather_json["list"][i+2]["weather"][0]["description"]}でしょう'
                    break
            else:
                tenki="天気情報が見つかりませんでした"
        command.reply_text=tenki
        return command