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

# Global debug flag (set to True for debugging output)
DEBUG = False

def debug(*args, **kwargs):
    if DEBUG:
        st.write(*args, **kwargs)

# ---------------------------------------------------
# Εξατομίκευση CSS & Animation για Pro Look
# ---------------------------------------------------
def inject_custom_css():
    custom_css = """
    <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        .block-container {
            background: #161b22;
            color: #e0e0e0;
            padding: 1.2rem;
        }
        .sidebar .sidebar-content {
            background: #23272f;
            border: none;
        }
        .card {
            background: #1a1a1d;
            padding: 2rem 2.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            margin-bottom: 2rem;
            animation: fadein 1.5s;
        }
        @keyframes fadein { 0% {opacity:0;} 100%{opacity:1;} }
        .header-title {
            color: #ffd600;
            margin-bottom: 1rem;
            font-size: 2rem;
            text-align: center;
            letter-spacing: 0.5px;
            font-weight: 700;
        }
        .nav-section {
            padding: 1rem;
            background: #2c2f36;
            border-radius: 10px;
            margin-bottom: 1.2rem;
        }
        .nav-section h4 {
            margin: 0;
            color: #ffd600;
            font-weight: 500;
        }
        .stButton button {
            background-color: #009688;
            color: #fff;
            border-radius: 8px;
            padding: 10px 20px;
            border: none;
            box-shadow: 0 3px 6px rgba(0,0,0,0.12);
            font-size: 1.05rem;
            transition: background-color 0.2s;
        }
        .stButton button:hover {
            background-color: #26a69a;
        }
        .plotly-graph-div {
            border: 1px solid #23272f;
            border-radius: 10px;
        }
        .legend {
            font-size: 0.95rem;
            color: #ffd600;
        }
        .footer {
            text-align:center;
            color:gray;
            font-size:0.9rem;
            padding:1.3rem 0 0.1rem 0;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------------------
# Footer Branding
# ---------------------------------------------------
def render_footer():
    st.markdown("""
        <hr>
        <div class='footer'>
            &copy; 2025 EYATH SA • Powered by OpenAI & Streamlit | Contact: <a href='mailto:ilioumbas@eyath.gr'>ilioumbas@eyath.gr</a>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# Καλωσόρισμα και οδηγίες
# ---------------------------------------------------
def run_intro_page():
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col_logo, col_text = st.columns([1, 3])
        with col_logo:
            base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
            logo_path = os.path.join(base_dir, "logo.jpg")
            if os.path.exists(logo_path):
                st.image(logo_path, width=180, output_format="auto", caption="EYATH Water Quality")
            else:
                st.markdown("💧")
        with col_text:
            st.markdown("""
                <h2 class='header-title'>🚀 Καλωσορίσατε στην Εφαρμογή Ανάλυσης Υδάτων EYATH</h2>
                <p style='font-size:1.15rem;text-align:center'>
                Εξερευνήστε τα δεδομένα ποιότητας με ευκολία.<br>
                Επιλέξτε τι θέλετε να δείτε από το πλάι και απολαύστε δυναμικά, διαδραστικά γραφήματα!
                </p>
                """, unsafe_allow_html=True)
            with st.expander("🔰 Οδηγίες Χρήσης", expanded=False):
                st.write("""
                    - Επιλέξτε υδάτινο σώμα, δείκτη και ανάλυση στην πλαϊνή μπάρα.
                    - Περιηγηθείτε στις καρτέλες με τα διαγράμματα.
                    - Ανεβάστε το δικό σας KML για custom σημεία δειγματοληψίας.
                    - Όλα τα δεδομένα & εικόνες μένουν τοπικά.
                """)
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------
def run_custom_ui():
    st.sidebar.markdown("<div class='nav-section'><h4>🛠️ Επιλογές Ανάλυσης</h4></div>", unsafe_allow_html=True)
    st.sidebar.info("❔ Επιλέξτε τις ρυθμίσεις σας και προχωρήστε στα αποτελέσματα!")
    waterbody = st.sidebar.selectbox("🌊 Υδάτινο σώμα", ["Γαδουρά"], key="waterbody_choice")
    index = st.sidebar.selectbox("🔬 Δείκτης", ["Πραγματικό", "Χλωροφύλλη", "Θολότητα"], key="index_choice")
    analysis = st.sidebar.selectbox(
        "📊 Είδος Ανάλυσης",
        [
            "Επιφανειακή Αποτύπωση",
            "Προφίλ ποιότητας και στάθμης",
            "Eργαλεία Πρόβλεψης και έγκαιρης ενημέρωσης"
        ],
        key="analysis_choice"
    )
    st.sidebar.markdown(
        f"""<div style="padding: 0.7rem; background:#2c2f36; border-radius:8px; margin-top:1.2rem;">
        <strong>🌊 Υδάτινο σώμα:</strong> {waterbody}<br>
        <strong>🔬 Δείκτης:</strong> {index}<br>
        <strong>📊 Ανάλυση:</strong> {analysis}
        </div>""",
        unsafe_allow_html=True
    )

# ---------------------------------------------------
# Main App Logic
# ---------------------------------------------------
if __name__ == "__main__":
    inject_custom_css()
    run_intro_page()
    run_custom_ui()
    render_footer()
