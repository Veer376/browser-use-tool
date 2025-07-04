# filepath: c:\Users\aryav\projects\orbitagent\browser_use_agent\services\browser.py
from playwright.async_api import async_playwright, Page, Browser, Playwright
from google.genai import types
import io
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from .schema import BrowserActionResult
from ..utils.logger import browser_info, browser_error
class Browser:
    def __init__(self, use_debug_chrome: bool = False):
        self.viewport_width = 1280
        self.viewport_height = 800
        self.auto_switch_to_new_tabs = True 
        self.all_pages = [] 
        self.use_debug_chrome = use_debug_chrome
        self.chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" if use_debug_chrome else None
        self.debug_port = 9222 
        self.user_data_dir = "./chrome-user-data" if use_debug_chrome else None
        
        self.headless = False
    
    async def initialize(self):
        try:
            self.playwright = await async_playwright().start()
            
            # Common browser arguments for both modes
            browser_args = [
                "--disable-extensions", 
                "--disable-file-system", 
                "--start-maximized",
            ]
            
            # Add debug port if specified
            if self.debug_port:
                browser_args.append(f"--remote-debugging-port={self.debug_port}")
            
            # Common launch options for both modes
            common_options = {
                "headless": self.headless,
            }
            
            # Use custom Chrome path if specified
            if self.chrome_path:
                common_options["executable_path"] = self.chrome_path
                
            common_options["args"] = browser_args
            
            # Initialize browser based on chosen mode
            if self.use_debug_chrome:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    **common_options
                )
                
                self.browser = self.context
            else:
                # Launch standard sandboxed browser
                browser_info(f"Launching sandboxed browser")
                # In sandbox mode, we have a browser object that creates contexts
                self.browser = await self.playwright.chromium.launch(**common_options)
                self.context = await self.browser.new_context(no_viewport=True)  # No initial viewport in sandbox mode
            
            self.page = await self.context.new_page()
            
            # Initialize page tracking
            self.all_pages = list(self.context.pages)
            browser_info(f"Browser initialized with viewport")
            return True
        except Exception as e:
            browser_error(f"Error initializing browser: {e}")
            
            # Close context if it exists
            if hasattr(self, 'context') and self.context:
                await self.context.close()
                
            # Close browser if it's different from context
            if hasattr(self, 'browser') and self.browser and hasattr(self, 'context') and self.browser != self.context:
                await self.browser.close()
                
            # Always stop playwright
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                
            return False
                
    async def navigate(self, url: str) -> BrowserActionResult:
        try:
            # Store page count before navigation
            initial_pages = len(self.context.pages)
            
            await self.page.goto(url, wait_until='load', timeout=60000) # Wait for load, reasonable timeout
            
            browser_info(f"Navigated to {url} - Current page count: {len(self.context.pages)}")
            
            # Check if navigation created new tabs (redirects, popups, etc.)
            if len(self.context.pages) > initial_pages:
                await self._switch_to_newest_tab()
                
            return BrowserActionResult.create_success(
                action_type="navigate",
                message=f"Navigated to {url}",
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="navigate",
                message=f"Error navigating to {url}: {str(e)}",
            )
            
    async def close(self) -> BrowserActionResult:
        try:
            # Close context first
            if hasattr(self, 'context') and self.context:
                await self.context.close()
                
            # Only close browser separately if it's different from context
            # (In persistent mode, browser == context)
            if hasattr(self, 'browser') and self.browser and self.browser != self.context:
                await self.browser.close()
                
            # Always stop playwright
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                
            return BrowserActionResult.create_success(
                action_type="close",
                message="Browser successfully closed",
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="close",
                message=f"Error closing browser: {str(e)}",
            )

    async def screenshot_bytes(self, iteration=None) -> BrowserActionResult:
        try:
            screenshot_bytes = await self.page.screenshot()
            return BrowserActionResult.create_success(
                action_type="screenshot",
                message="Screenshot captured successfully",
                data=screenshot_bytes
            )
        except Exception as e:
            browser_error(f"Error taking screenshot: {e}")
            return BrowserActionResult.create_failure(
                action_type="screenshot",
                message=f"Error taking screenshot: {str(e)}",
            )   

    async def screenshot_part(self) -> BrowserActionResult:
        try:
            # Take the screenshot
            screenshot_bytes = await self.page.screenshot()
            
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
            return BrowserActionResult.create_success(
                action_type="screenshot",
                message="Screenshot part captured successfully",
                data={"part": part_data}
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="screenshot",
                message=f"Error taking screenshot part: {str(e)}",
            )
            
    async def click_coordinates(self, x: float = 0, y: float = 0, label: str = None, button: str = "left", timeout: int = 5000, delay_after: int = 500) -> BrowserActionResult:
        
        try:
            # Store page count before click
            initial_pages = len(self.context.pages)
            
            new_tab_opened = False
            
            await self.page.mouse.click(x, y)

            if len(self.context.pages) > initial_pages:
                new_tab_opened = await self._switch_to_newest_tab()
            
            success_message = f"Successfully clicked at coordinates ({x},{y}), label: '{label}'"
            if new_tab_opened:
                success_message += " - New tab opened, switched to it"
                
            return BrowserActionResult.create_success(
                action_type="click",
                message=success_message,
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="click",
                message=f"Error clicking at coordinates ({x},{y}): {str(e)}",
            )
            
    async def scroll(self, direction: str = "down", amount: int = 500, x: float = None, y: float = None, delay_after: int = 500) -> BrowserActionResult:
        
        try:
            await self.page.mouse.move(x, y)
            
            scroll_delta_y = amount if direction == "down" else -amount
            
            await self.page.mouse.wheel(0, scroll_delta_y)
            await self.page.wait_for_timeout(delay_after)
            return BrowserActionResult.create_success(
                action_type="scroll",
                message=f"Successfully scrolled {direction} by {amount} pixels",
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="scroll",
                message=f"Error scrolling {direction}: {str(e)}",
            )
            
    async def type(self, text: str, label: str = None, delay: int = 50, timeout: int = 10000, delay_after: int = 200) -> BrowserActionResult:
        label = label or '[NO LABEL]'
        try:
            focused = await self.page.evaluate("""
                () => {
                  const el = document.activeElement;
                  return {
                    tag: el?.tagName,
                    isContentEditable: el?.isContentEditable
                  }
                }
                """)
            
            if not (focused["tag"].upper() in ["INPUT", "TEXTAREA"] or focused["isContentEditable"]):
                raise ValueError("No focusable input field selected.")

            await self.page.keyboard.type(text, delay=delay)
            await self.page.wait_for_timeout(delay_after)
            return BrowserActionResult.create_success(
                action_type="type",
                message=f"Typed text: '{text}' into field: '{label}'",
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="type",
                message=f"Error typing text '{text}': {str(e)}",
            )
            
    async def press_keys(self, keys, delay_after: int = 200) -> BrowserActionResult:
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
                
                await self.page.keyboard.press(pw_key)
                pressed_keys.append(pw_key)
                
                if pw_key == "Enter":
                    try:
                        await self.page.wait_for_load_state("load", timeout=10000)
                    except Exception as e:
                        try:
                            await self.page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception as ne:
                            await self.page.wait_for_timeout(2000)
                else:
                    await self.page.wait_for_timeout(delay_after)
            return BrowserActionResult.create_success(
                action_type="press_keys",
                message=f"Successfully pressed keys: {', '.join(pressed_keys)}",
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="press_keys",
                message=f"Error pressing keys: {str(e)}",
            )
            
    async def go_back(self, delay_after: int = 1000) -> BrowserActionResult:
        try:
            await self.page.go_back()
            await self.page.wait_for_timeout(delay_after)
            return BrowserActionResult.create_success(
                action_type="go_back",
                message="🔙  Navigated back",
            )
        except Exception as e:
            return BrowserActionResult.create_failure(
                action_type="go_back",
                message=f"Error navigating back: {str(e)}",
            )
    
    async def show_pointer(self, x: float, y: float):
        try:

            await self.page.wait_for_load_state("domcontentloaded")
            
            js_code = """(coords) => {                // Remove existing pointer if any
                const existingPointer = document.getElementById('ai-pointer');
                if (existingPointer) existingPointer.remove();
                
                // Create pointer element
                const pointer = document.createElement('div');
                pointer.id = 'ai-pointer';                
                pointer.style.cssText = `
                    position: fixed;
                    width: 8px;
                    height: 8px;
                    background: rgba(255, 0, 0, 0.7);
                    border: 3px solid white;
                    border-radius: 50%;
                    pointer-events: none;
                    transform: translate(-50%, -50%);
                    z-index: 2147483647;
                    left: ${coords.x}px;
                    top: ${coords.y}px;
                    box-shadow: 0 0 15px red;
                `;
                
                // Add CSS animation
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes pulse {
                        0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                        50% { transform: translate(-50%, -50%) scale(1.5); opacity: 0.7; }
                        100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                    }
                    #ai-pointer {
                        animation: pulse 1s infinite;
                    }
                `;
                document.head.appendChild(style);
                
                // Append pointer to body
                document.body.appendChild(pointer);
                
                // Create ripple effect
                setInterval(() => {
                    const ripple = pointer.cloneNode();
                    ripple.style.animation = 'none';
                    document.body.appendChild(ripple);
                    ripple.animate([
                        { transform: 'translate(-50%, -50%) scale(1)', opacity: 0.5 },
                        { transform: 'translate(-50%, -50%) scale(2)', opacity: 0 }
                    ], {
                        duration: 1000,
                        easing: 'ease-out'
                    }).onfinish = () => ripple.remove();
                }, 2000);
                  // Verify pointer creation
                return !!document.getElementById('ai-pointer');}"""
            
            browser_info(f"Attempting to show pointer at coordinates: ({x}, {y})")
            # Pass coordinates as a dictionary to match the JavaScript parameters
            result = await self.page.evaluate(js_code, {'x': x, 'y': y})
            
            if result:
                browser_info(f"Pointer created successfully at ({x}, {y})")
                return BrowserActionResult.create_success(
                    action_type="show_pointer",
                    message=f"Successfully showed pointer at coordinates ({x},{y})",
                )
            else:
                raise Exception("Failed to create pointer element")
        except Exception as e:
            browser_error(f"Error showing pointer: {e}")
            return BrowserActionResult.create_failure(
                action_type="show_pointer",
                message=f"Error showing pointer: {str(e)}",
            )
        
    async def hide_pointer(self):
        """Remove the visual pointer."""
        try:
            js_code = """() => {
                const pointer = document.getElementById('ai-pointer');
                if (pointer) pointer.remove();
            }"""
            await self.page.evaluate(js_code)
            return BrowserActionResult.create_success(
                action_type="hide_pointer",
                message="Successfully removed pointer",
            )
        except Exception as e:
            browser_error(f"Error removing pointer: {e}")
            return BrowserActionResult.create_failure(
                action_type="hide_pointer",
                message=f"Error removing pointer: {str(e)}",
            )
    
    async def _switch_to_newest_tab(self):

        if not self.auto_switch_to_new_tabs:
            return False

        current_pages = self.context.pages
        # Trust the caller - they already detected new tabs
        newest_page = current_pages[-1]  # Get the most recent page
        
        # Update our tracking
        self.page = newest_page
        self.all_pages = list(current_pages)
        
        # Bring to front and ensure it's ready
        await self.page.bring_to_front()
        await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        
        # Set viewport size for the new tab
        await self.page.set_viewport_size({"width": self.viewport_width, "height": self.viewport_height})

        browser_info(f"🔄 Switched to new tab: {self.page.url}")
        return True
    
    def set_auto_switch_tabs(self, enabled: bool):
        """Enable or disable automatic switching to new tabs"""
        self.auto_switch_to_new_tabs = enabled
        browser_info(f"Auto-switch to new tabs: {'enabled' if enabled else 'disabled'}")
        
    async def get_all_tabs_info(self):
        """Get information about all open tabs"""
        tabs_info = []
        for i, page in enumerate(self.context.pages):
            try:
                title = await page.title()
                tabs_info.append({
                    "index": i,
                    "url": page.url,
                    "title": title,
                    "is_current": page == self.page
                })
            except Exception as e:
                tabs_info.append({
                    "index": i,
                    "url": page.url,
                    "title": f"Error getting title: {str(e)}",
                    "is_current": page == self.page
                })
        return tabs_info
    
    async def show_pointer_pro(self, x:float, y:float):
        try: 
            js_code = """
            (coords) => {
    // This is a self-contained function to create a radial splash animation at given coordinates.
    // It now includes a programmatically generated SVG cursor.

    const { x, y } = coords;

    // --- 1. Define and Inject CSS Keyframes ---
    // This part remains the same. It defines the animation for the splash lines.
    const styleId = 'radial-splash-animation-style';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.innerHTML = `
            @keyframes radial-splash-animation {
                0% {
                    transform: scaleY(0);
                    opacity: 1;
                }
                50% {
                    transform: scaleY(1);
                    opacity: 1;
                }
                100% {
                    transform: scaleY(1);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // --- 2. Create the Main Animation Container ---
    const container = document.createElement('div');
    container.style.position = 'fixed';
    container.style.left = `${x}px`;
    container.style.top = `${y}px`;
    container.style.pointerEvents = 'none';
    container.style.zIndex = '40';

    // --- NEW: Create the SVG Cursor Icon ---
    const svgNS = "http://www.w3.org/2000/svg";
    const cursorSvg = document.createElementNS(svgNS, "svg");

    // Set SVG attributes. The viewBox defines the coordinate system.
    cursorSvg.setAttribute('width', '36');
    cursorSvg.setAttribute('height', '36');
    cursorSvg.setAttribute('viewBox', '0 0 36 36');
    cursorSvg.style.position = 'absolute';
    // Offset the SVG so the tip of the pointer is at the (x,y) coordinate.
    cursorSvg.style.transform = 'translate(-4px, -4px)';

    // Create a group for the "sparkle" lines
    const sparkles = document.createElementNS(svgNS, 'g');
    sparkles.setAttribute('fill', 'none');
    sparkles.setAttribute('stroke', 'black');
    sparkles.setAttribute('stroke-width', '2.5');
    sparkles.setAttribute('stroke-linecap', 'round');

    // Define the paths for the three sparkle lines
    const sparklePaths = [
        'M18 2 L22 6',
        'M2 18 L6 22',
        'M8 2 L12 6'
    ];

    sparklePaths.forEach(d => {
        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('d', d);
        sparkles.appendChild(path);
    });

    // Create the main pointer shape
    const pointer = document.createElementNS(svgNS, 'path');
    pointer.setAttribute('d', 'M9 9 L23 23 L17.5 24 L7.5 14 Z');
    pointer.setAttribute('fill', 'black');

    // Add the pointer and sparkles to the SVG, then the SVG to the container
    cursorSvg.appendChild(pointer);
    cursorSvg.appendChild(sparkles);
    container.appendChild(cursorSvg);


    // --- 3. Generate and Style the Animated Lines ---
    // This logic remains the same, creating the radial lines around the new cursor.
    const numberOfLines = 12;
    const maxAnimationTime = (1.2 + 0.4 + 0.1) * 1000;

    for (let i = 0; i < numberOfLines; i++) {
        const angle = (i * 30) + Math.random() * 10 - 5;
        const length = 40 + Math.random() * 30;
        const duration = 1.2 + Math.random() * 0.4;
        const delay = Math.random() * 0.1;

        const wrapper = document.createElement('div');
        wrapper.style.position = 'absolute';
        wrapper.style.transformOrigin = 'top left';
        wrapper.style.transform = `rotate(${angle}deg)`;

        const line = document.createElement('div');
        line.style.width = '2px';
        line.style.backgroundColor = 'black';
        line.style.borderRadius = '9999px';
        line.style.height = `${length}px`;
        line.style.transformOrigin = '50% 0%';
        line.style.animationName = 'radial-splash-animation';
        line.style.animationDuration = `${duration}s`;
        line.style.animationDelay = `${delay}s`;
        line.style.animationFillMode = 'both';

        wrapper.appendChild(line);
        container.appendChild(wrapper);
    }

    // --- 4. Add to Document and Schedule Cleanup ---
    document.body.appendChild(container);

    setTimeout(() => {
        if (container.parentNode) {
            container.parentNode.removeChild(container);
        }
    }, maxAnimationTime + 200);
};

"""

            browser_info(f"Attempting to show pointer at coordinates: ({x}, {y})")
            # Pass coordinates as a dictionary to match the JavaScript parameters
            result = await self.page.evaluate(js_code, {'x': x, 'y': y})
        
            if result:
                browser_info(f"Pointer created successfully at ({x}, {y})")
                return BrowserActionResult.create_success(
                    action_type="show_pointer",
                    message=f"Successfully showed pointer at coordinates ({x},{y})",
                )
            else:
                raise Exception("Failed to create pointer element")
        except Exception as e:
            browser_error(f"Error showing pointer: {e}")
            return BrowserActionResult.create_failure(
                action_type="show_pointer",
                message=f"Error showing pointer: {str(e)}",
            )