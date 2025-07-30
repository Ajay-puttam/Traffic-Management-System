import pygame
import sys
import math
import os
import random
from typing import Dict, Any, Tuple, List
from traffic_simulator import TrafficSimulator
import xml.etree.ElementTree as ET
import re


class TrafficVisualizer:
    """
    Pygame-based visualizer for the traffic simulation with AI optimization display.
    """

    def __init__(self, width: int = 1200, height: int = 800):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("AI Traffic Management System")

        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (128, 128, 128)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)
        self.BLUE = (0, 0, 255)
        self.ORANGE = (255, 165, 0)
        self.PURPLE = (128, 0, 128)
        self.CYAN = (0, 255, 255)

        # Fonts
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_large = pygame.font.Font(None, 48)

        # Simulation area (centered, fills window)
        self.sim_area = pygame.Rect(0, 0, self.width, self.height)
        self.info_area = pygame.Rect(700, 50, 450, 700)

        # SUMO network bounds (from convBoundary in intersection.net.xml)
        self.sumo_x_min = 0.0
        self.sumo_x_max = 200.0
        self.sumo_y_min = 0.0
        self.sumo_y_max = 200.0
        # SUMO netOffset correction
        self.net_offset_x = 100.0
        self.net_offset_y = 100.0

        # --- Parse SUMO network bounds and netOffset from XML ---
        net_xml = "config/intersection.net.xml"
        try:
            tree = ET.parse(net_xml)
            root = tree.getroot()
            location = root.find("location")
            if location is not None:
                net_offset_str = location.attrib.get("netOffset", "0.0,0.0")
                conv_boundary_str = location.attrib.get(
                    "convBoundary", "0.0,0.0,200.0,200.0"
                )
                self.net_offset_x, self.net_offset_y = map(
                    float, net_offset_str.split(",")
                )
                x_min, y_min, x_max, y_max = map(float, conv_boundary_str.split(","))
                self.sumo_x_min = x_min
                self.sumo_x_max = x_max
                self.sumo_y_min = y_min
                self.sumo_y_max = y_max
            else:
                # Fallback to defaults if <location> not found
                self.sumo_x_min = 0.0
                self.sumo_x_max = 200.0
                self.sumo_y_min = 0.0
                self.sumo_y_max = 200.0
                self.net_offset_x = 100.0
                self.net_offset_y = 100.0
        except Exception as e:
            print(f"[WARN] Could not parse network bounds from {net_xml}: {e}")
            self.sumo_x_min = 0.0
            self.sumo_x_max = 200.0
            self.sumo_y_min = 0.0
            self.sumo_y_max = 200.0
            self.net_offset_x = 100.0
            self.net_offset_y = 100.0

        # Vehicle PNGs (smaller sizes for better fit)
        self.car_pngs = [
            pygame.transform.scale(
                pygame.image.load(os.path.join("images", "Audi.png")), (24, 48)
            ),
            pygame.transform.scale(
                pygame.image.load(os.path.join("images", "Black_viper.png")), (24, 48)
            ),
            pygame.transform.scale(
                pygame.image.load(os.path.join("images", "car.png")), (24, 48)
            ),
            pygame.transform.scale(
                pygame.image.load(os.path.join("images", "Mini_truck.png")), (24, 48)
            ),
        ]
        self.vehicle_images = {
            "car": self.car_pngs,
            "bus": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "bus.png")), (30, 60)
            ),
            "bike": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "bike.png")), (14, 28)
            ),
            "emergency": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "Ambulance.png")), (24, 48)
            ),
        }

        # Traffic light positions (relative to intersection center)
        self.traffic_light_positions = {
            "north": (300, 100),
            "south": (300, 500),
            "east": (500, 300),
            "west": (100, 300),
        }

        self.simulator = None
        self.clock = pygame.time.Clock()
        self.running = False
        self.lane_shapes = self.load_lane_shapes("config/intersection.net.xml")

    def load_lane_shapes(self, xml_path):
        lane_shapes = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for edge in root.findall(".//edge"):
                for lane in edge.findall("lane"):
                    lane_id = lane.attrib["id"]
                    shape_str = lane.attrib.get("shape", "")
                    if shape_str:
                        points = [
                            tuple(map(float, pt.split(",")))
                            for pt in shape_str.strip().split()
                        ]
                        lane_shapes[lane_id] = points
        except Exception as e:
            print(f"Error loading lane shapes: {e}")
        return lane_shapes

    def interpolate_along_shape(self, shape, pos):
        # shape: list of (x, y), pos: distance from start
        if not shape or len(shape) < 2:
            return shape[0] if shape else (0, 0)
        total = 0
        for i in range(len(shape) - 1):
            x0, y0 = shape[i]
            x1, y1 = shape[i + 1]
            seg_len = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if total + seg_len >= pos:
                ratio = (pos - total) / seg_len if seg_len > 0 else 0
                x = x0 + (x1 - x0) * ratio
                y = y0 + (y1 - y0) * ratio
                return (x, y)
            total += seg_len
        return shape[-1]

    def set_simulator(self, simulator: TrafficSimulator):
        """
        Set the traffic simulator instance.

        Args:
            simulator: TrafficSimulator instance
        """
        self.simulator = simulator

    def draw_intersection(self):
        """
        Draw a realistic, zoomed-in 4-way intersection with wide roads, sidewalks, grass, lane markings, and crosswalks.
        """
        # Fill background with grass
        GRASS = (34, 139, 34)
        SIDEWALK = (150, 150, 150)
        ROAD = (60, 60, 60)
        LANE = (255, 255, 255)
        YELLOW = (255, 204, 0)
        CROSSWALK = (255, 255, 255)

        screen = self.screen
        area = self.sim_area
        centerx, centery = area.centerx, area.centery
        width, height = area.width, area.height

        # Draw grass background
        screen.fill(GRASS)

        # Road and sidewalk dimensions
        road_width = 180
        sidewalk_width = 20
        crosswalk_width = 6  # thinner crosswalks
        crosswalk_length = 40  # shorter crosswalks
        intersection_size = road_width

        # Draw sidewalks (horizontal)
        pygame.draw.rect(
            screen,
            SIDEWALK,
            (0, centery - road_width // 2 - sidewalk_width, width, sidewalk_width),
        )
        pygame.draw.rect(
            screen, SIDEWALK, (0, centery + road_width // 2, width, sidewalk_width)
        )
        # Draw sidewalks (vertical)
        pygame.draw.rect(
            screen,
            SIDEWALK,
            (centerx - road_width // 2 - sidewalk_width, 0, sidewalk_width, height),
        )
        pygame.draw.rect(
            screen, SIDEWALK, (centerx + road_width // 2, 0, sidewalk_width, height)
        )

        # Draw roads (horizontal)
        pygame.draw.rect(
            screen, ROAD, (0, centery - road_width // 2, width, road_width)
        )
        # Draw roads (vertical)
        pygame.draw.rect(
            screen, ROAD, (centerx - road_width // 2, 0, road_width, height)
        )

        # Draw intersection box (to cover sidewalk corners)
        pygame.draw.rect(
            screen,
            ROAD,
            (
                centerx - road_width // 2,
                centery - road_width // 2,
                road_width,
                road_width,
            ),
        )

        # --- Crosswalks (cover full road width, slightly shorter stripes) ---
        crosswalk_stripe_count = 10
        crosswalk_stripe_length = road_width // 5  # slightly shorter than before
        crosswalk_stripe_width = 6
        crosswalk_gap = (
            road_width - crosswalk_stripe_count * crosswalk_stripe_width
        ) // (crosswalk_stripe_count - 1)
        # North crosswalk (horizontal stripes, above intersection)
        y_north = centery - road_width // 2
        for i in range(crosswalk_stripe_count):
            x = centerx - road_width // 2 + i * (crosswalk_stripe_width + crosswalk_gap)
            pygame.draw.rect(
                screen,
                CROSSWALK,
                (
                    x,
                    y_north - crosswalk_stripe_length,
                    crosswalk_stripe_width,
                    crosswalk_stripe_length,
                ),
            )
        # South crosswalk (horizontal stripes, below intersection)
        y_south = centery + road_width // 2
        for i in range(crosswalk_stripe_count):
            x = centerx - road_width // 2 + i * (crosswalk_stripe_width + crosswalk_gap)
            pygame.draw.rect(
                screen,
                CROSSWALK,
                (x, y_south, crosswalk_stripe_width, crosswalk_stripe_length),
            )
        # West crosswalk (vertical stripes, left of intersection)
        x_west = centerx - road_width // 2
        for i in range(crosswalk_stripe_count):
            y = centery - road_width // 2 + i * (crosswalk_stripe_width + crosswalk_gap)
            pygame.draw.rect(
                screen,
                CROSSWALK,
                (
                    x_west - crosswalk_stripe_length,
                    y,
                    crosswalk_stripe_length,
                    crosswalk_stripe_width,
                ),
            )
        # East crosswalk (vertical stripes, right of intersection)
        x_east = centerx + road_width // 2
        for i in range(crosswalk_stripe_count):
            y = centery - road_width // 2 + i * (crosswalk_stripe_width + crosswalk_gap)
            pygame.draw.rect(
                screen,
                CROSSWALK,
                (x_east, y, crosswalk_stripe_length, crosswalk_stripe_width),
            )

        # --- Calculate crosswalk boundaries for line endings ---
        crosswalk_offset = (
            crosswalk_stripe_length + 2
        )  # stop lines just before crosswalks
        # Horizontal (left and right) yellow lines
        pygame.draw.line(
            screen,
            YELLOW,
            (0, centery),
            (centerx - road_width // 2 - crosswalk_offset, centery),
            4,
        )
        pygame.draw.line(
            screen,
            YELLOW,
            (centerx + road_width // 2 + crosswalk_offset, centery),
            (width, centery),
            4,
        )
        # Vertical (top and bottom) yellow lines
        pygame.draw.line(
            screen,
            YELLOW,
            (centerx, 0),
            (centerx, centery - road_width // 2 - crosswalk_offset),
            4,
        )
        pygame.draw.line(
            screen,
            YELLOW,
            (centerx, centery + road_width // 2 + crosswalk_offset),
            (centerx, height),
            4,
        )

        # --- Lane Markings (no lines in center box, end before crosswalks) ---
        lane_offsets = [-45, 45]
        for offset in lane_offsets:
            # Left segment (horizontal)
            for i in range(0, centerx - road_width // 2 - crosswalk_offset - 20, 40):
                end_x = min(i + 20, centerx - road_width // 2 - crosswalk_offset)
                pygame.draw.line(
                    screen, LANE, (i, centery + offset), (end_x, centery + offset), 2
                )
            # Right segment (horizontal)
            for i in range(
                centerx + road_width // 2 + crosswalk_offset + 20, width, 40
            ):
                start_x = max(i, centerx + road_width // 2 + crosswalk_offset)
                pygame.draw.line(
                    screen,
                    LANE,
                    (start_x, centery + offset),
                    (i + 20, centery + offset),
                    2,
                )
        for offset in lane_offsets:
            # Top segment (vertical)
            for i in range(0, centery - road_width // 2 - crosswalk_offset - 20, 40):
                end_y = min(i + 20, centery - road_width // 2 - crosswalk_offset)
                pygame.draw.line(
                    screen, LANE, (centerx + offset, i), (centerx + offset, end_y), 2
                )
            # Bottom segment (vertical)
            for i in range(
                centery + road_width // 2 + crosswalk_offset + 20, height, 40
            ):
                start_y = max(i, centery + road_width // 2 + crosswalk_offset)
                pygame.draw.line(
                    screen,
                    LANE,
                    (centerx + offset, start_y),
                    (centerx + offset, i + 20),
                    2,
                )

    def draw_traffic_lights(self, traffic_light_state: Dict[str, Any]):
        """
        Draw traffic lights with current state.

        Args:
            traffic_light_state: Current traffic light state
        """
        if not traffic_light_state:
            return

        state = traffic_light_state.get("state", "GGGgrrrrGGGgrrrr")
        phase = traffic_light_state.get("phase", 0)

        # Draw traffic lights for each direction
        directions = ["north", "south", "east", "west"]

        for i, direction in enumerate(directions):
            pos = self.traffic_light_positions[direction]
            x, y = pos[0] + self.sim_area.x, pos[1] + self.sim_area.y

            # Determine light color based on state and direction
            if direction in ["north", "south"]:
                if phase == 0:  # North-South green
                    color = self.GREEN
                elif phase == 1:  # Yellow
                    color = self.YELLOW
                else:  # Red
                    color = self.RED
            else:  # East-West
                if phase == 2:  # East-West green
                    color = self.GREEN
                elif phase == 3:  # Yellow
                    color = self.YELLOW
                else:  # Red
                    color = self.RED

            # Draw traffic light
            pygame.draw.circle(self.screen, color, (x, y), 15)
            pygame.draw.circle(self.screen, self.BLACK, (x, y), 15, 2)

    def sumo_to_screen(self, x, y):
        # Use parsed netOffset and convBoundary for accurate mapping
        x -= self.net_offset_x
        y -= self.net_offset_y
        # Calculate scale based on actual network bounds
        sumo_width = self.sumo_x_max - self.sumo_x_min
        sumo_height = self.sumo_y_max - self.sumo_y_min
        scale_x = self.sim_area.width / sumo_width
        scale_y = self.sim_area.height / sumo_height
        # Use the smaller scale to maintain aspect ratio
        scale = min(scale_x, scale_y)
        zoom_factor = 1.7  # <--- Increase this value to zoom in more or less
        scale *= zoom_factor
        # Center the network in the simulation area
        center_x = self.sim_area.centerx
        center_y = self.sim_area.centery
        screen_x = int(center_x + x * scale)
        screen_y = int(center_y - y * scale)  # Y axis is inverted in pygame
        return screen_x, screen_y

    def get_vehicle_rotation(self, vehicle_info):
        angle = vehicle_info.get("angle", None)
        if angle is not None:
            # Rotate by -angle to match SUMO's heading with up-facing images
            return -angle
        # Fallback to edge-based logic if angle is missing
        edge = vehicle_info.get("edge", "")
        if "north" in edge and "center" in edge:
            if edge.startswith("north"):
                return 0
            else:
                return 180
        elif "south" in edge and "center" in edge:
            if edge.startswith("south"):
                return 180
            else:
                return 0
        elif "east" in edge and "center" in edge:
            if edge.startswith("east"):
                return -90
            else:
                return 90
        elif "west" in edge and "center" in edge:
            if edge.startswith("west"):
                return 90
            else:
                return -90
        return 0

    def draw_vehicles(self, vehicles: Dict[str, Any]):
        """
        Draw vehicles on the intersection, aligned to their lanes.
        Also draws debug info: lane centerlines, vehicle positions, and logs lane_id/lane_index.
        """
        # --- DEBUG: Draw lane centerlines ---
        for lane_id, shape in self.lane_shapes.items():
            color = (0, 200, 255)  # Cyan for lane centerlines
            for i in range(len(shape) - 1):
                x1, y1 = self.sumo_to_screen(*shape[i])
                x2, y2 = self.sumo_to_screen(*shape[i + 1])
                pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), 2)

        # Per-direction lane width (side-by-side gap)
        lane_widths = {
            "north": 40,  # px
            "south": 40,  # px
            "east": 40,  # px
            "west": 60,  # px (example: wider for west)
        }
        # Per-direction additional offset (default 0, adjust as needed)
        direction_offsets = {
            "north": 0,
            "south": 0,
            "east": 0,
            "west": 45,  # px, for example, to move west vehicles further right
        }
        num_lanes = 3  # adjust if your SUMO net uses a different number
        for vehicle_id, vehicle_info in vehicles.items():
            vehicle_type = vehicle_info.get("type", "car")
            edge = vehicle_info.get("edge", "")
            lane_id = vehicle_info.get("lane", "")
            pos_on_lane = vehicle_info.get("position", (0, 0))
            lane_pos = vehicle_info.get("lanePosition", None)
            # Determine direction from edge
            if "north" in edge:
                direction = "north"
            elif "south" in edge:
                direction = "south"
            elif "east" in edge:
                direction = "east"
            elif "west" in edge:
                direction = "west"
            else:
                direction = "unknown"
            # Improved direction inference: fallback to lane_id if edge is not helpful
            if direction == "unknown":
                if "north" in lane_id:
                    direction = "north"
                elif "south" in lane_id:
                    direction = "south"
                elif "east" in lane_id:
                    direction = "east"
                elif "west" in lane_id:
                    direction = "west"
            # If still unknown, print a warning and skip offsetting, but suppress warning for connector lanes (lane_id starting with ':')
            if direction == "unknown":
                if not lane_id.startswith(":"):
                    print(
                        f"[WARN] Could not determine direction for vehicle {vehicle_id} (lane_id={lane_id}). Skipping lane offset."
                    )
                lane_width = 0
                dir_offset = 0
            else:
                lane_width = lane_widths.get(direction, 40)
                dir_offset = direction_offsets.get(direction, 0)
            lane_index = 1
            # Improved lane index extraction for various lane_id formats
            lane_index_match = re.search(r"_(\d+)$", lane_id)
            if lane_index_match:
                lane_index = int(lane_index_match.group(1))
            else:
                # Try to extract from patterns like ':center_20_0' or ':center_10_0'
                alt_match = re.search(r"_(\d+)_?(\d+)?$", lane_id)
                if alt_match:
                    # Use the last group that is not None
                    if alt_match.group(2):
                        lane_index = int(alt_match.group(2))
                    else:
                        lane_index = int(alt_match.group(1))
                else:
                    print(
                        f"[WARN] Could not extract lane_index from lane_id='{lane_id}' for vehicle {vehicle_id}. Defaulting to 1."
                    )
                    lane_index = 1
            # --- DEBUG: Print lane_id and lane_index ---
            print(
                f"Vehicle {vehicle_id}: lane_id={lane_id}, lane_index={lane_index}, direction={direction}"
            )
            offset = (lane_index - (num_lanes - 1) / 2) * lane_width
            # --- ADJUST VEHICLE POSITION TO MATCH CYAN LINES ---
            # For all vehicles, use the lane shape (cyan line) as the true center for vehicle placement.
            # Only apply offset for approach lanes (not for connector lanes, i.e., lane_id starting with ':').
            if lane_id in self.lane_shapes and lane_pos is not None:
                shape = self.lane_shapes[lane_id]
                x, y = self.interpolate_along_shape(shape, lane_pos)
                screen_x, screen_y = self.sumo_to_screen(x, y)
            else:
                position = vehicle_info.get("position", (0, 0))
                screen_x, screen_y = self.sumo_to_screen(position[0], position[1])
            # Only apply offset for approach lanes (not for connector lanes)
            if not lane_id.startswith(":"):
                if direction in ["north", "south"]:
                    screen_x += offset + dir_offset
                elif direction in ["east", "west"]:
                    screen_y += offset + dir_offset
            # --- DEBUG: Draw vehicle position as a small circle ---
            pygame.draw.circle(
                self.screen, (255, 0, 0), (int(screen_x), int(screen_y)), 6
            )
            # Consistent car image assignment
            if vehicle_type == "car":
                idx = abs(hash(vehicle_id)) % len(self.car_pngs)
                img = self.car_pngs[idx]
            elif vehicle_type == "bus":
                img = self.vehicle_images["bus"]
            elif vehicle_type == "bike":
                img = self.vehicle_images["bike"]
            elif vehicle_type == "emergency":
                img = self.vehicle_images["emergency"]
            else:
                idx = abs(hash(vehicle_id)) % len(self.car_pngs)
                img = self.car_pngs[idx]
            # Rotate image based on direction
            angle = self.get_vehicle_rotation(vehicle_info)
            img_rot = pygame.transform.rotate(img, angle)
            rect = img_rot.get_rect(center=(int(screen_x), int(screen_y)))
            self.screen.blit(img_rot, rect)
            # Draw vehicle ID for debugging
            if vehicle_type == "emergency":
                text = self.font_small.render(vehicle_id[:3], True, self.WHITE)
                self.screen.blit(text, (screen_x + 10, screen_y - 10))

    # def draw_info_panel(
    #     self, metrics: Dict[str, Any], optimization_status: Dict[str, Any]
    # ):
    #     """
    #     Draw information panel with metrics and optimization data.
    #
    #     Args:
    #         metrics: Traffic flow metrics
    #         optimization_status: Current optimization status
    #     """
    #     # Background
    #     pygame.draw.rect(self.screen, self.WHITE, self.info_area)
    #     pygame.draw.rect(self.screen, self.BLACK, self.info_area, 2)
    #
    #     y_offset = 70
    #
    #     # Title
    #     title = self.font_large.render("AI Traffic Management", True, self.BLACK)
    #     self.screen.blit(title, (self.info_area.x + 10, 60))
    #
    #     # Simulation time
    #     sim_time = metrics.get("simulation_duration", 0)
    #     time_text = self.font_medium.render(f"Time: {sim_time:.1f}s", True, self.BLACK)
    #     self.screen.blit(time_text, (self.info_area.x + 10, y_offset))
    #     y_offset += 40
    #
    #     # Total vehicles
    #     total_vehicles = metrics.get("total_vehicles", 0)
    #     vehicles_text = self.font_medium.render(
    #         f"Vehicles: {total_vehicles}", True, self.BLACK
    #     )
    #     self.screen.blit(vehicles_text, (self.info_area.x + 10, y_offset))
    #     y_offset += 40
    #
    #     # Emergency vehicles
    #     emergency_vehicles = metrics.get("emergency_vehicles", 0)
    #     emergency_text = self.font_medium.render(
    #         f"Emergency: {emergency_vehicles}", True, self.RED
    #     )
    #     self.screen.blit(emergency_text, (self.info_area.x + 10, y_offset))
    #     y_offset += 40
    #
    #     # Efficiency score
    #     efficiency = metrics.get("efficiency_score", 0)
    #     efficiency_text = self.font_medium.render(
    #         f"Efficiency: {efficiency:.1f}%", True, self.BLACK
    #     )
    #     self.screen.blit(efficiency_text, (self.info_area.x + 10, y_offset))
    #     y_offset += 40
    #
    #     # Average waiting time
    #     avg_wait = metrics.get("average_waiting_time", 0)
    #     wait_text = self.font_medium.render(
    #         f"Avg Wait: {avg_wait:.1f}s", True, self.BLACK
    #     )
    #     self.screen.blit(wait_text, (self.info_area.x + 10, y_offset))
    #     y_offset += 60
    #
    #     # Density information
    #     densities = metrics.get("densities", {})
    #     if densities:
    #         density_title = self.font_medium.render(
    #             "Density Analysis:", True, self.BLACK
    #         )
    #         self.screen.blit(density_title, (self.info_area.x + 10, y_offset))
    #         y_offset += 30
    #
    #         for approach, density in densities.items():
    #             # Color code based on density
    #             if density < 0.1:
    #                 color = self.GREEN
    #             elif density < 0.3:
    #                 color = self.YELLOW
    #             elif density < 0.5:
    #                 color = self.ORANGE
    #             else:
    #                 color = self.RED
    #
    #             density_text = self.font_small.render(
    #                 f"{approach}: {density:.3f}", True, color
    #             )
    #             self.screen.blit(density_text, (self.info_area.x + 20, y_offset))
    #             y_offset += 25
    #
    #     y_offset += 20
    #
    #     # Congestion levels
    #     congestion_levels = metrics.get("congestion_levels", {})
    #     if congestion_levels:
    #         congestion_title = self.font_medium.render(
    #             "Congestion Levels:", True, self.BLACK
    #         )
    #         self.screen.blit(congestion_title, (self.info_area.x + 10, y_offset))
    #         y_offset += 30
    #
    #         for approach, level in congestion_levels.items():
    #             if level == "Low":
    #                 color = self.GREEN
    #             elif level == "Medium":
    #                 color = self.YELLOW
    #             elif level == "High":
    #                 color = self.ORANGE
    #             else:
    #                 color = self.RED
    #
    #             level_text = self.font_small.render(f"{approach}: {level}", True, color)
    #             self.screen.blit(level_text, (self.info_area.x + 20, y_offset))
    #             y_offset += 25
    #
    #     y_offset += 20
    #
    #     # Current phase
    #     current_phase = optimization_status.get("current_phase", 0)
    #     phase_text = self.font_medium.render(
    #         f"Phase: {current_phase}", True, self.BLACK
    #     )
    #     self.screen.blit(phase_text, (self.info_area.x + 10, y_offset))
    #     y_offset += 40
    #
    #     # Optimization status
    #     optimizations = optimization_status.get("recent_optimizations", 0)
    #     opt_text = self.font_medium.render(
    #         f"Optimizations: {optimizations}", True, self.BLACK
    #     )
    #     self.screen.blit(opt_text, (self.info_area.x + 10, y_offset))

    def draw_controls(self):
        """
        Draw control instructions.
        """
        controls = [
            "Controls:",
            "SPACE - Step simulation",
            "R - Reset simulation",
            "Q - Quit",
            "S - Start/Stop auto-step",
        ]

        y_offset = self.height - 120

        for i, control in enumerate(controls):
            color = self.BLACK if i == 0 else self.GRAY
            text = self.font_small.render(control, True, color)
            self.screen.blit(text, (10, y_offset + i * 20))

    def handle_events(self) -> bool:
        """
        Handle pygame events.

        Returns:
            bool: True if should continue running
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False
                elif event.key == pygame.K_r and self.simulator:
                    self.simulator.reset_simulation()
                elif event.key == pygame.K_SPACE and self.simulator:
                    self.simulator.step_simulation()
                elif event.key == pygame.K_s:
                    # Toggle auto-step mode
                    pass

        return True

    def update_display(self):
        """
        Update the display with current simulation data.
        """
        if not self.simulator:
            return

        # Clear screen
        self.screen.fill(self.WHITE)

        # Draw intersection
        self.draw_intersection()

        # Get simulation data
        traffic_light_state = self.simulator.get_traffic_light_state()
        vehicles = self.simulator.get_vehicle_positions()
        metrics = self.simulator.get_performance_metrics()
        optimization_status = self.simulator.get_simulation_status()

        # Draw traffic lights
        self.draw_traffic_lights(traffic_light_state)

        # Draw vehicles
        self.draw_vehicles(vehicles)

        # Draw info panel
        # if metrics:
        #     self.draw_info_panel(
        #         metrics.get("current_metrics", {}), optimization_status
        #     )

        # Draw controls
        self.draw_controls()

        # Update display
        pygame.display.flip()

    def run(self, auto_step: bool = False, step_delay: float = 0.1):
        """
        Run the visualizer main loop.

        Args:
            auto_step: Whether to automatically step the simulation
            step_delay: Delay between auto-steps in seconds
        """
        self.running = True

        while self.running:
            # Handle events
            self.running = self.handle_events()

            # Auto-step if enabled
            if auto_step and self.simulator:
                self.simulator.step_simulation()
                pygame.time.wait(int(step_delay * 1000))

            # Update display
            self.update_display()

            # Control frame rate
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def close(self):
        """
        Close the visualizer.
        """
        self.running = False
        pygame.quit()
