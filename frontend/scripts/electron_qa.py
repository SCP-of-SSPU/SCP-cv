import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        port = os.environ.get("SCP_CV_ELECTRON_CDP_PORT", "9222")
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        pages = [candidate for context in browser.contexts for candidate in context.pages]
        assert pages, "打包 Electron 未打开渲染页面"
        page = next((candidate for candidate in pages if candidate.url.startswith("app://scp-cv/")), pages[0])
        page.on("console", lambda message: errors.append(f"console: {message.type}: {message.text}") if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)
        assert page.get_by_text("连接播放主机").is_visible()
        page.screenshot(path=str(Path("docs/qa/003-electron.png")), full_page=True)
        assert page.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth")
        if errors:
            raise AssertionError("\n".join(errors))
        # connect_over_cdp 的 browser.close 会关闭被测 Electron；由外层进程按 PID 清理。


if __name__ == "__main__":
    main()
