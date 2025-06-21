#!/usr/bin/env python
"""
Browser-use-tool main script for testing.

This script provides a simple interface to test the browser agent.
"""

import sys
import os
import base64
from typing import Dict, Any
from browser_use.browser.browser import Browser
from browser_use.browser.browser_manager import initialize_browser, get_browser, close_browser
# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the agent
from browser_use.agent.agent import agent

def is_end_state(state):
    """
    Check if the state represents the end of agent execution.
    This is a simplification - in practice, we check if there are no more tool calls.
    """
    if not state.get("messages"):
        return False
    
    last_message = state["messages"][-1]
    # If the last message is from the assistant and has no tool calls, we're at the end
    if last_message.get("role") == "assistant" and not last_message.get("tool_calls"):
        return True
    return False

def main():
    """Run a simple test of the browser automation agent."""
    print("Initializing browser automation test...")    # Initialize the global browser instance
    browser = initialize_browser()
    result = browser.navigate("https://www.bing.com")
    if not result['success']:
        print(f"Error navigating to Bing: {result['message']}")
        # Clean up and exit if navigation fails
        close_browser()
        sys.exit(1)
    screenshot = browser.screenshot_bytes()
    screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

    # Define a simple task
    task = "book a flight from new york to san francisco on 2024-12-25"

    # Initialize the state
    initial_state = {
        "messages": [
            {"role": "user", "content": task}
        ],
        "current_screenshot": screenshot_base64,
        "goal": task,
        "browser_state": {
            "url": browser.page.url,
            "viewport_width": browser.viewport_width,
            "viewport_height": browser.viewport_height,
            "page_title": browser.page.title() if browser.page else ""
        },
        "execution_history": []
    }
    
    print("\nStarting agent execution...")
    print("=" * 50)
    
    try:
        print("\nRunning agent...")
        
        # Instead of streaming, we'll run the agent one step at a time
        state = initial_state.copy()
        max_steps = 10  # Set a maximum number of steps to prevent infinite loops
        step_num = 0
        
        while step_num < max_steps:
            step_num += 1
            print(f"\nStep {step_num}")
            print("-" * 50)
            
            new_state = agent.invoke(state)
            state = new_state 
            
            if state.get("messages") and len(state["messages"]) > 0:
                last_message = state["messages"][-1]
                role = last_message.get("role", "unknown")
                content = last_message.get("content", "")
                
                print(f"Role: {role}")
                if role == "assistant":
                    # Only print first 200 chars if it's too long
                    if len(content) > 200:
                        print(f"Content: {content[:200]}...")
                    else:
                        print(f"Content: {content}")
                
                # Print tool calls if any
                tool_calls = last_message.get("tool_calls", [])
                if tool_calls:
                    print("\nTool calls:")
                    for tool_call in tool_calls:
                        print(f"  - Tool: {tool_call.get('name', 'unknown')}")
                        print(f"  - Args: {tool_call.get('args', {})}")
                        
                    # Track in execution history
                    for tool_call in tool_calls:
                        tool_name = tool_call.get("name", "unknown_tool")
                        args = tool_call.get("args", {})
                        state.setdefault("execution_history", []).append(f"Called {tool_name}: {args}")
            
            # After each step, take a new screenshot to update the state
            try:
                screenshot = browser.screenshot_bytes()
                state["current_screenshot"] = base64.b64encode(screenshot).decode('utf-8')
                
                # Update browser state
                state["browser_state"] = {
                    "url": browser.page.url,
                    "viewport_width": browser.viewport_width,
                    "viewport_height": browser.viewport_height,
                    "page_title": browser.page.title()
                }
                print(f"Updated browser state: URL={browser.page.url}, Title={browser.page.title()}")
            except Exception as e:
                print(f"Error updating screenshot: {e}")
                import traceback
                traceback.print_exc()
            
            # Check if we need to continue or if we've reached the END node
            if is_end_state(state):
                print("Reached end state. Execution complete.")
                break
                
    except Exception as e:
        print(f"Error in agent execution: {e}")
        import traceback
        traceback.print_exc()
    
    # Print completion message
    print("\n" + "=" * 50)
    print("Agent execution complete!")
    
    # Print execution summary
    if state.get("execution_history"):
        print("\nActions performed:")
        for i, action in enumerate(state["execution_history"], 1):
            print(f"  {i}. {action}")
      # Clean up
    try:
        close_browser()
        print("\nBrowser closed successfully.")
    except Exception as e:
        print(f"\nError closing browser: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")        # Try to close browser on interrupt
        try:
            from browser_use.browser.browser_manager import close_browser
            close_browser()
            print("Browser closed.")
        except:
            pass
    except Exception as e:
        print(f"\nError: {str(e)}")
