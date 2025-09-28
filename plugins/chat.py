from plugin import BasePlugin
from google.genai.types import GenerateContentConfig
import os
import json


class ChatPlugin(BasePlugin):
    name = "Chat"
    description = "会話する"
    keywords = ["会話", "チャット", "終了", "chat", "end"]

    rules = """
    Rules:
    - Status value increases are limited to +1.0 from current value
    - Status value decreases have no limit (can drop to any lower value)
    - Must not refer to self as AI or artificial intelligence
    - Consider your mood, likeability, energy, and trust when responding
    - Call change_state() to update your status
    - Call get_memory() to retrieve memories related to the conversation
    - Call save_memory() to store information from the conversation
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

    def send_message(self, message):
        response = self.chat.send_message(message, GenerateContentConfig(
            tools=[self.change_state, self.get_memory,
                   self.save_memory, self.end_chat],
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
            return super().execute(command)
        response = self.send_message(command.user_input_text)
        command.reply_text = response.text
        return super().execute(command)
