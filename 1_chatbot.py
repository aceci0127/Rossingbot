import streamlit as st
from pipeline import AthenaPipeline

# Set the page configuration
st.set_page_config(page_title="Chat with RossigBot ", page_icon="🐢")

# Title for the Streamlit app
st.title("🐢        Rossigbot       🐢")

# Initialize session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []

# User input
if prompt := st.chat_input("Ask rossigbot anything..."):
    # Display user message
    with st.chat_message("🥔", ):
        st.markdown(prompt)
    # Append user message to conversation
    st.session_state.conversation.append({"role": "🥔", "content": prompt})

    # Generate response
    pipeline = AthenaPipeline(prompt, st.session_state.conversation, 'DORA')
    response = pipeline.run_pipeline(prompt, st.session_state.conversation, 'DORA')
    st.session_state.conversation.append(prompt)
    st.session_state.conversation.append(response)

    st.session_state.conversation.append({"role": "assistant", "content": response})

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(response)
    # Append assistant response to conversation
    st.session_state.conversation.append({"role": "assistant", "content": response})