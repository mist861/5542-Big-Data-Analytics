import streamlit as st

import chromadb
from ragatouille import RAGPretrainedModel
import ollama
from typing import Optional
import os

import argparse

parser = argparse.ArgumentParser(description='Chatbot script')
parser.add_argument('--store', action="store", dest='store', default='./chroma')
parser.add_argument('--model', action="store", dest='model', default='llama3.1')
parser.add_argument('--bot_title', action="store", dest='bot_title', default='GrocerBot')
parser.add_argument('--bot_description', action="store", dest='bot_description', default='An example chatbot created for 5542-0001 Fall 2024 project')
parser.add_argument('--collection', action="store", dest='collection', default='grocery')
args = parser.parse_args()

pathToScriptDir = os.path.dirname(os.path.realpath(__file__))

chroma_client = chromadb.PersistentClient(path=args.store)
collection = chroma_client.get_or_create_collection(name=args.collection)

def rag_query(
    question: str,
    llm: str,
    knowledge_index=collection,
    reranker: Optional[RAGPretrainedModel] = None,
    num_retrieved_docs: int = 5,
    num_docs_final: int = 1):
    print("=> Retrieving documents...")
    relevant_docs = knowledge_index.query(query_texts=question, n_results=num_retrieved_docs)
    relevant_docs = relevant_docs['documents'][0]

    if reranker:
        print("=> Reranking documents...")
        relevant_docs = reranker.rerank(question, relevant_docs, k=num_docs_final)

    relevant_docs = relevant_docs[:num_docs_final]

    final_prompt = f"""
        You are a helpful assistant. Use the provided context to answer the provided question. 
        The attribute names of each item are set in UPPERCASE followed by the attribute value.
        For example, the cost or price of an item follows the term "PRICE_CURRENT".
        
        CONTEXT: {relevant_docs}
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

st.title(args.bot_title) # Set the page title
st.caption(args.bot_description) # Set the page caption

if "messages" not in st.session_state: # If there are no messages in the session state, display a default message
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages: # Display the messages in the session state (right now, just the above)
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(): # If anything is added to the prompt by the user
    st.session_state.messages.append({"role": "user", "content": prompt}) # Add it to the session state
    st.chat_message("user").write(prompt) # Show it in the chat log
    msg = rag_query(prompt, args.model) # Generate a message by calling the above function
    st.session_state.messages.append({"role": "assistant", "content": msg}) # Add the message to the session state
    st.chat_message("assistant").write(msg) # Write the message out in the UI