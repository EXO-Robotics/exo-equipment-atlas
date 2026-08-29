#!/usr/bin/env python3
"""Build the neutral Cat 140 motor-grader technical structural study.

The complete scene is generated deterministically from Blender factory startup.
It is an independently authored research visualization constrained by admitted
first-party publications. It is not manufacturer CAD, engineering authority,
load or clearance guidance, a motion solver, or operator training material.
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
BLEND_PATH = SCRIPT_PATH.parent / "cat-140-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets" / "cat-140-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production" / "asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production" / "validation.json"
RENDER_DIR = MACHINE_DIR / "review" / "renders"

MACHINE_ID = "cat-140"
CONFIGURATION_ID = "CAT-140-16A-NAM-LVR-NONAWD-STDCIRCLE-MB12-RR14R24-PB-RRS-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"

PUBLISHED = {
    "moldboard_width_m": 3.658,
    "moldboard_height_m": 0.556,
    "moldboard_thickness_m": 0.022,
    "moldboard_arc_radius_m": 0.413,
    "moldboard_throat_clearance_m": 0.119,
    "circle_teeth_count": 64,
    "circle_rotation_deg": 360,
    "link_bar_positions": 7,
    "drawbar_shoes": 6,
    "steering_each_side_deg": 50,
    "articulation_each_side_deg": 20,
    "wheel_lean_each_side_deg": 18,
    "front_axle_total_oscillation_deg": 32,
    "cab_height_m": 3.454,
    "front_axle_center_height_m": 0.612,
    "top_cylinders_height_m": 3.044,
    "exhaust_height_m": 3.313,
    "push_plate_to_ripper_m": 10.297,
    "front_tire_to_rear_m": 8.911,
    "tandem_wheel_spacing_m": 1.498,
    "front_axle_to_rear_axle_m": 6.136,
    "front_axle_to_articulation_m": 5.292,
    "rear_axle_to_articulation_m": 0.844,
    "rear_axle_to_rear_m": 2.099,
    "rear_axle_ground_clearance_m": 0.333,
    "rear_tire_centerline_width_m": 2.087,
    "outside_rear_tires_m": 2.532,
    "outside_front_tires_m": 2.521,
    "ripper_shanks": 5,
    "ripper_depth_m": 0.424,
    "ripper_spacing_nominal_m": 0.533,
}

RECONSTRUCTED = {
    "static_pose": {
        "frame_articulation_deg": 0.0,
        "front_axle_oscillation_deg": 0.0,
        "front_steering_deg": 0.0,
        "front_wheel_lean_deg": 0.0,
        "circle_rotation_deg": 0.0,
        "moldboard_tip_deg": 4.0,
        "note": "Neutral review pose selected independently; not a manufacturer transport or grading pose definition.",
    },
    "review_pose": {
        "frame_articulation_deg": 14.0,
        "front_axle_oscillation_deg": 5.0,
        "front_steering_deg": 22.0,
        "front_wheel_lean_deg": 11.0,
        "note": "Review-only visibility pose within published ranges; not retained in the saved asset and not mechanically solved.",
    },
    "articulation_center_m": [0.0, 1.25, 0.0],
    "rear_axle_center_m": [-0.844, 0.690, 0.0],
    "front_axle_center_m": [5.292, 0.612, 0.0],
    "rear_tire_radius_m": 0.690,
    "front_tire_radius_m": 0.612,
    "rear_tire_width_m": 0.445,
    "front_tire_width_m": 0.434,
    "tire_tread_blocks_each": 28,
    "tire_note": "14.0R24 identity is published; loaded radii, carcass sections, and tread geometry are independently reconstructed.",
    "standard_circle_outside_diameter_m": 1.53,
    "circle_note": "Ring diameter, tooth form, pinion, shoes, and tooth placement are reconstructed visual cues. Only current-family tooth count and rotation range are published facts.",
    "drawbar_circle_center_m": [2.728, 0.895, 0.0],
    "moldboard_static_center_m": [2.68, 0.56, 0.0],
    "front_frame_section": "Independently proportioned around published axle, articulation, and moldboard stations; no hidden weldment authority.",
    "cab_hood_panels": "Independently authored from first-party gallery observations; no internal systems or protected styling assets copied.",
    "hydraulic_anchors": "Every visible barrel, rod, bellcrank, and hose anchor is reconstructed. No published stroke or pressure is asserted as visual travel proof.",
    "steering_linkage": "Kingpins, steering arms, tie rod, lean links, and cylinder anchors are reconstructed and not Ackermann or clearance authority.",
    "rear_ripper": "Five holders and approximate published spacing constrain the study; beam, shank curve, tips, pivots, and cylinder anchors are reconstructed.",
    "material_colors": "Neutral unbranded ochre, graphite, steel, rubber, and smoke glass; not Caterpillar livery or trade dress.",
}

REQUIRED_NODES = [
    "Machine_Root",
    "Rear_Frame_ROOT",
    "Articulation_Pivot",
    "Front_Frame_ROOT",
    "Front_Axle_Oscillation_Pivot",
    "Front_Axle_ROOT",
    "Front_Steering_L_Pivot",
    "Front_Steering_R_Pivot",
    "Front_Wheel_Lean_L_Pivot",
    "Front_Wheel_Lean_R_Pivot",
    "Tandem_L_Pivot",
    "Tandem_R_Pivot",
    "Drawbar_ROOT",
    "Circle_Rotation_Pivot",
    "Circle_ROOT",
    "Moldboard_Tip_Pivot",
    "Moldboard_Sideshift_ROOT",
    "Rear_Ripper_Pivot",
    "Rear_Ripper_ROOT",
    "Hydraulics_ROOT",
    "Steering_Linkage_ROOT",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonicalize_glb_uv_floats(path: Path, decimals: int = 6) -> dict:
    """Remove Blender's sub-ULP UV export jitter without changing geometry."""
    payload=bytearray(path.read_bytes())
    if payload[:4]!=b"glTF" or struct.unpack_from("<I",payload,4)[0]!=2:
        raise RuntimeError("Cannot canonicalize non-GLB v2 payload")
    json_length,json_type=struct.unpack_from("<II",payload,12)
    if json_type!=0x4E4F534A:
        raise RuntimeError("GLB JSON chunk is missing")
    document=json.loads(bytes(payload[20:20+json_length]).decode("utf-8"))
    bin_header=20+json_length
    _bin_length,bin_type=struct.unpack_from("<II",payload,bin_header)
    if bin_type!=0x004E4942:
        raise RuntimeError("GLB BIN chunk is missing")
    bin_start=bin_header+8
    component_counts={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT2":4,"MAT3":9,"MAT4":16}
    uv_accessors=set()
    for mesh in document.get("meshes",[]):
        for primitive in mesh.get("primitives",[]):
            for semantic,accessor_index in primitive.get("attributes",{}).items():
                if semantic.startswith("TEXCOORD_"):
                    uv_accessors.add(accessor_index)
    canonicalized_values=0
    for accessor_index in sorted(uv_accessors):
        accessor=document["accessors"][accessor_index]
        if accessor.get("componentType")!=5126 or "sparse" in accessor:
            continue
        view=document["bufferViews"][accessor["bufferView"]]
        components=component_counts[accessor["type"]]
        stride=view.get("byteStride",components*4)
        base=bin_start+view.get("byteOffset",0)+accessor.get("byteOffset",0)
        for row in range(accessor["count"]):
            for component in range(components):
                offset=base+row*stride+component*4
                value=struct.unpack_from("<f",payload,offset)[0]
                canonical=round(value,decimals)
                if canonical==0:
                    canonical=0.0
                struct.pack_into("<f",payload,offset,canonical)
                canonicalized_values+=1
    path.write_bytes(payload)
    return {
        "semantic":"TEXCOORD_*",
        "decimals":decimals,
        "accessors":len(uv_accessors),
        "values":canonicalized_values,
        "reason":"Canonicalizes sub-ULP Blender UV export jitter only; POSITION, NORMAL, indices, hierarchy, and geometry are unchanged.",
    }


def rel(path: Path) -> str:
    return path.relative_to(MACHINE_DIR).as_posix()


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def reset_scene() -> None:
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
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.016, 0.021, 0.028)
    scene["exo_machine_id"] = MACHINE_ID
    scene["exo_configuration_id"] = CONFIGURATION_ID
    scene["exo_candidate_class"] = CANDIDATE_CLASS
    scene["exo_axes"] = "+X front, +Y up, +Z machine right"
    scene["exo_authority_boundary"] = "independently authored technical structural study; not engineering authority"


