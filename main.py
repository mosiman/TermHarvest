from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, Container, Grid, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Footer, Header, Label, Button, Rule, TextArea, Input
from textual import on
from dataclasses import dataclass
from typing import List

import pyfiglet

GAME_NAME = "FARMING SIM NAME TBD 2025"

@dataclass
class Task:
    id: str
    description: str
    cost: int
    
    def __post_init__(self):
        self.cost_str = f"{self.cost} AP"


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
        elif command.startswith("/task add"):
            self.handle_task_add(command)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_btn":
            self.app.pop_screen()
    
    def handle_task_add(self, command: str) -> None:
        """Handle /task add [description] command"""
        # Extract everything after "/task add "
        if not command.startswith("/task add "):
            self.app.bell()  # Alert sound for invalid command
            return
        
        description = command[len("/task add "):].strip()
        if not description:
            self.app.bell()
            return
        
        # Find the task list component and add the task
        task_list = self.query_one(".task_list", TaskListAP)
        if task_list:
            task_list.add_task(description)
            self.query_one("#command_input").value = ""  # Clear input

class TaskListAP(Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = [
            Task("T1", "Investigate B3", 1),
            Task("T2", "Fertilize D4", 1),
        ]
        self.next_task_id = len(self.tasks) + 1  # Start from T4
    
    def compose(self) -> ComposeResult:
        yield Label("Tasks:", id="tasks_title")
        
        taskGrid = Grid(
            *[widget for task in self.tasks 
              for widget in (
                  Label(task.id, classes="task_id"),
                  Label(task.description, classes="task_desc"),
                  Label(task.cost_str, classes="task_cost")
              )],
            classes="task_grid_list"
        )
        yield taskGrid
    
    def add_task(self, description: str) -> None:
        """Add a new task with the given description"""
        # Simple task cost calculation - could be enhanced
        cost = 2 if "irrigate" in description.lower() else 1
        
        new_task = Task(f"T{self.next_task_id}", description, cost)
        self.tasks.append(new_task)
        self.next_task_id += 1
        
        # Refresh the task list display
        self.query(".task_grid_list").remove()
        
        taskGrid = Grid(
            *[widget for task in self.tasks 
              for widget in (
                  Label(task.id, classes="task_id"),
                  Label(task.description, classes="task_desc"),
                  Label(task.cost_str, classes="task_cost")
              )],
            classes="task_grid_list"
        )
        self.mount(taskGrid)

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
