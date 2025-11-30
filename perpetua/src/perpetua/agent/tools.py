from ..utils import load_env, find_rag_directory

from ..repo_graph import RepoGraph

load_env()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from .document_processing import RAGStore

from langchain.tools import tool

from langchain_ollama import ChatOllama

from langchain_tavily import TavilySearch

import os

from pydantic import BaseModel, Field

local = os.getenv('LOCAL') == "True"

if not local:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )

    summarizer = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )

    #embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
else:
    llm = ChatOllama(
        model=os.getenv('LOCAL_MODEL'),
        temperature=0,
    )

    summarizer = llm

    #local based emebdding function 
    
tavily_search = TavilySearch(max_results=3)

class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Search query for retrieval.")

_ragstore_cache = {}

def get_ragstore(vector_db_path: str, relational_db_path: str,):
    if not relational_db_path in _ragstore_cache:
        doc_processor = RAGStore(vector_db_path, relational_db_path)
        _ragstore_cache[relational_db_path] = doc_processor
    return _ragstore_cache[relational_db_path]

@tool(response_format="content_and_artifact")
def retrieve_context(query: str, vector_db_path: str = "", relational_db_path: str = "") -> tuple[str, list]:
    """Retrieve relevant context from the vector store based on a query.
    
    This is the PRIMARY tool you should use to answer questions about the codebase.
    ALWAYS use this tool first when the user asks about code, files, functions, classes, or any project-related questions.
    The vector_db_path and relational_db_path parameters are automatically handled - you can pass empty strings for them.
    
    Args:
        query: The search query to find relevant documents. Use specific keywords related to what the user is asking about.
        vector_db_path: (Automatically handled - pass empty string)
        relational_db_path: (Automatically handled - pass empty string)
        
    Returns:
        A tuple containing (serialized_string, retrieved_documents).
    """
    doc_processor = get_ragstore(vector_db_path, relational_db_path)
    retrieved_docs = doc_processor.vector_store.similarity_search(query, k=10)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata.get("source", "?")}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

@tool(response_format="content")
def search_web(search_terms: str):
    """ Searches the web for additional information """
    # Search query
    structured_llm = summarizer.with_structured_output(SearchQuery)
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

@tool(response_format="content")
def retrieve_repo_graph():
    """Retrieves the repository structure to understand the codebase layout.
    Use this tool when the user asks about:
    - The overall structure of the repository
    - What files/directories exist in the project
    - The organization of the codebase
    - Finding where certain types of files are located
    
    Returns:
        A formatted string representation of the repository structure.
    """
    rag_dir = find_rag_directory(os.getcwd()) + "/.rag/"
    graph_json = rag_dir + "repo-graph-lock.json"
    repo_graph = RepoGraph.load_graph(graph_json).to_tree()
    
    return repo_graph


TOOLS = [retrieve_context, search_web, retrieve_repo_graph]
TOOLS_BY_NAME = {tool.name : tool for tool in TOOLS}

model_with_tools = llm.bind_tools(TOOLS)