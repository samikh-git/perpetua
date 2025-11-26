# Localrag v. 0

*Tuesday, Novemebr 25, 2025*

Localrag is a command line tool that allows you to use an LLM to ask questions about the codebase in which you have initialized the localrag project. 

## Commands

Commands for this CLI have been copied from git, so they should be fairly intuitive for anyone who has operated with git.

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
LANGSMITH_TRACING=
LANGSMITH_API_KEY=

GOOGLE_API_KEY=

TAVILY_API_KEY=

# Optional: For evaluation and tracing
LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=localrag
```

The optional ones are recommended if you want to evaluate/debug the agent if you make any modifications.

### Installation

### Next steps

*In order of importance*

* **Optimizations**: currently, every process is very slow. I would like to be faster and more user friendly. Ideal operation speed would be git like for the initializing and adding files.
* **Local LLMs**: I want to see if it is possible to use a locally running LLM. This would avoid having to a third-party API for the LLM calls which could become expensive very quickly. Maybe Ollama or Vllm could be good for this.
* **Third-party APIs**: this is more of a miscelanneous category. I would like to explore better alternatives (if they exist!) for Tavily and Milvus. I will look into FAISS, Chroma for the vector stores.
* **Adding more tools to the agent**: ideally, some cursor capabilities would be great to be able to rewrite code.

