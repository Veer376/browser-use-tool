# filepath: c:\Users\aryav\projects\orbitagent\browser_use_agent\services\browser.py
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from google.genai import types
import io
from typing import Optional, Any
from pydantic import BaseModel

# Example improvement (conceptual):
class BrowserActionResult(BaseModel):
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
    
DEBUG_MODE = True

def correct_coordinates(x, y, viewport_width=1280, viewport_height=800):
    
    model_coord_range = 1000.0

    x_scale_factor = viewport_width / model_coord_range
    y_scale_factor = viewport_height / model_coord_range

    x_original = x * x_scale_factor
    y_original = y * y_scale_factor

    return x_original, y_original


class Browser:    
    def __init__(self, viewport_width=1280, viewport_height=800):
        try:
            # Standard viewport size that provides good visibility for most web content
            # 1280x800 is a common resolution that works well for most websites
            self.viewport_width = viewport_width
            self.viewport_height = viewport_height
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=False, # Keep False for debugging, True for headless
                chromium_sandbox=True,
                env={},
                args=["--disable-extensions", "--disable-file-system"]
            )
            self.page = self.browser.new_page()
            self.page.set_viewport_size({"width": viewport_width, "height": viewport_height})
            print(f"[BROWSER] Browser initialized with viewport: {viewport_width}x{viewport_height}")
            
            self.iteration_count = 0
            self.last_screenshot_path = None

        except Exception as e:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()

    def navigate(self, url: str):
        try:
            self.page.goto(url, wait_until='load', timeout=60000) # Wait for load, reasonable timeout
            return {
                "success": True,
                "message": f"Successfully navigated to {url}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error navigating to {url}: {str(e)}",
            }
            
    def close(self):
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
            return {
                "success": True,
                "message": "Browser successfully closed",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error closing browser: {str(e)}",
            }
            
    def screenshot_bytes(self, iteration=None) -> types.Part:
        try:
            screenshot_bytes = self.page.screenshot()
            return screenshot_bytes
        except Exception as e:
            return str(e)

    def screenshot_part(self):
        try:
            # Take the screenshot
            screenshot_bytes = self.page.screenshot()
            
            # Convert to Part object for the model
            # image_stream = io.BytesIO(screenshot_bytes)
            # img = Image.open(image_stream)
            # img = img.convert('L') # Keep color for better model interpretation
            
            # Optional resizing (consider if needed for performance vs. model accuracy)
            # scale_factor = min(640 / width, 640 / height)
            # new_width = int(width * scale_factor)
            # new_height = int(height * scale_factor)
            # img = img.resize((new_width, new_height))
            
            # output_stream = io.BytesIO()
            # # Use PNG for lossless quality, JPEG if size is critical
            # img.save(output_stream, format="PNG")
            # output_bytes = output_stream.getvalue()
            
            part_data = types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=screenshot_bytes,
                )
            )
            return {
                "success": True,
                "message": "Screenshot part captured successfully",
                "data": part_data
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error taking screenshot part: {str(e)}",
            }
            
    def click(self, x: float, y: float, label: str = None, button: str = "left", timeout: int = 5000, delay_after: int = 500):
        
        label = label or '[no label provided]'
        
        try:
            # Convert from model coordinates (0-1000 scale) to actual page coordinates
            # using the current viewport dimensions
            x_orig, y_orig = correct_coordinates(
                x=x, 
                y=y, 
                viewport_width=self.viewport_width, 
                viewport_height=self.viewport_height
            )
            
            # Execute the click
            self.page.mouse.click(x_orig, y_orig, button=button)
            self.page.wait_for_timeout(delay_after)
            return {
                "success": True,
                "message": f"Successfully clicked at coordinates ({x},{y}), label: '{label}'",
            }
        except Exception as e:
            print(f"[BROWSER] ERROR clicking: {e}")
            return {
                "success": False,
                "message": f"Error clicking at coordinates ({x},{y}): {str(e)}",
            }
            
    def scroll(self, direction: str = "down", amount: int = 500, x: float = None, y: float = None, delay_after: int = 500):
        
        try:
            if x is not None and y is not None:
                x_orig, y_orig = correct_coordinates(
                    x=x, 
                    y=y, 
                    viewport_width=self.viewport_width, 
                    viewport_height=self.viewport_height
                )
                self.page.mouse.move(x_orig, y_orig)
            
            scroll_delta_y = amount if direction == "down" else -amount
            
            self.page.mouse.wheel(0, scroll_delta_y)
            self.page.wait_for_timeout(delay_after)
            return {
                "success": True,
                "message": f"Successfully scrolled {direction} by {amount} pixels",
            }
        except Exception as e:
            return {
                "success": False,                
                "message": f"Error scrolling {direction}: {str(e)}",
            }
            
    def type_text(self, text: str, label: str = None, delay: int = 50, timeout: int = 10000, delay_after: int = 200):
        label = label or '[no field label provided]'
        try:
            self.page.keyboard.type(text, delay=delay)
            self.page.wait_for_timeout(delay_after)
            return {
                "success": True,
                "message": f"Typed text: '{text}' into field: '{label}'",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error typing text '{text}': {str(e)}",                
            }
            
    def press_keys(self, keys, delay_after: int = 200):
        try:
            pressed_keys = []
            for key in keys:
                pw_key = key
                if key.lower() == "enter":
                    pw_key = "Enter"
                elif key.lower() == "tab":
                    pw_key = "Tab"
                elif key.lower() == "escape" or key.lower() == "esc":
                    pw_key = "Escape"
                
                print(f"[BROWSER] Pressing key: '{pw_key}'")
                self.page.keyboard.press(pw_key)
                pressed_keys.append(pw_key)
                
                if pw_key == "Enter":
                    try:
                        self.page.wait_for_load_state("load", timeout=10000)
                    except Exception as e:
                        try:
                            self.page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception as ne:
                            self.page.wait_for_timeout(2000)
                else:
                    self.page.wait_for_timeout(delay_after)
            return {
                "success": True,
                "message": f"Successfully pressed keys: {', '.join(pressed_keys)}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error pressing keys: {str(e)}",              
            }
            
    def go_back(self, delay_after: int = 1000):
        try:
            self.page.go_back()
            self.page.wait_for_timeout(delay_after)
            return {
                "success": True,
                "message": "Successfully navigated back to previous page",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error navigating back: {str(e)}",
            }
