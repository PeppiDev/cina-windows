import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

def get_config_dir() -> Path:
    """Determina la ruta de configuración adecuada para Windows (con fallback)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "cina"
    return Path.home() / ".config" / "cina"

CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model": "gemini-3.7-flash",
    "voice": "es-ES-AlvaroNeural",
    "tts_engine": "edge-tts",  # "edge-tts" o "sapi"
    "speech_rate": "+0%",
    "speech_volume": "+0%",
    "hotkey": "<ctrl>+<alt>+s",
    "capture_backend": "pillow",  # "pillow" nativo de Windows
    "prompt_style": "concise_answer",  # Respuestas directas preparadas para locución
    "play_start_chime": False,  # No emitir sonidos al capturar (100% silencioso)
    "tcp_port": 47832           # Puerto IPC local para Windows
}

AVAILABLE_VOICES = [
    ("es-ES-AlvaroNeural", "Español (España) - Álvaro (Hombre)"),
    ("es-ES-ElviraNeural", "Español (España) - Elvira (Mujer)"),
    ("es-MX-DaliaNeural", "Español (México) - Dalia (Mujer)"),
    ("es-MX-JorgeNeural", "Español (México) - Jorge (Hombre)"),
    ("es-AR-TomasNeural", "Español (Argentina) - Tomás (Hombre)"),
    ("es-AR-ElenaNeural", "Español (Argentina) - Elena (Mujer)"),
    ("es-CO-GonzaloNeural", "Español (Colombia) - Gonzalo (Hombre)"),
    ("es-CO-SalomeNeural", "Español (Colombia) - Salomé (Mujer)"),
    ("es-CL-LorenzoNeural", "Español (Chile) - Lorenzo (Hombre)"),
    ("es-CL-CatalinaNeural", "Español (Chile) - Catalina (Mujer)"),
]

AVAILABLE_MODELS = [
    ("gemini-3.7-flash", "Gemini 3.7 Flash (Recomendado y Multimodal)"),
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite (Ultra Rápido, ~0.7s)"),
]


class ConfigManager:
    def __init__(self):
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> Dict[str, Any]:
        """Carga la configuración desde el disco o crea una por defecto."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
            else:
                self.save()
        except Exception as e:
            print(f"[Config] Error al cargar configuración: {e}")

        # Comprobar si hay variable de entorno GEMINI_API_KEY
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key and not self.config.get("api_key"):
            self.config["api_key"] = env_key

        return self.config

    def save(self) -> bool:
        """Guarda la configuración actual en el disco."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] Error al guardar configuración: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()


config_mgr = ConfigManager()

