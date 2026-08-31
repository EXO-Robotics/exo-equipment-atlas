#!/usr/bin/env python3
"""Deterministic machine-local Komatsu PC210LC-11 structural-study builder.

The public geometry is an independently authored, neutral reconstruction in
metres.  Only facts explicitly named in design.json constrain it; no Komatsu
CAD, drawing geometry, logo, texture, or protected livery is imported.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared_generator():
    spec = importlib.util.spec_from_file_location("exo_fleet_builder", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared fleet generator: {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared_generator()


class KomatsuPC210LC11Builder(shared.FleetBuilder):
    """Selected 5.7 m boom / 2.925 m arm / 700 mm-shoe candidate."""

    BOOM_LENGTH = 5.700
    ARM_LENGTH = 2.925
    SHOE_WIDTH = 0.700
    TRACK_LENGTH = 4.450
    TRACK_GAUGE = 2.380
    BUCKET_WIDTH = 0.914
    BOOM_STROKE = 1.334
    ARM_STROKE = 1.490
    BUCKET_STROKE = 1.105

    SWING = shared.Vector((-1.25, 1.02, 0.0))
    BOOM_PIVOT_POINT = shared.Vector((-1.05, 1.50, 0.0))
    BOOM_VECTOR = shared.Vector((math.sqrt(BOOM_LENGTH ** 2 - 1.35 ** 2), 1.35, 0.0))
    STICK_VECTOR = shared.Vector((-1.30, -math.sqrt(ARM_LENGTH ** 2 - 1.30 ** 2), 0.0))
    STICK_PIVOT_POINT = BOOM_PIVOT_POINT + BOOM_VECTOR
    BUCKET_PIVOT_POINT = STICK_PIVOT_POINT + STICK_VECTOR
    TOOTH_VECTOR = shared.Vector((
        9.705 / 2.0 - BUCKET_PIVOT_POINT.x,
        0.090 - BUCKET_PIVOT_POINT.y,
        0.0,
    ))

    REQUIRED_PARENTS = {
        "Track_L_ROOT": "Running_Gear_ROOT",
        "Track_R_ROOT": "Running_Gear_ROOT",
        "Upper_Swing_Pivot": "Machine_Root",
        "Upper_ROOT": "Upper_Swing_Pivot",
        "Hydraulics_ROOT": "Upper_ROOT",
        "Boom_Pivot": "Upper_ROOT",
        "Boom_ROOT": "Boom_Pivot",
        "Stick_Pivot": "Boom_ROOT",
        "Stick_ROOT": "Stick_Pivot",
        "Bucket_Pivot": "Stick_ROOT",
        "Bucket_ROOT": "Bucket_Pivot",
        "Boom_Cylinder_L_ROOT": "Upper_ROOT",
        "Boom_Cylinder_L_Rod_ROOT": "Boom_ROOT",
        "Boom_Cylinder_R_ROOT": "Upper_ROOT",
        "Boom_Cylinder_R_Rod_ROOT": "Boom_ROOT",
        "Arm_Crowd_Actuator_ROOT": "Boom_ROOT",
        "Arm_Crowd_Rod_ROOT": "Stick_ROOT",
        "Bucket_H_Link_ROOT": "Stick_ROOT",
        "Bucket_Dogbone_ROOT": "Bucket_H_Link_ROOT",
        "Bucket_Curl_Actuator_ROOT": "Stick_ROOT",
        "Bucket_Curl_Rod_ROOT": "Bucket_H_Link_ROOT",
        "Boom_Cylinder_L_Barrel": "Boom_Cylinder_L_ROOT",
        "Boom_Cylinder_L_Rod": "Boom_Cylinder_L_Rod_ROOT",
        "Boom_Cylinder_R_Barrel": "Boom_Cylinder_R_ROOT",
        "Boom_Cylinder_R_Rod": "Boom_Cylinder_R_Rod_ROOT",
        "Arm_Crowd_Cylinder_Barrel": "Arm_Crowd_Actuator_ROOT",
        "Arm_Crowd_Cylinder_Rod": "Arm_Crowd_Rod_ROOT",
        "Bucket_Curl_Cylinder_Barrel": "Bucket_Curl_Actuator_ROOT",
        "Bucket_Curl_Cylinder_Rod": "Bucket_Curl_Rod_ROOT",
        "Bucket_H_Link_L": "Bucket_H_Link_ROOT",
        "Bucket_H_Link_R": "Bucket_H_Link_ROOT",
        "Bucket_Dogbone_L": "Bucket_Dogbone_ROOT",
        "Bucket_Dogbone_R": "Bucket_Dogbone_ROOT",
        "Bucket_Linkage_Ear_L": "Bucket_ROOT",
        "Bucket_Linkage_Ear_R": "Bucket_ROOT",
    }

    def write_machine_wrapper(self):
        """Do not overwrite the audited local subclass with a generic wrapper."""

    def reset_scene(self):
        """Use deterministic Workbench review renders while retaining PBR GLB materials."""
        super().reset_scene()
        scene = shared.bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.render_aa = "FXAA"
        shading = scene.display.shading
        # Flat lighting keeps the neutral palette legible in every headless
        # review frame.  Disable screen-space effects because their sampling
        # changes PNG bytes between otherwise identical headless rebuilds.
        shading.light = "FLAT"
        shading.color_type = "MATERIAL"
        shading.show_shadows = False
        shading.show_cavity = False
        shading.show_specular_highlight = False
        shading.background_type = "VIEWPORT"
        shading.background_color = (0.050, 0.065, 0.085)

    @staticmethod
    def strip_png_text_metadata(path):
        """Remove Blender's wall-clock PNG text chunks after each review render."""
        payload = path.read_bytes()
        signature = b"\x89PNG\r\n\x1a\n"
        if not payload.startswith(signature):
            raise RuntimeError(f"Review render is not a PNG: {path}")
        normalized = bytearray(signature)
        cursor = len(signature)
        while cursor < len(payload):
            length = int.from_bytes(payload[cursor:cursor + 4], "big")
            chunk_end = cursor + 12 + length
            if chunk_end > len(payload):
                raise RuntimeError(f"Truncated PNG chunk in {path}")
            chunk_type = payload[cursor + 4:cursor + 8]
            if chunk_type != b"tEXt":
                normalized.extend(payload[cursor:chunk_end])
            cursor = chunk_end
        path.write_bytes(normalized)

    def render_views(self):
        self.setup_render_scene()
        camera = shared.bpy.data.objects["Review_Camera"]
        span = max(self.length, self.width, self.height)
        full_center = shared.Vector((0.0, self.height * 0.46, 0.0))
        linkage_center = shared.Vector((3.86, 0.68, 0.0))
        views = [
            ("operator-side", (0.0, self.height * 0.62, -span * 1.55),
             full_center, max(self.length, self.carrier_width, self.height) * 1.08),
            ("front-three-quarter", (span * 1.10, self.height * 0.88, -span * 1.02),
             full_center, span * 1.18),
            ("rear-three-quarter", (-span * 1.12, self.height * 0.82, span * 0.96),
             full_center, max(self.length, self.carrier_width, self.height) * 1.18),
            ("elevated-technical", (span * 0.65, span * 1.45, -span * 0.95),
             full_center, span * 1.30),
            # A real mechanism inspection frame: the bucket curl cylinder,
            # H-link, paired dogbones, ears and pins fill the image.
            ("articulation-detail", (6.85, 2.60, -4.25),
             linkage_center, 2.55),
            ("right-side", (0.0, self.height * 0.62, span * 1.55),
             full_center, max(self.length, self.carrier_width, self.height) * 1.08),
        ]
        paths = []
        for label, location, target, ortho_scale in views:
            camera.location = location
            self.point_at(camera, target)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            shared.bpy.context.scene.render.filepath = str(path)
            shared.bpy.ops.render.render(write_still=True)
            paths.append(path)
        for path in paths:
            self.strip_png_text_metadata(path)
        return paths

    def required_semantics(self):
        return [
            *super().required_semantics(),
            "Boom_Cylinder_L_ROOT", "Boom_Cylinder_L_Rod_ROOT",
            "Boom_Cylinder_R_ROOT", "Boom_Cylinder_R_Rod_ROOT",
            "Arm_Crowd_Actuator_ROOT", "Arm_Crowd_Rod_ROOT",
            "Bucket_Curl_Actuator_ROOT", "Bucket_Curl_Rod_ROOT",
            "Bucket_H_Link_ROOT", "Bucket_Dogbone_ROOT",
        ]

    @staticmethod
    def rot2(vector, angle):
        cosine, sine = math.cos(angle), math.sin(angle)
        return shared.Vector((
            vector.x * cosine - vector.y * sine,
            vector.x * sine + vector.y * cosine,
            vector.z,
        ))

    @staticmethod
    def world_location(obj):
        return obj.matrix_world.translation.copy()

    def to_local(self, parent, point):
        shared.bpy.context.view_layer.update()
        return parent.matrix_world.inverted() @ shared.Vector(point)

    def object_bounds(self, obj):
        minimum = [math.inf, math.inf, math.inf]
        maximum = [-math.inf, -math.inf, -math.inf]
        for vertex in obj.data.vertices:
            point = obj.matrix_world @ vertex.co
            for axis in range(3):
                minimum[axis] = min(minimum[axis], point[axis])
                maximum[axis] = max(maximum[axis], point[axis])
        return {"min": minimum, "max": maximum,
                "size": [maximum[i] - minimum[i] for i in range(3)]}

    def subtree_bounds(self, root_name):
        root = shared.bpy.data.objects[root_name]
        minimum = [math.inf, math.inf, math.inf]
        maximum = [-math.inf, -math.inf, -math.inf]
        mesh_names = []
        for obj in self.public_objects():
            if obj.type != "MESH":
                continue
            current = obj
            while current is not None and current != root:
                current = current.parent
            if current != root:
                continue
            bounds = self.object_bounds(obj)
            mesh_names.append(obj.name)
            for axis in range(3):
                minimum[axis] = min(minimum[axis], bounds["min"][axis])
                maximum[axis] = max(maximum[axis], bounds["max"][axis])
        if not mesh_names:
            raise RuntimeError(f"No mesh descendants found for {root_name}")
        return {"min": minimum, "max": maximum,
                "size": [maximum[i] - minimum[i] for i in range(3)],
                "mesh_nodes": sorted(mesh_names)}

    def add_exact_track(self, prefix, center):
        root = self.empty(f"{prefix}_ROOT", center, self.running_root, role="track_root")
        pitch = self.TRACK_LENGTH / 15.0
        for row, y in (("Bottom", 0.035), ("Top", 0.805)):
            for index in range(15):
                x = -self.TRACK_LENGTH / 2.0 + pitch / 2.0 + index * pitch
                pad = self.box(
                    f"{prefix}_Pad_{row}_{index + 1:02d}", (x, y, 0.0),
                    (pitch * 0.88, 0.070, self.SHOE_WIDTH), self.materials["rubber"],
                    root, role="track_shoe", bevel=0.006,
                )
                pad["exo_published_shoe_width_m"] = self.SHOE_WIDTH
        for label, x in (("Rear", -2.190), ("Front", 2.190)):
            self.box(
                f"{prefix}_{label}_End_Shoe", (x, 0.420, 0.0),
                (0.070, 0.700, self.SHOE_WIDTH), self.materials["rubber"], root,
                role="track_shoe", bevel=0,
            )
            self.cylinder(
                f"{prefix}_{label}_Wheel", (x * 0.80, 0.420, 0.0), 0.345, 0.535,
                self.materials["steel"], root, vertices=24, role="track_wheel",
            )
        for index in range(7):
            self.cylinder(
                f"{prefix}_Roller_{index + 1:02d}", (-1.44 + index * 0.48, 0.220, 0.0),
                0.125, 0.525, self.materials["graphite"], root,
                vertices=20, role="track_roller",
            )
        self.box(
            f"{prefix}_Track_Frame", (0.0, 0.465, 0.0), (3.62, 0.235, 0.475),
            self.materials["graphite"], root, role="track_frame",
        )
        for end_label, x in (("Rear", -1.752), ("Front", 1.752)):
            for tooth in range(10):
                angle = math.tau * tooth / 10
                self.box(
                    f"{prefix}_{end_label}_Sprocket_Tooth_{tooth + 1:02d}",
                    (x + math.cos(angle) * 0.315, 0.420 + math.sin(angle) * 0.315, 0.0),
                    (0.080, 0.055, 0.555), self.materials["steel"], root,
                    rotation=(0.0, 0.0, angle), role="track_sprocket_tooth", bevel=0.004,
                )
        return root

    def add_split_hydraulic(self, prefix, base_world, end_world, base_parent,
                            moving_parent, radius, stroke, base_root_name=None,
                            moving_root_name=None):
        base_world, end_world = shared.Vector(base_world), shared.Vector(end_world)
        vector = end_world - base_world
        if vector.length <= 0.20:
            raise RuntimeError(f"Degenerate hydraulic assembly {prefix}")
        direction = vector.normalized()
        overlap = max(0.120, radius * 1.35)
        join = base_world + vector * 0.58
        barrel_end = join + direction * overlap / 2.0
        rod_start = join - direction * overlap / 2.0
        base_root = self.empty(base_root_name or f"{prefix}_ROOT", parent=base_parent,
                               role="hydraulic_fixed_half_root")
        moving_root = self.empty(moving_root_name or f"{prefix}_Rod_ROOT",
                                 parent=moving_parent, role="hydraulic_moving_half_root")
        start_local = self.to_local(base_root, base_world)
        barrel_end_local = self.to_local(base_root, barrel_end)
        rod_start_local = self.to_local(moving_root, rod_start)
        end_local = self.to_local(moving_root, end_world)
        barrel = self.pipe_between(f"{prefix}_Barrel", start_local, barrel_end_local,
                                   radius, self.materials["graphite"], base_root,
                                   role="hydraulic_barrel")
        rod = self.pipe_between(f"{prefix}_Rod", rod_start_local, end_local,
                                radius * 0.48, self.materials["rod"], moving_root,
                                role="hydraulic_rod")
        base_pin = self.cylinder(f"{prefix}_Base_Pin", start_local, radius * 0.82,
                                 0.255, self.materials["steel"], base_root,
                                 vertices=20, role="hydraulic_pin")
        end_pin = self.cylinder(f"{prefix}_Rod_End_Pin", end_local, radius * 0.78,
                                0.255, self.materials["steel"], moving_root,
                                vertices=20, role="hydraulic_pin")
        for side, z in (("L", -0.105), ("R", 0.105)):
            self.box(f"{prefix}_Base_Clevis_{side}",
                     (start_local.x, start_local.y, start_local.z + z),
                     (0.180, 0.150, 0.055), self.materials["steel"], base_root,
                     role="hydraulic_clevis", bevel=0.010)
            self.box(f"{prefix}_Rod_End_Clevis_{side}",
                     (end_local.x, end_local.y, end_local.z + z),
                     (0.160, 0.140, 0.050), self.materials["steel"], moving_root,
                     role="hydraulic_clevis", bevel=0.009)
        base_root["exo_barrel_start_local"] = list(start_local)
        base_root["exo_barrel_end_local"] = list(barrel_end_local)
        moving_root["exo_rod_start_local"] = list(rod_start_local)
        moving_root["exo_rod_end_local"] = list(end_local)
        base_root["exo_published_stroke_m"] = stroke
        barrel["exo_neutral_overlap_m"] = overlap
        rod["exo_neutral_overlap_m"] = overlap
        base_pin["exo_joint_owner"] = base_parent.name
        end_pin["exo_joint_owner"] = moving_parent.name
        return base_root, moving_root

    def add_operator_station(self, upper):
        cab = self.empty("Operator_Station_ROOT", (0.10, 0.48, -0.66), upper,
                         role="operator_station")
        self.box("Cab_Floor", (0.0, 0.065, 0.0), (1.55, 0.13, 1.18),
                 self.materials["graphite"], cab, role="cab_structure")
        self.box("Cab_Roof", (0.0, 1.485, 0.0), (1.52, 0.120, 1.18),
                 self.materials["body"], cab, role="cab_structure", bevel=0)
        self.box("Cab_Front_Glass", (0.725, 0.86, 0.0), (0.065, 1.30, 1.08),
                 self.materials["glass"], cab, role="glazing")
        self.box("Cab_Rear_Glass", (-0.725, 0.82, 0.0), (0.065, 1.18, 1.04),
                 self.materials["glass"], cab, role="glazing")
        for side, z in (("L", -0.555), ("R", 0.555)):
            self.box(f"Cab_{side}_Glass", (0.0, 0.86, z), (1.32, 1.18, 0.045),
                     self.materials["glass"], cab, role="glazing")
            for label, x in (("Rear", -0.725), ("Front", 0.725)):
                self.box(f"Cab_{side}_{label}_Post", (x, 0.80, z),
                         (0.075, 1.32, 0.070), self.materials["graphite"], cab,
                         role="cab_structure")
        self.box("Operator_Seat", (-0.20, 0.50, 0.02), (0.46, 0.68, 0.54),
                 self.materials["graphite"], cab, role="operator_cue")
        self.box("Control_Console", (0.34, 0.48, -0.38), (0.42, 0.38, 0.20),
                 self.materials["graphite"], cab, role="operator_cue")
        self.pipe_between("Cab_Front_Wiper", (0.735, 0.33, -0.30),
                          (0.738, 1.08, 0.18), 0.012,
                          self.materials["graphite"], cab, role="cab_wiper")
        self.pipe_between("Cab_Door_Upper_Rail", (-0.48, 1.30, -0.582),
                          (0.48, 1.30, -0.582), 0.018,
                          self.materials["graphite"], cab, role="cab_door_frame")
        self.pipe_between("Cab_Door_Lower_Rail", (-0.48, 0.28, -0.582),
                          (0.48, 0.28, -0.582), 0.018,
                          self.materials["graphite"], cab, role="cab_door_frame")
        self.box("Cab_Door_Handle", (0.36, 0.72, -0.594),
                 (0.16, 0.035, 0.018), self.materials["rod"], cab,
                 role="cab_door_hardware", bevel=0.005)
        self.cylinder("Cab_Roof_Beacon", (-0.45, 1.575, 0.38), 0.055, 0.09,
                      self.materials["warning"], cab, vertices=20,
                      rotation=(math.pi / 2, 0.0, 0.0), role="safety_beacon")

    def build_excavator(self):
        self.add_exact_track("Track_L", (-1.35, 0.0, -self.TRACK_GAUGE / 2.0))
        self.add_exact_track("Track_R", (-1.35, 0.0, self.TRACK_GAUGE / 2.0))
        self.box("Carbody", (-1.35, 0.875, 0.0), (3.75, 0.130, 1.82),
                 self.materials["graphite"], self.fixed_root, role="carbody")
        for diagonal, start, end in (
            ("Front_L", (-0.20, 0.93, -0.12), (-0.58, 0.93, -1.18)),
            ("Front_R", (-0.20, 0.93, 0.12), (-0.58, 0.93, 1.18)),
            ("Rear_L", (-2.50, 0.93, -0.12), (-2.12, 0.93, -1.18)),
            ("Rear_R", (-2.50, 0.93, 0.12), (-2.12, 0.93, 1.18)),
        ):
            self.pipe_between(f"Carbody_X_Frame_{diagonal}", start, end, 0.095,
                              self.materials["steel"], self.fixed_root,
                              role="carbody_crossmember")
        for side, z in (("L", -self.TRACK_GAUGE / 2.0),
                        ("R", self.TRACK_GAUGE / 2.0)):
            self.cylinder(f"{side}_Travel_Motor_Housing", (-3.10, 0.42, z),
                          0.255, 0.64, self.materials["graphite"],
                          self.fixed_root, vertices=24, role="travel_motor")
            self.cylinder(f"{side}_Travel_Motor_Hub", (-3.10, 0.42, z),
                          0.135, 0.67, self.materials["steel"],
                          self.fixed_root, vertices=20, role="travel_motor_hub")
        self.cylinder("Swing_Bearing", tuple(self.SWING), 0.72, 0.140,
                      self.materials["steel"], self.fixed_root, vertices=32,
                      rotation=(math.pi / 2, 0.0, 0.0), role="swing_bearing")
        swing = self.empty("Upper_Swing_Pivot", tuple(self.SWING), self.root, role="pivot")
        upper = self.empty("Upper_ROOT", parent=swing, role="motion_root")
        self.hydraulics_root.parent = upper
        self.hydraulics_root.location = (0.0, 0.0, 0.0)
        self.box("Hydraulic_Distribution_Block", (-1.20, 0.42, 0.0),
                 (0.62, 0.46, 0.72), self.materials["graphite"],
                 self.hydraulics_root, role="hydraulic_manifold")
        self.box("Upper_Main_Deck", (-0.72, 0.100, 0.0), (4.55, 0.120, 2.65),
                 self.materials["graphite"], upper, role="upper_deck")
        self.side_profile(
            "Counterweight_Main",
            [(-3.58, 0.055), (-1.32, 0.055), (-1.08, 0.24),
             (-1.12, 1.26), (-1.40, 1.405), (-3.18, 1.405),
             (-3.6025, 1.08)],
            2.55, self.materials["body"], upper, role="counterweight",
        )
        self.box("Counterweight_Rear_Bumper", (-3.4825, 0.620, 0.0),
                 (0.240, 0.72, 2.30), self.materials["body_dark"], upper,
                 role="counterweight", bevel=0)
        self.side_profile(
            "Engine_House",
            [(-2.05, 0.265), (0.02, 0.265), (0.02, 1.08),
             (-0.26, 1.445), (-2.05, 1.445)],
            1.50, self.materials["body"], upper, z_center=0.48,
            role="engine_house",
        )
        for side, z in (("Operator", -0.285), ("Service", 1.245)):
            self.box(f"Engine_Hood_{side}_Panel", (-1.02, 0.84, z),
                     (1.76, 0.88, 0.030), self.materials["body_dark"], upper,
                     role="service_panel", bevel=0.012)
            self.pipe_between(f"Engine_Hood_{side}_Upper_Seam",
                              (-1.88, 1.285, z - (0.020 if side == "Operator" else -0.020)),
                              (-0.18, 1.285, z - (0.020 if side == "Operator" else -0.020)),
                              0.012, self.materials["steel"], upper,
                              role="service_panel_seam")
        for index in range(6):
            self.box(f"Rear_Radiator_Slot_{index + 1:02d}",
                     (-3.590, 0.56 + index * 0.105, 0.0),
                     (0.018, 0.060, 1.62), self.materials["graphite"], upper,
                     role="radiator_grille", bevel=0.002)
        for index in range(9):
            self.box(f"Engine_Vent_{index + 1:02d}",
                     (-1.04 + index * 0.19, 1.075, 1.238), (0.115, 0.34, 0.024),
                     self.materials["graphite"], upper, role="vent", bevel=0.003)
        self.box("Fuel_Tank_Step", (-0.02, 0.34, 1.12), (0.72, 0.12, 0.30),
                 self.materials["steel"], upper, role="service_step", bevel=0.015)
        for index, x in enumerate((-0.30, -0.06, 0.18)):
            self.box(f"Fuel_Tank_Step_Tread_{index + 1:02d}",
                     (x, 0.408, 1.12), (0.15, 0.018, 0.28),
                     self.materials["graphite"], upper, role="service_step_tread",
                     bevel=0.002)
        self.add_operator_station(upper)
        rail_y = 3.135 - self.SWING.y - 0.025
        for side, z in (("L", -1.16), ("R", 1.16)):
            self.pipe_between(f"Handrail_Top_Rail_{side}", (-2.62, rail_y, z),
                              (0.10, rail_y, z), 0.025, self.materials["warning"],
                              upper, role="handrail")
            for index, x in enumerate((-2.55, -1.68, -0.81, 0.06)):
                self.pipe_between(f"Handrail_{side}_Post_{index + 1:02d}",
                                  (x, 1.30, z), (x, rail_y, z), 0.022,
                                  self.materials["warning"], upper, role="handrail")

        boom_pivot = self.empty("Boom_Pivot", tuple(self.BOOM_PIVOT_POINT - self.SWING),
                                upper, role="pivot")
        boom = self.empty("Boom_ROOT", parent=boom_pivot, role="motion_root")
        boom_direction = self.BOOM_VECTOR.normalized()
        boom_perpendicular = shared.Vector((-boom_direction.y, boom_direction.x, 0.0))
        boom_centers = [
            shared.Vector((0.0, 0.0, 0.0)),
            self.BOOM_VECTOR * 0.22 + shared.Vector((0.0, 0.18, 0.0)),
            self.BOOM_VECTOR * 0.62 + shared.Vector((0.0, 0.40, 0.0)),
            self.BOOM_VECTOR,
        ]
        boom_half_depths = (0.34, 0.36, 0.30, 0.23)
        boom_line_offsets = (0.40, 0.42, 0.34, 0.18)
        boom_upper = [center + boom_perpendicular * depth
                      for center, depth in zip(boom_centers, boom_half_depths)]
        boom_lower = [center - boom_perpendicular * depth
                      for center, depth in zip(boom_centers, boom_half_depths)]
        boom_outline = [(point.x, point.y) for point in boom_upper]
        boom_outline.extend((point.x, point.y) for point in reversed(boom_lower))
        self.side_profile("Boom_Box_Girder", boom_outline, 0.46,
                          self.materials["body"], boom, role="boom_box_girder")
        for side, z in (("L", -0.255), ("R", 0.255)):
            self.side_profile(f"Boom_Web_Plate_{side}", boom_outline, 0.055,
                              self.materials["body_dark"], boom, z_center=z,
                              role="boom_web_plate")
            for segment in range(len(boom_centers) - 1):
                start = boom_centers[segment] + boom_perpendicular * boom_line_offsets[segment]
                end = boom_centers[segment + 1] + boom_perpendicular * boom_line_offsets[segment + 1]
                start.z = end.z = z + (-0.045 if side == "L" else 0.045)
                self.pipe_between(f"Boom_Hydraulic_Line_{side}_{segment + 1:02d}",
                                  tuple(start), tuple(end), 0.018,
                                  self.materials["graphite"], boom,
                                  role="hydraulic_line")
        self.pipe_between("Boom_Main", (0.0, 0.0, 0.0), tuple(self.BOOM_VECTOR),
                          0.132, self.materials["body"], boom, role="boom")
        for side, z in (("L", -0.145), ("R", 0.145)):
            self.pipe_between(f"Boom_Side_Plate_{side}", (0.10, 0.0, z),
                              tuple(self.BOOM_VECTOR + shared.Vector((-0.10, 0.0, z))),
                              0.082, self.materials["body_dark"], boom,
                              role="boom_side_plate")
        self.cylinder("Boom_Foot_Pin", (0.0, 0.0, 0.0), 0.155, 0.62,
                      self.materials["steel"], boom, vertices=24, role="pivot_pin")
        for side, z in (("L", -0.34), ("R", 0.34)):
            self.side_profile(f"Boom_Foot_Gusset_{side}",
                              [(-0.16, -0.24), (0.52, -0.18),
                               (0.70, 0.22), (-0.08, 0.30)],
                              0.075, self.materials["steel"], boom,
                              z_center=z, role="boom_mount_gusset")
        stick_pivot = self.empty("Stick_Pivot", tuple(self.BOOM_VECTOR), boom, role="pivot")
        stick = self.empty("Stick_ROOT", parent=stick_pivot, role="motion_root")
        stick_direction = self.STICK_VECTOR.normalized()
        stick_perpendicular = shared.Vector((-stick_direction.y, stick_direction.x, 0.0))
        stick_centers = [
            shared.Vector((0.0, 0.0, 0.0)),
            self.STICK_VECTOR * 0.48 + shared.Vector((-0.10, 0.05, 0.0)),
            self.STICK_VECTOR,
        ]
        stick_half_depths = (0.28, 0.235, 0.155)
        stick_upper = [center + stick_perpendicular * depth
                       for center, depth in zip(stick_centers, stick_half_depths)]
        stick_lower = [center - stick_perpendicular * depth
                       for center, depth in zip(stick_centers, stick_half_depths)]
        stick_outline = [(point.x, point.y) for point in stick_upper]
        stick_outline.extend((point.x, point.y) for point in reversed(stick_lower))
        self.side_profile("Stick_Box_Girder", stick_outline, 0.38,
                          self.materials["body_dark"], stick,
                          role="stick_box_girder")
        for side, z in (("L", -0.215), ("R", 0.215)):
            self.side_profile(f"Stick_Web_Plate_{side}", stick_outline, 0.050,
                              self.materials["body"], stick, z_center=z,
                              role="stick_web_plate")
            for segment in range(len(stick_centers) - 1):
                start = stick_centers[segment] + stick_perpendicular * 0.305
                end = stick_centers[segment + 1] + stick_perpendicular * 0.305
                start.z = end.z = z + (-0.040 if side == "L" else 0.040)
                self.pipe_between(f"Stick_Hydraulic_Line_{side}_{segment + 1:02d}",
                                  tuple(start), tuple(end), 0.016,
                                  self.materials["graphite"], stick,
                                  role="hydraulic_line")
        self.pipe_between("Stick_Main", (0.0, 0.0, 0.0), tuple(self.STICK_VECTOR),
                          0.112, self.materials["body_dark"], stick, role="stick")
        for side, z in (("L", -0.115), ("R", 0.115)):
            self.pipe_between(f"Stick_Side_Plate_{side}", (0.0, 0.0, z),
                              tuple(self.STICK_VECTOR + shared.Vector((0.0, 0.0, z))),
                              0.068, self.materials["body"], stick,
                              role="stick_side_plate")
        self.cylinder("Boom_Stick_Pin", (0.0, 0.0, 0.0), 0.135, 0.52,
                      self.materials["steel"], stick, vertices=24, role="pivot_pin")
        bucket_pivot = self.empty("Bucket_Pivot", tuple(self.STICK_VECTOR), stick, role="pivot")
        bucket = self.empty("Bucket_ROOT", parent=bucket_pivot, role="motion_root")
        self.side_profile("Bucket_Shell",
                          [(0.0, 0.0), (0.42, 0.44), (1.26, 0.34), (1.50, 0.03),
                           (1.36, -0.17), (0.30, -0.12), (-0.08, 0.07)],
                          self.BUCKET_WIDTH, self.materials["steel"], bucket,
                          role="bucket")
        bucket_cheek_profile = [
            (0.02, 0.02), (0.43, 0.40), (1.22, 0.31),
            (1.45, 0.04), (1.32, -0.13), (0.34, -0.09),
        ]
        for side, z in (("L", -self.BUCKET_WIDTH / 2.0 + 0.014),
                        ("R", self.BUCKET_WIDTH / 2.0 - 0.014)):
            self.side_profile(f"Bucket_Cheek_{side}", bucket_cheek_profile,
                              0.028, self.materials["body_dark"], bucket,
                              z_center=z, role="bucket_side_cheek")
            self.pipe_between(f"Bucket_Heel_Rib_{side}", (0.35, -0.10, z),
                              (1.30, -0.12, z), 0.024,
                              self.materials["rod"], bucket,
                              role="bucket_reinforcement")
        self.cylinder("Bucket_Torque_Tube", (0.42, 0.34, 0.0), 0.105, 0.82,
                      self.materials["graphite"], bucket, vertices=24,
                      role="bucket_torque_tube")
        self.box("Bucket_Cutting_Edge", (1.45, -0.145, 0.0),
                 (0.36, 0.065, 0.90), self.materials["rod"], bucket,
                 role="bucket_cutting_edge", bevel=0.006)
        for index, z in enumerate((-0.34, -0.17, 0.0, 0.17, 0.34)):
            self.box(f"Bucket_Tooth_{index + 1:02d}",
                     (self.TOOTH_VECTOR.x - 0.090, self.TOOTH_VECTOR.y, z),
                     (0.180, 0.060, 0.105), self.materials["rod"], bucket,
                     role="bucket_tooth", bevel=0)
        self.cylinder("Stick_Bucket_Pin", (0.0, 0.0, 0.0), 0.125, 0.58,
                      self.materials["steel"], bucket, vertices=24, role="pivot_pin")

        boom_unit = self.BOOM_VECTOR.normalized()
        for side, z in (("L", -0.39), ("R", 0.39)):
            self.add_split_hydraulic(
                f"Boom_Cylinder_{side}",
                self.BOOM_PIVOT_POINT + shared.Vector((-0.65, -0.22, z)),
                self.BOOM_PIVOT_POINT + boom_unit * 1.85 + shared.Vector((0.0, 0.0, z)),
                upper, boom, 0.085, self.BOOM_STROKE,
            )
        self.add_split_hydraulic(
            "Arm_Crowd_Cylinder", self.BOOM_PIVOT_POINT + boom_unit * 2.40,
            self.STICK_PIVOT_POINT + self.STICK_VECTOR * 0.38,
            boom, stick, 0.082, self.ARM_STROKE,
            base_root_name="Arm_Crowd_Actuator_ROOT",
            moving_root_name="Arm_Crowd_Rod_ROOT",
        )

        h_pivot_world = shared.Vector((3.80, 1.05, 0.0))
        h_root = self.empty("Bucket_H_Link_ROOT", tuple(self.to_local(stick, h_pivot_world)),
                            stick, role="bucket_linkage_motion_root")
        h_lower = shared.Vector((-0.15, -0.30, 0.0))
        h_cylinder_pin = shared.Vector((0.12, 0.0, 0.0))
        link_z = 0.165
        for side, z in (("L", -link_z), ("R", link_z)):
            self.pipe_between(f"Bucket_H_Link_{side}", (0.0, 0.0, z),
                              (h_lower.x, h_lower.y, z), 0.048,
                              self.materials["warning"], h_root, role="bucket_h_link")
            self.side_profile(f"Bucket_Bellcrank_Plate_{side}",
                              [(0.06, 0.06), (h_lower.x - 0.07, h_lower.y - 0.05),
                               (h_cylinder_pin.x + 0.06, h_cylinder_pin.y - 0.05)],
                              0.050, self.materials["warning"], h_root,
                              z_center=z, role="bucket_h_link_plate")
        self.cylinder("Bucket_H_Link_Pivot_Pin", (0.0, 0.0, 0.0), 0.055,
                      link_z * 2.45, self.materials["graphite"], h_root,
                      vertices=20, role="bucket_linkage_pin")
        self.cylinder("Bucket_H_Link_Lower_Cross_Pin", tuple(h_lower), 0.052,
                      link_z * 2.45, self.materials["graphite"], h_root,
                      vertices=20, role="bucket_linkage_pin")
        self.cylinder("Bucket_H_Link_Cylinder_Pin", tuple(h_cylinder_pin), 0.050,
                      link_z * 2.45, self.materials["steel"], h_root,
                      vertices=20, role="bucket_linkage_pin")
        ear_local = shared.Vector((0.23, 0.25, 0.0))
        ear_world = self.BUCKET_PIVOT_POINT + ear_local
        ear_from_h = ear_world - h_pivot_world
        dogbone = self.empty("Bucket_Dogbone_ROOT", parent=h_root,
                             role="bucket_linkage_root")
        for side, z in (("L", -link_z), ("R", link_z)):
            self.pipe_between(f"Bucket_Dogbone_{side}",
                              (h_lower.x, h_lower.y, z),
                              (ear_from_h.x, ear_from_h.y, z), 0.042,
                              self.materials["rod"], dogbone, role="bucket_dogbone")
        self.cylinder("Bucket_Dogbone_End_Pin", tuple(ear_from_h), 0.050,
                      link_z * 2.45, self.materials["graphite"], dogbone,
                      vertices=20, role="bucket_linkage_pin")
        self.cylinder("Bucket_Ear_Cross_Pin", tuple(ear_local), 0.050,
                      link_z * 2.45, self.materials["steel"], bucket,
                      vertices=20, role="bucket_linkage_pin")
        for side, z in (("L", -link_z), ("R", link_z)):
            self.side_profile(f"Bucket_Linkage_Ear_{side}",
                              [(0.03, 0.02), (ear_local.x - 0.07, ear_local.y - 0.08),
                               (ear_local.x + 0.08, ear_local.y + 0.04), (0.10, 0.18)],
                              0.055, self.materials["steel"], bucket,
                              z_center=z, role="bucket_linkage_ear")
        self.add_split_hydraulic(
            "Bucket_Curl_Cylinder", (4.15, 1.90, 0.0), h_pivot_world + h_cylinder_pin,
            stick, h_root, 0.074, self.BUCKET_STROKE,
            base_root_name="Bucket_Curl_Actuator_ROOT",
            moving_root_name="Bucket_Curl_Rod_ROOT",
        )
        h_root["exo_bucket_ear_local_xy_m"] = [ear_local.x, ear_local.y]
        h_root["exo_h_link_vector_xy_m"] = [h_lower.x, h_lower.y]
        h_root["exo_cylinder_crank_xy_m"] = [h_cylinder_pin.x, h_cylinder_pin.y]
        h_root["exo_dogbone_length_m"] = (ear_from_h - h_lower).length

    def gate(self, gate_id, passed, method, evidence, semantic_nodes, fact_ids):
        return {
            "id": gate_id,
            "status": "PASS" if passed else "FAIL",
            "detail": {
                "method": method,
                "evidence": evidence,
                "semantic_nodes": list(dict.fromkeys(semantic_nodes)),
                "fact_ids": list(dict.fromkeys(fact_ids)),
            },
        }

    def hydraulic_neutral_measurement(self, fixed_name, moving_name):
        fixed = shared.bpy.data.objects[fixed_name]
        moving = shared.bpy.data.objects[moving_name]
        barrel_start = fixed.matrix_world @ shared.Vector(fixed["exo_barrel_start_local"])
        barrel_end = fixed.matrix_world @ shared.Vector(fixed["exo_barrel_end_local"])
        rod_start = moving.matrix_world @ shared.Vector(moving["exo_rod_start_local"])
        rod_end = moving.matrix_world @ shared.Vector(moving["exo_rod_end_local"])
        axis = (rod_end - barrel_start).normalized()
        overlap = (barrel_end - rod_start).dot(axis)
        offset = rod_start - barrel_start
        lateral = (offset - axis * offset.dot(axis)).length
        return {
            "barrel_rod_axial_overlap_m": round(overlap, 6),
            "rod_start_centerline_residual_m": round(lateral, 6),
            "neutral_pin_span_m": round((rod_end - barrel_start).length, 6),
            "published_stroke_m": round(float(fixed["exo_published_stroke_m"]), 6),
        }

    def working_range_reachability(self):
        effective_second_link = self.ARM_LENGTH + self.TOOTH_VECTOR.length
        boom_origin_from_swing = self.BOOM_PIVOT_POINT - self.SWING
        targets = {
            "maximum_digging_height_m": shared.Vector((0.0, 9.970, 0.0)),
            "maximum_dumping_height_m": shared.Vector((0.0, 7.110, 0.0)),
            "maximum_digging_depth_m": shared.Vector((0.0, -6.620, 0.0)),
            "maximum_ground_reach_m": shared.Vector((9.700, 0.0, 0.0)),
        }
        lower = abs(self.BOOM_LENGTH - effective_second_link)
        upper = self.BOOM_LENGTH + effective_second_link
        records, all_reachable = {}, True
        for label, target in targets.items():
            relative = target - boom_origin_from_swing
            distance = math.hypot(relative.x, relative.y)
            reachable = lower <= distance <= upper
            cosine = (
                self.BOOM_LENGTH ** 2 + effective_second_link ** 2 - distance ** 2
            ) / (2.0 * self.BOOM_LENGTH * effective_second_link)
            cosine = max(-1.0, min(1.0, cosine))
            elbow = math.acos(cosine)
            reconstructed = math.sqrt(
                self.BOOM_LENGTH ** 2 + effective_second_link ** 2
                - 2.0 * self.BOOM_LENGTH * effective_second_link * math.cos(elbow)
            )
            residual = abs(reconstructed - distance)
            records[label] = {
                "target_from_swing_center_xy_m": [round(target.x, 6), round(target.y, 6)],
                "target_distance_from_boom_pivot_m": round(distance, 6),
                "solved_internal_angle_rad": round(elbow, 6),
                "radial_residual_m": round(residual, 9),
                "reachable": reachable,
            }
            all_reachable = all_reachable and reachable and residual <= 1e-8
        return all_reachable, records

    def bucket_four_bar_samples(self):
        h_root = shared.bpy.data.objects["Bucket_H_Link_ROOT"]
        h_world = self.world_location(h_root)
        bucket_world = self.world_location(shared.bpy.data.objects["Bucket_ROOT"])
        ear = shared.Vector((*h_root["exo_bucket_ear_local_xy_m"], 0.0))
        h_vector = shared.Vector((*h_root["exo_h_link_vector_xy_m"], 0.0))
        crank = shared.Vector((*h_root["exo_cylinder_crank_xy_m"], 0.0))
        dogbone_length = float(h_root["exo_dogbone_length_m"])
        h_length = h_vector.length
        neutral_h_angle = math.atan2(h_vector.y, h_vector.x)
        cylinder_base = shared.Vector((4.15, 1.90, 0.0))
        samples, cylinder_lengths, all_closed = [], [], True
        for bucket_angle in (0.0, 0.125, 0.250):
            ear_world = bucket_world + self.rot2(ear, bucket_angle)
            delta = ear_world - h_world
            center_distance = math.hypot(delta.x, delta.y)
            cosine = (
                center_distance ** 2 + h_length ** 2 - dogbone_length ** 2
            ) / (2.0 * center_distance * h_length)
            feasible = -1.0 <= cosine <= 1.0
            cosine = max(-1.0, min(1.0, cosine))
            h_angle = math.atan2(delta.y, delta.x) + math.acos(cosine)
            lower_world = h_world + self.rot2(shared.Vector((h_length, 0.0, 0.0)), h_angle)
            residual = abs((ear_world - lower_world).length - dogbone_length)
            h_delta = h_angle - neutral_h_angle
            cylinder_pin = h_world + self.rot2(crank, h_delta)
            cylinder_length = (cylinder_pin - cylinder_base).length
            cylinder_lengths.append(cylinder_length)
            samples.append({
                "bucket_angle_rad": bucket_angle,
                "solved_h_link_delta_rad": round(h_delta, 6),
                "dogbone_closure_residual_m": round(residual, 9),
                "bucket_cylinder_pin_distance_m": round(cylinder_length, 6),
            })
            all_closed = all_closed and feasible and residual <= 1e-7
        stroke_use = max(cylinder_lengths) - min(cylinder_lengths)
        return all_closed and stroke_use <= self.BUCKET_STROKE, samples, stroke_use

    def front_sweep_samples(self, track_front_x):
        physical_tooth_bottom = self.TOOTH_VECTOR + shared.Vector((0.0, -0.030, 0.0))
        records, min_y, min_track_clearance = [], math.inf, math.inf
        for boom_angle in (0.0, 0.09, 0.18):
            for arm_angle in (-0.18, -0.09, 0.0):
                for bucket_angle in (0.0, 0.125, 0.25):
                    boom_tip = self.BOOM_PIVOT_POINT + self.rot2(self.BOOM_VECTOR, boom_angle)
                    bucket_pin = boom_tip + self.rot2(self.STICK_VECTOR, boom_angle + arm_angle)
                    tooth = bucket_pin + self.rot2(
                        physical_tooth_bottom, boom_angle + arm_angle + bucket_angle
                    )
                    min_y = min(min_y, tooth.y)
                    for swing_angle in (-0.32, 0.0, 0.32):
                        radial_x = tooth.x - self.SWING.x
                        swept_x = self.SWING.x + radial_x * math.cos(swing_angle)
                        conservative_x = (
                            swept_x - self.BUCKET_WIDTH / 2.0 * abs(math.sin(swing_angle))
                        )
                        min_track_clearance = min(
                            min_track_clearance, conservative_x - track_front_x
                        )
                    records.append({
                        "boom_rad": boom_angle,
                        "arm_rad": arm_angle,
                        "bucket_rad": bucket_angle,
                        "physical_tooth_bottom_xy_m": [round(tooth.x, 6), round(tooth.y, 6)],
                    })
        return min_y, min_track_clearance, records

    def machine_specific_validation_gates(self, contract):
        shared.bpy.context.view_layer.update()
        tolerance = 0.003
        bounds = contract["bounds"]
        envelope_ok = all(
            abs(bounds["size_m"][index] - expected) <= tolerance
            for index, expected in enumerate((9.705, 3.135, 3.080))
        ) and bounds["min_m"][1] >= -1e-6

        left_track = self.subtree_bounds("Track_L_ROOT")
        right_track = self.subtree_bounds("Track_R_ROOT")
        shoe = self.object_bounds(shared.bpy.data.objects["Track_L_Pad_Bottom_01"])
        gauge = abs(
            self.world_location(shared.bpy.data.objects["Track_R_ROOT"]).z
            - self.world_location(shared.bpy.data.objects["Track_L_ROOT"]).z
        )
        track_ok = (
            abs(left_track["size"][0] - self.TRACK_LENGTH) <= tolerance
            and abs(right_track["size"][0] - self.TRACK_LENGTH) <= tolerance
            and abs(shoe["size"][2] - self.SHOE_WIDTH) <= tolerance
            and abs(gauge - self.TRACK_GAUGE) <= tolerance
        )
        undercarriage_ground_ok = (
            abs(left_track["min"][1]) <= 1e-6 and abs(right_track["min"][1]) <= 1e-6
        )

        carbody_bounds = self.object_bounds(shared.bpy.data.objects["Carbody"])
        deck_bounds = self.object_bounds(shared.bpy.data.objects["Upper_Main_Deck"])
        swing_clearance = deck_bounds["min"][1] - carbody_bounds["max"][1]
        swing_ok = swing_clearance >= 0.05

        actual_parents, hierarchy_ok = {}, True
        for name, expected in self.REQUIRED_PARENTS.items():
            obj = shared.bpy.data.objects.get(name)
            actual = obj.parent.name if obj is not None and obj.parent is not None else None
            actual_parents[name] = actual
            hierarchy_ok = hierarchy_ok and actual == expected

        boom_length = (
            self.world_location(shared.bpy.data.objects["Stick_Pivot"])
            - self.world_location(shared.bpy.data.objects["Boom_Pivot"])
        ).length
        arm_length = (
            self.world_location(shared.bpy.data.objects["Bucket_Pivot"])
            - self.world_location(shared.bpy.data.objects["Stick_Pivot"])
        ).length
        bucket_width = self.object_bounds(shared.bpy.data.objects["Bucket_Shell"])["size"][2]
        lengths_ok = (
            abs(boom_length - self.BOOM_LENGTH) <= 1e-6
            and abs(arm_length - self.ARM_LENGTH) <= 1e-6
            and abs(bucket_width - self.BUCKET_WIDTH) <= tolerance
        )

        curl_closed, curl_samples, bucket_stroke_use = self.bucket_four_bar_samples()
        dogbone_pin_gap = (
            self.world_location(shared.bpy.data.objects["Bucket_Dogbone_End_Pin"])
            - self.world_location(shared.bpy.data.objects["Bucket_Ear_Cross_Pin"])
        ).length
        bucket_linkage_ok = curl_closed and dogbone_pin_gap <= 1e-7
        reach_ok, reach_records = self.working_range_reachability()

        pairs = {
            "boom_left": ("Boom_Cylinder_L_ROOT", "Boom_Cylinder_L_Rod_ROOT"),
            "boom_right": ("Boom_Cylinder_R_ROOT", "Boom_Cylinder_R_Rod_ROOT"),
            "arm": ("Arm_Crowd_Actuator_ROOT", "Arm_Crowd_Rod_ROOT"),
            "bucket": ("Bucket_Curl_Actuator_ROOT", "Bucket_Curl_Rod_ROOT"),
        }
        hydraulic_records = {
            key: self.hydraulic_neutral_measurement(*names) for key, names in pairs.items()
        }
        boom_base = self.BOOM_PIVOT_POINT + shared.Vector((-0.65, -0.22, 0.0))
        boom_anchor = self.BOOM_PIVOT_POINT + self.BOOM_VECTOR.normalized() * 1.85
        boom_lengths = []
        for angle in (0.0, 0.09, 0.18):
            moving = self.BOOM_PIVOT_POINT + self.rot2(
                boom_anchor - self.BOOM_PIVOT_POINT, angle
            )
            boom_lengths.append((moving - boom_base).length)
        arm_base = self.BOOM_VECTOR.normalized() * 2.40
        arm_anchor = self.STICK_VECTOR * 0.38
        arm_lengths = [
            (self.BOOM_VECTOR + self.rot2(arm_anchor, angle) - arm_base).length
            for angle in (-0.18, -0.09, 0.0)
        ]
        stroke_use = {
            "boom_m": round(max(boom_lengths) - min(boom_lengths), 6),
            "arm_m": round(max(arm_lengths) - min(arm_lengths), 6),
            "bucket_m": round(bucket_stroke_use, 6),
        }
        hydraulic_ok = all(
            item["barrel_rod_axial_overlap_m"] >= 0.115
            and item["rod_start_centerline_residual_m"] <= 1e-5
            for item in hydraulic_records.values()
        ) and (
            stroke_use["boom_m"] <= self.BOOM_STROKE
            and stroke_use["arm_m"] <= self.ARM_STROKE
            and stroke_use["bucket_m"] <= self.BUCKET_STROKE
        )

        bucket_bounds = self.subtree_bounds("Bucket_ROOT")
        track_front_x = max(left_track["max"][0], right_track["max"][0])
        bucket_track_clearance = bucket_bounds["min"][0] - track_front_x
        lateral_track_gap = right_track["min"][2] - left_track["max"][2]
        self_collision_ok = bucket_track_clearance >= 1.5 and lateral_track_gap >= 1.0
        min_tooth_y, min_swept_clearance, sweep_records = self.front_sweep_samples(track_front_x)
        swept_ok = min_tooth_y >= 0.005 and min_swept_clearance >= 1.0

        return [
            self.gate(
                "published_transport_envelope", envelope_ok,
                "Decode all public GLB POSITION accessors through node transforms and compare the visible AABB with brochure page 21 dimensions A, D/N, and F.",
                {"measured_xyz_m": bounds["size_m"], "required_xyz_m": [9.705, 3.135, 3.080], "absolute_tolerance_m": tolerance, "minimum_y_m": bounds["min_m"][1]},
                ["Counterweight_Rear_Bumper", "Bucket_Tooth_03", "Handrail_Top_Rail_L", "Track_L_ROOT", "Track_R_ROOT"],
                ["public-envelope-x", "public-envelope-y", "public-envelope-z"],
            ),
            self.gate(
                "track_gauge_and_shoe_width", track_ok,
                "Measure both complete track mesh subtrees, one physical shoe, and lateral track-root separation in world metres after modifiers.",
                {"left_track_length_m": round(left_track["size"][0], 6), "right_track_length_m": round(right_track["size"][0], 6), "shoe_width_m": round(shoe["size"][2], 6), "track_gauge_m": round(gauge, 6), "required_m": {"track_length": 4.45, "shoe_width": 0.7, "track_gauge": 2.38}},
                ["Track_L_ROOT", "Track_R_ROOT", "Track_L_Pad_Bottom_01"],
                ["track-length", "shoe-width", "track-gauge"],
            ),
            self.gate(
                "undercarriage_ground_contact", undercarriage_ground_ok,
                "Measure the minimum world-Y vertex of each complete authored track subtree.",
                {"left_min_y_m": round(left_track["min"][1], 6), "right_min_y_m": round(right_track["min"][1], 6), "ground_y_m": 0.0},
                ["Track_L_ROOT", "Track_R_ROOT"], [],
            ),
            self.gate(
                "upper_swing_clearance", swing_ok,
                "Subtract measured Carbody maximum Y from Upper_Main_Deck minimum Y in the neutral pose.",
                {"carbody_max_y_m": round(carbody_bounds["max"][1], 6), "upper_deck_min_y_m": round(deck_bounds["min"][1], 6), "clearance_m": round(swing_clearance, 6), "minimum_m": 0.05},
                ["Upper_Swing_Pivot", "Upper_ROOT", "Upper_Main_Deck", "Carbody", "Swing_Bearing"], [],
            ),
            self.gate(
                "boom_arm_bucket_hierarchy", hierarchy_ok,
                "Resolve actual parent ownership for carrier, front equipment, actuator halves, H-link, dogbones, and bucket ears before export.",
                {"parents": {name: {"expected": self.REQUIRED_PARENTS[name], "actual": actual_parents[name]} for name in self.REQUIRED_PARENTS}},
                ["Upper_ROOT", "Boom_ROOT", "Stick_ROOT", "Bucket_ROOT", "Arm_Crowd_Actuator_ROOT", "Bucket_H_Link_ROOT", "Bucket_Dogbone_ROOT"], [],
            ),
            self.gate(
                "boom_and_arm_length_constraints", lengths_ok,
                "Measure semantic pivot chords and physical Bucket_Shell lateral width in world metres; compare with brochure pages 20-21.",
                {"boom_chord_m": round(boom_length, 6), "arm_chord_m": round(arm_length, 6), "bucket_width_m": round(bucket_width, 6), "required_m": {"boom": 5.7, "arm": 2.925, "bucket_width": 0.914}, "tolerance_m": tolerance},
                ["Boom_Pivot", "Stick_Pivot", "Bucket_Pivot", "Bucket_Shell"],
                ["boom-length", "arm-length", "selected-bucket-width"],
            ),
            self.gate(
                "bucket_linkage_visual_closure", bucket_linkage_ok,
                "Solve the reconstructed H-link/dogbone circle intersection at three bucket angles and directly compare neutral dogbone-end and bucket-ear pin centers.",
                {"neutral_pin_gap_m": round(dogbone_pin_gap, 9), "samples": curl_samples, "maximum_residual_m": 1e-7},
                ["Bucket_H_Link_ROOT", "Bucket_H_Link_L", "Bucket_H_Link_R", "Bucket_Dogbone_ROOT", "Bucket_Dogbone_L", "Bucket_Dogbone_R", "Bucket_Linkage_Ear_L", "Bucket_Linkage_Ear_R", "Bucket_Ear_Cross_Pin"], [],
            ),
            self.gate(
                "published_working_range_endpoints", reach_ok,
                "Solve a conservative two-link radial reachability equation for brochure page 22 A/B/C/G using exact authored link lengths and boom-pivot offset; this is geometric reachability, not manufacturer anchor or force proof.",
                {"source_locator": "EN-PC210LCi-11BR02-0225-V2 page 22, Working Range A/B/C/G", "effective_bucket_tip_radius_m": round(self.TOOTH_VECTOR.length, 6), "solutions": reach_records},
                ["Upper_Swing_Pivot", "Boom_Pivot", "Stick_Pivot", "Bucket_Pivot", "Bucket_Tooth_03"],
                ["maximum-digging-height", "maximum-dumping-height", "maximum-digging-depth", "maximum-ground-reach"],
            ),
            self.gate(
                "hydraulic_cylinder_visual_closure", hydraulic_ok,
                "Transform barrel-mouth and rod-start centerline points from their separate fixed/moving parents, require neutral overlap, and sample declared joint ranges against brochure page 20 strokes.",
                {"neutral_pairs": hydraulic_records, "sampled_stroke_use_m": stroke_use, "published_strokes_m": {"boom_each": 1.334, "arm": 1.49, "bucket": 1.105}, "boom_cylinder_count": 2},
                ["Boom_Cylinder_L_ROOT", "Boom_Cylinder_L_Rod_ROOT", "Boom_Cylinder_R_ROOT", "Boom_Cylinder_R_Rod_ROOT", "Arm_Crowd_Actuator_ROOT", "Arm_Crowd_Rod_ROOT", "Bucket_Curl_Actuator_ROOT", "Bucket_Curl_Rod_ROOT"],
                ["boom-cylinder-stroke", "arm-cylinder-stroke", "bucket-cylinder-stroke"],
            ),
            self.gate(
                "ground_collision", bounds["min_m"][1] >= -1e-6,
                "Decode the complete rebuilt public GLB AABB and require no visible vertex below Y=0 in the authored transport pose.",
                {"public_glb_min_y_m": bounds["min_m"][1], "ground_y_m": 0.0, "tolerance_m": 1e-6},
                ["Machine_Root", "Track_L_ROOT", "Track_R_ROOT", "Bucket_ROOT"], [],
            ),
            self.gate(
                "self_collision", self_collision_ok,
                "Measure neutral non-adjacent bucket-to-track longitudinal separation and inner-face separation of the two complete track subtrees.",
                {"bucket_track_clearance_m": round(bucket_track_clearance, 6), "track_inner_gap_m": round(lateral_track_gap, 6), "minimums_m": {"bucket_track": 1.5, "track_inner_gap": 1.0}},
                ["Bucket_ROOT", "Track_L_ROOT", "Track_R_ROOT"], [],
            ),
            self.gate(
                "swept_volume_collision", swept_ok,
                "Evaluate 27 boom/arm/bucket endpoint combinations and both swing extremes; require the physical tooth-bottom point above ground and conservatively forward of the track-front plane.",
                {"front_pose_count": len(sweep_records), "swing_samples_rad": [-0.32, 0.0, 0.32], "minimum_tooth_bottom_y_m": round(min_tooth_y, 6), "minimum_bucket_track_clearance_m": round(min_swept_clearance, 6), "limits_m": {"tooth_bottom_y": 0.005, "bucket_track_clearance": 1.0}, "front_samples": sweep_records},
                ["Upper_ROOT", "Boom_ROOT", "Stick_ROOT", "Bucket_ROOT", "Track_L_ROOT", "Track_R_ROOT"], [],
            ),
        ]

    def create_receipt(self, contract, render_paths, validation):
        receipt = super().create_receipt(contract, render_paths, validation)
        for name in self.REQUIRED_PARENTS:
            receipt["required_semantic_nodes"][name] = name in contract["node_names"]
        for name in (
            "Boom_Cylinder_L_Base_Pin", "Boom_Cylinder_L_Rod_End_Pin",
            "Boom_Cylinder_R_Base_Pin", "Boom_Cylinder_R_Rod_End_Pin",
            "Arm_Crowd_Cylinder_Base_Pin", "Arm_Crowd_Cylinder_Rod_End_Pin",
            "Bucket_Curl_Cylinder_Base_Pin", "Bucket_Curl_Cylinder_Rod_End_Pin",
            "Bucket_H_Link_Pivot_Pin", "Bucket_H_Link_Lower_Cross_Pin",
            "Bucket_H_Link_Cylinder_Pin", "Bucket_Dogbone_End_Pin",
            "Bucket_Ear_Cross_Pin",
        ):
            receipt["required_semantic_nodes"][name] = name in contract["node_names"]
        return receipt


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = shared.parse_args(argv)
    design_path = Path(args.design).resolve()
    try:
        design = shared.load_design(design_path)
    except shared.DesignContractError as error:
        raise SystemExit(f"fleet design rejected: {error}") from error
    KomatsuPC210LC11Builder(design, design_path, Path(args.output_dir)).run()


if __name__ == "__main__":
    main()
