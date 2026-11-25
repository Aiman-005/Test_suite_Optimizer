from frontend.components import project_selection


def test_sync_project_selection_updates_shared_selection(monkeypatch):
    session_state = {
        "selected_project_path": "tinydb",
        "analysis_project_selector": "boltons"
    }
    monkeypatch.setattr(
        project_selection.st,
        "session_state",
        session_state
    )

    project_selection.sync_project_selection(
        "analysis_project_selector"
    )

    assert session_state["selected_project_path"] == "boltons"
