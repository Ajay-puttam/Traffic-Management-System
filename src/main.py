#!/usr/bin/env python3
"""
Main application for AI-based Traffic Management System
"""

import os
import sys
import time
import argparse
from traffic_simulator import TrafficSimulator
from visualizer import TrafficVisualizer


def check_sumo_installation():
    """
    Check if SUMO is properly installed and configured.

    Returns:
        bool: True if SUMO is available
    """
    try:
        import traci

        return True
    except ImportError:
        print("Error: SUMO/TraCI not found!")
        print("Please install SUMO and ensure it's in your PATH")
        print("Download from: https://sumo.dlr.de/docs/Downloads.php")
        return False


def check_dependencies():
    """
    Check if all required dependencies are installed.

    Returns:
        bool: True if all dependencies are available
    """
    required_packages = ["pygame", "numpy", "matplotlib"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Error: Missing required packages: {', '.join(missing_packages)}")
        print("Please install using: pip install -r requirements.txt")
        return False

    return True


def run_headless_simulation(duration: int = 3600):
    """
    Run simulation without visualization (headless mode).

    Args:
        duration: Simulation duration in Nseconds
    """
    print("Starting headless simulation...")

    # Create simulator
    simulator = TrafficSimulator()

    # Start simulation
    if not simulator.start_simulation():
        print("Failed to start simulation")
        return

    print(f"Running simulation for {duration} seconds...")
    start_time = time.time()

    # Run simulation
    results = simulator.run_simulation_for_duration(duration)

    end_time = time.time()
    real_time = end_time - start_time

    # Print results
    print("\n=== Simulation Results ===")
    print(
        f"Simulation time: {results.get('end_time', 0) - results.get('start_time', 0):.1f} seconds"
    )
    print(f"Real time: {real_time:.1f} seconds")
    print(
        f"Speed factor: {(results.get('end_time', 0) - results.get('start_time', 0)) / real_time:.1f}x"
    )
    print(f"Optimizations applied: {results.get('optimizations_applied', 0)}")
    print(f"Emergency events: {results.get('emergency_events', 0)}")

    # Get final metrics
    final_metrics = simulator.get_performance_metrics()
    if final_metrics:
        print(
            f"Final efficiency score: {final_metrics.get('current_metrics', {}).get('efficiency_score', 0):.1f}%"
        )
        print(
            f"Average waiting time: {final_metrics.get('average_waiting_time', 0):.1f} seconds"
        )

    # Stop simulation
    simulator.stop_simulation()


def run_visual_simulation(auto_step: bool = True):
    """
    Run simulation with Pygame visualization.

    Args:
        auto_step: Whether to automatically step the simulation
    """
    print("Starting visual simulation...")

    # Create simulator and visualizer
    simulator = TrafficSimulator()
    visualizer = TrafficVisualizer()

    # Connect simulator to visualizer
    visualizer.set_simulator(simulator)

    # Start simulation
    if not simulator.start_simulation():
        print("Failed to start simulation")
        return

    print("Simulation started successfully!")
    print("Controls:")
    print("  SPACE - Step simulation manually")
    print("  R - Reset simulation")
    print("  Q - Quit")
    print("  S - Toggle auto-step mode")

    # This is the new, corrected function call
    # Run visualizer
    visualizer.run(auto_step=auto_step, step_delay=0.01)  # Default to 0.01 second delay


def run_interactive_mode():
    """
    Run in interactive mode with user controls.
    """
    print("Starting interactive simulation...")

    # Create simulator and visualizer
    simulator = TrafficSimulator()
    visualizer = TrafficVisualizer()

    # Connect simulator to visualizer
    visualizer.set_simulator(simulator)

    # Start simulation
    if not simulator.start_simulation():
        print("Failed to start simulation")
        return

    print("Interactive mode started!")
    print("Controls:")
    print("  SPACE - Step simulation")
    print("  R - Reset simulation")
    print("  Q - Quit")

    # Run visualizer without auto-step
    visualizer.run(auto_step=False)


def main():
    """
    Main application entry point.
    """
    parser = argparse.ArgumentParser(description="AI Traffic Management System")
    parser.add_argument(
        "--mode",
        choices=["headless", "visual", "interactive"],
        default="visual",
        help="Simulation mode",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Simulation duration in seconds (headless mode)",
    )
    parser.add_argument(
        "--auto-step",
        action="store_true",
        default=True,
        help="Auto-step simulation (visual mode)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/sumo.sumocfg",
        help="Path to SUMO configuration file",
    )

    args = parser.parse_args()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    if not check_sumo_installation():
        sys.exit(1)

    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}")
        print("Please ensure the SUMO configuration files are in the config/ directory")
        sys.exit(1)

    print("=== AI Traffic Management System ===")
    print("Smart traffic light optimization based on vehicle density")
    print()

    try:
        if args.mode == "headless":
            run_headless_simulation(args.duration)
        elif args.mode == "visual":
            run_visual_simulation(args.auto_step)
        elif args.mode == "interactive":
            run_interactive_mode()

    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Simulation ended")


if __name__ == "__main__":
    main()
