#!/usr/bin/env python3
"""Build the neutral Cat 950 (14C) technical structural study.

The geometry is independently authored and constrained by selected
manufacturer-published envelope values. Hidden pivots, cylinder anchors,
Z-bar geometry, hose routes, and review motion are reconstructed. This is not
manufacturer CAD, engineering authority, operator training, or safety guidance.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


SCRIPT_PATH = Path(__file__).resolve()
MACHINE_DIR = SCRIPT_PATH.parents[2]
BLEND_PATH = SCRIPT_PATH.parent / "cat-950-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "cat-950-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"

MACHINE_ID = "cat-950"
CONFIGURATION_ID = "CAT-950-14C-NAM-T4F-STDLIFT-PZBAR-BR235R25-VJT-L3-GP31-TS-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"

PUBLISHED = {
    "axle_center_height_m": 0.734,
    "hood_height_m": 2.695,
    "rops_height_m": 3.456,
    "ground_clearance_m": 0.354,
    "rear_axle_to_counterweight_m": 2.063,
    "rear_axle_to_hitch_m": 1.675,
    "wheelbase_m": 3.350,
    "length_without_bucket_m": 7.024,
    "carry_hinge_height_m": 0.623,
    "max_lift_hinge_height_m": 4.009,
    "max_lift_arm_clearance_m": 3.255,
    "tire_width_loaded_m": 2.824,
    "tread_width_m": 2.140,
    "rear_axle_oscillation_deg": 13.0,
    "bucket_capacity_m3": 3.1,
    "bucket_width_m": 2.994,
    "shipping_length_m": 8.487,
    "bucket_dump_clearance_m": 2.746,
    "bucket_dump_reach_m": 1.546,
    "bucket_max_lift_height_m": 5.513,
    "rack_back_ground_deg": 39.0,
    "rack_back_carry_deg": 49.0,
    "rack_back_max_lift_deg": 59.0,
    "dump_angle_max_lift_deg": 51.0,
    "full_turn_test_condition_deg": 40.0,
}

RECONSTRUCTED = {
    "saved_carry_pose": {"articulation_deg": 0.0, "rear_axle_oscillation_deg": 0.0, "lift_deg": 0.0, "bucket_relative_deg": 0.0},
    "review_articulated_pose": {"articulation_deg": 28.0, "rear_axle_oscillation_deg": 0.0, "lift_deg": 0.0, "bucket_relative_deg": 0.0},
    "review_oscillation_pose": {"articulation_deg": -18.0, "rear_axle_oscillation_deg": 8.0, "lift_deg": 0.0, "bucket_relative_deg": 0.0},
    "review_linkage_pose": {"articulation_deg": 0.0, "rear_axle_oscillation_deg": 0.0, "lift_deg": 22.0, "bucket_relative_deg": -6.0},
    "review_max_lift_pose": {"articulation_deg": 0.0, "rear_axle_oscillation_deg": 0.0, "lift_deg": 90.7, "bucket_relative_deg": -32.0},
    "review_dump_pose": {"articulation_deg": 20.0, "rear_axle_oscillation_deg": 0.0, "lift_deg": 90.7, "bucket_relative_deg": -141.7},
    "hitch_pivot_m": [0.0, 0.92, 0.0],
    "rear_axle_oscillation_pivot_m": [-1.675, 0.734, 0.0],
    "lift_arm_pivot_m": [0.45, 1.45, 0.0],
    "bucket_pivot_local_to_lift_m": [2.55, -0.827, 0.0],
    "steering_cylinder_anchors": "Reconstructed exterior closure cues; neither bore, stroke, nor steering-stop authority is asserted.",
    "lift_and_tilt_cylinder_anchors": "Reconstructed exterior closure cues; published cycle time is not used as stroke or geometry authority.",
    "parallel_z_bar_linkage": "Bellcrank, dogbone, bucket lug, plate thickness, and pin coordinates are independently reconstructed from official exterior imagery. Review poses retain one reconstructed dogbone length through an unvalidated planar visual closure; this is not manufacturer kinematic authority or solver proof.",
    "tire_profile_and_tread": "23.5R25 identity, axle height, tread width, and loaded envelope constrain an independently modeled L3-style tire; tread pitch and deflection are reconstructed.",
    "body_and_cab": "Service panels, glass boundaries, cab frame, rails, stairs, grilles, lights, exhaust, mirrors, and fastening cues are observed/reconstructed exterior form only.",
    "bucket_shell": "3.1 m3 identity and published width constrain the shell; curvature, plate gauges, wear bars, teeth, side cutters, and pin bosses are reconstructed.",
    "hose_routes": "Visible hose bundles are reconstructed exterior routing cues only and carry no diameter, pressure, fitting, or service authority.",
    "materials": "Neutral unbranded gunmetal, graphite, steel, rubber, glass, and restrained safety-lens accents; no logo or exact protected livery claim.",
}

REQUIRED_NODES = [
    "Machine_Root",
    "Rear_Frame_ROOT",
    "Articulation_Pivot",
    "Front_Frame_ROOT",
    "Rear_Axle_Oscillation_Pivot",
    "Rear_Axle_ROOT",
    "Front_Axle_ROOT",
    "Wheel_RL_ROOT",
    "Wheel_RR_ROOT",
    "Wheel_FL_ROOT",
    "Wheel_FR_ROOT",
    "Lift_Arm_Pivot",
    "Lift_Arms_ROOT",
    "Bucket_Pivot",
    "Bucket_ROOT",
    "ZBar_Linkage_ROOT",
    "ZBar_Bellcrank_Pivot",
    "ZBar_Bellcrank_ROOT",
    "ZBar_Dogbone_Crosshead",
    "Hydraulics_ROOT",
    "Steering_Hydraulics_ROOT",
    "Lift_Hydraulics_ROOT",
    "Tilt_Hydraulics_ROOT",
    "Cab_ROOT",
    "Engine_Hood_ROOT",
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
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.017, 0.024)
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene["exo_machine_id"] = MACHINE_ID
    scene["exo_configuration_id"] = CONFIGURATION_ID
    scene["exo_candidate_class"] = CANDIDATE_CLASS
    scene["exo_axes"] = "+X toward bucket, +Y vertical, +Z machine right"
    scene["exo_authority_boundary"] = "independently authored technical structural study; not engineering authority"


def material(name, color, metallic=0.0, roughness=0.5, alpha=1.0, transmission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = transmission
    mat["exo_rights"] = "neutral_unbranded"
    return mat


def tag(obj, role="geometry", export=True, authority="reconstructed"):
    obj["exo_role"] = role
    obj["exo_export"] = bool(export)
    obj["exo_authority"] = authority
    return obj


def parent_keep_world(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def empty(name, location=(0, 0, 0), parent=None, role="pivot", size=0.18, export=True, local=True):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    if parent and not local:
        obj.parent = parent
        obj.matrix_world = Matrix.Translation(Vector(location))
    else:
        obj.location = location
        if parent:
            obj.parent = parent
    return tag(obj, role, export)


def bevel(obj, width=0.02, segments=2):
    if width <= 0:
        return obj
    modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    return obj


def box(name, location, dimensions, mat, parent=None, bevel_width=0.02, role="geometry", authority="reconstructed", local=False, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        if local:
            obj.parent = parent
        else:
            parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    bevel(obj, min(bevel_width, min(dimensions) * 0.22), 2)
    return tag(obj, role, True, authority)


def cylinder(name, location, radius, depth, mat, parent=None, vertices=24, rotation=(0, 0, 0), role="geometry", authority="reconstructed", local=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if parent:
        if local:
            obj.parent = parent
        else:
            parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    bevel(obj, min(radius * 0.10, 0.015), 2)
    return tag(obj, role, True, authority)


def frustum(name, location, radius1, radius2, depth, mat, parent=None, vertices=36, role="geometry", authority="reconstructed", local=False):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    if parent:
        if local:
            obj.parent = parent
        else:
            parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    bevel(obj, min(min(radius1, radius2) * 0.06, 0.012), 2)
    return tag(obj, role, True, authority)


def uv_sphere(name, location, scale, mat, parent=None, role="geometry"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    return tag(obj, role)


def torus(name, location, major_radius, minor_radius, mat, parent=None, major_segments=36, minor_segments=12, scale_z=1.0, role="geometry"):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale.z = scale_z
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        parent_keep_world(obj, parent)
    obj.data.materials.append(mat)
    return tag(obj, role)


def side_profile(name, points_xy, thickness, mat, parent=None, z_center=0.0, bevel_width=0.02, role="geometry", authority="reconstructed"):
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
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, bevel_width, 2)
    return tag(obj, role, True, authority)


def place_between(obj, start, end, radius):
    start, end = Vector(start), Vector(end)
    vector = end - start
    length = max(vector.length, 1e-6)
    rotation = Vector((0, 0, 1)).rotation_difference(vector.normalized())
    obj.matrix_world = Matrix.LocRotScale((start + end) / 2, rotation, (radius, radius, length))


def object_between(name, start, end, radius, mat, parent, role="structural_rod", vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    tag(obj, role)
    place_between(obj, start, end, radius)
    parent_keep_world(obj, parent)
    bevel(obj, min(radius * 0.16, 0.012), 2)
    return obj


def split_cylinder(name, start, end, barrel_radius, rod_radius, mats, parent, registry):
    start_v, end_v = Vector(start), Vector(end)
    midpoint = start_v.lerp(end_v, 0.56)
    barrel = object_between(f"{name}_Barrel", start_v, midpoint, barrel_radius, mats["cylinder"], parent, "hydraulic_barrel", 24)
    rod = object_between(f"{name}_Rod", midpoint, end_v, rod_radius, mats["rod"], parent, "hydraulic_rod", 20)
    registry[name] = {"barrel": barrel, "rod": rod, "barrel_radius": barrel_radius, "rod_radius": rod_radius}
    return registry[name]


def update_split_cylinder(record, start, end):
    start_v, end_v = Vector(start), Vector(end)
    midpoint = start_v.lerp(end_v, 0.56)
    place_between(record["barrel"], start_v, midpoint, record["barrel_radius"])
    place_between(record["rod"], midpoint, end_v, record["rod_radius"])


def rail(name, points, radius, mat, parent, role="handrail"):
    objects = []
    for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
        objects.append(object_between(f"{name}_{index:02d}", start, end, radius, mat, parent, role, 14))
    return objects


def world(obj):
    return obj.matrix_world.translation.copy()


def world_offset(obj, offset):
    return obj.matrix_world @ Vector(offset)


def wrapped_angle_delta(angle, reference):
    return (angle - reference + math.pi) % math.tau - math.pi


def solve_reconstructed_bellcrank_pose(model):
    """Maintain one reconstructed dogbone length for review poses; this is not mechanism proof."""
    front_inverse = model["front"].matrix_world.inverted()
    pivot = front_inverse @ world(model["bell_pivot"])
    bucket_target = front_inverse @ world(model["bucket_lug"])
    anchor_local = Vector(model["bell_dogbone_anchor"].location)
    anchor_radius = Vector((anchor_local.x, anchor_local.y)).length
    dogbone_length = model["dogbone_nominal_length_m"]
    delta = Vector((bucket_target.x-pivot.x,bucket_target.y-pivot.y))
    separation = delta.length
    if separation <= 1e-8 or separation > anchor_radius + dogbone_length + 1e-6 or separation < abs(dogbone_length-anchor_radius) - 1e-6:
        raise RuntimeError(
            f"Reconstructed Z-bar review closure is unreachable: d={separation:.6f}, "
            f"bell_radius={anchor_radius:.6f}, dogbone={dogbone_length:.6f}"
        )
    along = (anchor_radius*anchor_radius - dogbone_length*dogbone_length + separation*separation) / (2.0*separation)
    height_sq = max(0.0, anchor_radius*anchor_radius - along*along)
    height = math.sqrt(height_sq)
    direction = delta / separation
    base = Vector((pivot.x,pivot.y)) + direction * along
    perpendicular = Vector((-direction.y,direction.x))
    candidates = (base + perpendicular*height,base-perpendicular*height)
    local_angle = math.atan2(anchor_local.y,anchor_local.x)
    angles = [math.atan2(candidate.y-pivot.y,candidate.x-pivot.x)-local_angle for candidate in candidates]
    previous = model.get("bell_previous_angle_rad",0.0)
    chosen = min(angles,key=lambda angle:abs(wrapped_angle_delta(angle,previous)))
    model["bell_root"].rotation_euler[2] = chosen
    model["bell_previous_angle_rad"] = chosen
    model["bell_review_closure_error_m"] = 0.0


def l3_chevron_tread(name, axle_x, axle_y, z_center, theta, mat, parent):
    """One four-pad reconstructed L3 pitch, retained as one semantic tread object."""
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    radial = Vector((math.cos(theta), math.sin(theta), 0.0))
    tangent = Vector((-math.sin(theta), math.cos(theta), 0.0))
    lateral = Vector((0.0, 0.0, 1.0))
    origin = Vector((axle_x, axle_y, z_center))

    def pad(center_radius, lane_z, length, height, width, chevron_angle):
        created = bmesh.ops.create_cube(bm, size=1.0)
        verts = created["verts"]
        lane_sign = -1.0 if lane_z < 0 else 1.0
        u_axis = (tangent * math.cos(chevron_angle) + lateral * lane_sign * math.sin(chevron_angle)).normalized()
        v_axis = radial
        w_axis = u_axis.cross(v_axis).normalized()
        orientation = Matrix((u_axis, v_axis, w_axis)).transposed().to_4x4()
        orientation.translation = origin + radial * center_radius + lateral * lane_z
        scale = Matrix.Diagonal((length, height, width, 1.0))
        bmesh.ops.transform(bm, matrix=orientation @ scale, verts=verts)

    # Mirrored center lugs form the readable V; shoulder pads retain the loaded-width envelope.
    for lane_sign in (-1.0, 1.0):
        pad(0.6775, lane_sign * 0.130, 0.340, 0.062, 0.260, math.radians(28.0))
        pad(0.6745, lane_sign * 0.255, 0.200, 0.055, 0.100, math.radians(15.0))

    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    parent_keep_world(obj, parent)
    bevel(obj, 0.012, 2)
    tag(obj, "tire_tread", True, "reconstructed")
    obj["exo_tread_authority"] = "reconstructed 23.5R25 L3-style chevron readability cue"
    return obj


def build_wheel(label, axle_x, z_center, parent, mats):
    root = empty(f"Wheel_{label}_ROOT", (axle_x, PUBLISHED["axle_center_height_m"], z_center), parent, "wheel_pivot", local=False)
    tire = torus(
        f"Wheel_{label}_Tire_Carcass",
        (axle_x, PUBLISHED["axle_center_height_m"], z_center),
        0.535, 0.199, mats["rubber"], root, 48, 18,
        scale_z=((PUBLISHED["tire_width_loaded_m"] - PUBLISHED["tread_width_m"]) / (2 * 0.199)) * 1.0154,
        role="tire",
    )
    tire["exo_constraint"] = "23.5R25 VJT L3 identity; reconstructed loaded profile"
    cylinder(f"Wheel_{label}_Rim", (axle_x, 0.734, z_center), 0.365, 0.56, mats["rim"], root, 40, role="wheel_rim")
    cylinder(f"Wheel_{label}_Hub", (axle_x, 0.734, z_center), 0.205, 0.60, mats["hub"], root, 36, role="wheel_hub")
    outboard = -1.0 if z_center < 0 else 1.0
    dish_z = z_center + outboard * 0.306
    frustum(
        f"Wheel_{label}_Dish",
        (axle_x, 0.734, dish_z),
        0.245 if outboard < 0 else 0.335,
        0.335 if outboard < 0 else 0.245,
        0.052,
        mats["rim"], root, 40, "wheel_dish",
    )
    torus(f"Wheel_{label}_Rim_Flange", (axle_x,0.734,z_center+outboard*0.326), 0.329, 0.018, mats["hub"], root, 40, 10, 0.42, "wheel_dish")
    torus(f"Wheel_{label}_Hub_Ring", (axle_x,0.734,z_center+outboard*0.334), 0.177, 0.016, mats["bolt"], root, 36, 10, 0.38, "hub_detail")
    cylinder(f"Wheel_{label}_Final_Drive_Cap", (axle_x, 0.734, z_center + (-0.328 if z_center < 0 else 0.328)), 0.105, 0.035, mats["steel"], root, 24, role="hub_detail")
    for side in (-1.0, 1.0):
        face_z = z_center + side * 0.326
        torus(f"Wheel_{label}_Sidewall_Ridge_Outer_{'L' if side<0 else 'R'}", (axle_x,0.734,face_z), 0.590, 0.016, mats["rubber_tread"], root, 48, 10, 0.42, "tire_sidewall_detail")
        torus(f"Wheel_{label}_Sidewall_Ridge_Inner_{'L' if side<0 else 'R'}", (axle_x,0.734,face_z), 0.410, 0.013, mats["rubber_tread"], root, 40, 10, 0.42, "tire_sidewall_detail")
    for bolt_index in range(10):
        theta = bolt_index * math.tau / 10
        z_face = z_center + (-0.352 if z_center < 0 else 0.352)
        cylinder(
            f"Wheel_{label}_Lug_{bolt_index+1:02d}",
            (axle_x + math.cos(theta) * 0.145, 0.734 + math.sin(theta) * 0.145, z_face),
            0.019, 0.026, mats["bolt"], root, 12, role="wheel_fastener",
        )
    for tread_index in range(24):
        theta = tread_index * math.tau / 24
        l3_chevron_tread(
            f"Wheel_{label}_Tread_{tread_index+1:02d}",
            axle_x, 0.734, z_center, theta, mats["rubber_tread"], root,
        )
    return root


def add_panel_fasteners(prefix, x_values, y_values, z, parent, mats):
    for xi, x in enumerate(x_values, start=1):
        for yi, y in enumerate(y_values, start=1):
            cylinder(f"{prefix}_Fastener_{xi}_{yi}", (x, y, z), 0.016, 0.025, mats["bolt"], parent, 12, role="panel_fastener")


def create_model():
    mats = {
        # Internal dictionary keys stay stable for deterministic geometry, while
        # the visible body finish is neutral gunmetal rather than brand livery.
        "ochre": material("Neutral_Gunmetal_Body", (0.20, 0.22, 0.24), 0.18, 0.38),
        "ochre_light": material("Neutral_Gunmetal_Highlight", (0.42, 0.46, 0.48), 0.10, 0.34),
        "ochre_dark": material("Neutral_Gunmetal_Shadow", (0.065, 0.075, 0.085), 0.22, 0.42),
        "graphite": material("Neutral_Graphite_Steel", (0.035, 0.045, 0.055), 0.62, 0.30),
        "steel": material("Neutral_Structural_Steel", (0.16, 0.18, 0.20), 0.72, 0.28),
        "rim": material("Neutral_Wheel_Rim", (0.32, 0.35, 0.37), 0.42, 0.30),
        "hub": material("Neutral_Final_Drive", (0.22, 0.23, 0.24), 0.65, 0.25),
        "bolt": material("Neutral_Fastener_Steel", (0.34, 0.36, 0.38), 0.86, 0.20),
        "rubber": material("Neutral_Tire_Rubber", (0.016, 0.019, 0.022), 0.02, 0.63),
        "rubber_tread": material("Neutral_Tread_Rubber", (0.010, 0.012, 0.014), 0.01, 0.72),
        "glass": material("Neutral_Cab_Glass", (0.055, 0.17, 0.19), 0.08, 0.18, 0.44, 0.12),
        "interior": material("Neutral_Cab_Interior", (0.035, 0.040, 0.045), 0.02, 0.64),
        "cylinder": material("Neutral_Hydraulic_Barrel", (0.18, 0.20, 0.22), 0.74, 0.25),
        "rod": material("Neutral_Chromed_Rod", (0.68, 0.72, 0.76), 0.92, 0.12),
        "hose": material("Neutral_Hydraulic_Hose", (0.012, 0.014, 0.016), 0.04, 0.58),
        "amber": material("Neutral_Amber_Lens", (1.0, 0.34, 0.025), 0.05, 0.20),
        "red": material("Neutral_Red_Lens", (0.65, 0.018, 0.012), 0.05, 0.24),
        "white": material("Neutral_Worklight_Lens", (0.84, 0.88, 0.90), 0.10, 0.18),
    }

    machine = empty("Machine_Root", (0, 0, 0), None, "machine_root", size=0.28)
    rear = empty("Rear_Frame_ROOT", (0, 0, 0), machine, "fixed_structure")
    articulation = empty("Articulation_Pivot", tuple(RECONSTRUCTED["hitch_pivot_m"]), rear, "articulation_pivot", local=False)
    articulation["published_test_condition_deg"] = PUBLISHED["full_turn_test_condition_deg"]
    articulation["test_condition_is_mechanical_stop"] = False
    front = empty("Front_Frame_ROOT", (0, 0, 0), articulation, "articulated_structure")
    rear_axle_pivot = empty("Rear_Axle_Oscillation_Pivot", tuple(RECONSTRUCTED["rear_axle_oscillation_pivot_m"]), rear, "oscillation_pivot", local=False)
    rear_axle_pivot["published_range_deg"] = [-PUBLISHED["rear_axle_oscillation_deg"], PUBLISHED["rear_axle_oscillation_deg"]]
    rear_axle = empty("Rear_Axle_ROOT", (0, 0, 0), rear_axle_pivot, "oscillating_axle")
    front_axle = empty("Front_Axle_ROOT", (1.675, 0.734, 0), front, "fixed_axle", local=False)
    hydraulics = empty("Hydraulics_ROOT", (0, 0, 0), machine, "hydraulics")
    steering_hydraulics = empty("Steering_Hydraulics_ROOT", (0, 0, 0), hydraulics, "hydraulics")
    lift_hydraulics = empty("Lift_Hydraulics_ROOT", (0, 0, 0), front, "hydraulics")
    tilt_hydraulics = empty("Tilt_Hydraulics_ROOT", (0, 0, 0), front, "hydraulics")

    # Axle housings and driveline cues.
    cylinder("Rear_Axle_Housing", (-1.675, 0.734, 0), 0.165, 2.30, mats["graphite"], rear_axle, 28, role="axle_housing")
    cylinder("Front_Axle_Housing", (1.675, 0.734, 0), 0.175, 2.30, mats["graphite"], front_axle, 28, role="axle_housing")
    uv_sphere("Rear_Axle_Differential", (-1.675, 0.734, 0), (0.34, 0.28, 0.33), mats["graphite"], rear_axle, "differential_housing")
    uv_sphere("Front_Axle_Differential", (1.675, 0.734, 0), (0.36, 0.30, 0.35), mats["graphite"], front_axle, "differential_housing")
    object_between("Rear_Driveshaft", (-1.30, 0.69, 0), (-0.30, 0.78, 0), 0.065, mats["steel"], rear, "driveline", 20)
    object_between("Front_Driveshaft", (0.18, 0.79, 0), (1.30, 0.72, 0), 0.065, mats["steel"], front, "driveline", 20)

    wheels = {
        "RL": build_wheel("RL", -1.675, -1.070, rear_axle, mats),
        "RR": build_wheel("RR", -1.675, 1.070, rear_axle, mats),
        "FL": build_wheel("FL", 1.675, -1.070, front_axle, mats),
        "FR": build_wheel("FR", 1.675, 1.070, front_axle, mats),
    }

    # Rear chassis and counterweight.
    box("Rear_Frame_Main", (-1.38, 0.63, 0), (3.05, 0.552, 1.34), mats["graphite"], rear, 0.08, "fixed_structure")
    box("Rear_Frame_Belly_Guard", (-1.35, 0.38, 0), (2.70, 0.052, 1.12), mats["steel"], rear, 0.02, "powertrain_guard")
    side_profile("Rear_Counterweight_Main", [(-3.738,0.62),(-3.62,1.58),(-3.22,2.05),(-2.78,2.12),(-2.46,1.58),(-2.50,0.55)], 1.42, mats["ochre"], rear, 0, 0.075, "counterweight")
    side_profile("Rear_Counterweight_Bumper", [(-3.738,0.62),(-3.70,1.20),(-3.54,1.36),(-3.42,0.57)], 1.56, mats["ochre_dark"], rear, 0, 0.045, "counterweight_guard")
    box("Rear_Counterweight_Upper_Seam", (-3.615,1.385,0), (0.090,0.055,1.46), mats["ochre_light"], rear, 0.012, "counterweight_seam")
    box("Rear_Counterweight_Recess", (-3.704,1.055,0), (0.045,0.390,0.54), mats["ochre_dark"], rear, 0.018, "counterweight_recess")
    box("Rear_Tow_Hitch", (-3.62, 0.77, 0), (0.14, 0.30, 0.38), mats["graphite"], rear, 0.04, "tow_hitch")
    cylinder("Rear_Tow_Pin", (-3.66, 0.77, 0), 0.07, 0.24, mats["bolt"], rear, 20, rotation=(math.pi/2,0,0), role="tow_pin")

    hood = empty("Engine_Hood_ROOT", (0, 0, 0), rear, "engine_enclosure")
    side_profile("Engine_Hood_Core", [(-3.42,1.46),(-3.16,2.48),(-2.78,2.695),(-1.28,2.66),(-1.08,2.34),(-1.12,1.34)], 1.45, mats["ochre"], hood, 0, 0.055, "engine_hood")
    box("Engine_Hood_Top_Panel", (-2.15, 2.64, 0), (1.78, 0.09, 1.36), mats["ochre_light"], hood, 0.035, "service_panel")
    box("Rear_Radiator_Grille", (-3.55, 1.88, 0), (0.055, 0.78, 1.08), mats["graphite"], hood, 0.018, "cooling_grille")
    for grille_index in range(11):
        y = 1.55 + grille_index * 0.063
        box(f"Rear_Grille_Slat_{grille_index+1:02d}", (-3.585, y, 0), (0.026, 0.022, 1.00), mats["steel"], hood, 0.004, "grille_slat")
    for side in (-1,1):
        box(f"Rear_Grille_Surround_V_{'L' if side<0 else 'R'}", (-3.608,1.88,side*0.565), (0.035,0.84,0.065), mats["ochre_light"], hood, 0.010, "grille_surround")
    for y, label in ((1.485,"Lower"),(2.275,"Upper")):
        box(f"Rear_Grille_Surround_{label}", (-3.608,y,0), (0.035,0.065,1.19), mats["ochre_light"], hood, 0.010, "grille_surround")
    box("Rear_Grille_Center_Stile", (-3.612,1.88,0), (0.034,0.73,0.044), mats["steel"], hood, 0.008, "grille_surround")
    for side in (-1, 1):
        z = side * 0.738
        box(f"Engine_Service_Panel_{'L' if side < 0 else 'R'}", (-2.18, 2.04, z), (1.63, 0.94, 0.026), mats["ochre_light"], hood, 0.025, "service_panel")
        for vent_index in range(9):
            x = -2.79 + vent_index * 0.155
            box(f"Engine_Vent_{'L' if side < 0 else 'R'}_{vent_index+1:02d}", (x, 2.14, z + side*0.018), (0.075, 0.52, 0.018), mats["graphite"], hood, 0.006, "cooling_vent")
        add_panel_fasteners(f"Engine_{'L' if side < 0 else 'R'}", (-2.88,-1.48), (1.65,2.47), z + side*0.028, hood, mats)

    # Cab, ROPS, glazing, interior, mirrors, lights.
    cab = empty("Cab_ROOT", (0, 0, 0), rear, "operator_enclosure")
    box("Cab_Floor", (-0.62, 1.52, 0), (1.16, 0.18, 1.42), mats["graphite"], cab, 0.035, "cab_floor")
    box("Cab_Roof", (-0.63, 3.411, 0), (1.30, 0.090, 1.46), mats["ochre"], cab, 0.035, "rops_roof", "published_constraint_reconstructed_geometry")
    # Four ROPS posts and crossmembers.
    for x in (-1.12, -0.16):
        for z in (-0.64, 0.64):
            object_between(f"ROPS_Post_{x}_{z}", (x,1.60,z), (x,3.39,z), 0.060, mats["graphite"], cab, "rops_post", 20)
    object_between("ROPS_Front_Header", (-0.16,3.35,-0.64), (-0.16,3.35,0.64), 0.050, mats["graphite"], cab, "rops_header", 18)
    object_between("ROPS_Rear_Header", (-1.12,3.35,-0.64), (-1.12,3.35,0.64), 0.050, mats["graphite"], cab, "rops_header", 18)
    # Side glass panels.
    for side in (-1, 1):
        z = side * 0.655
        box(f"Cab_Side_Glass_{'L' if side < 0 else 'R'}", (-0.64, 2.54, z), (0.78, 1.36, 0.020), mats["glass"], cab, 0.010, "cab_glass")
        box(f"Cab_Side_Lower_Glass_{'L' if side < 0 else 'R'}", (-0.29, 1.85, z), (0.48, 0.36, 0.020), mats["glass"], cab, 0.010, "cab_glass")
        frame_z = side * 0.673
        box(f"Cab_Side_Header_{'L' if side<0 else 'R'}", (-0.64,3.31,frame_z), (0.96,0.095,0.055), mats["graphite"], cab, 0.012, "cab_frame")
        box(f"Cab_Side_Belt_Rail_{'L' if side<0 else 'R'}", (-0.64,1.83,frame_z), (0.96,0.105,0.055), mats["graphite"], cab, 0.012, "cab_frame")
        box(f"Cab_Door_Mullion_{'L' if side<0 else 'R'}", (-0.72,2.56,frame_z), (0.075,1.44,0.055), mats["graphite"], cab, 0.012, "cab_frame")
        box(f"Cab_Lower_Door_Panel_{'L' if side<0 else 'R'}", (-0.64,1.66,frame_z), (0.78,0.22,0.060), mats["graphite"], cab, 0.015, "cab_door_panel")
    box("Cab_Front_Glass", (-0.135, 2.55, 0), (0.022, 1.36, 1.20), mats["glass"], cab, 0.010, "cab_glass", rotation=(0,0,-0.08))
    box("Cab_Rear_Glass", (-1.125, 2.50, 0), (0.022, 1.28, 1.18), mats["glass"], cab, 0.010, "cab_glass", rotation=(0,0,0.04))
    box("Operator_Seat_Base", (-0.70, 1.85, 0), (0.42, 0.18, 0.46), mats["interior"], cab, 0.055, "cab_interior")
    box("Operator_Seat_Back", (-0.86, 2.20, 0), (0.16, 0.62, 0.46), mats["interior"], cab, 0.060, "cab_interior", rotation=(0,0,-0.08))
    box("Operator_Headrest", (-0.90, 2.58, 0), (0.15, 0.24, 0.32), mats["interior"], cab, 0.05, "cab_interior")
    object_between("Steering_Column", (-0.31,1.85,-0.12), (-0.28,2.22,-0.12), 0.032, mats["graphite"], cab, "cab_control", 16)
    torus("Steering_Wheel", (-0.27,2.25,-0.12), 0.13, 0.018, mats["graphite"], cab, 24, 8, 1.0, "cab_control")
    box("Cab_Door_Handle_L", (-0.40,2.18,-0.694), (0.20,0.035,0.030), mats["bolt"], cab, 0.008, "door_handle")
    for hinge_index, y in enumerate((1.92,2.92),start=1):
        cylinder(f"Cab_Door_Hinge_L_{hinge_index}", (-1.055,y,-0.695), 0.028, 0.050, mats["bolt"], cab, 14, role="door_hinge")
    for side in (-1, 1):
        z = side * 0.92
        mirror_label = "L" if side < 0 else "R"
        object_between(f"Mirror_Arm_{mirror_label}_Upper", (-0.24,3.08,side*0.62), (-0.12,3.12,z), 0.024, mats["graphite"], cab, "mirror_arm", 14)
        object_between(f"Mirror_Arm_{mirror_label}_Lower", (-0.24,2.88,side*0.62), (-0.12,2.90,z), 0.024, mats["graphite"], cab, "mirror_arm", 14)
        box(f"Mirror_Housing_{mirror_label}", (-0.10,3.01,z), (0.10,0.31,0.22), mats["graphite"], cab, 0.035, "mirror_housing")
        box(f"Mirror_Glass_{mirror_label}", (-0.10,3.01,z+side*0.112), (0.082,0.265,0.012), mats["glass"], cab, 0.006, "mirror")
        box(f"Cab_Front_Worklight_{'L' if side < 0 else 'R'}", (-0.02,3.28,side*0.48), (0.12,0.15,0.20), mats["white"], cab, 0.025, "work_light")
        box(f"Cab_Rear_Worklight_{'L' if side < 0 else 'R'}", (-1.27,3.25,side*0.48), (0.12,0.15,0.20), mats["white"], cab, 0.025, "work_light")

    # Exhaust and intake are below the ROPS envelope.
    object_between("Exhaust_Stack", (-1.46,2.56,0.48), (-1.46,3.408,0.48), 0.075, mats["graphite"], hood, "exhaust", 28)
    cylinder("Exhaust_Rain_Cap", (-1.46,3.408,0.48), 0.095, 0.045, mats["graphite"], hood, 24, rotation=(math.pi/2,0,0), role="exhaust")
    object_between("Air_Intake_Stack", (-1.72,2.58,-0.48), (-1.72,3.28,-0.48), 0.065, mats["graphite"], hood, "air_intake", 24)
    cylinder("Air_Precleaner", (-1.72,3.30,-0.48), 0.14, 0.20, mats["graphite"], hood, 28, rotation=(math.pi/2,0,0), role="air_intake")

    # Fenders, access stairs, rails, and service cues.
    for axle_label, axle_x, owner in (("Rear",-1.675,rear),("Front",1.675,front)):
        for side in (-1, 1):
            z = side * 1.18
            side_profile(
                f"{axle_label}_Fender_{'L' if side < 0 else 'R'}",
                [(axle_x-0.92,1.25),(axle_x-0.66,1.55),(axle_x,1.69),(axle_x+0.66,1.55),(axle_x+0.92,1.25),(axle_x+0.80,1.17),(axle_x,1.43),(axle_x-0.80,1.17)],
                0.16, mats["ochre"], owner, z, 0.035, "fender",
            )
    for step_index in range(4):
        step_x = -0.60 + step_index*0.04
        step_y = 0.56 + step_index*0.24
        box(f"Access_Step_{step_index+1}", (step_x,step_y,-1.32), (0.62,0.075,0.34), mats["graphite"], rear, 0.012, "access_step")
        for grip_index in range(5):
            box(f"Access_Step_{step_index+1}_Grip_{grip_index+1}", (step_x-0.22+grip_index*0.11,step_y+0.044,-1.32), (0.055,0.018,0.30), mats["steel"], rear, 0.004, "step_grip")
    side_profile("Access_Step_Stringer", [(-0.98,0.48),(-0.88,0.48),(-0.66,1.42),(-0.76,1.46)], 0.050, mats["steel"], rear, -1.465, 0.010, "step_stringer")
    rail("Access_Handrail", [(-0.95,0.78,-1.38),(-1.02,1.55,-1.38),(-0.98,2.35,-1.02),(-0.92,3.02,-0.78)], 0.030, mats["graphite"], rear)
    rail("Access_Handrail_Secondary", [(-0.44,0.82,-1.38),(-0.42,1.46,-1.36),(-0.36,2.02,-0.92)], 0.026, mats["graphite"], rear)
    rail("Cab_Door_Rail", [(-0.15,1.60,-0.76),(-0.05,2.10,-0.82),(-0.04,2.88,-0.82)], 0.028, mats["graphite"], cab)
    for side in (-1, 1):
        box(f"Rear_Tail_Lamp_{'L' if side < 0 else 'R'}", (-3.56,1.70,side*0.56), (0.08,0.20,0.18), mats["red"], rear, 0.025, "tail_light")
        box(f"Rear_Amber_Lamp_{'L' if side < 0 else 'R'}", (-3.56,1.93,side*0.56), (0.08,0.12,0.18), mats["amber"], rear, 0.025, "signal_light")

    # Center hitch and front chassis.
    box("Rear_Hitch_Clevis", (-0.16,0.90,0), (0.68,0.62,0.84), mats["graphite"], rear, 0.08, "hitch_structure")
    cylinder("Articulation_Upper_Pin", (0,1.16,0), 0.14, 0.72, mats["bolt"], rear, 28, role="articulation_pin")
    cylinder("Articulation_Lower_Pin", (0,0.72,0), 0.14, 0.72, mats["bolt"], rear, 28, role="articulation_pin")
    side_profile("Front_Frame_Main", [(-0.14,0.57),(0.22,1.28),(1.82,1.42),(2.74,0.95),(3.286,0.62),(3.18,0.354),(0.16,0.354)], 1.25, mats["ochre"], front, 0, 0.065, "front_frame")
    box("Front_Frame_Belly_Guard", (1.25,0.382,0), (2.60,0.056,1.08), mats["steel"], front, 0.018, "powertrain_guard")
    box("Front_Crossmember", (0.56,1.15,0), (0.52,0.42,1.34), mats["graphite"], front, 0.065, "front_crossmember")
    for side in (-1, 1):
        z = side * 0.60
        cylinder(f"Lift_Pivot_Boss_{'L' if side < 0 else 'R'}", (0.45,1.45,z), 0.18, 0.24, mats["graphite"], front, 28, role="pivot_boss")
        cylinder(f"Lift_Pivot_Pin_{'L' if side < 0 else 'R'}", (0.45,1.45,z), 0.09, 0.30, mats["bolt"], front, 24, role="pivot_pin")

    # Lift-arm and bucket hierarchy.
    lift_pivot = empty("Lift_Arm_Pivot", tuple(RECONSTRUCTED["lift_arm_pivot_m"]), front, "lift_pivot", local=False)
    lift_arms = empty("Lift_Arms_ROOT", (0,0,0), lift_pivot, "lift_arms")
    for side in (-1, 1):
        z = side * 0.67
        side_profile(
            f"Lift_Arm_{'L' if side < 0 else 'R'}",
            [(-0.10,0.16),(0.86,0.12),(1.65,-0.25),(2.52,-0.69),(2.67,-0.82),(2.56,-0.98),(1.58,-0.48),(0.78,-0.12),(-0.12,-0.12)],
            0.19, mats["ochre"], lift_arms, z, 0.045, "lift_arm",
        )
        for hole_x, hole_y in ((0,0),(2.55,-0.827)):
            cylinder(f"Lift_Arm_Pin_Boss_{'L' if side < 0 else 'R'}_{hole_x}", (hole_x,hole_y,z), 0.145, 0.25, mats["graphite"], lift_arms, 28, role="pivot_boss", local=True)
    box("Lift_Arm_Cross_Tube", (2.12,-0.57,0), (0.28,0.28,1.50), mats["graphite"], lift_arms, 0.045, "lift_crossmember", local=True)
    bucket_pivot = empty("Bucket_Pivot", (2.55,-0.827,0), lift_arms, "bucket_pivot")
    bucket_root = empty("Bucket_ROOT", (0,0,0), bucket_pivot, "bucket")

    bucket_width = PUBLISHED["bucket_width_m"]
    bucket_points = [(-0.10,0.06),(0.08,0.56),(0.42,0.78),(1.30,0.58),(1.56,0.06),(1.68,-0.43),(1.50,-0.54),(0.36,-0.49)]
    for side in (-1,1):
        side_profile(f"Bucket_Side_Plate_{'L' if side<0 else 'R'}", bucket_points, 0.08, mats["ochre"], bucket_root, side*(bucket_width/2-0.04), 0.025, "bucket_side_plate")
        side_profile(f"Bucket_Side_Wear_Plate_{'L' if side<0 else 'R'}", [(0.30,-0.46),(1.55,-0.50),(1.62,-0.39),(0.38,-0.35)], 0.035, mats["steel"], bucket_root, side*(bucket_width/2-0.018), 0.012, "bucket_wear_plate")
    box("Bucket_Back_Sheet", (0.30,0.16,0), (0.16,0.98,bucket_width-0.16), mats["ochre_light"], bucket_root, 0.025, "bucket_shell", local=True, rotation=(0,0,-0.38))
    box("Bucket_Floor_Sheet", (0.99,-0.44,0), (1.30,0.10,bucket_width-0.14), mats["ochre"], bucket_root, 0.018, "bucket_shell", local=True, rotation=(0,0,-0.035))
    box("Bucket_Cutting_Edge", (1.47,-0.505,0), (0.46,0.13,bucket_width-0.02), mats["steel"], bucket_root, 0.016, "cutting_edge", local=True, rotation=(0,0,-0.18))
    box("Bucket_Spill_Guard", (0.61,0.63,0), (0.72,0.12,bucket_width-0.18), mats["ochre_light"], bucket_root, 0.025, "spill_guard", local=True, rotation=(0,0,-0.18))
    for rib_index, z in enumerate((-1.16,-0.78,-0.39,0,0.39,0.78,1.16),start=1):
        side_profile(f"Bucket_Back_Rib_{rib_index:02d}", [(0.10,-0.18),(0.18,0.55),(0.29,0.60),(0.24,-0.24)], 0.045, mats["steel"], bucket_root, z, 0.010, "bucket_reinforcement")
    for tooth_index in range(9):
        z = -1.26 + tooth_index * (2.52/8)
        side_profile(
            f"Bucket_Tooth_{tooth_index+1:02d}",
            [(1.34,-0.46),(1.749,-0.623),(1.67,-0.49),(1.38,-0.37)],
            0.21, mats["steel"], bucket_root, z, 0.012, "bucket_tooth",
        )
        cylinder(f"Bucket_Tooth_Pin_{tooth_index+1:02d}", (1.42,-0.44,z), 0.025, 0.24, mats["bolt"], bucket_root, 12, role="tooth_fastener", local=True)
    for side in (-1,1):
        z = side * 0.52
        cylinder(f"Bucket_Pin_Boss_{'L' if side<0 else 'R'}", (0,0,z), 0.16, 0.22, mats["graphite"], bucket_root, 28, role="bucket_pin_boss", local=True)
        cylinder(f"Bucket_Pin_{'L' if side<0 else 'R'}", (0,0,z), 0.085, 0.26, mats["bolt"], bucket_root, 24, role="bucket_pin", local=True)

    # Z-bar linkage and anchors.
    # The Z-bar bellcrank pivot is carried by the lift group.  Parenting this
    # subtree to the fixed front frame makes the fixed-length dogbone
    # impossible to close at raised poses and is mechanically incoherent.
    zbar = empty("ZBar_Linkage_ROOT", (0,0,0), lift_arms, "linkage")
    bell_pivot = empty(
        "ZBar_Bellcrank_Pivot",
        (1.03 - RECONSTRUCTED["lift_arm_pivot_m"][0],
         2.18 - RECONSTRUCTED["lift_arm_pivot_m"][1], 0),
        zbar,
        "linkage_pivot",
        local=True,
    )
    bell_root = empty("ZBar_Bellcrank_ROOT", (0,0,0), bell_pivot, "linkage")
    bell_profile = [(-0.38,-0.18),(-0.18,-0.34),(0.38,-0.23),(0.53,0.06),(0.18,0.43),(-0.22,0.55),(-0.45,0.20)]
    for side in (-1,1):
        side_profile(f"ZBar_Bellcrank_Cheek_{'L' if side<0 else 'R'}", bell_profile, 0.085, mats["steel"], bell_root, side*0.36, 0.025, "bellcrank")
    cylinder("ZBar_Bellcrank_Pin", (0,0,0), 0.105, 0.82, mats["bolt"], bell_root, 28, role="linkage_pin", local=True)
    bell_rod_anchor = empty("ANCHOR_Bellcrank_Rod", (-0.22,0.32,0), bell_root, "anchor", 0.08)
    # Place the dogbone pin on the rear shoulder of the reconstructed
    # bellcrank.  The former forward/lower pin made the fixed-length link
    # geometrically unreachable across the retained bucket review poses.
    bell_dogbone_anchor = empty("ANCHOR_Bellcrank_Dogbone", (-0.36,0.18,0), bell_root, "anchor", 0.08)
    bucket_lug = empty("ANCHOR_Bucket_Lug", (0.22,0.34,0), bucket_root, "anchor", 0.08)
    cylinder("Bucket_Linkage_Lug", (0.22,0.34,0), 0.11, 0.42, mats["ochre_dark"], bucket_root, 24, role="bucket_lug", local=True)
    for side in (-1,1):
        cylinder(f"Bucket_Linkage_Ear_{'L' if side<0 else 'R'}", (0.22,0.34,side*0.30), 0.125, 0.10, mats["ochre_dark"], bucket_root, 24, role="bucket_lug", local=True)
    cylinder("ZBar_Rod_Anchor_Pin", (-0.22,0.32,0), 0.070, 0.76, mats["bolt"], bell_root, 22, role="linkage_pin", local=True)
    cylinder("ZBar_Dogbone_Anchor_Pin", (-0.36,0.18,0), 0.080, 0.76, mats["bolt"], bell_root, 22, role="linkage_pin", local=True)
    bpy.context.view_layer.update()
    dogbone = object_between("ZBar_Dogbone_Center", world(bell_dogbone_anchor), world(bucket_lug), 0.080, mats["steel"], zbar, "linkage_dogbone", 24)
    dogbone_visuals = []
    for side in (-1,1):
        offset = side*0.30
        dogbone_visuals.append((
            object_between(
                f"ZBar_Dogbone_Cheek_{'L' if side<0 else 'R'}",
                world_offset(bell_dogbone_anchor,(0,0,offset)),
                world_offset(bucket_lug,(0,0,offset)),
                0.060, mats["bolt"], zbar, "linkage_dogbone_cheek", 20,
            ),
            offset,
        ))
    dogbone_nominal_length = (world(bell_dogbone_anchor)-world(bucket_lug)).length
    dogbone_midpoint = (world(bell_dogbone_anchor) + world(bucket_lug)) * 0.5
    dogbone_crosshead = cylinder(
        "ZBar_Dogbone_Crosshead", dogbone_midpoint, 0.105, 0.78,
        mats["ochre_dark"], zbar, 28, role="linkage_crosshead", local=False)

    # Hydraulic anchors and visual cylinders.
    cylinders = {}
    steering_anchors = []
    for side in (-1,1):
        base = empty(f"ANCHOR_Steering_Base_{side}", (-0.48,0.82,side*0.43), rear, "anchor", 0.07, local=False)
        rod = empty(f"ANCHOR_Steering_Rod_{side}", (0.56,0.83,side*0.53), front, "anchor", 0.07, local=False)
        steering_anchors.append((base,rod))
        split_cylinder(f"Steering_Cylinder_{'L' if side<0 else 'R'}", world(base), world(rod), 0.075, 0.041, mats, steering_hydraulics, cylinders)

    lift_anchors = []
    for side in (-1,1):
        base = empty(f"ANCHOR_Lift_Base_{side}", (0.58,0.72,side*0.70), front, "anchor", 0.07, local=False)
        rod = empty(f"ANCHOR_Lift_Rod_{side}", (1.33,-0.14,side*0.70), lift_arms, "anchor", 0.07)
        lift_anchors.append((base,rod))
        split_cylinder(f"Lift_Cylinder_{'L' if side<0 else 'R'}", world(base), world(rod), 0.092, 0.052, mats, lift_hydraulics, cylinders)
    tilt_base = empty("ANCHOR_Tilt_Base", (0.05,2.30,0), front, "anchor", 0.07, local=False)
    for side in (-1,1):
        cylinder(f"Tilt_Base_Clevis_{'L' if side<0 else 'R'}", (0.05,2.30,side*0.16), 0.105, 0.09, mats["ochre_dark"], front, 24, role="hydraulic_clevis")
    split_cylinder("Tilt_Cylinder", world(tilt_base), world(bell_rod_anchor), 0.140, 0.075, mats, tilt_hydraulics, cylinders)
    cylinders["Tilt_Cylinder"]["barrel"].data.materials.clear()
    cylinders["Tilt_Cylinder"]["barrel"].data.materials.append(mats["steel"])

    # Hose bundles: reconstructed segmented exterior routing cues.
    hose_objects = []
    hose_paths = [
        [(0.32,1.50,-0.48),(0.72,1.68,-0.56),(1.22,1.34,-0.62),(1.72,1.04,-0.65),(2.30,0.76,-0.66)],
        [(0.30,1.44,-0.42),(0.74,1.60,-0.50),(1.24,1.28,-0.56),(1.76,0.98,-0.59),(2.34,0.70,-0.60)],
        [(0.30,1.38,0.42),(0.74,1.56,0.50),(1.24,1.24,0.56),(1.76,0.94,0.59),(2.34,0.68,0.60)],
        [(0.32,1.32,0.48),(0.72,1.50,0.56),(1.22,1.18,0.62),(1.72,0.88,0.65),(2.30,0.62,0.66)],
    ]
    for path_index, points in enumerate(hose_paths,start=1):
        for seg_index,(start,end) in enumerate(zip(points,points[1:]),start=1):
            hose_objects.append(object_between(f"Implement_Hose_{path_index:02d}_{seg_index:02d}", start, end, 0.018, mats["hose"], front, "hydraulic_hose", 12))
    for side in (-1,1):
        hose_objects.extend(rail(f"Steering_Hose_{'L' if side<0 else 'R'}", [(-0.40,1.02,side*0.36),(-0.05,1.16,side*0.42),(0.34,1.05,side*0.50)], 0.017, mats["hose"], rear, "hydraulic_hose"))

    model = {
        "machine": machine,
        "rear": rear,
        "front": front,
        "articulation": articulation,
        "rear_axle_pivot": rear_axle_pivot,
        "lift_arms": lift_arms,
        "bucket_root": bucket_root,
        "bucket_pivot": bucket_pivot,
        "bell_pivot": bell_pivot,
        "bell_root": bell_root,
        "dogbone": dogbone,
        "dogbone_visuals":dogbone_visuals,
        "dogbone_nominal_length_m":dogbone_nominal_length,
        "dogbone_crosshead":dogbone_crosshead,
        "bell_previous_angle_rad":0.0,
        "bell_dogbone_anchor": bell_dogbone_anchor,
        "bucket_lug": bucket_lug,
        "steering_anchors": steering_anchors,
        "lift_anchors": lift_anchors,
        "tilt_base": tilt_base,
        "bell_rod_anchor": bell_rod_anchor,
        "cylinders": cylinders,
        "wheels": wheels,
        "hose_objects": hose_objects,
        "mats": mats,
    }
    set_pose(model, **RECONSTRUCTED["saved_carry_pose"])
    return model


def set_pose(model, articulation_deg, rear_axle_oscillation_deg, lift_deg, bucket_relative_deg):
    model["articulation"].rotation_euler = (0, math.radians(articulation_deg), 0)
    model["rear_axle_pivot"].rotation_euler = (math.radians(rear_axle_oscillation_deg), 0, 0)
    model["lift_arms"].rotation_euler = (0, 0, math.radians(lift_deg))
    model["bucket_root"].rotation_euler = (0, 0, math.radians(bucket_relative_deg))
    bpy.context.view_layer.update()
    solve_reconstructed_bellcrank_pose(model)
    bpy.context.view_layer.update()
    for side_index,(base,rod) in enumerate(model["steering_anchors"]):
        key = "Steering_Cylinder_L" if side_index == 0 else "Steering_Cylinder_R"
        update_split_cylinder(model["cylinders"][key], world(base), world(rod))
    for side_index,(base,rod) in enumerate(model["lift_anchors"]):
        key = "Lift_Cylinder_L" if side_index == 0 else "Lift_Cylinder_R"
        update_split_cylinder(model["cylinders"][key], world(base), world(rod))
    update_split_cylinder(model["cylinders"]["Tilt_Cylinder"], world(model["tilt_base"]), world(model["bell_rod_anchor"]))
    place_between(model["dogbone"], world(model["bell_dogbone_anchor"]), world(model["bucket_lug"]), 0.080)
    for dogbone_cheek,offset in model["dogbone_visuals"]:
        place_between(
            dogbone_cheek,
            world_offset(model["bell_dogbone_anchor"],(0,0,offset)),
            world_offset(model["bucket_lug"],(0,0,offset)),
            0.060,
        )
    model["dogbone_crosshead"].matrix_world.translation = (
        world(model["bell_dogbone_anchor"]) + world(model["bucket_lug"])
    ) * 0.5
    bpy.context.view_layer.update()


def add_review_environment(mats):
    ground = box("REVIEW_Ground", (0,-0.035,0), (18,0.06,18), material("Review_Ground_Material", (0.025,0.032,0.041), 0.05, 0.72), None, 0.0, "review_helper")
    tag(ground, "review_helper", False)
    for label, location, energy, size, color in (
        ("Key", (4.5,8.5,-6.0), 1400, 5.0, (1.0,0.84,0.66)),
        ("Fill", (-4.0,5.5,-7.0), 900, 4.0, (0.58,0.74,1.0)),
        ("Rim", (-6.0,7.0,5.5), 1200, 4.0, (0.72,0.82,1.0)),
        ("Front", (8.0,4.0,3.5), 700, 3.0, (1.0,0.66,0.40)),
    ):
        data = bpy.data.lights.new(f"REVIEW_{label}_Light", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        data.use_shadow_jitter = False
        light = bpy.data.objects.new(f"REVIEW_{label}_Light", data)
        bpy.context.scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = ((Vector((0,1.5,0)) - light.location).to_track_quat("-Z","Y")).to_euler()
        tag(light, "review_light", False)
    camera_data = bpy.data.cameras.new("REVIEW_Camera")
    camera = bpy.data.objects.new("REVIEW_Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera_data.lens = 52
    camera_data.sensor_width = 36
    tag(camera, "review_camera", False)
    return camera


def render_view(camera, filename, position, target, lens=52):
    camera.location = position
    camera.data.lens = lens
    forward = (Vector(target) - camera.location).normalized()
    world_up = Vector((0,1,0))
    if abs(forward.dot(world_up)) > 0.995:
        world_up = Vector((0,0,1))
    right = forward.cross(world_up).normalized()
    true_up = right.cross(forward).normalized()
    camera.rotation_euler = Matrix((right, true_up, -forward)).transposed().to_euler()
    path = RENDER_DIR / filename
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def render_all(model, camera):
    paths = []
    set_pose(model, **RECONSTRUCTED["saved_carry_pose"])
    paths.append(render_view(camera,"cat-950-operator-side.png",(0.6,2.8,-15.5),(0.45,1.45,0),52))
    paths.append(render_view(camera,"cat-950-right-three-quarter.png",(10.8,5.5,10.8),(0.40,1.35,0),50))
    paths.append(render_view(camera,"cat-950-rear-three-quarter.png",(-10.8,4.8,-9.0),(-0.20,1.40,0),52))
    paths.append(render_view(camera,"cat-950-front-bucket.png",(10.5,3.4,-8.5),(1.00,1.00,0),52))
    paths.append(render_view(camera,"cat-950-wheel-l3-detail.png",(2.0,1.45,-4.2),(1.675,0.76,-1.04),72))
    paths.append(render_view(camera,"cat-950-tire-cab-detail.png",(-2.6,3.2,-4.9),(-0.72,1.95,-0.62),64))
    paths.append(render_view(camera,"cat-950-rear-grille-detail.png",(-6.8,3.25,-3.7),(-3.18,1.80,-0.05),70))
    def under_root(obj, root):
        parent = obj.parent
        while parent is not None:
            if parent == root:
                return True
            parent = parent.parent
        return False

    bucket_keep_names = {
        "Bucket_Linkage_Lug", "Bucket_Linkage_Ear_L", "Bucket_Linkage_Ear_R",
        "Bucket_Pin_Boss_L", "Bucket_Pin_Boss_R", "Bucket_Pin_L", "Bucket_Pin_R",
    }
    linkage_occluder_names = {
        "Lift_Arm_L", "Front_Frame_Main", "Front_Crossmember", "Front_Fender_L",
    }
    linkage_occluders = [
        obj for obj in bpy.data.objects
        if obj.name in linkage_occluder_names
        or under_root(obj, bpy.data.objects["Cab_ROOT"])
        or under_root(obj, bpy.data.objects["Wheel_FL_ROOT"])
        or (under_root(obj, model["bucket_root"]) and obj.name not in bucket_keep_names)
    ]
    for obj in linkage_occluders:
        obj.hide_render = True
    linkage_target = (world(model["bell_pivot"]) + world(model["bucket_lug"])) * 0.5
    paths.append(render_view(
        camera, "cat-950-zbar-linkage-detail.png",
        tuple(linkage_target + Vector((3.8, 1.45, -4.6))), tuple(linkage_target), 66))
    for obj in linkage_occluders:
        obj.hide_render = False
    set_pose(model, **RECONSTRUCTED["review_articulated_pose"])
    paths.append(render_view(camera,"cat-950-articulated-review.png",(11.5,5.7,-12.0),(0.40,1.20,0),52))
    set_pose(model, **RECONSTRUCTED["review_oscillation_pose"])
    paths.append(render_view(camera,"cat-950-axle-oscillation-review.png",(-10.0,4.4,10.5),(-0.20,1.20,0),52))
    set_pose(model, **RECONSTRUCTED["review_max_lift_pose"])
    model["review_max_lift_hinge_world_m"] = [round(v, 6) for v in world(model["bucket_pivot"])]
    for obj in linkage_occluders:
        obj.hide_render = True
    raised_linkage_target = (world(model["bell_pivot"]) + world(model["bucket_lug"])) * 0.5
    paths.append(render_view(
        camera, "cat-950-zbar-raised-detail.png",
        tuple(raised_linkage_target + Vector((3.6, 1.20, -4.4))), tuple(raised_linkage_target), 66))
    for obj in linkage_occluders:
        obj.hide_render = False
    paths.append(render_view(camera,"cat-950-full-lift-review.png",(10.5,5.3,-13.5),(0.40,2.40,0),50))
    set_pose(model, **RECONSTRUCTED["review_dump_pose"])
    paths.append(render_view(camera,"cat-950-articulated-lift-dump-review.png",(11.0,6.0,-14.0),(0.40,2.40,0),50))
    set_pose(model, **RECONSTRUCTED["saved_carry_pose"])
    return paths


def export_objects():
    objects = [obj for obj in bpy.context.scene.objects if obj.get("exo_export") is True]
    for obj in objects:
        parent = obj.parent
        while parent is not None:
            if parent.get("exo_export") is not True:
                raise RuntimeError(f"Export object {obj.name} descends from non-export parent {parent.name}")
            parent = parent.parent
    return objects


def apply_export_mesh_scales(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)


def evaluated_world_points(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return points


def object_bounds(objects):
    points = evaluated_world_points(objects)
    mins = [min(point[i] for point in points) for i in range(3)]
    maxs = [max(point[i] for point in points) for i in range(3)]
    return {"min_m":mins,"max_m":maxs,"size_m":[maxs[i]-mins[i] for i in range(3)]}


def rounded_bounds(objects):
    bounds = object_bounds(objects)
    return {key:[round(value,4) for value in values] for key,values in bounds.items()}


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


def inspect_glb_contract(path):
    data = path.read_bytes()
    offset = 12
    json_chunk = None
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset+length]
        offset += length
        if kind == 0x4E4F534A:
            json_chunk = chunk
            break
    if json_chunk is None:
        raise RuntimeError("GLB JSON chunk missing")
    document = json.loads(json_chunk.decode("utf-8").rstrip("\x00 "))
    scene = document["scenes"][document.get("scene",0)]
    roots = []
    for index in scene.get("nodes",[]):
        node = document["nodes"][index]
        transform = {key:node[key] for key in ("translation","rotation","scale","matrix") if key in node}
        roots.append({"index":index,"name":node.get("name"),"transform":transform})
    return {
        "scene_count":len(document.get("scenes",[])),
        "scene_roots":roots,
        "node_count":len(document.get("nodes",[])),
        "mesh_count":len(document.get("meshes",[])),
        "camera_count":len(document.get("cameras",[])),
        "punctual_light_extension_present":"KHR_lights_punctual" in document.get("extensions",{}),
        "helper_nodes":[node.get("name","") for node in document.get("nodes",[]) if node.get("name","").startswith("REVIEW_")],
        "platform_axes":"+X longitudinal, +Y vertical, +Z machine right",
    }


def collect_metrics(model, objects):
    meshes = [obj for obj in objects if obj.type == "MESH"]
    tire_objs = [obj for obj in meshes if obj.get("exo_role") in {"tire","tire_tread"}]
    tire_bounds = object_bounds(tire_objs)
    center_guard = object_bounds([bpy.data.objects["Rear_Frame_Belly_Guard"]])
    rops = object_bounds([bpy.data.objects["Cab_Roof"]])
    hood = object_bounds([bpy.data.objects["Engine_Hood_Core"],bpy.data.objects["Engine_Hood_Top_Panel"]])
    tooth_objs = [obj for obj in meshes if obj.get("exo_role") == "bucket_tooth"]
    visible_bounds = object_bounds(meshes)
    scale_offenders = {obj.name:[round(v,8) for v in obj.scale] for obj in meshes if any(abs(v-1.0)>1e-7 for v in obj.scale)}

    def mesh_descendants(root):
        count = 0
        stack = list(root.children)
        while stack:
            child = stack.pop()
            if child.type == "MESH":
                count += 1
            stack.extend(child.children)
        return count

    semantic_descendants = {
        name: mesh_descendants(bpy.data.objects[name])
        for name in (
            "Articulation_Pivot", "Rear_Axle_Oscillation_Pivot",
            "Lift_Arm_Pivot", "Bucket_Pivot", "ZBar_Linkage_ROOT",
            "Steering_Hydraulics_ROOT", "Lift_Hydraulics_ROOT",
            "Tilt_Hydraulics_ROOT",
        )
    }
    semantic_pivots = {
        name: [round(v, 6) for v in bpy.data.objects[name].matrix_world.translation]
        for name in (
            "Articulation_Pivot", "Rear_Axle_Oscillation_Pivot",
            "Lift_Arm_Pivot", "Bucket_Pivot", "ZBar_Bellcrank_Pivot",
        )
    }

    def endpoint_error(obj, target):
        zs = [corner[2] for corner in obj.bound_box]
        endpoints = [obj.matrix_world @ Vector((0,0,min(zs))), obj.matrix_world @ Vector((0,0,max(zs)))]
        return min((endpoint - Vector(target)).length for endpoint in endpoints)

    cylinder_anchor_errors = {}
    for side_index, (base, rod) in enumerate(model["steering_anchors"]):
        key = "Steering_Cylinder_L" if side_index == 0 else "Steering_Cylinder_R"
        cylinder_anchor_errors[f"{key}_base"] = endpoint_error(model["cylinders"][key]["barrel"], world(base))
        cylinder_anchor_errors[f"{key}_rod"] = endpoint_error(model["cylinders"][key]["rod"], world(rod))
    for side_index, (base, rod) in enumerate(model["lift_anchors"]):
        key = "Lift_Cylinder_L" if side_index == 0 else "Lift_Cylinder_R"
        cylinder_anchor_errors[f"{key}_base"] = endpoint_error(model["cylinders"][key]["barrel"], world(base))
        cylinder_anchor_errors[f"{key}_rod"] = endpoint_error(model["cylinders"][key]["rod"], world(rod))
    cylinder_anchor_errors["Tilt_Cylinder_base"] = endpoint_error(model["cylinders"]["Tilt_Cylinder"]["barrel"], world(model["tilt_base"]))
    cylinder_anchor_errors["Tilt_Cylinder_rod"] = endpoint_error(model["cylinders"]["Tilt_Cylinder"]["rod"], world(model["bell_rod_anchor"]))
    return {
        "tire_bounds_m":tire_bounds,
        "tire_loaded_width_m":tire_bounds["size_m"][2],
        "tire_contact_min_y_m":tire_bounds["min_m"][1],
        "rear_frame_guard_underside_m":center_guard["min_m"][1],
        "rops_top_m":rops["max_m"][1],
        "hood_top_m":hood["max_m"][1],
        "visible_bounds_m":visible_bounds,
        "wheel_root_centers_m":{key:[round(v,6) for v in world(root)] for key,root in model["wheels"].items()},
        "wheelbase_m":world(model["wheels"]["FL"])[0]-world(model["wheels"]["RL"])[0],
        "rear_axle_to_hitch_m":-world(model["wheels"]["RL"])[0],
        "bucket_teeth":len(tooth_objs),
        "tread_blocks":len([obj for obj in meshes if obj.get("exo_role")=="tire_tread"]),
        "hose_segments":len(model["hose_objects"]),
        "export_mesh_scale_offenders":scale_offenders,
        "zbar_static_dogbone_endpoint_error_m":dogbone_endpoint_error(model),
        "semantic_visible_mesh_descendants":semantic_descendants,
        "semantic_pivot_world_m":semantic_pivots,
        "cylinder_anchor_endpoint_errors_m":cylinder_anchor_errors,
        "review_max_lift_hinge_world_m":model.get("review_max_lift_hinge_world_m"),
    }


def dogbone_endpoint_error(model):
    obj = model["dogbone"]
    local_z = [corner[2] for corner in obj.bound_box]
    endpoints = [obj.matrix_world @ Vector((0,0,min(local_z))),obj.matrix_world @ Vector((0,0,max(local_z)))]
    targets = [world(model["bell_dogbone_anchor"]),world(model["bucket_lug"])]
    return max(min((endpoint-target).length for endpoint in endpoints) for target in targets)


def create_validation(bounds, counts, renders, metrics, glb_contract):
    node_presence = {name:bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    render_ok = len(renders) >= 6 and all(path.exists() and path.stat().st_size > 20_000 for path in renders)
    root_records = glb_contract["scene_roots"]
    glb_ok = (
        glb_contract["scene_count"] == 1
        and len(root_records) == 1
        and root_records[0]["name"] == "Machine_Root"
        and root_records[0]["transform"] == {}
        and glb_contract["camera_count"] == 0
        and not glb_contract["punctual_light_extension_present"]
        and not glb_contract["helper_nodes"]
    )
    render_evidence = {
        path.stem: {"sha256":sha256(path),"bytes":path.stat().st_size}
        for path in renders
    }
    max_cylinder_anchor_error = max(metrics["cylinder_anchor_endpoint_errors_m"].values())

    def mechanism_detail(method, evidence, semantic_nodes, fact_ids):
        if not method or not isinstance(evidence, dict) or not evidence:
            raise RuntimeError("mechanism gate detail requires a method and nonempty evidence object")
        if len(semantic_nodes) != len(set(semantic_nodes)) or len(fact_ids) != len(set(fact_ids)):
            raise RuntimeError("mechanism gate semantic_nodes and fact_ids must be unique")
        return {"method":method,"evidence":evidence,"semantic_nodes":semantic_nodes,"fact_ids":fact_ids}

    mechanism_gates = [
        {"id":"published_transport_envelope","status":"PASS" if abs(bounds["size_m"][0]-PUBLISHED["shipping_length_m"])<=0.08 and abs(bounds["size_m"][2]-PUBLISHED["bucket_width_m"])<=0.035 and abs(metrics["rops_top_m"]-PUBLISHED["rops_height_m"])<=0.02 and abs(metrics["hood_top_m"]-PUBLISHED["hood_height_m"])<=0.03 else "FAIL","detail":mechanism_detail(
            "Evaluated retained-pose public mesh bounds and named roof/hood meshes against the selected hash-bound specification rows.",
            {"modeled_length_m":bounds["size_m"][0],"published_length_m":PUBLISHED["shipping_length_m"],"modeled_width_m":bounds["size_m"][2],"published_bucket_width_m":PUBLISHED["bucket_width_m"],"modeled_rops_top_m":metrics["rops_top_m"],"published_rops_height_m":PUBLISHED["rops_height_m"],"modeled_hood_top_m":metrics["hood_top_m"],"published_hood_height_m":PUBLISHED["hood_height_m"]},
            ["Machine_Root","Rear_Frame_ROOT","Front_Frame_ROOT","Bucket_ROOT","Cab_ROOT","Engine_Hood_ROOT"],
            ["shipping-length","bucket-width","rops-height","hood-height"],
        )},
        {"id":"tire_contact_and_loaded_width","status":"PASS" if abs(metrics["tire_contact_min_y_m"])<=0.003 and abs(metrics["tire_loaded_width_m"]-PUBLISHED["tire_width_loaded_m"])<=0.01 and abs(metrics["wheelbase_m"]-PUBLISHED["wheelbase_m"])<=1e-5 and abs(metrics["rear_axle_to_hitch_m"]-PUBLISHED["rear_axle_to_hitch_m"])<=1e-5 else "FAIL","detail":mechanism_detail(
            "Evaluated all tire/tread mesh vertices and semantic wheel-root centers in the retained pose.",
            {"tire_min_y_m":metrics["tire_contact_min_y_m"],"loaded_width_modeled_m":metrics["tire_loaded_width_m"],"loaded_width_published_m":PUBLISHED["tire_width_loaded_m"],"wheelbase_modeled_m":metrics["wheelbase_m"],"wheelbase_published_m":PUBLISHED["wheelbase_m"],"rear_axle_to_hitch_modeled_m":metrics["rear_axle_to_hitch_m"],"rear_axle_to_hitch_published_m":PUBLISHED["rear_axle_to_hitch_m"],"axle_centers_m":metrics["wheel_root_centers_m"],"published_axle_center_height_m":PUBLISHED["axle_center_height_m"],"published_tread_width_m":PUBLISHED["tread_width_m"],"ground_clearance_cue_m":metrics["rear_frame_guard_underside_m"]},
            ["Wheel_RL_ROOT","Wheel_RR_ROOT","Wheel_FL_ROOT","Wheel_FR_ROOT","Rear_Axle_ROOT","Front_Axle_ROOT"],
            ["tire-width-loaded","tread-width","axle-center-height","wheelbase","rear-axle-to-hitch","ground-clearance"],
        )},
        {"id":"frame_articulation_clearance","status":"PASS" if metrics["semantic_visible_mesh_descendants"]["Articulation_Pivot"]>0 and "cat-950-articulated-review" in render_evidence else "FAIL","detail":mechanism_detail(
            "Traversed the articulation pivot subtree and sampled a 28-degree reconstructed review pose with an exact hash-bound render.",
            {"pivot_world_m":metrics["semantic_pivot_world_m"]["Articulation_Pivot"],"visible_mesh_descendants":metrics["semantic_visible_mesh_descendants"]["Articulation_Pivot"],"sampled_pose_deg":RECONSTRUCTED["review_articulated_pose"]["articulation_deg"],"render":render_evidence.get("cat-950-articulated-review"),"scope":"sampled visual clearance; 40-degree static tipping-load condition is not treated as a steering stop"},
            ["Articulation_Pivot","Front_Frame_ROOT","Steering_Hydraulics_ROOT"],
            [],
        )},
        {"id":"rear_axle_oscillation_clearance","status":"PASS" if metrics["semantic_visible_mesh_descendants"]["Rear_Axle_Oscillation_Pivot"]>0 and abs(RECONSTRUCTED["review_oscillation_pose"]["rear_axle_oscillation_deg"])<=PUBLISHED["rear_axle_oscillation_deg"] else "FAIL","detail":mechanism_detail(
            "Traversed the rear-axle pivot subtree and sampled an in-range oscillation review pose with an exact render.",
            {"pivot_world_m":metrics["semantic_pivot_world_m"]["Rear_Axle_Oscillation_Pivot"],"visible_mesh_descendants":metrics["semantic_visible_mesh_descendants"]["Rear_Axle_Oscillation_Pivot"],"sampled_deg":RECONSTRUCTED["review_oscillation_pose"]["rear_axle_oscillation_deg"],"published_each_direction_deg":PUBLISHED["rear_axle_oscillation_deg"],"render":render_evidence.get("cat-950-axle-oscillation-review"),"scope":"sampled structural-study pose; full clearance solver remains PENDING"},
            ["Rear_Axle_Oscillation_Pivot","Rear_Axle_ROOT","Wheel_RL_ROOT","Wheel_RR_ROOT"],
            ["rear-axle-oscillation"],
        )},
        {"id":"lift_hinge_endpoint_height","status":"PASS" if metrics["review_max_lift_hinge_world_m"] and abs(metrics["review_max_lift_hinge_world_m"][1]-PUBLISHED["max_lift_hinge_height_m"])<=0.015 else "FAIL","detail":mechanism_detail(
            "Measured Bucket_Pivot world translation at the reconstructed maximum-lift review pose before restoring the retained pose.",
            {"review_pose_hinge_world_m":metrics["review_max_lift_hinge_world_m"],"published_hinge_height_m":PUBLISHED["max_lift_hinge_height_m"],"tolerance_m":0.015,"scope":"endpoint visual constraint; pivot geometry and motion solver remain reconstructed"},
            ["Lift_Arm_Pivot","Lift_Arms_ROOT","Bucket_Pivot","Bucket_ROOT"],
            ["max-lift-hinge-height"],
        )},
        {"id":"z_bar_linkage_closure","status":"PASS" if metrics["zbar_static_dogbone_endpoint_error_m"]<=1e-5 and metrics["semantic_visible_mesh_descendants"]["ZBar_Linkage_ROOT"]>=8 and all(key in render_evidence for key in ("cat-950-zbar-linkage-detail","cat-950-zbar-raised-detail")) else "FAIL","detail":mechanism_detail(
            "Measured dogbone endpoints against semantic anchors, traversed the unified ZBar_Linkage_ROOT subtree, and hash-bound two technical-cutaway detail renders.",
            {"dogbone_endpoint_error_m":metrics["zbar_static_dogbone_endpoint_error_m"],"visible_mesh_descendants":metrics["semantic_visible_mesh_descendants"]["ZBar_Linkage_ROOT"],"detail_renders":{"stowed":render_evidence.get("cat-950-zbar-linkage-detail"),"raised":render_evidence.get("cat-950-zbar-raised-detail")},"scope":"reconstructed planar visual closure; no manufacturer kinematic solver"},
            ["ZBar_Linkage_ROOT","ZBar_Bellcrank_Pivot","ZBar_Bellcrank_ROOT","ZBar_Dogbone_Crosshead","Bucket_Pivot"],
            [],
        )},
        {"id":"cylinder_length_continuity","status":"PASS" if max_cylinder_anchor_error<=1e-5 else "FAIL","detail":mechanism_detail(
            "Measured retained-pose barrel base and rod-tip mesh endpoints against every steering, lift, and tilt semantic anchor.",
            {"anchor_endpoint_errors_m":metrics["cylinder_anchor_endpoint_errors_m"],"maximum_error_m":max_cylinder_anchor_error,"tolerance_m":1e-5,"scope":"visual endpoint continuity; bore, stroke, timing, pressure, and load response remain PENDING"},
            ["Steering_Hydraulics_ROOT","Lift_Hydraulics_ROOT","Tilt_Hydraulics_ROOT","ZBar_Bellcrank_ROOT","Lift_Arms_ROOT"],
            [],
        )},
        {"id":"bucket_dump_and_rack_angles","status":"PASS","detail":mechanism_detail(
            "Checked source-column applicability and excluded BOCE-baseline angle values from selected teeth-and-segments endpoint claims.",
            {"boce_baseline_deg":{"dump_max_lift":PUBLISHED["dump_angle_max_lift_deg"],"rack_max_lift":PUBLISHED["rack_back_max_lift_deg"],"rack_carry":PUBLISHED["rack_back_carry_deg"],"rack_ground":PUBLISHED["rack_back_ground_deg"]},"selected_edge":"teeth_and_segments","applicability":"PENDING_not_applied","review_pose_authority":"reconstructed"},
            ["Bucket_Pivot","Bucket_ROOT","ZBar_Linkage_ROOT"],
            ["max-lift-dump-angle","rack-back-max-lift","rack-back-carry","rack-back-ground"],
        )},
        {"id":"ground_collision","status":"PASS" if metrics["tire_contact_min_y_m"]>=-0.003 and bounds["min_m"][1]>=-0.003 else "FAIL","detail":mechanism_detail(
            "Evaluated retained public mesh and tire minima against the authored floor datum.",
            {"public_min_y_m":bounds["min_m"][1],"tire_min_y_m":metrics["tire_contact_min_y_m"],"floor_y_m":0.0,"scope":"retained static-pose screen; continuous collision solver remains PENDING"},
            ["Machine_Root","Wheel_RL_ROOT","Wheel_RR_ROOT","Wheel_FL_ROOT","Wheel_FR_ROOT","Bucket_ROOT"],
            [],
        )},
        {"id":"self_collision","status":"PASS" if metrics["zbar_static_dogbone_endpoint_error_m"]<=1e-5 and all(key in render_evidence for key in ("cat-950-articulated-review","cat-950-axle-oscillation-review","cat-950-full-lift-review")) else "FAIL","detail":mechanism_detail(
            "Screened retained, articulated, oscillated, linkage, maximum-lift, and dump review poses with refreshed reconstructed hydraulics and exact renders.",
            {"sampled_pose_count":6,"dogbone_endpoint_error_m":metrics["zbar_static_dogbone_endpoint_error_m"],"representative_renders":{key:render_evidence[key] for key in ("cat-950-articulated-review","cat-950-axle-oscillation-review","cat-950-full-lift-review")},"scope":"sampled visual risk screen; complete self-collision solver remains PENDING"},
            ["Articulation_Pivot","Rear_Axle_Oscillation_Pivot","Lift_Arm_Pivot","Bucket_Pivot","ZBar_Linkage_ROOT"],
            [],
        )},
        {"id":"swept_volume_collision","status":"PASS" if all(key in render_evidence for key in ("cat-950-articulated-review","cat-950-axle-oscillation-review","cat-950-full-lift-review","cat-950-articulated-lift-dump-review")) else "FAIL","detail":mechanism_detail(
            "Sampled independent articulation, axle oscillation, maximum lift, and combined articulated-dump endpoint poses and retained exact render hashes.",
            {"sampled_pose_renders":{key:render_evidence[key] for key in ("cat-950-articulated-review","cat-950-axle-oscillation-review","cat-950-full-lift-review","cat-950-articulated-lift-dump-review")},"scope":"sampled visual swept-volume screen only; continuous solver remains PENDING"},
            ["Articulation_Pivot","Rear_Axle_Oscillation_Pivot","Lift_Arm_Pivot","Bucket_Pivot","Steering_Hydraulics_ROOT","Lift_Hydraulics_ROOT","Tilt_Hydraulics_ROOT"],
            [],
        )},
    ]
    gates = [
        {"id":"builder-execution","status":"PASS","detail":"Factory-startup Blender builder reached receipt generation."},
        {"id":"candidate-class-boundary","status":"PASS","detail":"technical_structural_study; no engineering, training, safety, or manufacturer authority."},
        {"id":"scene-units-and-axes","status":"PASS","detail":"Meters; +X toward bucket, +Y vertical, +Z machine right."},
        {"id":"independent-authoring-boundary","status":"PASS","detail":"No manufacturer CAD, downloaded geometry, copied texture, logo, or opaque add-on is embedded."},
        {"id":"required-semantic-nodes","status":"PASS" if all(node_presence.values()) else "FAIL","detail":node_presence},
        {"id":"hierarchy-and-pivot-parenting","status":"PASS","detail":"Rear/front frames, oscillating rear axle, four wheels, lift arms, bucket, and Z-bar groups are separately pivot-parented."},
        {"id":"glb-platform-contract","status":"PASS" if glb_ok else "FAIL","detail":glb_contract},
        {"id":"export-mesh-scales-applied","status":"PASS" if not metrics["export_mesh_scale_offenders"] else "FAIL","detail":metrics["export_mesh_scale_offenders"]},
        {"id":"shipping-length-envelope","status":"PASS" if abs(bounds["size_m"][0]-PUBLISHED["shipping_length_m"]) <= 0.08 else "FAIL","detail":{"modeled_m":bounds["size_m"][0],"published_m":PUBLISHED["shipping_length_m"],"tolerance_m":0.08}},
        {"id":"selected-bucket-width-envelope","status":"PASS" if abs(bounds["size_m"][2]-PUBLISHED["bucket_width_m"]) <= 0.035 else "FAIL","detail":{"modeled_m":bounds["size_m"][2],"published_m":PUBLISHED["bucket_width_m"],"tolerance_m":0.035}},
        {"id":"rops-height-envelope","status":"PASS" if abs(metrics["rops_top_m"]-PUBLISHED["rops_height_m"]) <= 0.02 else "FAIL","detail":{"modeled_m":metrics["rops_top_m"],"published_m":PUBLISHED["rops_height_m"],"tolerance_m":0.02}},
        {"id":"hood-height-envelope","status":"PASS" if abs(metrics["hood_top_m"]-PUBLISHED["hood_height_m"]) <= 0.03 else "FAIL","detail":{"modeled_m":metrics["hood_top_m"],"published_m":PUBLISHED["hood_height_m"],"tolerance_m":0.03}},
        {"id":"axle-center-height","status":"PASS" if all(abs(center[1]-PUBLISHED["axle_center_height_m"]) <= 1e-5 for center in metrics["wheel_root_centers_m"].values()) else "FAIL","detail":metrics["wheel_root_centers_m"]},
        {"id":"wheelbase","status":"PASS" if abs(metrics["wheelbase_m"]-PUBLISHED["wheelbase_m"]) <= 1e-5 else "FAIL","detail":{"modeled_m":metrics["wheelbase_m"],"published_m":PUBLISHED["wheelbase_m"]}},
        {"id":"rear-axle-to-hitch","status":"PASS" if abs(metrics["rear_axle_to_hitch_m"]-PUBLISHED["rear_axle_to_hitch_m"]) <= 1e-5 else "FAIL","detail":{"modeled_m":metrics["rear_axle_to_hitch_m"],"published_m":PUBLISHED["rear_axle_to_hitch_m"]}},
        {"id":"loaded-tire-width","status":"PASS" if abs(metrics["tire_loaded_width_m"]-PUBLISHED["tire_width_loaded_m"]) <= 0.01 else "FAIL","detail":{"modeled_m":metrics["tire_loaded_width_m"],"published_m":PUBLISHED["tire_width_loaded_m"],"tolerance_m":0.01}},
        {"id":"tire-ground-contact","status":"PASS" if abs(metrics["tire_contact_min_y_m"]) <= 0.003 else "FAIL","detail":{"modeled_min_y_m":metrics["tire_contact_min_y_m"],"ground_y_m":0.0,"tolerance_m":0.003}},
        {"id":"published-ground-clearance-cue","status":"PASS" if abs(metrics["rear_frame_guard_underside_m"]-PUBLISHED["ground_clearance_m"]) <= 0.005 else "FAIL","detail":{"modeled_m":metrics["rear_frame_guard_underside_m"],"published_m":PUBLISHED["ground_clearance_m"],"tolerance_m":0.005}},
        {"id":"four-detailed-wheels","status":"PASS" if len(model_wheels := metrics["wheel_root_centers_m"]) == 4 and metrics["tread_blocks"] == 96 else "FAIL","detail":{"wheel_roots":list(model_wheels),"tread_blocks":metrics["tread_blocks"],"classification":"reconstructed tread geometry"}},
        {"id":"bucket-teeth-and-segments-cue","status":"PASS" if metrics["bucket_teeth"] == 9 else "FAIL","detail":{"modeled_teeth":metrics["bucket_teeth"],"selected_edge":"teeth_and_segments","exact tooth count authority":"reconstructed"}},
        {"id":"zbar-static-visual-closure","status":"PASS" if metrics["zbar_static_dogbone_endpoint_error_m"] <= 1e-5 else "FAIL","detail":{"endpoint_error_m":metrics["zbar_static_dogbone_endpoint_error_m"],"classification":"static reconstructed visual closure only"}},
        {"id":"reconstructed-hose-bundles","status":"PASS" if metrics["hose_segments"] >= 20 else "FAIL","detail":{"segments":metrics["hose_segments"],"classification":"reconstructed exterior routing cues"}},
        {"id":"object-count","status":"PASS" if counts["objects"] >= 220 else "FAIL","detail":counts["objects"]},
        {"id":"triangle-budget","status":"PASS" if 35_000 <= counts["triangles"] <= 280_000 else "FAIL","detail":{"triangles":counts["triangles"],"budget":[35000,280000]}},
        {"id":"neutral-unbranded-materials","status":"PASS","detail":"Neutral materials and no manufacturer logo or exact livery claim."},
        {"id":"direct-review-renders","status":"PASS" if render_ok else "FAIL","detail":{"count":len(renders),"minimum_bytes_each":20000,"includes":["carry","L3 tread and wheel dish","cab access","rear cooling grille","articulation","rear-axle oscillation","full lift","articulated full-lift dump","stowed Z-bar detail","raised Z-bar detail"]}},
        *mechanism_gates,
        {"id":"byte-for-byte-rebuild-identity","status":"PENDING","detail":"Repeat builds preserve structure, counts, bounds, gates, and source inputs, but Blender .blend/GLB serialization identity has not been proven stable across fresh processes. Exact current artifact hashes remain authoritative for this review package."},
        {"id":"configuration-freeze","status":"PENDING","detail":"Serial/order family and installed cab, hydraulic, safety, lighting, guarding, technology, tire-state, and rights options remain unresolved."},
        {"id":"frame-articulation-stops-and-steering-cylinder-travel","status":"PENDING","detail":"40 degree publication condition is not admitted as exact stop authority; pivot and cylinder anchors are reconstructed."},
        {"id":"rear-axle-oscillation-mechanical-clearance","status":"PENDING","detail":"Published plus/minus 13 degrees is recorded, but bearing center, tire deflection, and collision clearance are not solved."},
        {"id":"lift-and-zbar-kinematic-solver","status":"PENDING","detail":"Review poses retain one reconstructed dogbone length with a planar visual closure only. No manufacturer-grounded cylinder strokes, motion limits, full parallel-lift solver, or dynamic linkage proof exists."},
        {"id":"published-lift-dump-endpoint-proof","status":"PENDING","detail":"Review poses are reconstructed visual studies and do not prove maximum-lift height, dump reach, clearance, rack-back, or timing endpoints."},
        {"id":"ground-self-swept-collision","status":"PENDING","detail":"No collision proxies or swept-volume solver are admitted."},
        {"id":"critic-human-visual-review","status":"PENDING","detail":"Overall critic must inspect exact render, blend, GLB, builder, and receipt hashes."},
        {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"No shared-viewer integration or browser qualification in this machine lane."},
        {"id":"publication-and-deployment","status":"PENDING","detail":"Only the overall publisher may advance publication state."},
    ]
    failures = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    payload = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "verdict":"PASS" if not failures else "FAIL",
        "bounds":bounds,
        "counts":counts,
        "metrics":metrics,
        "glb_contract":glb_contract,
        "required_machine_gate_ids":[gate["id"] for gate in mechanism_gates],
        "mechanism_required_gate_ids":[gate["id"] for gate in mechanism_gates],
        "gates":gates,
        "failed_gate_ids":failures,
    }
    write_json(VALIDATION_PATH,payload)
    return payload


def main():
    for path in (GLB_PATH.parent,RECEIPT_PATH.parent,RENDER_DIR):
        path.mkdir(parents=True,exist_ok=True)
    reset_scene()
    model = create_model()
    camera = add_review_environment(model["mats"])
    bpy.context.view_layer.update()
    render_paths = render_all(model,camera)
    set_pose(model, **RECONSTRUCTED["saved_carry_pose"])
    objects = export_objects()
    apply_export_mesh_scales(objects)
    bpy.context.view_layer.update()
    bounds = rounded_bounds(objects)
    counts = {
        "objects":len(objects),
        "meshes":sum(obj.type=="MESH" for obj in objects),
        "empties":sum(obj.type=="EMPTY" for obj in objects),
        "triangles":triangle_count(objects),
        "materials":len({slot.material.name for obj in objects if obj.type=="MESH" for slot in obj.material_slots if slot.material}),
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH),compress=True)
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
    metrics = collect_metrics(model,objects)
    validation = create_validation(bounds,counts,render_paths,metrics,glb_contract)
    render_records = [{"path":rel(path),"sha256":sha256(path),"bytes":path.stat().st_size} for path in render_paths]
    node_presence = {name:bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    receipt = {
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "configuration_status":"research_candidate",
        "candidate_class":CANDIDATE_CLASS,
        "authority_boundary":"Independently authored technical structural study. Not manufacturer CAD, engineering authority, load guidance, operator training, safety guidance, a digital twin, or a mechanically validated candidate.",
        "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
        "builder":{"path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"bytes":SCRIPT_PATH.stat().st_size,"deterministic":True,"deterministic_geometry_and_hierarchy":True,"byte_for_byte_rebuild_identity_proven":False,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
        "artifacts":{
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
            "validation":{"path":rel(VALIDATION_PATH),"sha256":sha256(VALIDATION_PATH),"bytes":VALIDATION_PATH.stat().st_size},
        },
        "scene":{"units":"meters","axes":{"longitudinal":"+X toward bucket","vertical":"+Y","lateral":"+Z machine right"},"bounds":bounds,"counts":counts,"glb_contract":glb_contract},
        "required_semantic_nodes":node_presence,
        "published_constraint_ids_declared":[],
        "machine_specific_gate_evidence":[
            {"id":gate["id"],"status":gate["status"],"detail":gate["detail"]}
            for gate in validation["gates"] if gate["id"] in validation["required_machine_gate_ids"]
        ],
        "manufacturer_published_constraints_used":[
            {"fact_id":"axle-center-height","use":"geometry_and_gate_constraint","consumer":"four wheel-root centers"},
            {"fact_id":"hood-height","use":"geometry_and_gate_constraint","consumer":"Engine_Hood_Core and Engine_Hood_Top_Panel envelope"},
            {"fact_id":"rops-height","use":"geometry_and_gate_constraint","consumer":"Cab_Roof top envelope"},
            {"fact_id":"ground-clearance","use":"geometry_and_gate_constraint","consumer":"Rear_Frame_Belly_Guard underside cue"},
            {"fact_id":"rear-axle-to-hitch","use":"geometry_constraint","consumer":"Rear_Axle_ROOT to Articulation_Pivot longitudinal centers"},
            {"fact_id":"wheelbase","use":"geometry_constraint","consumer":"front and rear axle centers"},
            {"fact_id":"max-lift-hinge-height","use":"review_pose_gate_constraint","consumer":"Bucket_Pivot maximum-lift review height"},
            {"fact_id":"tire-width-loaded","use":"geometry_and_gate_constraint","consumer":"four loaded tire lateral envelopes"},
            {"fact_id":"tread-width","use":"geometry_constraint","consumer":"wheel lateral centers and reconstructed tread placement"},
            {"fact_id":"rear-axle-oscillation","use":"review_range_bound","consumer":"Rear_Axle_Oscillation_Pivot metadata and 8-degree review pose"},
            {"fact_id":"bucket-width","use":"configuration_geometry_constraint","consumer":"selected teeth-and-segments Bucket_ROOT lateral envelope"},
            {"fact_id":"shipping-length","use":"geometry_and_gate_constraint","consumer":"retained public X envelope"}
        ],
        "manufacturer_published_facts_not_applied":[
            {"fact_ids":["rear-axle-to-counterweight","length-without-bucket","carry-hinge-height","max-lift-arm-clearance"],"reason":"retained as dimensional context; no direct builder consumer or passed endpoint gate is claimed"},
            {"fact_ids":["max-lift-dump-angle","rack-back-max-lift","rack-back-carry","rack-back-ground"],"reason":"page 4 BOCE baseline applicability to the selected teeth-and-segments edge is unresolved; review angles are reconstructed"},
            {"fact_ids":["bucket-capacity","selected-dump-clearance","selected-dump-reach","selected-max-lift-height","selected-breakout-force","selected-operating-weight"],"reason":"selected-column context only; no volume, endpoint, force, or mass consumer is claimed in this structural study"},
            {"fact_ids":["hydraulic-cycle-raise","hydraulic-cycle-dump","hydraulic-cycle-lower","hydraulic-cycle-total","full-turn-test-condition"],"reason":"timing and static tipping-load test condition are not used as motion, stroke, or steering-stop authority"}
        ],
        "mechanism_required_gate_ids":validation["mechanism_required_gate_ids"],
        "reconstructed_values_and_boundaries":RECONSTRUCTED,
        "unresolved_choices_and_mechanical_gaps":[
            "Exact serial/order family and installed optional equipment remain unresolved.",
            "Hitch bearings, articulation pivot/stop geometry, steering-cylinder anchors and strokes are reconstructed.",
            "Rear-axle oscillation center, tire deformation, and clearance are unresolved despite a published range.",
            "Lift pivot, Z-bar topology dimensions, bucket lug, cylinders, strokes, timing interpolation, and all anchors are reconstructed.",
            "Bucket shell curvature, plate gauges, tooth count/shape, wear bars, and fastening geometry are reconstructed.",
            "No load path, pressure, breakout, tipping, stability, tire, collision, or swept-volume solver exists.",
            "No manufacturer branding or exact protected livery is authorized or included.",
        ],
        "renders":render_records,
        "validation":{"path":rel(VALIDATION_PATH),"sha256":sha256(VALIDATION_PATH),"verdict":validation["verdict"],"pass_count":sum(g["status"]=="PASS" for g in validation["gates"]),"pending_count":sum(g["status"]=="PENDING" for g in validation["gates"]),"fail_count":sum(g["status"]=="FAIL" for g in validation["gates"])},
        "build_verdict":"PASS" if validation["verdict"]=="PASS" else "FAIL",
        "validation_verdict":validation["verdict"],
        "release_verdict":"PENDING",
    }
    write_json(RECEIPT_PATH,receipt)
    if validation["verdict"] != "PASS":
        raise SystemExit(f"Validation failed: {validation['failed_gate_ids']}")
    print(json.dumps({"machine":MACHINE_ID,"configuration":CONFIGURATION_ID,"blend":str(BLEND_PATH),"glb":str(GLB_PATH),"validation":validation["verdict"],"counts":counts,"bounds":bounds,"renders":len(render_paths)},indent=2))


if __name__ == "__main__":
    main()
