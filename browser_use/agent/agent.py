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
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from .utils import get_model, SYSTEM_MESSAGE
from .tools import tools
from langgraph.checkpoint.memory import InMemorySaver

llm = get_model()

class BrowserState(BaseModel):
    """Current state of the browser"""
    url: str = ""
    viewport_width: int = 1280
    viewport_height: int = 800
    page_title: Optional[str] = None
    
class State(TypedDict):
    """State maintained by the supervisor agent"""
    messages: Annotated[list[dict], add_messages]
    current_screenshot: str
    goal: str
    browser_state: Dict[str, Any]  # Browser metadata
    execution_history: List[str]  # History of actions performed


browser_action_router = ToolNode(
    tools,
    name="browser_action_router"
)

x=0
async def browser_supervisor(state: State):
    """Supervisor agent that manages browser actions based on user goals."""
    print("Starting browser supervisor agent...")
    multimodal_content = [
        {"type": "text", "text": f"Goal: {state['goal']}\n\nCurrent browser state: {state['browser_state']}\n\nExecution history: {state['execution_history']}"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{state['current_screenshot']}"}}
    ]
    
    
    folder = "screenshots"
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    global x
    filename = f"screenshot_{x}.png"
    x += 1
    filepath = os.path.join(folder, filename)
    
    image_data = base64.b64decode(state['current_screenshot'])
    with open(filepath, "wb") as f:
        f.write(image_data)
        
        
    response = await llm.bind_tools(tools).ainvoke([
        SystemMessage(content=SYSTEM_MESSAGE),
        HumanMessage(content=multimodal_content)
    ])
    return {"messages": [response]}

builder = StateGraph(State)
builder.add_node("browser_supervisor", browser_supervisor)
builder.add_node("browser_action_router", browser_action_router)
builder.add_edge(START, "browser_supervisor")
builder.add_conditional_edges(
    "browser_supervisor",
    lambda state: "browser_action_router" if getattr(state["messages"][-1], "tool_calls", None) else END
)
# builder.add_edge("browser_action_router", "browser_supervisor")


checkpointer = InMemorySaver()
agent = builder.compile(checkpointer=checkpointer)


