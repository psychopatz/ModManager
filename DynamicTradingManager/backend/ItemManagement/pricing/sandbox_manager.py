import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SandboxManager:
    def __init__(self, sandbox_txt_path: Path, storage_path: Path):
        self.sandbox_txt_path = sandbox_txt_path
        self.storage_path = storage_path
        self.definitions: Dict[str, Dict[str, Any]] = {}
        self.values: Dict[str, Any] = {}
        self._load()

    def _load(self):
        # 1. Parse definitions
        if self.sandbox_txt_path.exists():
            content = self.sandbox_txt_path.read_text(encoding="utf-8")
            pattern = re.compile(r'option MarketSense\.(?P<key>\w+)\s*\{(?P<body>.*?)\}', re.DOTALL)
            for match in pattern.finditer(content):
                key = match.group('key')
                body = match.group('body')
                
                type_match = re.search(r'type\s*=\s*(\w+)', body)
                default_match = re.search(r'default\s*=\s*([\d\.\-]+)', body)
                
                if type_match and default_match:
                    self.definitions[key] = {
                        "type": type_match.group(1),
                        "default": float(default_match.group(1)) if type_match.group(1) != "integer" else int(default_match.group(1))
                    }

        # 2. Load stored values
        if self.storage_path.exists():
            try:
                self.values = json.loads(self.storage_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load sandbox values: {e}")
                self.values = {}

    def get_value(self, key: str) -> Any:
        if key in self.values:
            return self.values[key]
        if key in self.definitions:
            return self.definitions[key]["default"]
        return None

    def save_value(self, key: str, value: Any):
        self.values[key] = value
        self.storage_path.write_text(json.dumps(self.values, indent=4), encoding="utf-8")

    def get_tag_adjustment(self, mode: str, tags: list[str]) -> float:
        """
        Mimics Lua's getSandboxTagMultiplier.
        mode: "Price" (additive) or "Stock" (multiplicative)
        """
        total = 0.0 if mode == "Price" else 1.0
        
        for tag in tags:
            parts = tag.split('.')
            path = ""
            for part in parts:
                path = path + (part if path == "" else "." + part)
                clean_path = path.replace(".", "")
                opt_key = f"{mode}{clean_path}{'Value' if mode == 'Price' else 'Mult'}"
                
                val = self.get_value(opt_key)
                if val is not None:
                    if mode == "Price":
                        total += float(val)
                    else:
                        total *= float(val)
        return total

    def get_all_options(self) -> Dict[str, Any]:
        result = {}
        for key, dfn in self.definitions.items():
            result[key] = {
                "value": self.get_value(key),
                "default": dfn["default"],
                "type": dfn["type"]
            }
        return result

# Singleton instance helper
_instance: Optional[SandboxManager] = None

def get_sandbox_manager() -> SandboxManager:
    global _instance
    if _instance is None:
        from config.server_settings import get_server_settings
        settings = get_server_settings()
        
        sandbox_txt = Path(settings.market_sense_path) / "Contents/mods/MarketSense/42.16/media/sandbox-options.txt"
        storage = Path(__file__).parent / "sandbox_values.json"
        
        _instance = SandboxManager(sandbox_txt, storage)
    return _instance
