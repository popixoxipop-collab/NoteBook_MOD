import streamlit as st
from langchain_openai import ChatOpenAI


@st.cache_resource
def get_llm():
    return ChatOpenAI(model='gpt-4.1-mini', temperature=0)
