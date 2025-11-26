from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from .document_processing import RAGStore
from langgraph.graph import MessagesState
from langchain.tools import tool
from langchain.messages import SystemMessage, ToolMessage, HumanMessage, RemoveMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_tavily import TavilySearch

import sqlite3

from typing import Literal
from pydantic import BaseModel, Field

gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2
)

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

tavily_search = TavilySearch(max_results=3)

class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Search query for retrieval.")

#---------# TOOLS #-------------#
@tool(response_format="content_and_artifact")
def retrieve_context(query: str, vector_db_path: str, relational_db_path: str) -> tuple[str, list]:
    """Retrieve relevant context from the vector store based on a query.
    
    Args:
        query: The search query to find relevant documents.
        
    Returns:
        A tuple containing (serialized_string, retrieved_documents).
    """
    doc_processor = RAGStore(vector_db_path, embeddings, relational_db_path)
    retrieved_docs = doc_processor.vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

@tool(response_format="content")
def search_web(search_terms: str):
    """ Searches the web for additional information """
    # Search query
    structured_llm = gemini.with_structured_output(SearchQuery)
    search_query = structured_llm.invoke([search_terms])
    
    # Search
    data = tavily_search.invoke({"query": search_query.search_query})
    search_docs = data.get("results", data)
    

     # Format
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ]
    )
    return formatted_search_docs

TOOLS = [retrieve_context, search_web]
TOOLS_BY_NAME = {tool.name : tool for tool in TOOLS}

model_with_tools = gemini.bind_tools(TOOLS)

#--- Nodes ---#

class LocalRagState(MessagesState):
    summary: str
    llm_calls: int
    vector_db_path: str
    relational_db_path: str

SYSTEM_PROMPT = (
    "You have access to a tool that retrieves context from a codebase."
    "Don't worry about the paths to vector and realtional databases as these will be passed in the state directly. No need to ask the user for them. Just retrieve."
    "Use the tool to help answer user queries about the project they are working on."
    "You have acess to the web. Please use this if the provided context is not sufficient (ie to look up documentation)"
)


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
    
    for tool_call in state["messages"][-1].tool_calls:
        if tool_call['name'] == "retrieve_context":
            tool_call["args"]["vector_db_path"] = state["vector_db_path"]
            tool_call["args"]["relational_db_path"] = state["relational_db_path"]
        tool = TOOLS_BY_NAME[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        
        if isinstance(observation, tuple):
            content = observation[0]
        else:
            content = observation
        result.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
    return {"messages": result}

def summarize_conversation(state: LocalRagState):
    """ Summarizes our conversation to save space """
    summary = state.get("summary", "")

    if summary:
        
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
        
    else:
        summary_message = "Create a summary of the conversation above:"

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = gemini.invoke(messages)
    
    # Delete all but the 2 most recent messages
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}


def should_continue(state: LocalRagState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tool_node"
    
    if len(messages) > 6:
        return "summarize_conversation"

    return END


app = StateGraph(LocalRagState)

app.add_node("llm_call", llm_call)
app.add_node("tool_node", tool_node)
app.add_node("summarize_conversation", summarize_conversation)

app.add_edge(START, "llm_call")
app.add_conditional_edges("llm_call", 
    should_continue,
    ["tool_node", "summarize_conversation", END]
)

app.add_edge("tool_node", "llm_call")

def invoke_agent(content: str, vector_db_path : str, relational_db_path: str, config: dict) -> str:
    """Invoke the agent
    
    Args:
    content (str): our message to the LLM
    vector_db_path (str): the string representation of the path to the vector store
    relational_db_path: the string representation of the path to the relational database
    
    Returns:
    str: The LLM's text response
     """
    conn = sqlite3.connect(relational_db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    agent = app.compile(checkpointer=memory)

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
