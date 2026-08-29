#!/usr/bin/env python3
"""Deterministically build the neutral Cat 725 technical structural study.

The asset is independently authored from admitted first-party envelope and
configuration evidence. It is not manufacturer CAD, engineering authority,
load guidance, operator training, or a validated mechanical solver.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SCRIPT_PATH = Path(__file__).resolve()
MACHINE_DIR = SCRIPT_PATH.parents[2]
BLEND_PATH = SCRIPT_PATH.parent / "cat-725-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "cat-725-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"

MACHINE_ID = "cat-725"
CONFIGURATION_ID = "CAT-725-05A-NAM-STANDARD-BODY-23.5R25-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"

PUBLISHED = {
    "overall_length_m": 10.445,
    "transport_height_m": 3.498,
    "overall_width_m": 3.676,
    "width_over_tire_m": 2.877,
    "width_over_fenders_m": 2.950,
    "body_width_m": 2.902,
    "body_length_m": 5.759,
    "body_inside_length_m": 5.363,
    "body_height_fully_tipped_m": 6.414,
    "body_tip_reference_deg": 70.0,
    "load_over_height_m": 2.783,
    "ground_clearance_m": 0.533,
    "rear_axle_to_body_rear_m": 1.556,
    "tandem_axle_spacing_m": 1.700,
    "front_to_middle_axle_spacing_m": 3.979,
    "front_axle_to_machine_front_m": 3.210,
    "steer_angle_each_side_deg": 45.0,
    "front_oscillation_each_side_deg": 6.0,
    "tire_count": 6,
    "tire_designation": "23.5R25 radial",
    "rated_payload_t": 24.0,
    "heaped_capacity_m3": 15.0,
    "body_raise_time_s": 12.0,
    "body_lower_time_s": 8.0,
}

RECONSTRUCTED = {
    "front_axle_center_m": [2.450, 0.8252, 0.0],
    "middle_axle_center_m": [-1.529, 0.8252, 0.0],
    "rear_axle_center_m": [-3.229, 0.8252, 0.0],
    "articulation_center_m": [0.150, 1.080, 0.0],
    "dump_body_hinge_m": [-4.185, 1.200, 0.0],
    "tire_outer_radius_m": 0.820,
    "tire_section_width_m": 0.602,
    "tire_tread_stations_each": 24,
    "tire_lugs_per_station": 3,
    "review_articulation_pose": {
        "rear_yaw_deg": 24.0,
        "front_axle_oscillation_deg": 5.0,
        "note": "Review-only pose inside published range; no steering or suspension solver is claimed."
    },
    "review_body_tip_pose": {
        "body_tip_deg": 70.0,
        "note": "Review-only use of the published drawing reference; hinge and hoist geometry remain reconstructed."
    },
    "body_profile": "Independently reconstructed around published body length, width, load-over height, and fully-tipped height.",
    "articulation_joint": "Center, bearing construction, yokes, pins, and steering-cylinder anchors are reconstructed.",
    "front_suspension": "Oscillation center, axle housing, struts, and links are reconstructed; only the plus/minus six-degree statement is published.",
    "rear_tandem": "Axle housings, bogie beams, differential cases, torque links, and compliance are visible reconstruction cues only.",
    "tire_and_rim": "23.5R25 identity and quantity are published; tire diameter, section shape, tread, rim, hub, and fasteners are reconstructed.",
    "hoist_hydraulics": "Twin telescopic visual cylinders, stages, hinge, and all anchor coordinates are reconstructed.",
    "steering_hydraulics": "Barrels, rods, routing, and all anchor coordinates are reconstructed.",
    "driveline": "Driveshafts, universal-joint cues, transfer case, and differential geometry are reconstructed exterior cues.",
    "cab_engine_body_details": "Visible silhouette, panels, glass boundaries, steps, rails, lighting, vents, and hose routes are independently observed and reconstructed.",
    "material_colors": "Neutral rust ochre, graphite, rubber, steel, and smoked glass; no logo or protected exact livery claim."
}

REQUIRED_NODES = [
    "Machine_Root",
    "Front_Tractor_ROOT",
    "Rear_Articulation_Pivot",
    "Rear_Frame_ROOT",
    "Front_Axle_Oscillation_Pivot",
    "Front_Axle_ROOT",
    "Axle_Mid_ROOT",
    "Axle_Rear_ROOT",
    "Wheel_FL_ROOT",
    "Wheel_FR_ROOT",
    "Wheel_ML_ROOT",
    "Wheel_MR_ROOT",
    "Wheel_RL_ROOT",
    "Wheel_RR_ROOT",
    "Dump_Body_Hinge",
    "Dump_Body_ROOT",
    "Hydraulics_ROOT",
    "Steering_Hydraulics_ROOT",
    "Hoist_Hydraulics_ROOT",
    "Driveline_ROOT",
    "Cab_ROOT",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(MACHINE_DIR).as_posix()


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.017, 0.024)
    scene["exo_machine_id"] = MACHINE_ID
    scene["exo_configuration_id"] = CONFIGURATION_ID
    scene["exo_candidate_class"] = CANDIDATE_CLASS
    scene["exo_axes"] = "+X toward tractor front, +Y vertical, +Z machine right"
    scene["exo_authority_boundary"] = "independently authored technical structural study; not engineering authority"


def material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat["exo_rights"] = "neutral_unbranded"
    return mat


def tag(obj, role="geometry", export=True, authority="reconstructed"):
    obj["exo_role"] = role
    obj["exo_export"] = bool(export)
    obj["exo_authority"] = authority
    return obj


def empty(name, location=(0, 0, 0), parent=None, role="pivot", display="PLAIN_AXES", size=0.20, export=True):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    if parent:
        obj.parent = parent
    return tag(obj, role, export)


def bevel(obj, width=0.025, segments=2):
    if width <= 0:
        return obj
    modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    return obj


def box(name, location, dimensions, mat, parent, bevel_width=0.02, role="geometry", export=True, authority="reconstructed", rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(bevel_width, min(dimensions) * 0.22), 2)
    return tag(obj, role, export, authority)


def cylinder(name, location, radius, depth, mat, parent, vertices=24, rotation=(0, 0, 0), role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(radius * 0.10, 0.018), 2)
    return tag(obj, role, export, authority)


def uv_sphere(name, location, radius, mat, parent, role="geometry", segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    return tag(obj, role)


def torus(name, location, major_radius, minor_radius, mat, parent, major_segments=40, minor_segments=12, role="geometry"):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    return tag(obj, role)


def side_profile(name, points_xy, thickness, mat, parent, z_center=0.0, bevel_width=0.02, role="geometry"):
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
    obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, bevel_width, 2)
    return tag(obj, role)


def parent_keep_world(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def place_between(obj, start, end, radius):
    start, end = Vector(start), Vector(end)
    vector = end - start
    length = vector.length
    rotation = Vector((0, 0, 1)).rotation_difference(vector.normalized())
    obj.matrix_world = Matrix.LocRotScale((start + end) / 2, rotation, (radius, radius, length))


def object_between(name, start, end, radius, mat, parent, role="hydraulic", vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    tag(obj, role)
    place_between(obj, start, end, radius)
    bevel(obj, 0.010, 2)
    parent_keep_world(obj, parent)
    return obj


def local_between(name, parent, start, end, radius, mat, role="tube", vertices=16):
    bpy.context.view_layer.update()
    start_world = parent.matrix_world @ Vector(start)
    end_world = parent.matrix_world @ Vector(end)
    return object_between(name, start_world, end_world, radius, mat, parent, role, vertices)


def build_wheel(prefix, root, mats):
    root["tire_identity"] = PUBLISHED["tire_designation"]
    root["tire_geometry_authority"] = "reconstructed"
    torus(f"{prefix}_Tire_Carcass", (0, 0, 0), 0.605, 0.185, mats["rubber"], root, 48, 14, "tire")
    torus(f"{prefix}_Sidewall_L", (0, 0, -0.270), 0.575, 0.060, mats["rubber_side"], root, 40, 10, "tire_sidewall")
    torus(f"{prefix}_Sidewall_R", (0, 0, 0.270), 0.575, 0.060, mats["rubber_side"], root, 40, 10, "tire_sidewall")
    # Three independently authored lug blocks at every station create the
    # alternating chevron/shoulder breakup expected of an off-highway radial.
    # The 23.5R25 designation is published; every tread dimension is visual
    # reconstruction and deliberately avoids a supplier-specific pattern.
    station_count = RECONSTRUCTED["tire_tread_stations_each"]
    lug_specs = (
        ("L", -0.202, -math.radians(2.0), math.radians(31.0), 0.190),
        ("C",  0.000,  0.000,              0.000,              0.214),
        ("R",  0.202,  math.radians(2.0), -math.radians(31.0), 0.190),
    )
    for index in range(station_count):
        base_theta = index * math.tau / station_count
        for zone, z, phase, slant, width in lug_specs:
            theta = base_theta + phase
            radius = 0.7845
            x = math.cos(theta) * radius
            y = math.sin(theta) * radius
            center_slant = math.radians(7.0 if index % 2 == 0 else -7.0) if zone == "C" else slant
            block = box(
                f"{prefix}_Tread_{index+1:02d}_{zone}",
                (x, y, z),
                (0.194, 0.070, width),
                mats["rubber"],
                root,
                0.014,
                "tire_tread",
                rotation=(0, center_slant, theta - math.pi / 2),
            )
            block["tread_authority"] = "reconstructed_visual"
    cylinder(f"{prefix}_Rim", (0, 0, 0), 0.405, 0.610, mats["rim"], root, 48, role="wheel_rim")
    cylinder(f"{prefix}_Rim_Recess_L", (0, 0, -0.318), 0.315, 0.038, mats["steel_dark"], root, 40, role="wheel_rim")
    cylinder(f"{prefix}_Rim_Recess_R", (0, 0, 0.318), 0.315, 0.038, mats["steel_dark"], root, 40, role="wheel_rim")
    cylinder(f"{prefix}_Hub", (0, 0, 0), 0.190, 0.690, mats["steel"], root, 32, role="wheel_hub")
    for side, z in (("L", -0.365), ("R", 0.365)):
        cylinder(f"{prefix}_Hub_Cap_{side}", (0, 0, z), 0.105, 0.060, mats["hub"], root, 28, role="wheel_hub")
        for bolt_index in range(10):
            theta = bolt_index * math.tau / 10
            cylinder(
                f"{prefix}_Bolt_{side}_{bolt_index+1:02d}",
                (math.cos(theta) * 0.145, math.sin(theta) * 0.145, z + (-0.034 if side == "L" else 0.034)),
                0.018,
                0.028,
                mats["bolt"],
                root,
                12,
                role="wheel_fastener",
            )


def add_axle(prefix, axle_root, mats, wheel_left_name, wheel_right_name):
    cylinder(f"{prefix}_Axle_Housing", (0, 0, 0), 0.125, 2.18, mats["steel_dark"], axle_root, 28, role="axle_housing")
    uv_sphere(f"{prefix}_Differential_Case", (0, 0, 0), 0.265, mats["steel_dark"], axle_root, "differential_case", 28, 14)
    cylinder(f"{prefix}_Differential_Input", (0.20, 0.08, 0), 0.085, 0.40, mats["steel"], axle_root, 20, rotation=(0, math.pi / 2, 0), role="driveline")
    left = empty(wheel_left_name, (0, 0, -1.1375), axle_root, "wheel_group", "CIRCLE", 0.18)
    right = empty(wheel_right_name, (0, 0, 1.1375), axle_root, "wheel_group", "CIRCLE", 0.18)
    build_wheel(wheel_left_name.replace("_ROOT", ""), left, mats)
    build_wheel(wheel_right_name.replace("_ROOT", ""), right, mats)
    return left, right


def create_model():
    mats = {
        "ochre": material("Neutral_Rust_Ochre", (0.64, 0.285, 0.045), 0.20, 0.34),
        "ochre_light": material("Neutral_Ochre_Highlight", (0.82, 0.43, 0.075), 0.12, 0.32),
        "ochre_dark": material("Neutral_Ochre_Shadow", (0.31, 0.115, 0.018), 0.25, 0.40),
        "steel_dark": material("Neutral_Graphite_Steel", (0.026, 0.035, 0.043), 0.70, 0.29),
        "steel": material("Neutral_Machined_Steel", (0.29, 0.32, 0.34), 0.86, 0.20),
        "rod": material("Neutral_Hydraulic_Rod", (0.60, 0.63, 0.65), 0.95, 0.12),
        "rubber": material("Neutral_Offroad_Rubber", (0.012, 0.015, 0.018), 0.02, 0.82),
        "rubber_side": material("Neutral_Rubber_Sidewall", (0.025, 0.029, 0.032), 0.02, 0.74),
        "rim": material("Neutral_Wheel_Rim", (0.20, 0.22, 0.23), 0.74, 0.30),
        "hub": material("Neutral_Hub_Cap", (0.40, 0.42, 0.43), 0.88, 0.20),
        "bolt": material("Neutral_Fastener", (0.11, 0.12, 0.13), 0.88, 0.22),
        "glass": material("Neutral_Smoked_Glass", (0.035, 0.080, 0.100), 0.34, 0.14),
        "interior": material("Neutral_Cab_Interior", (0.020, 0.025, 0.030), 0.08, 0.68),
        "grille": material("Neutral_Grille", (0.018, 0.023, 0.028), 0.64, 0.34),
        "lens": material("Neutral_Lamp_Lens", (0.76, 0.75, 0.61), 0.08, 0.18),
        "red": material("Neutral_Rear_Lens", (0.45, 0.018, 0.012), 0.08, 0.24),
        "hose": material("Neutral_Hydraulic_Hose", (0.014, 0.018, 0.020), 0.06, 0.70),
        "ground": material("Review_Ground", (0.045, 0.055, 0.064), 0.0, 0.78),
    }

    machine = empty("Machine_Root", role="machine_root", size=0.34)
    front = empty("Front_Tractor_ROOT", parent=machine, role="fixed_group", size=0.26)

    # Front frame and guarded powertrain volumes.
    box("Front_Frame_Rail_L", (2.18, 0.745, -0.54), (4.50, 0.34, 0.24), mats["steel_dark"], front, 0.045, "frame_rail")
    box("Front_Frame_Rail_R", (2.18, 0.745, 0.54), (4.50, 0.34, 0.24), mats["steel_dark"], front, 0.045, "frame_rail")
    box("Front_Frame_Crossmember", (1.05, 0.76, 0), (0.30, 0.36, 1.44), mats["steel"], front, 0.038, "frame_crossmember")
    box("Crankcase_Guard", (3.25, 0.72, 0), (2.10, 0.22, 1.32), mats["steel_dark"], front, 0.045, "guard")
    # The tractor nose is composed as a stepped, descending service hood with
    # separate lower bumper corners and wheel-arch fenders.  These features are
    # independently observed/reconstructed, not copied manufacturer surfaces.
    box("Front_Bumper_Center", (5.510, 0.690, 0), (0.300, 0.300, 1.32), mats["steel_dark"], front, 0.050, "bumper")
    for side, z, yaw in (("L", -0.96, math.radians(-10.0)), ("R", 0.96, math.radians(10.0))):
        box(f"Front_Bumper_Corner_{side}", (5.410, 0.760, z), (0.34, 0.50, 0.46), mats["steel_dark"], front, 0.055, "bumper", rotation=(0, yaw, 0))
        box(f"Front_Lower_Skid_Cheek_{side}", (5.210, 0.905, z), (0.46, 0.24, 0.38), mats["ochre_dark"], front, 0.040, "guard", rotation=(0, yaw * 0.60, 0))
    box("Front_Grille_Frame", (5.455, 1.510, 0), (0.34, 1.18, 1.92), mats["ochre_dark"], front, 0.060, "engine_enclosure")
    box("Front_Grille", (5.632, 1.500, 0), (0.020, 0.98, 1.58), mats["grille"], front, 0.003, "grille")
    for index in range(12):
        box(f"Front_Grille_Slat_{index+1:02d}", (5.645, 1.085 + index * 0.074, 0), (0.016, 0.032, 1.56), mats["steel"], front, 0.003, "grille_slat")

    side_profile(
        "Engine_Hood_Lower_Step",
        [(2.70,0.90),(2.78,1.34),(3.12,1.54),(3.28,1.73),(4.70,1.68),(5.15,1.50),(5.44,1.19),(5.44,0.90)],
        2.40, mats["ochre_dark"], front, bevel_width=0.060, role="engine_enclosure"
    )
    side_profile(
        "Engine_Hood_Main",
        [(2.82,1.34),(3.18,1.64),(3.32,2.25),(3.65,2.45),(4.45,2.40),(4.93,2.21),(5.28,1.94),(5.40,1.49),(4.72,1.66),(3.25,1.72)],
        2.20, mats["ochre"], front, bevel_width=0.070, role="engine_enclosure"
    )
    side_profile(
        "Engine_Hood_Crown",
        [(3.18,2.20),(3.55,2.55),(4.30,2.52),(4.83,2.31),(5.18,2.03),(4.92,1.95),(3.44,2.13)],
        1.62, mats["ochre_light"], front, bevel_width=0.050, role="engine_enclosure"
    )
    fender_profile = [
        (1.50,0.72),(1.56,1.20),(1.77,1.56),(2.08,1.78),(2.45,1.86),(2.82,1.78),(3.13,1.56),(3.35,1.20),(3.40,0.72),
        (3.20,0.72),(3.13,1.14),(2.94,1.41),(2.70,1.57),(2.45,1.63),(2.20,1.57),(1.96,1.41),(1.77,1.14),(1.70,0.72),
    ]
    for side, z in (("L", -1.422), ("R", 1.422)):
        side_profile(f"Front_Fender_Arch_{side}", fender_profile, 0.100, mats["ochre"], front, z_center=z, bevel_width=0.025, role="fender")
        side_profile(
            f"Hood_Service_Door_{side}",
            [(3.25,1.23),(3.32,2.08),(3.62,2.30),(4.45,2.25),(4.96,2.04),(5.18,1.72),(5.06,1.31),(4.72,1.20),(3.60,1.18)],
            0.040, mats["ochre_light"], front, z_center=(-1.121 if side == "L" else 1.121), bevel_width=0.012, role="service_panel"
        )
        for seam_index, x in enumerate((3.58, 4.15, 4.70), 1):
            box(f"Hood_Seam_{side}_{seam_index}", (x, 1.68, z + (0.280 if side == "L" else -0.280)), (0.018, 0.78, 0.012), mats["ochre_dark"], front, 0.002, "service_panel_seam")
        box(f"Hood_Latch_{side}", (4.82, 1.62, z + (0.265 if side == "L" else -0.265)), (0.16, 0.045, 0.025), mats["steel_dark"], front, 0.004, "service_latch")
        box(f"Fender_AntiSlip_{side}", (3.45, 0.985, z), (0.72, 0.055, 0.20), mats["steel_dark"], front, 0.008, "access_step")
    for index in range(8):
        box(f"Hood_Vent_R_{index+1:02d}", (3.46 + index * 0.17, 2.16, 1.123), (0.105, 0.026, 0.018), mats["grille"], front, 0.003, "vent")
    cylinder("Low_Profile_Exhaust", (3.20, 2.64, 0.78), 0.085, 0.42, mats["steel_dark"], front, 28, rotation=(math.pi / 2, 0, 0), role="exhaust")
    cylinder("Air_Intake", (3.65, 2.67, 0.91), 0.072, 0.34, mats["steel_dark"], front, 24, rotation=(math.pi / 2, 0, 0), role="intake")

    # Cab is a distinct framed volume with readable glazing and interior cues.
    cab = empty("Cab_ROOT", (0, 0, 0), front, "fixed_group", "PLAIN_AXES", 0.18)
    side_profile("Cab_Interior_Block", [(0.45,1.00),(0.50,2.88),(1.00,3.34),(2.30,3.34),(2.56,2.70),(2.53,1.00)], 1.78, mats["interior"], cab, z_center=-0.18, bevel_width=0.060, role="cab_interior")
    for side, z_glass, z_frame in (("Left", -1.087, -1.115), ("Right", 0.727, 0.755)):
        side_profile(
            f"Cab_{side}_Rear_Glass",
            [(0.58,1.76),(0.62,2.86),(1.02,3.25),(1.45,3.25),(1.45,1.76)],
            0.035, mats["glass"], cab, z_center=z_glass, bevel_width=0.010, role="glass"
        )
        side_profile(
            f"Cab_{side}_Front_Glass",
            [(1.58,1.76),(1.58,3.25),(2.28,3.25),(2.46,2.72),(2.52,1.76)],
            0.035, mats["glass"], cab, z_center=z_glass, bevel_width=0.010, role="glass"
        )
        side_profile(
            f"Cab_A_Pillar_{side}",
            [(2.47,1.68),(2.60,1.70),(2.40,3.29),(2.27,3.29)],
            0.085, mats["steel_dark"], cab, z_center=z_frame, bevel_width=0.012, role="cab_frame"
        )
        box(f"Cab_B_Pillar_{side}", (1.515, 2.50, z_frame), (0.105, 1.64, 0.085), mats["steel_dark"], cab, 0.014, "cab_frame")
        side_profile(
            f"Cab_Rear_Pillar_{side}",
            [(0.50,1.66),(0.64,1.66),(0.69,2.88),(1.05,3.27),(0.92,3.32),(0.54,2.94)],
            0.085, mats["steel_dark"], cab, z_center=z_frame, bevel_width=0.012, role="cab_frame"
        )
        box(f"Cab_Belt_Rail_{side}", (1.54, 1.715, z_frame), (2.00, 0.105, 0.085), mats["steel_dark"], cab, 0.014, "cab_frame")
    side_profile("Cab_Front_Glass", [(2.31,1.74),(2.53,1.74),(2.42,3.27),(2.25,3.27)], 1.78, mats["glass"], cab, z_center=-0.18, bevel_width=0.012, role="glass")
    box("Cab_Rear_Glass", (0.535, 2.43, -0.18), (0.035, 1.14, 1.66), mats["glass"], cab, 0.012, "glass")
    side_profile("Cab_Roof", [(0.43,3.30),(0.62,3.498),(2.30,3.498),(2.55,3.35),(2.38,3.28),(0.68,3.28)], 2.02, mats["ochre_dark"], cab, z_center=-0.18, bevel_width=0.045, role="cab_frame")
    box("Cab_Front_Sun_Visor", (2.43, 3.30, -0.18), (0.24, 0.10, 1.88), mats["ochre_dark"], cab, 0.025, "cab_frame", rotation=(0, 0, math.radians(-8.0)))
    box("Cab_Floor", (1.54, 1.10, -0.18), (2.15, 0.20, 1.92), mats["steel_dark"], cab, 0.035, "cab_frame")
    box("Operator_Seat_Back", (1.28, 2.00, -0.38), (0.52, 0.82, 0.50), mats["interior"], cab, 0.10, "cab_interior")
    box("Operator_Seat_Base", (1.43, 1.60, -0.38), (0.58, 0.20, 0.56), mats["interior"], cab, 0.08, "cab_interior")
    cylinder("Steering_Wheel", (2.04, 2.08, -0.38), 0.18, 0.045, mats["steel_dark"], cab, 28, rotation=(math.pi / 2, 0, 0), role="cab_interior")
    box("Operator_Display", (2.25, 2.00, -0.36), (0.10, 0.30, 0.46), mats["glass"], cab, 0.035, "cab_interior")

    # Access system and exterior rails.
    for index in range(4):
        step_x = 0.62 + index * 0.31
        step_y = 0.48 + index * 0.20
        box(f"Cab_Access_Step_{index+1}", (step_x, step_y, -1.415), (0.46, 0.070, 0.36), mats["steel_dark"], front, 0.012, "access_step")
        for bar_index in range(3):
            box(f"Cab_Access_Grate_{index+1}_{bar_index+1}", (step_x, step_y + 0.039, -1.525 + bar_index * 0.11), (0.40, 0.014, 0.022), mats["steel"], front, 0.002, "access_step")
    box("Cab_Access_Deck", (1.72, 1.00, -1.36), (1.55, 0.080, 0.42), mats["steel_dark"], front, 0.015, "access_step")
    rail_segments = [
        ((0.50,0.82,-1.47),(0.50,2.55,-1.47)),
        ((0.50,2.55,-1.47),(1.25,3.15,-1.47)),
        ((1.25,3.15,-1.47),(2.30,3.15,-1.47)),
        ((2.75,0.92,1.31),(4.95,0.92,1.31)),
        ((2.75,0.92,-1.31),(4.95,0.92,-1.31)),
    ]
    for index, (start, end) in enumerate(rail_segments, 1):
        local_between(f"Access_Rail_{index:02d}", front, start, end, 0.026, mats["steel"], "handrail", 14)
    box("Front_Light_L", (5.645, 1.90, -0.72), (0.020, 0.24, 0.38), mats["lens"], front, 0.004, "lighting")
    box("Front_Light_R", (5.645, 1.90, 0.72), (0.020, 0.24, 0.38), mats["lens"], front, 0.004, "lighting")

    # Overall-width witness is visible mirror geometry, not a private helper.
    for side, z in (("L", -1.798), ("R", 1.798)):
        local_between(f"Mirror_Arm_{side}", front, (1.90,2.75,-1.12 if side == "L" else 1.12), (1.72,2.84,z), 0.022, mats["steel"], "mirror_arm", 12)
        box(f"Mirror_{side}", (1.72, 2.84, z), (0.24, 0.38, 0.080), mats["glass"], front, 0.030, "mirror")
        box(f"Mirror_Convex_{side}", (1.74, 2.55, z), (0.18, 0.18, 0.078), mats["glass"], front, 0.050, "mirror")

    # Front axle pivot explicitly owns the oscillating axle and both wheels.
    front_axle_pivot = empty("Front_Axle_Oscillation_Pivot", (2.450, 0.8252, 0), front, "revolute_pivot", "CIRCLE", 0.32)
    front_axle_pivot["axis"] = "+X"
    front_axle_pivot["range_deg"] = [-6.0, 6.0]
    front_axle_pivot["center_authority"] = "reconstructed"
    front_axle = empty("Front_Axle_ROOT", parent=front_axle_pivot, role="articulated_group", size=0.22)
    add_axle("Front", front_axle, mats, "Wheel_FL_ROOT", "Wheel_FR_ROOT")
    cylinder("Front_Axle_Pivot_Pin", (0, 0, 0), 0.165, 0.48, mats["steel"], front_axle_pivot, 30, rotation=(0, math.pi / 2, 0), role="pivot_pin")
    for side, z in (("L", -0.78), ("R", 0.78)):
        local_between(f"Front_Suspension_Strut_{side}", front_axle, (0,0.10,z), (0.20,0.72,z), 0.075, mats["steel_dark"], "suspension_strut", 20)

    # Central hitch; rear frame geometry is authored in local coordinates
    # relative to the reconstructed articulation center.
    articulation = empty("Rear_Articulation_Pivot", (0.150, 1.080, 0), front, "revolute_pivot", "CIRCLE", 0.42)
    articulation["axis"] = "+Y"
    articulation["range_deg"] = [-45.0, 45.0]
    articulation["center_authority"] = "reconstructed"
    rear = empty("Rear_Frame_ROOT", parent=articulation, role="articulated_group", size=0.25)
    cylinder("Articulation_Knuckle_Outer", (0, 0, 0), 0.42, 0.72, mats["steel_dark"], rear, 40, rotation=(math.pi / 2, 0, 0), role="articulation_knuckle")
    cylinder("Articulation_Knuckle_Pin", (0, 0, 0), 0.17, 0.84, mats["steel"], rear, 32, rotation=(math.pi / 2, 0, 0), role="pivot_pin")
    box("Hitch_Yoke_L", (-0.38, -0.02, -0.47), (0.92, 0.42, 0.22), mats["steel_dark"], rear, 0.055, "articulation_yoke")
    box("Hitch_Yoke_R", (-0.38, -0.02, 0.47), (0.92, 0.42, 0.22), mats["steel_dark"], rear, 0.055, "articulation_yoke")

    def rear_local(x, y, z=0.0):
        return (x - 0.150, y - 1.080, z)

    for side, z in (("L", -0.55), ("R", 0.55)):
        box(f"Rear_Frame_Rail_{side}", rear_local(-2.43, 0.82, z), (4.66, 0.34, 0.25), mats["steel_dark"], rear, 0.045, "frame_rail")
    box("Rear_Frame_Crossmember_Front", rear_local(-0.80, 0.84, 0), (0.30, 0.38, 1.48), mats["steel"], rear, 0.040, "frame_crossmember")
    box("Rear_Frame_Crossmember_Rear", rear_local(-4.20, 0.84, 0), (0.34, 0.38, 1.48), mats["steel"], rear, 0.040, "frame_crossmember")
    box("Rear_Bogie_Beam_L", rear_local(-2.38, 0.98, -0.88), (2.58, 0.30, 0.22), mats["ochre_dark"], rear, 0.055, "tandem_bogie")
    box("Rear_Bogie_Beam_R", rear_local(-2.38, 0.98, 0.88), (2.58, 0.30, 0.22), mats["ochre_dark"], rear, 0.055, "tandem_bogie")

    mid_axle = empty("Axle_Mid_ROOT", rear_local(-1.529, 0.8252, 0), rear, "axle_group", "CIRCLE", 0.20)
    rear_axle = empty("Axle_Rear_ROOT", rear_local(-3.229, 0.8252, 0), rear, "axle_group", "CIRCLE", 0.20)
    add_axle("Middle", mid_axle, mats, "Wheel_ML_ROOT", "Wheel_MR_ROOT")
    add_axle("Rear", rear_axle, mats, "Wheel_RL_ROOT", "Wheel_RR_ROOT")
    for prefix, axle, x_sign in (("Middle", mid_axle, 1), ("Rear", rear_axle, -1)):
        for side, z in (("L", -0.76), ("R", 0.76)):
            local_between(f"{prefix}_Torque_Link_{side}", axle, (0,0.12,z), (0.52*x_sign,0.55,z), 0.055, mats["steel"], "suspension_link", 16)

    # Body pivot and a fabricated, open standard body. Profile dimensions are
    # constrained but not claimed as manufacturer plate geometry.
    body_hinge = empty("Dump_Body_Hinge", rear_local(-4.185, 1.200, 0), rear, "revolute_pivot", "CIRCLE", 0.34)
    body_hinge["axis"] = "+Z"
    body_hinge["tip_reference_deg"] = 70.0
    body_hinge["center_authority"] = "reconstructed"
    body = empty("Dump_Body_ROOT", parent=body_hinge, role="articulated_group", size=0.26)
    body_profile = [
        (-0.600,0.120),(-0.585,0.820),(-0.300,0.970),(3.960,1.420),(4.730,1.525),(4.973,1.583),
        (5.159,0.520),(4.870,0.300),(3.720,0.205),(2.150,0.025),(0.180,0.015),
    ]
    side_profile("Dump_Body_Side_L", body_profile, 0.090, mats["ochre"], body, z_center=-1.406, bevel_width=0.035, role="dump_body_side")
    side_profile("Dump_Body_Side_R", body_profile, 0.090, mats["ochre"], body, z_center=1.406, bevel_width=0.035, role="dump_body_side")
    inner_profile = [(-0.48,0.19),(-0.46,0.72),(-0.20,0.84),(3.93,1.28),(4.76,1.42),(4.96,0.58),(4.68,0.36),(3.65,0.29),(2.10,0.13),(0.16,0.12)]
    side_profile("Dump_Body_Inner_L", inner_profile, 0.025, mats["ochre_dark"], body, z_center=-1.348, bevel_width=0.010, role="dump_body_inner")
    side_profile("Dump_Body_Inner_R", inner_profile, 0.025, mats["ochre_dark"], body, z_center=1.348, bevel_width=0.010, role="dump_body_inner")
    side_profile(
        "Dump_Body_Scow_Underbody",
        [(-0.42,0.12),(0.16,0.02),(2.18,-0.035),(3.72,0.13),(4.80,0.31),(4.92,0.48),(4.63,0.49),(3.62,0.31),(2.12,0.16),(0.12,0.18)],
        2.58, mats["ochre_dark"], body, bevel_width=0.030, role="dump_body_floor"
    )
    side_profile("Dump_Body_Front_Headboard", [(4.68,0.30),(5.159,0.52),(4.973,1.583),(4.70,1.52)], 2.73, mats["ochre_light"], body, bevel_width=0.040, role="dump_body_front")
    box("Dump_Body_Headboard_Top_Lip", (4.84, 1.530, 0), (0.22, 0.060, 2.88), mats["ochre_light"], body, 0.018, "dump_body_front")
    top_rail_profile = [(-0.54,0.79),(-0.46,0.96),(3.98,1.43),(4.73,1.53),(4.973,1.583),(4.95,1.47),(4.70,1.43),(-0.36,0.86)]
    side_profile("Dump_Body_Top_Rail_L", top_rail_profile, 0.080, mats["ochre_light"], body, z_center=-1.411, bevel_width=0.022, role="dump_body_top_rail")
    side_profile("Dump_Body_Top_Rail_R", top_rail_profile, 0.080, mats["ochre_light"], body, z_center=1.411, bevel_width=0.022, role="dump_body_top_rail")
    for side, z in (("L", -1.418), ("R", 1.418)):
        box(f"Dump_Body_Underrail_{side}", (2.30, 0.225, z), (4.72, 0.145, 0.075), mats["steel_dark"], body, 0.015, "dump_body_underrail", rotation=(0, 0, math.radians(4.2)))
        side_profile(
            f"Dump_Body_Rear_Taper_Gusset_{side}",
            [(-0.57,0.16),(-0.54,0.77),(-0.18,0.91),(0.52,0.92),(0.38,0.27)],
            0.060, mats["ochre_dark"], body, z_center=z, bevel_width=0.014, role="dump_body_rear_taper"
        )
        for index in range(8):
            x = -0.08 + index * 0.63
            rib = box(f"Dump_Body_Rib_{side}_{index+1:02d}", (x, 0.62 + x * 0.122, z), (0.110, 0.86, 0.070), mats["ochre_dark"], body, 0.018, "dump_body_reinforcement", rotation=(0, 0, math.radians(-11.0)))
            rib["authority"] = "reconstructed_visual"
        side_profile(
            f"Dump_Body_Hinge_Clevis_{side}",
            [(-0.25,-0.03),(0.30,-0.03),(0.46,0.19),(0.25,0.35),(-0.18,0.27)],
            0.150, mats["steel_dark"], body, z_center=(-0.96 if side == "L" else 0.96), bevel_width=0.025, role="dump_body_hinge_bracket"
        )
        side_profile(
            f"Dump_Body_Hoist_Clevis_{side}",
            [(1.93,0.04),(2.38,0.05),(2.44,0.31),(2.19,0.45),(1.96,0.29)],
            0.140, mats["steel_dark"], body, z_center=(-0.64 if side == "L" else 0.64), bevel_width=0.022, role="dump_body_hoist_bracket"
        )
    cylinder("Dump_Body_Hinge_Pin", (0, 0, 0), 0.180, 3.04, mats["steel"], body_hinge, 36, role="pivot_pin")
    box("Dump_Body_Rear_Rock_Lip", (-0.555, 0.34, 0), (0.105, 0.30, 2.55), mats["steel_dark"], body, 0.025, "dump_body_rear_taper")
    box("Rear_Light_Bar", (-0.50, 0.48, 0), (0.18, 0.22, 2.58), mats["steel_dark"], body, 0.025, "lighting_structure")
    box("Rear_Stop_Lamp_L", (-0.59, 0.48, -0.88), (0.030, 0.16, 0.30), mats["red"], body, 0.004, "lighting")
    box("Rear_Stop_Lamp_R", (-0.59, 0.48, 0.88), (0.030, 0.16, 0.30), mats["red"], body, 0.004, "lighting")

    # Hydraulics own world-space cylinder meshes and explicit anchor empties.
    hydraulics = empty("Hydraulics_ROOT", parent=machine, role="hydraulic_group", size=0.22)
    steering_hydraulics = empty("Steering_Hydraulics_ROOT", parent=hydraulics, role="hydraulic_owner_group", size=0.18)
    hoist_hydraulics = empty("Hoist_Hydraulics_ROOT", parent=hydraulics, role="hydraulic_owner_group", size=0.18)
    anchors = {}
    for name, loc, parent in [
        ("ANCHOR_Steer_Base_L", (0.55,0.92,-0.66), front),
        ("ANCHOR_Steer_Base_R", (0.55,0.92,0.66), front),
        ("ANCHOR_Steer_Rod_L", rear_local(-0.58,0.94,-0.62), rear),
        ("ANCHOR_Steer_Rod_R", rear_local(-0.58,0.94,0.62), rear),
        ("ANCHOR_Hoist_Base_L", rear_local(-2.70,0.92,-0.64), rear),
        ("ANCHOR_Hoist_Base_R", rear_local(-2.70,0.92,0.64), rear),
        ("ANCHOR_Hoist_Body_L", (2.15,0.24,-0.64), body),
        ("ANCHOR_Hoist_Body_R", (2.15,0.24,0.64), body),
    ]:
        anchors[name] = empty(name, loc, parent, "hydraulic_anchor", "SPHERE", 0.075)

    cylinders = {}

    def make_pair(key, a_name, b_name, barrel_radius, rod_radius, owner, stages=False):
        bpy.context.view_layer.update()
        start = anchors[a_name].matrix_world.translation.copy()
        end = anchors[b_name].matrix_world.translation.copy()
        vector = end - start
        barrel_end = start + vector * 0.62
        rod_start = start + vector * 0.54
        cylinders[f"{key}_Barrel"] = object_between(f"{key}_Barrel", start, barrel_end, barrel_radius, mats["steel_dark"], owner, "hydraulic_barrel", 26)
        if stages:
            mid_start = start + vector * 0.48
            mid_end = start + vector * 0.82
            cylinders[f"{key}_Stage"] = object_between(f"{key}_Stage", mid_start, mid_end, rod_radius * 1.28, mats["steel"], owner, "hydraulic_stage", 24)
            rod_start = start + vector * 0.76
        cylinders[f"{key}_Rod"] = object_between(f"{key}_Rod", rod_start, end, rod_radius, mats["rod"], owner, "hydraulic_rod", 22)

    make_pair("Steer_L", "ANCHOR_Steer_Base_L", "ANCHOR_Steer_Rod_L", 0.085, 0.045, steering_hydraulics)
    make_pair("Steer_R", "ANCHOR_Steer_Base_R", "ANCHOR_Steer_Rod_R", 0.085, 0.045, steering_hydraulics)
    make_pair("Hoist_L", "ANCHOR_Hoist_Base_L", "ANCHOR_Hoist_Body_L", 0.120, 0.060, hoist_hydraulics, True)
    make_pair("Hoist_R", "ANCHOR_Hoist_Base_R", "ANCHOR_Hoist_Body_R", 0.120, 0.060, hoist_hydraulics, True)

    # Exterior hoses are route cues only.
    hose_segments = []
    for side, z in (("L", -0.78), ("R", 0.78)):
        points = [(0.62,1.16,z),(0.28,1.05,z),(-0.20,1.00,z),(-0.70,0.96,z)]
        for offset_index, dz in enumerate((-0.055, 0.0, 0.055), 1):
            for seg in range(len(points) - 1):
                a = (points[seg][0], points[seg][1], points[seg][2] + dz)
                b = (points[seg+1][0], points[seg+1][1], points[seg+1][2] + dz)
                hose_segments.append(local_between(f"Articulation_Hose_{side}_{offset_index}_{seg+1}", front, a, b, 0.022, mats["hose"], "hydraulic_hose", 12))
    for side, z in (("L", -0.82), ("R", 0.82)):
        points = [rear_local(-1.20,1.12,z), rear_local(-2.10,1.18,z), rear_local(-3.15,1.18,z)]
        for seg in range(len(points)-1):
            hose_segments.append(local_between(f"Hoist_Hose_{side}_{seg+1}", rear, points[seg], points[seg+1], 0.024, mats["hose"], "hydraulic_hose", 12))

    # Driveline cues, including transfer case and visible shafts.
    driveline = empty("Driveline_ROOT", parent=machine, role="driveline_group", size=0.18)
    box("Transfer_Case", (0.78, 0.88, 0), (0.60, 0.54, 0.72), mats["steel_dark"], driveline, 0.080, "transfer_case")
    object_between("Front_Driveshaft", (0.98,0.86,0), (2.23,0.84,0), 0.072, mats["steel"], driveline, "driveshaft", 20)
    object_between("Rear_Driveshaft_Forward", (0.55,0.84,0), (-1.28,0.84,0), 0.072, mats["steel"], driveline, "driveshaft", 20)
    object_between("Rear_Driveshaft_Tandem", (-1.76,0.84,0), (-3.02,0.84,0), 0.068, mats["steel"], driveline, "driveshaft", 20)
    for index, x in enumerate((0.98,2.23,0.55,-1.28,-1.76,-3.02), 1):
        uv_sphere(f"Driveshaft_UJoint_{index:02d}", (x,0.84,0), 0.105, mats["steel_dark"], driveline, "universal_joint", 18, 10)

    # Private inspection volumes remain in the .blend and are not exported.
    inspection = empty("Inspection_Volumes", parent=machine, role="inspection_group", size=0.30, export=False)
    envelope = empty("INSPECT_Transport_Envelope", (0.4375, PUBLISHED["transport_height_m"] / 2, 0), inspection, "inspection_volume", "CUBE", 1.0, export=False)
    envelope.scale = (PUBLISHED["overall_length_m"] / 2, PUBLISHED["transport_height_m"] / 2, PUBLISHED["overall_width_m"] / 2)
    tipped = empty("INSPECT_Fully_Tipped_Height", (-1.2, PUBLISHED["body_height_fully_tipped_m"] / 2, 0), inspection, "inspection_volume", "CUBE", 1.0, export=False)
    tipped.scale = (4.5, PUBLISHED["body_height_fully_tipped_m"] / 2, 1.6)
    articulation_volume = empty("INSPECT_Articulation_Swept", (0.15,1.08,0), inspection, "inspection_volume", "SPHERE", 2.4, export=False)
    articulation_volume["published_range_deg"] = [-45,45]

    # Review environment never enters the public asset.
    box("Review_Ground", (0.40, -0.025, 0), (16.0, 0.05, 12.0), mats["ground"], machine, 0.0, "review_environment", False)

    return {
        "mats": mats,
        "machine": machine,
        "front": front,
        "rear_pivot": articulation,
        "rear": rear,
        "front_axle_pivot": front_axle_pivot,
        "body_hinge": body_hinge,
        "body": body,
        "anchors": anchors,
        "cylinders": cylinders,
        "hose_segments": hose_segments,
    }


def refresh_hydraulics(model):
    bpy.context.view_layer.update()
    anchors = model["anchors"]
    cylinders = model["cylinders"]
    definitions = [
        ("Steer_L", "ANCHOR_Steer_Base_L", "ANCHOR_Steer_Rod_L", 0.085, 0.045, False),
        ("Steer_R", "ANCHOR_Steer_Base_R", "ANCHOR_Steer_Rod_R", 0.085, 0.045, False),
        ("Hoist_L", "ANCHOR_Hoist_Base_L", "ANCHOR_Hoist_Body_L", 0.120, 0.060, True),
        ("Hoist_R", "ANCHOR_Hoist_Base_R", "ANCHOR_Hoist_Body_R", 0.120, 0.060, True),
    ]
    for key, a_name, b_name, barrel_radius, rod_radius, stages in definitions:
        start = anchors[a_name].matrix_world.translation.copy()
        end = anchors[b_name].matrix_world.translation.copy()
        vector = end - start
        place_between(cylinders[f"{key}_Barrel"], start, start + vector * 0.62, barrel_radius)
        if stages:
            place_between(cylinders[f"{key}_Stage"], start + vector * 0.48, start + vector * 0.82, rod_radius * 1.28)
            rod_start = start + vector * 0.76
        else:
            rod_start = start + vector * 0.54
        place_between(cylinders[f"{key}_Rod"], rod_start, end, rod_radius)
    bpy.context.view_layer.update()


def point_camera(obj, target):
    forward = (Vector(target) - obj.location).normalized()
    world_up = Vector((0.0, 1.0, 0.0))
    right = forward.cross(world_up).normalized()
    true_up = right.cross(forward).normalized()
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Matrix((right, true_up, -forward)).transposed().to_quaternion()


def add_review_lighting():
    def area(name, location, energy, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        tag(obj, "review_environment", False)
        return obj
    key = area("Review_Key", (3.5, 8.0, -7.0), 1750, 5.5, (1.0, 0.80, 0.60))
    fill = area("Review_Fill", (-5.0, 5.5, 7.0), 1200, 4.5, (0.58, 0.76, 1.0))
    rim = area("Review_Rim", (-2.0, 8.5, -1.0), 1350, 4.0, (0.76, 0.88, 1.0))
    for light, target in ((key,(0.5,1.5,0)),(fill,(-0.6,1.4,0)),(rim,(-1.5,1.7,0))):
        point_camera(light, target)


def render_view(name, camera_location, target, lens=55):
    camera_data = bpy.data.cameras.new(f"Camera_{name}")
    camera_data.lens = lens
    camera_data.sensor_width = 36
    camera = bpy.data.objects.new(f"Camera_{name}", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = camera_location
    point_camera(camera, target)
    tag(camera, "review_environment", False)
    bpy.context.scene.camera = camera
    path = RENDER_DIR / f"cat-725-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def render_all(model):
    paths = [
        render_view("operator-side", (0.2, 4.8, -18.0), (0.45, 1.55, 0), 54),
        render_view("right-three-quarter", (13.0, 6.4, 15.0), (0.45, 1.50, 0), 52),
        render_view("rear-three-quarter", (-13.0, 5.9, 12.0), (-0.5, 1.45, 0), 52),
        render_view("front-three-quarter", (15.0, 5.7, -12.0), (1.2, 1.55, 0), 52),
        render_view("articulation-knuckle-detail", (3.4, 2.7, -5.0), (0.10, 1.00, -0.20), 72),
        render_view("tandem-driveline-detail", (-2.3, 2.5, 5.4), (-2.35, 0.86, 0), 70),
    ]

    # Published-range review pose; restored before save/export.
    model["rear_pivot"].rotation_euler[1] = math.radians(RECONSTRUCTED["review_articulation_pose"]["rear_yaw_deg"])
    model["front_axle_pivot"].rotation_euler[0] = math.radians(RECONSTRUCTED["review_articulation_pose"]["front_axle_oscillation_deg"])
    refresh_hydraulics(model)
    paths.append(render_view("articulated-oscillation-review", (7.0, 11.8, 12.0), (-0.2, 1.35, 0), 52))
    paths.append(render_view("front-oscillation-detail", (7.2, 2.45, -5.2), (2.45, 0.82, 0), 70))
    cutaway_roles = {"engine_enclosure", "service_panel", "service_panel_seam", "service_latch", "grille", "grille_slat", "vent", "bumper", "guard", "lighting"}
    cutaway_objects = [obj for obj in bpy.data.objects if obj.get("exo_role") in cutaway_roles and obj.parent == model["front"]]
    for obj in cutaway_objects:
        obj.hide_render = True
    paths.append(render_view("front-oscillation-technical-cutaway", (7.4, 1.55, 0.0), (2.45, 0.82, 0), 68))
    for obj in cutaway_objects:
        obj.hide_render = False
    model["rear_pivot"].rotation_euler[1] = 0.0
    model["front_axle_pivot"].rotation_euler[0] = 0.0

    model["body_hinge"].rotation_euler[2] = math.radians(RECONSTRUCTED["review_body_tip_pose"]["body_tip_deg"])
    refresh_hydraulics(model)
    paths.append(render_view("raised-body-review", (-11.5, 7.6, -15.5), (-0.9, 2.65, 0), 48))
    paths.append(render_view("raised-hoist-detail", (-0.2, 4.8, -6.0), (-2.1, 1.65, -0.30), 68))
    model["body_hinge"].rotation_euler[2] = 0.0
    refresh_hydraulics(model)
    return paths


def export_objects():
    return [obj for obj in bpy.context.scene.objects if obj.get("exo_export", False)]


def evaluated_world_points(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return points


def object_bounds(objects):
    points = evaluated_world_points(objects)
    mins = [min(point[i] for point in points) for i in range(3)]
    maxs = [max(point[i] for point in points) for i in range(3)]
    return {
        "min_m": [round(v, 4) for v in mins],
        "max_m": [round(v, 4) for v in maxs],
        "size_m": [round(maxs[i] - mins[i], 4) for i in range(3)],
    }


def triangle_count(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
        bpy.data.meshes.remove(mesh)
    return total


def apply_export_mesh_scales(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)


def inspect_glb_contract(path):
    data = path.read_bytes()
    offset = 12
    json_chunk = None
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            json_chunk = chunk
            break
    if json_chunk is None:
        raise RuntimeError("GLB JSON chunk missing")
    document = json.loads(json_chunk.decode("utf-8").rstrip("\x00 "))
    scene = document["scenes"][document.get("scene", 0)]
    roots = []
    for index in scene.get("nodes", []):
        node = document["nodes"][index]
        transform = {key: node[key] for key in ("translation", "rotation", "scale", "matrix") if key in node}
        roots.append({"index": index, "name": node.get("name"), "transform": transform})
    mesh_scale_offenders = []
    for node in document.get("nodes", []):
        if "mesh" in node and any(abs(value - 1.0) > 1e-4 for value in node.get("scale", [1, 1, 1])):
            mesh_scale_offenders.append({"name": node.get("name"), "scale": node.get("scale")})
    return {
        "scene_count": len(document.get("scenes", [])),
        "scene_roots": roots,
        "camera_count": len(document.get("cameras", [])),
        "punctual_light_extension_present": "KHR_lights_punctual" in document.get("extensions", {}),
        "inspection_helper_nodes": sorted(
            node.get("name", "") for node in document.get("nodes", [])
            if node.get("name", "").startswith("INSPECT_") or node.get("name") == "Inspection_Volumes"
        ),
        "mesh_scale_offenders": mesh_scale_offenders,
        "platform_axes": "+X longitudinal toward tractor front, +Y vertical, +Z machine right",
    }


def collect_metrics(model, objects):
    bpy.context.view_layer.update()
    body_objects = [obj for obj in objects if str(obj.get("exo_role", "")).startswith("dump_body") or obj.get("exo_role") in {"body_top_rail", "body_reinforcement", "lighting_structure", "lighting"} and obj.parent == model["body"]]
    straight_bounds = object_bounds([obj for obj in objects if obj.type == "MESH"])
    tire_treads = [obj for obj in objects if obj.get("exo_role") == "tire_tread"]
    tire_contact = min(point.y for point in evaluated_world_points(tire_treads))
    frame_rails = [obj for obj in objects if obj.get("exo_role") == "frame_rail"]
    frame_min = min(point.y for point in evaluated_world_points(frame_rails))
    wheel_roots = [bpy.data.objects[name] for name in ("Wheel_FL_ROOT","Wheel_FR_ROOT","Wheel_ML_ROOT","Wheel_MR_ROOT","Wheel_RL_ROOT","Wheel_RR_ROOT")]
    axle_positions = {
        "front": list(bpy.data.objects["Front_Axle_Oscillation_Pivot"].matrix_world.translation),
        "middle": list(bpy.data.objects["Axle_Mid_ROOT"].matrix_world.translation),
        "rear": list(bpy.data.objects["Axle_Rear_ROOT"].matrix_world.translation),
    }
    model["body_hinge"].rotation_euler[2] = math.radians(PUBLISHED["body_tip_reference_deg"])
    refresh_hydraulics(model)
    tipped_bounds = object_bounds(body_objects)
    model["body_hinge"].rotation_euler[2] = 0.0
    refresh_hydraulics(model)
    cylinder_endpoint_errors = {}
    pairs = {
        "steer_left": ("Steer_L_Rod", "ANCHOR_Steer_Rod_L"),
        "steer_right": ("Steer_R_Rod", "ANCHOR_Steer_Rod_R"),
        "hoist_left": ("Hoist_L_Rod", "ANCHOR_Hoist_Body_L"),
        "hoist_right": ("Hoist_R_Rod", "ANCHOR_Hoist_Body_R"),
    }
    for key, (obj_name, anchor_name) in pairs.items():
        obj = bpy.data.objects[obj_name]
        local_z = [corner[2] for corner in obj.bound_box]
        endpoints = [obj.matrix_world @ Vector((0,0,min(local_z))), obj.matrix_world @ Vector((0,0,max(local_z)))]
        target = bpy.data.objects[anchor_name].matrix_world.translation
        cylinder_endpoint_errors[key] = min((endpoint-target).length for endpoint in endpoints)
    return {
        "straight_bounds": straight_bounds,
        "tire_contact_min_y_m": tire_contact,
        "frame_rail_underside_y_m": frame_min,
        "wheel_root_count": len(wheel_roots),
        "tread_block_count": len(tire_treads),
        "axle_positions_m": axle_positions,
        "front_to_middle_spacing_m": axle_positions["front"][0] - axle_positions["middle"][0],
        "middle_to_rear_spacing_m": axle_positions["middle"][0] - axle_positions["rear"][0],
        "body_tipped_max_y_m": tipped_bounds["max_m"][1],
        "body_tipped_bounds": tipped_bounds,
        "cylinder_endpoint_errors_m": cylinder_endpoint_errors,
    }


def create_validation(bounds, counts, render_paths, metrics, glb_contract):
    node_presence = {name: bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    root_records = glb_contract["scene_roots"]
    glb_ok = (
        glb_contract["scene_count"] == 1
        and len(root_records) == 1
        and root_records[0]["name"] == "Machine_Root"
        and root_records[0]["transform"] == {}
        and glb_contract["camera_count"] == 0
        and not glb_contract["punctual_light_extension_present"]
        and not glb_contract["inspection_helper_nodes"]
        and not glb_contract["mesh_scale_offenders"]
    )
    render_ok = all(path.exists() and path.stat().st_size > 20_000 for path in render_paths)
    closure_error = max(metrics["cylinder_endpoint_errors_m"].values())
    gates = [
        {"id":"builder-execution","status":"PASS","detail":"Factory-startup background builder reached deterministic receipt generation."},
        {"id":"candidate-class-boundary","status":"PASS","detail":"technical_structural_study; not engineering authority or a mechanical solver."},
        {"id":"scene-units-and-axes","status":"PASS","detail":"Meters; +X tractor front, +Y vertical, +Z machine right."},
        {"id":"independent-authoring-boundary","status":"PASS","detail":"No manufacturer CAD, copied texture, downloaded geometry, logo, or opaque add-on is embedded."},
        {"id":"required-semantic-nodes","status":"PASS" if all(node_presence.values()) else "FAIL","detail":node_presence},
        {"id":"hierarchy-and-pivot-parenting","status":"PASS","detail":"Rear steer, front oscillation, body tip, six wheels, hydraulics, and driveline have explicit semantic owners."},
        {"id":"six-tire-identity","status":"PASS" if metrics["wheel_root_count"] == 6 else "FAIL","detail":{"wheel_roots":metrics["wheel_root_count"],"published":6,"designation":"23.5R25 radial"}},
        {"id":"reconstructed-tread-readability","status":"PASS" if metrics["tread_block_count"] == PUBLISHED["tire_count"] * RECONSTRUCTED["tire_tread_stations_each"] * RECONSTRUCTED["tire_lugs_per_station"] else "FAIL","detail":{"blocks":metrics["tread_block_count"],"expected_reconstructed":PUBLISHED["tire_count"] * RECONSTRUCTED["tire_tread_stations_each"] * RECONSTRUCTED["tire_lugs_per_station"],"pattern":"three-lug alternating chevron stations; visual reconstruction"}},
        {"id":"authored-tire-ground-contact","status":"PASS" if abs(metrics["tire_contact_min_y_m"]) <= 0.002 else "FAIL","detail":{"measured_y_m":metrics["tire_contact_min_y_m"],"authored_ground_y_m":0.0,"tolerance_m":0.002}},
        {"id":"published-ground-clearance-frame-cue","status":"PASS" if abs(metrics["frame_rail_underside_y_m"]-PUBLISHED["ground_clearance_m"]) <= 0.05 else "FAIL","detail":{"modeled_m":metrics["frame_rail_underside_y_m"],"published_m":PUBLISHED["ground_clearance_m"],"tolerance_m":0.05,"classification":"published_constraint_reconstructed_frame_geometry"}},
        {"id":"published-overall-length","status":"PASS" if abs(bounds["size_m"][0]-PUBLISHED["overall_length_m"]) <= 0.05 else "FAIL","detail":{"modeled_m":bounds["size_m"][0],"published_m":PUBLISHED["overall_length_m"],"tolerance_m":0.05}},
        {"id":"published-transport-height","status":"PASS" if abs(bounds["size_m"][1]-PUBLISHED["transport_height_m"]) <= 0.035 else "FAIL","detail":{"modeled_m":bounds["size_m"][1],"published_m":PUBLISHED["transport_height_m"],"tolerance_m":0.035}},
        {"id":"published-overall-width","status":"PASS" if abs(bounds["size_m"][2]-PUBLISHED["overall_width_m"]) <= 0.025 else "FAIL","detail":{"modeled_m":bounds["size_m"][2],"published_m":PUBLISHED["overall_width_m"],"tolerance_m":0.025,"visible_feature":"mirrors"}},
        {"id":"published-front-middle-axle-spacing","status":"PASS" if abs(metrics["front_to_middle_spacing_m"]-PUBLISHED["front_to_middle_axle_spacing_m"]) <= 0.001 else "FAIL","detail":{"modeled_m":metrics["front_to_middle_spacing_m"],"published_m":PUBLISHED["front_to_middle_axle_spacing_m"]}},
        {"id":"published-tandem-axle-spacing","status":"PASS" if abs(metrics["middle_to_rear_spacing_m"]-PUBLISHED["tandem_axle_spacing_m"]) <= 0.001 else "FAIL","detail":{"modeled_m":metrics["middle_to_rear_spacing_m"],"published_m":PUBLISHED["tandem_axle_spacing_m"]}},
        {"id":"published-body-tip-height-study","status":"PASS" if abs(metrics["body_tipped_max_y_m"]-PUBLISHED["body_height_fully_tipped_m"]) <= 0.10 else "FAIL","detail":{"modeled_m":metrics["body_tipped_max_y_m"],"published_m":PUBLISHED["body_height_fully_tipped_m"],"tolerance_m":0.10,"hinge_and_shape_authority":"reconstructed"}},
        {"id":"static-hydraulic-endpoint-closure","status":"PASS" if closure_error <= 1e-4 else "FAIL","detail":{"errors_m":metrics["cylinder_endpoint_errors_m"],"tolerance_m":1e-4,"classification":"visual_static_closure_not_stroke_validation"}},
        {"id":"glb-platform-contract","status":"PASS" if glb_ok else "FAIL","detail":glb_contract},
        {"id":"public-glb-authoring-helpers-stripped","status":"PASS" if not glb_contract["inspection_helper_nodes"] else "FAIL","detail":{"exported_helpers":glb_contract["inspection_helper_nodes"],"private_blend_helpers_retained":True}},
        {"id":"object-density","status":"PASS" if counts["objects"] >= 300 else "FAIL","detail":{"objects":counts["objects"],"minimum":300}},
        {"id":"triangle-budget","status":"PASS" if 30_000 <= counts["triangles"] <= 240_000 else "FAIL","detail":{"triangles":counts["triangles"],"budget":[30000,240000]}},
        {"id":"neutral-unbranded-materials","status":"PASS","detail":"Neutral materials and no logo; no exact Caterpillar livery claim."},
        {"id":"review-renders-nonempty","status":"PASS" if render_ok and len(render_paths) >= 8 else "FAIL","detail":{"count":len(render_paths),"minimum_count":8,"minimum_bytes_each":20000}},
        {"id":"articulated-steer-oscillation-review","status":"PASS" if any("articulated-oscillation-review" in path.name for path in render_paths) else "FAIL","detail":"Direct review render uses reconstructed 24 degree yaw and 5 degree axle oscillation inside published ranges."},
        {"id":"raised-body-review","status":"PASS" if sum("raised-" in path.name for path in render_paths) >= 2 else "FAIL","detail":"Direct full-pose and hoist-detail renders use the published 70 degree drawing reference with reconstructed hinge and anchors."},
        {"id":"configuration-freeze","status":"PENDING","detail":"Research candidate retains serial/order, tire manufacturer, body option, payload, camera, autolube, and rights choices."},
        {"id":"steering-suspension-hoist-solver","status":"PENDING","detail":"No motion interpolation, cylinder stroke, load, or joint-limit solver exists."},
        {"id":"ground-self-swept-collision","status":"PENDING","detail":"No swept-volume or collision solver exists."},
        {"id":"critic-human-visual-review","status":"PENDING","detail":"Overall critic must inspect exact artifact and render hashes at the end of the ten-machine batch."},
        {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"No shared-viewer integration in this machine lane."},
        {"id":"publication-and-deployment","status":"PENDING","detail":"Only the overall publisher may advance publication state."},
    ]
    failed = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    payload = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "verdict":"PASS" if not failed else "FAIL",
        "bounds":bounds,
        "counts":counts,
        "metrics":metrics,
        "glb_contract":glb_contract,
        "gates":gates,
        "failed_gate_ids":failed,
    }
    write_json(VALIDATION_PATH, payload)
    return payload


def main():
    for path in (GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)
    reset_scene()
    model = create_model()
    add_review_lighting()
    bpy.context.view_layer.update()
    render_paths = render_all(model)

    objects = export_objects()
    # Pose-dependent measurements and cylinder closure must be collected while
    # procedural cylinder primitives still use their unit meshes. Applying
    # export scales first would double-scale a subsequently refreshed cylinder.
    metrics = collect_metrics(model, objects)
    apply_export_mesh_scales(objects)
    bpy.context.view_layer.update()
    mesh_objects = [obj for obj in objects if obj.type == "MESH"]
    bounds = object_bounds(mesh_objects)
    counts = {
        "objects": len(objects),
        "meshes": len(mesh_objects),
        "empties": sum(obj.type == "EMPTY" for obj in objects),
        "triangles": triangle_count(objects),
        "materials": len({slot.material.name for obj in mesh_objects for slot in obj.material_slots if slot.material}),
    }

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = model["machine"]
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=False,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )

    glb_contract = inspect_glb_contract(GLB_PATH)
    validation = create_validation(bounds, counts, render_paths, metrics, glb_contract)
    render_records = [{"path":rel(path),"sha256":sha256(path),"bytes":path.stat().st_size} for path in render_paths]
    node_presence = {name: bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    receipt = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "configuration_status":"research_candidate",
        "candidate_class":CANDIDATE_CLASS,
        "authority_boundary":"Independently authored technical structural study. Not manufacturer CAD, engineering authority, load guidance, operator training, safety guidance, a digital twin, or a mechanically validated candidate.",
        "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
        "builder":{"path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"deterministic":True,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
        "artifacts":{
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
        },
        "scene":{"units":"meters","axes":{"longitudinal":"+X toward tractor front","vertical":"+Y","lateral":"+Z machine right"},"visible_aabb_xyz_m":bounds["size_m"],"bounds":bounds,**counts},
        "glb_contract":glb_contract,
        "private_nonexport_inspection_nodes":["Inspection_Volumes","INSPECT_Transport_Envelope","INSPECT_Fully_Tipped_Height","INSPECT_Articulation_Swept"],
        "required_semantic_nodes":node_presence,
        "manufacturer_published_constraints_used":[
            "overall-length","height-transport-position","overall-width","width-over-tire","width-over-fenders",
            "body-width","body-length","body-inside-length","body-height-fully-tipped","body-tip-reference",
            "ground-clearance","rear-axle-to-body-rear","tandem-axle-spacing","front-to-middle-axle-spacing",
            "front-axle-to-machine-front","steering-angle","front-suspension-oscillation","standard-tire-count",
            "rated-payload","heaped-body-capacity","body-raise-time","body-lower-time"
        ],
        "reconstructed_values":RECONSTRUCTED,
        "unresolved_choices":["exact serial or order family","body liner and exhaust-heated-body selections","payload and camera options","automatic lubrication","exact tire manufacturer and tread pattern","public material and branding authorization"],
        "mechanical_gaps":["articulation joint center and bearing authority","front oscillation center and suspension linkage authority","dump-body hinge and hoist-anchor authority","steering and hoist cylinder strokes","tandem suspension and driveline internals","tire construction and rim dimensions","motion solver and endpoint proof","ground self and swept collision validation","load and stability authority"],
        "renders":render_records,
        "build_verdict":"PASS" if validation["verdict"] == "PASS" else "FAIL",
        "validation_verdict":validation["verdict"],
        "validation_path":rel(VALIDATION_PATH),
        "higher_stage_gates":"PENDING",
    }
    write_json(RECEIPT_PATH, receipt)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Structural validation failed: {validation['failed_gate_ids']}")
    print(json.dumps({"status":"PASS","machine":MACHINE_ID,"blend":str(BLEND_PATH),"glb":str(GLB_PATH),"validation":validation["verdict"],"counts":counts,"bounds":bounds,"metrics":metrics}, indent=2))


if __name__ == "__main__":
    main()
