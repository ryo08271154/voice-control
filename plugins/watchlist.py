import requests
import pickle
from bs4 import BeautifulSoup
server_url="http://localhost:8000"
def load_cookies():
    try:
        with open("config/watchlist_cookies.pkl", "rb") as f:
            cookies = pickle.load(f)
    except FileNotFoundError:
        cookies = {}
    return cookies
def save_cookies(cookies):
    with open("config/watchlist_cookies.pkl", "wb") as f:
        pickle.dump(cookies, f)
def account_login(username,password):
    try:
        csrf_token=session.get(f"{server_url}/accounts/login/").cookies.get("csrftoken")
        session.post(f"{server_url}/accounts/login/",data={"username":username,"password":password,"csrfmiddlewaretoken":csrf_token})
        print("ログインしました")
    except:
        print("ログインに失敗しました")
def account_logout():
    try:
        csrf_token=session.get(f"{server_url}/").cookies.get("csrftoken")
        session.post(f"{server_url}/accounts/logout/",data={"csrfmiddlewaretoken":csrf_token})
        print("ログアウトしました")
    except:
        print("ログアウトに失敗しました")
def login_check(session,username="",password=""):
    try:
        index=session.get(server_url)
        if index.history:
            print("ログイン中")
            if username and password:
                account_login(username,password)
                save_cookies(session.cookies)
            else:
                print("ログイン情報がありません")
        else:
            print("ログイン済み")
        return session
    except:
        print("ログインチェックに失敗しました")
def search(keyword,type=""):
    params={"q":keyword,"type":type}
    if type=="":
        del params["type"]
    response=session.get(f"{server_url}/search",params=params)
    return response
def review_search(keyword):
    response=search(keyword,"record")
    soup=BeautifulSoup(response.text,"html.parser")
    count=soup.find("div",class_="title-section").find("p").text
    reviews=soup.find_all("a",class_="title-item")
    reply_text=""
    for review in reviews:
        title=review.find("p").text
        review_title=review.find("h3").text
        reply_text+=f"タイトル{title}の{review_title} "
    reply_text+=f"の{count}の視聴記録が見つかりました。"
    return reply_text
def monthly_review():
    response=session.get(f"{server_url}/mypage/reviews")
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
session=requests.session()
cookies=load_cookies()
session.cookies.update(cookies)
from plugin import BasePlugin
class WatchListPlugin(BasePlugin):
    name="watchlist"
    description="視聴記録(https://github.com/ryo08271154/watchlist)専用のプラグイン"
    keywords=["視聴記録","リスト","見た","見てる","視聴","いつ"]
    required_config=["server_url","username","password"]
    def execute(self, command):
        global server_url,session
        config=self.get_config()
        server_url=config.get("server_url")
        username=config.get("username")
        password=config.get("password")
        session=login_check(session,username,password)
        if "今月" in command.user_input_text:
            reply_text=monthly_review()
        elif "視聴" in command.user_input_text or "見た" in command.user_input_text or "検索" in command.user_input_text:
            keyword=command.user_input_text.replace("視聴記録","").replace("見た","").replace("検索","").replace("の","").replace("で","").replace("して","")
            reply_text=review_search(keyword)
        else:
            reply_text="視聴記録の何を検索するかわかりませんでした"
        command.reply_text=reply_text
        return super().execute(command)