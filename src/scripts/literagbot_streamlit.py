import streamlit as st
import configparser
import chromadb
from ragatouille import RAGPretrainedModel
import ollama
from typing import Optional
import os

config = configparser.ConfigParser()
config.read('./literagbot.config')


chroma_client = chromadb.PersistentClient(path=config.get('CORPUS','STORE'))
collection = chroma_client.get_or_create_collection(name=config.get('CORPUS','COLLECTION'))

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

st.title(config.get('CHAT','TITLE')) # Set the page title
st.caption(config.get('CHAT','DESCRIPTION')) # Set the page caption

if "messages" not in st.session_state: # If there are no messages in the session state, display a default message
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages: # Display the messages in the session state (right now, just the above)
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(): # If anything is added to the prompt by the user
    st.session_state.messages.append({"role": "user", "content": prompt}) # Add it to the session state
    st.chat_message("user").write(prompt) # Show it in the chat log
    msg = rag_query(prompt, config.get('CHAT','MODEL')) # Generate a message by calling the above function
    st.session_state.messages.append({"role": "assistant", "content": msg}) # Add the message to the session state
    st.chat_message("assistant").write(msg) # Write the message out in the UI
