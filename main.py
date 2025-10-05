from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, Container, Grid, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Footer, Header, Label, Button, Rule, TextArea, Input
from textual import on

import pyfiglet

GAME_NAME = "FARMING SIM NAME TBD 2025"


class TitlePage(Screen):
    def compose(self) -> ComposeResult:
        title_fig = pyfiglet.figlet_format(GAME_NAME)
        yield Label(title_fig, id="title_label")
        yield HorizontalGroup(Button("Start", id="start_btn"), Button("Options", id="opt_btn"), id="titlepage_menu_btns_grp")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start_btn":
            self.app.push_screen(GameScreen())

class GameScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Container (
            Label(GAME_NAME, id="game_title"),
            HorizontalGroup(
                FarmPlotVisible(classes="farmplot"),
                TaskListAP(classes="task_list"),
                Journal(classes="journal_logs"),
            ),
            Label("Farm sim vroom vroom brrrrrrrrr", id="game_subtitle"),
            Input(placeholder="/help for help", id="command_input"),
            Button("Back to title", id="back_btn"),
        )

    @on(Input.Submitted, "#command_input")
    def handle_command(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if command == "/help":
            self.app.push_screen(HelpModal())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_btn":
            self.app.pop_screen()

class TaskListAP(Container):
    def compose(self) -> ComposeResult:
        taskGrid = Grid(
            Label("T1", classes="task_id"),
            Label("Investigate B3", classes="task_desc"),
            Label("1 AP", classes="task_cost"),
            Label("T2", classes="task_id"),
            Label("Fertilize D4", classes="task_desc"),
            Label("1 AP", classes="task_cost"),
            Label("T3", classes="task_id"),
            Label("Irrigate ALL 20mm", classes="task_desc"),
            Label("2 AP", classes="task_cost"),
            classes="task_grid_list"
        )
        yield Label("Tasks:", id="tasks_title")
        yield taskGrid

class CommandLine(Input):
    def compose(self) -> ComposeResult:
        yield Input(placeholder="/help for help")


class JournalEntry(VerticalGroup):
    def compose(self) -> ComposeResult:
        yield Rule()
        yield Label("2025-01-01")
        yield Rule()
        yield Label("Investigate B3: Found pests!")
        yield Label("Fertilized D4")
        yield Label("Irrigate ALL 20mm")

class Journal(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield JournalEntry()
        yield JournalEntry()
        yield JournalEntry()
        yield JournalEntry()

class FarmPlotVisible(Grid):
    """ The farm plot is hardcoded to be 4x4 for the purposes of this hackathon """

    def compose(self) -> ComposeResult:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        height = 4
        width = 4

        grid = [
            [ Label(f"{row}{col}", id=f"farmplot_{row}{col}", classes="sector") for col in range(1,width+1)]
            for row in alphabet[0:height]
        ]
        for r in range(0, height):
            for c in range(0, width):
                yield grid[r][c]

class HelpModal(ModalScreen):
    """Modal screen showing available commands"""
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Available Commands", id="help_title"),
            VerticalGroup(
                Label("/help - Show this help dialog"),
                Label("/inspect [plot] - Inspect a farm plot"),
                Label("/fertilize [plot] - Fertilize a plot"),
                Label("/irrigate [amount] - Irrigate all plots"),
            ),
            Button("OK", id="ok_btn"),
        )

    @on(Button.Pressed, "#ok_btn")
    def close_modal(self) -> None:
        self.app.pop_screen()


class FarmingSimApp(App):
    """ An interactive game for the 2025 NASA SpaceApps """

    CSS_PATH = "fs.tcss"

    def on_mount(self) -> None:
        self.push_screen(TitlePage(id = "titlescreen"))



if __name__ == "__main__":
    app = FarmingSimApp()
    app.run()
