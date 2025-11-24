import requests
from plugin import BasePlugin, Device


class HomeAssistantPlugin(BasePlugin):
    name = "HomeAssistant"
    description = "HomeAssistant Conversation APIを使用して、スマートホームデバイスを操作します。"
    required_config = ["token", "url", "agent_id"]

    def __init__(self, voice_control=None):
        super().__init__(voice_control)
        config = self.get_config()
        token = config.get("token")
        self.url = config.get("url")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
        }
        self.agent_id = config.get("agent_id", "conversation.home_assistant")

    def get_devices(self):
        template = """
        [
        {% for did in states | map(attribute='entity_id') | map('device_id') | reject('none') | unique %}
        {"device_id": "{{ did }}", "device_name": "{{ device_attr(did, 'name') or device_attr(did, 'name_by_user') }}"}{% if not loop.last %},{% endif %}
        {% endfor %}
        ]
        """
        data = {"template": template}
        devices = requests.post(
            f"{self.url}/api/template", headers=self.headers, json=data)
        return devices.json()

    def update_devices(self):
        devices = self.get_devices()
        for device in devices:
            self.keywords.append(device["device_name"])
            self.devices.append(Device(device["device_name"]))

    def can_handle(self, text):
        if not self.keywords:
            self.update_devices()
        return super().can_handle(text)

    def execute(self, command):
        data = {
            "text": f"{command.user_input_text}",
            "agent_id": self.agent_id
        }
        response = requests.post(
            f"{self.url}/api/conversation/process", json=data, headers=self.headers)
        response_json = response.json()
        command.reply_text = response_json["response"]["speech"]["plain"]["speech"]
        return super().execute(command)
