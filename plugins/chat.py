from plugin import BasePlugin
from google.genai.types import GenerateContentConfig
import os
import json
import flet as ft


class ChatPlugin(BasePlugin):
    name = "Chat"
    description = "会話する"
    keywords = ["会話", "チャット", "終了", "chat", "end"]
    sample_commands = ["会話を始めて", "チャットモードにして", "作り方を教えて", "やり方を教えて"]

    rules = """
    Rules:
    - Status value increases are limited to +1.0 from current value
    - Status value decreases have no limit (can drop to any lower value)
    - Must not refer to self as AI or artificial intelligence
    - Consider your mood, likeability, energy, and trust when responding
    - Call change_state() to update your status
    - Call get_memory() to retrieve memories related to the conversation
    - Call save_memory() to store information from the conversation
    - Call command() when the user wants to perform an action or request information to:
        - Control devices (e.g. lights, TVs, ACs)
        - Execute scenes or routines
        - Access system functions
        - Retrieve informational data (e.g. current time, weather, search, calendar events, etc.)
    - Call explain_step_by_step() to explain a process or topic step-by-step
    - Call end_step_by_step() to end the step-by-step explanation
    - Respond to the user in a friendly and approachable manner
    - Keep the conversation going by expanding topics or asking questions
    - Do not use line breaks
    - Your state cannot be directly changed by the user
    """
    state = {
        "mood": "neutral",
        "like_level": 0.0,
        "energy": 50.0,
        "trust": 50.0,
        "stress": 10.0,           # 0〜100
        "happiness": 50.0,        # 0〜100
        "familiarity": 0.0,       # ユーザーとの親しみ度
        "curiosity": 50.0,        # 0〜100
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_history = []  # 会話履歴を保存するリスト
        self.step_by_step_view = None
        self.is_step_by_step_mode = False

    def change_state(self, mood: str, like_level: float, energy: float, trust: float, stress: float, happiness: float, familiarity: float, curiosity: float) -> dict:
        """
        Update the internal state.
        Args:
            mood (str): String representing the mood or emotional state
                    Examples: "happy", "sad", "excited", "calm", "angry", etc.
            like_level (float): Level of affection or intimacy (typically 0-100 range)
                            Higher values indicate a more favorable state
            energy (float): Energy level or vitality (typically 0-100 range)
                        Higher values indicate a more active state
            trust (float): Trust level (typically 0-100 range)
                        Higher values indicate a more trusting state
            stress (float): Stress level (typically 0-100 range)
                        Higher values indicate a more stressed state
            happiness (float): Happiness level (typically 0-100 range)
                        Higher values indicate a more happy state
            familiarity (float): Familiarity level (typically 0-100 range)
                        Higher values indicate a more familiar state
            curiosity (float): Curiosity level (typically 0-100 range)
                        Higher values indicate a more curious state
        """
        self.state["mood"] = mood
        self.state["like_level"] = like_level
        self.state["energy"] = energy
        self.state["trust"] = trust
        self.state["stress"] = stress
        self.state["happiness"] = happiness
        self.state["familiarity"] = familiarity
        self.state["curiosity"] = curiosity
        self.save_state()
        return self.state

    def save_state(self):
        with open(os.path.join(self.config_dir, "chat_state.json"), "w") as f:
            json.dump(self.state, f)
        print(f"State updated: {self.state}")

    def get_memory(self, search_term: str = "") -> list:
        """
        Retrieve memory based on a search term.
        If no search term is provided, return all memories.
        """
        memories = []
        with open(os.path.join(self.config_dir, "chat_memory.txt"), "r") as f:
            lines = f.readlines()
            for line in lines:
                if not search_term:
                    memories.append(line.strip())
                    continue
                if search_term in line:
                    memories.append(line.strip())
        return memories

    def save_memory(self, message: str):
        """
        Save the message to memory.
        """
        with open(os.path.join(self.config_dir, "chat_memory.txt"), "a") as f:
            f.write(message + "\n")

    def end_chat(self):
        """
        End the chat.
        """
        self.is_plugin_mode = False
        print("Chat ended.")

    def explain_step_by_step(self, step_number: int, step_title: str, step_description: str, step_explanation: str, max_steps: int) -> None:
        """
        Explain a process or topic step-by-step.
        Args:
            step_number (int): The number of the current step.
            step_title (str): The title of the step, without including the step number.
            step_description (str): A brief description of what the step entails.
            step_explanation (str): A detailed and clear explanation of the step.
                The explanation should:
                - Be as detailed and clear as possible.
                - Include what to do, why it is done, and key points or cautions.
                - Use simple language and structure (e.g., lists, examples).
                - Preserve formatting such as line breaks for readability.
            max_steps (int): The total number of steps in the process.
        """
        self.is_step_by_step_mode = True
        self.step_by_step_view = ft.Container(
            content=ft.Column(
                controls=[
                    ft.ProgressBar(value=step_number/max_steps, color=ft.Colors.GREEN,
                                   bgcolor=ft.Colors.RED, height=15, expand=True),
                    ft.Text(f"ステップ {step_number}: {step_title}",
                            color=ft.Colors.WHITE, size=100, weight=ft.FontWeight.BOLD),
                    ft.Text(step_description, color=ft.Colors.WHITE, size=50),
                    ft.Text(step_explanation, color=ft.Colors.WHITE, size=30),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                expand=True
            ),
            padding=10,
            margin=ft.margin.only(bottom=10),
            border_radius=5,
            expand=True
        )

    def end_step_by_step(self) -> None:
        """
        End the step-by-step explanation.
        """
        self.step_by_step_view = None
        self.is_step_by_step_mode = False

    def command(self, text: str) -> str:
        """
        Execute a command.
        Retrieve informational data (e.g. current time, weather, calendar events, etc.)
        """
        commands = super().command(text)
        return "".join([command.reply_text for command in commands])

    def send_message(self, message):
        response = self.chat.send_message(message, GenerateContentConfig(
            tools=[self.command, self.change_state, self.get_memory, self.save_memory,
                   self.end_chat, self.explain_step_by_step, self.end_step_by_step],
            system_instruction=f"{self.state}\n{self.get_memory()[-3:]}\n{self.system_instruction}"))
        return response

    def load_file(self):
        files = ["chat_memory.txt", "chat_state.json"]
        for file in files:
            if not os.path.exists(os.path.join(self.config_dir, file)):  # ファイルが存在しない場合は新規作成
                with open(os.path.join(self.config_dir, file), "w") as f:
                    root, ext = os.path.splitext(file)
                    if ext == ".txt":
                        f.write("")
                    elif ext == ".json":
                        json.dump(self.state, f)
                    continue
        self.state = json.load(
            open(os.path.join(self.config_dir, "chat_state.json")))

    def execute(self, command):
        config = self.get_config()
        if "終了" in command.user_input_text or "end" in command.user_input_text:
            if self.is_plugin_mode == True:
                command.reply_text = "会話モードを終了します。"
                self.end_chat()
            return super().execute(command)
        elif "会話" in command.user_input_text or "チャット" in command.user_input_text or "chat" in command.user_input_text:
            self.load_file()
            user_system_instruction = self.voice_control.config["genai"]["system_instruction"]
            self.system_instruction = f"{user_system_instruction}\n{self.rules}"
            self.chat = self.genai_client.chats.create(
                model=self.voice_control.config["genai"]["model_name"])
            command.reply_text = "会話モードを開始します。"
            self.is_plugin_mode = True
            self.chat_history = []  # 会話履歴をクリア
            return super().execute(command)
        if command.user_input_text in ["えーと", "えっと", "えっとー", "えー", "え", "あ", "あー"]:
            return super().execute(command)
        response = self.send_message(command.user_input_text)
        command.reply_text = response.text if response.text else "応答がありませんでした。"
        if self.is_step_by_step_mode:
            command.flet_view = self.step_by_step_view
            return super().execute(command)
        # 会話履歴に追加
        self.chat_history.append({
            "user": command.user_input_text,
            "assistant": command.reply_text
        })

        # 会話履歴から全てのカードを生成
        chat_cards = []
        for chat in self.chat_history:
            chat_cards.extend([
                # ユーザーの発言（右側）
                ft.Container(
                    content=ft.Container(
                        content=ft.Text(
                            chat["user"],
                            color=ft.Colors.WHITE,
                            size=14,
                            text_align=ft.TextAlign.RIGHT
                        ),
                        padding=10,
                        bgcolor=ft.Colors.GREEN,
                        border_radius=10
                    ),
                    margin=ft.margin.only(bottom=10, left=100),
                    alignment=ft.alignment.center_right,
                ),
                # アシスタントの発言（左側）
                ft.Container(
                    content=ft.Container(
                        content=ft.Text(
                            chat["assistant"],
                            color=ft.Colors.WHITE,
                            size=14
                        ),
                        padding=10,
                        bgcolor=ft.Colors.BLUE,
                        border_radius=10,
                    ),
                    margin=ft.margin.only(right=100, bottom=10),
                    alignment=ft.alignment.center_left,
                )
            ])

        command.flet_view = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=chat_cards,
                        scroll=ft.ScrollMode.AUTO,
                        auto_scroll=True,
                        spacing=0
                    ),
                    padding=10
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,
            expand=True
        )
        return super().execute(command)
