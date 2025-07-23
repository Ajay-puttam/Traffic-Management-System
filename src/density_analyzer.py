import traci
import numpy as np
from typing import Dict, List, Tuple
import time


class DensityAnalyzer:
    """
    Analyzes vehicle density in different approaches and provides optimization recommendations.
    """

    def __init__(self):
        # Updated edge IDs to match the new network
        self.approaches = ["north2center", "south2center", "east2center", "west2center"]
        self.density_history = {approach: [] for approach in self.approaches}
        self.max_history_length = 50  # Keep last 50 density readings
        self.edge_length = 100.0  # meters, as per network definition

    def _get_vehicle_number(self, approach: str) -> int:
        vehicles = traci.edge.getLastStepVehicleNumber(approach)
        if isinstance(vehicles, (tuple, list)):
            vehicles = vehicles[0] if vehicles else 0
        return int(vehicles)

    def _get_vehicle_ids(self, approach: str):
        vehicles = traci.edge.getLastStepVehicleIDs(approach)
        if isinstance(vehicles, (tuple, list)):
            return list(vehicles)
        elif vehicles:
            return [vehicles]
        else:
            return []

    def calculate_density(self, approach: str) -> float:
        """
        Calculate vehicle density for a specific approach.

        Args:
            approach: The approach edge ID (e.g., 'north2center')

        Returns:
            float: Density value (vehicles per meter)
        """
        try:
            vehicles = self._get_vehicle_number(approach)
            density = vehicles / self.edge_length if self.edge_length > 0 else 0
            return density
        except Exception as e:
            print(f"Error calculating density for {approach}: {e}")
            return 0.0

    def get_all_densities(self) -> Dict[str, float]:
        """
        Get density for all approaches.

        Returns:
            Dict[str, float]: Dictionary mapping approach to density
        """
        densities = {}
        for approach in self.approaches:
            density = self.calculate_density(approach)
            densities[approach] = density
            self.density_history[approach].append(density)
            if len(self.density_history[approach]) > self.max_history_length:
                self.density_history[approach].pop(0)
        return densities

    def get_density_trend(self, approach: str, window: int = 10) -> float:
        """
        Calculate the trend of density over time.

        Args:
            approach: The approach edge ID
            window: Number of recent readings to consider

        Returns:
            float: Trend value (positive = increasing, negative = decreasing)
        """
        history = self.density_history[approach]
        if len(history) < window:
            return 0.0
        recent = history[-window:]
        if len(recent) < 2:
            return 0.0
        x = np.arange(len(recent))
        y = np.array(recent)
        try:
            slope = np.polyfit(x, y, 1)[0]
            return slope
        except:
            return 0.0

    def get_priority_score(self, approach: str) -> float:
        """
        Calculate priority score for an approach based on density and trend.

        Args:
            approach: The approach edge ID

        Returns:
            float: Priority score (higher = more priority)
        """
        current_density = self.calculate_density(approach)
        density_trend = self.get_density_trend(approach)
        base_priority = current_density * 100
        trend_bonus = density_trend * 50
        emergency_bonus = self.check_emergency_vehicles(approach) * 200
        total_priority = base_priority + trend_bonus + emergency_bonus
        return max(0, total_priority)

    def check_emergency_vehicles(self, approach: str) -> int:
        """
        Check if there are emergency vehicles on the approach.

        Args:
            approach: The approach edge ID

        Returns:
            int: Number of emergency vehicles
        """
        try:
            vehicles = self._get_vehicle_ids(approach)
            emergency_count = 0
            for vehicle in vehicles:
                vehicle_type = traci.vehicle.getTypeID(vehicle)
                if vehicle_type == "emergency":
                    emergency_count += 1
            return emergency_count
        except Exception as e:
            print(f"Error checking emergency vehicles: {e}")
            return 0

    def get_optimization_recommendations(self) -> Dict[str, any]:
        """
        Get AI-based optimization recommendations.

        Returns:
            Dict containing optimization data
        """
        densities = self.get_all_densities()
        priorities = {
            approach: self.get_priority_score(approach) for approach in self.approaches
        }
        max_priority_approach = max(priorities, key=priorities.get)
        total_density = sum([float(d) for d in densities.values()])
        if total_density > 0:
            base_green_time = 30
            density_ratio = densities[max_priority_approach] / total_density
            recommended_green_time = int(base_green_time * (1 + density_ratio * 2))
            recommended_green_time = max(15, min(60, recommended_green_time))
        else:
            recommended_green_time = 30
        total_vehicles = sum(
            [self._get_vehicle_number(approach) for approach in self.approaches]
        )
        emergency_vehicles = sum(
            [self.check_emergency_vehicles(approach) for approach in self.approaches]
        )
        return {
            "densities": densities,
            "priorities": priorities,
            "recommended_approach": max_priority_approach,
            "recommended_green_time": recommended_green_time,
            "total_vehicles": total_vehicles,
            "emergency_vehicles": emergency_vehicles,
        }

    def get_congestion_level(self, approach: str) -> str:
        """
        Determine congestion level for an approach.

        Args:
            approach: The approach edge ID

        Returns:
            str: Congestion level ('Low', 'Medium', 'High', 'Critical')
        """
        density = self.calculate_density(approach)
        if density < 0.1:
            return "Low"
        elif density < 0.3:
            return "Medium"
        elif density < 0.5:
            return "High"
        else:
            return "Critical"

    def get_system_health_metrics(self) -> Dict[str, any]:
        """
        Get overall system health metrics.

        Returns:
            Dict containing health metrics
        """
        densities = self.get_all_densities()
        total_vehicles = sum(
            [self._get_vehicle_number(approach) for approach in self.approaches]
        )
        emergency_vehicles = sum(
            [self.check_emergency_vehicles(approach) for approach in self.approaches]
        )
        total_waiting_time = 0.0
        vehicle_count = 0
        for approach in self.approaches:
            vehicles = self._get_vehicle_ids(approach)
            for vehicle in vehicles:
                try:
                    waiting_time = float(traci.vehicle.getWaitingTime(vehicle))
                    total_waiting_time += waiting_time
                    vehicle_count += 1
                except:
                    continue
        avg_waiting_time = total_waiting_time / max(1, vehicle_count)
        densities_list = [
            float(d) for d in list(densities.values()) if isinstance(d, (int, float))
        ]
        if densities_list:
            average_density = float(np.mean(densities_list))
            max_density = float(max(densities_list))
        else:
            average_density = 0.0
            max_density = 0.0
        return {
            "total_vehicles": total_vehicles,
            "emergency_vehicles": emergency_vehicles,
            "average_density": average_density,
            "max_density": max_density,
            "average_waiting_time": avg_waiting_time,
            "congestion_levels": {
                approach: self.get_congestion_level(approach)
                for approach in self.approaches
            },
        }
