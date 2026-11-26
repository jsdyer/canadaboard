"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import os
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                expect(page.locator(".card")).to_have_count(6)
                expect(page.locator("#checked")).to_contain_text("Sources checked")
                page.get_by_role("button",name="Pin Inflation",exact=True).click()
                page.reload()
                page.locator("#pins").click()
                expect(page.locator(".card")).to_have_count(1)
                expect(page.locator(".card")).to_contain_text("Inflation")
                page.locator("[data-range='36']").click()
                expect(page.locator("#status")).to_contain_text("36 months")
                with page.expect_download() as download:
                    page.locator("#export").click()
                assert download.value.suggested_filename == 'canada-board-observations.csv'
                page.locator("#pins").click()
                page.locator(".card details").first.click()
                expect(page.locator(".card table").first).to_be_visible()
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: project subpath, actual indicators, pin persistence, periods, CSV, table and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
