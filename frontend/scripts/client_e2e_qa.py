"""在已启动的 Vite preview + simulation ControlHost 上验证共享 Web 流程。"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    frontend_url = os.environ.get("SCP_CV_FRONTEND_URL", "http://127.0.0.1:4176")
    username = os.environ.get("SCP_CV_QA_USERNAME", "operator")
    password = os.environ.get("SCP_CV_QA_PASSWORD", "Security-password-123")
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda message: errors.append(f"console: {message.type}: {message.text}") if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        page.goto(f"{frontend_url}/login", wait_until="domcontentloaded", timeout=15000)
        print("login page", page.url, page.locator("input").count(), flush=True)
        inputs = page.locator("input")
        assert inputs.count() >= 2
        inputs.nth(0).fill(username)
        inputs.nth(1).fill(password)
        page.get_by_role("button", name="登录", exact=True).click()
        print("submitted", flush=True)
        page.wait_for_url("**/dashboard", timeout=15000)
        page.get_by_text("播放控制台").first.wait_for(timeout=10000)
        assert page.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth")
        page.screenshot(path=str(Path("docs/qa/003-web-controlhost.png")), full_page=True)
        assert not errors, "\n".join(errors)
        browser.close()


if __name__ == "__main__":
    main()
