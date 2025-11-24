# -*- coding: utf-8 -*-
from plugin import BasePlugin
import json
import time
import hashlib
import hmac
import base64
import uuid
import requests
import os
import datetime
import re
dir_name = os.path.dirname(__file__)
dir_name = os.path.abspath(os.path.join(dir_name, os.pardir))


class Switchbot:
    def __init__(self):
        self.config = {}
        self.devices, self.scenes = self.setup()

    def setup(self):
        try:
            devices = json.load(
                open(os.path.join(dir_name, "config", "switchbot_devices.json"), "r"))
            scenes = json.load(
                open(os.path.join(dir_name, "config", "switchbot_scenes.json"), "r"))
        except:
            devices = {"body": {"infraredRemoteList": []}}
            scenes = {"body": []}
        return devices, scenes

    def header(self):
        # Declare empty header dictionary
        apiHeader = {}
        # open token
        # copy and paste from the SwitchBot app V6.14 or later
        token = self.config.get("switchbot_token")
        # secret key
        # copy and paste from the SwitchBot app V6.14 or later
        secret = self.config.get("switchbot_secret")
        nonce = uuid.uuid4()
        t = int(round(time.time() * 1000))
        string_to_sign = '{}{}{}'.format(token, t, nonce)

        string_to_sign = bytes(string_to_sign, 'utf-8')
        secret = bytes(secret, 'utf-8')

        sign = base64.b64encode(
            hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())
        # print ('Authorization: {}'.format(token))
        # print ('t: {}'.format(t))
        # print ('sign: {}'.format(str(sign, 'utf-8')))
        # print ('nonce: {}'.format(nonce))

        # Build api header JSON
        apiHeader['Authorization'] = token
        apiHeader['Content-Type'] = 'application/json'
        apiHeader['charset'] = 'utf8'
        apiHeader['t'] = str(t)
        apiHeader['sign'] = str(sign, 'utf-8')
        apiHeader['nonce'] = str(nonce)
        # print(apiHeader)
        return apiHeader

    def get_device_list(self):
        apiHeader = self.header()
        r = requests.get(
            url="https://api.switch-bot.com/v1.1/devices", headers=apiHeader)
        j = r.json()
        with open(os.path.join(dir_name, "config", "switchbot_devices.json"), "w") as f:
            json.dump(j, f, ensure_ascii=False,
                      indent=2, separators=(',', ': '))
        return j

    def get_scene_list(self):
        apiHeader = self.header()
        r = requests.get(
            url="https://api.switch-bot.com/v1.1/scenes", headers=apiHeader)
        j = r.json()
        with open(os.path.join(dir_name, "config", "switchbot_scenes.json"), "w") as f:
            json.dump(j, f, ensure_ascii=False,
                      indent=2, separators=(',', ': '))
        return j

    def status(self, name):
        apiHeader = self.header()
        # device =devices["body"]["deviceList"]
        for i in self.devices["body"]["deviceList"]:
            if i["deviceName"] == name:
                device_info = i
                break
        id = device_info["deviceId"]
        r = requests.get(
            url=f"https://api.switch-bot.com/v1.1/devices/{id}/status", headers=apiHeader)
        j = r.json()

        # print(j)
        return j

    def commands(self, name, onoff, c_type="command", parameter="default"):
        command = {}
        command["commandType"] = c_type
        command["command"] = onoff
        command["parameter"] = parameter
        apiHeader = self.header()
        for i in self.devices["body"]["infraredRemoteList"]:
            if i["deviceName"] == name:
                device_info = i
                break
        id = device_info["deviceId"]
        r = requests.post(
            url=f"https://api.switch-bot.com/v1.1/devices/{id}/commands", headers=apiHeader, json=command)
        j = r.json()
        # print(j)
        return j
        # print(devices)

    def scene(self, name):
        apiHeader = self.header()
        for i in self.scenes["body"]:
            if i["sceneName"] == name:
                scene_info = i
                print(i)
                break
        id = scene_info["sceneId"]
        r = requests.post(
            url=f"https://api.switch-bot.com/v1.1/scenes/{id}/execute", headers=apiHeader,)
        j = r.json()
        # print(j)
        return j


