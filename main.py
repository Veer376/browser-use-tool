#!/usr/bin/env python
"""
Browser-use-tool main script for testing.

This script provides a simple interface to test the browser agent.
"""
import uuid
import asyncio
import sys
import os
import base64
from typing import Dict, Any
from browser_use.browser.browser import Browser
from browser_use.browser.browser_manager import initialize_browser, get_browser, close_browser
from langgraph.errors import NodeInterrupt


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from browser_use.agent.agent import agent

async def main(task):
    
    browser = await initialize_browser(viewport_width=1280, viewport_height=800)
    
    try: 
        await browser.navigate("https://www.bing.com")
        screenshot = await browser.screenshot_bytes()
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
        
        
        initial_state = {
            "messages": [{"role": "user", "content": task}],
            "current_screenshot": screenshot_base64,
            "goal": task,
            "browser_state": {
                "url": "https://www.bing.com",  # Initial URL
                "viewport_width": browser.viewport_width,
                "viewport_height": browser.viewport_height,
                "page_title": "Bing"  # Initial page title assumption
            },
            "execution_history": []
        }
        config = {
            "recursion_limit": 10,
            "configurable" : {
                "thread_id": str(uuid.uuid4()),
            }
        }
        agent.update_state(config=config, values=initial_state)
                
        for _ in range(10):
            async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": task}]},
                config=config,
                stream_mode="values"):
                
                print(chunk["messages"][-1].pretty_print())

            # Update the state with fresh screenshot after each action
            new_screenshot = await browser.screenshot_bytes()
            new_screenshot_base64 = base64.b64encode(new_screenshot).decode('utf-8')
            
            try:
                agent.update_state(config, {"current_screenshot": new_screenshot_base64})
            except Exception as e:
                print(f"State update error: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await browser.close()

asyncio.run(main(task = "book a movie ticket for me"))