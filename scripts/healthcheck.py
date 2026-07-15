import sys

# playwright is provided by the worker Docker image, not the app venv (py3.8)
from playwright.sync_api import sync_playwright  # type: ignore


def check() -> bool:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            browser.close()
    except Exception as exc:
        print(f"[health] not ready: {exc}", flush=True)
        return False
    print("[health] ready", flush=True)
    return True


def main() -> int:
    return 0 if check() else 1


if __name__ == "__main__":
    raise SystemExit(main())
