import os
import socket
import threading
from typing import Callable, Optional
from cina.config import config_mgr

DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 47832

def get_tcp_port() -> int:
    return int(config_mgr.get("tcp_port", DEFAULT_TCP_PORT))


class IPCServer:
    def __init__(self, on_trigger: Callable[[], None]):
        self.on_trigger = on_trigger
        self.host = DEFAULT_TCP_HOST
        self.port = get_tcp_port()
        self.running = False
        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia el servidor IPC sobre localhost TCP en un hilo en segundo plano."""
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind((self.host, self.port))
            self._server_sock.listen(5)

            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            print(f"[IPC] Servidor TCP escuchando en {self.host}:{self.port}")
        except Exception as e:
            print(f"[IPC] Error al iniciar servidor en {self.host}:{self.port}: {e}")

    def _listen_loop(self):
        while self.running:
            try:
                conn, _ = self._server_sock.accept()
                with conn:
                    conn.settimeout(2.0)
                    data = conn.recv(1024).decode("utf-8", errors="ignore").strip()
                    if data == "TRIGGER":
                        conn.sendall(b"OK\n")
                        if self.on_trigger:
                            threading.Thread(target=self.on_trigger, daemon=True).start()
                    elif data == "PING":
                        conn.sendall(b"PONG\n")
                    elif data == "STOP":
                        conn.sendall(b"STOPPED\n")
            except Exception as e:
                if not self.running:
                    break

    def stop(self):
        self.running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None


class IPCClient:
    @staticmethod
    def is_server_running() -> bool:
        host = DEFAULT_TCP_HOST
        port = get_tcp_port()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((host, port))
                s.sendall(b"PING\n")
                resp = s.recv(1024).decode("utf-8", errors="ignore").strip()
                return resp == "PONG"
        except Exception:
            return False

    @staticmethod
    def send_trigger() -> bool:
        host = DEFAULT_TCP_HOST
        port = get_tcp_port()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((host, port))
                s.sendall(b"TRIGGER\n")
                resp = s.recv(1024).decode("utf-8", errors="ignore").strip()
                return resp == "OK"
        except Exception as e:
            print(f"[IPCClient] Error enviando trigger a {host}:{port}: {e}")
            return False

