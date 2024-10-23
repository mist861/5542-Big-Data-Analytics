import sys
import os
import subprocess
import argparse

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


parser = argparse.ArgumentParser(description='Chatbot initialize script')
parser.add_argument('--requirements', action="store", dest='requirements', default='rag_requirements.txt')
parser.add_argument('--store', action="store", dest='store', default='./chroma')
parser.add_argument('--collection', action="store", dest='collection', default='grocery')
parser.add_argument('--dataset', action="store", dest='dataset', default='./data_raw/WMT_Grocery_202209.csv')
parser.add_argument('--split_1', action="store", dest='split_1', default='CATEGORY')
parser.add_argument('--split_2', action="store", dest='split_2', default=None)
parser.add_argument('--vector_init', action="store", dest='vector_init', default=True)
args = parser.parse_args()

pathToScriptDir = os.path.dirname(os.path.realpath(__file__))
app = App(os.path.join(pathToScriptDir, "rag_env"))
app.run()
# app.pip_install_requirements(args.requirements)
app.pip_install('streamlit')
app.pip_install('pandas')
app.pip_install('chromadb')
app.pip_install('ragatouille')
app.pip_install('ollama')
app.pip_install('typing')

import pandas
import chromadb
import ollama

ollama.pull('llama3.1')
corpus = pandas.read_csv(args.dataset)

if args.vector_init == True:
    if args.split_2 is not None:
        chunks = {}
        for category in corpus['CATEGORY'].unique():
            chunks[category] = {}
        for row in range(len(corpus)):
            category = corpus[args.split_1][row]
            brand = corpus[args.split_2][row]
            if brand not in chunks[category]:
                chunks[category][brand] = [corpus.loc[row]]
            else:
                chunks[category][brand].append([corpus.loc[row]])
        ids = []
        metadata = []
        docs = []
        i = 0
        for split in chunks:
            for subsplit in chunks[split]:
                temp_docs = []
                ids.append(f"{i+1}")
                i+=1
                metadata.append({'split_1':split, 'split_2':subsplit})
                for doc in range(len(chunks[split][subsplit])):
                    for string in range(len(chunks[split][subsplit][doc])):
                        temp_docs.append(chunks[split][subsplit][0].index[string])
                        temp_docs.append(chunks[split][subsplit][doc][string])
                docs.append(" ".join(str(x) for x in temp_docs))
    else:
        chunks = {}
        for category in corpus[args.split_1].unique():
            chunks[category] = []
        ids = []
        metadata = []
        docs = []
        i = 0
        for split in chunks:
            temp_docs = []
            ids.append(f"{i+1}")
            i+=1
            metadata.append({'split_1':split})
            for string in range(len(chunks[split])):
                temp_docs.append(chunks[split][0].index[string])
                temp_docs.append(chunks[category][split][string])
            docs.append(" ".join(str(x) for x in temp_docs))


    chroma_client = chromadb.PersistentClient(path=args.store)
    collection = chroma_client.get_or_create_collection(name=args.collection)

    batch_size = 10000
    batch_count = (len(docs) - 1) // batch_size + 1

    for batch in range(batch_count):
        db_docs = docs[batch*batch_size:(batch+1)*batch_size]
        db_ids = ids[batch*batch_size:(batch+1)*batch_size]
        db_metadata = metadata[batch*batch_size:(batch+1)*batch_size]
        print(f"Adding batch {batch+1}/{batch_count} to vector store")
        collection.add(documents=db_docs, ids=db_ids, metadatas=db_metadata)