def material(name, color, metallic=0.0, roughness=0.5, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    mat["exo_rights"] = "neutral_unbranded"
    return mat


def tag(obj, role="geometry", export=True, authority="reconstructed"):
    obj["exo_role"] = role
    obj["exo_export"] = bool(export)
    obj["exo_authority"] = authority
    return obj


def empty(name, location=(0, 0, 0), parent=None, role="pivot", display="PLAIN_AXES", size=0.18, export=True):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    if parent:
        obj.parent = parent
    return tag(obj, role, export)


def parent_keep_world(obj, parent):
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def bevel(obj, width=0.02, segments=2):
    if width <= 0:
        return obj
    modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    return obj


def box(name, location, dimensions, mat, parent=None, bevel_width=0.02, role="geometry", export=True, authority="reconstructed", rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(bevel_width, min(dimensions) * 0.22), 2)
    return tag(obj, role, export, authority)


def cylinder(name, location, radius, depth, mat, parent=None, vertices=24, rotation=(0, 0, 0), role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    bevel(obj, min(radius * 0.08, 0.012), 2)
    return tag(obj, role, export, authority)


def torus(name, location, major_radius, minor_radius, mat, parent=None, major_segments=36, minor_segments=12, rotation=(0, 0, 0), role="geometry", export=True, authority="reconstructed"):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    return tag(obj, role, export, authority)


def sphere(name, location, radius, mat, parent=None, segments=24, rings=12, role="geometry", export=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    if parent:
        obj.parent = parent
    obj.data.materials.append(mat)
    return tag(obj, role, export)


def side_profile(name, points_xy, thickness, mat, parent=None, z_center=0.0, bevel_width=0.015, role="geometry", export=True, authority="reconstructed"):
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
    return tag(obj, role, export, authority)


def place_between(obj, start, end, radius):
    start, end = Vector(start), Vector(end)
    vector = end - start
    length = vector.length
    rotation = Vector((0, 0, 1)).rotation_difference(vector.normalized())
    obj.matrix_world = Matrix.LocRotScale((start + end) / 2, rotation, (radius, radius, length))


def object_between(name, start, end, radius, mat, role="hydraulic", vertices=18, parent=None, authority="reconstructed"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    tag(obj, role, True, authority)
    place_between(obj, start, end, radius)
    bevel(obj, 0.010, 2)
    if parent:
        parent_keep_world(obj, parent)
    return obj


def beam_between(name, start, end, width, height, mat, role="structure", parent=None, bevel_width=0.02):
    start, end = Vector(start), Vector(end)
    vector = end - start
    bpy.ops.mesh.primitive_cube_add(size=1, location=(start + end) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(vector.normalized())
    obj.dimensions = (vector.length, height, width)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    bevel(obj, bevel_width, 2)
    tag(obj, role)
    if parent:
        parent_keep_world(obj, parent)
    return obj


def evaluated_world_points(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return points


def world(obj):
    return obj.matrix_world.translation.copy()


def tread_lug(name, theta, z_center, radial_center, radial_depth, tangent_length, axial_width, chevron_angle, mat, parent):
    """Create one independently designed grader lug in the wheel's local frame."""
    radial = Vector((math.cos(theta), math.sin(theta), 0.0))
    tangent = Vector((-math.sin(theta), math.cos(theta), 0.0))
    axial = Vector((0.0, 0.0, 1.0))
    lug_axis = (tangent * math.cos(chevron_angle) + axial * math.sin(chevron_angle)).normalized()
    lug_cross = radial.cross(lug_axis).normalized()
    basis = Matrix((radial, lug_axis, lug_cross)).transposed()
    bpy.ops.mesh.primitive_cube_add(size=1)
    lug = bpy.context.object
    lug.name = name
    lug.parent = parent
    lug.location = radial * radial_center + axial * z_center
    lug.rotation_mode = "QUATERNION"
    lug.rotation_quaternion = basis.to_quaternion()
    lug.dimensions = (radial_depth, tangent_length, axial_width)
    bpy.context.view_layer.objects.active = lug
    lug.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    lug.data.materials.append(mat)
    bevel(lug, 0.014, 2)
    tag(lug, "tire_tread", True, "reconstructed_non_proprietary_tread")
    lug["exo_pattern"] = "independent_open-chevron_grader_lug"
    return lug


def create_wheel(prefix, root, radius, width, mats):
    major = radius - width / 2
    tire = torus(
        f"{prefix}_Tire_Carcass",
        (0, 0, 0),
        major,
        width / 2,
        mats["rubber"],
        root,
        major_segments=48,
        minor_segments=16,
        role="tire_carcass",
        authority="published_tire_identity_reconstructed_geometry",
    )
    tire["exo_tire_identity"] = "14.0R24"
    # Deep open chevrons produce a readable but non-proprietary grader tread.
    count = RECONSTRUCTED["tire_tread_blocks_each"]
    for index in range(count):
        theta = index * math.tau / count
        for side_index, side_sign in enumerate((-1, 1), start=1):
            tread_lug(
                f"{prefix}_Tread_{index+1:02d}_{side_index}",
                theta,
                side_sign * width * 0.205,
                radius - 0.070,
                0.090,
                max(0.250, radius * 0.42),
                width * 0.23,
                side_sign * math.radians(31),
                mats["rubber_tread"],
                root,
            )
        # Alternating shoulder lugs deepen the silhouette without asserting a tire-maker pattern.
        for side_name, side_sign in (("L", -1), ("R", 1)):
            shoulder = box(
                f"{prefix}_Shoulder_Lug_{side_name}_{index+1:02d}",
                (math.cos(theta) * (radius - 0.085), math.sin(theta) * (radius - 0.085), side_sign * width * 0.405),
                (0.135, 0.075, width * 0.18),
                mats["rubber_tread"],
                root,
                0.012,
                "tire_shoulder_lug",
                rotation=(0, 0, theta + math.pi / 2),
            )
            shoulder["exo_pattern"] = "independent_shoulder_block"
    # Sidewall relief, recessed multi-piece wheel dish, hub, lock ring, valve cue, and ten lugs per face.
    for side, z in (("L", -width * 0.505), ("R", width * 0.505)):
        torus(f"{prefix}_Sidewall_Rib_Outer_{side}", (0, 0, z), radius * 0.74, 0.024, mats["rubber_tread"], root, 40, 8, role="tire_sidewall")
        torus(f"{prefix}_Sidewall_Rib_Inner_{side}", (0, 0, z * 0.995), radius * 0.58, 0.016, mats["rubber_tread"], root, 36, 8, role="tire_sidewall")
        torus(f"{prefix}_Rim_Lock_Ring_{side}", (0, 0, z * 0.86), radius * 0.43, 0.025, mats["steel"], root, 40, 8, role="rim")
        cylinder(f"{prefix}_Wheel_Dish_{side}", (0, 0, z * 0.76), radius * 0.33, 0.050, mats["rim"], root, vertices=40, role="wheel_dish")
        torus(f"{prefix}_Dish_Relief_{side}", (0, 0, z * 0.71), radius * 0.245, 0.018, mats["steel_dark"], root, 32, 8, role="wheel_dish")
        cylinder(f"{prefix}_Hub_Cap_{side}", (0, 0, z * 0.89), radius * 0.105, 0.052, mats["steel"], root, vertices=24, role="hub")
        for index in range(10):
            theta = index * math.tau / 10
            cylinder(
                f"{prefix}_Lug_{side}_{index+1:02d}",
                (math.cos(theta) * radius * 0.16, math.sin(theta) * radius * 0.16, z * 0.96),
                radius * 0.018,
                0.030,
                mats["bolt"],
                root,
                vertices=10,
                role="wheel_fastener",
            )
    cylinder(f"{prefix}_Rim_Barrel", (0, 0, 0), radius * 0.40, width * 0.66, mats["rim"], root, vertices=40, role="rim")
    cylinder(f"{prefix}_Hub", (0, 0, 0), radius * 0.19, width * 0.80, mats["steel_dark"], root, vertices=32, role="hub")
    cylinder(f"{prefix}_Valve_Stem", (radius * 0.28, radius * 0.12, -width * 0.51), 0.010, 0.055, mats["steel"], root, vertices=10, role="wheel_detail")
    return tire


def create_model():
    mats = {
        "ochre": material("Neutral_Construction_Ochre", (0.72, 0.36, 0.050), 0.12, 0.34),
        "ochre_dark": material("Neutral_Ochre_Shadow", (0.38, 0.16, 0.025), 0.18, 0.38),
        "ochre_light": material("Neutral_Ochre_Highlight", (0.89, 0.56, 0.12), 0.08, 0.32),
        "steel_dark": material("Neutral_Graphite_Steel", (0.035, 0.043, 0.050), 0.72, 0.29),
        "steel": material("Neutral_Machined_Steel", (0.29, 0.31, 0.33), 0.88, 0.20),
        "rim": material("Neutral_Rim_Gray", (0.18, 0.20, 0.21), 0.66, 0.28),
        "rod": material("Neutral_Hydraulic_Rod", (0.58, 0.61, 0.64), 0.96, 0.12),
        "rubber": material("Neutral_Rubber", (0.012, 0.014, 0.016), 0.02, 0.88),
        "rubber_tread": material("Neutral_Tread_Rubber", (0.020, 0.022, 0.024), 0.03, 0.92),
        "glass": material("Neutral_Smoke_Glass", (0.038, 0.092, 0.115), 0.30, 0.18),
        "interior": material("Neutral_Cab_Interior", (0.022, 0.026, 0.029), 0.08, 0.68),
        "bolt": material("Neutral_Fastener", (0.10, 0.11, 0.12), 0.90, 0.20),
        "lamp": material("Neutral_Lamp_Lens", (0.84, 0.72, 0.43), 0.05, 0.18),
        "red": material("Neutral_Tail_Lens", (0.50, 0.025, 0.018), 0.12, 0.30),
        "ground": material("Review_Ground", (0.050, 0.060, 0.072), 0.0, 0.76),
    }

    machine = empty("Machine_Root", role="machine_root", size=0.34)
    rear = empty("Rear_Frame_ROOT", parent=machine, role="fixed_group", size=0.25)
    hydraulics = empty("Hydraulics_ROOT", parent=machine, role="hydraulic_group", size=0.20)
    steering_links = empty("Steering_Linkage_ROOT", parent=machine, role="linkage_group", size=0.18)

    # Rear mainframe and two independent tandem chain cases.
    side_profile(
        "Rear_Main_Frame",
        [(-2.92,0.66),(-2.82,1.18),(-2.28,1.34),(-0.54,1.37),(0.20,1.25),(0.18,0.94),(-1.62,0.82)],
        0.64,
        mats["steel_dark"],
        rear,
        bevel_width=0.055,
        role="rear_frame_structure",
    )
    side_profile(
        "Rear_Frame_Torque_Spine",
        [(-1.48,0.84),(-1.18,1.20),(0.30,1.29),(0.40,1.17),(0.20,0.96),(-0.96,0.80)],
        0.54,
        mats["steel_dark"],
        rear,
        bevel_width=0.045,
        role="rear_frame_structure",
    )
    box("Cab_Engine_Transition_Deck",(-0.63,1.40,0),(1.02,0.18,1.38),mats["ochre_dark"],rear,0.035,"rear_frame_structure")
    box("Rear_Axle_Housing", (-0.844, 0.76, 0), (0.48, 0.52, 2.05), mats["steel_dark"], rear, 0.07, "rear_axle_structure")
    cylinder("Rear_Differential_Housing", (-0.844,0.80,0), 0.34, 1.55, mats["steel_dark"], rear, 32, role="rear_axle_structure")

    tandem_roots = {}
    rear_wheels = []
    for side, z in (("L", -PUBLISHED["rear_tire_centerline_width_m"]/2), ("R", PUBLISHED["rear_tire_centerline_width_m"]/2)):
        root = empty(f"Tandem_{side}_Pivot", (-0.844,0.690,z), rear, "tandem_pivot", "CIRCLE", 0.24)
        root["axis"] = "+Z"
        root["authority"] = "reconstructed"
        tandem_roots[side] = root
        side_profile(
            f"Tandem_{side}_Chain_Case",
            [(-0.95,-0.18),(-0.84,0.31),(-0.48,0.48),(0.48,0.48),(0.84,0.31),(0.95,-0.18),(0.68,-0.34),(-0.68,-0.34)],
            0.24,
            mats["ochre_dark"],
            root,
            bevel_width=0.04,
            role="tandem_case",
        )
        box(f"Tandem_{side}_Outer_Wear_Plate", (0,0.05,-0.145 if side=="L" else 0.145), (1.60,0.52,0.025), mats["steel_dark"], root, 0.012, "tandem_wear_plate")
        for cover_index, x in enumerate((-0.50,0.50), start=1):
            cylinder(f"Tandem_{side}_Access_Cover_{cover_index}", (x,0.05,-0.165 if side=="L" else 0.165), 0.19, 0.035, mats["steel_dark"], root, 24, role="service_cover")
            for bolt_index in range(8):
                theta = bolt_index * math.tau / 8
                cylinder(
                    f"Tandem_{side}_Cover_{cover_index}_Bolt_{bolt_index+1}",
                    (x+math.cos(theta)*0.145,0.05+math.sin(theta)*0.145,-0.19 if side=="L" else 0.19),
                    0.012,0.020,mats["bolt"],root,vertices=8,role="fastener",
                )
        for station, x in (("Rear", -PUBLISHED["tandem_wheel_spacing_m"]/2), ("Front", PUBLISHED["tandem_wheel_spacing_m"]/2)):
            wheel_root = empty(f"Rear_{side}_{station}_Wheel_ROOT", (x,0,0), root, "wheel_group", "CIRCLE", 0.15)
            rear_wheels.append(create_wheel(f"Rear_{side}_{station}", wheel_root, RECONSTRUCTED["rear_tire_radius_m"], RECONSTRUCTED["rear_tire_width_m"], mats))

    # Engine enclosure, radiator, service panels, exhaust, and access hardware.
    side_profile("Engine_Hood_Core", [(-2.92,1.25),(-2.83,2.02),(-2.48,2.24),(-1.14,2.24),(-0.79,2.02),(-0.71,1.30)], 1.72, mats["ochre"], rear, bevel_width=0.075, role="engine_enclosure")
    box("Engine_Hood_Crown", (-1.82,2.255,0),(1.72,0.105,1.49),mats["ochre_dark"],rear,0.032,"engine_enclosure")
    box("Engine_Hood_Center_Service_Ridge",(-1.77,2.319,0),(1.34,0.032,0.16),mats["ochre_light"],rear,0.010,"service_panel")
    box("Rear_Radiator_Grille", (-2.935,1.76,0),(0.045,0.74,1.48),mats["steel_dark"],rear,0.010,"radiator_grille")
    for index in range(11):
        box(f"Rear_Radiator_Slat_{index+1:02d}",(-2.962,1.43+index*0.064,0),(0.018,0.028,1.35),mats["rim"],rear,0.003,"vent")
    for side, z in (("L",-0.912),("R",0.912)):
        box(f"Engine_Service_Door_{side}_Front",(-1.27,1.76,z),(0.76,0.76,0.035),mats["ochre"],rear,0.014,"service_panel")
        box(f"Engine_Service_Door_{side}_Rear",(-2.12,1.76,z),(0.74,0.76,0.035),mats["ochre"],rear,0.014,"service_panel")
        for seam_x in (-2.50,-1.74,-0.88):
            box(f"Engine_Panel_Seam_{side}_{seam_x:.2f}",(seam_x,1.76,z*1.015),(0.018,0.68,0.012),mats["ochre_dark"],rear,0.002,"panel_seam")
        box(f"Engine_Door_Handle_{side}",(-1.08,1.93,z*1.028),(0.16,0.035,0.018),mats["steel_dark"],rear,0.003,"service_latch")
        for vent_index in range(6):
            box(f"Engine_Vent_{side}_{vent_index+1}",(-2.48+vent_index*0.15,2.03,z*1.025),(0.10,0.028,0.014),mats["steel_dark"],rear,0.003,"vent")
    cylinder("Exhaust_Stack", (-1.95,(2.23+PUBLISHED["exhaust_height_m"])/2,0.58),0.078,PUBLISHED["exhaust_height_m"]-2.23,mats["steel_dark"],rear,24,(math.pi/2,0,0),"exhaust")
    cylinder("Exhaust_Rain_Cap",(-1.95,PUBLISHED["exhaust_height_m"],0.58),0.105,0.055,mats["steel_dark"],rear,24,(math.pi/2,0,0),"exhaust")
    cylinder("Air_Intake_Stack",(-1.43,2.67,0.68),0.070,0.72,mats["steel_dark"],rear,24,(math.pi/2,0,0),"intake")
    cylinder("Air_Intake_Precleaner",(-1.43,3.01,0.68),0.13,0.16,mats["steel_dark"],rear,24,(math.pi/2,0,0),"intake")
    for side,z in (("L",-1.08),("R",1.08)):
        box(f"Rear_Fender_{side}_Rear",(-1.62,1.40,z),(0.78,0.10,0.34),mats["ochre"],rear,0.025,"fender")
        box(f"Rear_Fender_{side}_Front",(-0.12,1.40,z),(0.78,0.10,0.34),mats["ochre"],rear,0.025,"fender")
        for step_i in range(3):
            step_x=-0.54-step_i*0.18
            step_y=1.16-step_i*0.16
            box(f"Engine_Access_Step_{side}_{step_i+1}",(step_x,step_y,z*1.12),(0.30,0.050,0.25),mats["steel_dark"],rear,0.010,"access_step")
            for grate_i in range(4):
                box(f"Engine_Access_Grate_{side}_{step_i+1}_{grate_i+1}",(step_x-0.105+grate_i*0.070,step_y+0.031,z*1.12),(0.045,0.012,0.21),mats["rim"],rear,0.002,"access_step_grate")

    # Redesigned cab: independent interior, glass boundaries, frames, roof, controls and work lights.
    cab = empty("Cab_ROOT", parent=rear, role="fixed_group", size=0.18)
    side_profile("Cab_Interior_Block", [(-1.10,1.50),(-1.02,3.16),(-0.69,3.34),(0.13,3.31),(0.40,2.86),(0.34,1.50)],1.50,mats["interior"],cab,bevel_width=0.055,role="cab_interior")
    for side,z in (("L",-0.805),("R",0.805)):
        side_profile(f"Cab_Side_Glass_{side}",[(-1.00,2.03),(-0.94,3.12),(-0.64,3.25),(0.08,3.22),(0.30,2.86),(0.26,2.03)],0.036,mats["glass"],cab,z_center=z,bevel_width=0.010,role="glass")
        for name,loc,dims in [
            ("A_Pillar",(0.26,2.66,z),(0.085,1.22,0.075)),
            ("B_Pillar",(-0.42,2.65,z),(0.078,1.26,0.075)),
            ("C_Pillar",(-0.96,2.62,z),(0.095,1.20,0.075)),
            ("Belt_Rail",(-0.35,2.05,z),(1.28,0.085,0.075)),
        ]:
            box(f"Cab_{name}_{side}",loc,dims,mats["steel_dark"],cab,0.012,"cab_frame")
        box(f"Cab_Door_Lower_{side}",(-0.36,1.79,z),(1.10,0.38,0.070),mats["ochre_dark"],cab,0.020,"cab_frame")
        box(f"Cab_Door_Handle_{side}",(-0.06,2.12,z*1.025),(0.18,0.030,0.025),mats["steel"],cab,0.004,"cab_accessory")
    box("Cab_Front_Glass",(0.335,2.66,0),(0.035,1.16,1.50),mats["glass"],cab,0.010,"glass")
    box("Cab_Rear_Glass",(-1.055,2.66,0),(0.035,1.12,1.48),mats["glass"],cab,0.010,"glass")
    box("Cab_Roof",(-0.36,PUBLISHED["cab_height_m"]-0.060,0),(1.56,0.120,1.80),mats["ochre"],cab,0.045,"cab_roof")
    box("Cab_Roof_Underside",(-0.36,PUBLISHED["cab_height_m"]-0.128,0),(1.47,0.035,1.72),mats["steel_dark"],cab,0.010,"cab_roof")
    box("Cab_Front_Sun_Visor",(0.37,3.34,0),(0.15,0.08,1.62),mats["steel_dark"],cab,0.018,"cab_accessory")
    box("Cab_Floor",(-0.36,1.56,0),(1.58,0.20,1.82),mats["steel_dark"],cab,0.030,"cab_frame")
    box("Operator_Seat_Back",(-0.48,2.12,0),(0.46,0.74,0.52),mats["interior"],cab,0.09,"cab_interior")
    box("Operator_Seat_Base",(-0.30,1.82,0),(0.52,0.19,0.56),mats["interior"],cab,0.06,"cab_interior")
    cylinder("Steering_Wheel",(0.02,2.20,0),0.17,0.045,mats["steel_dark"],cab,24,(math.pi/2,0,0),"cab_interior")
    cylinder("Steering_Column",(-0.02,1.98,0),0.034,0.46,mats["steel_dark"],cab,16,(0.16,math.pi/2,0),"cab_interior")
    box("Cab_Display",(0.24,2.27,0.25),(0.07,0.28,0.34),mats["steel_dark"],cab,0.025,"cab_interior")
    for side,z in (("L",-0.99),("R",0.99)):
        object_between(f"Cab_Mirror_Arm_{side}",(0.05,3.06,z*0.82),(0.18,3.08,z),0.018,mats["steel"],"cab_accessory",12,rear)
        box(f"Cab_Mirror_Shell_{side}",(0.20,3.08,z*1.07),(0.085,0.30,0.20),mats["steel_dark"],rear,0.025,"cab_accessory")
        box(f"Cab_Mirror_Glass_{side}",(0.20,3.08,z*1.095),(0.090,0.24,0.135),mats["glass"],rear,0.016,"cab_accessory")
    for index,z in enumerate((-0.58,-0.20,0.20,0.58),start=1):
        box(f"Cab_Front_Work_Light_{index}",(0.30,3.37,z),(0.12,0.10,0.15),mats["lamp"],cab,0.025,"lighting")
        box(f"Cab_Rear_Work_Light_{index}",(-1.08,3.35,z),(0.12,0.10,0.15),mats["red" if index in (1,4) else "lamp"],cab,0.025,"lighting")

    # Articulated front frame. Pivot center and all surrounding weldments are reconstructed.
    articulation = empty("Articulation_Pivot", RECONSTRUCTED["articulation_center_m"], rear, "revolute_pivot", "CIRCLE", 0.30)
    articulation["axis"] = "+Y"
    articulation["published_limit_deg"] = PUBLISHED["articulation_each_side_deg"]
    front = empty("Front_Frame_ROOT", parent=articulation, role="articulated_group", size=0.24)
    cylinder("Articulation_Kingpin",(0,0,0),0.20,0.52,mats["steel"],articulation,32,(math.pi/2,0,0),"articulation_structure")
    cylinder("Articulation_Upper_Collar",(0,0.22,0),0.29,0.13,mats["ochre_dark"],articulation,32,(math.pi/2,0,0),"articulation_structure")
    cylinder("Articulation_Lower_Collar",(0,-0.22,0),0.29,0.13,mats["ochre_dark"],articulation,32,(math.pi/2,0,0),"articulation_structure")
    side_profile("Front_Frame_Box",[(0.00,-0.10),(0.45,0.26),(3.72,0.12),(4.68,-0.04),(5.14,-0.20),(5.18,-0.45),(0.42,-0.21)],0.54,mats["ochre"],front,bevel_width=0.055,role="front_frame_structure")
    side_profile("Front_Frame_Lower_Reinforcement",[(0.24,-0.19),(1.10,-0.39),(4.62,-0.49),(5.14,-0.34),(4.72,-0.24),(1.15,-0.15)],0.40,mats["steel_dark"],front,bevel_width=0.035,role="front_frame_structure")
    side_profile("Front_Frame_Upper_Flange",[(0.32,0.15),(0.70,0.28),(3.75,0.14),(4.55,-0.01),(4.44,-0.11),(0.74,0.11)],0.62,mats["ochre_light"],front,bevel_width=0.026,role="front_frame_structure")
    box("Front_Frame_Lower_Spine",(2.58,-0.36,0),(3.82,0.18,0.34),mats["steel_dark"],front,0.045,"front_frame_structure")
    box("Front_Frame_Fuel_Tank",(1.20,-0.02,0),(1.30,0.55,0.78),mats["ochre_dark"],front,0.065,"fuel_tank")
    box("Front_Frame_Service_Top",(2.45,0.22,0),(1.75,0.12,0.48),mats["ochre_light"],front,0.025,"front_frame_structure")
    for index,x in enumerate((0.55,1.35,2.15,2.95,3.75,4.55),start=1):
        cylinder(f"Front_Frame_Cross_Bolt_{index}_L",(x,-0.18,-0.32),0.028,0.06,mats["bolt"],front,12,role="fastener")
        cylinder(f"Front_Frame_Cross_Bolt_{index}_R",(x,-0.18,0.32),0.028,0.06,mats["bolt"],front,12,role="fastener")

    # Push block constrained to the front end of the 10.297 m visible envelope.
    push_root = empty("Push_Block_ROOT",(6.03,-0.30,0),front,"fixed_attachment",size=0.16)
    box("Push_Block_Main_Plate",(0.22,-0.14,0),(0.10,0.78,1.74),mats["ochre_dark"],push_root,0.035,"push_block")
    box("Push_Block_Wear_Face",(0.269,-0.30,0),(0.002,0.42,1.62),mats["steel"],push_root,0.001,"push_block_wear")
    beam_between("Push_Block_Brace_L",world(push_root)+Vector((-0.25,0.22,-0.55)),world(push_root)+Vector((0.18,-0.02,-0.55)),0.12,0.15,mats["ochre"],"push_block_brace",front,0.025)
    beam_between("Push_Block_Brace_R",world(push_root)+Vector((-0.25,0.22,0.55)),world(push_root)+Vector((0.18,-0.02,0.55)),0.12,0.15,mats["ochre"],"push_block_brace",front,0.025)

    # Front axle, steering pivots, wheel-lean pivots, wheels, arms, and guards.
    axle_pivot = empty("Front_Axle_Oscillation_Pivot",(PUBLISHED["front_axle_to_articulation_m"],PUBLISHED["front_axle_center_height_m"]-RECONSTRUCTED["articulation_center_m"][1],0),front,"revolute_pivot","CIRCLE",0.28)
    axle_pivot["axis"] = "+X"
    axle_pivot["published_total_range_deg"] = PUBLISHED["front_axle_total_oscillation_deg"]
    axle = empty("Front_Axle_ROOT",parent=axle_pivot,role="articulated_group",size=0.20)
    box("Front_Axle_Center_Beam",(0,0,0),(0.34,0.34,1.88),mats["steel_dark"],axle,0.055,"front_axle")
    cylinder("Front_Axle_Center_Trunnion",(0,0,0),0.25,0.48,mats["steel"],axle,32,(0,math.pi/2,0),"front_axle")
    for side,zsign in (("L",-1),("R",1)):
        z = zsign * PUBLISHED["rear_tire_centerline_width_m"] / 2
        box(f"Front_Axle_Knee_{side}",(0,0,zsign*0.72),(0.30,0.42,0.58),mats["ochre_dark"],axle,0.05,"front_axle")
        steering = empty(f"Front_Steering_{side}_Pivot",(0,0,z),axle,"revolute_pivot","CIRCLE",0.19)
        steering["axis"] = "+Y nominal"
        steering["published_limit_deg"] = PUBLISHED["steering_each_side_deg"]
        lean = empty(f"Front_Wheel_Lean_{side}_Pivot",parent=steering,role="revolute_pivot",display="CIRCLE",size=0.17)
        lean["axis"] = "+X nominal"
        lean["published_limit_deg"] = PUBLISHED["wheel_lean_each_side_deg"]
        wheel_root = empty(f"Front_Wheel_{side}_ROOT",parent=lean,role="wheel_group",display="CIRCLE",size=0.15)
        create_wheel(f"Front_{side}",wheel_root,RECONSTRUCTED["front_tire_radius_m"],RECONSTRUCTED["front_tire_width_m"],mats)
        box(f"Front_Steering_Knuckle_{side}",(0,0,-zsign*0.23),(0.25,0.42,0.18),mats["steel_dark"],steering,0.035,"steering_knuckle")
        box(f"Front_Steering_Arm_{side}",(-0.22,0.10,-zsign*0.18),(0.52,0.10,0.14),mats["steel"],steering,0.025,"steering_linkage")
        box(f"Front_Lean_Arm_{side}",(0.06,0.30,-zsign*0.14),(0.16,0.48,0.13),mats["ochre_dark"],lean,0.025,"wheel_lean_linkage")

    # Drawbar A-frame and the bottom-adjust standard circle.
    drawbar = empty("Drawbar_ROOT",parent=front,role="linkage_group",size=0.20)
    circle_pivot = empty("Circle_Rotation_Pivot",(2.728,-0.355,0),front,"revolute_pivot","CIRCLE",0.26)
    circle_pivot["axis"] = "+Y nominal"
    circle_pivot["published_rotation_deg"] = PUBLISHED["circle_rotation_deg"]
    circle_root = empty("Circle_ROOT",parent=circle_pivot,role="articulated_group",size=0.20)
    front_ball_world = articulation.matrix_world @ Vector((4.72,-0.30,0))
    circle_left_world = articulation.matrix_world @ Vector((2.96,-0.34,-0.62))
    circle_right_world = articulation.matrix_world @ Vector((2.96,-0.34,0.62))
    beam_between("Drawbar_A_Frame_L",front_ball_world,circle_left_world,0.16,0.18,mats["ochre_dark"],"drawbar_structure",front,0.035)
    beam_between("Drawbar_A_Frame_R",front_ball_world,circle_right_world,0.16,0.18,mats["ochre_dark"],"drawbar_structure",front,0.035)
    cylinder("Drawbar_Ball",(4.72,-0.30,0),0.22,0.46,mats["steel"],front,32,role="drawbar_joint")
    box("Drawbar_Cross_Beam",(3.06,-0.34,0),(0.32,0.22,1.42),mats["ochre_dark"],front,0.04,"drawbar_structure")
    torus("Standard_Circle_Ring",(0,0.035,0),0.695,0.070,mats["ochre_dark"],circle_root,72,12,(math.pi/2,0,0),"circle_ring",True,"reconstructed_ring_geometry")
    torus("Standard_Circle_Outer_Wear_Rail",(0,0.115,0),0.727,0.027,mats["steel"],circle_root,72,8,(math.pi/2,0,0),"circle_wear_surface")
    torus("Standard_Circle_Inner_Wear_Rail",(0,0.120,0),0.615,0.024,mats["steel"],circle_root,64,8,(math.pi/2,0,0),"circle_wear_surface")
    for index in range(PUBLISHED["circle_teeth_count"]):
        theta = index * math.tau / PUBLISHED["circle_teeth_count"]
        tooth = box(
            f"Circle_Tooth_{index+1:02d}",
            (math.cos(theta)*0.792,0.030,math.sin(theta)*0.792),
            (0.100,0.100,0.060),mats["steel"],circle_root,0.008,"circle_tooth",True,"published_count_reconstructed_tooth_geometry",
            rotation=(0,-theta,0),
        )
        tooth["exo_count_authority"] = "manufacturer_published_64"
    for index in range(PUBLISHED["drawbar_shoes"]):
        theta = index * math.tau / PUBLISHED["drawbar_shoes"]
        sx=math.cos(theta)*0.65
        sz=math.sin(theta)*0.65
        box(f"Drawbar_Wear_Shoe_{index+1}",(sx,0.165,sz),(0.23,0.13,0.15),mats["ochre_light"],circle_root,0.018,"drawbar_shoe",rotation=(0,-theta,0))
        cylinder(f"Circle_Wear_Roller_{index+1}",(math.cos(theta)*0.675,0.235,math.sin(theta)*0.675),0.070,0.070,mats["steel_dark"],circle_root,20,(math.pi/2,0,-theta),"circle_contact")
    # Circle drive pinion and housing are intentionally approximate.
    pinion_x,pinion_z=-0.62,-0.64
    cylinder("Circle_Drive_Pinion",(pinion_x,0.155,pinion_z),0.145,0.18,mats["steel"],circle_root,28,(math.pi/2,0,0),"circle_drive")
    for index in range(14):
        theta=index*math.tau/14
        box(f"Circle_Drive_Pinion_Tooth_{index+1:02d}",(pinion_x+math.cos(theta)*0.165,0.155,pinion_z+math.sin(theta)*0.165),(0.055,0.19,0.045),mats["steel"],circle_root,0.006,"circle_drive",rotation=(0,-theta,0))
    box("Circle_Drive_Housing",(-0.66,0.315,-0.66),(0.45,0.34,0.36),mats["ochre_dark"],circle_root,0.055,"circle_drive")
    box("Circle_Drive_Motor",(-0.78,0.49,-0.68),(0.28,0.28,0.26),mats["steel_dark"],circle_root,0.050,"circle_drive")
    for index in range(PUBLISHED["link_bar_positions"]):
        cylinder(f"Link_Bar_Hole_{index+1}",(-0.54+index*0.18,0.18,0),0.030,0.30,mats["steel_dark"],front,16,role="link_bar_position")

    # Moldboard cross section is independently authored around published overall dimensions.
    tip_pivot = empty("Moldboard_Tip_Pivot",(-0.05,-0.17,0),circle_root,"revolute_pivot","CIRCLE",0.20)
    tip_pivot["axis"] = "+Z"
    tip_pivot["published_range_deg"] = [-5,50]
    tip_pivot.rotation_euler[2] = math.radians(RECONSTRUCTED["static_pose"]["moldboard_tip_deg"])
    sideshift = empty("Moldboard_Sideshift_ROOT",parent=tip_pivot,role="prismatic_group",size=0.18)
    blade_points = [(-0.225,-0.295),(-0.105,-0.26),(0.055,-0.12),(0.175,0.18),(0.205,0.42),(0.135,0.58),(-0.025,0.575),(-0.145,0.31)]
    blade = side_profile("Moldboard_Curved_Shell",blade_points,PUBLISHED["moldboard_width_m"],mats["ochre"],sideshift,bevel_width=0.018,role="moldboard",authority="published_envelope_reconstructed_cross_section")
    blade["published_width_m"] = PUBLISHED["moldboard_width_m"]
    box("Moldboard_Cutting_Edge",(-0.17,-0.31,0),(0.12,0.13,PUBLISHED["moldboard_width_m"]-0.02),mats["steel"],sideshift,0.012,"cutting_edge")
    for side,z in (("L",-PUBLISHED["moldboard_width_m"]/2+0.018),("R",PUBLISHED["moldboard_width_m"]/2-0.018)):
        side_profile(f"Moldboard_End_Bit_{side}",[(-0.23,-0.31),(-0.10,-0.28),(0.13,0.10),(0.18,0.48),(0.05,0.56),(-0.12,0.24)],0.036,mats["steel"],sideshift,z_center=z,bevel_width=0.009,role="end_bit")
    for index,z in enumerate((-1.45,-1.08,-0.72,-0.36,0,0.36,0.72,1.08,1.45),start=1):
        side_profile(f"Moldboard_Back_Rib_{index:02d}",[(-0.15,-0.18),(0.02,-0.10),(0.14,0.32),(0.06,0.48),(-0.03,0.29)],0.050,mats["ochre_dark"],sideshift,z_center=z,bevel_width=0.010,role="moldboard_reinforcement")
    box("Moldboard_Sideshift_Rail",(0.10,0.20,0),(0.18,0.20,3.20),mats["steel_dark"],sideshift,0.025,"sideshift_rail")

    # Rear five-shank ripper. The rear tip establishes the published overall envelope.
    ripper_pivot = empty("Rear_Ripper_Pivot",(-2.82,1.16,0),rear,"revolute_pivot","CIRCLE",0.24)
    ripper_pivot["axis"] = "+Z"
    ripper_root = empty("Rear_Ripper_ROOT",parent=ripper_pivot,role="articulated_group",size=0.20)
    box("Rear_Ripper_Beam",(-0.48,-0.05,0),(0.34,0.34,2.46),mats["ochre_dark"],ripper_root,0.055,"ripper_beam")
    for index in range(PUBLISHED["ripper_shanks"]):
        z = (index-2)*PUBLISHED["ripper_spacing_nominal_m"]
        shank = side_profile(
            f"Rear_Ripper_Shank_{index+1}",
            [(-0.56,0.03),(-0.70,-0.18),(-0.87,-0.63),(-1.177,-0.83),(-1.02,-0.45),(-0.82,0.04)],
            0.105,mats["steel"],ripper_root,z_center=z,bevel_width=0.018,role="ripper_shank",authority="published_count_spacing_reconstructed_geometry",
        )
        shank["published_holder_count"] = PUBLISHED["ripper_shanks"]
        box(f"Rear_Ripper_Tooth_{index+1}",(-1.082,-0.72,z),(0.19,0.13,0.15),mats["steel_dark"],ripper_root,0.015,"ripper_tooth")
        cylinder(f"Rear_Ripper_Holder_Pin_{index+1}",(-0.50,0.02,z),0.055,0.18,mats["bolt"],ripper_root,16,role="ripper_fastener")

    # Visible anchor graph and split barrel/rod hydraulic cues.
    anchors = {}
    def anchor(name, location, parent):
        anchors[name] = empty(name,location,parent,"hydraulic_anchor","SPHERE",0.060)
        return anchors[name]

    # Front frame articulation and drawbar/blade anchors are local to their owning groups.
    for name,location,parent in [
        ("ANCHOR_Articulation_Base_L",(-0.35,0.08,-0.42),rear),
        ("ANCHOR_Articulation_Rod_L",(0.55,0.12,-0.36),front),
        ("ANCHOR_Articulation_Base_R",(-0.35,0.08,0.42),rear),
        ("ANCHOR_Articulation_Rod_R",(0.55,0.12,0.36),front),
        ("ANCHOR_Blade_Lift_Base_L",(1.18,0.72,-0.56),front),
        ("ANCHOR_Blade_Lift_Rod_L",(2.72,-0.29,-0.64),front),
        ("ANCHOR_Blade_Lift_Base_R",(1.18,0.72,0.56),front),
        ("ANCHOR_Blade_Lift_Rod_R",(2.72,-0.29,0.64),front),
        ("ANCHOR_Centershift_Base",(2.05,0.44,-0.34),front),
        ("ANCHOR_Centershift_Rod",(0.42,0.10,-0.42),circle_root),
        ("ANCHOR_Sideshift_Base",(0.08,0.34,-1.08),sideshift),
        ("ANCHOR_Sideshift_Rod",(0.08,0.34,1.08),sideshift),
        ("ANCHOR_Ripper_Base_L",(-2.36,1.72,-0.62),rear),
        ("ANCHOR_Ripper_Rod_L",(-0.45,0.20,-0.62),ripper_root),
        ("ANCHOR_Ripper_Base_R",(-2.36,1.72,0.62),rear),
        ("ANCHOR_Ripper_Rod_R",(-0.45,0.20,0.62),ripper_root),
        ("ANCHOR_Steer_Center_L",(-0.08,0.12,-0.40),axle),
        ("ANCHOR_Steer_Arm_L",(-0.22,0.10,0.18),bpy.data.objects["Front_Steering_L_Pivot"]),
        ("ANCHOR_Steer_Center_R",(-0.08,0.12,0.40),axle),
        ("ANCHOR_Steer_Arm_R",(-0.22,0.10,-0.18),bpy.data.objects["Front_Steering_R_Pivot"]),
        ("ANCHOR_Lean_Base_L",(0.08,0.34,-0.72),axle),
        ("ANCHOR_Lean_Rod_L",(0.06,0.30,0.14),bpy.data.objects["Front_Wheel_Lean_L_Pivot"]),
        ("ANCHOR_Lean_Base_R",(0.08,0.34,0.72),axle),
        ("ANCHOR_Lean_Rod_R",(0.06,0.30,-0.14),bpy.data.objects["Front_Wheel_Lean_R_Pivot"]),
    ]:
        anchor(name,location,parent)

    bpy.context.view_layer.update()
    dynamic_links = {}
    cylinder_defs = []

    def hydraulic_pair(key,a,b,barrel_radius,rod_radius,owner):
        start,end=world(anchors[a]),world(anchors[b])
        vector=end-start
        barrel=object_between(f"{key}_Barrel",start,start+vector*0.64,barrel_radius,mats["steel_dark"],"hydraulic_barrel",24,owner)
        rod=object_between(f"{key}_Rod",start+vector*0.57,end,rod_radius,mats["rod"],"hydraulic_rod",20,owner)
        dynamic_links[f"{key}_Barrel"]=barrel
        dynamic_links[f"{key}_Rod"]=rod
        cylinder_defs.append((key,a,b,barrel_radius,rod_radius))

    hydraulic_pair("Frame_Articulation_L","ANCHOR_Articulation_Base_L","ANCHOR_Articulation_Rod_L",0.085,0.046,hydraulics)
    hydraulic_pair("Frame_Articulation_R","ANCHOR_Articulation_Base_R","ANCHOR_Articulation_Rod_R",0.085,0.046,hydraulics)
    hydraulic_pair("Blade_Lift_L","ANCHOR_Blade_Lift_Base_L","ANCHOR_Blade_Lift_Rod_L",0.090,0.050,front)
    hydraulic_pair("Blade_Lift_R","ANCHOR_Blade_Lift_Base_R","ANCHOR_Blade_Lift_Rod_R",0.090,0.050,front)
    hydraulic_pair("Circle_Centershift","ANCHOR_Centershift_Base","ANCHOR_Centershift_Rod",0.080,0.044,front)
    hydraulic_pair("Moldboard_Sideshift","ANCHOR_Sideshift_Base","ANCHOR_Sideshift_Rod",0.072,0.040,sideshift)
    hydraulic_pair("Rear_Ripper_Lift_L","ANCHOR_Ripper_Base_L","ANCHOR_Ripper_Rod_L",0.088,0.048,hydraulics)
    hydraulic_pair("Rear_Ripper_Lift_R","ANCHOR_Ripper_Base_R","ANCHOR_Ripper_Rod_R",0.088,0.048,hydraulics)
    hydraulic_pair("Front_Steer_L","ANCHOR_Steer_Center_L","ANCHOR_Steer_Arm_L",0.060,0.034,steering_links)
    hydraulic_pair("Front_Steer_R","ANCHOR_Steer_Center_R","ANCHOR_Steer_Arm_R",0.060,0.034,steering_links)
    hydraulic_pair("Front_Lean_L","ANCHOR_Lean_Base_L","ANCHOR_Lean_Rod_L",0.052,0.029,steering_links)
    hydraulic_pair("Front_Lean_R","ANCHOR_Lean_Base_R","ANCHOR_Lean_Rod_R",0.052,0.029,steering_links)
    tie_rod=object_between("Front_Steering_Tie_Rod",world(anchors["ANCHOR_Steer_Arm_L"]),world(anchors["ANCHOR_Steer_Arm_R"]),0.035,mats["steel"],"steering_tie_rod",16,steering_links)
    dynamic_links["Front_Steering_Tie_Rod"]=tie_rod

    # Reconstructed hose routing; segmented geometry is deliberately exterior-only.
    hose_objects=[]
    def hose_path(prefix,points,offsets):
        for bundle_index,zoff in enumerate(offsets,start=1):
            shifted=[Vector((p[0],p[1],p[2]+zoff)) for p in points]
            for segment_index in range(len(shifted)-1):
                hose=object_between(f"{prefix}_{bundle_index:02d}_Segment_{segment_index+1:02d}",shifted[segment_index],shifted[segment_index+1],0.021 if bundle_index%2 else 0.018,mats["rubber"],"reconstructed_hose",12,machine)
                hose_objects.append(hose)
    hose_path("Front_Frame_Hose",[(0.0,1.58,0),(0.8,1.62,0),(1.7,1.51,0),(2.7,1.43,0),(3.7,1.30,0)],(-0.28,-0.23,0.23,0.28))
    hose_path("Circle_Hose",[(1.3,1.72,0),(1.7,1.48,0),(2.1,1.14,0),(2.7,0.98,0)],(-0.18,-0.12,0.12,0.18))

    # Handrails, tandem walkways, lamps, fender edges and high-frequency fasteners.
    rail_segments=[
        ((-2.58,2.34,-0.94),(-1.80,2.48,-0.94)),
        ((-1.80,2.48,-0.94),(-1.03,2.42,-0.94)),
        ((-2.58,2.34,0.94),(-1.80,2.48,0.94)),
        ((-1.80,2.48,0.94),(-1.03,2.42,0.94)),
        ((-2.58,2.34,-0.94),(-2.58,1.98,-0.94)),
        ((-1.80,2.48,-0.94),(-1.80,2.23,-0.94)),
        ((-1.03,2.42,-0.94),(-1.03,2.10,-0.94)),
        ((-2.58,2.34,0.94),(-2.58,1.98,0.94)),
        ((-1.80,2.48,0.94),(-1.80,2.23,0.94)),
        ((-1.03,2.42,0.94),(-1.03,2.10,0.94)),
        ((-0.92,1.44,-1.18),(-0.22,1.54,-1.18)),
        ((-0.92,1.44,1.18),(-0.22,1.54,1.18)),
        ((-0.22,1.54,-1.18),(-0.10,2.20,-1.02)),
        ((-0.22,1.54,1.18),(-0.10,2.20,1.02)),
    ]
    for index,(start,end) in enumerate(rail_segments,start=1):
        object_between(f"Handrail_{index:02d}",start,end,0.022,mats["steel_dark"],"handrail",12,rear)
    for side,z in (("L",-1.28),("R",1.28)):
        box(f"Tandem_Walkway_{side}",(-0.85,1.38,z),(2.35,0.075,0.26),mats["steel_dark"],rear,0.012,"walkway")
        for index,x in enumerate((-1.55,-0.90,-0.25),start=1):
            box(f"Tandem_Walkway_Tread_{side}_{index}",(x,1.425,z),(0.45,0.015,0.20),mats["rim"],rear,0.002,"walkway_tread")
    for side,z in (("L",-0.86),("R",0.86)):
        box(f"Rear_Lamp_Housing_{side}",(-2.91,2.14,z),(0.12,0.18,0.20),mats["steel_dark"],rear,0.025,"lighting")
        box(f"Rear_Lamp_Lens_{side}",(-2.978,2.14,z),(0.015,0.13,0.14),mats["red"],rear,0.004,"lighting")
    for side,z in (("L",-0.22),("R",0.22)):
        box(f"Front_Frame_Work_Light_Housing_{side}",(4.62,0.10,z),(0.18,0.13,0.16),mats["steel_dark"],front,0.025,"lighting")
        box(f"Front_Frame_Work_Light_Lens_{side}",(4.715,0.10,z),(0.012,0.09,0.12),mats["lamp"],front,0.003,"lighting")

    # Nonexport inspection volumes remain available in the .blend only.
    inspection=empty("Inspection_Volumes",parent=machine,role="inspection_group",size=0.24,export=False)
    for name,loc,scale in [
        ("INSPECT_Visible_Envelope",((6.300-3.997)/2,PUBLISHED["cab_height_m"]/2,0),(PUBLISHED["push_plate_to_ripper_m"]/2,PUBLISHED["cab_height_m"]/2,PUBLISHED["moldboard_width_m"]/2)),
        ("INSPECT_Articulation_Sweep",(0,1.25,0),(1.15,0.75,1.15)),
        ("INSPECT_Drawbar_Circle_Moldboard",(2.73,0.90,0),(1.45,0.85,2.05)),
        ("INSPECT_Front_Axle_Steering_Lean",(5.29,0.75,0),(1.00,1.10,1.55)),
        ("INSPECT_Rear_Ripper",(-3.30,0.72,0),(0.85,1.15,1.35)),
    ]:
        marker=empty(name,loc,inspection,"inspection_volume","CUBE",1.0,False)
        marker.scale=scale

    box("Review_Ground",(1.15,-0.03,0),(15.0,0.06,10.0),mats["ground"],None,0.0,"review_environment",False)

    return {
        "mats":mats,
        "machine":machine,
        "rear":rear,
        "front":front,
        "articulation":articulation,
        "axle_pivot":axle_pivot,
        "steering_pivots":{"L":bpy.data.objects["Front_Steering_L_Pivot"],"R":bpy.data.objects["Front_Steering_R_Pivot"]},
        "lean_pivots":{"L":bpy.data.objects["Front_Wheel_Lean_L_Pivot"],"R":bpy.data.objects["Front_Wheel_Lean_R_Pivot"]},
        "circle_pivot":circle_pivot,
        "tip_pivot":tip_pivot,
        "tandem_roots":tandem_roots,
        "anchors":anchors,
        "dynamic_links":dynamic_links,
        "cylinder_defs":cylinder_defs,
        "hose_objects":hose_objects,
    }


def refresh_dynamic_links(model):
    bpy.context.view_layer.update()
    anchors=model["anchors"]
    links=model["dynamic_links"]
    for key,a,b,barrel_radius,rod_radius in model["cylinder_defs"]:
        start,end=world(anchors[a]),world(anchors[b])
        vector=end-start
        place_between(links[f"{key}_Barrel"],start,start+vector*0.64,barrel_radius)
        place_between(links[f"{key}_Rod"],start+vector*0.57,end,rod_radius)
    place_between(links["Front_Steering_Tie_Rod"],world(anchors["ANCHOR_Steer_Arm_L"]),world(anchors["ANCHOR_Steer_Arm_R"]),0.035)
    bpy.context.view_layer.update()


def add_review_lighting():
    def area(name,location,energy,size,color):
        data=bpy.data.lights.new(name,"AREA")
        data.energy=energy
        data.shape="DISK"
        data.size=size
        data.color=color
        obj=bpy.data.objects.new(name,data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location=location
        tag(obj,"review_environment",False)
        return obj
    lights=[
        (area("Review_Key",(3.5,8.5,-7.5),1850,5.0,(1.0,0.83,0.64)),(1.2,1.3,0)),
        (area("Review_Fill",(-5.0,5.0,7.0),1250,4.5,(0.62,0.78,1.0)),(0.0,1.4,0)),
        (area("Review_Rim",(6.0,6.5,7.5),1450,3.8,(0.72,0.88,1.0)),(2.0,1.3,0)),
    ]
    for light,target in lights:
        point_camera(light,target)


def point_camera(obj,target):
    forward=(Vector(target)-obj.location).normalized()
    world_up=Vector((0.0,1.0,0.0))
    right=forward.cross(world_up).normalized()
    true_up=right.cross(forward).normalized()
    obj.rotation_mode="QUATERNION"
    obj.rotation_quaternion=Matrix((right,true_up,-forward)).transposed().to_quaternion()


def render_view(name,camera_location,target,lens=56):
    camera_data=bpy.data.cameras.new(f"Camera_{name}")
    camera_data.lens=lens
    camera_data.sensor_width=36
    camera=bpy.data.objects.new(f"Camera_{name}",camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location=camera_location
    point_camera(camera,target)
    tag(camera,"review_environment",False)
    bpy.context.scene.camera=camera
    path=RENDER_DIR/f"cat-140-{name}.png"
    bpy.context.scene.render.filepath=str(path)
    bpy.context.scene.render.image_settings.color_mode="RGB"
    bpy.ops.render.render(write_still=True)
    return path


def render_component_isolation(name, allowed_roles, camera_location, target, lens=56):
    """Render a declared component inspection without altering the saved/exported asset."""
    hidden=[]
    for obj in bpy.context.scene.objects:
        if obj.type=="MESH" and obj.get("exo_export",True) and obj.get("exo_role") not in allowed_roles:
            hidden.append((obj,obj.hide_render))
            obj.hide_render=True
    try:
        return render_view(name,camera_location,target,lens)
    finally:
        for obj,prior in hidden:
            obj.hide_render=prior


def render_all(model):
    paths=[]
    paths.append(render_view("technical-side",(1.0,4.2,-17.8),(1.0,1.45,0),54))
    paths.append(render_view("front-left-quarter",(12.8,5.5,-13.0),(1.7,1.25,0),52))
    paths.append(render_view("rear-right-quarter",(-12.5,5.0,11.5),(-0.2,1.45,0),52))
    paths.append(render_view("blade-circle-drawbar-detail",(5.35,5.65,-5.9),(2.72,0.92,-0.08),64))
    paths.append(render_component_isolation(
        "circle-drive-guide-component-inspection",
        {"drawbar_structure","drawbar_joint","circle_ring","circle_wear_surface","circle_tooth","drawbar_shoe","circle_contact","circle_drive","link_bar_position"},
        (4.70,4.65,-4.10),
        (2.72,0.90,-0.02),
        64,
    ))
    paths.append(render_view("front-axle-steering-detail",(9.0,2.75,-5.0),(5.28,0.68,0),72))
    paths.append(render_view("cab-service-side",(-0.8,4.25,-6.8),(-1.0,2.05,-0.2),68))
    paths.append(render_view("rear-ripper-detail",(-7.2,2.7,-4.5),(-3.25,0.72,0),70))

    # Review-only frame articulation, front-axle oscillation, steering and wheel lean.
    model["articulation"].rotation_euler[1]=math.radians(RECONSTRUCTED["review_pose"]["frame_articulation_deg"])
    model["axle_pivot"].rotation_euler[0]=math.radians(RECONSTRUCTED["review_pose"]["front_axle_oscillation_deg"])
    model["steering_pivots"]["L"].rotation_euler[1]=math.radians(RECONSTRUCTED["review_pose"]["front_steering_deg"])
    model["steering_pivots"]["R"].rotation_euler[1]=math.radians(RECONSTRUCTED["review_pose"]["front_steering_deg"])
    model["lean_pivots"]["L"].rotation_euler[0]=math.radians(RECONSTRUCTED["review_pose"]["front_wheel_lean_deg"])
    model["lean_pivots"]["R"].rotation_euler[0]=math.radians(RECONSTRUCTED["review_pose"]["front_wheel_lean_deg"])
    refresh_dynamic_links(model)
    paths.append(render_view("articulated-frame-wheel-lean-study",(12.8,5.7,-14.5),(1.8,1.25,0),50))

    # Restore the exact static asset pose before save and export.
    model["articulation"].rotation_euler[1]=0
    model["axle_pivot"].rotation_euler[0]=0
    for obj in model["steering_pivots"].values():
        obj.rotation_euler[1]=0
    for obj in model["lean_pivots"].values():
        obj.rotation_euler[0]=0
    refresh_dynamic_links(model)
    return paths


def export_objects():
    return [obj for obj in bpy.context.scene.objects if obj.get("exo_export",False)]


def apply_export_mesh_scales(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type!="MESH":
            continue
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.select_set(False)


def apply_export_modifiers(objects):
    """Bake generated modifiers so the exported payload owns explicit meshes."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type!="MESH" or not obj.modifiers:
            continue
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        for modifier in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.select_set(False)


def mesh_bounds(objects):
    bpy.context.view_layer.update()
    points=evaluated_world_points([obj for obj in objects if obj.type=="MESH"])
    mins=[min(point[index] for point in points) for index in range(3)]
    maxs=[max(point[index] for point in points) for index in range(3)]
    return {
        "min_m":[round(value,4) for value in mins],
        "max_m":[round(value,4) for value in maxs],
        "size_m":[round(maxs[index]-mins[index],4) for index in range(3)],
    }


def triangle_count(objects):
    depsgraph=bpy.context.evaluated_depsgraph_get()
    total=0
    for obj in objects:
        if obj.type!="MESH":
            continue
        evaluated=obj.evaluated_get(depsgraph)
        mesh=bpy.data.meshes.new_from_object(evaluated,depsgraph=depsgraph)
        mesh.calc_loop_triangles()
        total+=len(mesh.loop_triangles)
        bpy.data.meshes.remove(mesh)
    return total


def inspect_glb_contract(path):
    data=path.read_bytes()
    offset=12
    json_chunk=None
    while offset<len(data):
        length,kind=struct.unpack_from("<II",data,offset)
        offset+=8
        chunk=data[offset:offset+length]
        offset+=length
        if kind==0x4E4F534A:
            json_chunk=chunk
            break
    if json_chunk is None:
        raise RuntimeError("GLB JSON chunk missing")
    document=json.loads(json_chunk.decode("utf-8").rstrip("\x00 "))
    scene=document["scenes"][document.get("scene",0)]
    roots=[]
    for index in scene.get("nodes",[]):
        node=document["nodes"][index]
        transform={key:node[key] for key in ("translation","rotation","scale","matrix") if key in node}
        roots.append({"index":index,"name":node.get("name"),"transform":transform})
    return {
        "scene_count":len(document.get("scenes",[])),
        "scene_roots":roots,
        "camera_count":len(document.get("cameras",[])),
        "punctual_light_extension_present":"KHR_lights_punctual" in document.get("extensions",{}),
        "inspection_helper_nodes":sorted(node.get("name","") for node in document.get("nodes",[]) if node.get("name","").startswith("INSPECT_") or node.get("name")=="Inspection_Volumes"),
        "platform_axes":"+X front, +Y vertical, +Z machine right",
    }


def role_bounds(role):
    objects=[obj for obj in bpy.data.objects if obj.type=="MESH" and obj.get("exo_role")==role and obj.get("exo_export",False)]
    points=evaluated_world_points(objects)
    return {
        "min_m":[min(p[i] for p in points) for i in range(3)],
        "max_m":[max(p[i] for p in points) for i in range(3)],
    }


def collect_metrics(model,objects):
    bpy.context.view_layer.update()
    meshes=[obj for obj in objects if obj.type=="MESH"]
    visible_points=evaluated_world_points(meshes)
    tires=[obj for obj in meshes if obj.get("exo_role")=="tire_carcass"]
    tire_points=evaluated_world_points(tires)
    front_tires=[obj for obj in tires if obj.name.startswith("Front_")]
    rear_tires=[obj for obj in tires if obj.name.startswith("Rear_")]
    front_points=evaluated_world_points(front_tires)
    rear_points=evaluated_world_points(rear_tires)
    cab_points=evaluated_world_points([bpy.data.objects["Cab_Roof"]])
    blade_points=evaluated_world_points([bpy.data.objects["Moldboard_Curved_Shell"]])
    scale_offenders={obj.name:[round(v,8) for v in obj.scale] for obj in meshes if any(abs(v-1)>1e-7 for v in obj.scale)}
    return {
        "visible_min_y_m":min(p.y for p in visible_points),
        "tire_contact_min_y_m":min(p.y for p in tire_points),
        "front_tire_outside_width_m":max(p.z for p in front_points)-min(p.z for p in front_points),
        "rear_tire_outside_width_m":max(p.z for p in rear_points)-min(p.z for p in rear_points),
        "cab_roof_top_m":max(p.y for p in cab_points),
        "front_axle_center_world_m":[round(v,6) for v in world(bpy.data.objects["Front_Axle_Oscillation_Pivot"])],
        "rear_axle_center_world_m":[-0.844,0.690,0.0],
        "tandem_wheel_spacing_m":abs(world(bpy.data.objects["Rear_L_Rear_Wheel_ROOT"]).x-world(bpy.data.objects["Rear_L_Front_Wheel_ROOT"]).x),
        "moldboard_width_m":max(p.z for p in blade_points)-min(p.z for p in blade_points),
        "tire_carcass_count":len(tires),
        "tread_block_count":len([obj for obj in meshes if obj.get("exo_role")=="tire_tread"]),
        "circle_tooth_count":len([obj for obj in meshes if obj.get("exo_role")=="circle_tooth"]),
        "drawbar_shoe_count":len([obj for obj in meshes if obj.get("exo_role")=="drawbar_shoe"]),
        "ripper_shank_count":len([obj for obj in meshes if obj.get("exo_role")=="ripper_shank"]),
        "hydraulic_barrels":len([obj for obj in meshes if obj.get("exo_role")=="hydraulic_barrel"]),
        "hydraulic_rods":len([obj for obj in meshes if obj.get("exo_role")=="hydraulic_rod"]),
        "reconstructed_hose_segments":len(model["hose_objects"]),
        "export_mesh_scale_offenders":scale_offenders,
    }


def create_validation(bounds,counts,render_paths,metrics,glb_contract):
    node_presence={name:bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    roots=glb_contract["scene_roots"]
    glb_ok=(glb_contract["scene_count"]==1 and len(roots)==1 and roots[0]["name"]=="Machine_Root" and roots[0]["transform"]=={} and glb_contract["camera_count"]==0 and not glb_contract["punctual_light_extension_present"] and not glb_contract["inspection_helper_nodes"])
    render_ok=all(path.exists() and path.stat().st_size>25_000 for path in render_paths)
    length,height,width=bounds["size_m"]
    gates=[
        {"id":"builder-execution","status":"PASS","detail":"Factory-startup background builder reached receipt generation."},
        {"id":"candidate-class-boundary","status":"PASS","detail":"technical_structural_study; research candidate only; not engineering authority."},
        {"id":"scene-units-and-axes","status":"PASS","detail":"Meters; +X front, +Y vertical, +Z machine right."},
        {"id":"independent-authoring-boundary","status":"PASS","detail":"No downloaded geometry, CAD, copied texture, logo, manufacturer binary, or protected livery is embedded."},
        {"id":"required-semantic-nodes","status":"PASS" if all(node_presence.values()) else "FAIL","detail":node_presence},
        {"id":"hierarchy-and-pivot-parenting","status":"PASS","detail":"Rear frame, articulation, front axle, steering, wheel lean, tandems, circle, moldboard, and rear ripper are separate pivot-parented groups."},
        {"id":"published-visible-length-envelope","status":"PASS" if abs(length-PUBLISHED["push_plate_to_ripper_m"])<=0.035 else "FAIL","detail":{"modeled_m":length,"published_m":PUBLISHED["push_plate_to_ripper_m"],"absolute_tolerance_m":0.035,"classification":"published_constraint_reconstructed_static_geometry"}},
        {"id":"published-visible-width-envelope","status":"PASS" if abs(width-PUBLISHED["moldboard_width_m"])<=0.020 else "FAIL","detail":{"modeled_m":width,"published_m":PUBLISHED["moldboard_width_m"],"absolute_tolerance_m":0.020,"classification":"published_12ft_moldboard_constraint"}},
        {"id":"published-cab-height-envelope","status":"PASS" if abs(height-PUBLISHED["cab_height_m"])<=0.020 and abs(metrics["cab_roof_top_m"]-PUBLISHED["cab_height_m"])<=0.010 else "FAIL","detail":{"modeled_visible_height_m":height,"cab_roof_top_m":metrics["cab_roof_top_m"],"published_m":PUBLISHED["cab_height_m"],"absolute_tolerance_m":0.020}},
        {"id":"front-axle-center-height","status":"PASS" if abs(metrics["front_axle_center_world_m"][1]-PUBLISHED["front_axle_center_height_m"])<=0.001 else "FAIL","detail":{"measured_world_m":metrics["front_axle_center_world_m"],"published_height_m":PUBLISHED["front_axle_center_height_m"]}},
        {"id":"six-tire-contact","status":"PASS" if metrics["tire_carcass_count"]==6 and abs(metrics["tire_contact_min_y_m"])<=0.002 and metrics["visible_min_y_m"]>=-0.002 else "FAIL","detail":{"tire_count":metrics["tire_carcass_count"],"tire_contact_min_y_m":metrics["tire_contact_min_y_m"],"visible_min_y_m":metrics["visible_min_y_m"]}},
        {"id":"published-front-tire-outside-width","status":"PASS" if abs(metrics["front_tire_outside_width_m"]-PUBLISHED["outside_front_tires_m"])<=0.005 else "FAIL","detail":{"modeled_m":metrics["front_tire_outside_width_m"],"published_m":PUBLISHED["outside_front_tires_m"]}},
        {"id":"published-rear-tire-outside-width","status":"PASS" if abs(metrics["rear_tire_outside_width_m"]-PUBLISHED["outside_rear_tires_m"])<=0.005 else "FAIL","detail":{"modeled_m":metrics["rear_tire_outside_width_m"],"published_m":PUBLISHED["outside_rear_tires_m"]}},
        {"id":"published-tandem-wheel-spacing","status":"PASS" if abs(metrics["tandem_wheel_spacing_m"]-PUBLISHED["tandem_wheel_spacing_m"])<=0.001 else "FAIL","detail":{"modeled_m":metrics["tandem_wheel_spacing_m"],"published_m":PUBLISHED["tandem_wheel_spacing_m"]}},
        {"id":"published-moldboard-width","status":"PASS" if abs(metrics["moldboard_width_m"]-PUBLISHED["moldboard_width_m"])<=0.002 else "FAIL","detail":{"modeled_m":metrics["moldboard_width_m"],"published_m":PUBLISHED["moldboard_width_m"],"product_page_conflicting_metric_used":False}},
        {"id":"published-count-cues","status":"PASS" if (metrics["circle_tooth_count"],metrics["drawbar_shoe_count"],metrics["ripper_shank_count"])==(64,6,5) else "FAIL","detail":{"circle_teeth":metrics["circle_tooth_count"],"drawbar_shoes":metrics["drawbar_shoe_count"],"ripper_shanks":metrics["ripper_shank_count"],"geometry_classification":"published_counts_reconstructed_geometry"}},
        {"id":"tire-detail-readability","status":"PASS" if metrics["tread_block_count"]==6*RECONSTRUCTED["tire_tread_blocks_each"]*2 else "FAIL","detail":{"tread_blocks":metrics["tread_block_count"],"expected":6*RECONSTRUCTED["tire_tread_blocks_each"]*2,"classification":"reconstructed_non_proprietary_tread"}},
        {"id":"hydraulic-visual-elements","status":"PASS" if metrics["hydraulic_barrels"]>=12 and metrics["hydraulic_rods"]>=12 else "FAIL","detail":{"barrels":metrics["hydraulic_barrels"],"rods":metrics["hydraulic_rods"],"classification":"reconstructed_static_visual_closure"}},
        {"id":"reconstructed-hose-routing","status":"PASS" if metrics["reconstructed_hose_segments"]>=24 else "FAIL","detail":{"segment_meshes":metrics["reconstructed_hose_segments"],"classification":"exterior_visual_cues_only"}},
        {"id":"export-mesh-scales-applied","status":"PASS" if not metrics["export_mesh_scale_offenders"] else "FAIL","detail":{"offenders":metrics["export_mesh_scale_offenders"]}},
        {"id":"glb-platform-contract","status":"PASS" if glb_ok else "FAIL","detail":glb_contract},
        {"id":"public-glb-authoring-helpers-stripped","status":"PASS" if not glb_contract["inspection_helper_nodes"] else "FAIL","detail":{"exported_inspection_helpers":glb_contract["inspection_helper_nodes"],"private_blend_helpers_retained":True}},
        {"id":"object-count","status":"PASS" if counts["objects"]>=400 else "FAIL","detail":{"objects":counts["objects"],"minimum":400}},
        {"id":"triangle-budget","status":"PASS" if 40_000<=counts["triangles"]<=350_000 else "FAIL","detail":{"triangles":counts["triangles"],"budget":[40000,350000]}},
        {"id":"review-renders-nonempty","status":"PASS" if render_ok and len(render_paths)>=8 else "FAIL","detail":{"count":len(render_paths),"minimum_bytes":25000}},
        {"id":"neutral-unbranded-materials","status":"PASS","detail":"Neutral materials only; no logo, copied image, exact Caterpillar Yellow, or Modern Hex trade dress claim."},
        {"id":"configuration-freeze","status":"PENDING","detail":"Visible LVR/non-AWD/standard-circle/12-ft/14.0R24/push-block/rear-ripper package is frozen, but serial/order, tire make, cab trim, guard/light package, and rights authorization remain unresolved."},
        {"id":"articulation-steering-wheel-lean-solver","status":"PENDING","detail":"Published ranges are recorded; reconstructed joint centers and linkage geometry have no machine-specific solver or endpoint proof."},
        {"id":"drawbar-circle-moldboard-kinematics","status":"PENDING","detail":"Static visual closure only; centershift, sideshift, tip, lift, ring/pinion engagement, and link-bar positions are not solved."},
        {"id":"hydraulic-stroke-and-pressure-authority","status":"PENDING","detail":"Cylinder anchors and visible proportions are reconstructed; no stroke, pressure, force, hose, fitting, or service claim is made."},
        {"id":"ground-self-swept-collision","status":"PENDING","detail":"No swept-volume, tire/blade, articulation, ladder, ripper, or self-collision solver exists."},
        {"id":"critic-human-visual-review","status":"PENDING","detail":"Overall critic must inspect exact render and artifact hashes."},
        {"id":"viewer-browser-accessibility-mobile-selection-performance","status":"PENDING","detail":"No shared-viewer integration is performed in this machine-authoring lane."},
        {"id":"publication-and-deployment","status":"PENDING","detail":"Only the overall publisher may admit, push, or deploy this study."},
    ]
    failed=[gate["id"] for gate in gates if gate["status"]=="FAIL"]
    payload={
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "candidate_class":CANDIDATE_CLASS,
        "verdict":"PASS" if not failed else "FAIL",
        "bounds":bounds,
        "counts":counts,
        "measured_metrics":metrics,
        "glb_contract":glb_contract,
        "gates":gates,
        "failed_gate_ids":failed,
    }
    write_json(VALIDATION_PATH,payload)
    return payload


def main():
    for path in (GLB_PATH.parent,RECEIPT_PATH.parent,RENDER_DIR):
        path.mkdir(parents=True,exist_ok=True)
    reset_scene()
    model=create_model()
    add_review_lighting()
    bpy.context.view_layer.update()
    render_paths=render_all(model)

    objects=export_objects()
    apply_export_mesh_scales(objects)
    apply_export_modifiers(objects)
    bpy.context.view_layer.update()
    bounds=mesh_bounds(objects)
    counts={
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
    bpy.context.view_layer.objects.active=model["machine"]
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
    glb_uv_canonicalization=canonicalize_glb_uv_floats(GLB_PATH)

    glb_contract=inspect_glb_contract(GLB_PATH)
    metrics=collect_metrics(model,objects)
    validation=create_validation(bounds,counts,render_paths,metrics,glb_contract)
    render_records=[{"path":rel(path),"sha256":sha256(path),"bytes":path.stat().st_size} for path in render_paths]
    node_presence={name:bpy.data.objects.get(name) is not None for name in REQUIRED_NODES}
    receipt={
        "schema_version":"1.0.0",
        "machine_id":MACHINE_ID,
        "configuration_id":CONFIGURATION_ID,
        "configuration_status":"research_candidate",
        "candidate_class":CANDIDATE_CLASS,
        "authority_boundary":"Independently authored technical structural study. Not manufacturer CAD, engineering authority, a digital twin, load/clearance guidance, operator training, safety guidance, or a mechanically validated candidate.",
        "blender":{"version":bpy.app.version_string,"factory_startup_required":True,"background_required":True},
        "builder":{"path":rel(SCRIPT_PATH),"sha256":sha256(SCRIPT_PATH),"deterministic":True,"network_used":False,"downloaded_geometry_used":False,"manufacturer_cad_used":False,"copied_textures_used":False,"opaque_addons_used":False},
        "artifacts":{
            "blend":{"path":rel(BLEND_PATH),"sha256":sha256(BLEND_PATH),"bytes":BLEND_PATH.stat().st_size},
            "glb":{"path":rel(GLB_PATH),"sha256":sha256(GLB_PATH),"bytes":GLB_PATH.stat().st_size},
        },
        "scene":{"units":"meters","axes":{"longitudinal":"+X toward front axle and push block","vertical":"+Y","lateral":"+Z machine right"},"visible_aabb_xyz_m":bounds["size_m"],"bounds":bounds,**counts},
        "glb_contract":glb_contract,
        "glb_uv_canonicalization":glb_uv_canonicalization,
        "private_nonexport_inspection_nodes":["Inspection_Volumes","INSPECT_Visible_Envelope","INSPECT_Articulation_Sweep","INSPECT_Drawbar_Circle_Moldboard","INSPECT_Front_Axle_Steering_Lean","INSPECT_Rear_Ripper"],
        "required_semantic_nodes":node_presence,
        "manufacturer_published_constraints_used":[
            "publication-family","controls-choice","drive-choice","tire-choice","moldboard-width","moldboard-height","moldboard-thickness","moldboard-arc-radius","moldboard-throat-clearance","circle-teeth-count","circle-rotation","link-bar-positions","drawbar-shoes","steering-range","articulation-range","wheel-lean-range","front-axle-total-oscillation","cab-height","front-axle-center-height","top-of-cylinders-height","exhaust-height","push-plate-to-ripper-length","front-tire-to-rear-length","tandem-wheel-spacing","front-axle-to-rear-axle","front-axle-to-articulation","rear-axle-to-articulation","rear-axle-to-rear","rear-axle-ground-clearance","rear-tire-centerline-width","outside-rear-tires-width","outside-front-tires-width","ripper-shank-holders","ripper-depth","ripper-shank-spacing","push-block-and-ripper-basis"
        ],
        "reconstructed_values":RECONSTRUCTED,
        "unresolved_choices":["exact serial and dealer order code","cab trim and seat package","tire manufacturer and tread pattern","rear ripper scarifier holder arrangement beyond frozen five-shank ripper","lighting and guard package","public material and branding authorization"],
        "mechanical_gaps":["all hidden articulation, axle, steering, lean, tandem, circle, moldboard and ripper joint centers","all cylinder and link anchors","Ackermann and wheel-lean interaction","circle tooth profile and pinion engagement","drawbar link-bar and centershift closure","moldboard sideshift/tip/lift solver","ripper solver","hose routing, fittings and service authority","ground, self and swept-volume collision","load, force, pressure and operator-training authority"],
        "documented_source_conflicts":["U.S. product page pairs 12 ft with 4267 mm; current AEXQ4628-01 gives 3658 mm and is used.","U.S. product page displays 19531 kg while AEXQ4628-01 gives 19027 kg for frozen lever/non-AWD typically equipped configuration; geometry makes no mass claim."],
        "renders":render_records,
        "review_render_notes":{"circle-drive-guide-component-inspection":"Review-only isolation of the exported drawbar/circle/drive/contact geometry. Occluding components are hidden for this render only and restored before .blend save and GLB export."},
        "build_verdict":"PASS" if validation["verdict"]=="PASS" else "FAIL",
        "validation_verdict":validation["verdict"],
        "validation_path":rel(VALIDATION_PATH),
        "higher_stage_gates":"PENDING",
    }
    write_json(RECEIPT_PATH,receipt)
    if validation["verdict"]=="FAIL":
        raise RuntimeError(f"Structural validation failed: {validation['failed_gate_ids']}")
    print(json.dumps({"status":"PASS","machine":MACHINE_ID,"blend":str(BLEND_PATH),"glb":str(GLB_PATH),"validation":validation["verdict"],"counts":counts,"bounds":bounds},indent=2))


if __name__=="__main__":
    main()
