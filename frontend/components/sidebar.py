
import streamlit as st


def render_sidebar(pages):
    with st.sidebar:

        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-logo">TSO</div>
                <div class="sidebar-brand-text">
                    <div class="sidebar-brand-title">TEST SUITE</div>
                    <div class="sidebar-brand-subtitle">OPTIMIZER</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="sidebar-tagline">INTELLIGENT TEST MANAGEMENT</div>',
            unsafe_allow_html=True,
        )

        st.divider()

        st.markdown(
            '<div class="sidebar-section-label">WORKSPACE</div>',
            unsafe_allow_html=True,
        )

        for page in pages:
            st.page_link(
                page,
                label=page.title,
                icon=page.icon,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        st.markdown(
            """
            <div class="sidebar-section-label">WORKSPACE STATUS</div>
            <div class="sidebar-status-card">
                <div class="sidebar-status-top">
                    <span class="sidebar-status-dot"></span>
                    <span class="sidebar-status-label">LOCAL WORKSPACE</span>
                </div>
                <div class="sidebar-status-title">Test Suite Optimizer</div>
                <div class="sidebar-status-caption">
                    Python · AI Lab Project
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="sidebar-footer">
                TEST SUITE OPTIMIZER<br>
                <span>PROJECT WORKSPACE</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
