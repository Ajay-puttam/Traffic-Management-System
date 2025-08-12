import os
import sys
import traci

# Set SUMO_HOME
if "SUMO_HOME" not in os.environ:
    os.environ["SUMO_HOME"] = "C:/Program Files (x86)/Eclipse/Sumo"

# Add SUMO tools to Python path
tools = os.path.join(os.environ["SUMO_HOME"], "tools")
sys.path.append(tools)


def test_sumo():
    """Test basic SUMO functionality"""
    print("Testing SUMO connection...")

    # Create a simple SUMO command
    sumo_cmd = ["sumo", "-c", "sumo_sim/simple_config.sumocfg"]

    try:
        print(f"Starting SUMO with: {' '.join(sumo_cmd)}")
        traci.start(sumo_cmd)
        print("SUMO started successfully!")

        # Run a few simulation steps
        for i in range(10):
            traci.simulationStep()
            time = traci.simulation.getTime()
            vehicles = traci.vehicle.getIDList()
            print(f"Step {i}: Time={time:.1f}s, Vehicles={len(vehicles)}")

        traci.close()
        print("Test completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_sumo()
