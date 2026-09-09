"""通过 Android WebView CDP 验证实际 APK 与 HTTPS simulation ControlHost。"""

import os
from playwright.sync_api import sync_playwright


def main() -> None:
    port = os.environ.get("SCP_CV_ANDROID_CDP_PORT", "9228")
    host_origin = os.environ.get("SCP_CV_HOST_ORIGIN", "https://localhost:7241")
    username = os.environ.get("SCP_CV_QA_USERNAME", "operator")
    password = os.environ.get("SCP_CV_QA_PASSWORD", "Security-password-123")
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        page = browser.contexts[0].pages[0]
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        inputs = page.locator("input")
        assert inputs.count() >= 2
        inputs.nth(0).fill(host_origin)
        inputs.nth(1).fill("Android AVD QA")
        page.get_by_role("button", name="保存并检测连接").click()
        page.get_by_role("button", name="登录此主机").wait_for(timeout=15000)
        page.get_by_role("button", name="登录此主机").click()
        inputs = page.locator("input")
        inputs.nth(0).fill(username)
        inputs.nth(1).fill(password)
        page.locator("button").filter(has_text="登录").click()
        page.wait_for_url("**/dashboard", timeout=15000)
        page.get_by_text("控制链路已连接").first.wait_for(timeout=15000)
        assert page.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth")
        assert not errors, "\n".join(errors)


if __name__ == "__main__":
    main()
