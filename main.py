# main.py

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from src.tui.screens import RFCSelectionScreen

class RFCAnalysisApp(App):
    """A Textual app to analyze RFCs."""

    TITLE = "RFC Analysis Tool"
    SUB_TITLE = "Search, filter, and read RFCs"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(RFCSelectionScreen())

if __name__ == "__main__":
    app = RFCAnalysisApp()
    app.run()