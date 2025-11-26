# Design Doc 

## General Architecture

Creates .rag folder within each repo with the following components: 

1. Relational Database

2. Vector store

3. Staging area (sub directory called staging)

4. Repo structure file

## Important commands

`rag init`: initializes a local rag project by reacting the .rag foler int he root of the repository

`rag add path/to/file`: adds a file to the staging area

`rag rm path/to/file`: remove a file from the staging area

`rag commit`: commits currently staged files

`rag prompt`: opens a chat window that allows the user to ask the agent about their codebase

## Ideal workflow

Users should commit more often so that they can have access to the most up-to-date information about their codebase and be able to query it. 

The idea would be to allow developers to ask questions about their codebase and have them answered. It would also be able to provide suggestions using the codebase as context.

## Relational database

I will use SQLite. We will have the following tables: 

*Docs*
|uuid|filepath|file_hash|chunk_count|last_indexed|
|---|---|---|---|---|
|INTEGER (PRIMARY KEY)|TEXT|TEXT|INTEGER|TEXT|
|A unique integer identifier for each file that we are tracking | The path to our file that we are tracing | A hash of our file. This will allow us to see pretty easily if our file has changed. | This will be the number of chunks from processing our docs for our vector store | This will be the datetime for the last time we updated this file.

When files are commited, it should first check in here for the need to actually update the vector store and the relational database. We will use the file hash to determine this.

## Vector Store 

This will be a vector database that will be used to allow the agent to query the codebase for the project. This vector store is using Milvus. I need to do more research about this to determine if there may be a better alternative. Important functionalities: 

- Need to be able to track chunks (files). We will use the *uuid* of each file to track this.
- Need to be able to delete tracker chunks pretty quickly/update the vector store quickly.

## Staging area

This will just be a directory in the `.rag` directory where we will copy files before committing them.

## Agent

We will use Langchain to orchestrate the agent. We will have one tool call to the vector store to query information about the codebase. 
The agent should connect to the vector store in the .rag folder.

## App

We will use typer with rich print to design the CLI functionality.


## Questions

1 - How to make sure that the agent connects to one vector store? 

Resolved: use state to keep track of the paths to the different databases.

2 - How to make sure that files are removed from vector store when a file is deleted? 

