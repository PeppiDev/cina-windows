import os
import io
import re
import json
import base64
import time
from typing import Optional, Tuple, List
from PIL import Image

SYSTEM_PROMPT = """
Eres un asistente de voz en tiempo real especializado en resolver dudas, preguntas y exámenes que aparecen en la pantalla del usuario.

Tu tarea:
1. Analiza cuidadosamente la captura de pantalla suministrada.
2. Determina si contiene preguntas, cuestionarios, exámenes tipo test, problemas matemáticos, ejercicios de programación o dudas teóricas.
3. SI DETECTAS PREGUNTAS:
   - Responde de forma directa, concisa y ordenada.
   - Si es opción múltiple: Indica el número de la pregunta o su tema, cuál es la opción correcta (ejemplo: "Opción B") y da una explicación breve de una o dos oraciones con la justificación.
   - Si es un problema de desarrollo o código: Da la solución directa y el razonamiento clave.
   - Prioriza la claridad para que el usuario entienda inmediatamente al escucharlo.
4. SI NO DETECTAS PREGUNTAS:
   - Di exactamente: "No se han detectado preguntas en la pantalla." y añade en una sola frase qué contenido o aplicación se está visualizando.
5. FORMATO OBLIGATORIO PARA AUDIO:
   - Tu respuesta será leída en voz alta por un sintetizador de voz (TTS) en los auriculares del usuario.
   - NO uses asteriscos (*), almohadillas (#), tablas markdown ni fórmulas complejas.
   - Usa un lenguaje hablado, natural, fluido y en español neutro o directo.
"""

def clean_key(raw: str) -> str:
    """Sanitiza y limpia una clave de API eliminando comillas, espacios y prefijos accidentales."""
    if not raw:
        return ""
    k = str(raw).strip()
    for prefix in ["export ", "set "]:
        if k.lower().startswith(prefix):
            k = k[len(prefix):].strip()
    if "=" in k and not k.startswith("AQ.") and not k.startswith("AIza"):
        k = k.split("=", 1)[1].strip()
    k = k.strip(' \t\r\n\'"“”«»')
    return k


