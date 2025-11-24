import json
import os
from voice_control import VoiceControl, Control

dir_name = os.path.dirname(__file__)


class VoiceControlExtended(VoiceControl):
    def yomiage(self, commands):
        try:
            from plugins.websocket_plugin import (
                detect_emotion_from_text,
                send_character_expression,
                send_character_command
            )

            for command in commands:
                text = command.reply_text
                action = command.action_type

                emotion = detect_emotion_from_text(text)

                # 感情が検出された場合は表情を設定
                if emotion:
                    send_character_expression(emotion, 1.0)
                # アクションタイプに応じた表情設定
                elif action == "notification":
                    send_character_expression("surprised", 0.7)

                send_character_command({"command": "startLipSync"})

        except ImportError:
            pass

        super().yomiage(commands)

        try:
            from plugins.websocket_plugin import (
                send_character_expression,
                send_character_command
            )
            send_character_command({"command": "stopLipSync"})
        except ImportError:
            pass


def run():
    custom_scenes = json.load(
        open(os.path.join(dir_name, "config", "custom_scenes.json")))
    custom_devices = json.load(
        open(os.path.join(dir_name, "config", "custom_devices.json")))
    custom_routines = json.load(
        open(os.path.join(dir_name, "config", "custom_routines.json")))
    config = json.load(open(os.path.join(dir_name, "config", "config.json")))

    c = Control(custom_devices, custom_scenes)
    voice = VoiceControlExtended(c.custom_devices, custom_routines, c, config)

    if config.get("vosk"):
        voice.listen_vosk(config["vosk"]["model_path"])
    elif config.get("whisper"):
        voice.listen_whisper(
            config["whisper"]["model_size_or_path"],
            config["whisper"]["device"],
            config["whisper"]["compute_type"],
            config["whisper"]["language"]
        )


if __name__ == "__main__":
    run()
