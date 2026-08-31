#!/usr/bin/env python3
"""Build one deterministic, neutral fleet technical structural study.

Run with Blender 5.1 or newer:

  blender --factory-startup --background --python scripts/fleet/build_machine.py -- \
    --design machines/<id>/source/design.json --output-dir machines/<id>

The generated geometry is independently authored and deliberately generic. It
is not manufacturer CAD, engineering authority, safety guidance, a digital
twin, or proof of machine-specific kinematics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


SCRIPT_PATH = Path(__file__).resolve()
if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))

from design_contract import DesignContractError, load_design  # noqa: E402


# Complexity metrics are integrity floors, never fidelity scores.  Earlier
# revisions padded generic archetypes to 190 meshes with cosmetic fasteners;
# that made an intentionally low-detail reskin look "complete".  Machine
# specificity and component coverage are now separate fail-closed gates, while
# these deliberately modest floors catch only empty or broken exports.
MINIMUMS = {"nodes": 80, "mesh_nodes": 60, "triangles": 5_000, "renders": 6}
ROOT_NAME = "Machine_Root"
AUTHORITY_BOUNDARY = (
    "Independently authored neutral technical structural study. Not manufacturer CAD, "
    "engineering authority, load guidance, operator training, safety guidance, a digital "
    "twin, or a mechanically validated candidate."
)
HIDDEN_GEOMETRY_BOUNDARY = (
    "All hidden structure, pivot centers, anchors, linkage proportions, underbody volumes, "
    "and internal geometry are reconstructed visualization choices unless a design record "
    "explicitly identifies a manufacturer-published envelope constraint."
)

PALETTES = {
    "oxide": (0.58, 0.17, 0.065),
    "sand": (0.52, 0.39, 0.18),
    "sage": (0.23, 0.34, 0.20),
    "slate": (0.18, 0.25, 0.31),
    "amber": (0.68, 0.37, 0.06),
}

ARCHETYPE_SEMANTICS = {
    "wheeled_tractor": [
        "Front_Axle_Oscillation_Pivot", "Front_Axle_ROOT", "Steering_L_Pivot",
        "Steering_R_Pivot", "Rear_Hitch_Pivot", "Rear_Hitch_ROOT", "PTO_ROOT",
    ],
    "tracked_tractor": [
        "Chassis_Yaw_Pivot", "Front_Frame_ROOT", "Rear_Frame_ROOT", "Track_FL_ROOT",
        "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT", "Drawbar_Pivot",
    ],
    "twin_track_tractor": [
        "Track_L_ROOT", "Track_R_ROOT", "SmartRide_Level_ROOT", "Cab_Suspension_ROOT",
        "Rear_Hitch_Pivot", "Rear_Hitch_ROOT", "Drawbar_Pivot",
    ],
    "combine": [
        "Header_Lift_Pivot", "Header_ROOT", "Reel_Pivot", "Reel_ROOT",
        "Feederhouse_ROOT", "Unloader_Swing_Pivot", "Unloader_ROOT",
    ],
    "forage_harvester": [
        "Header_Lift_Pivot", "Header_ROOT", "Feedroll_ROOT", "Spout_Yaw_Pivot",
        "Spout_ROOT", "Spout_Tip_Pivot", "Spout_Tip_ROOT",
    ],
    "high_clearance_sprayer": [
        "Front_Axle_Oscillation_Pivot", "Front_Axle_ROOT", "Boom_Center_ROOT",
        "Boom_L_Fold_Pivot", "Boom_L_ROOT", "Boom_R_Fold_Pivot", "Boom_R_ROOT",
    ],
    "self_propelled_mower": [
        "Header_Lift_Pivot", "Header_ROOT", "Conditioner_ROOT", "Deck_L_Fold_Pivot",
        "Deck_L_ROOT", "Deck_R_Fold_Pivot", "Deck_R_ROOT",
    ],
    "square_baler": [
        "Drawbar_Yaw_Pivot", "Drawbar_ROOT", "Pickup_Lift_Pivot", "Pickup_ROOT",
        "Plunger_ROOT", "Bale_Chute_Pivot", "Bale_Chute_ROOT",
    ],
    "self_propelled_round_baler": [
        "Front_Axle_Oscillation_Pivot", "Front_Axle_ROOT", "Pickup_Lift_Pivot",
        "Pickup_ROOT", "Bale_Chamber_ROOT", "Tailgate_Pivot", "Tailgate_ROOT",
    ],
    "articulated_hauler": [
        "Chassis_Yaw_Pivot", "Front_Frame_ROOT", "Rear_Frame_ROOT", "Bed_Tip_Pivot",
        "Bed_ROOT",
    ],
    "excavator": [
        "Track_L_ROOT", "Track_R_ROOT", "Upper_Swing_Pivot", "Upper_ROOT",
        "Boom_Pivot", "Boom_ROOT", "Stick_Pivot", "Stick_ROOT", "Bucket_Pivot",
        "Bucket_ROOT",
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, base: Path) -> dict:
    return {
        "path": os.path.relpath(path, base).replace(os.sep, "/"),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


class FleetBuilder:
    def __init__(self, design: dict, design_path: Path, output_dir: Path):
        self.design = design
        self.design_path = design_path.resolve()
        self.output_dir = output_dir.resolve()
        self.machine_id = design["machine_id"]
        self.configuration_id = design["configuration_id"]
        self.archetype = design["archetype"]
        self.length = design["dimensions_m"]["length"]
        self.width = design["dimensions_m"]["width"]
        self.height = design["dimensions_m"]["height"]
        carrier = design.get("carrier_dimensions_m")
        if carrier is None:
            legacy_carrier = design.get("reconstructed_values", {}).get("carrier_display_envelope_m")
            if isinstance(legacy_carrier, list) and len(legacy_carrier) == 3 and all(
                isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
                for value in legacy_carrier
            ):
                carrier = {"length": float(legacy_carrier[0]), "width": float(legacy_carrier[1]), "height": float(legacy_carrier[2])}
        carrier = carrier or design["dimensions_m"]
        if any(carrier[axis] > design["dimensions_m"][axis] + 1e-9 for axis in ("length", "width", "height")):
            raise DesignContractError("carrier envelope cannot exceed the retained visible envelope")
        self.carrier_length = float(carrier["length"])
        self.carrier_width = float(carrier["width"])
        self.carrier_height = float(carrier["height"])
        self.attachment_span = float(design.get("attachment_span_m", self.width))
        self.blend_path = self.output_dir / "source" / "blender" / f"{self.machine_id}-structural-study.blend"
        self.wrapper_path = self.output_dir / "source" / "blender" / f"build_{self.machine_id.replace('-', '_')}.py"
        self.glb_path = self.output_dir / "assets" / f"{self.machine_id}-structural-study.glb"
        self.render_dir = self.output_dir / "review" / "renders"
        self.receipt_path = self.output_dir / "production" / "asset-receipt.json"
        self.validation_path = self.output_dir / "production" / "validation.json"
        self.materials: dict[str, bpy.types.Material] = {}
        self.root: bpy.types.Object | None = None
        self.fixed_root: bpy.types.Object | None = None
        self.running_root: bpy.types.Object | None = None
        self.hydraulics_root: bpy.types.Object | None = None
        self.detail_root: bpy.types.Object | None = None
        self.semantic_names: set[str] = set()
        self.render_objects: list[bpy.types.Object] = []

    def reset_scene(self) -> None:
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for datablocks in (
            bpy.data.meshes,
            bpy.data.curves,
            bpy.data.materials,
            bpy.data.cameras,
            bpy.data.lights,
        ):
            for block in list(datablocks):
                if block.users == 0:
                    datablocks.remove(block)
        scene = bpy.context.scene
        bpy.context.preferences.filepaths.save_version = 0
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1.0
        scene.unit_settings.length_unit = "METERS"
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 640
        scene.render.resolution_y = 480
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "8"
        scene.render.film_transparent = False
        scene.render.use_file_extension = True
        scene.render.image_settings.compression = 25
        scene.world.color = (0.012, 0.017, 0.023)
        scene["exo_machine_id"] = self.machine_id
        scene["exo_configuration_id"] = self.configuration_id
        scene["exo_archetype"] = self.archetype
        scene["exo_candidate_class"] = "technical_structural_study"
        scene["exo_axes"] = "+X forward, +Y up, +Z machine right"
        scene["exo_authority_boundary"] = AUTHORITY_BOUNDARY
        scene["exo_hidden_geometry_boundary"] = HIDDEN_GEOMETRY_BOUNDARY

    def material(self, name: str, color, metallic=0.0, roughness=0.5, alpha=1.0):
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*color, alpha)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, alpha)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if alpha < 1.0:
            mat.surface_render_method = "DITHERED"
        mat["exo_rights"] = "neutral_unbranded"
        return mat

    def create_materials(self) -> None:
        body = PALETTES[self.design["palette"]]
        self.materials = {
            "body": self.material("Neutral_Body", body, 0.18, 0.34),
            "body_dark": self.material("Neutral_Body_Shadow", tuple(v * 0.52 for v in body), 0.22, 0.39),
            "graphite": self.material("Neutral_Graphite", (0.035, 0.045, 0.055), 0.56, 0.33),
            "steel": self.material("Neutral_Steel", (0.28, 0.31, 0.34), 0.82, 0.24),
            "rod": self.material("Neutral_Rod", (0.58, 0.62, 0.66), 0.94, 0.13),
            "rubber": self.material("Neutral_Rubber", (0.018, 0.022, 0.025), 0.05, 0.78),
            "glass": self.material("Neutral_Glass", (0.10, 0.22, 0.29), 0.12, 0.18, 0.58),
            "warning": self.material("Neutral_Visibility_Cue", (0.90, 0.53, 0.07), 0.08, 0.38),
        }

    def tag(self, obj, role="geometry", authority="reconstructed", export=True):
        obj["exo_role"] = role
        obj["exo_authority"] = authority
        obj["exo_export"] = bool(export)
        return obj

    def empty(self, name, location=(0, 0, 0), parent=None, role="motion_root"):
        obj = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        obj.empty_display_type = "PLAIN_AXES"
        obj.empty_display_size = max(0.08, min(self.length, self.width, self.height) * 0.035)
        if parent is not None:
            obj.parent = parent
        self.tag(obj, role=role)
        self.semantic_names.add(name)
        return obj

    def box(self, name, location, dimensions, material, parent=None, rotation=(0, 0, 0), role="geometry", bevel=0.018):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        if bevel > 0:
            modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
            modifier.width = min(bevel, min(dimensions) * 0.22)
            modifier.segments = 2
        return self.tag(obj, role=role)

    def cylinder(self, name, location, radius, depth, material, parent=None, vertices=16, rotation=(0, 0, 0), role="geometry"):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation
        )
        obj = bpy.context.object
        obj.name = name
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
        modifier.width = min(radius * 0.10, depth * 0.08, 0.018)
        modifier.segments = 2
        return self.tag(obj, role=role)

    def cone(self, name, location, radius1, radius2, depth, material, parent=None, vertices=20, rotation=(0, 0, 0), role="geometry"):
        bpy.ops.mesh.primitive_cone_add(
            vertices=vertices, radius1=radius1, radius2=radius2, depth=depth,
            location=location, rotation=rotation,
        )
        obj = bpy.context.object
        obj.name = name
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role=role)

    def side_profile(self, name, points_xy, thickness, material, parent=None, z_center=0.0, role="geometry"):
        count = len(points_xy)
        vertices = [(x, y, z_center - thickness / 2) for x, y in points_xy]
        vertices += [(x, y, z_center + thickness / 2) for x, y in points_xy]
        faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, count * 2))]
        for index in range(count):
            nxt = (index + 1) % count
            faces.append((index, nxt, count + nxt, count + index))
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
        modifier.width = min(0.018, thickness * 0.12)
        modifier.segments = 2
        return self.tag(obj, role=role)

    def pipe_between(self, name, start, end, radius, material, parent=None, role="hydraulic"):
        start_v, end_v = Vector(start), Vector(end)
        vector = end_v - start_v
        if vector.length <= 1e-8:
            raise RuntimeError(f"zero-length pipe requested for {name}")
        obj = self.cylinder(name, (start_v + end_v) / 2, radius, vector.length, material, None, 16, role=role)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(vector.normalized())
        if parent is not None:
            obj.parent = parent
        return obj

    def wheel_tire(self, name, radius, half_width, material, parent):
        major_segments, minor_segments = 24, 8
        major = radius * 0.80
        radial = radius * 0.20
        vertices = []
        faces = []
        for major_index in range(major_segments):
            u = math.tau * major_index / major_segments
            for minor_index in range(minor_segments):
                v = math.tau * minor_index / minor_segments
                ring = major + radial * math.cos(v)
                vertices.append((ring * math.cos(u), ring * math.sin(u), half_width * math.sin(v)))
        for major_index in range(major_segments):
            nxt_major = (major_index + 1) % major_segments
            for minor_index in range(minor_segments):
                nxt_minor = (minor_index + 1) % minor_segments
                a = major_index * minor_segments + minor_index
                b = nxt_major * minor_segments + minor_index
                c = nxt_major * minor_segments + nxt_minor
                d = major_index * minor_segments + nxt_minor
                faces.append((a, b, c, d))
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role="tire_carcass")

    def add_wheel(self, prefix, center, radius, width, parent, tread_count=16):
        pivot = self.empty(f"{prefix}_Wheel_Pivot", center, parent, role="wheel_pivot")
        wheel_root = self.empty(f"{prefix}_Wheel_ROOT", (0, 0, 0), pivot, role="wheel_root")
        self.wheel_tire(f"{prefix}_Tire", radius, width / 2, self.materials["rubber"], wheel_root)
        self.cylinder(f"{prefix}_Rim", (0, 0, 0), radius * 0.48, width * 0.82, self.materials["steel"], wheel_root, vertices=20)
        self.cylinder(f"{prefix}_Hub", (0, 0, 0), radius * 0.18, width * 0.90, self.materials["graphite"], wheel_root, vertices=16)
        for index in range(tread_count):
            angle = math.tau * index / tread_count
            self.box(
                f"{prefix}_Tread_{index + 1:02d}",
                (math.cos(angle) * radius * 0.94, math.sin(angle) * radius * 0.94, 0),
                (radius * 0.10, radius * 0.15, width * 0.96),
                self.materials["rubber"], wheel_root, rotation=(0, 0, angle),
                role="tire_tread", bevel=radius * 0.015,
            )
        for index in range(8):
            angle = math.tau * index / 8
            self.cylinder(
                f"{prefix}_Lug_{index + 1:02d}",
                (math.cos(angle) * radius * 0.29, math.sin(angle) * radius * 0.29, -width * 0.43),
                radius * 0.027, width * 0.055, self.materials["steel"], wheel_root, vertices=12,
                role="wheel_fastener",
            )
        return wheel_root

    def add_track_pod(self, prefix, length, height, width, center, parent, pads=28, rollers=5):
        root = self.empty(f"{prefix}_ROOT", center, parent, role="track_root")
        provisional_pitch = (2 * length + math.pi * height) / pads
        pad_length = provisional_pitch * 0.74
        pad_thickness = height * 0.052
        radius = max(height * 0.22, height / 2 - pad_thickness / 2)
        straight = max(length - 2 * radius - pad_length, length * 0.32)
        perimeter = 2 * straight + 2 * math.pi * radius
        for index in range(pads):
            distance = (index + 0.5) * perimeter / pads
            if distance < straight:
                x, y, tangent = straight / 2 - distance, -radius, math.pi
            elif distance < straight + math.pi * radius:
                theta = -math.pi / 2 - (distance - straight) / radius
                x, y = -straight / 2 + radius * math.cos(theta), radius * math.sin(theta)
                tangent = theta - math.pi / 2
            elif distance < 2 * straight + math.pi * radius:
                d = distance - straight - math.pi * radius
                x, y, tangent = -straight / 2 + d, radius, 0
            else:
                theta = math.pi / 2 - (distance - 2 * straight - math.pi * radius) / radius
                x, y = straight / 2 + radius * math.cos(theta), radius * math.sin(theta)
                tangent = theta - math.pi / 2
            self.box(
                f"{prefix}_Pad_{index + 1:02d}", (x, y + height / 2, 0),
                (min(pad_length, perimeter / pads * 0.78), pad_thickness, width), self.materials["rubber"], root,
                rotation=(0, 0, tangent), role="track_pad", bevel=height * 0.008,
            )
        for label, x in (("Rear", -straight / 2), ("Front", straight / 2)):
            self.cylinder(
                f"{prefix}_{label}_Wheel", (x, height / 2, 0), radius * 0.84, width * 0.72,
                self.materials["steel"], root, vertices=20, role="track_wheel",
            )
        for index in range(rollers):
            x = 0 if rollers == 1 else -straight * 0.38 + index * (straight * 0.76 / (rollers - 1))
            self.cylinder(
                f"{prefix}_Roller_{index + 1:02d}", (x, height * 0.31, 0), radius * 0.30,
                width * 0.66, self.materials["graphite"], root, vertices=16, role="track_roller",
            )
        self.box(f"{prefix}_Frame", (0, height * 0.50, 0), (straight, height * 0.22, width * 0.55), self.materials["graphite"], root, role="track_frame")
        return root

    def add_cab(self, center_x, floor_y, cab_length, cab_width, cab_height, parent):
        cab = self.empty("Operator_Station_ROOT", (center_x, floor_y, 0), parent, role="operator_station")
        self.box("Cab_Floor", (0, 0.06 * cab_height, 0), (cab_length, 0.12 * cab_height, cab_width), self.materials["graphite"], cab, role="cab_structure")
        self.box("Cab_Roof", (0, cab_height - 0.055 * cab_height, 0), (cab_length * 0.96, 0.11 * cab_height, cab_width), self.materials["body"], cab, role="cab_structure")
        self.box("Cab_Front_Glass", (cab_length * 0.44, cab_height * 0.55, 0), (cab_length * 0.07, cab_height * 0.72, cab_width * 0.88), self.materials["glass"], cab, role="glazing")
        self.box("Cab_Rear_Glass", (-cab_length * 0.44, cab_height * 0.55, 0), (cab_length * 0.07, cab_height * 0.62, cab_width * 0.82), self.materials["glass"], cab, role="glazing")
        for side, z in (("L", -cab_width * 0.47), ("R", cab_width * 0.47)):
            self.box(f"Cab_{side}_Glass", (0, cab_height * 0.57, z), (cab_length * 0.76, cab_height * 0.60, cab_width * 0.045), self.materials["glass"], cab, role="glazing")
            for x in (-cab_length * 0.44, cab_length * 0.44):
                self.box(f"Cab_{side}_Post_{'F' if x > 0 else 'R'}", (x, cab_height * 0.52, z), (cab_length * 0.07, cab_height * 0.80, cab_width * 0.07), self.materials["graphite"], cab, role="cab_structure")
        self.box("Operator_Seat", (-cab_length * 0.08, cab_height * 0.30, 0), (cab_length * 0.32, cab_height * 0.38, cab_width * 0.42), self.materials["graphite"], cab, role="operator_cue")
        return cab

    def add_service_detail_density(self):
        """Do not synthesize detail merely to satisfy a mesh-count threshold.

        Machine-local builders may author evidence-supported fasteners, guards,
        treads, hoses, and service structure where those parts improve technical
        readability.  The shared generator deliberately contributes no padding.
        """
        return

    def build_common_roots(self):
        self.root = self.empty(ROOT_NAME, role="identity_root")
        self.fixed_root = self.empty("Fixed_Structure_ROOT", parent=self.root, role="fixed_structure_root")
        self.running_root = self.empty("Running_Gear_ROOT", parent=self.root, role="running_gear_root")
        self.hydraulics_root = self.empty("Hydraulics_ROOT", parent=self.root, role="hydraulics_root")
        self.detail_root = self.empty("Service_Detail_ROOT", parent=self.fixed_root, role="visible_detail_root")
        self.empty("Powertrain_ROOT", parent=self.fixed_root, role="powertrain_root")

    def build_wheeled_tractor(self):
        L, W, H = self.length, self.width, self.height
        rear_r = min(H * 0.29, L * 0.145)
        front_r = rear_r * 0.72
        rear_x, front_x = -L / 2 + rear_r, L / 2 - front_r
        rear_w, front_w = W * 0.20, W * 0.15
        self.box("Tractor_Main_Frame", (0, rear_r * 0.95, 0), (L * 0.58, H * 0.13, W * 0.42), self.materials["graphite"], self.fixed_root, role="chassis")
        self.box("Engine_Hood", (L * 0.20, H * 0.49, 0), (L * 0.34, H * 0.35, W * 0.55), self.materials["body"], self.fixed_root, role="engine_house")
        for index in range(9):
            self.box(f"Hood_Vent_{index + 1:02d}", (L * 0.25, H * (0.37 + index * 0.018), -W * 0.282), (L * 0.19, H * 0.008, W * 0.018), self.materials["graphite"], self.fixed_root, role="vent")
        cab_floor = rear_r * 0.72
        self.add_cab(-L * 0.13, cab_floor, L * 0.23, W * 0.52, H - cab_floor, self.fixed_root)
        front_axle_pivot = self.empty("Front_Axle_Oscillation_Pivot", (front_x, front_r, 0), self.running_root, role="pivot")
        front_axle = self.empty("Front_Axle_ROOT", parent=front_axle_pivot, role="motion_root")
        self.box("Front_Axle_Beam", (0, 0, 0), (front_r * 0.35, front_r * 0.20, W - front_w), self.materials["steel"], front_axle, role="axle")
        for side, z in (("L", -(W / 2 - front_w / 2)), ("R", W / 2 - front_w / 2)):
            steering = self.empty(f"Steering_{side}_Pivot", (0, 0, z), front_axle, role="steering_pivot")
            self.add_wheel(f"Front_{side}", (0, 0, 0), front_r, front_w, steering)
        for side, z in (("L", -(W / 2 - rear_w / 2)), ("R", W / 2 - rear_w / 2)):
            self.add_wheel(f"Rear_{side}", (rear_x, rear_r, z), rear_r, rear_w, self.running_root, 18)
        hitch = self.empty("Rear_Hitch_Pivot", (-L * 0.40, H * 0.24, 0), self.fixed_root, role="pivot")
        hitch_root = self.empty("Rear_Hitch_ROOT", parent=hitch, role="motion_root")
        self.box("Rear_Hitch_Drawbar", (-L * 0.02, 0, 0), (L * 0.12, H * 0.055, W * 0.09), self.materials["steel"], hitch_root, role="hitch")
        for side, z in (("L", -W * 0.09), ("R", W * 0.09)):
            self.pipe_between(
                f"Rear_Hitch_{side}_Lower_Link", (-L * 0.01, 0, z), (L * 0.055, H * 0.055, z),
                H * 0.012, self.materials["steel"], hitch_root, role="hitch_link",
            )
        self.pipe_between(
            "Rear_Hitch_Top_Link", (0, H * 0.07, 0), (L * 0.045, H * 0.13, 0),
            H * 0.011, self.materials["steel"], hitch_root, role="hitch_link",
        )
        pto = self.empty("PTO_ROOT", (-L * 0.34, H * 0.30, 0), self.fixed_root, role="rotary_root")
        self.cylinder("PTO_Shaft", (0, 0, 0), H * 0.025, L * 0.055, self.materials["steel"], pto, vertices=16, rotation=(0, math.pi / 2, 0), role="pto_shaft")
        self.cylinder("PTO_Guard", (L * 0.012, 0, 0), H * 0.043, L * 0.026, self.materials["warning"], pto, vertices=20, rotation=(0, math.pi / 2, 0), role="pto_guard")

    def build_tracked_tractor(self):
        L, W, H = self.length, self.width, self.height
        yaw = self.empty("Chassis_Yaw_Pivot", (0, H * 0.34, 0), self.root, role="pivot")
        front = self.empty("Front_Frame_ROOT", (0, -H * 0.34, 0), yaw, role="motion_root")
        rear = self.empty("Rear_Frame_ROOT", parent=self.root, role="motion_root")
        self.box("Front_Chassis", (L * 0.17, H * 0.37, 0), (L * 0.42, H * 0.16, W * 0.46), self.materials["graphite"], front, role="chassis")
        self.box("Rear_Chassis", (-L * 0.22, H * 0.37, 0), (L * 0.36, H * 0.16, W * 0.46), self.materials["graphite"], rear, role="chassis")
        pod_l, pod_h, pod_w = L * 0.24, H * 0.31, W * 0.22
        for frame, x, axle in ((front, L * 0.25, "F"), (rear, -L * 0.25, "R")):
            for side, z in (("L", -(W / 2 - pod_w / 2)), ("R", W / 2 - pod_w / 2)):
                self.add_track_pod(f"Track_{axle}{side}", pod_l, pod_h, pod_w, (x, 0, z), frame, pads=22)
        self.box("Engine_House", (-L * 0.12, H * 0.59, 0), (L * 0.30, H * 0.34, W * 0.48), self.materials["body"], self.fixed_root, role="engine_house")
        self.add_cab(L * 0.13, H * 0.43, L * 0.21, W * 0.48, H * 0.57, self.fixed_root)
        drawbar = self.empty("Drawbar_Pivot", (-L * 0.42, H * 0.24, 0), rear, role="pivot")
        self.box("Drawbar", (0, 0, 0), (L * 0.14, H * 0.055, W * 0.09), self.materials["steel"], drawbar, role="drawbar")

    def build_twin_track_tractor(self):
        L, W, H = self.length, self.carrier_width, self.height
        level_root = self.empty("SmartRide_Level_ROOT", (0, 0, 0), self.running_root, role="suspension_motion_root")
        track_length = L * 0.57
        track_height = H * 0.30
        track_width = W * 0.27
        for side, z in (("L", -(W / 2 - track_width / 2)), ("R", W / 2 - track_width / 2)):
            self.add_track_pod(f"Track_{side}", track_length, track_height, track_width, (-L * 0.05, 0, z), level_root, pads=38, rollers=4)
        self.box("Rigid_Main_Frame", (-L * 0.02, H * 0.36, 0), (L * 0.66, H * 0.14, W * 0.48), self.materials["graphite"], self.fixed_root, role="chassis")
        self.box("Engine_House", (L * 0.18, H * 0.55, 0), (L * 0.34, H * 0.34, W * 0.54), self.materials["body"], self.fixed_root, role="engine_house")
        cab_suspension = self.empty("Cab_Suspension_ROOT", (-L * 0.16, H * 0.39, 0), self.fixed_root, role="suspension_motion_root")
        self.add_cab(0, 0, L * 0.22, W * 0.52, H * 0.61, cab_suspension)
        hitch = self.empty("Rear_Hitch_Pivot", (-L * 0.40, H * 0.24, 0), self.fixed_root, role="pivot")
        hitch_root = self.empty("Rear_Hitch_ROOT", parent=hitch, role="motion_root")
        self.box("Rear_Hitch_Links", (-L * 0.01, 0, 0), (L * 0.14, H * 0.06, W * 0.16), self.materials["steel"], hitch_root, role="hitch")
        drawbar = self.empty("Drawbar_Pivot", (-L * 0.43, H * 0.17, 0), self.fixed_root, role="pivot")
        self.box("Drawbar", (0, 0, 0), (L * 0.12, H * 0.045, W * 0.08), self.materials["steel"], drawbar, role="drawbar")

    def add_four_wheel_running_gear(self, rear_radius, front_radius, rear_x=None, front_x=None, narrow=False, running_width=None):
        L, W = self.length, running_width or self.carrier_width
        rear_x = -L / 2 + rear_radius if rear_x is None else rear_x
        front_x = L / 2 - front_radius if front_x is None else front_x
        rear_w = W * (0.095 if narrow else 0.16)
        front_w = W * (0.085 if narrow else 0.13)
        for prefix, x, radius, tire_w in (("Rear", rear_x, rear_radius, rear_w), ("Front", front_x, front_radius, front_w)):
            for side, z in (("L", -(W / 2 - tire_w / 2)), ("R", W / 2 - tire_w / 2)):
                self.add_wheel(f"{prefix}_{side}", (x, radius, z), radius, tire_w, self.running_root, 14)

    def build_combine(self):
        L, W, H = self.length, self.carrier_width, self.height
        span = self.attachment_span
        rear_r, front_r = H * 0.16, H * 0.235
        tracked_front = self.design.get("tracked_front", False) or self.design.get("reconstructed_values", {}).get("running_gear") in {"front_terra_trac_rear_wheels", "front_tracks_rear_wheels"}
        if tracked_front:
            rear_w = W * 0.13
            for side, z in (("L", -(W / 2 - rear_w / 2)), ("R", W / 2 - rear_w / 2)):
                self.add_wheel(f"Rear_{side}", (-L * 0.29, rear_r, z), rear_r, rear_w, self.running_root, 14)
            track_width = W * 0.25
            for side, z in (("L", -(W / 2 - track_width / 2)), ("R", W / 2 - track_width / 2)):
                self.add_track_pod(f"Track_{side}", L * 0.25, H * 0.30, track_width, (L * 0.22, 0, z), self.running_root, pads=28)
        else:
            self.add_four_wheel_running_gear(rear_r, front_r, rear_x=-L * 0.29, front_x=L * 0.23, running_width=W)
        self.box("Separator_Main_House", (-L * 0.06, H * 0.53, 0), (L * 0.50, H * 0.48, W * 0.68), self.materials["body"], self.fixed_root, role="separator_house")
        self.box("Grain_Tank", (-L * 0.08, H * 0.79, 0), (L * 0.33, H * 0.30, W * 0.62), self.materials["body_dark"], self.fixed_root, role="grain_tank")
        self.add_cab(L * 0.24, H * 0.45, L * 0.18, W * 0.58, H * 0.55, self.fixed_root)
        feeder = self.empty("Feederhouse_ROOT", (L * 0.26, H * 0.34, 0), self.fixed_root, role="motion_root")
        self.side_profile("Feederhouse", [(0,-H*.08),(L*.22,-H*.18),(L*.23,H*.08),(0,H*.12)], W*.32, self.materials["body_dark"], feeder, role="feederhouse")
        header_pivot = self.empty("Header_Lift_Pivot", (L * 0.16, -H * 0.11, 0), feeder, role="pivot")
        header = self.empty("Header_ROOT", parent=header_pivot, role="motion_root")
        self.box("Header_Backbone", (L * 0.03, 0, 0), (L * 0.14, H * 0.13, span), self.materials["body"], header, role="header")
        self.box("Cutterbar", (L * 0.09, -H * 0.07, 0), (L * 0.06, H * 0.035, span * 0.98), self.materials["steel"], header, role="cutterbar")
        reel_pivot = self.empty("Reel_Pivot", (L * 0.04, H * 0.12, 0), header, role="pivot")
        reel = self.empty("Reel_ROOT", parent=reel_pivot, role="rotary_root")
        self.cylinder("Reel_Axle", (0, 0, 0), H * 0.035, span * 0.92, self.materials["steel"], reel, vertices=16, role="reel")
        for index in range(6):
            angle = math.tau * index / 6
            self.box(f"Reel_Bat_{index + 1}", (math.cos(angle)*H*.12, math.sin(angle)*H*.12, 0), (H*.035,H*.035,span*.90), self.materials["warning"], reel, role="reel_bat")
        unload_pivot = self.empty("Unloader_Swing_Pivot", (-L * 0.12, H * 0.82, W * 0.28), self.fixed_root, role="pivot")
        unload = self.empty("Unloader_ROOT", parent=unload_pivot, role="motion_root")
        self.cylinder("Unloader_Base_Collar", (0,0,0), H*.060, H*.085, self.materials["body_dark"], unload, vertices=20, role="unloader")
        self.pipe_between("Unloader_Auger", (0,0,0), (-L*.34,-H*.04,0), H*.035, self.materials["body"], unload, role="unloader")

    def build_forage_harvester(self):
        L, W, H = self.length, self.carrier_width, self.height
        span = self.attachment_span
        rear_r, front_r = H * 0.17, H * 0.22
        self.add_four_wheel_running_gear(rear_r, front_r, rear_x=-L*.27, front_x=L*.24, running_width=W)
        self.box("Processor_House", (-L * 0.06, H * 0.53, 0), (L * 0.52, H * 0.48, W * 0.68), self.materials["body"], self.fixed_root, role="processor_house")
        self.add_cab(L * 0.23, H * 0.43, L * 0.19, W * 0.58, H * 0.57, self.fixed_root)
        header_pivot = self.empty("Header_Lift_Pivot", (L*.36,H*.27,0), self.fixed_root, role="pivot")
        header = self.empty("Header_ROOT", parent=header_pivot, role="motion_root")
        self.side_profile("Header_Feeder_Bridge",[(-L*.03,H*.04),(L*.09,H*.02),(L*.09,-H*.07),(-L*.03,-H*.03)],W*.34,self.materials["body"],header,role="feederhouse")
        self.box("Crop_Header", (L*.08,-H*.06,0), (L*.18,H*.15,span), self.materials["body_dark"], header, role="header")
        feed = self.empty("Feedroll_ROOT", (L*.06,0,0), header, role="rotary_root")
        for index in range(4):
            self.cylinder(f"Feedroll_{index+1}", (index*L*.028,-H*.02,0), H*.045,span*.72,self.materials["steel"],feed,vertices=16,role="feedroll")
        yaw = self.empty("Spout_Yaw_Pivot", (-L*.08,H*.72,0), self.fixed_root, role="pivot")
        spout = self.empty("Spout_ROOT", parent=yaw, role="motion_root")
        self.pipe_between("Spout_Riser", (0,0,0), (0,H*.20,0), H*.045,self.materials["body_dark"],spout,role="spout")
        tip_pivot = self.empty("Spout_Tip_Pivot", (0,H*.20,0), spout, role="pivot")
        tip = self.empty("Spout_Tip_ROOT", parent=tip_pivot, role="motion_root")
        self.pipe_between("Spout_Tip", (0,0,0), (L*.28,H*.05,0), H*.042,self.materials["body"],tip,role="spout")

    def build_high_clearance_sprayer(self):
        L, W, H = self.length, self.carrier_width, self.height
        span = self.attachment_span
        radius = min(H*.20,L*.105)
        self.add_four_wheel_running_gear(radius, radius, rear_x=-L*.29, front_x=L*.29, narrow=True, running_width=W)
        axle_pivot = self.empty("Front_Axle_Oscillation_Pivot", (L*.29,radius,0), self.running_root, role="pivot")
        self.empty("Front_Axle_ROOT", parent=axle_pivot, role="motion_root")
        clearance = H * .36
        self.box("High_Clearance_Frame", (0,clearance,0),(L*.61,H*.09,W*.43),self.materials["graphite"],self.fixed_root,role="chassis")
        self.cylinder("Solution_Tank", (-L*.08,H*.57,0), H*.16,W*.48,self.materials["body"],self.fixed_root,vertices=28,rotation=(math.pi/2,0,0),role="solution_tank")
        self.add_cab(L*.22,H*.45,L*.18,W*.46,H*.55,self.fixed_root)
        boom_center = self.empty("Boom_Center_ROOT", (-L*.31,H*.58,0),self.fixed_root,role="motion_root")
        self.box("Boom_Center_Truss", (0,0,0),(L*.09,H*.06,W*.42),self.materials["steel"],boom_center,role="spray_boom")
        for side, sign in (("L",-1),("R",1)):
            pivot=self.empty(f"Boom_{side}_Fold_Pivot",(0,0,sign*W*.20),boom_center,role="pivot")
            root=self.empty(f"Boom_{side}_ROOT",parent=pivot,role="motion_root")
            wing_span = span / 2 - W * .20
            self.box(f"Boom_{side}_Inner",(0,0,sign*wing_span/2),(H*.05,H*.045,wing_span),self.materials["steel"],root,role="spray_boom")
            nozzle_count=max(8,min(36,int(wing_span/.65)))
            for index in range(nozzle_count):
                z=sign*wing_span*(index+.5)/nozzle_count
                self.cylinder(f"Boom_{side}_Nozzle_{index+1:02d}",(0,-H*.035,z),H*.009,H*.028,self.materials["warning"],root,vertices=10,rotation=(math.pi/2,0,0),role="spray_nozzle")

    def build_self_propelled_mower(self):
        L,W,H=self.length,self.carrier_width,self.height
        span=self.attachment_span
        r=min(H*.18,L*.105)
        self.add_four_wheel_running_gear(r*.85,r,rear_x=-L*.28,front_x=L*.25,running_width=W)
        self.box("Mower_Power_Module",(-L*.08,H*.48,0),(L*.43,H*.38,W*.60),self.materials["body"],self.fixed_root,role="power_module")
        self.add_cab(L*.16,H*.40,L*.19,W*.52,H*.60,self.fixed_root)
        pivot=self.empty("Header_Lift_Pivot",(L*.31,H*.25,0),self.fixed_root,role="pivot")
        header=self.empty("Header_ROOT",parent=pivot,role="motion_root")
        self.box("Mower_Header",(L*.08,-H*.07,0),(L*.20,H*.15,span),self.materials["body_dark"],header,role="mower_header")
        conditioner=self.empty("Conditioner_ROOT",(L*.07,-H*.02,0),header,role="rotary_root")
        self.cylinder("Conditioner_Roll",(0,0,0),H*.045,span*.74,self.materials["steel"],conditioner,vertices=20,role="conditioner")
        for side,sign in (("L",-1),("R",1)):
            wing=self.empty(f"Deck_{side}_Fold_Pivot",(0,0,sign*W*.32),header,role="pivot")
            wing_root=self.empty(f"Deck_{side}_ROOT",parent=wing,role="motion_root")
            self.box(f"Deck_{side}_Wing",(0,0,sign*W*.16),(L*.16,H*.10,W*.31),self.materials["body"],wing_root,role="mower_deck")

    def build_square_baler(self):
        L,W,H=self.length,self.width,self.height
        r=min(H*.16,L*.10)
        for side,z in (("L",-(W/2-W*.09)),("R",W/2-W*.09)):
            self.add_wheel(f"Baler_{side}",(-L*.13,r,z),r,W*.18,self.running_root,14)
        self.box("Bale_Chamber",(-L*.08,H*.49,0),(L*.58,H*.62,W*.78),self.materials["body"],self.fixed_root,role="bale_chamber")
        drawbar_pivot=self.empty("Drawbar_Yaw_Pivot",(L*.18,H*.18,0),self.fixed_root,role="pivot")
        drawbar=self.empty("Drawbar_ROOT",parent=drawbar_pivot,role="motion_root")
        self.pipe_between("Drawbar_Tube",(0,0,0),(L*.31,-H*.04,0),H*.035,self.materials["steel"],drawbar,role="drawbar")
        pickup_pivot=self.empty("Pickup_Lift_Pivot",(L*.14,H*.18,0),self.fixed_root,role="pivot")
        pickup=self.empty("Pickup_ROOT",parent=pickup_pivot,role="motion_root")
        self.cylinder("Pickup_Reel",(L*.15,-H*.05,0),H*.08,W*.74,self.materials["graphite"],pickup,vertices=20,role="pickup_reel")
        for index in range(20):
            angle=math.tau*index/20
            self.box(f"Pickup_Tine_{index+1:02d}",(L*.15+math.cos(angle)*H*.09,-H*.05+math.sin(angle)*H*.09,0),(H*.018,H*.025,W*.72),self.materials["steel"],pickup,rotation=(0,0,angle),role="pickup_tine",bevel=0.005)
        self.empty("Plunger_ROOT",(-L*.08,H*.50,0),self.fixed_root,role="linear_motion_root")
        chute_pivot=self.empty("Bale_Chute_Pivot",(-L*.37,H*.26,0),self.fixed_root,role="pivot")
        chute=self.empty("Bale_Chute_ROOT",parent=chute_pivot,role="motion_root")
        self.box("Bale_Chute",(-L*.03,-H*.04,0),(L*.16,H*.07,W*.60),self.materials["steel"],chute,rotation=(0,0,-0.12),role="bale_chute")

    def build_self_propelled_round_baler(self):
        L, W, H = self.length, self.carrier_width, self.height
        rear_r = min(H * 0.18, L * 0.105)
        front_r = rear_r * 0.80
        self.add_four_wheel_running_gear(
            rear_r, front_r, rear_x=-L * 0.22, front_x=L * 0.29, running_width=W
        )
        front_axle_pivot = self.empty(
            "Front_Axle_Oscillation_Pivot", (L * 0.29, front_r, 0),
            self.running_root, role="pivot",
        )
        self.empty("Front_Axle_ROOT", parent=front_axle_pivot, role="motion_root")
        self.box(
            "Self_Propelled_Baler_Frame", (0, H * 0.31, 0),
            (L * 0.66, H * 0.12, W * 0.50), self.materials["graphite"],
            self.fixed_root, role="chassis",
        )
        self.add_cab(L * 0.27, H * 0.39, L * 0.19, W * 0.48, H * 0.61, self.fixed_root)
        self.box(
            "Power_Module", (L * 0.05, H * 0.55, 0),
            (L * 0.22, H * 0.34, W * 0.54), self.materials["body"],
            self.fixed_root, role="power_module",
        )
        chamber = self.empty("Bale_Chamber_ROOT", (-L * 0.19, H * 0.56, 0), self.fixed_root, role="rotary_process_root")
        chamber_radius = min(H * 0.24, L * 0.13)
        self.cylinder(
            "Round_Bale_Chamber", (0, 0, 0), chamber_radius, W * 0.68,
            self.materials["body_dark"], chamber, vertices=32, role="round_bale_chamber",
        )
        for side, z in (("L", -W * 0.35), ("R", W * 0.35)):
            self.cylinder(
                f"Chamber_{side}_Side_Plate", (0, 0, z), chamber_radius * 0.82,
                W * 0.025, self.materials["body"], chamber, vertices=28,
                role="round_bale_chamber",
            )
        pickup_pivot = self.empty("Pickup_Lift_Pivot", (L * 0.18, H * 0.20, 0), self.fixed_root, role="pivot")
        pickup = self.empty("Pickup_ROOT", parent=pickup_pivot, role="motion_root")
        self.cylinder(
            "Pickup_Reel", (L * 0.13, -H * 0.04, 0), H * 0.075, W * 0.72,
            self.materials["graphite"], pickup, vertices=20, role="pickup_reel",
        )
        for index in range(18):
            angle = math.tau * index / 18
            self.box(
                f"Pickup_Tine_{index + 1:02d}",
                (L * 0.13 + math.cos(angle) * H * 0.085,
                 -H * 0.04 + math.sin(angle) * H * 0.085, 0),
                (H * 0.014, H * 0.022, W * 0.70), self.materials["steel"],
                pickup, rotation=(0, 0, angle), role="pickup_tine", bevel=0.004,
            )
        tailgate_pivot = self.empty(
            "Tailgate_Pivot", (-chamber_radius * 0.72, chamber_radius * 0.70, 0),
            chamber, role="pivot",
        )
        tailgate = self.empty("Tailgate_ROOT", parent=tailgate_pivot, role="motion_root")
        self.side_profile(
            "Round_Chamber_Tailgate",
            [(0, 0), (-chamber_radius * 0.48, -chamber_radius * 0.30),
             (-chamber_radius * 0.52, -chamber_radius * 1.05),
             (-chamber_radius * 0.10, -chamber_radius * 1.35),
             (chamber_radius * 0.08, -chamber_radius * 0.50)],
            W * 0.70, self.materials["body"], tailgate, role="tailgate",
        )

    def build_articulated_hauler(self):
        L,W,H=self.length,self.width,self.height
        r=min(H*.20,L*.085)
        front=self.empty("Front_Frame_ROOT",parent=self.root,role="motion_root")
        yaw=self.empty("Chassis_Yaw_Pivot",(0,H*.35,0),self.root,role="pivot")
        rear=self.empty("Rear_Frame_ROOT",(0,-H*.35,0),yaw,role="motion_root")
        tire_w=W*.17
        for prefix,x,owner in (("Front",L*.30,front),("Middle",-L*.12,rear),("Rear",-L*.36,rear)):
            for side,z in (("L",-(W/2-tire_w/2)),("R",W/2-tire_w/2)):
                self.add_wheel(f"{prefix}_{side}",(x,r,z),r,tire_w,owner,14)
        self.box("Front_Chassis",(L*.22,H*.34,0),(L*.36,H*.12,W*.48),self.materials["graphite"],front,role="chassis")
        self.box("Articulation_Knuckle",(L*.0175,H*.35,0),(L*.055,H*.11,W*.30),self.materials["steel"],self.fixed_root,role="articulation_structure")
        self.cylinder("Articulation_Pin",(L*.0175,H*.35,0),H*.055,W*.32,self.materials["graphite"],self.fixed_root,vertices=20,role="articulation_pin")
        self.add_cab(L*.27,H*.42,L*.18,W*.48,H*.58,front)
        self.box("Rear_Chassis",(-L*.24,H*.34,0),(L*.47,H*.13,W*.52),self.materials["graphite"],rear,role="chassis")
        bed_pivot=self.empty("Bed_Tip_Pivot",(-L*.06,H*.43,0),rear,role="pivot")
        bed=self.empty("Bed_ROOT",parent=bed_pivot,role="motion_root")
        self.box("Dump_Bed_Floor",(-L*.20,H*.05,0),(L*.46,H*.08,W*.74),self.materials["body"],bed,role="dump_bed")
        for side,z in (("L",-W*.37),("R",W*.37)):
            self.side_profile(f"Dump_Bed_Side_{side}",[(-L*.43,0),(L*.03,0),(-L*.02,H*.31),(-L*.39,H*.38)],H*.045,self.materials["body"],bed,z_center=z,role="dump_bed")
        if self.design.get("tailgate", True):
            tail_pivot=self.empty("Tailgate_Pivot",(-L*.42,H*.39,0),bed,role="pivot")
            tail=self.empty("Tailgate_ROOT",parent=tail_pivot,role="motion_root")
            self.box("Tailgate",(0,-H*.12,0),(H*.07,H*.32,W*.72),self.materials["body_dark"],tail,role="tailgate")
        self.pipe_between("Bed_Lift_Cylinder",(-L*.05,H*.36,0),(-L*.20,H*.52,0),H*.035,self.materials["steel"],self.hydraulics_root,role="hydraulic")

    def build_excavator(self):
        L,W,H=self.length,self.width,self.height
        track_l=L*.42
        track_h=H*.25
        track_w=W*.22
        for side,z in (("L",-(W/2-track_w/2)),("R",W/2-track_w/2)):
            self.add_track_pod(f"Track_{side}",track_l,track_h,track_w,(-L*.18,0,z),self.running_root,pads=30)
        self.box("Carbody",(-L*.18,track_h*.82,0),(track_l*.82,H*.11,W*.56),self.materials["graphite"],self.fixed_root,role="carbody")
        swing=self.empty("Upper_Swing_Pivot",(-L*.16,H*.31,0),self.root,role="pivot")
        upper=self.empty("Upper_ROOT",parent=swing,role="motion_root")
        self.box("Upper_House",(-L*.08,H*.16,0),(L*.32,H*.32,W*.72),self.materials["body"],upper,role="upper_house")
        self.add_cab(L*.05,H*.10,L*.16,W*.28,H*.50,upper)
        boom_pivot=self.empty("Boom_Pivot",(L*.01,H*.25,0),upper,role="pivot")
        boom=self.empty("Boom_ROOT",parent=boom_pivot,role="motion_root")
        boom_len=L*.36
        boom_rise=H*.36
        self.pipe_between("Boom_Main",(0,0,0),(boom_len,boom_rise,0),H*.075,self.materials["body"],boom,role="boom")
        stick_pivot=self.empty("Stick_Pivot",(boom_len,boom_rise,0),boom,role="pivot")
        stick=self.empty("Stick_ROOT",parent=stick_pivot,role="motion_root")
        stick_len=L*.23
        self.pipe_between("Stick_Main",(0,0,0),(stick_len,-H*.30,0),H*.060,self.materials["body_dark"],stick,role="stick")
        bucket_pivot=self.empty("Bucket_Pivot",(stick_len,-H*.30,0),stick,role="pivot")
        bucket=self.empty("Bucket_ROOT",parent=bucket_pivot,role="motion_root")
        self.side_profile("Bucket_Shell",[(0,0),(L*.10,-H*.02),(L*.12,-H*.15),(L*.03,-H*.18),(-L*.01,-H*.08)],W*.34,self.materials["steel"],bucket,role="bucket")
        self.pipe_between("Boom_Cylinder",(-L*.08,H*.30,-W*.16),(L*.01+boom_len*.55,H*.25+boom_rise*.55,-W*.16),H*.035,self.materials["steel"],upper,role="hydraulic")

    def build_model(self):
        self.build_common_roots()
        getattr(self, f"build_{self.archetype}")()
        self.add_service_detail_density()
        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"archetype builder omitted semantic nodes: {', '.join(missing)}")
        return self.root

    def mesh_world_bounds(self):
        minimum = [math.inf, math.inf, math.inf]
        maximum = [-math.inf, -math.inf, -math.inf]
        vertex_count = 0
        for obj in self.public_objects():
            if obj.type != "MESH":
                continue
            for vertex in obj.data.vertices:
                point = obj.matrix_world @ vertex.co
                for axis in range(3):
                    minimum[axis] = min(minimum[axis], point[axis])
                    maximum[axis] = max(maximum[axis], point[axis])
                vertex_count += 1
        if vertex_count == 0 or not all(math.isfinite(value) for value in minimum + maximum):
            raise RuntimeError("could not measure public visible geometry")
        return {
            "min_m": minimum,
            "max_m": maximum,
            "size_m": [maximum[index] - minimum[index] for index in range(3)],
            "vertices": vertex_count,
        }

    def apply_public_modifiers(self):
        for obj in sorted(
            (item for item in self.public_objects() if item.type == "MESH"),
            key=lambda item: item.name,
        ):
            for modifier in list(obj.modifiers):
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.object.select_all(action="DESELECT")

    def normalize_visible_envelope(self):
        """Measure the authored envelope without deforming the machine to fit it.

        Non-uniform post-build normalization previously made unrelated archetypes
        match published outer dimensions while corrupting wheel roundness, joint
        centers, and component measurements.  A machine-local builder must now
        author its geometry in metres.  The retained method name keeps older
        subclasses source-compatible, but this operation is verification-only.
        """
        self.apply_public_modifiers()
        bpy.context.view_layer.update()
        source = self.mesh_world_bounds()
        target_min = [-self.length / 2, 0.0, -self.width / 2]
        target_max = [self.length / 2, self.height, self.width / 2]
        target_size = [self.length, self.height, self.width]
        if any(value <= 1e-9 for value in source["size_m"]):
            raise RuntimeError(f"degenerate source envelope: {source}")
        return {
            "classification": "authored_visible_envelope_measurement",
            "source_bounds_m": {
                "min_m": [round(value, 6) for value in source["min_m"]],
                "max_m": [round(value, 6) for value in source["max_m"]],
                "size_m": [round(value, 6) for value in source["size_m"]],
            },
            "target_bounds_m": {
                "min_m": target_min, "max_m": target_max, "size_m": target_size,
            },
            "axis_scale_factors": [1.0, 1.0, 1.0],
            "calibrated_bounds_m": {
                "min_m": [round(value, 6) for value in source["min_m"]],
                "max_m": [round(value, 6) for value in source["max_m"]],
                "size_m": [round(value, 6) for value in source["size_m"]],
            },
            "authority": "independently_measured_from_authored_geometry",
        }

    def required_semantics(self):
        names = list(ARCHETYPE_SEMANTICS[self.archetype])
        if self.archetype == "combine" and (
            self.design.get("tracked_front", False)
            or self.design.get("reconstructed_values", {}).get("running_gear")
            in {"front_terra_trac_rear_wheels", "front_tracks_rear_wheels"}
        ):
            names.extend(["Track_L_ROOT", "Track_R_ROOT"])
        if self.archetype == "articulated_hauler" and self.design.get("tailgate", True):
            names.extend(["Tailgate_Pivot", "Tailgate_ROOT"])
        return names

    def semantic_support(self, names):
        """Measure whether each semantic owns exported visible geometry."""
        support = {}
        for name in names:
            obj = bpy.data.objects.get(name)
            descendants = [] if obj is None else list(obj.children_recursive)
            visible_descendants = [
                child.name for child in descendants
                if child.type == "MESH" and self.is_public(child)
            ]
            if obj is not None and obj.type == "MESH" and self.is_public(obj):
                visible_descendants.insert(0, obj.name)
            support[name] = {
                "present": obj is not None,
                "role": obj.get("exo_role") if obj is not None else None,
                "visible_mesh_descendants": visible_descendants,
            }
        return support

    def mechanism_required_gates(self):
        """Load the machine contract whose gate IDs must be represented exactly."""
        path = self.output_dir / "mechanism.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"cannot load mechanism gate contract {path}: {error}") from error
        if payload.get("machine_id") != self.machine_id or payload.get("configuration_id") != self.configuration_id:
            raise RuntimeError("mechanism gate contract identity does not match the design")
        required = payload.get("required_gates")
        if not isinstance(required, list) or not required or any(not isinstance(item, str) or not item for item in required):
            raise RuntimeError("mechanism.required_gates must be a nonempty string array")
        if len(required) != len(set(required)):
            raise RuntimeError("mechanism.required_gates contains duplicate IDs")
        return required

    def machine_specific_validation_gates(self, contract):
        """Return independently measured gate records supplied by a local subclass.

        Base archetypes intentionally provide no machine-specific proof.  A local
        builder may override this hook and return records whose IDs exactly match
        mechanism.required_gates.  Unimplemented required gates remain explicit
        PENDING records instead of disappearing from validation.
        """
        return []

    def is_public(self, obj) -> bool:
        current = obj
        while current is not None:
            if current == self.root:
                return obj.type not in {"CAMERA", "LIGHT"} and bool(obj.get("exo_export", True))
            current = current.parent
        return False

    def public_objects(self):
        return [obj for obj in bpy.context.scene.objects if self.is_public(obj)]

    def apply_public_mesh_scales(self):
        public_meshes = sorted(
            (obj for obj in self.public_objects() if obj.type == "MESH"),
            key=lambda item: (-self.hierarchy_depth(item), item.name),
        )
        applied = []
        for obj in public_meshes:
            if any(abs(value - 1.0) > 1e-7 for value in obj.scale):
                before = [round(value, 8) for value in obj.scale]
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                applied.append({"node": obj.name, "before": before})
        bpy.ops.object.select_all(action="DESELECT")
        residual = {
            obj.name: [round(value, 8) for value in obj.scale]
            for obj in public_meshes
            if any(abs(value - 1.0) > 1e-5 for value in obj.scale)
        }
        return {"applied": applied, "residual": residual}

    @staticmethod
    def hierarchy_depth(obj):
        depth = 0
        current = obj.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def setup_render_scene(self):
        ground = self.box(
            "Review_Ground_Surface", (0, -0.045, 0),
            (max(self.length, self.width) * 2.8, 0.08, max(self.length, self.width) * 2.8),
            self.materials["graphite"], None, role="review_only", bevel=0,
        )
        ground["exo_export"] = False
        self.render_objects.append(ground)
        camera_data = bpy.data.cameras.new("Review_Camera_Data")
        camera = bpy.data.objects.new("Review_Camera", camera_data)
        bpy.context.scene.collection.objects.link(camera)
        camera["exo_export"] = False
        camera_data.type = "ORTHO"
        bpy.context.scene.camera = camera
        self.render_objects.append(camera)
        for name, energy, size, location in (
            ("Review_Key", 1100, 5.0, (self.length*.55,self.height*1.8,-self.width*1.5)),
            ("Review_Fill", 800, 4.0, (-self.length*.45,self.height*1.2,self.width*1.6)),
            ("Review_Rim", 950, 3.0, (-self.length*.55,self.height*2.0,-self.width*.3)),
        ):
            data=bpy.data.lights.new(name,"AREA")
            data.energy=energy
            data.shape="DISK"
            data.size=size
            light=bpy.data.objects.new(name,data)
            bpy.context.scene.collection.objects.link(light)
            light.location=location
            light.rotation_euler=(0,0,0)
            light["exo_export"]=False
            self.point_at(light,(0,self.height*.38,0))
            self.render_objects.append(light)

    @staticmethod
    def point_at(obj, target):
        forward=(Vector(target)-obj.location).normalized()
        world_up=Vector((0,1,0))
        if abs(forward.dot(world_up)) > 0.995:
            world_up=Vector((0,0,1))
        right=forward.cross(world_up).normalized()
        up=right.cross(forward).normalized()
        rotation=Matrix((right,up,-forward)).transposed().to_quaternion()
        obj.rotation_mode="QUATERNION"
        obj.rotation_quaternion=rotation

    def render_views(self):
        self.setup_render_scene()
        camera=bpy.data.objects["Review_Camera"]
        center=Vector((0,self.height*.46,0))
        span=max(self.length,self.width,self.height)
        carrier_span=max(self.length,self.carrier_width,self.height)
        views=[
            ("operator-side", (0,self.height*.62,-span*1.55), carrier_span*1.08),
            ("front-three-quarter", (span*1.10,self.height*.88,-span*1.02), span*1.18),
            ("rear-three-quarter", (-span*1.12,self.height*.82,span*.96), carrier_span*1.18),
            ("elevated-technical", (span*.65,span*1.45,-span*.95), span*1.30),
            ("articulation-detail", (span*.82,self.height*.62,-span*.72), carrier_span*.84),
            ("right-side", (0,self.height*.62,span*1.55), carrier_span*1.08),
        ]
        paths=[]
        for label,location,ortho_scale in views:
            camera.location=location
            self.point_at(camera,center)
            camera.data.ortho_scale=ortho_scale
            path=self.render_dir/f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        return paths

    def export(self):
        public=self.public_objects()
        bpy.ops.object.select_all(action="DESELECT")
        for obj in public:
            obj.select_set(True)
        bpy.context.view_layer.objects.active=self.root
        bpy.ops.export_scene.gltf(
            filepath=str(self.glb_path), export_format="GLB", use_selection=True,
            export_apply=True, export_yup=False, export_extras=True, export_texcoords=False,
            export_normals=True, export_cameras=False, export_lights=False,
        )
        bpy.ops.object.select_all(action="DESELECT")

    def run(self):
        for path in (self.blend_path.parent,self.glb_path.parent,self.render_dir,self.receipt_path.parent):
            path.mkdir(parents=True,exist_ok=True)
        self.write_machine_wrapper()
        self.reset_scene()
        self.create_materials()
        self.build_model()
        bpy.context.view_layer.update()
        self.envelope_fit = self.normalize_visible_envelope()
        scale_audit=self.apply_public_mesh_scales()
        bpy.context.view_layer.update()
        render_paths=self.render_views()
        bpy.ops.wm.save_as_mainfile(filepath=str(self.blend_path),compress=True)
        self.export()
        contract=inspect_glb(self.glb_path)
        validation=self.create_validation(contract,render_paths,scale_audit)
        write_json(self.validation_path,validation)
        receipt=self.create_receipt(contract,render_paths,validation)
        write_json(self.receipt_path,receipt)
        if validation["verdict"] != "PASS":
            raise RuntimeError(f"fleet build failed: {validation['failed_gate_ids']}")
        result={
            "status":"PASS","machine_id":self.machine_id,"archetype":self.archetype,
            "output_dir":str(self.output_dir),"blend":str(self.blend_path),"glb":str(self.glb_path),
            "receipt":str(self.receipt_path),"validation":str(self.validation_path),
            "renders":len(render_paths),
            "glb_contract":{key:value for key,value in contract.items() if key!="node_names"},
        }
        print("FLEET_BUILD_RESULT="+json.dumps(result,sort_keys=True))
        return result

    def write_machine_wrapper(self):
        shared_relative = os.path.relpath(SCRIPT_PATH, self.wrapper_path.parent).replace(os.sep, "/")
        design_relative = os.path.relpath(self.design_path, self.wrapper_path.parent).replace(os.sep, "/")
        output_relative = os.path.relpath(self.output_dir, self.wrapper_path.parent).replace(os.sep, "/")
        content = f'''#!/usr/bin/env python3
"""Machine-owned deterministic entrypoint for {self.machine_id}.

