import warnings
warnings.filterwarnings("ignore", message=".*", category=UserWarning)

import typer

import os
import shutil

from pathlib import Path

from localrag.rag.database.setup_db import DBManager
from localrag.rag.document_processing import RAGStore
from localrag.rag.rag import embeddings, invoke_agent

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.prompt import Prompt

import re

import uuid

console = Console()

app = typer.Typer()

@app.command()
def init():
    """Inits .rag directory
    
    Creates: 
    - sqlite database: .rag/database.db 
    - vector store for project: .rag/milvus.db
    - staging area: .rag/staging
    """
    current_directory = Path(os.getcwd())
    try:
        with console.status("intializing..."):
            os.mkdir(current_directory / ".rag")
            os.mkdir(current_directory / ".rag/staging")
            db = DBManager(current_directory / ".rag/database.db")
            db.create_doc_table()
            rag = RAGStore(
                vs_URI=str(current_directory/".rag/milvus.db"), 
                embeddings=embeddings, 
                sql_URI=str(current_directory / ".rag/database.db")
            )

            with open(".rag/threads.txt", "x") as f:
                f.write(str(uuid.uuid4()))

            repo_structure_doc_path = create_repo_structure_doc(os.getcwd())
            rag.add_documents(repo_structure_doc_path)
        console.print("[green]Created .rag directory. Your local rag project has been initialized!")
    except FileExistsError as e:
       console.print("[red]This is already a localrag project!")
    except Exception as e:
        raise e

        
@app.command()
def add(path: str):
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
    try: 
        assert check_initialization, "This is not a localrag project! Please initialize this repo."
        rag_directory = find_rag_directory(os.getcwd())
        os.remove(rag_directory + "/.rag/staging/" + path.split("/")[-1])   
    except Exception as e: 
        raise e        
    

@app.command()
def commit():
    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            embeddings=embeddings, 
            sql_URI=rag_path + "/.rag/database.db"
        )
        path = rag_path + "/.rag/staging"
        for file in os.listdir(path=path):
            rag.add_documents(path + "/" + file)

        for file in os.listdir(path=path):
            os.remove(path + "/" + file)

    except AssertionError as e:
        raise e

@app.command()
def ask():
    rag_path = find_rag_directory(os.getcwd())
    with open(rag_path + "/.rag/threads.txt", "r") as f:
        thread = f.readline()
    config = {"configurable": {"thread_id": thread}}

    while True:
        initial_message = Prompt.ask("You")

        if initial_message == "q" or initial_message == "Q":
            raise typer.Exit()

        msg = Markdown(invoke_agent(initial_message, rag_path + "/.rag/milvus.db", rag_path + "/.rag/milvus.db", config))
        console.print(Padding(msg, 1))
        

@app.command()
def status():
    if check_initialization():
        rag_path = find_rag_directory(os.getcwd())
        status = ""
        for file in os.listdir(rag_path + "/.rag/staging"):
            status += "[red]\t" + file + "\n"
        console.print("The following files have not been committed: \n")
        console.print(status)
    else:
        console.print("[red] This is not a localrag project. Please initialize.")

def check_initialization() -> bool:
    return bool(find_rag_directory(os.getcwd()))

def find_rag_directory(current_dir: str) -> str:
    while current_dir:
        for element in os.listdir(path=current_dir):
            if element == ".rag":
                return current_dir
        current_dir = "/".join(current_dir.split("/")[:-1])
    return ""

def create_repo_structure_doc(dir) -> str:
    """ Creates a .txt file in the .rag directory that keeps track of the repo structure.
    
    Returns: 
        string representation of absolute path to this file

    Notes: 
        This is not the most optimal way of doing this. We should probably check if the file has changed at all before deleting it, but it should be okay for now.
    
    """

    rag_dir = find_rag_directory(os.getcwd()) + "/.rag"

    structure = " Structure of the repo. Please use this to understand the codebase for this project! \n"

    for root, dir, files in os.walk(dir):
        if not (re.search(r"[/\\]\.git[\\/]*", root) or re.search(r"[/\\]\.rag[\\/]*", root)):
            structure += "Path to root: " + root + " Directories in this directory: " + str(dir) + " Files in this directory: " + str(files) + "\n"

    file_path = rag_dir+"/repo.txt"

    if os.path.exists(file_path):
        os.remove(file_path)

    with open(file_path, "x") as f:
        f.write(structure)

    return file_path
        

if __name__ == "__main__":
    app()