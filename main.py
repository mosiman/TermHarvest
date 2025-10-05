from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, Container, Grid, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Label, Button, Rule, Input, TabbedContent, TabPane
from textual import on
from dataclasses import dataclass
from enum import Enum, auto

import pyfiglet
from aquacrop_manager import AquaCropManager


class TaskType(Enum):
    INVESTIGATE = auto()
    IRRIGATE = auto()
    PESTICIDE = auto()

GAME_NAME = "FARMING SIM NAME TBD 2025"

@dataclass
class Task:
    id: str
    description: str
    cost: int
    task_type: TaskType | None = None
    cost_str: str = ""
    
    def __post_init__(self):
        self.cost_str = f"{self.cost} AP"


@dataclass
class GameState:
    aquacrop_manager: AquaCropManager
    date_str: str = ""
    season_str: str = ""
    current_season: int = 1
    previous_season: int = 1
    
    def __post_init__(self):
        self.update_from_aquacrop()
    
    def update_from_aquacrop(self) -> None:
        """Update date and season from aquacrop manager"""
        self.previous_season = self.current_season
        self.current_season = self.aquacrop_manager.get_current_season()
        self.date_str = self.aquacrop_manager.get_current_date()
        self.season_str = f"Season {self.current_season}"
    
    def season_changed(self) -> bool:
        """Check if season has changed since last update"""
        return self.current_season != self.previous_season


class TitlePage(Screen[object]):
    def compose(self) -> ComposeResult:
        title_fig = pyfiglet.figlet_format(GAME_NAME)
        yield Label(title_fig, id="title_label")
        yield HorizontalGroup(Button("Start", id="start_btn"), Button("Options", id="opt_btn"), id="titlepage_menu_btns_grp")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start_btn":
            self.app.push_screen(GameScreen())

