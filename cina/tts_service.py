import os
import re
import sys
import shutil
import asyncio
import tempfile
import subprocess
import threading
from typing import Optional, Callable


class TTSService:
    def __init__(self, voice: str = "es-ES-AlvaroNeural", rate: str = "+0%", volume: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_requested = False

    def clean_text_for_speech(self, text: str) -> str:
        """Limpia caracteres de markdown y formato para que suene natural al hablar."""
        if not text:
            return ""
        # Quitar bloques de código
        text = re.sub(r"```[\s\S]*?```", " código omitido ", text)
        # Quitar enlaces [texto](url)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Quitar negritas y cursivas (**texto**, *texto*, __texto__)
        text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
        # Quitar encabezados (# Header)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        # Quitar viñetas (- o * al inicio)
        text = re.sub(r"^[\*\-\+]\s*", "", text, flags=re.MULTILINE)
        # Quitar números de lista al inicio de línea
        text = re.sub(r"^\d+\.\s*", "", text, flags=re.MULTILINE)
        # Limpiar saltos de línea excesivos
        text = re.sub(r"\n+", ". ", text)
        # Limpiar espacios extra
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def stop(self):
        """Detiene cualquier audio que se esté reproduciendo actualmente."""
        self._stop_requested = True
        with self._lock:
            # Si estamos en Windows, detener dispositivo MCI si estaba reproduciendo
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.winmm.mciSendStringW("stop cina_audio", None, 0, None)
                    ctypes.windll.winmm.mciSendStringW("close cina_audio", None, 0, None)
                except Exception:
                    pass

            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=0.5)
                except Exception:
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass
                self.current_process = None
            self._is_speaking = False

    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak_async(self, text: str, voice: Optional[str] = None, on_start: Optional[Callable] = None, on_finish: Optional[Callable] = None):
        """Genera y reproduce el audio en un hilo independiente sin bloquear."""
        thread = threading.Thread(target=self._speak_worker, args=(text, voice, on_start, on_finish), daemon=True)
        thread.start()

    def _speak_worker(self, text: str, voice: Optional[str] = None, on_start: Optional[Callable] = None, on_finish: Optional[Callable] = None):
        self.stop()
        self._stop_requested = False
        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            if on_finish:
                on_finish()
            return

        target_voice = voice or self.voice
        tmp_mp3 = tempfile.mktemp(prefix="cina_tts_", suffix=".mp3")

        self._is_speaking = True
        if on_start:
            try:
                on_start()
            except Exception as e:
                print(f"[TTS] on_start error: {e}")

        success = False
        try:
            # 1. Intentar con Edge-TTS (Voz neuronal natural en español)
            success = self._generate_edge_tts(clean_text, target_voice, tmp_mp3)
            if success and os.path.exists(tmp_mp3) and os.path.getsize(tmp_mp3) > 100 and not self._stop_requested:
                self._play_audio(tmp_mp3)
            elif not self._stop_requested:
                # 2. Fallback offline con SAPI en Windows (o espeak)
                print("[TTS] Fallback a motor TTS local...")
                self._speak_fallback(clean_text)
        except Exception as e:
            print(f"[TTS] Error en síntesis de voz: {e}")
            if not self._stop_requested:
                self._speak_fallback(clean_text)
        finally:
            self._is_speaking = False
            if os.path.exists(tmp_mp3):
                try:
                    os.remove(tmp_mp3)
                except Exception:
                    pass
            if on_finish:
                try:
                    on_finish()
                except Exception as e:
                    print(f"[TTS] on_finish error: {e}")

    def _generate_edge_tts(self, text: str, voice: str, output_path: str) -> bool:
        """Usa la librería edge-tts para generar el archivo mp3."""
        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(text, voice, rate=self.rate, volume=self.volume)
                await communicate.save(output_path)

            asyncio.run(_run())
            return True
        except Exception as e:
            print(f"[TTS] Error ejecutando edge-tts: {e}")
            return False

    def _speak_fallback(self, text: str):
        """Fallback local offline: SAPI en Windows o espeak en Linux."""
        safe_text = text.replace('"', ' ').replace("'", " ")

        if sys.platform == "win32":
            # Usar Windows Speech API (SAPI) nativo de Windows (voces Helena, Sabina, etc.)
            cmd = [
                "powershell",
                "-NoProfile",
                "-WindowStyle", "Hidden",
                "-Command",
                f"(New-Object -ComObject SAPI.SpVoice).Speak('{safe_text}')"
            ]
        elif shutil.which("espeak-ng"):
            cmd = ["espeak-ng", "-v", "es", text]
        elif shutil.which("espeak"):
            cmd = ["espeak", "-v", "es", text]
        else:
            print("[TTS] No hay sintetizador de voz disponible.")
            return

        with self._lock:
            if self._stop_requested:
                return
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.current_process.wait()
        with self._lock:
            self.current_process = None

    def _play_audio(self, audio_file: str):
        """Reproduce un archivo de audio con el reproductor nativo del sistema operativo."""
        if self._stop_requested:
            return

        # 1. EN WINDOWS: Usar Windows Multimedia MCI API nativa (ctypes winmm.dll)
        if sys.platform == "win32":
            try:
                import ctypes
                winmm = ctypes.windll.winmm
                kernel32 = ctypes.windll.kernel32

                # Cerrar reproducciones previas si las hubiera
                winmm.mciSendStringW("close cina_audio", None, 0, None)

                # Obtener ruta corta (8.3) para evitar problemas con espacios en rutas de Windows
                short_buf = ctypes.create_unicode_buffer(1024)
                kernel32.GetShortPathNameW(audio_file, short_buf, 1024)
                clean_path = short_buf.value or audio_file

                open_cmd = f'open "{clean_path}" type mpegvideo alias cina_audio'
                err = winmm.mciSendStringW(open_cmd, None, 0, None)
                if err == 0:
                    with self._lock:
                        if self._stop_requested:
                            winmm.mciSendStringW("close cina_audio", None, 0, None)
                            return

                    # Reproducir y esperar término
                    winmm.mciSendStringW("play cina_audio wait", None, 0, None)
                    winmm.mciSendStringW("close cina_audio", None, 0, None)
                    return
                else:
                    print(f"[TTS] winmm MCI devolvió código de error {err}, recurriendo a reproductor secundario...")
            except Exception as e_mci:
                print(f"[TTS] Excepción en winmm MCI: {e_mci}")

        # 2. EN WINDOWS FALLBACK: PowerShell MediaPlayer
        if sys.platform == "win32":
            ps_cmd = (
                f"Add-Type -AssemblyName presentationCore; "
                f"$mp = New-Object system.windows.media.mediaplayer; "
                f"$mp.open([uri]'{audio_file}'); $mp.Play(); "
                f"Start-Sleep -Milliseconds 500; "
                f"while($mp.NaturalDuration.HasTimeSpan -and ($mp.Position -lt $mp.NaturalDuration.TimeSpan)) {{ Start-Sleep -Milliseconds 100 }}"
            )
            cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd]
            try:
                with self._lock:
                    if self._stop_requested:
                        return
                    self.current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.current_process.wait()
            except Exception as e_ps:
                print(f"[TTS] Falló reproducción PowerShell: {e_ps}")
            finally:
                with self._lock:
                    self.current_process = None
            return

        # 3. EN LINUX / OTROS SISTEMAS:
        player_cmd = None
        if shutil.which("pw-play"):
            player_cmd = ["pw-play", audio_file]
        elif shutil.which("mpv"):
            player_cmd = ["mpv", "--no-video", audio_file]
        elif shutil.which("ffplay"):
            player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file]
        elif shutil.which("paplay"):
            player_cmd = ["paplay", audio_file]

        if not player_cmd:
            print("[TTS] No se encontró reproductor de audio compatible.")
            return

        try:
            with self._lock:
                if self._stop_requested:
                    return
                self.current_process = subprocess.Popen(player_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.current_process.wait()
        except Exception as e:
            print(f"[TTS] Error durante reproducción de audio: {e}")
        finally:
            with self._lock:
                self.current_process = None

