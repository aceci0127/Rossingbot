import streamlit as st
from pipeline import AthenaPipeline

# Set the page configuration
st.set_page_config(page_title="Chat with RossigBot ", page_icon="🐢")

# Title for the Streamlit app
st.title("Rossigbot   🐢")

st.markdown("""
    <style>
        .bottom-left {
            position: fixed;
            bottom: 0;
            right: 0;
            padding: 10px;
            font-size: 16px;
            background-color: rgba(255, 255, 255, 0.7);
        }
    </style>
    <div class="bottom-right">Ti amo</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []

# User input
if prompt := st.chat_input("Ask rossigbot anything..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    # Append user message to conversation
    st.session_state.conversation.append({"role": "user", "content": prompt})

    # Generate response
    pipeline = AthenaPipeline(prompt, st.session_state.conversation, 'DORA')
    response = pipeline.run_pipeline(prompt, st.session_state.conversation, 'DORA')
    st.session_state.conversation.append(prompt)
    st.session_state.conversation.append(response)

    st.session_state.conversation.append({"role": "chatbot", "content": response})

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(response)
    # Append assistant response to conversation
    st.session_state.conversation.append({"role": "assistant", "content": response})