import os
import sys
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image

# En Windows, asegurar DPI Awareness para capturar la resolución completa sin recortes por escala (125%/150%)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ScreenCapture:
    def __init__(self, preferred_backend: str = "pillow"):
        self.backend = "pillow"
        print(f"[Capture] Backend de captura para Windows: {self.backend} (PIL ImageGrab nativo)")

    def capture_silent(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        Captura de pantalla silenciosa e invisible en Windows:
        - Sin sonido
        - Sin ventana emergente
        - Sin notificación
        - Sin robar foco
        """
        if not output_path:
            tmp_fd, output_path = tempfile.mkstemp(prefix="cina_win_raw_", suffix=".png")
            os.close(tmp_fd)

        output_path = os.path.abspath(output_path)

        try:
            from PIL import ImageGrab

            # En Windows all_screens=True captura la totalidad de monitores activos
            try:
                img = ImageGrab.grab(all_screens=True)
            except TypeError:
                img = ImageGrab.grab()

            img.save(output_path, "PNG")

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return output_path
            else:
                print("[Capture] Error: Archivo de captura vacío.")
                return None
        except Exception as e:
            print(f"[Capture] Falló ImageGrab en Windows: {e}")
            return None

    @staticmethod
    def optimize_image(input_path: str, max_width: int = 1920, quality: int = 85) -> str:
        """
        Optimiza y comprime la imagen para acelerar el envío a Gemini (reduce latencia).
        Mantiene la nitidez para la lectura de texto pero reduce el tamaño a ~200-400KB.
        """
        try:
            optimized_path = input_path.replace(".png", "_opt.jpg")
            with Image.open(input_path) as img:
                # Convertir a RGB si tiene canal Alpha
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Redimensionar si excede el tamaño máximo manteniendo proporción
                w, h = img.size
                if w > max_width:
                    ratio = max_width / float(w)
                    new_h = int(float(h) * ratio)
                    img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

                img.save(optimized_path, "JPEG", quality=quality, optimize=True)

            return optimized_path
        except Exception as e:
            print(f"[Capture] Error al optimizar imagen: {e}. Usando imagen original.")
            return input_path

