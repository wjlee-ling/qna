import os
import streamlit as st

from dotenv import load_dotenv
from streamlit import session_state as sst

st.set_page_config(layout="wide")

load_dotenv()
USER_CREDENTIALS = {
    "admin": os.getenv("PASSWORD"),
}


# Function to authenticate user
def authenticate(username, password):
    return USER_CREDENTIALS.get(username) == password


st.title("Casper AI 크루")

# Use session state to keep track of login state
if "logged_in" not in st.session_state:
    sst.logged_in = False

if not st.session_state.logged_in:
    st.subheader("Please login")

    # Login form
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if authenticate(username, password):
            sst.logged_in = True
            sst.username = username
            st.success("Login successful!")
        else:
            st.error("Invalid username or password")
else:
    st.subheader(f"Welcome, {sst.username}!")
    st.write("You are logged in.")
    logout_button = st.button("Logout")

    if logout_button:
        sst.logged_in = False
        sst.username = ""
        st.success("You have been logged out.")