Generated by scripts/fleet/build_machine.py. The shared generator remains the
authoring implementation and is hash-bound separately in asset-receipt.json.
"""
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / {json.dumps(shared_relative)}).resolve()
DESIGN = (HERE / {json.dumps(design_relative)}).resolve()
OUTPUT_DIR = (HERE / {json.dumps(output_relative)}).resolve()
sys.argv = [str(SHARED_GENERATOR), "--", "--design", str(DESIGN), "--output-dir", str(OUTPUT_DIR)]
runpy.run_path(str(SHARED_GENERATOR), run_name="__main__")
'''
        self.wrapper_path.write_text(content, encoding="utf-8")

    def create_validation(self,contract,render_paths,scale_audit):
        render_records=[{"path":str(path),"bytes":path.stat().st_size} for path in render_paths]
        required=[ROOT_NAME,"Fixed_Structure_ROOT","Running_Gear_ROOT","Hydraulics_ROOT",*self.required_semantics()]
        semantic_support = self.semantic_support(required)
        presence={name:record["present"] for name,record in semantic_support.items()}
        supported_semantics = {
            name: bool(record["visible_mesh_descendants"]) or record["role"] in {"datum_marker", "joint_marker", "identity_marker"}
            for name, record in semantic_support.items()
        }
        technical=[
            ("builder-execution",True,"Factory-startup background builder reached validation generation."),
            (
                "machine-specific-builder",
                type(self) is not FleetBuilder,
                "Machine-local subclass owns the selected machine topology."
                if type(self) is not FleetBuilder
                else "Direct shared-archetype output cannot qualify as a machine-specific technical build.",
            ),
            ("candidate-class-boundary",True,"technical_structural_study only; not engineering authority."),
            ("scene-units-and-axes",True,"Meters; +X forward, +Y up, +Z machine right."),
            ("independent-authoring-boundary",True,"No downloaded geometry, CAD, copied textures, logos, or opaque add-ons."),
            ("one-identity-root",contract["scene_root_count"]==1 and contract["root_name"]==ROOT_NAME and contract["identity_root"],contract["root_record"]),
            ("required-semantic-nodes",all(presence.values()) and all(supported_semantics.values()),semantic_support),
            ("semantic-motion-hierarchy",contract["semantic_motion_nodes"]>=len(self.required_semantics()),{"semantic_motion_nodes":contract["semantic_motion_nodes"]}),
            ("export-mesh-scales-applied",not scale_audit["residual"] and not contract["nonidentity_mesh_scales"],{"authoring_residual":scale_audit["residual"],"glb_residual":contract["nonidentity_mesh_scales"]}),
            ("public-glb-no-cameras-lights",contract["cameras"]==0 and not contract["punctual_lights"],{"cameras":contract["cameras"],"punctual_lights":contract["punctual_lights"]}),
            ("public-glb-no-helpers",not contract["helper_like_mesh_nodes"],contract["helper_like_mesh_nodes"]),
            ("public-glb-no-images-textures",contract["images"]==0 and contract["textures"]==0,{"images":contract["images"],"textures":contract["textures"]}),
            ("node-density",contract["nodes"]>=MINIMUMS["nodes"],{"actual":contract["nodes"],"minimum":MINIMUMS["nodes"]}),
            ("mesh-density",contract["mesh_nodes"]>=MINIMUMS["mesh_nodes"],{"actual":contract["mesh_nodes"],"minimum":MINIMUMS["mesh_nodes"]}),
            ("triangle-density",contract["triangles"]>=MINIMUMS["triangles"],{"actual":contract["triangles"],"minimum":MINIMUMS["triangles"]}),
            ("finite-visible-bounds",all(math.isfinite(v) for v in contract["bounds"]["min_m"]+contract["bounds"]["max_m"]),contract["bounds"]),
            ("retained-visible-envelope",all(abs(contract["bounds"]["size_m"][index]-expected)<=0.03 for index,expected in enumerate((self.length,self.height,self.width))) and contract["bounds"]["min_m"][1]>=-0.005,{"actual_size_m":contract["bounds"]["size_m"],"expected_size_m":[self.length,self.height,self.width],"absolute_tolerance_m":0.03,"minimum_y_m":contract["bounds"]["min_m"][1]}),
            ("review-renders-nonempty",len(render_records)>=MINIMUMS["renders"] and all(item["bytes"]>10_000 for item in render_records),render_records),
            ("neutral-unbranded-materials",True,"Neutral palette and procedural materials only; no manufacturer marks or textures."),
        ]
        gates=[{"id":gate_id,"status":"PASS" if ok else "FAIL","detail":detail} for gate_id,ok,detail in technical]
        supplied = self.machine_specific_validation_gates(contract)
        if not isinstance(supplied, list):
            raise RuntimeError("machine_specific_validation_gates must return a list")
        supplied_by_id = {}
        for gate in supplied:
            if not isinstance(gate, dict) or not isinstance(gate.get("id"), str):
                raise RuntimeError("machine-specific gate records require an id")
            if gate["id"] in supplied_by_id:
                raise RuntimeError(f"duplicate machine-specific gate id {gate['id']}")
            if gate.get("status") not in {"PASS", "FAIL", "PENDING"}:
                raise RuntimeError(f"invalid machine-specific gate status for {gate['id']}")
            detail = gate.get("detail")
            if (
                not isinstance(detail, dict)
                or not isinstance(detail.get("method"), str)
                or not detail["method"].strip()
                or "evidence" not in detail
                or not isinstance(detail.get("semantic_nodes"), list)
                or not isinstance(detail.get("fact_ids"), list)
                or any(not isinstance(name, str) or not name for name in detail["semantic_nodes"])
                or any(not isinstance(fact_id, str) or not fact_id for fact_id in detail["fact_ids"])
                or len(detail["semantic_nodes"]) != len(set(detail["semantic_nodes"]))
                or len(detail["fact_ids"]) != len(set(detail["fact_ids"]))
            ):
                raise RuntimeError(
                    f"machine-specific gate {gate['id']} requires detail.method, detail.evidence, "
                    "and unique detail.semantic_nodes/detail.fact_ids arrays"
                )
            supplied_by_id[gate["id"]] = gate
        required_gate_ids = self.mechanism_required_gates()
        unexpected = sorted(set(supplied_by_id) - set(required_gate_ids))
        if unexpected:
            raise RuntimeError(f"machine-specific gates are not declared by mechanism.json: {', '.join(unexpected)}")
        covered_fact_ids = {
            fact_id for gate in supplied for fact_id in gate["detail"]["fact_ids"]
        }
        uncovered_constraints = sorted(set(self.design["published_constraints_used"]) - covered_fact_ids)
        if uncovered_constraints:
            raise RuntimeError(
                "published_constraints_used lacks machine-gate evidence binding: "
                + ", ".join(uncovered_constraints)
            )
        for gate_id in required_gate_ids:
            gates.append(supplied_by_id.get(gate_id, {
                "id": gate_id,
                "status": "FAIL",
                "detail": "Required by mechanism.json; no independently measured machine-local proof was supplied.",
            }))
        gates.extend([
            {"id":"configuration-freeze","status":"PENDING","detail":"Research candidate retains unresolved exact configuration and options."},
            {"id":"machine-specific-mechanical-solver","status":"PENDING","detail":"Generic structural pivots do not establish evidence-bound limits, endpoints, or cylinder closure."},
            {"id":"ground-self-swept-collision","status":"PENDING","detail":"No machine-specific swept-volume or collision solver exists."},
            {"id":"critic-human-visual-review","status":"PENDING","detail":"A human critic must inspect the exact render and artifact hashes."},
            {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"Viewer integration belongs to the publication lane."},
            {"id":"publication-and-deployment","status":"PENDING","detail":"Only the publisher may advance this research artifact to release."},
        ])
        required_nonpass = [gate_id for gate_id in required_gate_ids if supplied_by_id.get(gate_id, {}).get("status") != "PASS"]
        failed=sorted(set([gate["id"] for gate in gates if gate["status"]=="FAIL"] + required_nonpass))
        return {
            "schema_version":"1.0.0","machine_id":self.machine_id,"configuration_id":self.configuration_id,
            "archetype":self.archetype,"candidate_class":"technical_structural_study",
            "engineering_authority":False,"verdict":"PASS" if not failed else "FAIL",
            "verdict_scope":"technical_structural_study_only","release_status":"PENDING",
            "bounds":contract["bounds"],"counts":{"objects":contract["nodes"],"meshes":contract["mesh_nodes"],"triangles":contract["triangles"],"materials":contract["materials"]},
            "envelope_fit":self.envelope_fit,
            "glb_contract":{key:value for key,value in contract.items() if key!="node_names"},
            "required_machine_gate_ids":required_gate_ids,
            "gates":gates,"failed_gate_ids":failed,
        }

    def create_receipt(self,contract,render_paths,validation):
        required=[ROOT_NAME,"Fixed_Structure_ROOT","Running_Gear_ROOT","Hydraulics_ROOT",*self.required_semantics()]
        semantic_support = self.semantic_support(required)
        reconstructed=dict(self.design["reconstructed_values"])
        reconstructed.setdefault("hidden_geometry",HIDDEN_GEOMETRY_BOUNDARY)
        reconstructed.setdefault("generic_archetype_geometry",f"{self.archetype} proportions and visible detail are independently reconstructed for this technical study.")
        reconstructed.setdefault("visible_envelope_calibration", self.envelope_fit)
        builder_relative=os.path.relpath(self.wrapper_path,self.output_dir).replace(os.sep,"/")
        shared_relative=os.path.relpath(SCRIPT_PATH,self.output_dir).replace(os.sep,"/")
        design_relative=os.path.relpath(self.design_path,self.output_dir).replace(os.sep,"/")
        return {
            "schema_version":"1.0.0","machine_id":self.machine_id,"configuration_id":self.configuration_id,
            "configuration_status":"research_candidate","archetype":self.archetype,
            "candidate_class":"technical_structural_study","engineering_authority":False,
            "authority_boundary":AUTHORITY_BOUNDARY,
            "rights_boundary":"Neutral unbranded procedural geometry and materials; no manufacturer CAD, logo, copied texture, or protected livery claim.",
            "release_status":"PENDING",
            "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
            "builder":{"path":builder_relative,"sha256":sha256(self.wrapper_path),"bytes":self.wrapper_path.stat().st_size,"deterministic":True,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
            "shared_generator":{"path":shared_relative,"sha256":sha256(SCRIPT_PATH),"bytes":SCRIPT_PATH.stat().st_size},
            "design":{"path":design_relative,"sha256":sha256(self.design_path),"bytes":self.design_path.stat().st_size,"schema_version":self.design["schema_version"]},
            "artifacts":{"blend":file_record(self.blend_path,self.output_dir),"glb":file_record(self.glb_path,self.output_dir),"validation":file_record(self.validation_path,self.output_dir)},
            "scene":{"units":"meters","axes":{"longitudinal":"+X forward","vertical":"+Y up","lateral":"+Z machine right"},"bounds":contract["bounds"],"visible_aabb_xyz_m":contract["bounds"]["size_m"],"objects":contract["nodes"],"meshes":contract["mesh_nodes"],"triangles":contract["triangles"],"materials":contract["materials"]},
            "glb_contract":{key:value for key,value in contract.items() if key!="node_names"},
            "required_semantic_nodes":{name:name in contract["node_names"] for name in required},
            "semantic_node_roles":{
                name: record["role"] for name, record in semantic_support.items()
                if not record["visible_mesh_descendants"] and record["role"] in {"datum_marker", "joint_marker", "identity_marker"}
            },
            "published_constraint_ids_declared":self.design["published_constraints_used"],
            "machine_specific_gate_evidence":[
                {"id": gate["id"], "status": gate["status"], "detail": gate["detail"]}
                for gate in validation["gates"] if gate["id"] in validation["required_machine_gate_ids"]
            ],
            "reconstructed_values":reconstructed,
            "unresolved_choices":self.design["unresolved_choices"],
            "mechanical_gaps":self.design["mechanical_gaps"],
            "renders":[file_record(path,self.output_dir) for path in render_paths],
            "build_verdict":validation["verdict"],"validation_verdict":validation["verdict"],
            "validation_path":os.path.relpath(self.validation_path,self.output_dir).replace(os.sep,"/"),
            "higher_stage_gates":"PENDING",
        }


def read_glb(path: Path):
    raw=path.read_bytes()
    if len(raw)<20:
        raise RuntimeError("truncated GLB")
    magic,version,total=struct.unpack_from("<4sII",raw,0)
    if magic!=b"glTF" or version!=2 or total!=len(raw):
        raise RuntimeError("invalid GLB header")
    offset=12
    document=None
    binary=b""
    while offset<len(raw):
        length,kind=struct.unpack_from("<II",raw,offset)
        offset+=8
        payload=raw[offset:offset+length]
        offset+=length
        if kind==0x4E4F534A:
            document=json.loads(payload.decode("utf-8").rstrip(" \t\r\n\x00"))
        elif kind==0x004E4942:
            binary=payload
    if document is None or not binary:
        raise RuntimeError("GLB must contain JSON and BIN chunks")
    return document,binary


def node_matrix(node):
    if "matrix" in node:
        values=node["matrix"]
        return Matrix(tuple(tuple(values[column*4+row] for column in range(4)) for row in range(4)))
    translation=Matrix.Translation(Vector(node.get("translation",[0,0,0])))
    rv=node.get("rotation",[0,0,0,1])
    rotation=Quaternion((rv[3],rv[0],rv[1],rv[2])).to_matrix().to_4x4()
    sv=node.get("scale",[1,1,1])
    scale=Matrix.Diagonal(Vector((sv[0],sv[1],sv[2],1)))
    return translation@rotation@scale


def component(binary,offset,component_type,normalized):
    formats={5120:"b",5121:"B",5122:"h",5123:"H",5125:"I",5126:"f"}
    value=struct.unpack_from("<"+formats[component_type],binary,offset)[0]
    if not normalized or component_type==5126:
        return float(value)
    divisors={5120:127.0,5121:255.0,5122:32767.0,5123:65535.0,5125:4294967295.0}
    result=float(value)/divisors[component_type]
    return max(result,-1.0) if component_type in {5120,5122} else result


def inspect_glb(path: Path):
    gltf,binary=read_glb(path)
    scene=gltf.get("scenes",[{}])[gltf.get("scene",0)]
    root_indices=scene.get("nodes",[])
    nodes=gltf.get("nodes",[])
    root=nodes[root_indices[0]] if len(root_indices)==1 else {}
    minimum=[math.inf,math.inf,math.inf]
    maximum=[-math.inf,-math.inf,-math.inf]
    component_sizes={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}
    triangles=0
    mesh_nodes=0
    reachable=set()
    nonidentity={}
    helper_meshes=[]
    helper_pattern=("COL_","COLLISION","HIT_","INSP_","INSPECT","WITNESS","ENVELOPE","HELPER","GUIDE")

    def include_accessor(accessor_index,world):
        accessor=gltf["accessors"][accessor_index]
        if accessor.get("type")!="VEC3" or accessor.get("sparse"):
            raise RuntimeError("public POSITION accessor must be nonsparse VEC3")
        view=gltf["bufferViews"][accessor["bufferView"]]
        ctype=accessor["componentType"]
        csize=component_sizes[ctype]
        stride=view.get("byteStride",csize*3)
        start=view.get("byteOffset",0)+accessor.get("byteOffset",0)
        for index in range(accessor["count"]):
            vertex_start=start+index*stride
            local=[component(binary,vertex_start+axis*csize,ctype,accessor.get("normalized",False)) for axis in range(3)]
            point=world@Vector((local[0],local[1],local[2],1))
            for axis in range(3):
                minimum[axis]=min(minimum[axis],point[axis])
                maximum[axis]=max(maximum[axis],point[axis])

    def visit(index,parent_world):
        nonlocal triangles,mesh_nodes
        if index in reachable:
            raise RuntimeError(f"node {index} is multiply referenced or cyclic")
        reachable.add(index)
        node=nodes[index]
        world=parent_world@node_matrix(node)
        if "mesh" in node:
            mesh_nodes+=1
            scale=node.get("scale",[1,1,1])
            if any(abs(value-1)>1e-4 for value in scale):
                nonidentity[node.get("name",str(index))]=scale
            upper=node.get("name","").upper()
            if any(token in upper for token in helper_pattern):
                helper_meshes.append(node.get("name",str(index)))
            mesh=gltf["meshes"][node["mesh"]]
            for primitive in mesh.get("primitives",[]):
                if primitive.get("mode",4)!=4:
                    raise RuntimeError("only triangle-list public primitives are supported")
                accessor_index=primitive.get("indices",primitive["attributes"]["POSITION"])
                count=gltf["accessors"][accessor_index]["count"]
                if count%3:
                    raise RuntimeError("triangle-list element count is not divisible by three")
                triangles+=count//3
                include_accessor(primitive["attributes"]["POSITION"],world)
        for child in node.get("children",[]):
            visit(child,world)

    for root_index in root_indices:
        visit(root_index,Matrix.Identity(4))
    unreachable=[node.get("name",str(index)) for index,node in enumerate(nodes) if "mesh" in node and index not in reachable]
    if unreachable:
        raise RuntimeError(f"unreachable mesh nodes: {unreachable[:8]}")
    root_record={key:root[key] for key in ("translation","rotation","scale","matrix") if key in root}
    identity_root=(
        root.get("name")==ROOT_NAME
        and root.get("translation",[0,0,0])==[0,0,0]
        and root.get("rotation",[0,0,0,1])==[0,0,0,1]
        and root.get("scale",[1,1,1])==[1,1,1]
        and "matrix" not in root
    )
    node_names={node.get("name","") for node in nodes}
    semantic_motion_nodes=sum(1 for name in node_names if name.endswith("_ROOT") or "_Pivot" in name)
    return {
        "glb_version":gltf.get("asset",{}).get("version"),"scene_count":len(gltf.get("scenes",[])),
        "scene_root_count":len(root_indices),"root_name":root.get("name"),"root_record":root_record,
        "identity_root":identity_root,"nodes":len(nodes),"mesh_nodes":mesh_nodes,
        "mesh_definitions":len(gltf.get("meshes",[])),"materials":len(gltf.get("materials",[])),
        "triangles":triangles,"cameras":len(gltf.get("cameras",[])),
        "punctual_lights":"KHR_lights_punctual" in gltf.get("extensions",{}) or "KHR_lights_punctual" in gltf.get("extensionsUsed",[]),
        "images":len(gltf.get("images",[])),"textures":len(gltf.get("textures",[])),
        "nonidentity_mesh_scales":nonidentity,"helper_like_mesh_nodes":sorted(helper_meshes),
        "semantic_motion_nodes":semantic_motion_nodes,
        "bounds":{"min_m":[round(v,6) for v in minimum],"max_m":[round(v,6) for v in maximum],"size_m":[round(maximum[i]-minimum[i],6) for i in range(3)]},
        "node_names":node_names,
    }


def parse_args(argv):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design",required=True,help="Machine design JSON path")
    parser.add_argument("--output-dir",required=True,help="Machine package output directory")
    return parser.parse_args(argv)


def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    args=parse_args(argv)
    design_path=Path(args.design).resolve()
    try:
        design=load_design(design_path)
    except DesignContractError as error:
        raise SystemExit(f"fleet design rejected: {error}") from error
    FleetBuilder(design,design_path,Path(args.output_dir)).run()


if __name__=="__main__":
    main()
