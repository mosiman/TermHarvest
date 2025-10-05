from aquacrop import AquaCropModel, Soil, Crop, InitialWaterContent
from aquacrop.utils import prepare_weather, get_filepath
from dataclasses import dataclass
import logging


@dataclass
class FarmSector:
    model: AquaCropModel
    sector_id: str
    canopy_cover_history: list[float]


class AquaCropManager:
    def __init__(self, grid_size: tuple[int, int] = (4, 4)):
        self.grid_size: tuple[int, int] = grid_size
        self.sectors: dict[str, FarmSector] = {}
        self.logger: logging.Logger
        self.setup_logging()
        self.initialize_farm()
    
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
        sandy_loam = Soil(soil_type='SandyLoam')
        wheat = Crop('Wheat', planting_date='10/01')
        InitWC = InitialWaterContent(value=['FC'])
        
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        for row in range(self.grid_size[0]):
            for col in range(self.grid_size[1]):
                sector_id = f"{alphabet[row]}{col+1}"
                model = AquaCropModel(
                    sim_start_time='1979/10/01',
                    sim_end_time='1985/05/30',
                    weather_df=weather_data,
                    soil=sandy_loam,
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
                    sector.model._perform_timestep()
                    canopy_cover = sector.model._init_cond.canopy_cover
                    sector.canopy_cover_history.append(canopy_cover)
            
            # Log canopy cover at the end of each day
            if day % 5 == 0:  # Log every 5 days to avoid excessive logging
                canopy_cover = self.get_current_canopy_cover()
                self.logger.info("Day %d - Canopy cover: %s", day + 1, 
                               {s_id: f"{cover:.3f}" for s_id, cover in canopy_cover.items()})
        
        # Log final canopy cover after all days
        final_canopy_cover = self.get_current_canopy_cover()
        self.logger.info("Simulation complete - Final canopy cover: %s", 
                       {s_id: f"{cover:.3f}" for s_id, cover in final_canopy_cover.items()})
    
    def get_canopy_cover_values(self) -> dict[str, list[float]]:
        """Extract canopy cover values for each sector"""
        return {sector_id: sector.canopy_cover_history 
                for sector_id, sector in self.sectors.items()}
    
    def get_current_canopy_cover(self) -> dict[str, float]:
        """Get current canopy cover for each sector"""
        return {sector_id: sector.model._init_cond.canopy_cover 
                for sector_id, sector in self.sectors.items()}