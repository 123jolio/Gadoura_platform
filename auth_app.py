#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Water Quality App (Enterprise-Grade UI)
-----------------------------------------
Φιλικό, επαγγελματικό περιβάλλον ανάλυσης δορυφορικών δεδομένων υδάτων.
"""

import os
import glob
import re
from datetime import datetime, date
import xml.etree.ElementTree as ET
import io

import numpy as np
import pandas as pd
import rasterio
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rasterio.errors import NotGeoreferencedWarning
import warnings
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import streamlit_authenticator as stauth

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Ανάλυση Ποιότητας Επιφανειακών Υδάτων Ταμιευτήρων ΕΥΑΘ ΑΕ", page_icon="💧")

# --- AUTHENTICATION SETUP ---
names = ["Ilioumbas User"]
usernames = ["ilioumbas"]
plain_text_passwords = ["123"]

credentials = {"usernames": {}}
if len(names) == len(usernames) == len(plain_text_passwords):
    for i in range(len(usernames)):
        credentials["usernames"][usernames[i]] = {
            "name": names[i],
            "password": plain_text_passwords[i]
        }
else:
    st.error("Error: Lists must have the same number of items.")
    st.stop()

authenticator = None
try:
    authenticator = stauth.Authenticate(
        credentials,
        "water_quality_app_cookie_v6",
        "a_very_random_secret_key_v6",
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Error during authentication: {e}")
    st.stop()

# --- Global Configuration & Constants ---
DEBUG = False
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
LOGO_PATH = os.path.join(APP_BASE_DIR, "logo.jpg")

WATERBODY_FOLDERS = {
    "Γαδουρά": "Gadoura",
}

def debug_message(*args, **kwargs):
    if DEBUG:
        with st.expander("Debug Messages", expanded=False):
            st.write(*args, **kwargs)

def inject_custom_css():
    custom_css = """
    <style>
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
        .block-container { background: #161b22; color: #e0e0e0; padding: 1.2rem; }
        .stSidebar > div:first-child { background: #23272f; border-right: 1px solid #3a3f47; }
        .card {
            background: #1a1a1d; padding: 2rem 2.5rem; border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25); margin-bottom: 2rem;
            animation: fadein 1.0s ease-in-out;
        }
        @keyframes fadein {
            0% {opacity:0; transform: translateY(10px);}
            100%{opacity:1; transform: translateY(0px);}
        }
        .header-title {
            color: #ffd600; margin-bottom: 1.5rem; font-size: 2.2rem;
            text-align: center; letter-spacing: 0.5px; font-weight: 700;
        }
        .nav-section {
            padding: 1rem 1.2rem; background: #2c2f36; border-radius: 10px;
            margin-bottom: 1.2rem; border-left: 4px solid #ffd600;
        }
        .nav-section h4 { margin: 0; color: #ffd600; font-weight: 500; font-size: 1.1rem; }
        .stButton button {
            background-color: #009688; color: #ffffff; border-radius: 8px;
            padding: 10px 22px; border: none; box-shadow: 0 3px 8px rgba(0,0,0,0.15);
            font-size: 1.05rem; transition: background-color 0.2s, box-shadow 0.2s, transform 0.2s;
            cursor: pointer;
        }
        .stButton button:hover {
            background-color: #00796b; box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }
        .stButton button:active { background-color: #00695c; transform: translateY(0px); }
        .plotly-graph-div { border: 1px solid #2a2e37; border-radius: 10px; }
        .footer {
            text-align:center; color: #7a828e; font-size:0.85rem;
            padding: 2rem 0 0.5rem 0; border-top: 1px solid #2a2e37;
        }
        .footer a { color: #009688; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# --- Main content ---
if st.session_state.get("authentication_status"):
    # Add logout button
    try:
        authenticator.logout("Logout", location="main")
        st.write(f'Welcome *{st.session_state.get("name")}*')
        st.title('Water Quality App')
    except Exception as e:
        st.error(f"Logout error: {e}")
    
# If not logged in, show login form
else:
    try:
        name, authentication_status, username = authenticator.login("Login", location="main")
        st.session_state["name"] = name
        st.session_state["authentication_status"] = authentication_status
        st.session_state["username"] = username
    except Exception as e:
        st.error(f"Authentication error: {e}")
    
    if st.session_state.get("authentication_status") is False:
        st.error('Username/password is incorrect')
    elif st.session_state.get("authentication_status") is None:
        st.warning('Please enter your username and password')

# Create a two-column layout
left_column, right_column = st.columns(2)

# Add content to the left column
with left_column:
    st.header('Upload Data')
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        st.success('File uploaded successfully!')
        # Add your data processing code here

# Add content to the right column
with right_column:
    st.header('Data Analysis')
    st.write("Upload your water quality data to start the analysis.")
    
    # Add analysis options
    analysis_type = st.selectbox(
        'Select analysis type',
        ('Basic Statistics', 'Trend Analysis', 'Quality Assessment')
    )
    
    if st.button('Run Analysis'):
        st.write(f'Running {analysis_type} analysis...')
        # Add your analysis code here

# Add a footer
st.markdown("---")
st.write("Developed by Ilioumbas")
