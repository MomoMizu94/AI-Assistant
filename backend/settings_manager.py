import os
import json
from typing import Dict, Any

class SettingsManager:
    def __init__(self, settings_path: str, defaults: Dict[str, Any]):
        self.settings_path = settings_path
        self.defaults = defaults
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)

    def load_overrides(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.settings_path):
                return {}
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load()
                if isinstance(data, Dict):
                    return data
                else:
                    return {}
        except Exception:
            print(">>> [SettingsManager] Unable to locate settings file. Invalid path?")
            return {}
        
    def get_merged_settings(self) -> Dict[str, Any]:
        overrides = self.load_overrides()
        merged = dict(self.defaults)
        merged.update(overrides)
        return merged
    
    def save_overrides(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        # Store values that only exist in default settings
        # New settings needs to be added there first
        filtered_overrides = {}
        for key, value in overrides.items():
            if key in self.defaults:
                filtered_overrides[key] = value
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(filtered_overrides, f, ensure_ascii=False, indent=2)
        return filtered_overrides