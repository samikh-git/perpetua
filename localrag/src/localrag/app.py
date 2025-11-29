import warnings
warnings.filterwarnings("ignore", message=".*", category=UserWarning)

import typer

app = typer.Typer()

import os
import shutil

from pathlib import Path

import re

import uuid

import time

from .utils import *

from datetime import datetime

from rich.console import Console
console = Console() 

@app.command()
def config():
    """Creates a config folder in the home root of user called localrag. This is a required command to use the package."""
    from rich.prompt import Prompt
    from rich.live import Live

    if os.path.exists(HOME_DIR + "/localrag"):
        console.print(f"[yellow]The config directory has already been created. Please check {HOME_DIR + '/localrag'}")
    else:
        with Live(console=console, refresh_per_second=4):  # update 4 times a second to feel fluid
            for msg in MSGS:
                time.sleep(1)
                console.print(msg)
        GEMINI_API_KEY = Prompt.ask("Please input your gemini api key")
        TAVILY_SEARCH_API_KEY = Prompt.ask("Please input your tavily search api key")
        LOCAL = Prompt.ask("Please respond with [green]'True'[/green] or [red]'False'[/red] if you are using a local model")
        LOCAL_MODEL = Prompt.ask("Please input the name of the local ollama LLM you wish to use. Make sure it can support tool calls")
        LOCAL_MODEL_EMB = Prompt.ask("Please input the name of the embedding model you wish to use")
        env_file = make_env_file_content(GEMINI_API_KEY, TAVILY_SEARCH_API_KEY, LOCAL, LOCAL_MODEL, LOCAL_MODEL_EMB)
        os.mkdir(HOME_DIR + "/localrag")
        with open(HOME_DIR + "/localrag/.env", "x") as f:
            f.write(env_file)
        console.print(f"""[green]Created config file in {HOME_DIR + "/localrag"}.""")

@app.command()
def init():
    """Initializes localrag project by creating .rag directory.
    
    This is required to use LocalRAG in a project.
    """
    from .setup_db import DBManager
    from .agent.document_processing import RAGStore

    current_directory = Path(os.getcwd())
    try:
        with console.status("intializing..."):
            os.mkdir(current_directory / ".rag")
            os.mkdir(current_directory / ".rag/staging")
            db = DBManager(current_directory / ".rag/database.db")
            db.create_doc_table()
            rag = RAGStore(
                vs_URI=str(current_directory/".rag/milvus.db"), 
                sql_URI=str(current_directory / ".rag/database.db")
            )

            thread = str(uuid.uuid4())

            with open(".rag/threads.txt", "x") as f:
                f.write(thread)

            with open(HOME_DIR + f"/localrag/{thread}.txt", "x") as f:
                f.write(f"Conversations for thread id {thread} and localrag project {os.getcwd()} \n")

            create_repo_structure_doc()
        console.print("[green]Created .rag directory. Your local rag project has been initialized!")
    except FileExistsError as e:
       console.print("[red]This is already a localrag project!")
    except Exception as e:
        raise e

@app.command()
def ls():
    """ Lists all files currently tracked by the project """
    from .agent.document_processing import RAGStore

    rag_dir = find_rag_directory(os.getcwd()) + "/.rag/"

    rag = RAGStore(
        vs_URI=rag_dir + "milvus.db",
        sql_URI=rag_dir + "database.db",
    )

    rag.curr.execute("SELECT * FROM docs")
    result = rag.curr.fetchall()
    
    from rich.table import Table

    table = Table(show_lines=True)
    table.add_column("id")
    table.add_column("file path")
    table.add_column("file hash")
    table.add_column("chunk_count")
    table.add_column("last indexed")

    for row in result:
        table.add_row(*list[str](map(str, row)))

    rag.close()

    console.print(table)

@app.command()
def search(query: str):
    """Similarity search from the vector database directly
    
    Args:
        query (str): the query we want to search the vector DB directly.
    
    """
    from .agent.document_processing import RAGStore

    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            sql_URI=rag_path + "/.rag/database.db"
        )
        console.print(list(map(lambda x : x.page_content, rag.vector_store.similarity_search(query))))
    except Exception as e:
        raise e


        
@app.command()
def add(path: str):
    """ Adds a file or directory to the staging area 
    
    Args:
        path (str): the path to the file/directory we want to add to the staging area
    
    """
    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_directory = find_rag_directory(os.getcwd())
        if os.path.isdir(path):
            for root, dir, files in os.walk(path):
                if not (re.search(r"[/\\]\.git[\\/]*", root) or re.search(r"[/\\]\.rag[\\/]*", root)):
                    for file in files:
                        shutil.copy2(root + "/" + file, rag_directory + "/.rag/staging/" + file.split("/")[-1])
        else:
            shutil.copy2(path, rag_directory + "/.rag/staging/" + path.split("/")[-1])
    except AssertionError as e:
        raise e   

