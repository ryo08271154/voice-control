# -*- coding: utf-8 -*-
import json
import time
import hashlib
import hmac
import base64
import uuid
import requests
import os
def header():
    # Declare empty header dictionary
    apiHeader = {}
    # open token
    token = os.getenv("SWITCHBOT_TOKEN") # copy and paste from the SwitchBot app V6.14 or later
    # secret key
    secret = os.getenv("SWITCHBOT_SECRET") # copy and paste from the SwitchBot app V6.14 or later
    nonce = uuid.uuid4()
    t = int(round(time.time() * 1000))
    string_to_sign = '{}{}{}'.format(token, t, nonce)

    string_to_sign = bytes(string_to_sign, 'utf-8')
    secret = bytes(secret, 'utf-8')

    sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())
    # print ('Authorization: {}'.format(token))
    # print ('t: {}'.format(t))
    # print ('sign: {}'.format(str(sign, 'utf-8')))
    # print ('nonce: {}'.format(nonce))

    #Build api header JSON
    apiHeader['Authorization']=token
    apiHeader['Content-Type']='application/json'
    apiHeader['charset']='utf8'
    apiHeader['t']=str(t)
    apiHeader['sign']=str(sign, 'utf-8')
    apiHeader['nonce']=str(nonce)
    # print(apiHeader)
    return apiHeader

def get_device_list():
    global devices
    if len(devices)==0:
        apiHeader=header()
        r = requests.get(url="https://api.switch-bot.com/v1.1/devices",headers=apiHeader)
        j=r.json()
        with open(os.path.join(dir_name,"devices.json"),"w") as f:
            json.dump(j,f,ensure_ascii=False,indent=2, separators=(',', ': '))
        # infraredRemoteList=j["body"]["infraredRemoteList"]
        # device =j["body"]["deviceList"]
        # print(j)
        return j
def get_scene_list():
    global scenes
    if len(scenes)==0:
        apiHeader=header()
        r = requests.get(url="https://api.switch-bot.com/v1.1/scenes",headers=apiHeader)
        j=r.json()
        with open(os.path.join(dir_name,"scenes.json"),"w") as f:
            json.dump(j,f,ensure_ascii=False,indent=2, separators=(',', ': '))
        return j

def status(name):
    get_device_list()
    apiHeader=header()
    # device =devices["body"]["deviceList"]
    for i in devices["body"]["deviceList"]:
        if i["deviceName"]==name:
            device_info= i
            break
    id=device_info["deviceId"]
    r = requests.get(url=f"https://api.switch-bot.com/v1.1/devices/{id}/status",headers=apiHeader)
    j=r.json()

    # print(j)
    return j
def commands(name,onoff,c_type="command",parameter="default"):
    get_device_list()
    command={}
    command["commandType"]=c_type
    command["command"]=onoff
    command["commandparameter"]=parameter
    apiHeader=header()
    for i in devices["body"]["infraredRemoteList"]:
        if i["deviceName"]==name:
            device_info= i
            break
    id=device_info["deviceId"]
    r = requests.post(url=f"https://api.switch-bot.com/v1.1/devices/{id}/commands",headers=apiHeader,json=command)
    j=r.json()
    # print(j)
    return j
    # print(devices)
def scene(name):
    get_scene_list()
    apiHeader=header()
    for i in scenes["body"]:
        if i["sceneName"]==name:
            scene_info= i
            print(i)
            break
    id=scene_info["sceneId"]
    r = requests.post(url=f"https://api.switch-bot.com/v1.1/scenes/{id}/execute",headers=apiHeader,)
    j=r.json()
    # print(j)
    return j
dir_name=os.path.dirname(__file__)
try:
    devices=json.load(open(os.path.join(dir_name,"devices.json"),"r"))
    scenes=json.load(open(os.path.join(dir_name,"scenes.json"),"r"))
except:
    devices={}
    scenes={}
    get_device_list()
    get_scene_list()
# print(device_list())
# get_device_list())
# get_scene_list()
# print(scenes)
# commands("テレビ","turnOn")
# scene("入室")
# print(scenes)
# device_status=status("ハブ２ 07")
# print(device_list())
# print(device_status["body"]["temperature"])
# print(device_status["body"]["humidity"])
# print(device_status["body"]["lightLevel"])