# `localrag`

**Usage**:

```console
$ localrag [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `config`: 
* `init`: Initializes localrag project by creating...
* `ls`: Lists all files currently tracked by the...
* `search`: Similarity search from the vector database...
* `add`: Adds a file or directory to the staging area
* `rm`: Removes a file or directory from the...
* `reset`: Resets the project by clearing the staging...
* `diff`: Shows the difference between the most...
* `commit`: Adds files from staging area to vector...
* `ask`: Prompts the LLM for questions
* `status`: Provides a status update of what files are...

## `localrag init`

Initializes localrag project by creating .rag directory

**Usage**:

```console
$ localrag init [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `localrag ls`

Lists all files currently tracked by the project

**Usage**:

```console
$ localrag ls [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `localrag search`

Similarity search from the vector database directly

Args:
    query (str): the query we want to search the vector DB directly.

**Usage**:

```console
$ localrag search [OPTIONS] QUERY
```

**Arguments**:

* `QUERY`: [required]

**Options**:

* `--help`: Show this message and exit.

## `localrag add`

Adds a file or directory to the staging area 

Args:
    path (str): the path to the file/directory we want to add to the staging area

**Usage**:

```console
$ localrag add [OPTIONS] PATH
```

**Arguments**:

* `PATH`: [required]

**Options**:

* `--help`: Show this message and exit.

## `localrag rm`

Removes a file or directory from the staging area 

Args: 
    path (str): the string representation of the path to the file we want to remove from the staging area.

**Usage**:

```console
$ localrag rm [OPTIONS] PATH
```

**Arguments**:

* `PATH`: [required]

**Options**:

* `--help`: Show this message and exit.

## `localrag reset`

Resets the project by clearing the staging area. If hard is set to True, the full directory is reinitialized.

Args:
    hard (bool): dictates whether the directory needs to be reinitialized.

**Usage**:

```console
$ localrag reset [OPTIONS]
```

**Options**:

* `--hard / --no-hard`: [default: no-hard]
* `--help`: Show this message and exit.

## `localrag diff`

Shows the difference between the most recent tracked version of a file and the files in the staging area.

Notes:
    Very rudimentary. Just shows that file hashes are different.

**Usage**:

```console
$ localrag diff [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `localrag commit`

Adds files from staging area to vector database

**Usage**:

```console
$ localrag commit [OPTIONS]
```

**Options**:

* `--verbose / --no-verbose`: [default: no-verbose]
* `--help`: Show this message and exit.

## `localrag ask`

Prompts the LLM for questions

**Usage**:

```console
$ localrag ask [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `localrag status`

Provides a status update of what files are currently in the staging area

**Usage**:

```console
$ localrag status [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
