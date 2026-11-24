
import streamlit as st
from frontend.components.theme import load_css
from frontend.components.sidebar import render_sidebar


st.set_page_config(
    page_title="Test Suite Optimizer",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()
# Register all application pages
overview = st.Page(
    "Home.py",
    title="Overview",
    icon=":material/dashboard:",
    default=True,
)

projects = st.Page(
    "pages/1_Projects.py",
    title="Projects",
    icon=":material/folder_open:",
)

analysis = st.Page(
    "pages/2_Analysis.py",
    title="Analysis",
    icon=":material/analytics:",
)

optimization = st.Page(
    "pages/3_Optimization.py",
    title="Optimization",
    icon=":material/tune:",
)

results = st.Page(
    "pages/4_Results.py",
    title="Results & Comparison",
    icon=":material/monitoring:",
)

ai_experiments = st.Page(
    "pages/5_AI_Experiments.py",
    title="AI Experiments",
    icon=":material/psychology:",
)

pages = [
    overview,
    projects,
    analysis,
    optimization,
    results,
    ai_experiments,
]

# Centralized navigation
current_page = st.navigation(pages, position="hidden")

# Custom sidebar
render_sidebar(pages)

# Display selected page
current_page.run()
