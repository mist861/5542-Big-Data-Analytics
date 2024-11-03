# 5542-0001 Fall 2024 Team Project: LiteRAGBot

This directory contains the Python source code

## Execution:

In the src directory (this directory), run:

```
bash literagbot.sh
```

This will install all dependencies and launch the LiteRAGBot.  Modification to the application can be made in literagbot.config:

```
[INIT]
INIT = True #Flag to track if dependencies need installed or the vector store needs updating

[CORPUS]
DATA_DIR = ./example_data/ #Corpus location
STORE = ./chroma #Vector store location
COLLECTION = literagbot #Collection name
SPLIT_1 = CATEGORY #Required field name to split tables on, if any
SPLIT_2 = None #Optional secondary field name to further split tables on

[CHAT]
MODEL = llama3.1 #The LLM/Model used by the RAG
TITLE = LiteRagBot #The title page shown by the RAG UI
DESCRIPTION = An example chatbot created for 5542-0001 Fall 2024 project #A description of the application, shown in the RAG UI
```

After the initial run, the INIT flag will be set to False. If additional documents are added to the DATA_DIR to be added to the LiteRAGBot, the INIT flag in literagbot.config should be set back to True. This will recreate the vector store with the new documents.


## Requirements:

This can be ran on any Ubuntu-based Linux machine with a GUI capable of running Python.  The following dependencies are required:
