from plugin import BasePlugin
import threading
import time
import flet as ft
import schedule
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError


class GAuth:
    def __init__(self, path):
        self.path = path
        self.token = os.path.join(self.path, "google_token.json")
        self.credentials = os.path.join(self.path, "google_credentials.json")

    def auth(self, scopes, service_name, version):
        creds = None
        if os.path.exists(self.token):
            creds = Credentials.from_authorized_user_file(self.token, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    creds = None
                except:
                    creds = None
                    print("認証に失敗しました")
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials, scopes
                )
                creds = flow.run_local_server(port=0)
        with open(self.token, "w") as token:
            token.write(creds.to_json())

        try:
            return build(service_name, version, credentials=creds)
        except HttpError as error:
            print(f"An error occurred: {error}")


class Calendar(GAuth):
    def __init__(self, path):
        super().__init__(path)
        if not os.path.exists(self.credentials):
            print("Google の認証情報ファイルが見つかりません。google_credentials.json が見つかりません。Google Cloud Platform で認証情報を作成し、このファイルに保存してください。")
            self.service = None
        else:
            self.service = self.auth(scopes=["https://www.googleapis.com/auth/calendar.readonly",
                                     "https://www.googleapis.com/auth/tasks.readonly"], service_name="calendar", version="v3")

    def get_events(self, date=datetime.datetime.now()):
        time_min = date.astimezone(datetime.timezone.utc)
        time_max = time_min+datetime.timedelta(days=1)
        time_min = time_min.isoformat()
        time_max = time_max.isoformat()
        calendar_list = self.service.calendarList().list().execute()
        all_events = []
        for calendar_entry in calendar_list.get("items", []):
            calendar_id = calendar_entry["id"]
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            all_events.extend(events)
        all_events = sorted(all_events, key=lambda x: datetime.datetime.fromisoformat(
            x["start"].get("dateTime", x["start"].get("date"))).replace(tzinfo=datetime.timezone.utc))
        return all_events


class CalendarPlugin(BasePlugin):
    name = "Calendar"
    description = "Google Calendar APIを使用して予定を取得する"
    keywords = ["カレンダー", "スケジュール", "予定"]

    def __init__(self, voice_control=None):
        super().__init__(voice_control)
        self.gcalendar = Calendar(self.config_dir)
        threading.Thread(target=self.run_pending_jobs, daemon=True).start()
        self.set_today_events()
        schedule.every().day.at("06:00").do(self.set_today_events)

    def run_pending_jobs(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def set_today_events(self):
        date = datetime.datetime.now()
        today_events = self.gcalendar.get_events(date)
        for event in today_events:
            event_date = datetime.datetime.fromisoformat(
                event["start"].get("dateTime", event["start"].get("date")))
            event_title = event.get("summary", "タイトルなし")
            if event_date.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9))) <= datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))):
                continue
            self.add_notification(
                f"{event_title}の予定が1時間後にあります", timestamp=event_date.timestamp()-3600)  # 1時間前
            self.add_notification(
                f"{event_title}の予定が30分後にあります", timestamp=event_date.timestamp()-1800)  # 30分前

    def execute(self, command):
        text = command.user_input_text
        if "今日" in text:
            date = datetime.datetime.now()
        elif "明日" in text:
            date = datetime.datetime.now()+datetime.timedelta(days=1)
        elif "あさって" in text:
            date = datetime.datetime.now()+datetime.timedelta(days=2)
        else:
            date = None
        if "明日" in text or "あさって" in text:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if date:
            all_events = self.gcalendar.get_events(date)
            if not all_events:
                command.reply_text = "予定が見つかりませんでした"
                return super().execute(command)
            lv = ft.ListView(spacing=10, padding=20, expand=True)
            command.reply_text = f"{date.day}日の予定は"
            for event in all_events:
                start = datetime.datetime.fromisoformat(
                    event["start"].get("dateTime", event["start"].get("date")))
                event_name = event.get("summary", "タイトルなし")
                command.reply_text += f"{start.hour}時{start.minute}分{event_name} "
                lv.controls.append(ft.Container(content=ft.Column([ft.Text(event_name, size=20), ft.Text(
                    f"{start.hour}時{start.minute}分")]), bgcolor=ft.Colors.WHITE10, padding=10, border_radius=5))
            command.reply_text += "です"
            command.flet_view = lv
        else:
            command.reply_text = "いつの予定を教えてほしいかわかりませんでした"
        return super().execute(command)


class Tasks(GAuth):
    def __init__(self, path):
        super().__init__(path)
        self.service = self.auth(scopes=["https://www.googleapis.com/auth/tasks.readonly",
                                 "https://www.googleapis.com/auth/calendar.readonly"], service_name="tasks", version="v1")

    def get_todos(self, date=datetime.datetime.now()):
        task_lists = self.service.tasklists().list(maxResults=10).execute()
        tasks = []
        for task_list in task_lists.get("items", []):
            tasklist_id = task_list["id"]
            tasks.extend(self.service.tasks()
                         .list(
                tasklist=tasklist_id,
                dueMin=datetime.datetime.now().astimezone(datetime.timezone.utc).isoformat(),
                showCompleted=False,
                showDeleted=False,
                showHidden=False,
                maxResults=10,
            )
                .execute()["items"]
            )
        tasks = sorted(
            tasks, key=lambda x: datetime.datetime.fromisoformat(x["due"]))
        return tasks


class TasksPlugin(BasePlugin):
    name = "Tasks"
    description = "Google Tasks APIを使用してタスクを取得する"
    keywords = ["タスク", "作業", "宿題", "課題"]

    def __init__(self, voice_control=None):
        super().__init__(voice_control)
        self.tasks = Tasks(self.config_dir)
        
    def execute(self, command):
        text = command.user_input_text
        todos = self.tasks.get_todos()
        if not todos:
            command.reply_text = "タスクが見つかりませんでした"
            return super().execute(command)
        command.reply_text = "タスクは"
        lv = ft.ListView(spacing=10, padding=20, expand=True)
        for todo in todos:
            todo_date = todo.get("due", "")
            todo_title = todo.get("title", "タイトルなし")
            if todo_date:
                todo_date = datetime.datetime.fromisoformat(todo_date)
                command.reply_text += f"{todo_title} "
                lv.controls.append(ft.Container(content=ft.Column([ft.Text(
                    todo_title, size=20)]), bgcolor=ft.Colors.WHITE10, padding=10, border_radius=5))
        command.reply_text += "です"
        command.flet_view = lv
        return super().execute(command)
