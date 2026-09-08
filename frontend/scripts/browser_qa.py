from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        for width, height, label in [(1440, 900, "desktop"), (768, 1024, "tablet"), (390, 844, "mobile")]:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            page.on("console", lambda message: errors.append(f"console {label}: {message.type}: {message.text}") if message.type == "error" else None)
            page.on("pageerror", lambda error: errors.append(f"pageerror {label}: {error}"))
            page.goto("http://127.0.0.1:4173/login", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(Path("docs/qa") / f"003-browser-{label}.png"), full_page=True)
            if page.get_by_text("欢迎使用 SCP-cv 播放控制台").count():
                inputs = page.locator("input")
                assert inputs.count() >= 2
                assert inputs.nth(0).is_visible()
                assert inputs.nth(1).is_visible()
            else:
                assert page.get_by_text("首页").first.is_visible() or page.get_by_text("播放控制台").first.is_visible()
            assert page.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth")
            page.close()
        browser.close()
    if errors:
        raise AssertionError("\n".join(errors))


if __name__ == "__main__":
    main()