@app.command()
def rm(path: str):
    """ Removes a file or directory from the staging area 
    
    Args: 
        path (str): the string representation of the path to the file we want to remove from the staging area.
    """
    try: 
        assert check_initialization, "This is not a localrag project! Please initialize this repo."
        rag_directory = find_rag_directory(os.getcwd())
        os.remove(rag_directory + "/.rag/staging/" + path.split("/")[-1])   
    except Exception as e: 
        raise e       

@app.command()
def reset(hard: bool = False):
    """ Resets the project by clearing the staging area. If hard is set to True, the full directory is reinitialized.
    
    Args:
        hard (bool): dictates whether the directory needs to be reinitialized.
    """
    try: 
        assert check_initialization, "This is not a localrag project! Please initialize this repo."
        rag_directory = find_rag_directory(os.getcwd())
        if hard:
            os.remove(rag_directory + "/.rag")
            init()
        else:
            i = 0
            for f in os.listdir(rag_directory + "/.rag/staging"):
                os.remove(rag_directory + "/.rag/staging/" + f)
                i += 1
            console.print(f"[yellow]Deleted {i} files from staging area.")
    except Exception as e:
        raise e


@app.command()
def diff():
    """ Shows the difference between the most recent tracked version of a file and the files in the staging area.
    
    Notes:
        Very rudimentary. Just shows that file hashes are different.
    
    """
    from .agent.document_processing import RAGStore
    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            sql_URI=rag_path + "/.rag/database.db"
        )
        path = rag_path + "/.rag/staging"
        files_to_process = [path + "/" + file for file in os.listdir(path=path)]

        if not files_to_process:
            console.print("Staging area clean.")
            typer.Exit()

        current_hashes = rag.get_current_hashes(files_to_process)
        updated_hashes = [rag.get_file_hash(file) for file in files_to_process]
        for file in files_to_process:
            if current_hashes[file] != updated_hashes:
                console.print(f"[bold] {file}: [/bold] [red]different")
            else:
                console.print(f"[bold] {file}: [/bold] [green]no changes")
    except Exception as e:
        raise e

@app.command()
def commit(verbose: bool = False):
    """ Adds files from staging area to vector database """
    from .agent.document_processing import RAGStore

    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            sql_URI=rag_path + "/.rag/database.db"
        )
        path = rag_path + "/.rag/staging"
        files_to_process = [path + "/" + file for file in os.listdir(path=path)]
        
        rag.add_documents_batch(files_to_process, verbose)

        os.remove(rag_path + "/.rag/repo-graph-lock.json")

        create_repo_structure_doc()

        for file in os.listdir(path=path):
            os.remove(path + "/" + file)

    except AssertionError as e:
        raise e

@app.command()
def ask(save: bool = False):
    """ Prompts the LLM for questions 
    
    Args:
        save (bool) (default -- false): saves the conversation in the config folder. Not super easy to read.
    """
    from .agent.agent import invoke_agent
    from rich.markdown import Markdown
    from rich.prompt import Prompt

    rag_path = find_rag_directory(os.getcwd())
    with open(rag_path + "/.rag/threads.txt", "r") as f:
        thread = f.readline()
    config = {"configurable": {"thread_id": thread}}

    USER_DELIMETER = "------------------------------------------------ USER ----------------------------------------- "

    AGENT_DELIMETER = "------------------------------------------------ AGENT ----------------------------------------- "
    
    now = datetime.now()

    year = str(now.year)
    month = str(now.month)
    day = str(now.day)

    conversation = f"{month} {day}, {year}"

    while True:
        initial_message = Prompt.ask("You")

        if initial_message == "q" or initial_message == "Q":
            break

        msg = invoke_agent(initial_message, rag_path + "/.rag/milvus.db", rag_path + "/.rag/database.db", config)
        conversation += USER_DELIMETER + "\n" + initial_message + AGENT_DELIMETER + "\n" + msg + "\n"

        console.print(Markdown(msg), 1)
    
    if save:
        with open(HOME_DIR + f"/localrag/{thread}.txt", "a") as f:
            f.write(conversation)
        

@app.command()
def status():
    """ Provides a status update of what files are currently in the staging area """
    if check_initialization():
        rag_path = find_rag_directory(os.getcwd())
        status = ""
        for file in os.listdir(rag_path + "/.rag/staging"):
            status += "[red]\t" + file + "\n"
        console.print("The following files have not been committed: \n")
        console.print(status)
    else:
        console.print("[red] This is not a localrag project. Please initialize.")

@app.command()
def help():
    """Provides link to documentation for the project"""
    console.print("[yellow]Please check the following link for documentation.")
    console.print("[yellow]https://github.com/samikh-git/localrag/blob/main/localrag/README.md")


if __name__ == "__main__":
    app()