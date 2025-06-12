# src/tui/screens.py

import difflib
import pandas as pd
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Input, Static, Markdown, DataTable, Label, LoadingIndicator
from textual.containers import Vertical, Horizontal, VerticalScroll, Grid

import settings
from src.rfc import setup_rfc_datasets
from src.search import find_sections
from src.ai import query_model


class RFCSelectionScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Welcome to RFC-Analysis", id="title"),
            Static("Load RFCs from settings.py or enter a comma-separated list below.", id="instructions"),
            Button(f"Load from settings.py ({settings.RFCs})", id="from_settings", variant="primary"),
            Input(placeholder="e.g., 2616, 7230, 7231", id="rfc_input"),
            Button("Analyze Entered RFCs", id="from_input", variant="success"),
            id="selection_grid"
        )

    def on_button_pressed(self, event: Button.Pressed):
        rfcs = []
        if event.button.id == "from_settings":
            rfcs = settings.RFCs
        elif event.button.id == "from_input":
            rfc_input = self.query_one("#rfc_input").value
            if rfc_input:
                rfcs = [int(r.strip()) for r in rfc_input.split(',')]
        
        if rfcs:
            self.app.push_screen(MainMenuScreen(rfcs=rfcs))

class MainMenuScreen(Screen):
    def __init__(self, rfcs):
        self.rfcs = rfcs
        self.rfc_df = pd.DataFrame()
        self.section_df = pd.DataFrame()
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(f"Analyzing RFCs: {self.rfcs}", classes="header_label")
        yield Vertical(
            Static("Loading and processing RFCs...", id="loading_label"),
            LoadingIndicator(),
            id="loading_container"
        )

    def on_mount(self):
        # This will run in the background
        self.load_data()

    def load_data(self):
        self.rfc_df, self.section_df = setup_rfc_datasets(self.rfcs)
        self.query_one("#loading_container").remove()
        
        # Add buttons once data is loaded
        self.mount(
            Vertical(
                Button("Read Full RFCs", id="read_full", variant="primary"),
                Button("Search Sections", id="search", variant="primary"),
                classes="main_menu_buttons"
            )
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "read_full":
            self.app.push_screen(ReaderScreen(self.rfc_df, self.section_df))
        elif event.button.id == "search":
            self.app.push_screen(SearchScreen(self.rfc_df, self.section_df))

class SearchScreen(Screen):
    def __init__(self, rfc_df, section_df):
        self.rfc_df = rfc_df
        self.section_df = section_df
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("Search Sections", classes="header_label")
        yield Vertical(
            Input(placeholder="Keyword Search...", id="keyword"),
            Input(placeholder="Regex Search...", id="regex"),
            Input(placeholder="LLM Search (e.g., 'sections about security')...", id="llm"),
            Button("Search", variant="success", id="search_button"),
            id="search_inputs"
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        keyword = self.query_one("#keyword").value
        regex = self.query_one("#regex").value
        llm_prompt = self.query_one("#llm").value

        results_df = find_sections(self.section_df, keyword=keyword, regex=regex, llm_prompt=llm_prompt)
        
        if not results_df.empty:
            self.app.push_screen(ReaderScreen(self.rfc_df, results_df))
        else:
            self.app.push_screen(MessageScreen("No results found."))


class ReaderScreen(Screen):
    def __init__(self, rfc_df, section_df):
        self.rfc_df = rfc_df
        self.section_df = section_df.copy() # Avoid modifying original df
        self.current_section_index = 0
        super().__init__()

    def compose(self) -> ComposeResult:
        self.section_df['id'] = range(len(self.section_df))
        self.section_df['display'] = self.section_df.apply(lambda row: f"RFC {row['rfc']} - {row['number']} {row['title']}", axis=1)

        yield Horizontal(
            VerticalScroll(
                DataTable(id="section_table"),
                id="left_pane"
            ),
            VerticalScroll(
                Markdown(id="content_pane"),
                id="right_pane"
            )
        )
        yield Horizontal(
            Button("Previous", id="prev_section"), Button("Next", id="next_section"),
            Button("LLM Filter: Availability", id="llm_filter"),
            Button("Show Updates/Diff", id="show_updates"),
            classes="reader_buttons"
        )

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_column("Section", key="display")
        for index, row in self.section_df.iterrows():
            table.add_row(row['display'], key=str(row['id']))
        self.update_content()
    
    def update_content(self):
        row = self.section_df.iloc[self.current_section_index]
        title = f"# RFC {row['rfc']} - Section {row['number']}: {row['title']}\n\n"
        content = title + row['content']
        self.query_one("#content_pane").update(content)

    def on_data_table_row_selected(self, event):
        self.current_section_index = self.section_df[self.section_df.id == int(event.row_key.value)].index[0]
        self.update_content()
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "next_section":
            self.current_section_index = min(len(self.section_df) - 1, self.current_section_index + 1)
        elif event.button.id == "prev_section":
            self.current_section_index = max(0, self.current_section_index - 1)
        elif event.button.id == "llm_filter":
            self.apply_llm_filter()
        elif event.button.id == "show_updates":
            self.show_updates_diff()
        self.update_content()

    def show_updates_diff(self):
        section = self.section_df.iloc[self.current_section_index]
        if section['updated_by']:
            new_rfc, new_section_num = section['updated_by'][0]
            new_section = self.section_df[(self.section_df.rfc == new_rfc) & (self.section_df.number == new_section_num)]
            if not new_section.empty:
                old_text = section['content'].splitlines()
                new_text = new_section.iloc[0]['content'].splitlines()
                diff = difflib.unified_diff(old_text, new_text, fromfile=f"RFC {section['rfc']} {section['number']}", tofile=f"RFC {new_rfc} {new_section_num}")
                self.app.push_screen(MessageScreen("```diff\n" + "\n".join(diff) + "\n```"))
            else:
                 self.app.push_screen(MessageScreen("Updated section not found in current dataset."))
        else:
            self.app.push_screen(MessageScreen("No updates found for this section."))

    def apply_llm_filter(self):
        # Example filtering logic
        filtered_indices = []
        for index, row in self.section_df.iterrows():
            _, result = query_model(
                settings.MODEL,
                messages=[{'role': 'user', 'content': f"Extract availability requirements from this text:\n\n{row['content']}"}],
                schema=AvailabilityRequirement
            )
            if result and result.requirement:
                filtered_indices.append(index)
        
        if filtered_indices:
            self.section_df = self.section_df.loc[filtered_indices].reset_index(drop=True)
            self.current_section_index = 0
            self.on_mount() # Redraw table
        else:
            self.app.push_screen(MessageScreen("No sections matched the LLM filter."))

class MessageScreen(ModalScreen):
    def __init__(self, message: str):
        self.message = message
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Markdown(self.message),
            Button("Close", variant="primary"),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()