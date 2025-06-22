from langchain_core.tools import tool
from typing import List, Dict, Any
from ..browser.browser import Browser
from ..browser.browser_manager import get_browser
import base64
import json
from pydantic import BaseModel, Field

class UrlSchema(BaseModel):
    url: str = Field(..., description="The website URL to navigate to")

class Coordinates(BaseModel):
    x: int = Field(..., description="X coordinate of the element to click on")
    y: int = Field(..., description="Y coordinate of the element to click on")
    
class ClickSchema(BaseModel):
    label: str = Field(..., description="element to click on")
    location: Coordinates = Field(..., description="The location of the element to click on, in the format 'x,y'")
    
@tool("navigate_to_url", args_schema=UrlSchema, description="Use this tool to navigate to a specific website URL.")
async def navigate_to_url(url: str) -> str:
    browser = await get_browser()
    result = await browser.navigate(url)
    return result["message"]

@tool("click_element", args_schema=ClickSchema, description="Use this tool to click on an element in the current page.")
async def click_element(label: str, location: Coordinates) -> str:
    browser = await get_browser()
    result = await browser.click(x=location.x, y=location.y, label=label)
    return result["message"]
    
class TypeTextSchema(BaseModel):
    text: str = Field(..., description="Text to type into the input field")
    label: str = Field(..., description="Label of the input field to type into.")


@tool(
    "type_text",
    args_schema=TypeTextSchema,
    description="use this tool to type text in the input field."
)
async def type_text(text: str, label: str) -> str:
    browser = await get_browser()
    result = await browser.type_text(text=text, label=label)
    return result["message"]

class PressKeysSchema(BaseModel):
    keys: list[str] = Field(..., description="List of keys to press on the keyboard. For example: ['Enter', 'a', 'b', 'c']")
    
@tool("press_keys", args_schema=PressKeysSchema, description="Use this tool to press keys on the keyboard.")
async def press_keys(keys: list[str]) -> str:
    browser = await get_browser()
    result = await browser.press_keys(keys=keys)
    return result["message"]

tools = [
    # navigate_to_url,
    click_element,
    type_text,
    press_keys,
]