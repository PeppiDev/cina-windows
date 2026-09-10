#!/usr/bin/env python3
import os
import sys
import argparse
import tkinter as tk

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cina.config import config_mgr
from cina.ipc_service import IPCClient
from cina.capture import ScreenCapture
from cina.gemini_service import GeminiService
from cina.tts_service import TTSService
from cina.hotkey_service import HotkeyService


def run_oneshot():
    """Ejecuta una captura y respuesta directa sin interfaz gráfica (modo autónomo / trigger)."""
    print("[Cina-Win] Ejecutando captura silenciosa...")
    cap = ScreenCapture(preferred_backend=config_mgr.get("capture_backend", "pillow"))
    gemini = GeminiService(
        api_key=config_mgr.get("api_key", ""),
        model=config_mgr.get("model", "gemini-3.7-flash")
    )
    tts = TTSService(
        voice=config_mgr.get("voice", "es-ES-AlvaroNeural"),
        rate=config_mgr.get("speech_rate", "+0%"),
        volume=config_mgr.get("speech_volume", "+0%")
    )

    raw_path = cap.capture_silent()
    if not raw_path:
        print("[Cina-Win] Error: No se pudo capturar la pantalla.")
        tts._speak_fallback("Error: no se pudo capturar la pantalla.")
        return

    opt_path = cap.optimize_image(raw_path)
    print(f"[Cina-Win] Captura lista: {opt_path}. Consultando Gemini...")

    success, response_text, elapsed = gemini.analyze_image(opt_path)
    print(f"[Cina-Win] Respuesta obtenida en {elapsed:.2f}s:\n{response_text}")

    # Limpieza
    for p in [raw_path, opt_path]:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    if success:
        print("[Cina-Win] Reproduciendo audio de respuesta...")
        tts._speak_worker(response_text)
    else:
        print(f"[Cina-Win] Error: {response_text}")
        tts._speak_worker(f"Error de Gemini: {response_text}")


def handle_trigger():
    """Envía la señal a la app en segundo plano vía TCP o ejecuta captura directa."""
    if IPCClient.is_server_running():
        print("[Cina-Win] Notificando a la aplicación activa en segundo plano vía TCP...")
        if IPCClient.send_trigger():
            print("[Cina-Win] Disparo enviado con éxito.")
            return
        else:
            print("[Cina-Win] No se pudo enviar el comando vía socket TCP. Iniciando modo autónomo...")

    run_oneshot()


def run_headless():
    """Ejecuta el demonio en segundo plano sin ventana gráfica en Windows."""
    import time
    print("[Cina-Win] Iniciando en modo demonio (Headless)... Presiona Ctrl+C para salir.")
    hotkey = HotkeyService(
        hotkey_str=config_mgr.get("hotkey", "<ctrl>+<alt>+s"),
        on_trigger=run_oneshot
    )
    hotkey.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Cina-Win] Deteniendo demonio...")
        hotkey.stop()


def main():
    parser = argparse.ArgumentParser(description="Cina - Asistente de Pantalla y Audio con IA (Edición Windows)")
    parser.add_argument("--trigger", action="store_true", help="Disparar captura instantánea y locución")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en segundo plano sin ventana gráfica")

    args, _ = parser.parse_known_args()

    if args.trigger:
        handle_trigger()
        return

    if args.headless:
        run_headless()
        return

    # Iniciar GUI
    from cina.gui import CinaApp
    root = tk.Tk()
    app = CinaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

