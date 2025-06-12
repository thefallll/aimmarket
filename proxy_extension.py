import os
import zipfile
from proxy import Proxy
class ProxyExtension:

    def __init__(self, proxy: str = None):
        self.proxy = Proxy(proxy) if proxy else None
        self._extension_path: str = f"res/proxy_extensions/{self.proxy.host}" if proxy else "res/proxy_extensions/null_proxy"
        self._extension_zip: str = f"{self._extension_path}/extension.zip"
        self._extension_folder: str = f"{self._extension_path}/extension"

    @property
    def extension_zip(self) -> str:
        if not os.path.exists(self._extension_path):
            os.makedirs(self._extension_path)

        if not os.path.exists(self._extension_zip):
            with zipfile.ZipFile(self._extension_zip, "w") as zp:
                zp.writestr("manifest.json", self._manifest_json)
                zp.writestr("background.js", self._background_js)

        return self._extension_zip

    @property
    def extension_folder(self) -> str:
        """Создаёт папку расширения, если её нет"""
        if not os.path.exists(self._extension_path):
            os.makedirs(self._extension_path)

        if not os.path.exists(self._extension_folder):
            os.makedirs(self._extension_folder)

            with open(f"{self._extension_folder}/manifest.json", "w", encoding="utf-8") as f:
                f.write(self._manifest_json)

            with open(f"{self._extension_folder}/background.js", "w", encoding="utf-8") as f:
                f.write(self._background_js)

        return self._extension_folder

    @property
    def abs_extension_folder(self) -> str:
        """Возвращает абсолютный путь к расширению"""
        return os.path.abspath(self.extension_folder)

    @property
    def _manifest_json(self) -> str:
        """Создаёт manifest.json для Manifest V3"""
        return """{
            "name": "Proxy Auth Extension",
            "version": "1.0",
            "manifest_version": 3,
            "permissions": [
                "webRequest",
                "webRequestAuthProvider"
            ],
            "host_permissions": [
                "<all_urls>"
            ],
            "background": {
                "service_worker": "background.js"
            }
        }"""
    @property
    def _background_js(self) -> str:
        if self.proxy:
            return f"""chrome.webRequest.onAuthRequired.addListener(
    function(details, callback) {{
        callback({{
            authCredentials: {{
                username: "{self.proxy.username}",
                password: "{self.proxy.password}"
            }}
        }});
    }},
    {{ urls: ["<all_urls>"] }},
    ["asyncBlocking"]
    );"""
        else:
            return "// No proxy configured"
#     @property
#     def _background_js(self) -> str:
#         """Создаёт background.js с авторизацией на прокси (без proxy.settings)"""
#         if self.proxy:
#             return f"""chrome.webRequest.onAuthRequired.addListener(
#     (details, callback) => {{
#         callback({{
#             authCredentials: {{
#                 username: "{self.proxy.username}",
#                 password: "{self.proxy.password}"
#             }}
#         }});
#     }},
#     {{ urls: ["<all_urls>"] }},
#     ["asyncBlocking"]
# );"""
#         else:
#             return "// No proxy configured"