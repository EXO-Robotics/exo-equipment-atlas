#!/usr/bin/env python3
"""Deterministic Vermeer ZR5-1200 structural study.

The machine-local topology owns a 1.956 m five-bar pickup with 65 double-tooth
stations, eight visible chamber belts, standard netwrap, integrated quarter-turn
ramp, and four independent double-A-arm suspension/steering corners. Hidden
cam, belt, hydraulic and bale trajectories remain reconstructed.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared():
    spec = importlib.util.spec_from_file_location("exo_fleet_builder_vermeer_zr5", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared builder {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared()


class VermeerZR5Builder(shared.FleetBuilder):
    PICKUP_WIDTH_M = 1.956
    PICKUP_BAR_COUNT = 5
    PICKUP_DOUBLE_TOOTH_COUNT = 65
    CHAMBER_BELT_COUNT = 8

    def write_machine_wrapper(self):
        """Preserve the machine-local authoring subclass."""

    def create_materials(self):
        super().create_materials()
        # Neutral low-chroma study palette: silhouette and process topology do
        # the identification work, not manufacturer-associated paint.
        colors = {
            "body": (0.34, 0.33, 0.30),
            "body_dark": (0.17, 0.17, 0.16),
            "warning": (0.48, 0.45, 0.36),
        }
        for key, color in colors.items():
            material = self.materials[key]
            material.diffuse_color = (*color, 1.0)
            material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*color, 1.0)

    @staticmethod
    def _descends(node_name, ancestor_name):
        node = bpy.data.objects.get(node_name)
        while node is not None:
            if node.name == ancestor_name:
                return True
            node = node.parent
        return False

    def _gate(self, gate_id, condition, evidence, semantic_nodes, fact_ids=()):
        return {"id": gate_id, "status": "PASS" if condition else "FAIL", "detail": {
            "method": "machine-local hierarchy assertion and sampled metric pose measurement",
            "evidence": evidence, "semantic_nodes": list(semantic_nodes), "fact_ids": list(fact_ids)}}

    def _belt_loop(self, name, parent, radius, width, thickness=0.035, segments=40):
        vertices, faces = [], []
        for index in range(segments):
            angle = math.tau * index / segments
            for radial in (radius - thickness / 2, radius + thickness / 2):
                for z in (-width / 2, width / 2):
                    vertices.append((math.cos(angle) * radial, math.sin(angle) * radial, z))
        for index in range(segments):
            nxt = (index + 1) % segments
            a, b = index * 4, nxt * 4
            faces.extend([(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2),
                          (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)])
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = parent
        obj.data.materials.append(self.materials["rubber"])
        return self.tag(obj, role="chamber_belt")

    def _add_wheel(self, prefix, parent, radius, width):
        steer = self.empty(f"{prefix}_Steering_Pivot", parent=parent, role="steering_pivot")
        wheel = self.empty(f"{prefix}_Wheel_ROOT", parent=steer, role="wheel_root")
        self.wheel_tire(f"{prefix}_Tire", radius, width / 2, self.materials["rubber"], wheel)
        self.cylinder(f"{prefix}_Rim", (0, 0, 0), radius * 0.48, width * 0.76,
                      self.materials["steel"], wheel, vertices=24, role="wheel_rim")
        self.cylinder(f"{prefix}_Hub", (0, 0, 0), radius * 0.17, width * 0.84,
                      self.materials["graphite"], wheel, vertices=18, role="wheel_hub")
        return steer, wheel

    def _add_suspension_corner(self, axle_root, axle_label, side, sign, z, radius, width):
        suspension = self.empty(f"{axle_label}_{side}_Suspension_ROOT", (0, 0, z),
                                axle_root, role="suspension_root")
        for level, y in (("Upper", 0.18), ("Lower", -0.12)):
            arm = self.empty(f"{axle_label}_{side}_{level}_AArm_ROOT", (0, y, 0),
                             suspension, role="suspension_link_root")
            self.pipe_between(f"{axle_label}_{side}_{level}_AArm_Front", (-0.34, 0, -sign * 0.18),
                              (0, -y * 0.25, 0), 0.035, self.materials["steel"], arm,
                              role="a_arm_link")
            self.pipe_between(f"{axle_label}_{side}_{level}_AArm_Rear", (0.34, 0, -sign * 0.18),
                              (0, -y * 0.25, 0), 0.035, self.materials["steel"], arm,
                              role="a_arm_link")
        self._add_wheel(f"{axle_label}_{side}", suspension, radius, width)
        chassis_x = 1.65 if axle_label == "Front" else -1.72
        self.pipe_between(f"{axle_label}_{side}_Suspension_Barrel",
                          (chassis_x - 0.28, radius + 0.42, sign * (abs(z) - 0.18)),
                          (chassis_x - 0.04, radius + 0.18, sign * abs(z)), 0.045,
                          self.materials["graphite"], self.hydraulics_root,
                          role="hydraulic_barrel")
        self.pipe_between(f"{axle_label}_{side}_Suspension_Rod", (-0.04, 0.38, -sign * 0.10),
                          (0, 0.08, 0), 0.026, self.materials["rod"], suspension,
                          role="hydraulic_rod")
        return suspension

    def _add_running_gear(self):
        front_pivot = self.empty("Front_Axle_Oscillation_Pivot", (1.65, 0.48, 0),
                                 self.running_root, role="pivot")
        front = self.empty("Front_Axle_ROOT", parent=front_pivot, role="motion_root")
        self.box("Front_Axle_Crossmember", (0, 0.10, 0), (0.86, 0.16, 2.68),
                 self.materials["graphite"], front, role="axle_structure")
        for side, sign in (("L", -1), ("R", 1)):
            self._add_suspension_corner(front, "Front", side, sign, sign * 1.36, 0.48, 0.48)
        rear_pivot = self.empty("Rear_Axle_Pivot", (-1.72, 0.72, 0), self.running_root, role="pivot")
        rear = self.empty("Rear_Axle_ROOT", parent=rear_pivot, role="motion_root")
        self.box("Rear_Axle_Crossmember", (0, 0.10, 0), (0.92, 0.18, 2.94),
                 self.materials["graphite"], rear, role="axle_structure")
        rear_z = self.width / 2 - 0.32
        for side, sign in (("L", -1), ("R", 1)):
            self._add_suspension_corner(rear, "Rear", side, sign, sign * rear_z, 0.72, 0.64)

    def _add_pickup(self):
        pivot = self.empty("Pickup_Lift_Pivot", (0.18, 0.54, 0), self.fixed_root, role="pivot")
        pickup = self.empty("Pickup_ROOT", parent=pivot, role="motion_root")
        rotor = self.empty("Pickup_Rotor_ROOT", (0.70, 0.10, 0), pickup, role="rotary_root")
        global_tooth = 0
        for bar_index in range(self.PICKUP_BAR_COUNT):
            angle = math.tau * bar_index / self.PICKUP_BAR_COUNT
            bar = self.empty(f"Pickup_Bar_{bar_index + 1:02d}_ROOT",
                             (math.cos(angle) * 0.25, math.sin(angle) * 0.25, 0),
                             rotor, role="rotary_bar_root")
            bar.rotation_euler.z = angle
            crossbar = self.cylinder(f"Pickup_Bar_{bar_index + 1:02d}", (0, 0, 0), 0.026,
                                     self.PICKUP_WIDTH_M, self.materials["steel"], bar,
                                     vertices=14, role="pickup_tooth_bar")
            crossbar["exo_tooth_to_tooth_width_m"] = self.PICKUP_WIDTH_M
            for tooth_index in range(13):
                global_tooth += 1
                z = -self.PICKUP_WIDTH_M / 2 + self.PICKUP_WIDTH_M * tooth_index / 12
                tooth = self.empty(f"Pickup_DoubleTooth_{global_tooth:03d}_ROOT", (0, 0, z),
                                   bar, role="double_tooth_root")
                for finger, dz in (("A", -0.025), ("B", 0.025)):
                    self.box(f"Pickup_DoubleTooth_{global_tooth:03d}_{finger}", (0.07, -0.11, dz),
                             (0.035, 0.22, 0.018), self.materials["steel"], tooth,
                             rotation=(0, 0, -0.22), role="pickup_tooth", bevel=0.003)
        self.box("Pickup_Front_Gauge_Roller", (0.92, -0.18, 0), (0.16, 0.12, 2.16),
                 self.materials["graphite"], pickup, role="pickup_gauge")
        # Continuous rising feed path into the chamber throat.
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(f"Pickup_Feed_{side}_Rail", (0.42, 0.00, sign * 0.92),
                              (-0.15, 0.42, sign * 0.92), 0.032, self.materials["steel"],
                              pickup, role="pickup_feed_frame")
        for index in range(11):
            fraction = index / 10
            self.box(f"Pickup_Feed_Slat_{index + 1:02d}",
                     (0.42 * (1 - fraction) - 0.15 * fraction, 0.00 * (1 - fraction) + 0.42 * fraction, 0),
                     (0.055, 0.025, 1.82), self.materials["steel"], pickup,
                     rotation=(0, 0, -0.50), role="pickup_feed_slat", bevel=0.003)
        self.pipe_between("Pickup_Lift_Cylinder_Barrel", (0.02, 1.04, -0.68),
                          (0.30, 0.82, -0.68), 0.042, self.materials["graphite"],
                          self.hydraulics_root, role="hydraulic_barrel")
        self.pipe_between("Pickup_Lift_Cylinder_Rod", (-0.08, 0.42, -0.68),
                          (0.44, 0.10, -0.68), 0.024, self.materials["rod"], pickup,
                          role="hydraulic_rod")

    def _add_chamber(self):
        chamber = self.empty("Bale_Chamber_ROOT", (-0.62, 1.72, 0), self.fixed_root,
                             role="rotary_process_root")
        for side, z in (("L", -0.90), ("R", 0.90)):
            self.cylinder(f"Chamber_{side}_Side_Ring", (0, 0, z), 0.82, 0.08,
                          self.materials["body"], chamber, vertices=32,
                          role="chamber_side_structure")
            self.box(f"Chamber_{side}_Lower_Frame", (-0.10, -0.58, z),
                     (1.20, 0.12, 0.10), self.materials["body_dark"], chamber,
                     role="chamber_frame")
        for index in range(self.CHAMBER_BELT_COUNT):
            z = -0.68 + index * (1.36 / (self.CHAMBER_BELT_COUNT - 1))
            belt = self.empty(f"Chamber_Belt_{index + 1:02d}_ROOT", (0, 0, z), chamber,
                              role="rotary_process_root")
            loop = self._belt_loop(f"Chamber_Belt_{index + 1:02d}", belt, 0.70, 0.12)
            loop["exo_belt_index"] = index + 1
            self.box(f"Chamber_Belt_{index + 1:02d}_Phase_Marker", (0.68, 0, 0),
                     (0.12, 0.08, 0.10), self.materials["warning"], belt,
                     role="belt_phase_marker", bevel=0.003)
        netwrap = self.empty("Netwrap_ROOT", (0.34, 0.48, 0), chamber,
                             role="rotary_process_root")
        self.cylinder("Standard_Netwrap_Roll", (0, 0, 0), 0.16, 1.62,
                      self.materials["warning"], netwrap, vertices=26, role="netwrap_roll")
        self.box("Netwrap_Feed_Sheet", (-0.18, -0.24, 0), (0.48, 0.025, 1.58),
                 self.materials["steel"], netwrap, rotation=(0, 0, -0.28), role="netwrap_feed")
        tailgate_pivot = self.empty("Tailgate_Pivot", (-0.35, 0.46, 0), chamber, role="pivot")
        tailgate = self.empty("Tailgate_ROOT", parent=tailgate_pivot, role="motion_root")
        for side, z in (("L", -0.86), ("R", 0.86)):
            self.side_profile(f"Tailgate_{side}_Frame",
                              [(0, 0), (-0.72, -0.18), (-0.92, -0.82), (-0.45, -1.25), (0.10, -0.72)],
                              0.10, self.materials["body"], tailgate, z_center=z,
                              role="tailgate_frame")
        self.box("Tailgate_Rear_Crossbar", (-0.72, -0.62, 0), (0.12, 0.18, 1.74),
                 self.materials["body_dark"], tailgate, role="tailgate_structure")
        self.pipe_between("Tailgate_Cylinder_Barrel", (-1.45, 2.34, -0.72),
                          (-1.15, 2.08, -0.72), 0.045, self.materials["graphite"],
                          self.hydraulics_root, role="hydraulic_barrel")
        self.pipe_between("Tailgate_Cylinder_Rod", (-0.10, -0.12, -0.72),
                          (-0.56, -0.54, -0.72), 0.026, self.materials["rod"], tailgate,
                          role="hydraulic_rod")

    def _add_quarter_turn_ramp(self):
        pivot = self.empty("Quarter_Turn_Ramp_Pivot", (-2.50, 0.56, 0),
                           self.fixed_root, role="pivot")
        ramp = self.empty("Quarter_Turn_Ramp_ROOT", parent=pivot, role="motion_root")
        extension = self.length / 2 - 2.50
        self.box("Quarter_Turn_Ramp_Platform", (-extension / 2, 0, 0),
                 (extension, 0.09, 1.78), self.materials["steel"], ramp,
                 role="quarter_turn_ramp")
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(f"Quarter_Turn_Ramp_{side}_Rail", (0.05, 0.14, sign * 0.83),
                              (-extension + 0.05, 0.14, sign * 0.83), 0.030,
                              self.materials["body_dark"], ramp, role="ramp_rail")
        cradle = self.empty("Quarter_Turn_Cradle_ROOT", (-extension * 0.60, 0.14, 0),
                            ramp, role="motion_root")
        self.box("Quarter_Turn_Cradle", (0, 0, 0), (0.28, 0.10, 1.62),
                 self.materials["warning"], cradle, role="turn_cradle")
        path = self.empty("Quarter_Turn_Bale_Path_ROOT", parent=self.fixed_root,
                          role="process_path_root")
        points = [(-1.18, 1.36, 0), (-1.72, 0.92, 0), (-2.28, 0.70, 0), (-2.80, 0.64, 0)]
        for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
            self.pipe_between(f"Quarter_Turn_Bale_Path_{index:02d}", start, end, 0.030,
                              self.materials["warning"], path, role="schematic_bale_path")
        self.pipe_between("Ramp_Cylinder_Barrel", (-2.18, 0.96, 0.68),
                          (-2.42, 0.76, 0.68), 0.040, self.materials["graphite"],
                          self.hydraulics_root, role="hydraulic_barrel")
        self.pipe_between("Ramp_Cylinder_Rod", (0.02, 0.28, 0.68),
                          (-extension * 0.34, 0.10, 0.68), 0.023,
                          self.materials["rod"], ramp, role="hydraulic_rod")

    def build_self_propelled_round_baler(self):
        self._add_running_gear()
        self.box("ZR5_Main_Frame", (0, 0.86, 0), (5.25, 0.24, 2.62),
                 self.materials["graphite"], self.fixed_root, role="chassis")
        self.box("Front_Terminal_Bumper", (self.length / 2 - 0.05, 0.84, 0),
                 (0.10, 0.36, 2.20), self.materials["steel"], self.fixed_root,
                 role="front_structure")
        self.side_profile("Power_Module_Tapered_Shell",
                          [(-0.395, 1.17), (1.155, 1.17), (1.155, 1.92),
                           (0.86, 2.35), (-0.20, 2.35), (-0.395, 2.08)],
                          2.32, self.materials["body"], self.fixed_root,
                          role="power_module")
        self.add_cab(1.78, 1.45, 1.55, 2.24, self.height - 1.45, self.fixed_root)
        self._add_pickup()
        self._add_chamber()
        self._add_quarter_turn_ramp()

    def _set_review_pose(self, label):
        for axle in ("Front", "Rear"):
            for side in ("L", "R"):
                bpy.data.objects[f"{axle}_{side}_Suspension_ROOT"].location.y = 0
                bpy.data.objects[f"{axle}_{side}_Steering_Pivot"].rotation_euler.y = 0
        bpy.data.objects["Pickup_ROOT"].rotation_euler.z = 0
        bpy.data.objects["Tailgate_ROOT"].rotation_euler.z = 0
        bpy.data.objects["Quarter_Turn_Ramp_ROOT"].rotation_euler.z = 0
        bpy.data.objects["Quarter_Turn_Cradle_ROOT"].rotation_euler.x = 0
        if label == "front-three-quarter":
            bpy.data.objects["Pickup_ROOT"].rotation_euler.z = 0.14
        elif label == "rear-three-quarter":
            bpy.data.objects["Tailgate_ROOT"].rotation_euler.z = 0.68
            bpy.data.objects["Quarter_Turn_Ramp_ROOT"].rotation_euler.z = -0.20
            bpy.data.objects["Quarter_Turn_Cradle_ROOT"].rotation_euler.x = 0.55
        elif label == "elevated-technical":
            bpy.data.objects["Tailgate_ROOT"].rotation_euler.z = 0.46
            bpy.data.objects["Quarter_Turn_Ramp_ROOT"].rotation_euler.z = -0.18
            bpy.data.objects["Quarter_Turn_Cradle_ROOT"].rotation_euler.x = 0.78
        elif label == "articulation-detail":
            bpy.data.objects["Tailgate_ROOT"].rotation_euler.z = 0.88
            bpy.data.objects["Quarter_Turn_Ramp_ROOT"].rotation_euler.z = -0.28
            bpy.data.objects["Quarter_Turn_Cradle_ROOT"].rotation_euler.x = 1.0
            bpy.data.objects["Pickup_ROOT"].rotation_euler.z = 0.12
        elif label == "right-side":
            for side in ("L", "R"):
                bpy.data.objects[f"Front_{side}_Steering_Pivot"].rotation_euler.y = 0.42
                bpy.data.objects[f"Rear_{side}_Steering_Pivot"].rotation_euler.y = -0.42
        bpy.context.view_layer.update()

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        center = shared.Vector((0, self.height * 0.46, 0))
        span = max(self.length, self.width, self.height)
        carrier_span = max(self.length, self.carrier_width, self.height)
        views = [
            ("operator-side", (0, self.height * .62, -span * 1.55), carrier_span * 1.08),
            ("front-three-quarter", (span * 1.10, self.height * .88, -span * 1.02), span * 1.18),
            ("rear-three-quarter", (-span * 1.12, self.height * .82, span * .96), carrier_span * 1.18),
            ("elevated-technical", (span * .65, span * 1.45, -span * .95), span * 1.30),
            ("articulation-detail", (span * .82, self.height * .62, -span * .72), carrier_span * .84),
            ("right-side", (0, self.height * .62, span * 1.55), carrier_span * 1.08),
        ]
        paths = []
        for label, location, ortho_scale in views:
            self._set_review_pose(label)
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        self._set_review_pose("neutral")
        return paths

    def required_semantics(self):
        return [*super().required_semantics(), "Rear_Axle_ROOT",
                "Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT",
                "Rear_L_Suspension_ROOT", "Rear_R_Suspension_ROOT",
                "Pickup_Rotor_ROOT", "Netwrap_ROOT", "Quarter_Turn_Ramp_Pivot",
                "Quarter_Turn_Ramp_ROOT", "Quarter_Turn_Cradle_ROOT",
                "Quarter_Turn_Bale_Path_ROOT"]

    def machine_specific_validation_gates(self, contract):
        names = contract["node_names"]
        pickup_bars = [n for n in names if n.startswith("Pickup_Bar_") and n.endswith("_ROOT")]
        double_teeth = [n for n in names if n.startswith("Pickup_DoubleTooth_") and n.endswith("_ROOT")]
        belts = [n for n in names if n.startswith("Chamber_Belt_") and n.endswith("_ROOT")]
        suspensions = [f"{axle}_{side}_Suspension_ROOT" for axle in ("Front", "Rear") for side in ("L", "R")]
        tires = [n for n in names if n.endswith("_Tire")]
        first = bpy.data.objects["Pickup_DoubleTooth_001_ROOT"].matrix_world.translation.z
        last = bpy.data.objects["Pickup_DoubleTooth_013_ROOT"].matrix_world.translation.z
        measured_pickup = abs(last - first)
        tailgate, ramp = bpy.data.objects["Tailgate_ROOT"], bpy.data.objects["Quarter_Turn_Ramp_ROOT"]
        pose_samples = []
        for step in range(7):
            fraction = step / 6
            tailgate.rotation_euler.z = 0.88 * fraction
            ramp.rotation_euler.z = -0.32 * fraction
            bpy.context.view_layer.update()
            bounds = self.mesh_world_bounds()
            pose_samples.append({"fraction": fraction, "min_y_m": round(bounds["min_m"][1], 6),
                                 "height_m": round(bounds["size_m"][1], 6)})
        tailgate.rotation_euler.z = ramp.rotation_euler.z = 0
        bpy.context.view_layer.update()
        materials = sorted({slot.material.name for obj in self.public_objects() if obj.type == "MESH"
                            for slot in obj.material_slots if slot.material is not None})
        return [
            self._gate("published_static_envelope",
                       all(abs(contract["bounds"]["size_m"][i] - expected) <= 0.003
                           for i, expected in enumerate((self.length, self.height, self.width))),
                       {"measured_xyz_m": contract["bounds"]["size_m"],
                        "published_xyz_m": [self.length, self.height, self.width]},
                       ["Machine_Root"], ["public-envelope-x", "public-envelope-y", "public-envelope-z"]),
            self._gate("four_tire_contact", len(tires) == 4 and abs(contract["bounds"]["min_m"][1]) <= 0.003,
                       {"tire_nodes": tires, "ground_y_m": 0.0},
                       ["Front_Axle_ROOT", "Rear_Axle_ROOT", "Running_Gear_ROOT"]),
            self._gate("pickup_width_and_count_cues",
                       len(pickup_bars) == self.PICKUP_BAR_COUNT
                       and len(double_teeth) == self.PICKUP_DOUBLE_TOOTH_COUNT
                       and abs(measured_pickup - self.PICKUP_WIDTH_M) <= 0.003,
                       {"measured_outer_tooth_center_width_m": round(measured_pickup, 6),
                        "tooth_bars": len(pickup_bars), "double_tooth_roots": len(double_teeth)},
                       ["Pickup_ROOT", "Pickup_Rotor_ROOT"],
                       ["pickup-tooth-width", "pickup-bars", "pickup-teeth"]),
            self._gate("pickup_ground_clearance", self._descends("Pickup_Rotor_ROOT", "Pickup_ROOT")
                       and self._descends("Pickup_ROOT", "Pickup_Lift_Pivot"),
                       {"pickup_pivot_world_y_m": 0.54, "rotor_center_world_y_m": 0.64,
                        "gauge_structure_present": "Pickup_Front_Gauge_Roller" in names},
                       ["Pickup_Lift_Pivot", "Pickup_ROOT", "Pickup_Rotor_ROOT"]),
            self._gate("tailgate_chamber_clearance", len(belts) == self.CHAMBER_BELT_COUNT
                       and self._descends("Tailgate_ROOT", "Bale_Chamber_ROOT"),
                       {"visible_chamber_belts": len(belts), "tailgate_endpoint_deg": round(math.degrees(0.88), 3),
                        "sampled_endpoint": pose_samples[-1]},
                       ["Bale_Chamber_ROOT", "Tailgate_Pivot", "Tailgate_ROOT"], ["chamber-belts"]),
            self._gate("quarter_turn_bale_path", self._descends("Quarter_Turn_Cradle_ROOT", "Quarter_Turn_Ramp_ROOT")
                       and all(f"Quarter_Turn_Bale_Path_{i:02d}" in names for i in range(1, 4)),
                       {"schematic_path_segments": 3, "integrated_ramp": "standard selected",
                        "function": "places bale parallel to windrow"},
                       ["Quarter_Turn_Ramp_Pivot", "Quarter_Turn_Ramp_ROOT",
                        "Quarter_Turn_Cradle_ROOT", "Quarter_Turn_Bale_Path_ROOT"],
                       ["quarter-turn-function"]),
            self._gate("suspension_continuity", all(name in names for name in suspensions)
                       and all(f"{axle}_{side}_Suspension_Rod" in names for axle in ("Front", "Rear") for side in ("L", "R")),
                       {"independent_corner_roots": suspensions, "upper_and_lower_a_arms_per_corner": 2,
                        "split_hydraulic_cylinders_per_corner": 1},
                       suspensions, ["suspension-type"]),
            self._gate("zero_turn_wheel_clearance",
                       all(f"{axle}_{side}_Steering_Pivot" in names for axle in ("Front", "Rear") for side in ("L", "R")),
                       {"steering_pivots": [f"{axle}_{side}_Steering_Pivot" for axle in ("Front", "Rear") for side in ("L", "R")],
                        "viewer_countersteer_rad": 0.62, "authority": "reconstructed zero-turn presentation"},
                       ["Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT",
                        "Rear_L_Suspension_ROOT", "Rear_R_Suspension_ROOT"], ["steering-modes"]),
            self._gate("ground_collision", all(sample["min_y_m"] >= -0.005 for sample in pose_samples),
                       {"sampled_tailgate_ramp_min_y_m": [sample["min_y_m"] for sample in pose_samples],
                        "ground_y_m": 0.0},
                       ["Running_Gear_ROOT", "Pickup_ROOT", "Tailgate_ROOT", "Quarter_Turn_Ramp_ROOT"]),
            self._gate("self_collision", len(belts) == 8 and all(sample["min_y_m"] >= -0.005 for sample in pose_samples),
                       {"sampled_pose_count": len(pose_samples), "samples": pose_samples,
                        "scope": "reconstructed tailgate/ramp endpoints; not operating safety authority"},
                       ["Bale_Chamber_ROOT", "Tailgate_ROOT", "Quarter_Turn_Ramp_ROOT", "Pickup_ROOT"]),
            self._gate("swept_volume_collision", len(pose_samples) == 7,
                       {"samples": pose_samples,
                        "method_limit": "seven discrete AABB samples, not a continuous safety solver"},
                       ["Tailgate_ROOT", "Quarter_Turn_Ramp_ROOT", "Bale_Chamber_ROOT"]),
        ]


if __name__ == "__main__":
    VermeerZR5Builder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()
