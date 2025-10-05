from aquacrop import AquaCropModel, Soil, Crop, InitialWaterContent, FieldMngt, GroundWater, IrrigationManagement
from aquacrop.utils import prepare_weather, get_filepath

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def get_baseline_results():
    filepath=get_filepath('tunis_climate.txt')
    weather_data = prepare_weather(filepath)
    sandy_loam = Soil(soil_type='SandyLoam')
    wheat = Crop('Wheat', planting_date='10/01')
    InitWC = InitialWaterContent(value=['FC'])
    model = AquaCropModel(sim_start_time=f'{1979}/10/01',
                          sim_end_time=f'{1985}/05/30',
                          weather_df=weather_data,
                          soil=sandy_loam,
                          crop=wheat,
                          initial_water_content=InitWC)
    model.run_model(till_termination=True)
    np.average(model._outputs.final_stats["Dry yield (tonne/ha)"]) # 8.800
    return model

def get_overirrigated_results():
    # Try with way too much irrigation (expect really bad yields)
    filepath=get_filepath('tunis_climate.txt')
    weather_data = prepare_weather(filepath)
    sandy_loam = Soil(soil_type='SandyLoam')
    wheat = Crop('Wheat', planting_date='10/01')
    InitWC = InitialWaterContent(value=['FC'])
    irrigationStrategy = IrrigationManagement(5, depth=5000, MaxIrr=1000000, MaxIrrSeason=1000000) # max precip in data set is 84 so this is a lot
    model = AquaCropModel(sim_start_time=f'{1979}/10/01',
                          sim_end_time=f'{1985}/05/30',
                          weather_df=weather_data,
                          soil=sandy_loam,
                          crop=wheat,
                          irrigation_management=irrigationStrategy,
                          initial_water_content=InitWC)
    model.run_model(till_termination=True)
    np.average(model._outputs.final_stats["Dry yield (tonne/ha)"]) # 0.07

def single_irrigation_event_injection():
    # Inject a single irrigation event
    # Harvest dates are: 196, 562, 927, 1292, 1657, 2023
    # If we irrigate only once on step 1500, we should see the seasonal irrigation being nonzero on the 4th season only.

    filepath=get_filepath('tunis_climate.txt')
    weather_data = prepare_weather(filepath)
    sandy_loam = Soil(soil_type='SandyLoam')
    wheat = Crop('Wheat', planting_date='10/01')
    InitWC = InitialWaterContent(value=['FC'])
    model = AquaCropModel(sim_start_time=f'{1979}/10/01',
                          sim_end_time=f'{1985}/05/30',
                          weather_df=weather_data,
                          soil=sandy_loam,
                          crop=wheat,
                          initial_water_content=InitWC)
    model._initialize()
    irrigationDay = 1500 # note that this doesn't always get hit .. I think because we skip the off season. e.g. 1000 doesn't work.
    irrigationAmount = 1000 # mm
    default_irrmngt = model._param_struct.IrrMngt
    while not model._clock_struct.model_is_finished:
        s = model._clock_struct.time_step_counter
        if s % 500 == 0:
            print(f"On step {s}")
            print(f"Season: {model._clock_struct.season_counter}")
            print(f"Time step: {model._clock_struct.time_step}")
        if s == irrigationDay:
            print("It's irrigation day")
            model._param_struct.IrrMngt.irrigation_method=5
            model._param_struct.IrrMngt.depth=irrigationAmount
            model._param_struct.IrrMngt.MaxIrr=100000000
            model._param_struct.IrrMngt.MaxIrrSeason=100000000
        else:
            model._param_struct.IrrMngt.irrigation_method=0
            model._param_struct.IrrMngt.depth=0
            model._param_struct.IrrMngt.MaxIrr=25
            model._param_struct.IrrMngt.MaxIrrSeason=10000
        _ = model._perform_timestep()

    print(model._outputs.final_stats)

def model_pest_infestation_via_canopy_cover():
    # Model pest infestations by reducing canopy cover. Should see on average decrease in yield over baseline.
    # at step 0, canopy cover is 0.15.
    # at step 30, still 0.15
    # at step 60, grows to 0.616
    # at step 90, 0.87
    filepath=get_filepath('tunis_climate.txt')
    weather_data = prepare_weather(filepath)
    sandy_loam = Soil(soil_type='SandyLoam')
    wheat = Crop('Wheat', planting_date='10/01')
    InitWC = InitialWaterContent(value=['FC'])
    model = AquaCropModel(sim_start_time=f'{1979}/10/01',
                          sim_end_time=f'{1985}/05/30',
                          weather_df=weather_data,
                          soil=sandy_loam,
                          crop=wheat,
                          initial_water_content=InitWC)
    model._initialize()
    canopy_cover_dmg = 0.05 # 5% canopy cover loss per day
    infestation_day = 60
    while not model._clock_struct.model_is_finished:
        s = model._clock_struct.time_step_counter
        if (s > infestation_day) and (model._clock_struct.season_counter == 0):
            print("THE BUGS!!!!")
            cc = model._init_cond.canopy_cover 
            cc_dmg = model._init_cond.canopy_cover * (1 - canopy_cover_dmg)
            print(f"Before damage: {cc}; After damage: {cc_dmg}")
            model._init_cond.canopy_cover = cc_dmg
        _ = model._perform_timestep()

    print(model._outputs.final_stats)

def run_model_for_steps(model: AquaCropModel | None, steps: int = 50):
    if model is None:
        filepath=get_filepath('tunis_climate.txt')
        weather_data = prepare_weather(filepath)
        sandy_loam = Soil(soil_type='SandyLoam')
        wheat = Crop('Wheat', planting_date='10/01')
        InitWC = InitialWaterContent(value=['FC'])
        model = AquaCropModel(sim_start_time=f'{1979}/10/01',
                              sim_end_time=f'{1985}/05/30',
                              weather_df=weather_data,
                              soil=sandy_loam,
                              crop=wheat,
                              initial_water_content=InitWC)
        model._initialize()
    canopy_cover_dmg = 0.05 # 5% canopy cover loss per day
    infestation_day = 60
    i = 0
    while not model._clock_struct.model_is_finished:
        if i > steps:
            break
        _ = model._perform_timestep()
        i += 1

    print(model._outputs.final_stats)
    return model





