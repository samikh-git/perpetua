#Document processing for text-based files, main interface for documents
from langchain_core.documents import Document

from ..utils import load_env

load_env()

from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_community.document_loaders import TextLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from pathlib import Path
import hashlib
import uuid
from datetime import datetime

from langchain_milvus import Milvus

from rich.console import Console

import sqlite3
import os

console = Console()

CODE_LANGUAGES = {
    ".py": Language.PYTHON, ".js": Language.JS, ".ts": Language.TS, ".jsx": Language.JS, ".tsx": Language.TS, ".java": Language.JAVA, 
    ".c": Language.C, ".cpp": Language.CPP, ".cc": Language.CPP, ".cxx": Language.CPP, ".h": Language.CPP, ".hpp": Language.CPP,
    ".cs": Language.CSHARP, ".go": Language.GO, ".rs": Language.RUST, ".rb": Language.RUBY, ".php": Language.PHP, ".swift": Language.SWIFT, 
    ".kt": Language.KOTLIN, ".scala": Language.SCALA, ".lua": Language.LUA, ".pl": Language.PERL, ".sol": Language.SOL, ".proto": Language.PROTO,
    ".elixir": Language.ELIXIR, ".cob": Language.COBOL,
}

TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".tex", ".html", ".htm"}

class RAGStore:
    """A RAGStore that simplifies adding documents to a vector store.
    Its constructor will create a Milvus Lite vector store and SQLite relational database in desired locations
    if they do not exist.
    
    Args: 
    vs_URI: the desired URI to the vector store. 
    embeddings: needs to be an embedding function for the documents
    sql_URI: the desired URI for the SQL database
    """

    _instances = {}

    def __new__(cls, vs_URI, sql_URI):
        cache_key = (vs_URI, sql_URI)
        if cache_key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cache_key] = instance
            instance._initialized = False
        return cls._instances[cache_key]

    def __init__(self, vs_URI, sql_URI):
        if self._initialized:
            return
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        self.vector_store: Milvus = Milvus(
            embedding_function=embeddings,
            connection_args={"uri": vs_URI},
            index_params= {"index_type": "IVF_FLAT", "metric_type": "L2"},
            primary_field="id",
            text_field="text",
            auto_id=False,
        )
        self.conn = sqlite3.connect(sql_URI)
        self.curr = self.conn.cursor()
        self.conn.commit()
        self._initialized = True

    def close(self):
        """Closes sqlite connection"""
        self.conn.close()

    def add_documents(self, file_path: str, verbose: bool) -> None:
        """ Adds documents to our various databases.

        Args:
            file_path (str): the path to the file that we want to add. Note for now this can only be a file (no directories).
        """
        file_hash: str = self.get_file_hash(file_path);
        if self.validate(file_path, file_hash):

            splits_uuids = self.process_docs(Path(file_path), file_hash, verbose)

            self.curr.execute(""" 
            INSERT INTO docs (id, filepath, file_hash, chunk_count, last_indexed) VALUES (?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), file_path, file_hash, len(splits_uuids[0]), datetime.now().isoformat()))
            self.conn.commit()

            self.curr.execute("SELECT filepath FROM docs WHERE filepath = (?)", (file_path,))
            row = self.curr.fetchall()
            if row[0] == file_path:
                self.remove_doc(file_path)
            
            self.vector_store.add_documents(documents=splits_uuids[0], ids=splits_uuids[1])
        

    def validate(self, file_path: str, file_hash: str) -> bool:
        self.curr.execute("SELECT file_hash FROM docs WHERE filepath = (?)", (file_path,))
        row = self.curr.fetchall()
        if not row:
            return True  
        return row[0] != file_hash  

    def add_documents_batch(self, file_paths: list[str], verbose: bool) -> None:
        """Batch process multiple documents efficiently"""
        documents_to_add = []
        ids_to_add = []

        for file_path in file_paths:
            file_hash = self.get_file_hash(file_path)
            if self.validate(file_path, file_hash):
                splits_uuids = self.process_docs(Path(file_path), file_hash, verbose)
                self.curr.execute("SELECT filepath FROM docs WHERE filepath = (?)", (file_path,))
                existing = self.curr.fetchall()
                if existing:
                    self.remove_doc(file_path)
                    self.curr.execute("""
                        UPDATE docs SET file_hash=?, chunk_count=?, last_indexed=?
                        WHERE filepath=?
                    """, (file_hash, len(splits_uuids[0]), datetime.now().isoformat(), file_path))
                else:
                    self.curr.execute(""" 
                        INSERT INTO docs (id, filepath, file_hash, chunk_count, last_indexed) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (str(uuid.uuid4()), file_path, file_hash, len(splits_uuids[0]), datetime.now().isoformat()))
                
                documents_to_add.extend(splits_uuids[0])
                ids_to_add.extend(splits_uuids[1])

        if documents_to_add:
            self.vector_store.add_documents(documents=documents_to_add, ids=ids_to_add)
            self.conn.commit() 
            self.close()   

    def get_current_hashes(self, paths: list[str]) -> dict:
        assert all([os.path.exists(path) for path in paths]), "Some of these are not real paths"
        placeholder= '?' 
        placeholders= ', '.join(placeholder for unused in paths)
        query= 'SELECT filepath, file_hash FROM docs WHERE filepath IN(%s)' % placeholders
        self.curr.execute(query, paths)
        path_hash_dict = {path : hash for path, hash in self.curr.fetchall()}
        return path_hash_dict



    def get_file_hash(self, file_path) -> str:
        """Hash for change detection"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def process_docs(self, file_path: Path, file_hash: str, verbose: bool = False) -> tuple[list[Document], list[str]]:
        """Process code or text documents, using appropriate parser based on file type."""

        if file_path.suffix in CODE_LANGUAGES:
            lang: Language = CODE_LANGUAGES[file_path.suffix]
            loader = GenericLoader.from_filesystem(
                str(file_path.parent),
                glob=str(file_path.name),
                parser=LanguageParser(language=lang)
            )
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=1500,
                chunk_overlap=200,
                add_start_index=True,
            )
            content_type = "code"
            # Extract language name from enum - use value if available, otherwise use lowercase name
            language_name = lang.value if hasattr(lang, 'value') else lang.name.lower()
        elif file_path.suffix in TEXT_EXTENSIONS:
            loader = TextLoader(str(file_path))
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=200,
                add_start_index=True,
            )
            content_type = "text"
            language_name = "text"
        else:
            raise ValueError(f"Unsupported file extension: {file_path.suffix}")

        all_splits = text_splitter.split_documents(docs)
        if verbose:
            console.print(f"\n[italic]Split {str(file_path)} into {len(all_splits)} sub_documents")
        
        uuids = [str(uuid.uuid4()) for _ in range(len(all_splits))]
        
        for chunk, ids in zip(all_splits, uuids):
            chunk.metadata["uuid"] = ids
            chunk.metadata["source"] = str(file_path)
            chunk.metadata["hash"] = file_hash
            chunk.metadata["indexed_at"] = datetime.now().isoformat()
            chunk.metadata["content_type"] = content_type
            chunk.metadata["language"] = language_name
        
        return all_splits, uuids
        
    def remove_doc(self, file_path):
        res = self.vector_store.delete(
            expr=f"source == '{file_path}'",
        )