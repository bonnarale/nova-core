import json
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main() -> int:
    try:
        with urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return 0 if response.status == 200 and payload.get("status") == "ok" else 1
    except (OSError, URLError, json.JSONDecodeError):
        return 1


if __name__ == "__main__":
    sys.exit(main())

