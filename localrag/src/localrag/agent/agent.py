from ..utils import load_env

load_env()

from langgraph.graph import MessagesState
from langchain.messages import SystemMessage, ToolCall, ToolMessage, HumanMessage, RemoveMessage, AIMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

from langmem.short_term import SummarizationNode

import sqlite3

from typing import Literal, Union

from .prompts import *
from .tools import *

#--- Nodes ---#

class LocalRagState(MessagesState):
    summary: str
    llm_calls: int
    vector_db_path: str
    relational_db_path: str


def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content=SYSTEM_PROMPT
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }

def tool_node(state: LocalRagState):
    """Performs the tool call"""
    result = []
    
    last_message = state["messages"][-1]

    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {"messages": []}

    
    for tool_call in last_message.tool_calls:
        if tool_call['name'] == "retrieve_context":
            tool_call["args"]["vector_db_path"] = state["vector_db_path"]
            tool_call["args"]["relational_db_path"] = state["relational_db_path"]
        elif tool_call['name'] == "search_db":
            tool_call["args"]["relational_db_path"] = state["relational_db_path"]

        tool = TOOLS_BY_NAME[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        
        if isinstance(observation, tuple):
            content = observation[0]
        else:
            content = observation
        result.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
    return {"messages": result}

summarization_node = SummarizationNode(
    token_counter=count_tokens_approximately,
    model=summarizer,
    max_tokens=384,
    max_summary_tokens=128,
    output_messages_key="messages",
)

def should_continue(state: LocalRagState) -> Union[Literal["tool_node", "summarization_node"], type(END)]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_node"
    
    if len(messages) > 12:
        return "summarization_node"

    return END


app = StateGraph(LocalRagState)

app.add_node("llm_call", llm_call)
app.add_node("tool_node", tool_node)
app.add_node("summarization_node", summarization_node)

app.add_edge(START, "llm_call")
app.add_conditional_edges("llm_call", 
    should_continue,
    ["tool_node", "summarization_node", END]
)
app.add_edge("tool_node", "llm_call")
app.add_edge("summarization_node", "llm_call")

_agent_cache = {}

def choose_agent(relational_db_path: str):
    if relational_db_path not in _agent_cache:
        conn = sqlite3.connect(relational_db_path, check_same_thread=False)
        memory = SqliteSaver(conn)
        _agent_cache[relational_db_path] = app.compile(checkpointer=memory)
    return _agent_cache[relational_db_path]

def invoke_agent(content: str, vector_db_path : str, relational_db_path: str, config: dict) -> str:
    """Invoke the agent
    
    Args:
    content (str): our message to the LLM
    vector_db_path (str): the string representation of the path to the vector store
    relational_db_path: the string representation of the path to the relational database
    
    Returns:
    str: The LLM's text response
     """
    agent = choose_agent(relational_db_path)

    messages = [HumanMessage(content=content)]
    result = agent.invoke(
        {"messages": messages, 
        "vector_db_path": vector_db_path, 
        "relational_db_path": relational_db_path},
        config
    )
    content = result['messages'][-1].content
    if isinstance(content, list):
        if isinstance(content[0], dict):
            return content[0]["text"]
        return content[0]
    return content
