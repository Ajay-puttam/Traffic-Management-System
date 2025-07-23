import os
import sys
import traci
import time
from typing import Dict, Any, Optional
from traffic_optimizer import TrafficOptimizer


class TrafficSimulator:
    """
    Manages SUMO traffic simulation and coordinates with the traffic optimizer.
    """

    def __init__(self, config_path: str = "config/sumo.sumocfg"):
        self.config_path = config_path
        self.optimizer = TrafficOptimizer()
        self.simulation_running = False
        self.simulation_time = 0
        self.optimization_history = []
        self.max_history_length = 100

    def start_simulation(self) -> bool:
        """
        Start the SUMO simulation.

        Returns:
            bool: True if simulation started successfully
        """
        try:
            # Check if SUMO_HOME is set
            if "SUMO_HOME" not in os.environ:
                print("Warning: SUMO_HOME environment variable not set")
                print("Please set SUMO_HOME to your SUMO installation directory")

            # Start SUMO with the configuration
            sumo_binary = "sumo"
            sumo_cmd = [
                sumo_binary,
                "-c",
                self.config_path,
                "--no-step-log",
                "true",
                "--no-warnings",
                "true",
            ]

            traci.start(sumo_cmd)
            self.simulation_running = True
            self.simulation_time = 0

            print("SUMO simulation started successfully")
            return True

        except Exception as e:
            print(f"Error starting SUMO simulation: {e}")
            return False

    def step_simulation(self) -> Dict[str, Any]:
        """
        Step the simulation forward and perform optimization.

        Returns:
            Dict containing simulation step results
        """
        if not self.simulation_running:
            return {"error": "Simulation not running"}

        try:
            # Step the simulation
            traci.simulationStep()
            current_time = traci.simulation.getTime()

            # Handle different return types from traci.simulation.getTime()
            if isinstance(current_time, (tuple, list)):
                current_time = current_time[0] if current_time else 0.0
            else:
                current_time = float(current_time)

            self.simulation_time = current_time

            # Perform optimization
            optimization_result = self.optimizer.optimize_traffic_lights()

            # Handle emergency vehicles
            emergency_result = self.optimizer.handle_emergency_vehicles()

            # Get current metrics
            metrics = self.optimizer.get_traffic_flow_metrics()

            # Store optimization history
            step_result = {
                "timestamp": self.simulation_time,
                "optimization": optimization_result,
                "emergency": emergency_result,
                "metrics": metrics,
            }

            self.optimization_history.append(step_result)
            if len(self.optimization_history) > self.max_history_length:
                self.optimization_history.pop(0)

            return step_result

        except Exception as e:
            print(f"Error in simulation step: {e}")
            return {"error": str(e)}

    def run_simulation_for_duration(self, duration: int) -> Dict[str, Any]:
        """
        Run simulation for a specified duration.

        Args:
            duration: Duration to run in simulation seconds

        Returns:
            Dict containing simulation results
        """
        if not self.simulation_running:
            return {"error": "Simulation not running"}

        # Ensure simulation_time is a float
        current_time = float(self.simulation_time)

        results = {
            "start_time": current_time,
            "end_time": current_time + duration,
            "steps": [],
            "optimizations_applied": 0,
            "emergency_events": 0,
        }

        target_time = current_time + duration

        while self.simulation_time < target_time and self.simulation_running:
            step_result = self.step_simulation()

            if "error" not in step_result:
                results["steps"].append(step_result)

                if step_result["optimization"]["optimization_applied"]:
                    results["optimizations_applied"] += 1

                if step_result["emergency"]["emergency_detected"]:
                    results["emergency_events"] += 1
            else:
                print(f"Simulation step error: {step_result['error']}")
                break

        return results

    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get current simulation status.

        Returns:
            Dict containing simulation status
        """
        if not self.simulation_running:
            return {"status": "stopped"}

        try:
            status = {
                "status": "running",
                "simulation_time": self.simulation_time,
                "total_vehicles": traci.vehicle.getIDCount(),
                "optimization_status": self.optimizer.get_optimization_status(),
                "recent_optimizations": len(
                    [
                        h
                        for h in self.optimization_history
                        if h["optimization"]["optimization_applied"]
                    ]
                ),
            }

            return status

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_vehicle_positions(self) -> Dict[str, Any]:
        """
        Get positions of all vehicles in the simulation.

        Returns:
            Dict containing vehicle positions and information
        """
        if not self.simulation_running:
            return {}

        try:
            vehicles = {}
            vehicle_ids = traci.vehicle.getIDList()

            for vehicle_id in vehicle_ids:
                try:
                    position = traci.vehicle.getPosition(vehicle_id)
                    vehicle_type = traci.vehicle.getTypeID(vehicle_id)
                    speed = traci.vehicle.getSpeed(vehicle_id)
                    waiting_time = traci.vehicle.getWaitingTime(vehicle_id)
                    edge = traci.vehicle.getRoadID(vehicle_id)
                    angle = traci.vehicle.getAngle(vehicle_id)
                    lane = traci.vehicle.getLaneID(vehicle_id)
                    vehicles[vehicle_id] = {
                        "position": position,
                        "type": vehicle_type,
                        "speed": speed,
                        "waiting_time": waiting_time,
                        "edge": edge,
                        "angle": angle,
                        "lane": lane,  # Added lane info
                    }
                except:
                    continue

            return vehicles

        except Exception as e:
            print(f"Error getting vehicle positions: {e}")
            return {}

    def get_traffic_light_state(self) -> Dict[str, Any]:
        """
        Get current traffic light state.

        Returns:
            Dict containing traffic light information
        """
        if not self.simulation_running:
            return {}

        try:
            traffic_light_id = "center"
            phase = traci.trafficlight.getPhase(traffic_light_id)
            state = traci.trafficlight.getRedYellowGreenState(traffic_light_id)
            duration = traci.trafficlight.getPhaseDuration(traffic_light_id)

            # Get current time and handle type conversion
            current_time = traci.simulation.getTime()
            if isinstance(current_time, (tuple, list)):
                current_time = current_time[0] if current_time else 0.0
            else:
                current_time = float(current_time)

            # Ensure duration is a number
            if isinstance(duration, (tuple, list)):
                duration = duration[0] if duration else 1.0
            else:
                duration = float(duration)

            return {
                "phase": phase,
                "state": state,
                "duration": duration,
                "time_in_phase": current_time % duration,
            }

        except Exception as e:
            print(f"Error getting traffic light state: {e}")
            return {}

    def pause_simulation(self):
        """
        Pause the simulation.
        """
        # SUMO doesn't have a built-in pause, but we can stop stepping
        print("Simulation paused (no more steps will be executed)")

    def stop_simulation(self):
        """
        Stop the simulation and close SUMO.
        """
        if self.simulation_running:
            try:
                traci.close()
                self.simulation_running = False
                print("SUMO simulation stopped")
            except Exception as e:
                print(f"Error stopping simulation: {e}")

    def reset_simulation(self) -> bool:
        """
        Reset the simulation to initial state.

        Returns:
            bool: True if reset successful
        """
        try:
            self.stop_simulation()
            time.sleep(1)  # Give SUMO time to close
            success = self.start_simulation()

            if success:
                self.optimization_history.clear()
                self.optimizer.reset_optimization()
                print("Simulation reset successfully")

            return success

        except Exception as e:
            print(f"Error resetting simulation: {e}")
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.

        Returns:
            Dict containing performance metrics
        """
        if not self.simulation_running:
            return {}

        try:
            # Get current metrics
            current_metrics = self.optimizer.get_traffic_flow_metrics()

            # Calculate historical trends
            if len(self.optimization_history) > 0:
                recent_optimizations = self.optimization_history[-10:]  # Last 10 steps
                optimization_rate = len(
                    [
                        h
                        for h in recent_optimizations
                        if h["optimization"]["optimization_applied"]
                    ]
                ) / len(recent_optimizations)

                # Calculate average waiting time trend
                waiting_times = [
                    h["metrics"]["average_waiting_time"] for h in recent_optimizations
                ]
                avg_waiting_time = sum(waiting_times) / len(waiting_times)
            else:
                optimization_rate = 0
                avg_waiting_time = 0

            return {
                "current_metrics": current_metrics,
                "optimization_rate": optimization_rate,
                "average_waiting_time": avg_waiting_time,
                "total_optimizations": len(
                    [
                        h
                        for h in self.optimization_history
                        if h["optimization"]["optimization_applied"]
                    ]
                ),
                "total_emergency_events": len(
                    [
                        h
                        for h in self.optimization_history
                        if h["emergency"]["emergency_detected"]
                    ]
                ),
                "simulation_duration": self.simulation_time,
            }

        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            return {}
