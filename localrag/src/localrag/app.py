import warnings
warnings.filterwarnings("ignore", message=".*", category=UserWarning)

import typer

import os
import shutil

from pathlib import Path

import re

import uuid

from rich.console import Console
console = Console() 

app = typer.Typer()

@app.command()
def init():
    """Initializes localrag project by creating .rag directory"""
    from localrag.rag.database.setup_db import DBManager
    from localrag.rag.document_processing import RAGStore
    from localrag.rag.rag import embeddings

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
def ls():
    """ Lists all files currently tracked by the project """
    from localrag.rag.document_processing import RAGStore
    from localrag.rag.rag import embeddings

    rag_dir = find_rag_directory(os.getcwd()) + "/.rag/"

    rag = RAGStore(
        vs_URI=rag_dir + "milvus.db",
        embeddings= embeddings,
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
    from localrag.rag.document_processing import RAGStore
    from localrag.rag.rag import embeddings

    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            embeddings=embeddings, 
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
    from localrag.rag.document_processing import RAGStore
    from localrag.rag.rag import embeddings
    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            embeddings=embeddings, 
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
    from localrag.rag.document_processing import RAGStore
    from localrag.rag.rag import embeddings

    try:
        assert check_initialization(), "This is not a localrag project! Please initialize this repo."
        rag_path = find_rag_directory(os.getcwd())
        rag = RAGStore(
            vs_URI=rag_path + "/.rag/milvus.db", 
            embeddings=embeddings, 
            sql_URI=rag_path + "/.rag/database.db"
        )
        path = rag_path + "/.rag/staging"
        files_to_process = [path + "/" + file for file in os.listdir(path=path)]
        
        rag.add_documents_batch(files_to_process, verbose)

        for file in os.listdir(path=path):
            os.remove(path + "/" + file)

    except AssertionError as e:
        raise e

@app.command()
def ask():
    """ Prompts the LLM for questions """
    from localrag.rag.rag import invoke_agent
    from rich.markdown import Markdown
    from rich.padding import Padding
    from rich.prompt import Prompt

    rag_path = find_rag_directory(os.getcwd())
    with open(rag_path + "/.rag/threads.txt", "r") as f:
        thread = f.readline()
    config = {"configurable": {"thread_id": thread}}

    while True:
        initial_message = Prompt.ask("You")

        if initial_message == "q" or initial_message == "Q":
            raise typer.Exit()

        msg = Markdown(invoke_agent(initial_message, rag_path + "/.rag/milvus.db", rag_path + "/.rag/database.db", config))
        console.print(Padding(msg, 1))
        

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

def check_initialization() -> bool:
    """ Checks if the project is a part of a localrag project """
    return bool(find_rag_directory(os.getcwd()))

_rag_dirs = {}

def find_rag_directory(current_dir: str) -> str:
    """ Finds the closest .rag directory and returns the path to this directory """
    dir = current_dir
    if current_dir in _rag_dirs:
        return _rag_dirs[current_dir]
    while dir:
        for element in os.listdir(path=dir):
            if element == ".rag":
                return dir
        dir = "/".join(dir.split("/")[:-1])
        _rag_dirs[current_dir] = dir
    return ""

def create_repo_structure_doc(dir) -> str:
    """ Creates a .txt file in the .rag directory that keeps track of the repo structure.
    
    Returns: 
        string representation of absolute path to this file
    """

    rag_dir = find_rag_directory(os.getcwd()) + "/.rag"

    structure = "Structure of the repo. Please use this to understand the codebase for this project! \n"

    for root, dir, files in os.walk(dir):
        if not (re.search(r"[/\\]\.git[\\/]*", root) or re.search(r"[/\\]\.rag[\\/]*", root)):
            structure += "Path to root: " + root + " Directories in this directory: " + str(dir) + " Files in this directory: " + str(files) + "\n"

    file_path = rag_dir+"/repo.txt"

    if os.path.exists(file_path): 
        with open(file_path, "r") as f:
            old_content = "\n".join(f.readlines())

        if old_content == structure:
            os.remove(file_path)

    else:
        with open(file_path, "x") as f:
            f.write(structure)

    return file_path
        

if __name__ == "__main__":
    app()