# Legal Traffic Light v3.0 - Streamlit Edition
import streamlit as st
import re
import json
import html
from datetime import datetime
from typing import Dict, List, Tuple
from enum import Enum
import math

class RiskZone(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

st.set_page_config(page_title="Legal Traffic Light v3.0", page_icon="🚦", layout="wide")

st.markdown("# 🚦 Legal Traffic Light v3.0")
st.markdown("### System for analyzing legal documents against corporate regulations")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("### 🔐 Login")
    col1, col2 = st.columns([1, 1])
    with col1:
        name = st.text_input("Full Name")
        position = st.selectbox("Position", ["Specialist", "Senior Specialist", "Head of Department"])
    with col2:
        department = st.text_input("Department")
        demo_mode = st.button("Demo Mode")
    
    if st.button("Login"):
        if name and position and department:
            st.session_state.authenticated = True
            st.session_state.user_name = name
            st.session_state.user_position = position
            st.session_state.user_department = department
            st.session_state.demo_mode = False
            st.rerun()
    
    if demo_mode:
        st.session_state.authenticated = True
        st.session_state.user_name = "Demo User"
        st.session_state.user_position = "Specialist"
        st.session_state.user_department = "Legal Department"
        st.session_state.demo_mode = True
        st.rerun()
else:
    st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
    st.sidebar.markdown(f"{st.session_state.user_position} | {st.session_state.user_department}")
    if st.session_state.demo_mode:
        st.sidebar.info("Demo Mode")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    tab1, tab2, tab3 = st.tabs(["Document Analysis", "Regulations", "Settings"])
    
    with tab1:
        st.markdown("### Document Analysis")
        col1, col2 = st.columns([2, 1])
        with col1:
            contract_text = st.text_area("Enter contract text", height=300, placeholder="Paste contract text here...")
        with col2:
            doc_type = st.selectbox("Document Type", ["Service Agreement", "Supply Contract", "Rent Agreement", "Other"])
            contract_sum = st.number_input("Contract Sum (RUB)", min_value=0, value=1000000)
            if st.button("Analyze"):
                if contract_text:
                    st.success("Demo Analysis Complete")
                    st.markdown("#### Results")
                    col_red, col_yellow, col_green = st.columns(3)
                    with col_red:
                        st.metric("Critical Issues", 2)
                    with col_yellow:
                        st.metric("Warnings", 1)
                    with col_green:
                        st.metric("OK", 3)
    
    with tab2:
        st.markdown("### Regulation Matrix")
        regulations_data = {
            "Amount": ["0-100K", "100K-5M", "5M+"],
            "Zone": ["Green", "Yellow", "Red"],
            "Approver": ["Department Head", "Director", "Board"]
        }
        st.table(regulations_data)
    
    with tab3:
        st.markdown("### Settings")
        st.info("API keys stored securely (session only)")
        openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
