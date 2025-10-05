from aquacrop import AquaCropModel, Soil, Crop, InitialWaterContent
from aquacrop.utils import prepare_weather, get_filepath
from dataclasses import dataclass
import logging
import itertools
import random

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


@dataclass
class FarmSector:
    model: AquaCropModel
    sector_id: str
    canopy_cover_history: list[float]

@dataclass
class SessionWeather:
    session_date: datetime
    min_temp: float
    max_temp: float
    precipitation: float

class AquaCropManager:
    def __init__(self, grid_size: tuple[int, int] = (4, 4)):
        self.grid_size: tuple[int, int] = grid_size
        self.sectors: dict[str, FarmSector] = {}
        self.taw_penalty: float = 0.03 # takes two /steps before somewhat visible via canopy cover
        self.session_days: int = 30 # each "/step" is 30 days
        self.previous_session: datetime | None = None
        self.current_session: datetime
        self.dry_sectors: list[str] = []
        self.pest_sectors: list[str] = []
        self.logger: logging.Logger
        self.weather: pd.DataFrame
        self.setup_logging()
        self.initialize_farm()

    def print_sector_values(self, sector_values: dict[str,float]):
        pretty_str_lines: list[str] = ["\n"]
        # Extract unique rows and columns
        rows = sorted(set(k[0] for k in sector_values.keys()))
        cols = sorted(set(k[1] for k in sector_values.keys()))
        
        # Create grid
        grid = np.full((len(rows), len(cols)), np.nan)
        
        # Fill grid with values
        for sector, value in sector_values.items():
            row_idx = rows.index(sector[0])
            col_idx = cols.index(sector[1])
            grid[row_idx, col_idx] = value
        
        # Print grid with headers
        pretty_str_lines.append("    " + "   ".join(cols))  # Column headers
        for i, row in enumerate(rows):
            row_str = f"{row} | "
            for j, col in enumerate(cols):
                if not np.isnan(grid[i, j]):
                    row_str += f"{grid[i, j]:.2f} "
                else:
                    row_str += "  -   "
            pretty_str_lines.append(row_str)

        return "\n".join(pretty_str_lines)
    
    def setup_logging(self) -> None:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('log.txt'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("AquaCropManager initialized with %s grid", self.grid_size)
    
    def initialize_farm(self) -> None:
        """Initialize 4x4 farm with hardcoded parameters"""
        weather_data = prepare_weather(get_filepath('tunis_climate.txt'))
        default_soil_type = Soil(soil_type='SandyLoam')
        bad_soil_type = Soil(soil_type = 'Sand') # Not bad for all crops ... maybe just for this one.
        wheat = Crop('Wheat', planting_date='10/01')
        InitWC = InitialWaterContent(value=['FC'])
        
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        self.weather = weather_data

        # Pick two random sectors to have bad_soil_type
        all_points = [(i, j) for i in range(self.grid_size[0]) for j in range(self.grid_size[1])]
        dry_sectors_xy: list[tuple[int,int]] = random.sample(all_points, 2)

        
        for row in range(self.grid_size[0]):
            for col in range(self.grid_size[1]):
                sector_id = f"{alphabet[row]}{col+1}"
                if (row,col) in dry_sectors_xy:
                    self.dry_sectors.append(sector_id)
                    soil_type = bad_soil_type
                    # make it even worse by reducing the holding capacity?. via reducing field capacity.
                    self.logger.info(f"Sector {sector_id} will have taw penalties on every step")
                else:
                    soil_type = default_soil_type
                model = AquaCropModel(
                    sim_start_time='1979/10/01',
                    sim_end_time='1985/05/30',
                    weather_df=weather_data,
                    soil=soil_type,
                    crop=wheat,
                    initial_water_content=InitWC
                )
                model._initialize()
                self.sectors[sector_id] = FarmSector(model, sector_id, [])

        self.current_session = self.get_session_date()
        
        initial_canopy_cover = self.get_current_canopy_cover()
        self.logger.info("Farm initialized - Initial canopy cover: %s", 
                       {s_id: f"{cover:.3f}" for s_id, cover in initial_canopy_cover.items()})
    
    def step_simulation(self, days: int = 30) -> None:
        """Step all sectors forward by specified days"""
        self.logger.info("Stepping simulation by %d days", days)
        
        for day in range(days):
            for sector in self.sectors.values():
                if not sector.model._clock_struct.model_is_finished:
                    # Check for sector buffs / debuffs
                    if sector.sector_id in self.dry_sectors:
                        # Lose self.taw_penalty of TAW per day
                        old_th = sector.model._init_cond.th
                        sector.model._init_cond.th = sector.model._init_cond.th * (1 - self.taw_penalty)
                        self.logger.debug(f"Sector {sector.sector_id} TAW debuff. Old: {old_th} new: {sector.model._init_cond.th}")
                    sector.model._perform_timestep()
                    canopy_cover = sector.model._init_cond.canopy_cover
                    sector.canopy_cover_history.append(canopy_cover)
            
        
        # Update session
        self.current_session = self.get_session_date()
        # Log final canopy cover after all days
        canopy_cover = self.get_current_canopy_cover()
        biomass = self.get_current_biomass()

        # self.logger.info("Simulation complete - Final canopy cover: %s", 
        #                {s_id: f"{cover:.3f}" for s_id, cover in final_canopy_cover.items()})

        pretty_canopy = self.print_sector_values(canopy_cover)
        pretty_biomass = self.print_sector_values(biomass)
        self.logger.info("========== SIMULATION COMPLETE ==========")
        self.logger.info(f"Final canopy cover: {pretty_canopy}")
        self.logger.info(f"Final biomass: {pretty_biomass}")
    
    def get_canopy_cover_values(self) -> dict[str, list[float]]:
        """Extract canopy cover values for each sector"""
        return {sector_id: sector.canopy_cover_history 
                for sector_id, sector in self.sectors.items()}
    
    def get_current_canopy_cover(self) -> dict[str, float]:
        """Get current canopy cover for each sector"""
        return {sector_id: sector.model._init_cond.canopy_cover 
                for sector_id, sector in self.sectors.items()}

    def get_current_biomass(self) -> dict[str, float]:
        """Get current canopy cover for each sector"""
        return {sector_id: sector.model._init_cond.biomass 
                for sector_id, sector in self.sectors.items()}

    def get_current_hydration(self) -> dict[str, float]:
        """Get current canopy cover for each sector"""
        return {sector_id: sector.model._init_cond.biomass 
                for sector_id, sector in self.sectors.items()}
    
    def get_current_season(self) -> int:
        """Get current season from the first sector's model"""
        if not self.sectors:
            return 1
        first_sector = next(iter(self.sectors.values()))
        # Season counter starts at 0, so add 1 for display
        return first_sector.model._clock_struct.season_counter + 1

    def get_session_date(self) -> datetime:
        first_sector = next(iter(self.sectors.values()))
        step_start_time: datetime = first_sector.model._clock_struct.step_start_time.to_pydatetime()
        return step_start_time
    
    def get_current_date(self) -> str:
        """Get current date from the first sector's model"""
        if not self.sectors:
            return "1979-10-01"
        first_sector = next(iter(self.sectors.values()))
        timestamp = first_sector.model._clock_struct.step_start_time
        try:
            return timestamp.strftime("%Y-%m-%d")
        except AttributeError:
            # Fallback if timestamp is not a datetime-like object
            return "1979-10-01"

    def weather_data(self) -> tuple[SessionWeather | None, SessionWeather]:
        # Return the previous session weather
        # Return the forecasted high / lows (add a fudge factor)

        wdf = self.weather

        # If no previous session, don't return data for that
        if self.previous_session is None:
            prevSessionWeather = None
        else:
            prevSessionWeatherDf = wdf[
                (wdf['Date'] >= previous_session) & 
                (wdf['Date'] <= current_session)
            ]
            # Calculate the statistics
            lowest_low: float = prevSessionWeatherDf['MinTemp'].min()
            highest_high: float = prevSessionWeatherDf['MaxTemp'].max()
            precipitation_sum: float = prevSessionWeatherDf['Precipitation'].sum()

            # Create the dataclass instance
            prevSessionWeather = SessionWeather(
                session_date=self.previous_session,
                min_temp=lowest_low,
                max_temp=highest_high,
                precipitation=precipitation_sum
            )


        # For forecasts, take the average min, average max, and avg precipitation * session step length
        forecastSessionWeatherDf = wdf[
            (wdf['Date'] > self.current_session) & 
            (wdf['Date'] <= self.current_session + timedelta(days=self.session_days))
        ]
        # Calculate the statistics

        forecast_low: float = np.average(forecastSessionWeatherDf['MinTemp'])
        forecast_high: float = np.average(forecastSessionWeatherDf['MaxTemp'])
        forecast_precip: float = np.average(forecastSessionWeatherDf['Precipitation']) * 30

        forecastSessionWeather = SessionWeather(
            session_date=self.current_session,
            min_temp=forecast_low,
            max_temp=forecast_high,
            precipitation=forecast_precip
        )

        return (prevSessionWeather, forecastSessionWeather)


    def get_current_weather(self) -> dict[str, float]:
        """Get current weather data from the first sector's model"""
        if not self.sectors:
            return {"precipitation": 0.0, "min_temp": 0.0, "max_temp": 0.0, "et0": 0.0}
        
        first_sector = next(iter(self.sectors.values()))
        return {
            "precipitation": first_sector.model._init_cond.precipitation,
            "min_temp": first_sector.model._init_cond.temp_min,
            "max_temp": first_sector.model._init_cond.temp_max,
            "et0": first_sector.model._init_cond.et0
        }

    def get_weather_forecast(self, days: int = 30) -> list[dict[str, float]]:
        """Get weather forecast for the next specified number of days"""
        if not self.sectors:
            return []
        
        first_sector = next(iter(self.sectors.values()))
        
        # Check if model is properly initialized
        if not hasattr(first_sector.model, '_clock_struct') or not hasattr(first_sector.model, '_param_struct'):
            self.logger.warning("Model not properly initialized for weather forecast")
            return self._get_sample_weather_forecast(days)
        
        current_step = first_sector.model._clock_struct.time_step_counter
        weather_data = first_sector.model.weather_df
        
        # Debug logging
        self.logger.debug(f"Weather forecast: current_step={current_step}, weather_data_length={len(weather_data)}")
        
        # If we're at the end of the simulation, return empty forecast
        if current_step >= len(weather_data):
            self.logger.warning(f"Current step {current_step} exceeds weather data length {len(weather_data)}")
            return []
        
        forecast = []
        for i in range(current_step, min(current_step + days, len(weather_data))):
            row = weather_data.iloc[i]
            forecast.append({
                "min_temp": float(row["MinTemp"]),
                "max_temp": float(row["MaxTemp"]),
                "precipitation": float(row["Precipitation"]),
                "et0": float(row["ReferenceET"])
            })
        
        self.logger.debug(f"Weather forecast result: {len(forecast)} days")
        return forecast
    
    def _get_sample_weather_forecast(self, days: int = 30) -> list[dict[str, float]]:
        """Get sample weather forecast from the initial weather data"""
        try:
            from aquacrop.utils import prepare_weather, get_filepath
            weather_data = prepare_weather(get_filepath('tunis_climate.txt'))
            
            forecast = []
            for i in range(min(days, len(weather_data))):
                row = weather_data.iloc[i]
                forecast.append({
                    "min_temp": float(row["MinTemp"]),
                    "max_temp": float(row["MaxTemp"]),
                    "precipitation": float(row["Precipitation"]),
                    "et0": float(row["ReferenceET"])
                })
            
            self.logger.debug(f"Sample weather forecast: {len(forecast)} days")
            return forecast
        except Exception as e:
            self.logger.error(f"Error getting sample weather forecast: {e}")
            return []

    def get_previous_session_precipitation(self) -> float:
        """Get total precipitation from the previous simulation session (30 days)"""
        if not self.sectors:
            return 0.0
        
        first_sector = next(iter(self.sectors.values()))
        
        # Check if model is properly initialized
        if not hasattr(first_sector.model, '_clock_struct') or not hasattr(first_sector.model, '_param_struct'):
            self.logger.warning("Model not properly initialized for precipitation data")
            return 0.0
        
        current_step = first_sector.model._clock_struct.time_step_counter
        
        # Debug logging
        self.logger.debug(f"Previous precipitation: current_step={current_step}")
        
        # If this is the first session, return 0
        if current_step <= 30:
            self.logger.debug("First session, returning 0 precipitation")
            return 0.0
        
        weather_data = first_sector.model.weather_df
        
        # Sum precipitation from previous 30 days
        total_precip = 0.0
        start_step = max(0, current_step - 30)
        for i in range(start_step, current_step):
            total_precip += float(weather_data.iloc[i]["Precipitation"])
        
        self.logger.debug(f"Previous precipitation total: {total_precip}")
        return total_precip
