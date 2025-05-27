#!/bin/bash

# Set up the working directory
mkdir -p /app/data

cp -r ./* /app/ 2>/dev/null || true

cd /app

# Run the Streamlit app
streamlit run water_quality_app_v4.py
