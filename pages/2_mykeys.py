import streamlit as st
import json
import os

# Function to load API key from a JSON file
def load_api_key():
    if os.path.exists("api_key.json"):
        with open("api_key.json", "r") as file:
            data = json.load(file)
            return data.get("api_key", "")
    return ""

# Function to save API key to a JSON file
def save_api_key(api_key):
    with open("api_key.json", "w") as file:
        json.dump({"api_key": api_key}, file)

# Function to delete API key from JSON file
def delete_api_key():
    if os.path.exists("api_key.json"):
        os.remove("api_key.json")

# Streamlit App
st.title("API Key Storage")

# Load the stored API key (if exists)
stored_api_key = load_api_key()

# State variable to clear input field after saving
key_input = st.empty()

# Input field for API key (manual entry)
api_key = key_input.text_input("Enter your API key", value="", type="password")

# Save the API key if it has changed
if st.button("Save API Key"):
    if api_key:
        save_api_key(api_key)
        st.success("API key saved successfully!")
        key_input.empty()  # Clear the input field

# Show the stored API key (for demonstration, masked)
if stored_api_key:
    st.write(f"Stored API key (masked): {'*' * len(stored_api_key)}")

# Option to delete the stored API key
if st.button("Delete API Key"):
    delete_api_key()
    st.success("API key deleted successfully!")
    stored_api_key = ""  # Clear the displayed stored key