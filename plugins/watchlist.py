import requests
import pickle
from bs4 import BeautifulSoup
class WatchList:
    def __init__(self,server_url="http://127.0.0.1:8000"):
        self.server_url=server_url
        self.session=requests.session()
        self.cookies=self.load_cookies()
        self.session.cookies.update(self.cookies)
    def load_cookies(self):
        try:
            with open("config/watchlist_cookies.pkl", "rb") as f:
                cookies = pickle.load(f)
        except FileNotFoundError:
            cookies = {}
        return cookies
    def save_cookies(self,cookies):
        with open("config/watchlist_cookies.pkl", "wb") as f:
            pickle.dump(cookies, f)
    def account_login(self,username,password):
        try:
            csrf_token=self.session.get(f"{self.server_url}/accounts/login/").cookies.get("csrftoken")
            self.session.post(f"{self.server_url}/accounts/login/",data={"username":username,"password":password,"csrfmiddlewaretoken":csrf_token})
            print("ログインしました")
        except:
            print("ログインに失敗しました")
    def account_logout(self):
        try:
            csrf_token=self.session.get(f"{self.server_url}/").cookies.get("csrftoken")
            self.session.post(f"{self.server_url}/accounts/logout/",data={"csrfmiddlewaretoken":csrf_token})
            print("ログアウトしました")
        except:
            print("ログアウトに失敗しました")
    def login_check(self,username="",password=""):
        try:
            index=self.session.get(self.server_url)
            if index.history:
                print("ログイン中")
                if username and password:
                    self.account_login(username,password)
                    self.save_cookies(self.session.cookies)
                else:
                    print("ログイン情報がありません")
                    return False
            else:
                print("ログイン済み")
            return True
        except Exception as e:
            print(f"ログインチェックに失敗しました: {e}")
            return False
    def search(self,keyword,type=""):
        params={"q":keyword,"type":type}
        if type=="":
            del params["type"]
        response=self.session.get(f"{self.server_url}/search",params=params)
        return response
    def review_search(self,keyword):
        response=self.search(keyword,"record")
        soup=BeautifulSoup(response.text,"html.parser")
        count=soup.find("div",class_="title-section").find("p").text
        reviews=soup.find_all("a",class_="title-item")
        reply_text=""
        for review in reviews[:5]:
            title=review.find("p").text
            review_title=review.find("h3").text
            reply_text+=f"タイトル{title}の{review_title} "
        reply_text+=f"の{count}の視聴記録が見つかりました。"
        return reply_text
    def monthly_review(self):
        response=self.session.get(f"{self.server_url}/mypage/reviews")
        soup=BeautifulSoup(response.text,"html.parser")
        reviews=soup.find("div",class_="title-section").find("div",class_="title-container").find_all("a",class_="title-item")
        count=len(reviews)
        reply_text="今月は"
        for review in reviews:
            title=review.find("p").text
            review_title=review.find("h3").text
            reply_text+=f"タイトル{title}の{review_title} "
        reply_text+=f"の{count}件の視聴記録が見つかりました。"
        return reply_text
    def today_episodes(self):
        response=self.session.get(self.server_url)
        soup=BeautifulSoup(response.text,"html.parser")
        for topics in soup.find_all("div",class_="title-section"):
            if topics.find("h2").text=="24時間以内に放送されたエピソード":
                episodes=topics.find_all("a",class_="title-item")
                count=len(episodes)
                reply_text="24時間以内に放送されたエピソードは"
                for episode in episodes:
                    data=episode.find_all("p")
                    title=data[1].text
                    air_date=data[0].text
                    episode_title=episode.find("div",class_="episode-item").find("h3").text
                    reply_text+=f"タイトル{title}の{episode_title} "
                reply_text+=f"の{count}件です。"
                return reply_text
        else:
            return "24時間以内に放送されたエピソードが見つかりませんでした"
    def watch_schedule(self):
        response=self.session.get(f"{self.server_url}/watch_schedule")
        soup=BeautifulSoup(response.text,"html.parser")
        reply_text=""
        for day in soup.find_all("div",class_="title-section"):
            date=day.find("h2").text
            reply_text+=f"{date}に放送予定のエピソードは"
            episodes=day.find("div",class_="title-container").find_all("a",class_="title-item")
            count=len(episodes)
            for episode in episodes:
                data=episode.find_all("p")
                title=data[1].text
                reply_text+=f"タイトル{title} "
                reply_text+=f"の{count}です。"
        return reply_text
from plugin import BasePlugin
class WatchListPlugin(BasePlugin):
    name="watchlist"
    description="視聴記録(https://github.com/ryo08271154/watchlist)専用のプラグイン"
    keywords=["視聴記録","リスト","見た","見てる","見る","視聴"]
    required_config=["server_url","username","password"]
    session=WatchList()
    def execute(self, command):
        config=self.get_config()
        self.session.server_url=config.get("server_url")
        username=config.get("username")
        password=config.get("password")
        self.session.login_check(username,password)
        if "今月" in command.user_input_text:
            reply_text=self.session.monthly_review()
        elif "今日" in command.user_input_text:
            reply_text=self.session.today_episodes()
        elif "予定" in command.user_input_text:
            reply_text=self.session.watch_schedule()
        elif "視聴" in command.user_input_text or "見た" in command.user_input_text or "検索" in command.user_input_text:
            keyword=command.user_input_text.replace("視聴記録","").replace("見た","").replace("検索","").replace("の","").replace("で","").replace("して","")
            reply_text=self.session.review_search(keyword)
        else:
            reply_text="視聴記録の何を検索するかわかりませんでした"
        command.reply_text=reply_text
        return super().execute(command)