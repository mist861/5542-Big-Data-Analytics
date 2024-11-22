import configparser
import chromadb
from ragatouille import RAGPretrainedModel
import ollama
from typing import Optional
import os
import json

config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), '../literagbot.config')
config.read(config_path)

model = config.get('CHAT','MODEL')

chroma_client = chromadb.PersistentClient(path=config.get('CORPUS','STORE'))
collection = chroma_client.get_or_create_collection(name=config.get('CORPUS','COLLECTION'))

llmreranker = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")

def rag_query(
    question: str,
    llm: str,
    knowledge_index=collection,
    reranker: Optional[RAGPretrainedModel] = None,
    num_retrieved_docs: int = 8,
    num_docs_final: int = 4):
    print("=> Retrieving documents...")
    relevant_docs = knowledge_index.query(query_texts=question, n_results=num_retrieved_docs)
    relevant_docs = relevant_docs['documents'][0]

    if reranker:
        print("=> Reranking documents...")
        reranked_docs = reranker.rerank(question, relevant_docs, k=num_docs_final)
        relevant_docs = []
        for doc in reranked_docs:
            relevant_docs.append(doc['content'])

    if len(relevant_docs[0].split()) > 3000:
        num_docs_final = 1
        print(f"Number of documents modified to: {num_docs_final}")
    elif (len(relevant_docs[0].split()) + len(relevant_docs[1].split()) > 3000):
        num_docs_final = 2
        print(f"Number of documents modified to: {num_docs_final}")
    elif (len(relevant_docs[0].split()) + len(relevant_docs[1].split()) + len(relevant_docs[2].split()) > 3000):
        num_docs_final = 3
        print(f"Number of documents modified to: {num_docs_final}")

    relevant_docs = relevant_docs[:num_docs_final]
    relevant_docs.reverse()

    final_prompt = f"""
        CONTEXT: {relevant_docs}
        
        You are a helpful assistant. Use the above CONTEXT to answer the QUESTION below.
        Do not mention the CONTEXT directly. Pretend that you already know all provided CONTEXT.
        Do not make up an answer.
        
        QUESTION: {question}
        """

    response = ollama.chat(model=llm, messages=[
        {
            'role': 'user',
            'content': final_prompt,
        },
    ])
    answer = response['message']['content']

    return answer

prompts = []
answers = []
results = {}

file_path = os.path.join(os.path.dirname(__file__), './test_prompts.json')
with open(file_path, 'r', encoding='utf-8') as save_file:
    file = json.load(save_file) # Load the (currently default) save file
    for test, properties in file.items():
        prompts.append(properties['prompt'])
        answers.append(properties['answer'])

for prompt in range(0, len(prompts)):
    prediction = rag_query(prompts[prompt], model)
    print(f'Prompt: {prompts[prompt]}')
    print(f'Expected response: {answers[prompt]}')
    print(f'LLM response: {prediction}')
    results[prompt] = {'prompt':f'{prompts[prompt]}', 'expected_response':f'{answers[prompt]}', 'llm_response':f'{prediction}'}


results_path = os.path.join(os.path.dirname(__file__), f'../../results/{model}_results.json')
with open(results_path, 'w', encoding='utf-8') as results_file:
    json.dump(results, results_file, ensure_ascii=False, indent=4)


