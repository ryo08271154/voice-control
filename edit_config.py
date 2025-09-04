from plugin import PluginManager
import json
import os
dir_name = os.path.dirname(__file__)


def setup():
    custom_devices = {"deviceList": []}
    custom_scenes = {"sceneList": []}
    custom_routines = {"routineList": []}
    os.makedirs(f"{dir_name}/config", exist_ok=True)
    with open(f"{dir_name}/config/custom_devices.json", "w") as f:
        json.dump(custom_devices, f, indent=2)
    with open(f"{dir_name}/config/custom_scenes.json", "w") as f:
        json.dump(custom_scenes, f, indent=2)
    with open(f"{dir_name}/config/custom_routines.json", "w") as f:
        json.dump(custom_routines, f, indent=2)


def plugin_list():
    plugin_manager = PluginManager()
    plugins = plugin_manager.get_plugins()
    for i, plugin in enumerate(plugins):
        print("--------------------")
        print(f"{i}:プラグイン名: {plugin.name}")
        print(f"プラグイン説明: {plugin.description}")
    print("--------------------")
    return plugins


def plugin_config():
    while True:
        plugin_index_list = []
        plugins = []
        plugins_config = {}
        plugins_list = plugin_list()
        try:
            plugin_index_list = list(
                map(int, input("使用するプラグインの番号を入力してください(カンマ区切りで入力してください):").split(",")))
        except ValueError:
            plugins = config.get("plugins", [])
            plugins_config = config.get("plugins_config", {})
            break
        try:
            for i in plugin_index_list:
                plugins.append(plugins_list[i].name)
                print(f"プラグイン名: {plugins_list[i].name} の設定")
                plugin_config = {}
                for config_name in plugins_list[i].required_config:
                    plugin_config[config_name] = input(f"{config_name}の設定を入力してください:") or config.get(
                        "plugins_config", {}).get(plugins_list[i].name, {}).get(config_name, "")
                plugins_config[plugins_list[i].name] = plugin_config
            break
        except KeyboardInterrupt:
            exit()
        except Exception as e:
            print(f"入力が不正です。数字をカンマ区切りで入力してください。{e}")
    return plugins, plugins_config


if __name__ == '__main__':
    config_file = f"{dir_name}/config/config.json"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
        print("変更しない場合は何も入力せずにEnterを押してください。")
    else:
        config = {}
        setup()
    speech_engine = input(
        "VOSKを利用する場合はvoskと入力してください Whisperを利用する場合はwhisperと入力してください:") or "vosk"
    speech_engine_json = {}
    if speech_engine == "vosk":
        print("音声認識にVOSKを使用しているため、VOSKのモデルをダウンロードしておく必要があります。")
        vosk_model_path = input("VOSKのモデルパスを入力してください") or config.get(
            "vosk", {}).get("model_path", "")
        speech_engine_json = {"vosk": {"model_path": vosk_model_path}}
    elif speech_engine == "whisper":
        whisper_model_size_or_path = input("Whisperのモデルサイズまたはパスを入力してください:") or config.get(
            "whisper", {}).get("model_size_or_path", "")
        whisper_device = config.get("whisper", {}).get("device", "cpu")
        whisper_compute_type = config.get(
            "whisper", {}).get("compute_type", "int8")
        whisper_language = config.get("whisper", {}).get("language", "ja")
        speech_engine_json = {"whisper": {"model_size_or_path": whisper_model_size_or_path,
                                          "device": whisper_device, "compute_type": whisper_compute_type, "language": whisper_language}}
    genai_apikey = input("GeminiのAPIキーを入力してください:") or config.get(
        "genai", {}).get("apikey", "")
    genai_model = input("Geminiが使用するモデル名を入力してください:") or config.get(
        "genai", {}).get("model_name", "")
    genai_system_instruction = input("Geminiのシステム指示を入力してください:") or config.get(
        "genai", {}).get("system_instruction", "")
    genius_api_token = input("GeniusのAPIトークンを入力してください:") or config.get(
        "genius", {}).get("token", "")
    yomiage_server_url = input("音声読み上げサーバーのURLを入力してください:") or config.get(
        "server", {}).get("url", "")
    plugins, plugins_config = plugin_config()
    config = {**speech_engine_json, "genai": {"apikey": genai_apikey, "model_name": genai_model, "system_instruction": genai_system_instruction}, "mcpServers": {} or config.get("mcpServers", {}), "genius": {"token": genius_api_token}, "server": {
        "url": yomiage_server_url, "action": config.get("server", {}).get("action", "command"), "reply_text": config.get("server", {}).get("reply_text", "message")}, "plugins": plugins, "plugins_config": plugins_config}
    with open(f"{dir_name}/config/config.json", "w") as f:
        json.dump(config, f, indent=2)
        print("設定が保存されました。")
