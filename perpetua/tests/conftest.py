"""Pytest configuration and fixtures for CLI tests."""
import pytest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

# Import the app for testing
from localrag.app import app

@pytest.fixture
def runner():
    """Typer CLI test runner."""
    return CliRunner()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def initialized_project(temp_dir):
    """Create an initialized localrag project in a temp directory."""
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    try:
        # Create .rag directory structure manually to avoid API calls
        rag_dir = Path(temp_dir) / ".rag"
        rag_dir.mkdir()
        (rag_dir / "staging").mkdir()
        
        # Create threads.txt
        import uuid
        (rag_dir / "threads.txt").write_text(str(uuid.uuid4()))
        
        # Create minimal database
        with patch('localrag.app.DBManager') as mock_db:
            mock_db_instance = MagicMock()
            mock_db.return_value = mock_db_instance
            
            # Create database file
            db_path = rag_dir / "database.db"
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS docs(
                    id TEXT PRIMARY KEY,
                    filepath TEXT,
                    file_hash TEXT, 
                    chunk_count INT,
                    last_indexed TEXT
                )
            """)
            conn.commit()
            conn.close()
        
        yield temp_dir
    finally:
        os.chdir(original_cwd)

@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = os.path.join(temp_dir, "test_file.txt")
    with open(file_path, "w") as f:
        f.write("This is a test file.\nIt has multiple lines.")
    return file_path

@pytest.fixture
def sample_directory(temp_dir):
    """Create a sample directory with files for testing."""
    dir_path = os.path.join(temp_dir, "test_dir")
    os.makedirs(dir_path, exist_ok=True)
    
    # Create some test files
    for i in range(3):
        file_path = os.path.join(dir_path, f"file_{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"Content of file {i}")
    
    return dir_path

@pytest.fixture
def mock_embeddings():
    """Mock embeddings to avoid API calls."""
    mock = MagicMock()
    mock.embed_query.return_value = [0.1] * 768  # Mock embedding vector
    mock.embed_documents.return_value = [[0.1] * 768] * 10
    return mock

@pytest.fixture
def mock_rag_store():
    """Mock RAGStore for testing."""
    mock = MagicMock()
    mock.vector_store = MagicMock()
    mock.vector_store.similarity_search.return_value = [
        MagicMock(page_content="Test content 1", metadata={"source": "test1.txt"}),
        MagicMock(page_content="Test content 2", metadata={"source": "test2.txt"})
    ]
    mock.curr = MagicMock()
    mock.curr.execute.return_value = None
    mock.curr.fetchall.return_value = [
        (1, "test1.txt", "hash1", 5, "2024-01-01"),
        (2, "test2.txt", "hash2", 3, "2024-01-02")
    ]
    mock.close = MagicMock()
    mock.get_current_hashes.return_value = {"file1.txt": "hash1", "file2.txt": "hash2"}
    mock.get_file_hash.return_value = "hash1"
    mock.add_documents = MagicMock()
    mock.add_documents_batch = MagicMock()
    return mock

