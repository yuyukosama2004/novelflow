from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request


def main() -> int:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
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
                with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2) as response:
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
