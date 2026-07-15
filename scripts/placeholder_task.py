import os
import sys
from urllib.parse import quote_plus

# playwright is provided by the worker Docker image, not the app venv (py3.8)
from playwright.sync_api import Page, sync_playwright  # type: ignore

DEFAULT_QUERY = "BraveBird AI"
RESULT_COUNT = 5
CONSENT_LABELS = ("Accept all", "Accept the use of cookies and other data", "I agree", "Accept")


def run_search(query: str) -> int:
    print(f"[worker] launching browser for query: {query!r}", flush=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en&gl=us"
            print(f"[worker] navigating to {url}", flush=True)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            _accept_consent(page)

            page.wait_for_selector("#search, #rso", timeout=15000)
            print(f"[worker] results page loaded: {page.title()!r}", flush=True)
            results = _extract_results(page, RESULT_COUNT)
        finally:
            browser.close()

    if not results:
        print("[worker] no results captured (consent wall or CAPTCHA?)", flush=True)
        return 1

    print(f"[worker] captured top {len(results)} results:", flush=True)
    for rank, (title, link) in enumerate(results, start=1):
        print(f"{rank}. {title}", flush=True)
        print(f"   {link}", flush=True)
    return 0


def _accept_consent(page: Page) -> None:
    for label in CONSENT_LABELS:
        try:
            button = page.get_by_role("button", name=label)
            if button.count() > 0:
                button.first.click(timeout=3000)
                page.wait_for_load_state("domcontentloaded")
                print(f"[worker] dismissed consent via {label!r}", flush=True)
                return
        except Exception:
            continue


def _extract_results(page: Page, limit: int):
    results = []
    headings = page.locator("#search h3, #rso h3")
    for idx in range(headings.count()):
        if len(results) >= limit:
            break
        heading = headings.nth(idx)
        title = (heading.inner_text() or "").strip()
        if not title:
            continue
        anchor = heading.locator("xpath=ancestor::a[1]")
        if anchor.count() == 0:
            continue
        link = anchor.first.get_attribute("href")
        if not link or not link.startswith("http"):
            continue
        results.append((title, link))
    return results


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "unnamed"
    query = (
        sys.argv[2]
        if len(sys.argv) > 2 and sys.argv[2]
        else os.environ.get("TASK_PAYLOAD") or DEFAULT_QUERY
    )
    print(f"[worker] starting task={name}", flush=True)
    try:
        return run_search(query)
    except Exception as exc:
        print(f"[worker] error: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
