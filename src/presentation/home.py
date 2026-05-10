"""Home page presentation."""
import streamlit as st


def render_home():
    """Render the home page."""
    st.title("⚽ Football Scout Pro")
    st.subheader("Professional Player Analytics & Scouting Tool")
    
    st.markdown("---")
    
    # Navigation cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Player Explorer", use_container_width=True):
            st.session_state.current_page = "player_explorer"
            st.rerun()
    
    with col2:
        if st.button("🎯 Advanced Scouting", use_container_width=True):
            st.session_state.current_page = "advanced_scouting"
            st.rerun()
    
    with col3:
        if st.button("💰 Player Valuation", use_container_width=True):
            st.session_state.current_page = "player_valuation"
            st.rerun()
    
    st.markdown("---")
    st.info("Use the sidebar to navigate between pages or click the cards above.")
