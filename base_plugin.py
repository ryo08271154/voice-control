import importlib
import inspect
import os
dir_name=os.path.dirname(os.path.abspath(__file__))
class PluginManager:
    def __init__(self,plugin_dir:str="plugins"):
        self.plugin_dir=plugin_dir
        self.plugins=[]
    def load_plugins(self):
        plugins=[]
        for filename in os.listdir(os.path.join(dir_name,self.plugin_dir)):
            try:
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = f"plugins.{filename[:-3]}"
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj,BasePlugin) and obj != BasePlugin:
                            plugins.append(obj())
            except OSError as e:
                print(f"プラグインファイルの読み込み中にエラーが発生しました: {e}")
            except Exception as e:
                print(f"プラグインの読み込みにエラーが発生しました: {e}")
        self.plugins=plugins
        return plugins
class BasePlugin:
    name:str=""
    description:str=""
    keywords:list=[]
    def get_keywords(self) -> list:
        return self.keywords
    def can_handle(self, text: str) -> bool:
        return any(keyword in text for keyword in self.keywords)
    def execute(self,text:str,) -> str:
        return ""