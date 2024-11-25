import streamlit as st
from pipeline import AthenaPipeline

# Set the page configuration
st.set_page_config(page_title="Chat with RossigBot ", page_icon="🐢")

# Title for the Streamlit app
st.title("FrenchBot🇫🇷")

# Initialize session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
    conv = []

# User input
if prompt := st.chat_input("Ask rossigbot anything..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    # Append user message to conversation
    st.session_state.conversation.append({"role": "user", "content": prompt})

    # Generate response
    pipeline = AthenaPipeline(prompt, conv, 'DORA')
    response = pipeline.run_pipeline(prompt, conv, 'DORA', index_name='demo-escp')
    conv.append(prompt)
    conv.append(response)

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(response)
    # Append assistant response to conversation
    st.session_state.conversation.append({"role": "assistant", "content": response})