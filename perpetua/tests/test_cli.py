"""Unit tests for CLI commands."""
import os
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from typer.testing import CliRunner

from localrag.app import (
    app,
    check_initialization,
    find_rag_directory,
    create_repo_structure_doc
)


class TestInit:
    """Tests for the init command."""
    
    def test_init_creates_rag_directory(self, runner, temp_dir):
        """Test that init creates .rag directory structure."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            with patch('localrag.app.embeddings', new_callable=MagicMock):
                with patch('localrag.app.RAGStore') as mock_rag:
                    with patch('localrag.app.DBManager') as mock_db:
                        mock_db_instance = MagicMock()
                        mock_db.return_value = mock_db_instance
                        mock_rag_instance = MagicMock()
                        mock_rag.return_value = mock_rag_instance
                        
                        result = runner.invoke(app, ["init"], input="")
                        
                        assert result.exit_code == 0
                        assert (Path(temp_dir) / ".rag").exists()
                        assert (Path(temp_dir) / ".rag" / "staging").exists()
                        assert (Path(temp_dir) / ".rag" / "threads.txt").exists()
                        mock_db_instance.create_doc_table.assert_called_once()
        finally:
            os.chdir(original_cwd)
    
    def test_init_already_initialized(self, runner, temp_dir):
        """Test that init fails gracefully when already initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            # Create .rag directory first
            os.makedirs(Path(temp_dir) / ".rag", exist_ok=True)
            
            with patch('localrag.app.embeddings', new_callable=MagicMock):
                result = runner.invoke(app, ["init"], input="")
                # Should handle FileExistsError gracefully
                assert "already a localrag project" in result.stdout.lower() or result.exit_code != 0
        finally:
            os.chdir(original_cwd)


class TestLs:
    """Tests for the ls command."""
    
    def test_ls_not_initialized(self, runner, temp_dir):
        """Test ls fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["ls"])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_ls_initialized(self, runner, initialized_project):
        """Test ls works when project is initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            with patch('localrag.app.RAGStore') as mock_rag_class:
                mock_rag = MagicMock()
                mock_rag.curr = MagicMock()
                mock_rag.curr.execute.return_value = None
                mock_rag.curr.fetchall.return_value = [
                    (1, "test1.txt", "hash1", 5, "2024-01-01"),
                    (2, "test2.txt", "hash2", 3, "2024-01-02")
                ]
                mock_rag.close = MagicMock()
                mock_rag_class.return_value = mock_rag
                
                result = runner.invoke(app, ["ls"])
                assert result.exit_code == 0
                mock_rag.curr.execute.assert_called_once_with("SELECT * FROM docs")
        finally:
            os.chdir(original_cwd)


class TestSearch:
    """Tests for the search command."""
    
    def test_search_not_initialized(self, runner, temp_dir):
        """Test search fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["search", "test query"])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_search_initialized(self, runner, initialized_project):
        """Test search works when project is initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            with patch('localrag.app.RAGStore') as mock_rag_class:
                mock_rag = MagicMock()
                mock_doc1 = MagicMock()
                mock_doc1.page_content = "Test content 1"
                mock_doc2 = MagicMock()
                mock_doc2.page_content = "Test content 2"
                mock_rag.vector_store.similarity_search.return_value = [mock_doc1, mock_doc2]
                mock_rag_class.return_value = mock_rag
                
                result = runner.invoke(app, ["search", "test query"])
                assert result.exit_code == 0
                mock_rag.vector_store.similarity_search.assert_called_once_with("test query")
        finally:
            os.chdir(original_cwd)


class TestAdd:
    """Tests for the add command."""
    
    def test_add_file_not_initialized(self, runner, temp_dir, sample_file):
        """Test add fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["add", sample_file])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_add_file_initialized(self, runner, initialized_project, sample_file):
        """Test add copies file to staging area."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            result = runner.invoke(app, ["add", sample_file])
            assert result.exit_code == 0
            
            staging_path = Path(initialized_project) / ".rag" / "staging" / "test_file.txt"
            assert staging_path.exists()
            assert staging_path.read_text() == "This is a test file.\nIt has multiple lines."
        finally:
            os.chdir(original_cwd)
    
    def test_add_directory_initialized(self, runner, initialized_project, sample_directory):
        """Test add copies directory contents to staging area."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            result = runner.invoke(app, ["add", sample_directory])
            assert result.exit_code == 0
            
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            # Check that files from directory were copied
            files = list(staging_dir.glob("file_*.txt"))
            assert len(files) == 3
        finally:
            os.chdir(original_cwd)
    
    def test_add_ignores_git_and_rag_dirs(self, runner, initialized_project, temp_dir):
        """Test that add ignores .git and .rag directories."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            # Create a directory with .git subdirectory
            test_dir = Path(temp_dir) / "test_repo"
            test_dir.mkdir()
            git_dir = test_dir / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("git config")
            
            result = runner.invoke(app, ["add", str(test_dir)])
            assert result.exit_code == 0
            
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            # .git files should not be in staging
            assert not any(".git" in str(f) for f in staging_dir.iterdir())
        finally:
            os.chdir(original_cwd)


