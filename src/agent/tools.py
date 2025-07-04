import base64
from langchain_core.tools import tool
from typing import List, Dict, Any
from google.genai import types
from langgraph.prebuilt import InjectedState
from .utils import correct_coordinates
from ..browser import get_browser
from .schema import *
from langgraph.types import interrupt
import asyncio
from google import genai
import os
from ..utils.logger import tools_info, tools_error, tools_warning

@tool(
    "navigate_to_url", 
    description="Use this tool to navigate to a specific website URL."
)
async def navigate_to_url(url: str, state: Annotated[dict, InjectedState]) -> str:
    browser = await get_browser()
    result = await browser.navigate(url)
    
    if not result.success:
        state['execution_state']['consecutive_failures'] += 1
        state['execution_state']['errors'].append(f"Failed to navigate to {url}. Error: {result.message}")
    else :
        state['execution_state']['history'].append(f"Navigated to {url}")
        state['browser_state']['url'] = url
        # state['browser_state']['dom_structure'] = await browser.get_dom_structure()
    return result.message


@tool(
    "click",
    description="Use this tool to click on an element on the browser page by providing its label. "
)
async def click(label: str, description: str, state: Annotated[dict, InjectedState]) -> str:
    
    browser = await get_browser()
    
    screenshot_base64 = state["browser_state"]["screenshots"][-1]
    
    try:
        # Convert base64 string to bytes for the Gemini API
        screenshot_bytes = base64.b64decode(screenshot_base64)
        
        image_part = genai.types.Part(
            inline_data=genai.types.Blob(
                mime_type="image/jpeg",
                data=screenshot_bytes
            )
        )
    except Exception as e:
        return f"Error processing screenshot: {str(e)}"
        
    response = genai.Client(api_key=os.getenv("GENAI_API_KEY")).models.generate_content(
        model="gemini-2.5-flash",
        contents=[image_part, f"Return single most appropriate bounding box for clickable element with label: '{label}' and description: '{description}'. The box_2d should be [ymin, xmin, ymax, xmax] normalized to 0-1000. Example: {{\"box_2d\": [100, 200, 300, 400], \"label\": \"Submit\"}}"],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    def parse_json(json_output: str):
        # Parsing out the markdown fencing
        lines = json_output.splitlines()
        for i, line in enumerate(lines):
            if line == "```json":
                json_output = "\n".join(lines[i+1:])  # Remove everything before "```json"
                json_output = json_output.split("```")[0]  # Remove everything after the closing "```"
                break  # Exit the loop once "```json" is found
        return json_output
    
    import json
    bounding_box = json.loads(parse_json(response.text))
    
    y1 = int(bounding_box["box_2d"][0])
    x1 = int(bounding_box["box_2d"][1])
    y2 = int(bounding_box["box_2d"][2])
    x2 = int(bounding_box["box_2d"][3])
    
    if y1 == 0 and x1 == 0 and y2 == 0 and x2 == 0:
        return f"Failed because the LLM didn't find the coordinates of the label, Try to give the label with detail description"
    
    x =  (x1 + x2) / 2
    y = (y1 + y2) / 2
    
    viewport = await browser.page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
    width, height = viewport['width'], viewport['height']
    
    x, y = correct_coordinates(x, y, viewport_width=width, viewport_height=height)
    
    await browser.show_pointer(x=x, y=y)
    await browser.page.wait_for_timeout(10000)
    await browser.hide_pointer()

    result = await browser.click_coordinates(x=x, y=y, label=label)
    
    if not result.success:
        state['execution_state']['consecutive_failures'] += 1
        state['execution_state']['errors'].append(f"Failed to click on {label}. Error: {result.message}")
    else:
        state['execution_state']['history'].append(f"Clicked on {label}")
        
    return result.message
     
    
@tool(
    "type",
    description="use this tool to type text in the input field."
)
async def type(text: str, label: str, state: Annotated[dict, InjectedState]) -> str:
    
    browser = await get_browser()
    result = await browser.type(text=text, label=label)
    
    if not result.success:
        state['execution_state']['consecutive_failures'] += 1
        state['execution_state']['errors'].append(f"Failed to type text in {label}. Error: {result.message}")
    else:
        state['execution_state']['history'].append(f"Typed '{text}' in {label}")

    return result.message


@tool(
    "press_keys", 
    # args_schema=PressKeysSchema, 
    description="Use this tool to press keys on the keyboard e.g( 'Enter', 'Backspace' etc."
)
async def press_keys(keys: list[str], state: Annotated[dict, InjectedState]) -> str:
    browser = await get_browser()
    result = await browser.press_keys(keys=keys)
    
    if not result.success:
        state['execution_state']['consecutive_failures'] += 1
        state['execution_state']['errors'].append(f"Failed to press keys {keys}. Error: {result.message}")
    else: 
        state['execution_state']['history'].append(f"Pressed keys {keys}")
    return result.message


@tool(
    "go_back", 
    description="Use this tool to go back to the previous page in the browser history."
)
async def go_back(state: Annotated[dict, InjectedState]) -> str:
    browser = await get_browser()
    result = await browser.go_back()

    if not result.success:
        state['execution_state']['consecutive_failures'] += 1
        state['execution_state']['errors'].append(f"Failed to go back. Error: {result.message}")
    else:
        state['execution_state']['history'].append("Went back to the previous page.")

    return result.message


@tool(
    "human_interaction", 
    args_schema=InteractionSchema, 
    description="Use this tool to interact with the user if encountered any errors or need any help to proceed with the sensitive task. e.g. ('I need to login let me know your credentials', 'i have encountered mulitple errors how i should proceed') etc."
)
async def human_interaction(query: str):
    value = interrupt({"Agent": query})
    return f"USER: {value}"


@tool(
    "wait", 
    description="Use this tool to wait for seconds before proceeding with the next action."
)
async def wait(seconds: float, state: Annotated[dict, InjectedState]):
    try:
        # Ensure seconds is a number and not a string
        seconds_float = float(seconds)

        # Limit maximum wait time to a reasonable value (e.g., 300 seconds)
        max_wait = 300.0
        if seconds_float > max_wait:
            seconds_float = max_wait
        
        state['execution_state']['status'] = "waiting"  
        await asyncio.sleep(seconds_float)
        state['execution_state']['status'] = "running"
        
        # Update state if available
        if state is not None:
            state['execution_state']['history'].append(f"Waited for {seconds_float} seconds")
            
        return f"Waited for {seconds_float} seconds."
    
    except Exception as e:
        # Handle any other exceptions
        error_msg = f"Error while waiting: {str(e)}"
        return error_msg

@tool(
    "exit",
    description="use this tool to exit the agent."
)
async def exit(reason: str, state: Annotated[dict, InjectedState]) -> str:
    state['execution_state']['status'] = "failed"
    return f"Agent exited: {reason}"


tools = [
    navigate_to_url,
    click,
    type,
    press_keys,
    go_back,
    human_interaction,
    wait,
    exit
]