class GeminiService:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.7-flash"):
        self.raw_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        self.api_keys = self._parse_keys(self.raw_api_key)
        self.current_key_idx = 0
        self.model = model or "gemini-3.7-flash"

    def _parse_keys(self, key_str: str) -> List[str]:
        """Permite configurar varias claves separadas por comas, punto y coma o saltos de línea."""
        if not key_str:
            return []
        tokens = re.split(r"[,;\n\r]+", key_str)
        cleaned = []
        for t in tokens:
            ck = clean_key(t)
            if ck and ck not in cleaned:
                cleaned.append(ck)
        return cleaned

    def set_api_key(self, api_key: str):
        self.raw_api_key = api_key
        self.api_keys = self._parse_keys(api_key)
        self.current_key_idx = 0

    def set_model(self, model: str):
        if model:
            self.model = model

    def _get_active_key(self) -> str:
        if not self.api_keys:
            return ""
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def _rotate_key(self):
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            print(f"[GeminiService] Rotando a clave de API #{self.current_key_idx + 1}")

    def _get_model_candidates(self) -> List[str]:
        """Devuelve la lista ordenada de modelos con fallback automático."""
        candidates = []
        if self.model:
            candidates.append(self.model)

        fallbacks = [
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-latest",
            "gemini-2.5-flash"
        ]
        for m in fallbacks:
            if m not in candidates:
                candidates.append(m)
        return candidates

    def _format_429_error(self, raw_error: str) -> str:
        """Extrae el tiempo de espera en segundos y genera un mensaje limpio para locución y lectura."""
        match = re.search(r"retry in\s*([\d\.]+)\s*s", raw_error, re.IGNORECASE)
        if match:
            secs = int(float(match.group(1))) + 1
            return (
                f"Límite de solicitudes alcanzado en Gemini. "
                f"Por favor espera {secs} segundos para volver a consultar, "
                f"o añade una clave de respaldo en los ajustes."
            )
        return (
            "Límite de solicitudes alcanzado en la cuota gratuita de Gemini. "
            "Por favor espera unos segundos antes de volver a capturar, "
            "o añade otra clave de API en la configuración."
        )

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba rápida de la API key activa para validación inmediata en la interfaz."""
        if not self.api_keys:
            return False, "No hay ninguna clave de API configurada. Pega tu API Key de Google AI Studio."

        key = self._get_active_key()
        try:
            from google import genai
            client = genai.Client(api_key=key)

            # Probar con el modelo principal
            models_to_try = self._get_model_candidates()
            last_err = ""
            for m in models_to_try[:3]:
                try:
                    res = client.models.generate_content(
                        model=m,
                        contents="Hola, responde únicamente 'OK'."
                    )
                    if res and res.text:
                        return True, f"✅ Conexión exitosa con Gemini (Modelo: {m})."
                except Exception as e:
                    last_err = str(e)
                    if "400" in last_err and "API_KEY_INVALID" in last_err:
                        return False, "❌ La API Key no es válida. Asegúrate de copiar la clave correcta desde https://aistudio.google.com/."
                    if "403" in last_err or "PERMISSION_DENIED" in last_err:
                        return False, "❌ Permiso denegado: Tu clave no tiene permisos para usar la API de Gemini."
                    continue

            return False, f"❌ Error al probar la clave: {last_err}"
        except Exception as e_test:
            return False, f"❌ Error de inicialización: {e_test}"

    def analyze_image(self, image_path: str) -> Tuple[bool, str, float]:
        """
        Envía la captura de pantalla a Gemini implementando:
        1. Limpieza de claves y detección de claves inválidas con mensaje claro.
        2. Fallback automático entre modelos (3.7-flash, 3.6-flash, 3.5-flash-lite).
        3. Rotación de múltiples claves ante cuotas 429.
        """
        if not self.api_keys:
            return False, "Por favor ingresa tu API Key de Gemini en el campo superior y presiona 'Guardar' o 'Probar Clave'.", 0.0

        t0 = time.time()
        last_429_error = None
        last_invalid_key_error = False
        models_to_try = self._get_model_candidates()

        try:
            with Image.open(image_path) as img:
                img_copy = img.copy()
        except Exception as e_img:
            return False, f"Error al leer la imagen de captura: {e_img}", 0.0

        for key_attempt in range(len(self.api_keys)):
            current_key = self._get_active_key()

            for current_model in models_to_try:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=current_key)
                    cfg = types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=1000
                    )

                    print(f"[GeminiService] Consultando Gemini (Modelo: {current_model}, Clave #{self.current_key_idx + 1})...")
                    response = client.models.generate_content(
                        model=current_model,
                        contents=[img_copy, SYSTEM_PROMPT],
                        config=cfg
                    )

                    elapsed = time.time() - t0
                    text = response.text or "No se obtuvo respuesta de Gemini."

                    if current_model != self.model:
                        print(f"[GeminiService] Resuelto exitosamente con modelo alternativo: {current_model}")

                    return True, text.strip(), elapsed

                except Exception as e_sdk:
                    err_str = str(e_sdk)
                    print(f"[GeminiService] Error en modelo {current_model} con clave #{self.current_key_idx + 1}: {err_str}")

                    # Error de cuota 429
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                        last_429_error = err_str
                        continue

                    # Error de modelo no encontrado 404
                    if "404" in err_str or "NOT_FOUND" in err_str:
                        continue

                    # Clave de API inválida 400/403
                    if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "403" in err_str:
                        last_invalid_key_error = True
                        break

            if len(self.api_keys) > 1:
                self._rotate_key()

        elapsed = time.time() - t0
        if last_429_error:
            friendly_msg = self._format_429_error(last_429_error)
            print(f"[GeminiService] Cuota agotada: {friendly_msg}")
            return False, friendly_msg, elapsed

        if last_invalid_key_error:
            msg = "La API Key de Gemini ingresada no es válida. Por favor verifica que tu clave sea correcta en Google AI Studio (aistudio.google.com) y no contenga comillas ni espacios extra."
            print(f"[GeminiService] Clave inválida: {msg}")
            return False, msg, elapsed

        # Fallback final vía REST
        try:
            import requests

            with open(image_path, "rb") as f:
                img_bytes = f.read()

            mime_type = "image/jpeg" if image_path.endswith((".jpg", ".jpeg")) else "image/png"
            b64_data = base64.b64encode(img_bytes).decode("utf-8")

            active_key = self._get_active_key()
            for m in models_to_try[:2]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={active_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": SYSTEM_PROMPT},
                                {"inline_data": {"mime_type": mime_type, "data": b64_data}}
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}
                }

                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                elapsed = time.time() - t0

                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return True, text.strip(), elapsed
                elif resp.status_code == 429:
                    return False, self._format_429_error(resp.text), elapsed
                elif resp.status_code in (400, 403) and ("API_KEY_INVALID" in resp.text or "API key not valid" in resp.text):
                    return False, "La API Key de Gemini no es válida. Por favor revísala en Google AI Studio.", elapsed

            return False, f"Error en los servidores de Gemini ({resp.status_code}). Verifica tu conexión o intenta con otro modelo.", elapsed

        except Exception as e_rest:
            elapsed = time.time() - t0
            return False, f"Error de conexión con Google Gemini: {e_rest}", elapsed