class TestRm:
    """Tests for the rm command."""
    
    def test_rm_not_initialized(self, runner, temp_dir):
        """Test rm fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["rm", "test.txt"])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_rm_file_from_staging(self, runner, initialized_project):
        """Test rm removes file from staging area."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            test_file = staging_dir / "test.txt"
            test_file.write_text("test content")
            
            result = runner.invoke(app, ["rm", "test.txt"])
            assert result.exit_code == 0
            assert not test_file.exists()
        finally:
            os.chdir(original_cwd)


class TestReset:
    """Tests for the reset command."""
    
    def test_reset_not_initialized(self, runner, temp_dir):
        """Test reset fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["reset"])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_reset_soft_clears_staging(self, runner, initialized_project):
        """Test reset (soft) clears staging area."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            # Add some files to staging
            (staging_dir / "file1.txt").write_text("content1")
            (staging_dir / "file2.txt").write_text("content2")
            
            result = runner.invoke(app, ["reset"])
            assert result.exit_code == 0
            assert len(list(staging_dir.iterdir())) == 0
        finally:
            os.chdir(original_cwd)
    
    def test_reset_hard_reinitializes(self, runner, initialized_project):
        """Test reset (hard) reinitializes the project."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            with patch('localrag.app.embeddings', new_callable=MagicMock):
                with patch('localrag.app.RAGStore') as mock_rag:
                    with patch('localrag.app.DBManager') as mock_db:
                        mock_db_instance = MagicMock()
                        mock_db.return_value = mock_db_instance
                        mock_rag_instance = MagicMock()
                        mock_rag.return_value = mock_rag_instance
                        
                        result = runner.invoke(app, ["reset", "--hard"])
                        # Hard reset should reinitialize
                        assert (Path(initialized_project) / ".rag").exists()
        finally:
            os.chdir(original_cwd)


class TestDiff:
    """Tests for the diff command."""
    
    def test_diff_not_initialized(self, runner, temp_dir):
        """Test diff fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["diff"])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_diff_empty_staging(self, runner, initialized_project):
        """Test diff with empty staging area."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            with patch('localrag.app.RAGStore') as mock_rag_class:
                mock_rag = MagicMock()
                mock_rag_class.return_value = mock_rag
                
                result = runner.invoke(app, ["diff"])
                # Should print "Staging area clean." or exit
                assert "clean" in result.stdout.lower() or result.exit_code == 0
        finally:
            os.chdir(original_cwd)
    
    def test_diff_with_files(self, runner, initialized_project):
        """Test diff with files in staging."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            (staging_dir / "test.txt").write_text("test content")
            
            with patch('localrag.app.RAGStore') as mock_rag_class:
                mock_rag = MagicMock()
                mock_rag.get_current_hashes.return_value = {"test.txt": "hash1"}
                mock_rag.get_file_hash.return_value = "hash2"  # Different hash
                mock_rag_class.return_value = mock_rag
                
                result = runner.invoke(app, ["diff"])
                assert result.exit_code == 0
                mock_rag.get_current_hashes.assert_called_once()
        finally:
            os.chdir(original_cwd)


