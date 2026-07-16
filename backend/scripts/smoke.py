from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request


def find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def main() -> int:
    port = find_available_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        last_error = ""
        for _ in range(30):
            time.sleep(0.5)
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=2)
                if stdout:
                    print(stdout)
                if stderr:
                    print(stderr, file=sys.stderr)
                return process.returncode or 1
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health",
                    timeout=2,
                ) as response:
                    body = response.read().decode("utf-8")
                print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
                return 0
            except Exception as exc:
                last_error = str(exc)
        print(f"health check failed: {last_error}", file=sys.stderr)
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
