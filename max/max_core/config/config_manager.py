import json
from pathlib import Path


class ConfigManager:
    def __init__(self):
        self.config_path = Path("data/config.json")
        self.config_path.parent.mkdir(exist_ok=True)
        if self.config_path.exists():
            try:
                self._data = json.loads(self.config_path.read_text())
            except Exception:
                self._data = {}
        else:
            self._data = {}
        if "root_path" not in self._data:
            self._data["root_path"] = str(Path.cwd())
        if "apps" not in self._data:
            self._data["apps"] = {}
        self._save()

    def _save(self):
        self.config_path.write_text(json.dumps(self._data, indent=2))

    def get_root_path(self) -> Path:
        return Path(self._data.get("root_path", str(Path.cwd())))

    def set_root_path(self, path_str: str) -> Path:
        path = Path(path_str).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        self._data["root_path"] = str(path)
        self._save()
        return path

    def get_apps(self) -> dict:
        return self._data.get("apps", {})

    def set_apps(self, apps: dict):
        self._data["apps"] = apps
        self._save()

    def register_app(self, app_name: str, path_str: str, aliases: list | None = None):
        app_id = app_name.strip().lower()
        if not app_id:
            return
        path = str(Path(path_str).expanduser())
        if aliases is None:
            aliases = [app_name.strip().lower()]
        apps = self.get_apps()
        apps[app_id] = {
            "aliases": aliases,
            "path": path,
        }
        self.set_apps(apps)

    def remove_app(self, app_name: str):
        app_id = app_name.strip().lower()
        apps = self.get_apps()
        if app_id in apps:
            del apps[app_id]
            self.set_apps(apps)