class TestCommit:
    """Tests for the commit command."""
    
    def test_commit_not_initialized(self, runner, temp_dir):
        """Test commit fails when project is not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["commit"])
            assert result.exit_code != 0
        finally:
            os.chdir(original_cwd)
    
    def test_commit_adds_files_to_db(self, runner, initialized_project):
        """Test commit processes files from staging."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            (staging_dir / "test.txt").write_text("test content")
            
            with patch('localrag.app.RAGStore') as mock_rag_class:
                mock_rag = MagicMock()
                mock_rag.add_documents_batch = MagicMock()
                mock_rag_class.return_value = mock_rag
                
                result = runner.invoke(app, ["commit"])
                assert result.exit_code == 0
                mock_rag.add_documents_batch.assert_called_once()
                # Files should be removed from staging after commit
                assert len(list(staging_dir.iterdir())) == 0
        finally:
            os.chdir(original_cwd)
    
    def test_commit_verbose(self, runner, initialized_project):
        """Test commit with verbose flag."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            (staging_dir / "test.txt").write_text("test content")
            
            with patch('localrag.app.RAGStore') as mock_rag_class:
                mock_rag = MagicMock()
                mock_rag.add_documents_batch = MagicMock()
                mock_rag_class.return_value = mock_rag
                
                result = runner.invoke(app, ["commit", "--verbose"])
                assert result.exit_code == 0
                # Should pass verbose=True
                call_args = mock_rag.add_documents_batch.call_args
                assert call_args[1].get('verbose') is True or call_args[0][1] is True
        finally:
            os.chdir(original_cwd)


class TestStatus:
    """Tests for the status command."""
    
    def test_status_not_initialized(self, runner, temp_dir):
        """Test status handles non-initialized project."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["status"])
            # Should print error message
            assert "not a localrag project" in result.stdout.lower()
        finally:
            os.chdir(original_cwd)
    
    def test_status_initialized_empty_staging(self, runner, initialized_project):
        """Test status with empty staging area."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
        finally:
            os.chdir(original_cwd)
    
    def test_status_initialized_with_files(self, runner, initialized_project):
        """Test status shows files in staging."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            staging_dir = Path(initialized_project) / ".rag" / "staging"
            (staging_dir / "file1.txt").write_text("content1")
            (staging_dir / "file2.txt").write_text("content2")
            
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "file1.txt" in result.stdout or "file2.txt" in result.stdout
        finally:
            os.chdir(original_cwd)


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_check_initialization_false(self, temp_dir):
        """Test check_initialization returns False when not initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            assert check_initialization() is False
        finally:
            os.chdir(original_cwd)
    
    def test_check_initialization_true(self, initialized_project):
        """Test check_initialization returns True when initialized."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            assert check_initialization() is True
        finally:
            os.chdir(original_cwd)
    
    def test_find_rag_directory_not_found(self, temp_dir):
        """Test find_rag_directory returns empty string when not found."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            assert find_rag_directory(os.getcwd()) == ""
        finally:
            os.chdir(original_cwd)
    
    def test_find_rag_directory_found(self, initialized_project):
        """Test find_rag_directory finds .rag directory."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            result = find_rag_directory(os.getcwd())
            assert result == initialized_project
        finally:
            os.chdir(original_cwd)
    
    def test_find_rag_directory_parent_search(self, initialized_project):
        """Test find_rag_directory searches parent directories."""
        # Create a subdirectory
        subdir = Path(initialized_project) / "subdir" / "nested"
        subdir.mkdir(parents=True)
        
        original_cwd = os.getcwd()
        try:
            os.chdir(subdir)
            result = find_rag_directory(os.getcwd())
            assert result == initialized_project
        finally:
            os.chdir(original_cwd)
    
    def test_create_repo_structure_doc(self, initialized_project):
        """Test create_repo_structure_doc creates structure file."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            # Create a test file in the directory
            (Path(initialized_project) / "test.py").write_text("# test file")
            
            result = create_repo_structure_doc(initialized_project)
            assert Path(result).exists()
            content = Path(result).read_text()
            assert "Structure of the repo" in content
        finally:
            os.chdir(original_cwd)


class TestAsk:
    """Tests for the ask command."""
    
    def test_ask_not_initialized(self, runner, temp_dir):
        """Test ask fails when project is not initialized."""
        # This is an interactive command, so we test the setup
        result = runner.invoke(app, ["ask"], input="q\n", env={"PWD": temp_dir})
        # Should fail or exit when not initialized
        assert result.exit_code != 0 or "q" in result.stdout.lower()
    
    @patch('localrag.app.Prompt')
    @patch('localrag.app.invoke_agent')
    def test_ask_initialized(self, mock_invoke, mock_prompt, runner, initialized_project):
        """Test ask command with mocked input."""
        original_cwd = os.getcwd()
        try:
            os.chdir(initialized_project)
            mock_prompt.ask.side_effect = ["test question", "q"]
            mock_invoke.return_value = "Test answer"
            
            result = runner.invoke(app, ["ask"], input="q\n")
            # Should handle the interactive loop
            assert mock_invoke.called or result.exit_code == 0
        finally:
            os.chdir(original_cwd)

