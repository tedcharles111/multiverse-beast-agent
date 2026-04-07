# agent/tools/screenshot_tools.py
import os
import tempfile
from PIL import Image
import mss
from playwright.sync_api import sync_playwright

def capture_desktop_screen(output_path: str = None) -> str:
    """
    Capture entire desktop screenshot (cross-platform).
    Returns file path.
    """
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(), f"desktop_screenshot_{int(time.time())}.png")
    with mss.mss() as sct:
        sct.shot(output=output_path)
    return output_path

def capture_web_element(url: str, selector: str, output_path: str = None, wait_ms: int = 2000) -> str:
    """
    Navigate to URL and screenshot a specific element using Playwright.
    """
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(), f"web_element_{int(time.time())}.png")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(wait_ms)
        element = page.locator(selector).first
        element.screenshot(path=output_path)
        browser.close()
    return output_path

def capture_full_page(url: str, output_path: str = None) -> str:
    """Screenshot entire webpage."""
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(), f"fullpage_{int(time.time())}.png")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    return output_path
