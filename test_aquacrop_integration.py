#!/usr/bin/env python3
"""
Simple test to verify aquacrop integration works
"""

from aquacrop_manager import AquaCropManager

def test_aquacrop_integration():
    """Test that aquacrop manager can be initialized and basic functions work"""
    print("Testing AquaCropManager integration...")
    
    # Test initialization
    manager = AquaCropManager()
    print("✓ AquaCropManager initialized successfully")
    
    # Test sector creation
    sectors = manager.sectors
    print(f"✓ Created {len(sectors)} sectors")
    
    # Test canopy cover retrieval
    canopy_cover = manager.get_current_canopy_cover()
    print(f"✓ Retrieved canopy cover for {len(canopy_cover)} sectors")
    
    # Test stepping simulation
    print("Stepping simulation by 30 days...")
    manager.step_simulation(30)
    print("✓ Simulation stepped successfully")
    
    # Test canopy cover after stepping
    canopy_cover_after = manager.get_current_canopy_cover()
    print("Canopy cover values after 30 days:")
    for sector_id, cover in canopy_cover_after.items():
        print(f"  {sector_id}: {cover:.3f}")
    
    print("\n✓ All tests passed! Aquacrop integration is working.")

if __name__ == "__main__":
    test_aquacrop_integration()