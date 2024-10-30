import sys
import os
import subprocess
import argparse

parser = argparse.ArgumentParser(description='Chatbot initialize script')
parser.add_argument('--requirements', action="store", dest='requirements', default='rag_requirements.txt')
parser.add_argument('--store', action="store", dest='store', default='./chroma')
parser.add_argument('--model', action="store", dest='model', default='llama3.1')
parser.add_argument('--collection', action="store", dest='collection', default='grocery')
parser.add_argument('--dataset', action="store", dest='dataset', default='./example_data/')
parser.add_argument('--split_1', action="store", dest='split_1', default='CATEGORY')
parser.add_argument('--split_2', action="store", dest='split_2', default=None)
parser.add_argument('--store_add', action="store", dest='store_add', default=False)
args = parser.parse_args()

class App:
    def __init__(self, virtual_dir):
        self.virtual_dir = virtual_dir
        self.virtual_python = os.path.join(self.virtual_dir, "bin", "python3")

    def install_virtual_env(self):
        self.pip_install("virtualenv")
        if not os.path.exists(self.virtual_python):
            import subprocess
            subprocess.call([sys.executable, "-m", "virtualenv", self.virtual_dir])
        else:
            print("found virtual python: " + self.virtual_python)

    def is_venv(self):
        return sys.prefix==self.virtual_dir

    def restart_under_venv(self):
        print("Restarting under virtual environment " + self.virtual_dir)
        #exec(open(self.virtual_python).read(), {'__file__': self.virtual_python})
        subprocess.call([self.virtual_python, __file__] + sys.argv[1:])
        exit(0)

    def pip_install(self, package):
        try:
            __import__(package)
        except:
            subprocess.call([sys.executable, "-m", "pip", "install", package, "--upgrade"])

    def pip_install_requirements(self, requirements):
        try:
            with open(f'{requirements}', 'r') as packages:
                for package in packages:
                        package = package.strip()
                        __import__(package)
        except:
            subprocess.call([sys.executable, "-m", "pip", "install", "-r", requirements, "--upgrade"])

    def run(self):
        if not self.is_venv():
            self.install_virtual_env()
            self.restart_under_venv()
        else:
            print("Running under virtual environment")

pathToScriptDir = os.path.dirname(os.path.realpath(__file__))
app = App(os.path.join(pathToScriptDir, "rag_env"))
app.run()

app.pip_install('streamlit')
app.pip_install('pd')
app.pip_install('chromadb')
app.pip_install('ragatouille')
app.pip_install('ollama')
app.pip_install('typing')
app.pip_install('langchain')

import pandas as pd
import chromadb
import ollama
import langchain
from langchain.text_splitter import TokenTextSplitter

class Corpus():
    def __init__(self):
        self.tables = {}
        self.texts = {}
        self.corpus_tables = []
        self.corpus_texts = []
        self.chunker = TokenTextSplitter(chunk_size=1000, chunk_overlap=100)
        self.db_ids = []
        self.db_metadatas = []
        self.db_docs = []
        self.chroma_client = chromadb.PersistentClient(path=args.store)
        self.collection = self.chroma_client.get_or_create_collection(name=args.collection)


    def load_directory(self):
        for file in os.listdir(args.dataset):
            filename = os.fsdecode(file)
            path = os.path.join(args.dataset, filename)
            if filename.endswith(".csv") or filename.endswith(".xlsx"):
                print(f"Found table: {filename}")
                table = pd.read_csv(path)
                self.tables[f'{filename}'] = table
            elif filename.endswith(".txt"):
                print(f"Found text: {filename}")
                text = open(path, "r")
                self.texts[f'{filename}'] = text.read()
        pass

    def chunk_tables(self):
        if args.split_2 is not None:
            for file in self.tables:
                table_chunks = {}
                table = self.tables[f'{file}']
                for category in table[args.split_1]:
                    table_chunks[category] = {}
                for row in range(len(table)):
                    category = table[args.split_1][row]
                    brand = table[args.split_2][row]
                    if brand not in table_chunks[category]:
                        table_chunks[category][brand] = [table.loc[row]]
                    else:
                        table_chunks[category][brand].append([table.loc[row]])
                for category in table_chunks:
                    for brand in table_chunks[category]:
                        temp_docs = []
                        for doc in range(len(table_chunks[category][brand])):
                            for string in range(len(table_chunks[category][brand][doc])):
                                temp_docs.append(table_chunks[category][brand][0].index[string])
                                temp_docs.append(table_chunks[category][brand][doc][string])
                        self.corpus_tables.append(" ".join(str(x) for x in temp_docs))
        else:
            for file in self.tables:
                table_chunks = {}
                table = self.tables[f'{file}']
                for category in table[args.split_1]:
                    table_chunks[category] = {}
                for category in table_chunks:
                    temp_docs = []
                    for doc in range(len(table_chunks[category])):
                        for string in range(len(table_chunks[category][brand][doc])):
                            temp_docs.append(table_chunks[category][0].index[string])
                            temp_docs.append(table_chunks[category][doc][string])
                    self.corpus_tables.append(" ".join(str(x) for x in temp_docs))
        pass

    def chunk_texts(self):
        for file in self.texts:
            split = self.chunker.split_text(self.texts[f'{file}'])
            for chunked_text in split:
                self.corpus_texts.append(chunked_text)
        pass

    def make_corpus(self):
        i = 0
        if len(self.corpus_tables) > 0:
            for doc in self.corpus_tables:
                self.db_ids.append(f"{i+1}")
                i+=1
                self.db_metadatas.append({'filetype':'table','file':'placeholder'})
                self.db_docs.append(doc)
        if len(self.corpus_texts) > 0:
            for doc in self.corpus_texts:
                self.db_ids.append(f"{i+1}")
                i+=1
                self.db_metadatas.append({'filetype':'text','file':'placeholder'})
                self.db_docs.append(doc)
        pass

    def load_vector_store(self):
        batch_size = 10000
        batch_count = (len(self.db_docs) - 1) // batch_size + 1

        for batch in range(batch_count):
            db_docs = self.db_docs[batch*batch_size:(batch+1)*batch_size]
            db_ids = self.db_ids[batch*batch_size:(batch+1)*batch_size]
            db_metadatas = self.db_metadatas[batch*batch_size:(batch+1)*batch_size]
            print(f"Adding batch {batch+1}/{batch_count} to vector store")
            self.collection.add(documents=db_docs, ids=db_ids, metadatas=db_metadatas)
        pass

    def add_document_to_store(self):
        print("placeholder for adding a document")


store = Corpus()

if args.store_add == False:
    store.load_directory()
    store.chunk_tables()
    store.chunk_texts()
    store.make_corpus()
    store.load_vector_store()
    ollama.pull(args.model)
else:
    store.add_document_to_store()