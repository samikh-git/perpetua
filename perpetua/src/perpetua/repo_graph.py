import networkx as nx
import os

from datetime import datetime

import json

class Node:
    """A class that represents a node in the graph."""
    def __init__(self, name: str, path: str):
        self.name: str = name
        self.path: str = path
        self.is_file: bool = os.path.isfile(path)
        self.is_dir: bool = os.path.isdir(path)

    def to_json(self):
        return {"name": self.name, "path": self.path, "is_file": self.is_file, "is_dir": self.is_dir}

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        return f"Node({self.name}, {self.path})"

    def __str__(self):
        return f"{self.name}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Node):
            return self.path == other.path
        return False

class RepoGraph:
    """A class that represents the graph of a repository."""
    EXCLUDED_DIRS = [".git", ".rag", "__pycache__", ".DS_Store", "dist", "build", "env", "venv", "pytest_cache", ".pytest_cache"]
    def __init__(self, path: str) -> None:
        self.path = path
        self.G = nx.DiGraph()
        self.create_graph(path)

    @staticmethod
    def load_graph(path: str):
        """Loads a graph from a json file."""
        with open(path + "repo_graph-lock.json", "r") as f:
            data = json.load(f)
            G = nx.node_link_graph(data)
            instance = RepoGraph.__new__(RepoGraph)
            instance.G = G
            instance.path = path
            return instance

    def create_graph(self, path: str):
        """Creates the graph for the repository."""
        current_directory = Node(path.split("/")[-1], path)
        self.G.add_node(current_directory)
        for obj in os.listdir(path):
            if os.path.isdir(path + "/" + obj) and obj not in RepoGraph.EXCLUDED_DIRS:
                sub_dir = self.create_graph(path + "/" + obj)
                self.G.add_edge(current_directory, sub_dir)
            elif os.path.isfile(path + "/" + obj):
                name = obj.split("/")[-1]
                self.G.add_node(Node(name, path + "/" + obj))
                self.G.add_edge(current_directory, Node(name, path + "/" + obj))
        return current_directory

    def draw_graph(self):
        """Draws the graph using matplotlib and pydot."""
        import matplotlib.pyplot as plt
        import pydot
        from networkx.drawing.nx_pydot import graphviz_layout

        labels = {node : str(node) for node in self.G.nodes}
        pos = graphviz_layout(self.G, prog="dot")
        nx.draw(self.G, pos, with_labels=False)
        nx.draw_networkx_labels(self.G, pos, labels=labels, font_size = 8, )
        plt.show()

    def save_graph(self, path: str):
        """Saves the graph to a json file title repo-graph-lock.json. 
        
        Returns: path to the JSON lock file
        """
        data = nx.node_link_data(self.G)
        with open(path + "repo-graph-lock.json", "w") as f:
            json.dump(data, f, default=lambda obj: obj.to_json() if isinstance(obj, Node) else obj)
        return path + "repo-graph-lock.json"

    def to_tree(self):
        """Formats repo graph as a tree in string representation"""     
        tree = ""
        for x in nx.generate_network_text(self.G):
            tree += x
        return tree
