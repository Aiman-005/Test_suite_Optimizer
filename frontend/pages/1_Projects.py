import json
from pathlib import Path
from frontend.components.theme import load_css
import streamlit as st

load_css()
#configuration
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "projects.json"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "site-packages",
    "node_modules",
    "build",
    "dist"
}


# --------------------------------------------------
# Project registry
# --------------------------------------------------

def load_projects():
    if not REGISTRY_PATH.exists():
        return []

    try:
        with REGISTRY_PATH.open("r", encoding="utf-8") as file:
            projects = json.load(file)

        return projects if isinstance(projects, list) else []

    except (json.JSONDecodeError, OSError):
        st.error("Could not read the project registry.")
        return []


def save_projects(projects):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with REGISTRY_PATH.open("w", encoding="utf-8") as file:
        json.dump(projects, file, indent=4)


def contains_python_files(folder):
    for current_folder in folder.rglob("*"):
        if current_folder.is_dir() and current_folder.name in EXCLUDED_DIRS:
            continue

        if current_folder.is_file() and current_folder.suffix == ".py":
            return True

    return False


# --------------------------------------------------
# Page heading
# --------------------------------------------------

st.title("Projects")
st.caption("Register and manage the Python projects you want to analyze.")

projects = load_projects()

st.divider()

# --------------------------------------------------
# Register a project
# --------------------------------------------------

st.subheader("Register a project")
st.write("Add a Python project from a folder on your computer.")

with st.form("register_project_form"):
    project_name = st.text_input(
        "Project name",
        placeholder="e.g. My Python Project"
    )

    project_path = st.text_input(
        "Project folder path",
        placeholder=r"C:\Users\DELL\Documents\my_project"
    )

    submitted = st.form_submit_button(
        "Add project",
        type="primary",
        use_container_width=True
    )

    if submitted:
        if not project_path.strip():
            st.error("Please enter a project folder path.")

        else:
            folder = Path(project_path.strip()).expanduser()

            if not folder.exists() or not folder.is_dir():
                st.error("The specified folder does not exist.")

            elif not contains_python_files(folder):
                st.error("No Python files were found in this folder.")

            else:
                resolved_path = str(folder.resolve())

                duplicate = any(
                    item.get("path") == resolved_path
                    for item in projects
                )

                if duplicate:
                    st.warning("This project is already registered.")

                else:
                    name = project_name.strip() or folder.name

                    projects.append({
                        "name": name,
                        "path": resolved_path
                    })

                    save_projects(projects)

                    st.session_state["selected_project_path"] = resolved_path

                    st.success(f"{name} was registered successfully.")
                    st.rerun()


# --------------------------------------------------
# Registered projects
# --------------------------------------------------

st.divider()
st.subheader("Your projects")

if not projects:
    st.info("No projects registered yet. Add a Python project above.")

else:
    selected_path = st.session_state.get("selected_project_path")

    project_paths = [item["path"] for item in projects]

    if selected_path not in project_paths:
        selected_path = project_paths[0]

    selected_index = project_paths.index(selected_path)

    selected_name = st.selectbox(
        "Select a project",
        options=project_paths,
        index=selected_index,
        format_func=lambda path: next(
            item["name"] for item in projects
            if item["path"] == path
        ),
        key="project_selector"
    )

    st.session_state["selected_project_path"] = selected_name

    selected_project = next(
        item for item in projects
        if item["path"] == selected_name
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("#### " + selected_project["name"])
        st.caption(selected_project["path"])

        if Path(selected_project["path"]).is_dir():
            st.success("Project folder is available")
        else:
            st.warning("Project folder is no longer available")

    with col2:
        st.metric("Registered projects", len(projects))

        if st.button(
            "Remove project",
            use_container_width=True
        ):
            projects = [
                item for item in projects
                if item["path"] != selected_name
            ]

            save_projects(projects)

            st.session_state["selected_project_path"] = (
                projects[0]["path"] if projects else None
            )

            st.rerun()

    st.caption(
        "Removing a project only removes it from this registry. "
        "Your original project folder and files are not deleted."
    )
