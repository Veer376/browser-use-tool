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
from src.browser import initialize_browser
from langgraph.errors import NodeInterrupt
from src.agent.agent import build_agent
from langgraph.types import Command
from src.utils.logger import browser_info, browser_error, agent_info

async def main(task, use_debug_chrome):
    
    browser = await initialize_browser(use_debug_chrome=use_debug_chrome)
    
    try: 
        await browser.navigate("https://www.bing.com")
        result = await browser.screenshot_bytes()
        
        if not result.success:
            raise Exception(f"Failed to take screenshot: {result.message}")
        
        screenshot = result.data
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
        
        initial_state = {
            "user_id": "user_123",
            "session_id": str(uuid.uuid4()),
            "messages": [{"role": "user", "content": task}],
            "execution_state": {
                "task": task,
                "history": [],
                "errors": [],
                "consecutive_failures": 0,
                "status": "pending",
            },
            "browser_state": {
                "page_title": "Bing",
                "url": "https://www.bing.com",
                "dom_structure": "",
                "viewport_width": browser.viewport_width,
                "viewport_height": browser.viewport_height,
                "screenshots": [screenshot_base64]
            }
        }
        
        config = {
            "recursion_limit": 100,
            "configurable" : {
                "thread_id": str(uuid.uuid4()),
            }
        }
        
        agent = build_agent()
        async for chunk in agent.astream(initial_state, config=config, stream_mode="values"):
               
            interrupted1 = None
            if "__interrupt__" in chunk:
                agent_info("INTERRUPTED!")
                agent_info(f"Agent: {chunk['__interrupt__']}")
                interrupted1 = chunk
                break
            
            else : print(chunk["messages"][-1].pretty_print())

        if interrupted1:

            interrupted2 = None
            async for chunk in agent.astream(Command(resume=input("USER: ")), config=config, stream_mode="values"):
                    
                if "__interrupt__" in chunk:
                    agent_info("INTERRUPTED AGAIN!")
                    agent_info(f"Agent: {chunk['__interrupt__']}")
                    break
                else : print(chunk["messages"][-1].pretty_print())

            interrupted2 = chunk

            if interrupted2:
                user_input = input("USER: ")
                async for chunk in agent.astream(Command(resume=user_input), config=config, stream_mode="values"):
                    if "__interrupt__" in chunk:
                        agent_info("INTERRUPTED AGAIN!")
                        agent_info(f"Agent: {chunk['__interrupt__']}")
                        break
                    else : print(chunk["messages"][-1].pretty_print())

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await browser.close()



USE_DEBUG_CHROME = True
TASK = """
go to the whatsapp web and send message to abhishek with your introduction as the browser automation agent developed by Aryaveer.
"""
asyncio.run(main(task=TASK, use_debug_chrome=USE_DEBUG_CHROME))