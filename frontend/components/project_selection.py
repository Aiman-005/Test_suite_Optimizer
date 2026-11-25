import streamlit as st


def sync_project_selection(widget_key):
    st.session_state["selected_project_path"] = (
        st.session_state[widget_key]
    )
