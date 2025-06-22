"""
Module for managing the global browser instance.
This allows sharing a single browser instance across different parts of the application.
"""
from typing import Optional
from .browser import Browser

# Global browser instance
_browser_instance: Optional[Browser] = None

async def initialize_browser(viewport_width=1280, viewport_height=800) -> Browser:
    """
    Initialize the global browser instance if it doesn't exist yet.
    
    Args:
        viewport_width: Width of the browser viewport
        viewport_height: Height of the browser viewport
        
    Returns:
        The browser instance
    """
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = Browser(viewport_width, viewport_height)
        await _browser_instance.initialize()
    return _browser_instance

async def get_browser(viewport_width=1280, viewport_height=800) -> Browser:
    """
    Get the current browser instance or initialize one if it doesn't exist.
    
    Args:
        viewport_width: Width of the browser viewport if a new instance is created
        viewport_height: Height of the browser viewport if a new instance is created
    
    Returns:
        The browser instance
    """
    global _browser_instance
    if _browser_instance is None:
        await initialize_browser(viewport_width, viewport_height)
    return _browser_instance

async def close_browser():
    """
    Close the browser instance if it exists.
    """
    global _browser_instance
    if _browser_instance is not None:
        await _browser_instance.close()
        _browser_instance = None
