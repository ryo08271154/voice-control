from plugin import BasePlugin
import pychromecast
import time
import re


class ChromeCast:
    def __init__(self):
        self.chromecasts, self.browser = pychromecast.get_chromecasts()

    def volume_control(self, action, up_down=1):
        reply = ""
        for cast in self.chromecasts:
            cast.wait()
            if cast.status.app_id != None:
                volume = cast.status.volume_level
                try:
                    if action == "volume_up":
                        cast.set_volume(volume+(0.01*up_down))
                        reply = f"音量を{up_down}上げます"
                    if action == "volume_down":
                        cast.set_volume(volume-(0.01*up_down))
                        reply = f"音量を{up_down}下げます"
                except:
                    print("音量操作できません")
                break
        return reply

    def media_control(self, action):
        reply = ""
        for cast in self.chromecasts:
            cast.wait()
            mc = cast.media_controller
            if cast.status.app_id != None:
                mc.block_until_active(timeout=10)
                try:
                    if action == "Play":
                        mc.play()
                        reply = "再生します"
                    if action == "Pause":
                        mc.pause()
                        reply = "一時停止します"
                    if action == "Stop":
                        mc.stop()
                        reply = "停止します"
                except:
                    print("メディア操作できません")
                break
        return reply

    def back_or_skip(self, action, second=10):
        reply = ""
        for cast in self.chromecasts:
            cast.wait()
            mc = cast.media_controller
            if cast.status.app_id != None:
                try:
                    mc.block_until_active(timeout=10)
                    mc.play()
                    time.sleep(1)
                    mc.update_status()
                    current_time = mc.status.current_time
                    mc.pause()
                    if action == "Back":
                        mc.seek(current_time-second)
                        reply = f"{second}秒戻します"
                    if action == "Skip":
                        mc.seek(current_time+second)
                        reply = f"{second}秒スキップします"
                except:
                    print("メディア操作できません")
                break
        return reply


class ChromeCastPlugin(BasePlugin):
    name = "ChromecastMediaControl"
    description = "Chromecastデバイスを操作"
    keywords = ["Chromecast", "キャスト", "音量",
                "再生", "止めて", "一時停止", "停止", "戻す", "スキップ"]
    chromecast = ChromeCast()

    def execute(self, command):
        text = command.user_input_text
        action = None
        if "音量" in text:
            if "上げ" in text:
                action = "volume_up"
            elif "下げ" in text:
                action = "volume_down"
        elif "再生" in text:
            action = "Play"
        elif "一時停止" in text or "止めて" in text:
            action = "Pause"
        elif "停止" in text:
            action = "Stop"
        elif "戻す" in text or "スキップ" in text:
            if "戻す" in text:
                action = "Back"
            else:
                action = "Skip"

        if action == "volume_up":
            volume = re.sub(r"\D", "", text)
            if volume == "":
                volume = 1
            command.reply_text = self.chromecast.volume_control(
                action, int(volume))
        elif action == "volume_down":
            volume = re.sub(r"\D", "", text)
            if volume == "":
                volume = 1
            command.reply_text = self.chromecast.volume_control(
                action, int(volume))
        elif action == "Play":
            command.reply_text = self.chromecast.media_control(action)
        elif action == "Pause":
            command.reply_text = self.chromecast.media_control(action)
        elif action == "Stop":
            command.reply_text = self.chromecast.media_control(action)
        elif action == "Back":
            command.reply_text = self.chromecast.back_or_skip(action)
        elif action == "Skip":
            command.reply_text = self.chromecast.back_or_skip(action)
        command.action_type = action
        return super().execute(command)
