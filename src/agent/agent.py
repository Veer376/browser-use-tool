from typing import Annotated, List, Dict, Any, Literal, Optional, Union
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_core.messages.human import HumanMessage
from typing_extensions import TypedDict
from langgraph.types import interrupt, Command, Send
from langgraph.checkpoint.memory import InMemorySaver
import uuid
import os
import base64
import asyncio
import inspect
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from .utils import get_model, SYSTEM_MESSAGE
from .tools import tools
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import NodeInterrupt
from .schema import *
from ..browser import get_browser
from ..utils.logger import agent_info

llm = get_model()


browser_action_router = ToolNode(
    tools,
    name="browser_action_router"
)


x=0
async def browser_supervisor(state: AgentState):
    """Supervisor agent that manages browser actions based on user goals."""
    
    if state['execution_state']['status'] == "failed":
        agent_info(f"Completed Or Failed : {state['messages']}")
        return Command(goto=END)
    
    content = [
        {
            "type": "text", 
            "text": f"Goal: {state['execution_state']['task']}"
        },
        {
            "type": "image_url", 
            "image_url": {"url": f"data:image/png;base64,{state['browser_state']['screenshots'][-1]}"}
        },
        {
            "type": "text",
            "text": f"Last tool call status: {state['messages'][-1]}"
        },
        {
            "type": "text",
            "text": f"Execution History: {state['execution_state']['history'][-5:] if state['execution_state']['history'] else 'No actions taken yet.'}"
        },
        {
            "type": "text",
            "text": f"Analyze the screenshot and decide the next best action to take based on the user's goal. Also analyze the last tool call status."
        }
    ]
        
    response = await llm.bind_tools(tools).ainvoke([
        SystemMessage(content=SYSTEM_MESSAGE),
        HumanMessage(content=content)
    ])
    
    return {"messages": [response]}

# Additional state updater node
async def state_updater(state: AgentState):
    
    folder = "screenshots"
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    global x
    filename = f"screenshot_{x}.png"
    x += 1
    filepath = os.path.join(folder, filename)

    browser = await get_browser()
    result = await browser.screenshot_bytes()   
    
    if not result.success:
        agent_info(f"Failed to take screenshot: {result.message}")
        raise NodeInterrupt("Failed to take screenshot")
    
    screenshot = result.data
    
    with open(filepath, "wb") as f:
        f.write(screenshot)
        
    screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
    
    return {'browser_state': {'screenshots': [screenshot_base64]}}
    
    
    
    
def build_agent():
    builder = StateGraph(AgentState)
    builder.add_node("browser_supervisor", browser_supervisor)
    builder.add_node("browser_action_router", browser_action_router)
    builder.add_node("state_updater", state_updater)

    builder.add_edge(START, "browser_supervisor")
    builder.add_conditional_edges(
        "browser_supervisor",
        lambda state: "browser_action_router" if getattr(state["messages"][-1], "tool_calls", None) else END
    )
    builder.add_edge("browser_action_router", "state_updater")
    builder.add_edge("state_updater", "browser_supervisor")
    
    checkpointer = InMemorySaver()
    agent = builder.compile(checkpointer=checkpointer)

    return agent