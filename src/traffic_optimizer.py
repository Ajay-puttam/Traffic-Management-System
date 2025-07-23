import traci
import time
from typing import Dict, List, Tuple, Any
from density_analyzer import DensityAnalyzer


class TrafficOptimizer:
    """
    AI-based traffic light optimizer that adjusts timing based on vehicle density.
    """

    def __init__(self):
        self.density_analyzer = DensityAnalyzer()
        self.traffic_light_id = "center"
        self.phase_durations = [30, 6, 30, 6]  # Default phase durations
        self.current_phase = 0
        self.phase_start_time = 0
        self.min_phase_duration = 15  # Minimum green time
        self.max_phase_duration = 60  # Maximum green time
        self.yellow_duration = 6  # Yellow light duration
        self.optimization_interval = 5  # Check for optimization every 5 seconds

    def get_current_phase_info(self) -> Dict[str, Any]:
        """
        Get current traffic light phase information.

        Returns:
            Dict containing current phase info
        """
        try:
            current_phase = traci.trafficlight.getPhase(self.traffic_light_id)
            phase_duration = traci.trafficlight.getPhaseDuration(self.traffic_light_id)
            state = traci.trafficlight.getRedYellowGreenState(self.traffic_light_id)
            current_time = traci.simulation.getTime()

            # Handle different return types from traci.simulation.getTime()
            if isinstance(current_time, (tuple, list)):
                current_time = current_time[0] if current_time else 0.0
            else:
                current_time = float(current_time)

            return {
                "phase": current_phase,
                "duration": phase_duration,
                "state": state,
                "time_in_phase": current_time - self.phase_start_time,
            }
        except Exception as e:
            print(f"Error getting phase info: {e}")
            return {
                "phase": 0,
                "duration": 30,
                "state": "GGGgrrrrGGGgrrrr",
                "time_in_phase": 0,
            }

    def optimize_traffic_lights(self) -> Dict[str, Any]:
        """
        Main optimization function that adjusts traffic light timing.

        Returns:
            Dict containing optimization results
        """
        current_time = traci.simulation.getTime()

        # Get current optimization recommendations
        recommendations = self.density_analyzer.get_optimization_recommendations()
        current_phase_info = self.get_current_phase_info()

        optimization_result = {
            "timestamp": current_time,
            "current_phase": current_phase_info["phase"],
            "current_state": current_phase_info["state"],
            "recommendations": recommendations,
            "optimization_applied": False,
            "reason": "No optimization needed",
        }

        # Only optimize during green phases (0 and 2)
        if current_phase_info["phase"] in [0, 2]:
            time_in_phase = current_phase_info["time_in_phase"]

            # Check if we should extend the current phase
            if time_in_phase >= self.min_phase_duration:
                should_extend = self.should_extend_phase(
                    current_phase_info["phase"], recommendations
                )

                if should_extend:
                    # Extend the current phase
                    new_duration = self.calculate_optimal_duration(
                        current_phase_info["phase"], recommendations
                    )
                    traci.trafficlight.setPhaseDuration(
                        self.traffic_light_id, new_duration
                    )

                    optimization_result["optimization_applied"] = True
                    optimization_result["reason"] = (
                        f"Extended phase {current_phase_info['phase']} to {new_duration}s"
                    )
                    optimization_result["new_duration"] = new_duration

        return optimization_result

    def should_extend_phase(self, phase: int, recommendations: Dict[str, Any]) -> bool:
        """
        Determine if the current phase should be extended.

        Args:
            phase: Current traffic light phase
            recommendations: Optimization recommendations

        Returns:
            bool: True if phase should be extended
        """
        if phase == 0:  # North-South green
            north_priority = recommendations["priorities"].get("north_in", 0)
            south_priority = recommendations["priorities"].get("south_in", 0)
            max_priority = max(north_priority, south_priority)

        elif phase == 2:  # East-West green
            east_priority = recommendations["priorities"].get("east_in", 0)
            west_priority = recommendations["priorities"].get("west_in", 0)
            max_priority = max(east_priority, west_priority)

        else:
            return False

        # Extend if priority is high enough
        return max_priority > 50  # Threshold for extension

    def calculate_optimal_duration(
        self, phase: int, recommendations: Dict[str, Any]
    ) -> int:
        """
        Calculate optimal duration for the current phase.

        Args:
            phase: Current traffic light phase
            recommendations: Optimization recommendations

        Returns:
            int: Optimal duration in seconds
        """
        base_duration = 30

        if phase == 0:  # North-South green
            north_density = recommendations["densities"].get("north_in", 0)
            south_density = recommendations["densities"].get("south_in", 0)
            total_density = north_density + south_density

        elif phase == 2:  # East-West green
            east_density = recommendations["densities"].get("east_in", 0)
            west_density = recommendations["densities"].get("west_in", 0)
            total_density = east_density + west_density

        else:
            return base_duration

        # Adjust duration based on density
        if total_density > 0:
            # Scale duration based on density (more density = longer green)
            density_factor = min(2.0, 1 + total_density * 5)  # Max 2x duration
            optimal_duration = int(base_duration * density_factor)

            # Clamp to valid range
            optimal_duration = max(
                self.min_phase_duration, min(self.max_phase_duration, optimal_duration)
            )

            return optimal_duration

        return base_duration

    def handle_emergency_vehicles(self) -> Dict[str, Any]:
        """
        Handle emergency vehicle priority.

        Returns:
            Dict containing emergency handling results
        """
        emergency_result = {
            "emergency_detected": False,
            "action_taken": False,
            "affected_approach": None,
        }
        # Check for emergency vehicles in all approaches
        for approach in self.density_analyzer.approaches:
            emergency_count = self.density_analyzer.check_emergency_vehicles(approach)
            if emergency_count > 0:
                emergency_result["emergency_detected"] = True
                emergency_result["affected_approach"] = approach
                current_phase_info = self.get_current_phase_info()
                # North-South approaches
                if (
                    approach in ["north2center", "south2center"]
                    and current_phase_info["phase"] != 0
                ):
                    traci.trafficlight.setPhase(self.traffic_light_id, 0)
                    traci.trafficlight.setPhaseDuration(self.traffic_light_id, 45)
                    emergency_result["action_taken"] = True
                # East-West approaches
                elif (
                    approach in ["east2center", "west2center"]
                    and current_phase_info["phase"] != 2
                ):
                    traci.trafficlight.setPhase(self.traffic_light_id, 2)
                    traci.trafficlight.setPhaseDuration(self.traffic_light_id, 45)
                    emergency_result["action_taken"] = True
                break
        return emergency_result

    def get_traffic_flow_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive traffic flow metrics.

        Returns:
            Dict containing traffic flow metrics
        """
        metrics = {}

        # Get density and health metrics
        health_metrics = self.density_analyzer.get_system_health_metrics()
        recommendations = self.density_analyzer.get_optimization_recommendations()

        # Calculate flow efficiency
        total_vehicles = health_metrics["total_vehicles"]
        avg_waiting_time = health_metrics["average_waiting_time"]

        # Efficiency score (lower waiting time = higher efficiency)
        efficiency_score = max(0, 100 - avg_waiting_time * 2)

        metrics.update(health_metrics)
        metrics.update(recommendations)
        metrics["efficiency_score"] = efficiency_score
        metrics["current_phase_info"] = self.get_current_phase_info()

        return metrics

    def reset_optimization(self):
        """
        Reset optimization parameters to default.
        """
        self.phase_durations = [30, 6, 30, 6]
        self.current_phase = 0
        self.phase_start_time = 0

        # Reset traffic light to default program
        try:
            traci.trafficlight.setProgram(self.traffic_light_id, 0)
        except:
            pass

    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Get current optimization status and statistics.

        Returns:
            Dict containing optimization status
        """
        current_phase_info = self.get_current_phase_info()
        health_metrics = self.density_analyzer.get_system_health_metrics()

        return {
            "current_phase": current_phase_info["phase"],
            "time_in_phase": current_phase_info["time_in_phase"],
            "total_vehicles": health_metrics["total_vehicles"],
            "emergency_vehicles": health_metrics["emergency_vehicles"],
            "average_waiting_time": health_metrics["average_waiting_time"],
            "efficiency_score": max(
                0, 100 - health_metrics["average_waiting_time"] * 2
            ),
            "congestion_levels": health_metrics["congestion_levels"],
        }
