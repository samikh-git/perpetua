import os

from pathlib import Path

from dotenv import load_dotenv

from .repo_graph import RepoGraph

HOME_DIR = str(Path.home())

def load_env():
    """ Loads environment from config directory """
    if os.path.exists(HOME_DIR + "/perpetua/.env"):
        load_dotenv(HOME_DIR + "/perpetua/.env")
    else:
        raise FileNotFoundError("Project has not been configured. Please set run `perpetua config`")

def make_env_file_content(gemini_key: str, tavily_key: str, local: str, local_model: str, local_model_emb: str):
    """ Makes the content for the .env file for config """
    return f"GOOGLE_API_KEY={repr(gemini_key)}\nTAVILY_API_KEY={repr(tavily_key)}\nLOCAL={repr(local)}\nLOCAL_MODEL={repr(local_model)}\nLOCAL_EMBD_MODEL={repr(local_model_emb)}" 

def check_initialization() -> bool:
    """ Checks if the project is a part of a perpetua project """
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

def create_repo_structure_doc() -> str:
    """ Creates a JSON in the .rag directory that keeps track of the repo structure.
    
    Returns: 
        string representation of absolute path to this file
    """

    rag_dir = find_rag_directory(os.getcwd())

    graph = RepoGraph(rag_dir)

    return graph.save_graph(rag_dir + "/.rag/")


MSGS = ([r"""
    ____  ______ ____  ____  ______ ______ __  __    ___ 
   / __ \/ ____// __ \/ __ \/ ____//_  __// / / /   /   |
  / /_/ / __/  / /_/ / /_/ / __/    / /  / / / /   / /| |
 / ____/ /___ / _, _/ ____/ /___   / /  / /_/ /   / ___ |
/_/   /_____//_/ |_/_/   /_____/  /_/   \____/   /_/  |_|                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               

[italic]v.0.1.0 [/italic]
----------------------------------------------------------------
[italic]Built by Sami Khayatei Houssaini, November 2025[/italic]
""", """
Please answer the following questions to get this app configured.

If you do not wish to answer them at this time, please press `enter`
and skip. You should still set up your `.env` file in the localrag 
directory in your homepath.

Hope you enjoy!
----------------------------------------------------------------
"""
])


