# Localrag v. 0.1.0

Friday, November 28, 2025

Localrag is a command line tool that allows you to use an LLM to ask questions about the codebase in which you have initialized the localrag project. 

## Commands

Commands for this CLI have been copied from git, so they should be fairly intuitive for anyone who has operated with git. For exact documentation of the commands, 
please check [this file](docs.md)

### Configuring the package for your personal use.

```bash
localrag config
```

This will allow you to set up your environment for the project. Make sure to run this before running any other command as they will not work.

You will be prompted for some API keys or names of the local models you want to use for this package.

### Initializing the project
```bash
localrag init
```

This initializes the `.rag` directory. This directory is curcial for naking localrag work as all of the files are kept here. Please do not modify the `.rag` directory unless you know what you are doing.

### Adding files to the staging area

```bash
localrag add path\to\file
```

Adds a file/directory to the staging area. This copies the file to the staging directory in the `.rag` directory. It will take a little time.

### Committing

```bash
localrag commit
```

This will vectorize each file you added to the staging area. It will then add the vectorized file to a milvus database in the `.rag` directory. You must execute this command before being able to interact with the LLM.

### Status

```bash
localrag status
```

This will give you a status of what files are currently staged. 

### Removing file from staging area

```bash
localrag rm path\to\file
```

This will remove the file from the staging area.

### Prompting the LLM

```bash
localrag ask
```

This will open up chatting service that will allow you to query the LLM about your project. The LLM does not stream its response back so it will take some time before you see a response.

Currently, only Gemini is supported as the LLM. You will need to create a `.env` file with your Gemini API key in the folder for this package. Future versions will try to support more enterprise models as well as locally run models. 

### Miscellaneous commands

```bash
localrag reset
```

This clears the staging area. With the `--hard` optional argument, it will reinitialize the project.

```bash
localrag ls
```

It lists all files currently being tracked by the project

```bash
localrag diff
```

It shows if there difference between staged files and their tracked versions. Ideally, more information can be provided in the future.

```bash
localrag search "query"
```

Allows the user to query the vector store directly. This should be used as a sanity check or if you want to see some source code.

## Agent Tools

Our agent is equipped with the following tools to answer you questions: 

1. **Vector store retrieval**: this is classic RAG using a Milvus vector store contained within the `.rag` directory. Using this tool, the LLM is able to answer questions directly about your codebase. The agent is designed to privelege this tool over the others.
2. **Web Search**: this tool is used by the LLM to search the web to answer your questions. As of now, it will answer any question by using this but it is intended to get documentation or most up-to-date information about the tools you are using.
3. **Knowledge Graph Search**: this tool allows the agent to create create a graph with the codebases' structure. This should allow it to understand interdependencies between the different files and packages.

Tools in development: 

* database search: a tool that allows the agent to query any database given the URI to the database. This would be helpful for users to ask questions about their databases in the project without having to query it themselves.
* file writing: cursor capability to edit files and make appropriate changes to files. This is probably too ambitious and will take time to be implemented.

## Notes about the package

### Dependencies

```py
# Core dependencies
typer>=0.20.0,<0.21.0
rich>=13.0.0
python-dotenv>=1.0.0

# LangChain ecosystem
langchain>=0.1.0
langchain-core>=0.1.0
langchain-community>=0.0.20
langchain-text-splitters>=0.0.1
langchain-google-genai>=1.0.0
langchain-milvus>=0.1.0
langchain-tavily>=0.2.13,<0.3.0

# LangGraph
langgraph>=1.0.4,<2.0.0
```
You should also have a `.env` file with the following API keys: 

```bash
GOOGLE_API_KEY=

TAVILY_API_KEY=

LOCAL= #True or False if you want to use a local model
LOCAL_MODEL= #the name of your local model you want to use. Make sure it is supported by langchain for tool calling!

# Optional: For evaluation and tracing
LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=localrag
```

The optional ones are recommended if you want to evaluate/debug the agent if you make any modifications.

### Installation

Use the wheel in dist. This is the best way to use this project. Additionally, you can download it via pip.

### Next steps

*In order of importance*

* **Explore Neo4J Graph RAG**: maybe a graph is better suited for this project... Will look into this soon for next versions.
* **Adding more tools to the agent**: ideally, some cursor capabilities would be great to be able to rewrite code.
