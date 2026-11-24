
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
CSS_FILE = ROOT / "frontend" / "styles" / "main.css"


@st.cache_data
def read_css_file(file_path, modified_time):
    return Path(file_path).read_text(encoding="utf-8")


def load_css():
    theme = getattr(st.context, "theme", {}) or {}
    is_light = theme.get("base", theme.get("type", "dark")) == "light"

    if is_light:
        variables = """
        :root {
            --bg: #F3F6FC;
            --panel: #FFFFFF;
            --text: #172033;
            --muted: #64748B;
            --border: #E2E8F0;
            --accent: #6D5CE8;
            --cyan: #0891B2;
        }
        """
    else:
        variables = """
        :root {
            --bg: #080B12;
            --panel: #101622;
            --text: #EDF2FA;
            --muted: #9AA8BD;
            --border: #263244;
            --accent: #8B7CFF;
            --cyan: #43D9E8;
        }
        """

    if CSS_FILE.exists():
        css = read_css_file(
            str(CSS_FILE),
            CSS_FILE.stat().st_mtime_ns
        )

        st.markdown(
            f"<style>{variables}{css}</style>",
            unsafe_allow_html=True,
        )
