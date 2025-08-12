import os
import sys
import traci

# Set SUMO_HOME
if "SUMO_HOME" not in os.environ:
    os.environ["SUMO_HOME"] = "C:/Program Files (x86)/Eclipse/Sumo"

# Add SUMO tools to Python path
tools = os.path.join(os.environ["SUMO_HOME"], "tools")
sys.path.append(tools)


def test_connection():
    """Test basic traci connection"""
    print("Testing traci connection...")

    # Use the original working config
    sumo_cmd = ["sumo", "-c", "sumo_sim/sumo_config.sumocfg"]

    try:
        print(f"Starting SUMO with: {' '.join(sumo_cmd)}")
        traci.start(sumo_cmd)
        print("SUMO started successfully!")

        # Just run one step
        traci.simulationStep()
        print("Simulation step completed!")

        traci.close()
        print("Test completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_connection()
