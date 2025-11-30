# Test Suite for LocalRAG CLI

This directory contains comprehensive unit tests for the LocalRAG CLI functionality.

## Test Structure

- `conftest.py`: Pytest fixtures and configuration
- `test_cli.py`: Unit tests for all CLI commands

## Running Tests

### Prerequisites

Install pytest and required testing dependencies:

```bash
pip install pytest pytest-mock
```

Or if using poetry:

```bash
poetry add --group dev pytest pytest-mock
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_cli.py
```

### Run Specific Test Class

```bash
pytest tests/test_cli.py::TestInit
```

### Run Specific Test

```bash
pytest tests/test_cli.py::TestInit::test_init_creates_rag_directory
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=localrag --cov-report=html
```

## Test Coverage

The test suite covers:

1. **Init Command** (`TestInit`)
   - Creating .rag directory structure
   - Handling already initialized projects

2. **List Command** (`TestLs`)
   - Listing tracked files
   - Error handling for uninitialized projects

3. **Search Command** (`TestSearch`)
   - Vector database search
   - Error handling

4. **Add Command** (`TestAdd`)
   - Adding files to staging
   - Adding directories to staging
   - Ignoring .git and .rag directories

5. **Remove Command** (`TestRm`)
   - Removing files from staging
   - Error handling

6. **Reset Command** (`TestReset`)
   - Soft reset (clearing staging)
   - Hard reset (reinitialization)

7. **Diff Command** (`TestDiff`)
   - Comparing staged files with tracked versions
   - Empty staging area handling

8. **Commit Command** (`TestCommit`)
   - Committing files to database
   - Verbose mode

9. **Status Command** (`TestStatus`)
   - Showing staging area status
   - Error handling

10. **Helper Functions** (`TestHelperFunctions`)
    - `check_initialization()`
    - `find_rag_directory()`
    - `create_repo_structure_doc()`

## Test Fixtures

The test suite uses several fixtures defined in `conftest.py`:

- `runner`: Typer CLI test runner
- `temp_dir`: Temporary directory for testing
- `initialized_project`: Pre-initialized localrag project
- `sample_file`: Sample test file
- `sample_directory`: Sample test directory with files
- `mock_embeddings`: Mocked embeddings to avoid API calls
- `mock_rag_store`: Mocked RAGStore for testing

## Notes

- Tests use temporary directories to avoid modifying the actual project
- External dependencies (embeddings, LLM calls) are mocked to avoid API calls
- Tests clean up after themselves automatically
- All tests handle working directory changes properly

