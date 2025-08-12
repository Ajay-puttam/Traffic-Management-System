import traci
import time
import logging
from typing import Dict, List, Optional, Any
from density_analyzer import DensityAnalyzer


class TrafficOptimizer:
    """
    AI-based traffic light optimizer that adjusts timing based on vehicle density and other real-time factors.
    """

    def __init__(self):
        self.density_analyzer = DensityAnalyzer()
        self.traffic_light_id = "center"
        self.phase_start_time = 0.0
        self.current_phase_index = 0

        # --- THIS IS THE FIX ---
        # Define the phases with the yellow light duration reduced to 3 seconds
        self.phases = [
            {
                "duration": 30,
                "state": "GGGggrrrrrGGGggrrrrr",
            },  # Phase 0: North-South Green
            {
                "duration": 3,
                "state": "yyyyyrrrrryyyyyrrrrr",
            },  # Phase 1: North-South Yellow
            {
                "duration": 30,
                "state": "rrrrrGGGggrrrrrGGGgg",
            },  # Phase 2: East-West Green
            {
                "duration": 3,
                "state": "rrrrryyyyyrrrrryyyyy",
            },  # Phase 3: East-West Yellow
        ]

        # Constants
        self.MIN_GREEN = 15
        self.MAX_GREEN = 90
        self.MAX_WAIT_TIME = 60  # Max time a direction can wait for a green light
        self.PREEMPTIVE_SWITCH_THRESHOLD = (
            1.5  # Switch if waiting priority is 1.5x higher
        )

    def get_current_phase_info(self) -> Dict[str, Any]:
        """Get the current traffic light phase and time spent."""
        try:
            current_time = float(traci.simulation.getTime())
            phase_index = traci.trafficlight.getPhase(self.traffic_light_id)
            # Ensure phase_index is within the valid range
            if 0 <= phase_index < len(self.phases):
                phase_duration = self.phases[phase_index]["duration"]
            else:
                phase_duration = 30  # Default duration if phase is out of bounds

            return {
                "phase": phase_index,
                "duration": phase_duration,
                "state": traci.trafficlight.getRedYellowGreenState(
                    self.traffic_light_id
                ),
                "time_in_phase": current_time - self.phase_start_time,
            }
        except Exception as e:
            logging.warning(f"[Phase Info] Error: {e}")
            return {
                "phase": 0,
                "duration": 30,
                "state": "GGGgrrrrGGGgrrrr",
                "time_in_phase": 0,
            }

    def optimize_traffic_lights(self) -> Dict[str, Any]:
        """Dynamically adjust signal timing based on real-time traffic data."""
        current_time = traci.simulation.getTime()
        phase_info = self.get_current_phase_info()
        recs = self.density_analyzer.get_optimization_recommendations()

        # Check for preemptive switch
        if self._should_preempt(phase_info, recs):
            self._switch_to_next_phase(current_time, recs)
        # Check if it's time to switch to the next phase based on duration
        elif phase_info["time_in_phase"] >= phase_info["duration"]:
            self._switch_to_next_phase(current_time, recs)

        return {
            "timestamp": current_time,
            "current_phase": self.current_phase_index,
            "recommendations": recs,
        }

    def _should_preempt(self, phase_info: Dict[str, Any], recs: Dict[str, Any]) -> bool:
        """Determines if a preemptive switch is needed."""
        if phase_info["phase"] not in [0, 2]:  # Only check green phases
            return False

        if phase_info["time_in_phase"] < self.MIN_GREEN:
            return False

        priorities = recs["priorities"]
        current_priority = 0
        waiting_priority = 0

        if phase_info["phase"] == 0:  # North-South is green
            current_priority = max(
                priorities.get("north2center", 0), priorities.get("south2center", 0)
            )
            waiting_priority = max(
                priorities.get("east2center", 0), priorities.get("west2center", 0)
            )
        elif phase_info["phase"] == 2:  # East-West is green
            current_priority = max(
                priorities.get("east2center", 0), priorities.get("west2center", 0)
            )
            waiting_priority = max(
                priorities.get("north2center", 0), priorities.get("south2center", 0)
            )

        return waiting_priority > current_priority * self.PREEMPTIVE_SWITCH_THRESHOLD

    def _switch_to_next_phase(self, current_time: float, recs: Dict[str, Any]):
        """Switches the traffic light to the next phase."""
        self.current_phase_index = (self.current_phase_index + 1) % len(self.phases)

        # If the new phase is a green light phase, calculate its optimal duration
        if self.current_phase_index in [0, 2]:
            new_duration = self._calculate_optimal_duration(
                self.current_phase_index, recs
            )
            self.phases[self.current_phase_index]["duration"] = new_duration

        traci.trafficlight.setPhase(self.traffic_light_id, self.current_phase_index)
        # Use the duration from the phases list, which might be newly calculated
        traci.trafficlight.setPhaseDuration(
            self.traffic_light_id, self.phases[self.current_phase_index]["duration"]
        )
        self.phase_start_time = current_time

    def _calculate_optimal_duration(
        self, phase_index: int, recs: Dict[str, Any]
    ) -> int:
        """Compute optimal green light duration based on density and priority."""
        priorities = recs["priorities"]

        if phase_index == 0:  # North-South
            priority = max(
                priorities.get("north2center", 0), priorities.get("south2center", 0)
            )
        elif phase_index == 2:  # East-West
            priority = max(
                priorities.get("east2center", 0), priorities.get("west2center", 0)
            )
        else:
            return self.phases[phase_index]["duration"]

        # Scale duration based on priority score
        duration = self.MIN_GREEN + (priority / 100) * (self.MAX_GREEN - self.MIN_GREEN)

        return int(max(self.MIN_GREEN, min(self.MAX_GREEN, duration)))

    def handle_emergency_vehicles(self) -> Dict[str, Any]:
        """Give priority to emergency vehicles."""
        result = {
            "emergency_detected": False,
            "action_taken": False,
            "affected_approach": None,
        }
        for approach in self.density_analyzer.approaches:
            if self.density_analyzer.check_emergency_vehicles(approach) > 0:
                result.update(
                    {"emergency_detected": True, "affected_approach": approach}
                )
                phase = self.get_current_phase_info()["phase"]
                if approach in ["north2center", "south2center"] and phase != 0:
                    traci.trafficlight.setPhase(self.traffic_light_id, 0)
                    traci.trafficlight.setPhaseDuration(self.traffic_light_id, 60)
                    result["action_taken"] = True
                elif approach in ["east2center", "west2center"] and phase != 2:
                    traci.trafficlight.setPhase(self.traffic_light_id, 2)
                    traci.trafficlight.setPhaseDuration(self.traffic_light_id, 60)
                    result["action_taken"] = True
                break
        return result

    def manage_junction_yielding(self) -> Dict[str, Any]:
        """Ensure vehicles turning left yield to straight-moving vehicles."""
        actions = []
        turning_left, going_straight = [], []

        try:
            for vid in traci.vehicle.getIDList():
                road = traci.vehicle.getRoadID(vid)
                route = traci.vehicle.getRoute(vid)
                if road not in route:
                    continue
                pos = traci.vehicle.getLanePosition(vid)
                lane_len = traci.lane.getLength(traci.vehicle.getLaneID(vid))
                if lane_len - pos < 25:
                    idx = route.index(road)
                    if idx + 1 < len(route):
                        next_edge = route[idx + 1]
                        info = {"id": vid, "current": road, "next": next_edge}
                        if self._is_left_turn(road, next_edge):
                            turning_left.append(info)
                        elif self._is_straight(road, next_edge):
                            going_straight.append(info)

            for tveh in turning_left:
                oncoming = self._find_oncoming_vehicle(tveh, going_straight)
                if oncoming:
                    traci.vehicle.setSpeed(tveh["id"], 0.0)
                    actions.append(f"{tveh['id']} yields to {oncoming['id']}")
        except traci.TraCIException:
            pass

        return {"yielding_actions": actions, "applied": bool(actions)}

    def _is_left_turn(self, curr: str, nxt: str) -> bool:
        return {
            "north2center": "center2east",
            "south2center": "center2west",
            "east2center": "center2south",
            "west2center": "center2north",
        }.get(curr) == nxt

    def _is_straight(self, curr: str, nxt: str) -> bool:
        return {
            "north2center": "center2south",
            "south2center": "center2north",
            "east2center": "center2west",
            "west2center": "center2east",
        }.get(curr) == nxt

    def _find_oncoming_vehicle(
        self, turner: Dict, straight: List[Dict]
    ) -> Optional[Dict]:
        """Detect oncoming vehicle conflicting with a left-turner."""
        opp = {
            "north2center": "south2center",
            "south2center": "north2center",
            "east2center": "west2center",
            "west2center": "east2center",
        }.get(turner["current"])
        return next((v for v in straight if v["current"] == opp), None)

    def get_traffic_flow_metrics(self) -> Dict[str, Any]:
        """Combine system health and current signal state."""
        health = self.density_analyzer.get_system_health_metrics()
        recs = self.density_analyzer.get_optimization_recommendations()
        score = max(0, 100 - health["average_waiting_time"] * 2)

        return {
            **health,
            **recs,
            "efficiency_score": score,
            "current_phase_info": self.get_current_phase_info(),
        }

    def reset_optimization(self):
        """Reset to default program."""
        self.phase_start_time = 0
        self.current_phase_index = 0
        try:
            # Re-apply the initial program logic
            traci.trafficlight.setPhase(self.traffic_light_id, 0)
            traci.trafficlight.setPhaseDuration(
                self.traffic_light_id, self.phases[0]["duration"]
            )
        except Exception:
            pass

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get real-time optimization stats."""
        phase_info = self.get_current_phase_info()
        health = self.density_analyzer.get_system_health_metrics()
        return {
            "current_phase": phase_info["phase"],
            "time_in_phase": phase_info["time_in_phase"],
            "total_vehicles": health["total_vehicles"],
            "emergency_vehicles": health["emergency_vehicles"],
            "average_waiting_time": health["average_waiting_time"],
            "efficiency_score": max(0, 100 - health["average_waiting_time"] * 2),
            "congestion_levels": health["congestion_levels"],
        }
