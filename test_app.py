import streamlit as st
from datetime import datetime

st.title('Test Streamlit App')
st.write('If you can see this, Streamlit is working!')
st.write('Current time:', st.session_state.get('last_refresh', 'Not set yet'))

# Update the time every time the page loads
st.session_state.last_refresh = str(datetime.now())
