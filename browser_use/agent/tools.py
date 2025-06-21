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
def navigate_to_url(url: str) -> str:
    print(f"Navigating to URL: {url}")
    browser = get_browser()
    result = browser.navigate(url)
    return result["message"]

@tool("click_element", args_schema=ClickSchema, description="Use this tool to click on an element in the current page.")
def click_element(args_schema: ClickSchema) -> str:
    print(f"Clicking element: {args_schema.label} at {args_schema.location}")
    browser = get_browser()
    result = browser.click(x=args_schema.location.x, y=args_schema.location.y, label=args_schema.label)
    return result["message"]
    
class TypeTextSchema(BaseModel):
    text: str = Field(..., description="Text to type into the input field")
    label: str = Field(..., description="Label of the input field to type into.")


@tool(
    "type_text",
    args_schema=TypeTextSchema,
    description="use this tool to type text in the input field."
)
def type_text(args_schema: TypeTextSchema) -> str:
    print(f"Typing text: '{args_schema.text}' into input field with label: {args_schema.label}")
    browser = get_browser()
    result = browser.type_text(text=args_schema.text, label=args_schema.label)
    return result["message"]



tools = [
    # navigate_to_url,
    click_element,
    type_text,
]