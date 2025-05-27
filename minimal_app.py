import streamlit as st

st.title('Minimal Water Quality App')
st.write('If you can see this, the basic app is working!')

# Add a simple sidebar
st.sidebar.header('Options')
waterbody = st.sidebar.selectbox('Waterbody', ['Γαδουρά'])

# Add some basic content
st.header('Main Content')
st.write(f'Selected waterbody: {waterbody}')
