from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, Container, Grid, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Label, Button, Rule, Input, TabbedContent, TabPane
from textual import on
from typing_extensions import override
from dataclasses import dataclass
from enum import Enum, auto

import pyfiglet
from aquacrop_manager import AquaCropManager

import numpy as np

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log.txt')
    ]
)
log = logging.getLogger(__name__)


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
    added_date: str = ""
    
    def __post_init__(self):
        self.cost_str = f"{self.cost} AP"


@dataclass
class GameState:
    aquacrop_manager: AquaCropManager
    date_str: str = ""
    season_str: str = ""
    current_season: int = 1
    previous_season: int = 1
    activity_points_used: int = 0
    max_activity_points: int = 4
    
    def __post_init__(self):
        log.info("GameState post init")
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
    
    def reset_activity_points(self) -> None:
        """Reset activity points at the start of each simulation step"""
        self.activity_points_used = 0
    
    def can_add_task(self, task_cost: int) -> bool:
        """Check if a task can be added without exceeding AP limit"""
        return self.activity_points_used + task_cost <= self.max_activity_points
    
    def add_activity_points(self, cost: int) -> None:
        """Add activity points used"""
        self.activity_points_used += cost


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
                yield HorizontalGroup(
                    WeatherWidget(aquacrop_manager, id="weather_widget"),
                    NDVIDataWidget(aquacrop_manager, id="ndvi_widget", classes="ndviplot"),
                    SoilMoistureWidget(aquacrop_manager, id="moisture_widget", classes="moistureplot"),
                )

    def on_mount(self) -> None:
        """Mount the tabbed content after the main container."""
        # Get the container and mount tabbed content
        container = self.query_one(Container)
        tabs_container = Container(id="tabs_container")
        tabs_container.compose = self.compose_tabs
        container.mount(tabs_container, after="#game_title")
        
        # Update farm plot colors after mounting with a small delay
        self.set_timer(0.1, self.update_farm_plot_colors)
        self.set_timer(0.1, self.update_ndvi_plot_colors)
        self.set_timer(0.1, self.update_moisture_plot_colors)
        
    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab activation events"""
        if event.tab.id == "data_tab":
            # Update weather data when data tab becomes active
            weather_widget = self.query_one("#weather_widget", WeatherWidget)
            if weather_widget:
                weather_widget.update_weather_data()
    
    def update_farm_plot_colors(self) -> None:
        """Update farm plot colors after components are mounted"""
        log.info("Updating farm plot colours")
        farm_plot = self.query_one(".farmplot", FarmPlotVisible)
        if farm_plot:
            farm_plot.update_sector_colors()

    def update_ndvi_plot_colors(self) -> None:
        """Update farm plot colors after components are mounted"""
        log.info("Updating ndvi plot colours")
        ndvi_plot = self.query_one(".ndviplot", NDVIDataWidget)
        if ndvi_plot:
            ndvi_plot.update_sector_colors()

    def update_moisture_plot_colors(self) -> None:
        """Update moisture plot colors after components are mounted"""
        log.info("Updating moisture plot colours")
        moisture_plot = self.query_one(".moistureplot", SoilMoistureWidget)
        if moisture_plot:
            moisture_plot.update_sector_colors()

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
        """Handle /task add [type] [params] command"""
        if not command.startswith("/task add "):
            self.app.bell()  # Alert sound for invalid command
            return
        
        # Extract everything after "/task add "
        params = command[len("/task add "):].strip()
        if not params:
            self.app.bell()
            return
        
        # Parse the task type and parameters
        parts = params.split()
        task_type = parts[0].lower()
        
        # Handle different task types
        if task_type == "investigate" and len(parts) >= 2:
            sector_id = parts[1].upper()
            description = f"Investigate {sector_id}"
            cost = 1
            task_type_enum = TaskType.INVESTIGATE
        
        elif task_type == "irrigate" and len(parts) >= 3:
            sectors = parts[1].upper()
            try:
                amount = int(parts[2])
                description = f"Irrigate {sectors} {amount}mm"
                cost = 2
                task_type_enum = TaskType.IRRIGATE
            except ValueError:
                self.app.bell()
                return
        
        elif task_type == "pesticide" and len(parts) >= 2:
            sector_id = parts[1].upper()
            description = f"Pesticide {sector_id}"
            cost = 1
            task_type_enum = TaskType.PESTICIDE
        
        else:
            self.app.bell()  # Invalid command format
            return
        
        # Find the task list component and add the task
        task_list = self.query_one(".task_list", TaskListAP)
        if task_list:
            if task_list.add_task(description, task_type_enum, cost):
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
        
        # Get current tasks before resetting
        task_list = self.query_one(".task_list", TaskListAP)
        tasks_with_dates = [(game_state.date_str, task.description) for task in task_list.tasks] if task_list else []
        
        game_state.aquacrop_manager.step_simulation(30)
        game_state.update_from_aquacrop()
        
        # Reset activity points for new step
        game_state.reset_activity_points()
        
        # Update the display label
        date_season_label = self.query_one("#date_season_label", Label)
        date_season_label.update(f"{game_state.date_str} | {game_state.season_str}")
        
        # Update farm plot colors
        farm_plot = self.query_one(".farmplot", FarmPlotVisible)
        if farm_plot:
            farm_plot.update_sector_colors()

        # Update ndvi plot colors
        ndvi_plot = self.query_one(".ndviplot", NDVIDataWidget)
        if ndvi_plot:
            ndvi_plot.update_sector_colors()
        
        # Add journal entries for tasks (grouped by date)
        if tasks_with_dates:
            self.add_journal_entries(tasks_with_dates)
        
        # Clear tasks for next step
        if task_list:
            task_list.tasks.clear()
            task_list.refresh_task_display()
        
        # Check if season changed and show modal
        if game_state.season_changed():
            self.app.push_screen(SeasonStatsModal(game_state.current_season))
        
        command_input = self.query_one("#command_input", Input)
        command_input.value = ""  # Clear input
        print("Simulation stepped forward 30 days")
    
    def add_journal_entries(self, tasks_with_dates: list[tuple[str, str]]) -> None:
        """Add journal entries grouped by date"""
        journal = self.query_one(".journal_logs", Journal)
        if journal:
            # Group tasks by date
            tasks_by_date: dict[str, list[str]] = {}
            for date_str, task_desc in tasks_with_dates:
                if date_str not in tasks_by_date:
                    tasks_by_date[date_str] = []
                tasks_by_date[date_str].append(task_desc)
            
            # Add entries for each date
            for date_str, tasks in tasks_by_date.items():
                journal.add_entry(date_str, tasks)

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
        self.tasks: list[Task] = []
        self.next_task_id = 1
    
    def compose(self) -> ComposeResult:
        yield Label("Tasks:", id="tasks_title")
        
        # Add AP usage display
        game_state = self.get_game_state()
        if game_state:
            yield Label(f"AP Used: {game_state.activity_points_used}/{game_state.max_activity_points}", 
                       id="ap_display")
        
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
    
    def get_game_state(self) -> GameState | None:
        """Get the current game state from parent screen"""
        screen = self.screen
        if screen and hasattr(screen, 'query_one'):
            try:
                date_display = screen.query_one("#date_season_display", DateSeasonDisplay)
                return date_display.game_state
            except Exception:
                return None
        return None
    
    def add_task(self, description: str, task_type: TaskType | None = None, cost: int = 1) -> bool:
        """Add a new task with validation, return True if successful"""
        game_state = self.get_game_state()
        
        # Check if task can be added without exceeding AP limit
        if game_state and not game_state.can_add_task(cost):
            self.app.bell()  # Alert for AP limit exceeded
            # Show error modal
            self.app.push_screen(ActivityPointsModal(
                game_state.activity_points_used,
                game_state.max_activity_points,
                cost
            ))
            return False
        
        # Get current date for journal
        current_date = game_state.date_str if game_state else ""
        
        new_task = Task(f"T{self.next_task_id}", description, cost, task_type, current_date)
        self.tasks.append(new_task)
        self.next_task_id += 1
        
        # Add activity points
        if game_state:
            game_state.add_activity_points(cost)
        
        # Refresh the task list display
        self.refresh_task_display()
        
        return True
    
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
        
        # Remove the task and refund AP
        self.tasks.remove(task_to_remove)
        
        game_state = self.get_game_state()
        if game_state:
            game_state.activity_points_used = max(0, game_state.activity_points_used - task_to_remove.cost)
        
        # Refresh the task list display
        self.refresh_task_display()
        
        return True  # Task successfully removed
    
    def refresh_task_display(self) -> None:
        """Refresh the entire task list display including AP counter"""
        # Remove existing displays
        self.query(".task_grid_list").remove()
        
        # Update AP display instead of recreating it
        game_state = self.get_game_state()
        ap_display = self.query_one("#ap_display", Label)
        if ap_display and game_state:
            ap_display.update(f"AP Used: {game_state.activity_points_used}/{game_state.max_activity_points}")
        
        # Add task grid
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
    def __init__(self, date_str: str, tasks: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_str = date_str
        self.tasks = tasks
    
    def compose(self) -> ComposeResult:
        yield Rule()
        yield Label(self.date_str)
        yield Rule()
        for task in self.tasks:
            yield Label(f"- {task}")

class Journal(VerticalScroll):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries: list[JournalEntry] = []
    
    def compose(self) -> ComposeResult:
        for entry in self.entries:
            yield entry
    
    def add_entry(self, date_str: str, tasks: list[str]) -> None:
        """Add a new journal entry"""
        new_entry = JournalEntry(date_str, tasks)
        self.entries.append(new_entry)
        
        # Refresh journal display
        self.query(JournalEntry).remove()
        for entry in self.entries:
            self.mount(entry)

class SoilMoistureWidget(Grid):
    """ The farm plot is hardcoded to be 4x4 for the purposes of this hackathon """

    def __init__(self, aquacrop_manager: AquaCropManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aquacrop_manager = aquacrop_manager

    def compose(self) -> ComposeResult:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        height = 4
        width = 4

        #total accessible water
        taw = self.aquacrop_manager.get_current_hydration()

        grid = [
                [ Label(f"{taw[row + str(col)]:.1f}", id=f"moistureplot_{row}{col}", classes="sector") for col in range(1,width+1)]
            for row in alphabet[0:height]
        ]
        for r in range(0, height):
            for c in range(0, width):
                yield grid[r][c]
        
        # Initial color update
        self.update_sector_colors()

    def interpolate_color(self, value: float) -> str:
        # Convert hex colors to RGB components
        start_color = (0x67, 0x85, 0x98) # #678598
        end_color = (0x14, 0x96, 0xf4) # #1496f4
        
        # typical theta 0.2 - 0.5
        # Clamp value between 0 and 1
        value = max(0.1, min(0.2, value))
        normalized_value = (value - 0.1) / (0.2 - 0.1)
        
        # Interpolate each RGB component
        r = int(start_color[0] + (end_color[0] - start_color[0]) * normalized_value)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * normalized_value)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * normalized_value)
        
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_sector_colors(self) -> None:
        """Update sector background colors based on canopy cover values"""
        log.info("updating sector colours for moisture")
        hydration = self.aquacrop_manager.get_current_hydration()
        log.info(f"hydration: {hydration}")

        for sector_id, hydration_value in hydration.items():
            try:
                sector_widget = self.query_one(f"#moistureplot_{sector_id}", Label)
                color = self.interpolate_color(hydration_value)
                sector_widget.content = f"{hydration_value:.1f}"
                sector_widget.styles.background = color
            except Exception:
                # Widget might not be mounted yet
                pass

class NDVIDataWidget(Grid):
    """ The farm plot is hardcoded to be 4x4 for the purposes of this hackathon """

    def __init__(self, aquacrop_manager: AquaCropManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aquacrop_manager = aquacrop_manager

    def compose(self) -> ComposeResult:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        height = 4
        width = 4

        cc = self.aquacrop_manager.get_current_canopy_cover()

        grid = [
                [ Label(f"{cc[row + str(col)]:.1f}", id=f"ndviplot_{row}{col}", classes="sector") for col in range(1,width+1)]
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

        below_median_colour = "#8b2323"
        median_colour = "#897600"
        above_median_colour = "#44b342"

        """Update sector background colors based on canopy cover values"""
        log.info("updating sector colours for ndvi")
        canopy_cover = self.aquacrop_manager.get_current_canopy_cover()
        log.info(f"canopy cover: {canopy_cover}")

        median_cc = np.median([cover_value for _, cover_value in canopy_cover.items()])
        log.info(f"canop median: {median_cc}")

        for sector_id, cover_value in canopy_cover.items():
            try:
                sector_widget = self.query_one(f"#ndviplot_{sector_id}", Label)
                if cover_value < median_cc:
                    sector_widget.styles.background = below_median_colour
                elif cover_value > median_cc:
                    sector_widget.styles.background = above_median_colour
                else:
                    sector_widget.styles.background = median_colour

                sector_widget.content = f"{cover_value:.1f}"
            except Exception:
                # Widget might not be mounted yet
                pass


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


class ActivityPointsModal(ModalScreen[object]):
    """Modal screen showing activity points exceeded error"""
    
    def __init__(self, current_ap: int, max_ap: int, task_cost: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_ap: int = current_ap
        self.max_ap: int = max_ap
        self.task_cost: int = task_cost
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Activity Points Exceeded", id="ap_error_title"),
            VerticalGroup(
                Label(f"Current AP used: {self.current_ap}/{self.max_ap}"),
                Label(f"Task cost: {self.task_cost} AP"),
                Label("This task would exceed your activity point limit for this session."),
                Label("Remove some tasks or wait until the next simulation step."),
            ),
            Button("OK", id="ok_btn"),
        )

    @on(Button.Pressed, "#ok_btn")
    def close_modal(self) -> None:
        self.app.pop_screen()


class WeatherWidget(Container):
    """Widget to display weather information"""
    
    def __init__(self, aquacrop_manager: AquaCropManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aquacrop_manager: AquaCropManager = aquacrop_manager
    
    @override
    def compose(self) -> ComposeResult:
        yield Label("Weather Data", id="weather_title")
        yield VerticalGroup(
            Label("Previous session temperature: Loading...", id="prev_temp_label"),
            Label("Previous session precipitation: Loading...", id="prev_precip_label"),
            Label("Forecasted precipitation: Loading...", id="forecast_precip_label"),
            Label("Forecasted temperature range: Loading...", id="forecast_temp_label"),
            id="weather_data_group"
        )
    
    def on_mount(self) -> None:
        """Update weather data when widget is mounted"""
        self.update_weather_data()
    
    def update_weather_data(self) -> None:
        """Update weather data display"""
        # Get the game state
        gs = self.get_game_state()

        prev, forecast = gs.aquacrop_manager.weather_data()

        # Update labels
        prev_temp_label = self.query_one("#prev_temp_label", Label)
        prev_precip_label = self.query_one("#prev_precip_label", Label)
        forecast_precip_label = self.query_one("#forecast_precip_label", Label)
        forecast_temp_label = self.query_one("#forecast_temp_label", Label)

        if prev:
            prev_temp_label.update(f"Previous session temperature: {prev.min_temp:.1f}°C to {prev.max_temp:.1f}°C")
            prev_precip_label.update(f"Previous session precipitation: {prev.precipitation:.1f} mm")
        
        forecast_precip_label.update(f"Forecasted precipitation: {forecast.precipitation:.1f} mm")
        forecast_temp_label.update(f"Temperature range: {forecast.min_temp:.1f}°C to {forecast.max_temp:.1f}°C")

    def get_game_state(self) -> GameState | None:
        """Get the current game state from parent screen"""
        screen = self.screen
        if screen and hasattr(screen, 'query_one'):
            try:
                date_display = screen.query_one("#date_season_display", DateSeasonDisplay)
                return date_display.game_state
            except Exception:
                return None
        return None


class FarmingSimApp(App[object]):
    """ An interactive game for the 2025 NASA SpaceApps """

    CSS_PATH = "fs.tcss"

    def on_mount(self) -> None:
        self.push_screen(TitlePage(id = "titlescreen"))



if __name__ == "__main__":
    app = FarmingSimApp()
    app.run()
