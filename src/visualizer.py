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
        self.SIDEWALK = (150, 150, 150)
        self.ROAD = (60, 60, 60)
        self.LANE = (255, 255, 255)
        self.CROSSWALK = (255, 255, 255)

        # Load the grass texture
        try:
            self.grass_texture = pygame.image.load(os.path.join("images", "grass.png"))
        except pygame.error:
            print(
                "Warning: 'grass.png' not found. Using solid green color as fallback."
            )
            self.grass_texture = None

        # Fonts
        self.font_small = pygame.font.Font(None, 24)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_large = pygame.font.Font(None, 48)

        # Simulation area (centered, fills window)
        self.sim_area = pygame.Rect(0, 0, self.width, self.height)

        # SUMO network bounds and offset
        self.sumo_x_min = 0.0
        self.sumo_x_max = 200.0
        self.sumo_y_min = 0.0
        self.sumo_y_max = 200.0
        self.net_offset_x = 100.0
        self.net_offset_y = 100.0

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
                print(
                    f"[WARN] Could not parse network bounds from {net_xml}, using defaults"
                )
        except Exception as e:
            print(f"[WARN] Could not parse network bounds from {net_xml}: {e}")

        self.car_pngs = [
            pygame.transform.scale(
                pygame.image.load(os.path.join("images", "Audi.png")), (24, 48)
            ),
            pygame.transform.scale(
                pygame.image.load(os.path.join("images", "bluecar.png")), (24, 48)
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
                pygame.image.load(os.path.join("images", "bus2.png")), (30, 60)
            ),
            "bike": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "bike1.png")), (14, 28)
            ),
            "emergency": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "Ambulance.png")), (24, 48)
            ),
        }

        # Load and rotate traffic light images
        self.traffic_light_images = {
            "red": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "red.png")), (30, 55)
            ),
            "yellow": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "yellow.png")), (30, 55)
            ),
            "green": pygame.transform.scale(
                pygame.image.load(os.path.join("images", "green.png")), (30, 55)
            ),
        }
        self.traffic_light_images_rotated = {
            "red": pygame.transform.rotate(self.traffic_light_images["red"], 90),
            "yellow": pygame.transform.rotate(self.traffic_light_images["yellow"], 90),
            "green": pygame.transform.rotate(self.traffic_light_images["green"], 90),
        }

        # Adjusted traffic light positions to be on the sidewalks
        self.traffic_light_positions = {
            "north": (108, 110.40),  # Top-right corner
            "south": (92, 89.60),  # Bottom-left corner
            "east": (110.40, 92),  # Bottom-right corner
            "west": (89.60, 108),  # Top-left corner
        }

        self.simulator = None
        self.clock = pygame.time.Clock()
        self.running = False
        self.auto_step = False
        self.lane_shapes = self.load_lane_shapes("config/intersection.net.xml")

    def load_lane_shapes(self, xml_path):
        lane_shapes = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for edge in root.findall(".//edge"):
                edge_id = edge.attrib.get("id", "")
                if edge_id.startswith(":") or not edge_id.startswith(":"):
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
        self.simulator = simulator

    def sumo_to_screen(self, x, y):
        x -= self.net_offset_x
        y -= self.net_offset_y
        sumo_width = self.sumo_x_max - self.sumo_x_min
        sumo_height = self.sumo_y_max - self.sumo_y_min
        scale_x = self.sim_area.width / sumo_width
        scale_y = self.sim_area.height / sumo_height
        scale = min(scale_x, scale_y)
        zoom_factor = 2.5
        scale *= zoom_factor
        center_x = self.sim_area.centerx
        center_y = self.sim_area.centery
        screen_x = int(center_x + x * scale)
        screen_y = int(center_y - y * scale)
        return screen_x, screen_y

    def draw_intersection(self):
        if self.grass_texture:
            for x in range(0, self.width, self.grass_texture.get_width()):
                for y in range(0, self.height, self.grass_texture.get_height()):
                    self.screen.blit(self.grass_texture, (x, y))
        else:
            self.screen.fill((34, 139, 34))

        road_width_sumo = 12.8
        sidewalk_width_sumo = 2.0
        crosswalk_length_sumo = 3.0
        lane_divider_offset_sumo = 3.2

        center_screen = self.sumo_to_screen(100, 100)
        centerx, centery = center_screen
        road_width_px = (
            self.sumo_to_screen(road_width_sumo, 0)[0] - self.sumo_to_screen(0, 0)[0]
        )
        sidewalk_width_px = (
            self.sumo_to_screen(sidewalk_width_sumo, 0)[0]
            - self.sumo_to_screen(0, 0)[0]
        )
        crosswalk_length_px = (
            self.sumo_to_screen(crosswalk_length_sumo, 0)[0]
            - self.sumo_to_screen(0, 0)[0]
        )

        lane_offset_sumo_1 = 3.2
        lane_offset_px_1 = (
            self.sumo_to_screen(lane_offset_sumo_1, 0)[0] - self.sumo_to_screen(0, 0)[0]
        )

        pygame.draw.rect(
            self.screen,
            self.SIDEWALK,
            (
                0,
                centery - road_width_px / 2 - sidewalk_width_px,
                self.width,
                sidewalk_width_px,
            ),
        )
        pygame.draw.rect(
            self.screen,
            self.SIDEWALK,
            (0, centery + road_width_px / 2, self.width, sidewalk_width_px),
        )
        pygame.draw.rect(
            self.screen,
            self.SIDEWALK,
            (
                centerx - road_width_px / 2 - sidewalk_width_px,
                0,
                sidewalk_width_px,
                self.height,
            ),
        )
        pygame.draw.rect(
            self.screen,
            self.SIDEWALK,
            (centerx + road_width_px / 2, 0, sidewalk_width_px, self.height),
        )
        pygame.draw.rect(
            self.screen,
            self.ROAD,
            (0, centery - road_width_px / 2, self.width, road_width_px),
        )
        pygame.draw.rect(
            self.screen,
            self.ROAD,
            (centerx - road_width_px / 2, 0, road_width_px, self.height),
        )

        intersection_size_px = road_width_px
        pygame.draw.rect(
            self.screen,
            self.ROAD,
            (
                centerx - intersection_size_px / 2,
                centery - intersection_size_px / 2,
                intersection_size_px,
                intersection_size_px,
            ),
        )

        pygame.draw.line(
            self.screen,
            self.YELLOW,
            (0, centery),
            (centerx - intersection_size_px / 2, centery),
            4,
        )
        pygame.draw.line(
            self.screen,
            self.YELLOW,
            (centerx + intersection_size_px / 2, centery),
            (self.width, centery),
            4,
        )
        pygame.draw.line(
            self.screen,
            self.YELLOW,
            (centerx, 0),
            (centerx, centery - intersection_size_px / 2),
            4,
        )
        pygame.draw.line(
            self.screen,
            self.YELLOW,
            (centerx, centery + intersection_size_px / 2),
            (centerx, self.height),
            4,
        )

        y_north_stop = centery - road_width_px / 2
        y_south_stop = centery + road_width_px / 2
        x_west_stop = centerx - road_width_px / 2
        x_east_stop = centerx + road_width_px / 2
        crosswalk_stripe_width_px = 6
        crosswalk_gap_px = (road_width_px - 10 * crosswalk_stripe_width_px) // 9
        for i in range(10):
            x_pos = (
                centerx
                - road_width_px / 2
                + i * (crosswalk_stripe_width_px + crosswalk_gap_px)
            )
            pygame.draw.rect(
                self.screen,
                self.CROSSWALK,
                (
                    x_pos,
                    y_north_stop - crosswalk_length_px,
                    crosswalk_stripe_width_px,
                    crosswalk_length_px,
                ),
            )
            pygame.draw.rect(
                self.screen,
                self.CROSSWALK,
                (x_pos, y_south_stop, crosswalk_stripe_width_px, crosswalk_length_px),
            )
            y_pos = (
                centery
                - road_width_px / 2
                + i * (crosswalk_stripe_width_px + crosswalk_gap_px)
            )
            pygame.draw.rect(
                self.screen,
                self.CROSSWALK,
                (
                    x_west_stop - crosswalk_length_px,
                    y_pos,
                    crosswalk_length_px,
                    crosswalk_stripe_width_px,
                ),
            )
            pygame.draw.rect(
                self.screen,
                self.CROSSWALK,
                (x_east_stop, y_pos, crosswalk_length_px, crosswalk_stripe_width_px),
            )

        dash_length = 20
        gap_length = 20
        for i in range(
            0, int(centerx - intersection_size_px / 2), dash_length + gap_length
        ):
            pygame.draw.line(
                self.screen,
                self.LANE,
                (i, centery - lane_offset_px_1),
                (i + dash_length, centery - lane_offset_px_1),
                2,
            )
            pygame.draw.line(
                self.screen,
                self.LANE,
                (i, centery + lane_offset_px_1),
                (i + dash_length, centery + lane_offset_px_1),
                2,
            )

        for i in range(
            int(centerx + intersection_size_px / 2),
            self.width,
            dash_length + gap_length,
        ):
            pygame.draw.line(
                self.screen,
                self.LANE,
                (i, centery - lane_offset_px_1),
                (i + dash_length, centery - lane_offset_px_1),
                2,
            )
            pygame.draw.line(
                self.screen,
                self.LANE,
                (i, centery + lane_offset_px_1),
                (i + dash_length, centery + lane_offset_px_1),
                2,
            )

        for i in range(
            0, int(centery - intersection_size_px / 2), dash_length + gap_length
        ):
            pygame.draw.line(
                self.screen,
                self.LANE,
                (centerx - lane_offset_px_1, i),
                (centerx - lane_offset_px_1, i + dash_length),
                2,
            )
            pygame.draw.line(
                self.screen,
                self.LANE,
                (centerx + lane_offset_px_1, i),
                (centerx + lane_offset_px_1, i + dash_length),
                2,
            )

        for i in range(
            int(centery + intersection_size_px / 2),
            self.height,
            dash_length + gap_length,
        ):
            pygame.draw.line(
                self.screen,
                self.LANE,
                (centerx - lane_offset_px_1, i),
                (centerx - lane_offset_px_1, i + dash_length),
                2,
            )
            pygame.draw.line(
                self.screen,
                self.LANE,
                (centerx + lane_offset_px_1, i),
                (centerx + lane_offset_px_1, i + dash_length),
                2,
            )

    def draw_traffic_lights(self, traffic_light_state: Dict[str, Any]):
        if not traffic_light_state:
            return

        phase = traffic_light_state.get("phase", 0)
        time_in_phase = traffic_light_state.get("time_in_phase", 0)
        duration = traffic_light_state.get("duration", 0)

        for direction, pos_sumo in self.traffic_light_positions.items():
            x, y = self.sumo_to_screen(pos_sumo[0], pos_sumo[1])

            color_key = "red"
            is_green = False

            # --- THIS IS THE FIX ---
            # Use rotated images for east and west directions
            image_set = self.traffic_light_images
            if direction in ["east", "west"]:
                image_set = self.traffic_light_images_rotated

            if direction in ["north", "south"]:
                if phase == 0:
                    color_key = "green"
                    is_green = True
                elif phase == 1:
                    color_key = "yellow"
            else:
                if phase == 2:
                    color_key = "green"
                    is_green = True
                elif phase == 3:
                    color_key = "yellow"

            img = image_set[color_key]
            rect = img.get_rect(center=(x, y))
            self.screen.blit(img, rect)

            if is_green:
                remaining_time = duration - time_in_phase
                timer_text = self.font_medium.render(
                    f"{max(0, int(remaining_time))}", True, self.WHITE
                )

                if direction == "north":
                    timer_rect = timer_text.get_rect(center=(x, y + 35))
                elif direction == "south":
                    timer_rect = timer_text.get_rect(center=(x, y - 35))
                elif direction == "east":
                    timer_rect = timer_text.get_rect(center=(x - 35, y))
                else:
                    timer_rect = timer_text.get_rect(center=(x + 35, y))

                self.screen.blit(timer_text, timer_rect)

    def get_vehicle_rotation(self, vehicle_info):
        angle = vehicle_info.get("angle", None)
        if angle is not None:
            return -angle

        edge = vehicle_info.get("edge", "")
        if "north2center" in edge:
            return 0
        elif "south2center" in edge:
            return 180
        elif "east2center" in edge:
            return -90
        elif "west2center" in edge:
            return 90

        return 0

    def draw_vehicles(self, vehicles: Dict[str, Any]):
        for vehicle_id, vehicle_info in vehicles.items():
            vehicle_type = vehicle_info.get("type", "car")
            lane_id = vehicle_info.get("lane", "")
            lane_pos = vehicle_info.get("lanePosition", 0.0)

            if lane_id in self.lane_shapes and lane_pos is not None:
                shape = self.lane_shapes[lane_id]
                x, y = self.interpolate_along_shape(shape, lane_pos)
            else:
                x, y = vehicle_info.get("position", (0, 0))

            screen_x, screen_y = self.sumo_to_screen(x, y)

            if vehicle_type == "car":
                idx = abs(hash(vehicle_id)) % len(self.car_pngs)
                img = self.car_pngs[idx]
            elif vehicle_type in self.vehicle_images:
                img = self.vehicle_images[vehicle_type]
            else:
                img = self.car_pngs[0]

            angle = self.get_vehicle_rotation(vehicle_info)
            img_rot = pygame.transform.rotate(img, angle)
            rect = img_rot.get_rect(center=(int(screen_x), int(screen_y)))
            self.screen.blit(img_rot, rect)

    def draw_ui_feedback(self):
        if not self.simulator:
            return

        total_vehicles_passed = self.simulator.get_total_vehicles_passed()
        text = self.font_medium.render(
            f"Vehicles Passed: {total_vehicles_passed}", True, self.WHITE
        )
        self.screen.blit(text, (10, 10))

    def draw_controls(self):
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
                    self.auto_step = not self.auto_step

        return True

    def update_display(self):
        if not self.simulator:
            return

        self.draw_intersection()

        traffic_light_state = self.simulator.get_traffic_light_state()
        vehicles = self.simulator.get_vehicle_positions()

        self.draw_traffic_lights(traffic_light_state)
        self.draw_vehicles(vehicles)

        self.draw_controls()
        self.draw_ui_feedback()

        pygame.display.flip()

    def run(self, auto_step: bool = False, step_delay: float = 0.1):
        self.running = True
        self.auto_step = auto_step

        while self.running:
            self.running = self.handle_events()

            if self.auto_step and self.simulator:
                self.simulator.step_simulation()
                pygame.time.wait(int(step_delay * 1000))

            self.update_display()

            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def close(self):
        self.running = False
        pygame.quit()