switchbot = Switchbot()


class SwitchbotPlugin(BasePlugin):
    name = "SwitchBot"
    description = "SwitchBotAPIを使用してデバイスを操作する"
    keywords = ["スイッチボット", "リスト更新", "度", "モード", "風量",
                "冷房", "除湿", "送風", "暖房", "自動", "弱", "中", "強"]
    required_config = ["switchbot_token", "switchbot_secret"]

    _MODES = {
        "自動": 1,
        "冷房": 2,
        "除湿": 3,
        "送風": 4,
        "暖房": 5,
    }
    _FAN_SPEEDS = {
        "自動": 1,
        "弱": 2,
        "中": 3,
        "強": 4,
    }

    def __init__(self, voice_control=None):
        super().__init__(voice_control)
        config = self.get_config()
        switchbot.config = config
        switchbot_token = config.get("switchbot_token")
        switchbot_secret = config.get("switchbot_secret")
        if not switchbot_token or not switchbot_secret:
            raise ValueError("SwitchBotのAPIキーが設定されていません。")
        for device in switchbot.devices["body"]["infraredRemoteList"]:
            if device["remoteType"] == "Air Conditioner":
                self.add_device(
                    device_name=device["deviceName"],
                    device_type=device["remoteType"],
                    room=device.get("roomName", "unknown"),
                    on_func=lambda d: switchbot.commands(d.device_name, "on"),
                    off_func=lambda d: switchbot.commands(
                        d.device_name, "off"),
                    set_count_func=lambda d, count: self.air_conditioner_commands(
                        d.device_name, temperature=count),
                    up_func=lambda d, amount: self.air_conditioner_commands(
                        d.device_name, temperature=self.air_conditioner_status["temperature"]+amount),
                    down_func=lambda d, amount: self.air_conditioner_commands(
                        d.device_name, temperature=self.air_conditioner_status["temperature"]-amount),
                )
            elif "TV" in device["remoteType"] or "Streamer" in device["remoteType"] or "Set Top Box" in device["remoteType"]:
                self.add_device(
                    device_name=device["deviceName"],
                    device_type=device["remoteType"],
                    room=device.get("roomName", "unknown"),
                    on_func=lambda d: switchbot.commands(
                        d.device_name, "turnOn"),
                    off_func=lambda d: switchbot.commands(
                        d.device_name, "turnOff"),
                    play_func=lambda d: switchbot.commands(
                        d.device_name, "play"),
                    pause_func=lambda d: switchbot.commands(
                        d.device_name, "pause"),
                    stop_func=lambda d: switchbot.commands(
                        d.device_name, "stop"),
                    next_func=lambda d: switchbot.commands(
                        d.device_name, "next"),
                    previous_func=lambda d: switchbot.commands(
                        d.device_name, "previous"),
                    up_func=lambda d, amount: switchbot.commands(
                        d.device_name, "volumeAdd"),
                    down_func=lambda d, amount: switchbot.commands(
                        d.device_name, "volumeSub"),
                    set_count_func=lambda d, count: switchbot.commands(
                        d.device_name, "SetChannel", parameter=count),
                )
            elif "DVD" in device["remoteType"] or "Speaker" in device["remoteType"]:
                self.add_device(
                    device_name=device["deviceName"],
                    device_type=device["remoteType"],
                    room=device.get("roomName", "unknown"),
                    on_func=lambda d: switchbot.commands(
                        d.device_name, "turnOn"),
                    off_func=lambda d: switchbot.commands(
                        d.device_name, "turnOff"),
                    play_func=lambda d: switchbot.commands(
                        d.device_name, "Play"),
                    pause_func=lambda d: switchbot.commands(
                        d.device_name, "Pause"),
                    stop_func=lambda d: switchbot.commands(
                        d.device_name, "Stop"),
                    next_func=lambda d: switchbot.commands(
                        d.device_name, "Next"),
                    previous_func=lambda d: switchbot.commands(
                        d.device_name, "Previous"),
                    up_func=lambda d, amount: switchbot.commands(
                        d.device_name, "volumeAdd"),
                    down_func=lambda d, amount: switchbot.commands(
                        d.device_name, "volumeSub"),
                )
            elif "Light" in device["remoteType"]:
                self.add_device(
                    device_name=device["deviceName"],
                    device_type=device["remoteType"],
                    room=device.get("roomName", "unknown"),
                    on_func=lambda d: switchbot.commands(
                        d.device_name, "turnOn"),
                    off_func=lambda d: switchbot.commands(
                        d.device_name, "turnOff"),
                    up_func=lambda d, amount: switchbot.commands(
                        d.device_name, "brightnessUp"),
                    down_func=lambda d, amount: switchbot.commands(
                        d.device_name, "brightnessDown"),
                )
            else:
                self.add_device(device_name=device["deviceName"], device_type=device["remoteType"], room=device.get("roomName", "unknown"),
                                on_func=lambda d: switchbot.commands(
                                    d.device_name, "turnOn"),
                                off_func=lambda d: switchbot.commands(d.device_name, "turnOff"))
        for scene in switchbot.scenes["body"]:
            self.add_scene(scene_name=scene["sceneName"], room=scene.get("roomName", "unknown"),
                           excute_func=lambda s: switchbot.scene(s.scene_name))

    def air_conditioner_control(self, device_name, text):
        temperature = self.air_conditioner_status["temperature"]
        mode = None
        fan_speed = None
        temperature_match = re.search(r"(\d+)", text)
        if temperature_match:
            temperature_match = int(temperature_match.group(1))
            if "上" in text or "高" in text:
                temperature += temperature_match
            elif "下" in text or "低" in text:
                temperature -= temperature_match
            temperature = temperature_match
        for m in self._MODES:
            if m in text:
                mode = m
                break
        for f in self._FAN_SPEEDS:
            if f in text:
                fan_speed = f
                break
        if mode is None and fan_speed is None and not temperature_match:
            return ""
        return self.air_conditioner_commands(device_name=device_name, temperature=temperature, mode=mode, fan_speed=fan_speed)

    def air_conditioner_commands(self, device_name, temperature=None, mode=None, fan_speed=None, power_state=None):
        if temperature:
            self.air_conditioner_status["temperature"] = temperature
        if mode:
            self.air_conditioner_status["mode"] = self._MODES[mode]
        if fan_speed:
            self.air_conditioner_status["fan_speed"] = self._FAN_SPEEDS[fan_speed]
        if power_state:
            self.air_conditioner_status["power_state"] = power_state
        command = f"{self.air_conditioner_status['temperature']},{self.air_conditioner_status['mode']},{self.air_conditioner_status['fan_speed']},{self.air_conditioner_status['power_state']}"
        switchbot.commands(device_name, "setAll", "command", command)
        if power_state == "off":
            return f"{device_name}をオフにします"
        return f"{device_name}を{self.air_conditioner_status['temperature']}度、{list(self._MODES.keys())[list(self._MODES.values()).index(self.air_conditioner_status['mode'])]}、風量{list(self._FAN_SPEEDS.keys())[list(self._FAN_SPEEDS.values()).index(self.air_conditioner_status['fan_speed'])]}に設定しました"
    air_conditioner_status = {"temperature": 26,
                              "mode": 2 if datetime.date.today().month >= 5 and datetime.date.today().month <= 10 else 5,
                              "fan_speed": 1,
                              "power_state": "on"}

    def execute(self, command):
        text = command.user_input_text
        if "リスト更新" in text:
            switchbot.devices = switchbot.get_device_list()
            switchbot.scenes = switchbot.get_scene_list()
            self.keywords = [i["deviceName"] for i in switchbot.devices["body"]
                             ["infraredRemoteList"]]+[i["sceneName"] for i in switchbot.scenes["body"]]
        for i in switchbot.devices["body"]["infraredRemoteList"]:
            if i["deviceName"] in text:
                if i["remoteType"] == "Air Conditioner":
                    command.reply_text = self.air_conditioner_control(
                        i["deviceName"], text)
                    continue
        return super().execute(command)
