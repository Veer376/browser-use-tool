"""
Module for managing the global browser instance.
This allows sharing a single browser instance across different parts of the application.
"""
from typing import Optional
from .browser import Browser

# Global browser instance
_browser_instance: Optional[Browser] = None

def initialize_browser(viewport_width=1280, viewport_height=800) -> Browser:
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
    return _browser_instance

def get_browser() -> Optional[Browser]:
    """
    Get the current browser instance.
    
    Returns:
        The browser instance or None if not initialized
    """
    return _browser_instance

def close_browser():
    """
    Close the browser instance if it exists.
    """
    global _browser_instance
    if _browser_instance is not None:
        _browser_instance.close()
        _browser_instance = None