class DateSeasonDisplay(Container):
    def __init__(self, game_state: GameState, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_state: GameState = game_state
    
    def compose(self) -> ComposeResult:
        yield Label(f"{self.game_state.date_str} | {self.game_state.season_str}", id="date_season_label")


class GameScreen(Screen[object]):
    def compose(self) -> ComposeResult:
        aquacrop_manager = AquaCropManager()
        game_state = GameState(aquacrop_manager)
        yield Container (
            Label(GAME_NAME, id="game_title"),
            DateSeasonDisplay(game_state, id="date_season_display"),
            Input(placeholder="/help for help", id="command_input"),
            Button("Back to title", id="back_btn"),
        )

    def compose_tabs(self) -> ComposeResult:
        """Compose tabbed content."""
        aquacrop_manager = self.query_one("#date_season_display", DateSeasonDisplay).game_state.aquacrop_manager
        
        with TabbedContent(id="tabs"):
            with TabPane("Main", id="main_tab"):
                yield HorizontalGroup(
                    FarmPlotVisible(aquacrop_manager, classes="farmplot"),
                    TaskListAP(classes="task_list"),
                    Journal(classes="journal_logs"),
                )
            with TabPane("Data", id="data_tab"):
                yield Label("Data tab content coming soon...", id="data_placeholder")

    def on_mount(self) -> None:
        """Mount the tabbed content after the main container."""
        # Get the container and mount tabbed content
        container = self.query_one(Container)
        tabs_container = Container(id="tabs_container")
        tabs_container.compose = self.compose_tabs
        container.mount(tabs_container, after="#game_title")
        
        # Update farm plot colors after mounting with a small delay
        self.set_timer(0.1, self.update_farm_plot_colors)
    
    def update_farm_plot_colors(self) -> None:
        """Update farm plot colors after components are mounted"""
        farm_plot = self.query_one(".farmplot", FarmPlotVisible)
        if farm_plot:
            farm_plot.update_sector_colors()

    def handle_tab_switch(self, command: str) -> None:
        """Handle /tab [tab_name] command"""
        if not command.startswith("/tab "):
            self.app.bell()  # Alert sound for invalid command
            return
        
        tab_name = command[len("/tab "):].strip().lower()
        
        # Get the TabbedContent widget
        tabs = self.query_one("#tabs", TabbedContent)
        
        # Validate tab name and switch
        valid_tabs = {"main": "main_tab", "data": "data_tab"}
        
        if tab_name in valid_tabs:
            tabs.active = valid_tabs[tab_name]
            command_input = self.query_one("#command_input", Input)
            command_input.value = ""  # Clear input
        else:
            self.app.bell()  # Invalid tab name

    @on(Input.Submitted, "#command_input")
    def handle_command(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        print(f"Command received: '{command}'")  # Debug
        if command == "/help":
            self.app.push_screen(HelpModal())
        elif command == "/step":
            self.handle_step_simulation()
        elif command == "/canopy":
            self.handle_show_canopy()
        elif command.startswith("/task add"):
            self.handle_task_add(command)
        elif command.startswith("/task remove"):
            self.handle_task_remove(command)
        elif command.startswith("/tab"):
            self.handle_tab_switch(command)

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
            command_input = self.query_one("#command_input", Input)
            command_input.value = ""  # Clear input
    
    def handle_task_remove(self, command: str) -> None:
        """Handle /task remove [task_id] command"""
        # Extract task ID after "/task remove "
        if not command.startswith("/task remove "):
            self.app.bell()
            return
        
        task_id = command[len("/task remove "):].strip().upper()
        if not task_id:
            self.app.bell()
            return
        
        # Find the task list component and remove the task
        task_list = self.query_one(".task_list", TaskListAP)
        if task_list:
            if task_list.remove_task(task_id):
                command_input = self.query_one("#command_input", Input)
                command_input.value = ""  # Clear input
            else:
                self.app.bell()  # Task not found

    def handle_step_simulation(self) -> None:
        """Handle /step command - advance simulation by 30 days"""
        game_state = self.query_one("#date_season_display", DateSeasonDisplay).game_state
        game_state.aquacrop_manager.step_simulation(30)
        game_state.update_from_aquacrop()
        
        # Update the display label
        date_season_label = self.query_one("#date_season_label", Label)
        date_season_label.update(f"{game_state.date_str} | {game_state.season_str}")
        
        # Update farm plot colors
        farm_plot = self.query_one(".farmplot", FarmPlotVisible)
        if farm_plot:
            farm_plot.update_sector_colors()
        
        # Check if season changed and show modal
        if game_state.season_changed():
            self.app.push_screen(SeasonStatsModal(game_state.current_season))
        
        command_input = self.query_one("#command_input", Input)
        command_input.value = ""  # Clear input
        print("Simulation stepped forward 30 days")

    def handle_show_canopy(self) -> None:
        """Handle /canopy command - show current canopy cover values"""
        game_state = self.query_one("#date_season_display", DateSeasonDisplay).game_state
        canopy_cover = game_state.aquacrop_manager.get_current_canopy_cover()
        
        print("Current Canopy Cover Values:")
        for sector_id, cover in canopy_cover.items():
            print(f"{sector_id}: {cover:.3f}")
        
        # Update farm plot colors
        farm_plot = self.query_one(".farmplot", FarmPlotVisible)
        if farm_plot:
            farm_plot.update_sector_colors()
        
        command_input = self.query_one("#command_input", Input)
        command_input.value = ""  # Clear input

class TaskListAP(Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = [
            Task("T1", "Investigate B3", 1),
            Task("T2", "Fertilize D4", 1),
        ]
        self.next_task_id = len(self.tasks) + 1
    
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
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID, return True if successful"""
        # Find the task to remove
        task_to_remove = None
        for task in self.tasks:
            if task.id == task_id:
                task_to_remove = task
                break
        
        if not task_to_remove:
            return False  # Task not found
        
        # Remove the task
        self.tasks.remove(task_to_remove)
        
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
        
        return True  # Task successfully removed

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

    def __init__(self, aquacrop_manager: AquaCropManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aquacrop_manager = aquacrop_manager

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
        
        # Initial color update
        self.update_sector_colors()

    def interpolate_color(self, value: float) -> str:
        """Interpolate between #b49850 (0.0) and #4b702e (1.0) based on canopy cover"""
        # Convert hex colors to RGB components
        start_color = (0xb4, 0x98, 0x50)  # #b49850
        end_color = (0x4b, 0x70, 0x2e)    # #4b702e
        
        # Clamp value between 0 and 1
        value = max(0.0, min(1.0, value))
        
        # Interpolate each RGB component
        r = int(start_color[0] + (end_color[0] - start_color[0]) * value)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * value)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * value)
        
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_sector_colors(self) -> None:
        """Update sector background colors based on canopy cover values"""
        canopy_cover = self.aquacrop_manager.get_current_canopy_cover()
        
        for sector_id, cover_value in canopy_cover.items():
            try:
                sector_widget = self.query_one(f"#farmplot_{sector_id}", Label)
                color = self.interpolate_color(cover_value)
                sector_widget.styles.background = color
            except Exception:
                # Widget might not be mounted yet
                pass

class HelpModal(ModalScreen[object]):
    """Modal screen showing available commands"""
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Available Commands", id="help_title"),
            VerticalGroup(
                Label("/help - Show this help dialog"),
                Label("/step - Advance simulation by 30 days"),
                Label("/canopy - Show current canopy cover values"),
                Label("/inspect [plot] - Inspect a farm plot"),
                Label("/fertilize [plot] - Fertilize a plot"),
                Label("/irrigate [amount] - Irrigate all plots"),
            ),
            Button("OK", id="ok_btn"),
        )

    @on(Button.Pressed, "#ok_btn")
    def close_modal(self) -> None:
        self.app.pop_screen()


class SeasonStatsModal(ModalScreen[object]):
    """Modal screen showing season statistics"""
    
    def __init__(self, season_number: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season_number: int = season_number
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label(f"Season {self.season_number -1} Summary", id="season_stats_title"),
            VerticalGroup(
                Label("Detailed statistics will be added here"),
                Label("Canopy cover averages, yield data, etc."),
            ),
            Button("OK", id="ok_btn"),
        )

    @on(Button.Pressed, "#ok_btn")
    def close_modal(self) -> None:
        self.app.pop_screen()


class FarmingSimApp(App[object]):
    """ An interactive game for the 2025 NASA SpaceApps """

    CSS_PATH = "fs.tcss"

    def on_mount(self) -> None:
        self.push_screen(TitlePage(id = "titlescreen"))



if __name__ == "__main__":
    app = FarmingSimApp()
    app.run()
