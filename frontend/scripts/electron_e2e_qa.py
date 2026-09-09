"""验证实际打包 Electron 与 HTTPS simulation ControlHost 的会话/SSE。"""

import os
from playwright.sync_api import sync_playwright


def main() -> None:
    port = os.environ.get("SCP_CV_ELECTRON_CDP_PORT", "9227")
    host_origin = os.environ.get("SCP_CV_HOST_ORIGIN", "https://localhost:7241")
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        page = browser.contexts[0].pages[0]
        result = page.evaluate("""
            async (origin) => {
              try {
                const response = await fetch(`${origin}/api/auth/csrf/`, {
                  credentials: 'include',
                });
                const body = await response.json();
                return { status: response.status, csrfTokenPresent: Boolean(body.csrfToken) };
              } catch (error) {
                return { error: String(error) };
              }
            }
        """, host_origin)
        assert "error" not in result, result["error"]
        assert result["status"] == 200
        assert result["csrfTokenPresent"]
        print(result, flush=True)
        cookies = page.context.cookies(host_origin)
        print(
            [{"name": cookie["name"], "secure": cookie["secure"], "sameSite": cookie["sameSite"]} for cookie in cookies],
            flush=True,
        )


if __name__ == "__main__":
    main()
