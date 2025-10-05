from aquacrop import AquaCropModel, Soil, Crop, InitialWaterContent
from aquacrop.utils import prepare_weather, get_filepath
from dataclasses import dataclass
import logging
import itertools
import random

import numpy as np


@dataclass
class FarmSector:
    model: AquaCropModel
    sector_id: str
    canopy_cover_history: list[float]


class AquaCropManager:
    def __init__(self, grid_size: tuple[int, int] = (4, 4)):
        self.grid_size: tuple[int, int] = grid_size
        self.sectors: dict[str, FarmSector] = {}
        self.taw_penalty: float = 0.03 # takes two /steps before somewhat visible via canopy cover
        self.dry_sectors: list[str] = []
        self.pest_sectors: list[str] = []
        self.logger: logging.Logger
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
