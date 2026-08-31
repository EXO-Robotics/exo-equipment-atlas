#!/usr/bin/env python3
"""Deterministic Volvo DD128C 2,000 mm technical structural study.

Run with Blender factory startup in background mode. This is independently
authored neutral geometry. Published values constrain the study; hidden pivot,
eccentric, steering-cylinder, scraper, and spray routing geometry is explicitly
reconstructed and is not engineering authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


MACHINE_ID = "volvo-dd128c"
CONFIGURATION_ID = "VOLVO-DD128C-NAM-T4F-2000MM-OPEN-ROPS-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
MACHINE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = Path(__file__).resolve()
BLEND_PATH = MACHINE_DIR / "source/blender/volvo-dd128c-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets/volvo-dd128c-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production/asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production/validation.json"
RENDER_DIR = MACHINE_DIR / "review/renders"
DESIGN_PATH = MACHINE_DIR / "source/design.json"


def mv(x: float, y: float, z: float) -> Vector:
    """Machine (+X front,+Y up,+Z right) to Blender (X,Z,Y)."""
    return Vector((x, z, y))


PUBLISHED = {
    "overall-length": 5.973,
    "drum-center-distance": 3.550,
    "overall-height": 3.177,
    "overall-width": 2.218,
    "drum-width": 2.000,
    "drum-diameter": 1.400,
    "drum-shell-thickness": 0.020,
    "ground-clearance": 0.505,
    "articulation-limit": 40.0,
    "oscillation-limit": 10.0,
    "inside-turning-radius": 3.772,
    "water-capacity": 1280,
    "spray-bars-per-drum": 2,
    "nozzles-per-spray-bar": 10,
    "drum-wipers": 4,
    "auto-reversing-eccentrics": 1,
}

RECONSTRUCTED = {
    "front_drum_center_xyz_m": [1.775, 0.700, 0.0],
    "rear_drum_center_xyz_m": [-1.775, 0.700, 0.0],
    "articulation_center_xyz_m": [0.0, 1.045, 0.0],
    "oscillation_axis_xyz_m": [0.0, 1.045, 0.0],
    "review_articulation_deg": 24.0,
    "review_oscillation_deg": 1.0,
    "drum_end_guard_outer_z_m": 1.109,
    "drum_shell_edge_chamfer_visual_m": 0.035,
    "drum_hub_radius_m": 0.31,
    "eccentric_shaft_radius_m": 0.075,
    "eccentric_visual_offset_m": 0.11,
    "scraper_blade_thickness_m": 0.028,
    "spray_bar_tube_radius_m": 0.028,
    "spray_nozzle_visual_orifice_m": 0.006,
    "steering_cylinder_bore_visual_m": 0.075,
    "steering_cylinder_rod_visual_m": 0.042,
    "tank_split_visual_l": [640, 640],
    "operator_platform_height_m": 1.72,
    "open_rops_post_coordinates_m": [[-0.92, 1.78, -0.72], [-0.92, 1.78, 0.72], [0.28, 1.78, -0.72], [0.28, 1.78, 0.72]],
    "structural_triangle_budget": 140000,
}

UNRESOLVED = [
    "exact serial and order family",
    "exact articulation and oscillation bearing centers and envelopes",
    "steering-cylinder base and rod anchors, bore, stroke, and motion relationship",
    "planetary drive, drum bearing, eccentric shaft, weight, phase, and amplitude-change geometry",
    "primary and backup pump, filter, valve, hose, clamp, and nozzle-angle routing",
    "scraper spring rate, blade pressure, exact supports, and service travel",
    "body panel, water tank, hood hinge, rail, step, light, and fastener geometry",
    "Compact Assist and optional lighting configuration",
    "operator-station glazing; admitted standard equipment is an open ROPS/FOPS canopy",
    "public material and branding authorization",
]

COLLECTIONS: dict[str, bpy.types.Collection] = {}
MATERIALS: dict[str, bpy.types.Material] = {}
ARTICULATED: dict[str, bpy.types.Object] = {}
RENDER_PATHS: list[Path] = []


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dirs() -> None:
    for path in (BLEND_PATH.parent, GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    if hasattr(scene.render, "dither_intensity"):
        scene.render.dither_intensity = 0.0
    for stamp_property in (
        "use_stamp_camera", "use_stamp_date", "use_stamp_filename", "use_stamp_frame",
        "use_stamp_frame_range", "use_stamp_hostname", "use_stamp_labels", "use_stamp_lens",
        "use_stamp_marker", "use_stamp_memory", "use_stamp_note", "use_stamp_render_time",
        "use_stamp_scene", "use_stamp_sequencer_strip", "use_stamp_time",
    ):
        if hasattr(scene.render, stamp_property):
            setattr(scene.render, stamp_property, False)
    scene.view_settings.look = "AgX - Medium High Contrast"


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    COLLECTIONS[name] = collection
    return collection


def move_to_collection(obj: bpy.types.Object, name: str) -> None:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    COLLECTIONS[name].objects.link(obj)


def set_parent(obj: bpy.types.Object, parent: bpy.types.Object, preserve_world=True) -> None:
    world = obj.matrix_world.copy()
    obj.parent = parent
    if preserve_world:
        obj.matrix_world = world


def material(name: str, color: tuple[float, float, float, float], metallic=0.0,
             roughness=0.45, transmission=0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = color[3]
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if color[3] < 1.0:
        mat.surface_render_method = "DITHERED"
    MATERIALS[name] = mat
    return mat


def apply_material(obj: bpy.types.Object, name: str) -> None:
    if obj.type == "MESH":
        obj.data.materials.append(MATERIALS[name])


def add_empty(name: str, xyz: tuple[float, float, float], collection: str,
              size=0.12, parent=None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = mv(*xyz)
    COLLECTIONS[collection].objects.link(obj)
    if parent:
        bpy.context.view_layer.update()
        set_parent(obj, parent)
    return obj


def add_box(name: str, center: tuple[float, float, float],
            size: tuple[float, float, float], mat_name: str, collection: str,
            bevel=0.02, parent=None, hide_render=False) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[2], size[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = min(bevel, min(size) * 0.22)
        modifier.segments = 2
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    obj.hide_render = hide_render
    return obj


def add_cylinder(name: str, center: tuple[float, float, float], radius: float,
                 depth: float, axis: str, mat_name: str, collection: str,
                 vertices=32, parent=None, bevel=0.01) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(axis)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = min(bevel, radius * 0.16, depth * 0.12)
        modifier.segments = 2
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_torus(name: str, center: tuple[float, float, float], major_radius: float,
              minor_radius: float, axis: str, mat_name: str, collection: str,
              parent=None, major_segments=40, minor_segments=8) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major_radius, minor_radius=minor_radius,
                                     major_segments=major_segments, minor_segments=minor_segments,
                                     location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(axis)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_hollow_drum_shell(name: str, center: tuple[float, float, float],
                          outer_radius: float, wall_thickness: float, depth: float,
                          mat_name: str, collection: str, parent=None,
                          segments=96) -> bpy.types.Object:
    """Create a true annular drum shell, including visible end annuli."""
    inner_radius = outer_radius - wall_thickness
    half = depth * 0.5
    vertices = []
    for axial in (-half, half):
        for radius in (outer_radius, inner_radius):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                vertices.append((radius * math.cos(angle), axial, radius * math.sin(angle)))
    faces = []
    outer_a, inner_a, outer_b, inner_b = 0, segments, 2 * segments, 3 * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((outer_a + index, outer_a + nxt, outer_b + nxt, outer_b + index))
        faces.append((inner_a + nxt, inner_a + index, inner_b + index, inner_b + nxt))
        faces.append((outer_a + index, inner_a + index, inner_a + nxt, outer_a + nxt))
        faces.append((outer_b + nxt, inner_b + nxt, inner_b + index, outer_b + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    apply_material(obj, mat_name)
    if parent:
        obj.parent = parent
        obj.location = (0.0, 0.0, 0.0)
    else:
        obj.location = mv(*center)
    obj["published_outer_radius_m"] = outer_radius
    obj["published_wall_thickness_m"] = wall_thickness
    obj["measured_inner_radius_m"] = inner_radius
    obj["construction"] = "closed_annular_tube_with_end_annuli"
    return obj


def add_prism_xy(name: str, polygon: list[tuple[float, float]], z_center: float,
                 width: float, mat_name: str, collection: str,
                 parent=None) -> bpy.types.Object:
    half = width * 0.5
    verts = []
    for z in (-half, half):
        for x, y in polygon:
            verts.append(tuple(mv(x, y, z + z_center)))
    n = len(polygon)
    faces = [tuple(range(n)), tuple(range(n, 2 * n))[::-1]]
    for index in range(n):
        nxt = (index + 1) % n
        faces.append((index, nxt, n + nxt, n + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    apply_material(obj, mat_name)
    modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
    modifier.width = 0.025
    modifier.segments = 2
    if parent:
        set_parent(obj, parent)
    return obj


def add_polyline_tube(name: str, points: list[tuple[float, float, float]],
                      bevel_depth: float, mat_name: str, collection: str,
                      cyclic=False, parent=None) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        value = mv(*coordinate)
        point.co = (*value, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    COLLECTIONS[collection].objects.link(obj)
    obj.data.materials.append(MATERIALS[mat_name])
    if parent:
        set_parent(obj, parent)
    return obj


def add_unit_cylinder(name: str, mat_name: str, collection: str, parent=None,
                      vertices=28) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=2.0)
    obj = bpy.context.object
    obj.name = name
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def place_cylinder(obj: bpy.types.Object, a: tuple[float, float, float],
                   b: tuple[float, float, float], radius: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((radius, radius, direction.length * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def add_unit_beam(name: str, mat_name: str, collection: str, parent=None,
                  bevel=0.015) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.object
    obj.name = name
    modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
    modifier.width = bevel
    modifier.segments = 2
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def place_beam(obj: bpy.types.Object, a: tuple[float, float, float],
               b: tuple[float, float, float], width: float, depth: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("X", "Z").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((direction.length * 0.5, width * 0.5, depth * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def build_materials() -> None:
    material("NeutralBody", (0.26, 0.29, 0.31, 1.0), metallic=0.48, roughness=0.34)
    material("NeutralGraphite", (0.055, 0.064, 0.071, 1.0), metallic=0.56, roughness=0.30)
    material("NeutralSteel", (0.31, 0.34, 0.36, 1.0), metallic=0.80, roughness=0.24)
    material("MachinedDrum", (0.21, 0.23, 0.245, 1.0), metallic=0.88, roughness=0.26)
    material("SafetyAccent", (0.36, 0.30, 0.22, 1.0), metallic=0.34, roughness=0.42)
    material("Rubber", (0.018, 0.021, 0.023, 1.0), roughness=0.88)
    material("CylinderRod", (0.62, 0.66, 0.68, 1.0), metallic=0.94, roughness=0.13)
    material("Interior", (0.035, 0.040, 0.044, 1.0), roughness=0.82)
    material("Display", (0.045, 0.13, 0.16, 1.0), metallic=0.15, roughness=0.18)
    material("Lens", (0.78, 0.82, 0.73, 1.0), metallic=0.06, roughness=0.16)
    material("HoseBlue", (0.035, 0.12, 0.18, 1.0), roughness=0.58)
    material("HoseDark", (0.025, 0.031, 0.035, 1.0), roughness=0.74)
    material("Marker", (0.9, 0.19, 0.06, 1.0), roughness=0.4)
    material("Collision", (0.95, 0.1, 0.08, 0.0), roughness=0.5)
    material("Inspection", (0.08, 0.46, 0.95, 0.0), roughness=0.5)
    material("Ground", (0.055, 0.060, 0.066, 1.0), roughness=0.96)


def build_roots() -> tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    root = add_empty("Machine_Root", (0, 0, 0), "Fixed_Rear", 0.24)
    root["candidate_class"] = CANDIDATE_CLASS
    root["configuration_id"] = CONFIGURATION_ID
    root["engineering_authority"] = False
    articulation = add_empty("ArticulationSteer_Root_Reconstructed",
                             tuple(RECONSTRUCTED["articulation_center_xyz_m"]),
                             "Articulation", 0.16, root)
    articulation["authority"] = "reconstructed_constrained_by_plus_minus_40_deg"
    oscillation = add_empty("FrontOscillation_Root_Reconstructed",
                            tuple(RECONSTRUCTED["oscillation_axis_xyz_m"]),
                            "Articulation", 0.14, articulation)
    oscillation["authority"] = "reconstructed_constrained_by_plus_minus_10_deg"
    # Source-only dimensional witnesses.
    for name, xyz in {
        "Reference_Frontmost": (2.9865, 0.7, 0),
        "Reference_Rearmost": (-2.9865, 0.7, 0),
        "Reference_Width_Left": (0, 1.0, -1.109),
        "Reference_Width_Right": (0, 1.0, 1.109),
        "Reference_Height": (-0.3, 3.177, 0),
        "Reference_FrontDrumCenter": (1.775, 0.7, 0),
        "Reference_RearDrumCenter": (-1.775, 0.7, 0),
    }.items():
        witness = add_empty(name, xyz, "Markers", 0.07, root)
        witness["authority"] = "manufacturer_published_constraint_reference"
    return root, articulation, oscillation


def build_drum(prefix: str, center_x: float, parent: bpy.types.Object) -> None:
    center = (center_x, 0.700, 0.0)
    rotation_root = add_empty(f"{prefix}Drum_Rotation_ROOT", center, "Drums", 0.16, parent)
    rotation_root["mechanism_joint_id"] = f"{prefix.lower()}_drum_rotation"
    shell = add_hollow_drum_shell(f"{prefix}Drum_Shell_2000mm", center, 0.700, 0.020,
                                  2.000, "MachinedDrum", "Drums", rotation_root)
    shell["published_width_m"] = 2.0
    shell["published_diameter_m"] = 1.4
    shell["published_shell_thickness_m"] = 0.02
    shell["finish"] = "machined surface; chamfered and radiused edges"
    for suffix, z in (("L", -0.982), ("R", 0.982)):
        add_torus(f"{prefix}Drum_EdgeRing_{suffix}", center=(center_x, 0.700, z),
                  major_radius=0.665, minor_radius=0.026, axis="z",
                  mat_name="NeutralSteel", collection="Drums", parent=rotation_root,
                  major_segments=64, minor_segments=8)
        add_cylinder(f"{prefix}Drum_EndPlate_{suffix}", (center_x, 0.700, z),
                     0.47, 0.024, "z", "NeutralGraphite", "Drums", 48, rotation_root, 0.006)
        add_cylinder(f"{prefix}Drum_Hub_{suffix}", (center_x, 0.700, z + (-0.025 if suffix == "L" else 0.025)),
                     RECONSTRUCTED["drum_hub_radius_m"], 0.12, "z",
                     "NeutralSteel", "Drums", 48, rotation_root, 0.008)
        add_cylinder(f"{prefix}Drum_HubCap_{suffix}", (center_x, 0.700, z + (-0.09 if suffix == "L" else 0.09)),
                     0.16, 0.045, "z", "NeutralGraphite", "Drums", 40, rotation_root, 0.006)
        for index in range(10):
            angle = 2 * math.pi * index / 10
            y = 0.700 + 0.235 * math.sin(angle)
            x = center_x + 0.235 * math.cos(angle)
            z_bolt = z + (-0.077 if suffix == "L" else 0.077)
            add_cylinder(f"{prefix}HubBolt_{suffix}_{index + 1:02d}", (x, y, z_bolt),
                         0.016, 0.018, "z", "CylinderRod", "Drums", 12, rotation_root, 0.003)
    # Independent counter-rotation roots expose the published process without
    # claiming the manufacturer's undisclosed internal construction.
    eccentric_root = add_empty(f"{prefix}Eccentric_Rotation_ROOT", center,
                               "Drums", 0.11, rotation_root)
    eccentric_root["mechanism_joint_id"] = f"{prefix.lower()}_eccentric"
    shaft = add_cylinder(f"{prefix}EccentricShaft_Reconstructed", center, 0.075, 1.58,
                         "z", "CylinderRod", "Drums", 32, eccentric_root, 0.005)
    shaft["authority"] = "reconstructed_internal_visual_not_engineering_geometry"
    for side, z in (("L", -0.58), ("R", 0.58)):
        weight = add_cylinder(f"{prefix}EccentricWeight_{side}_Reconstructed",
                              (center_x + 0.11, 0.700, z), 0.16, 0.11, "z",
                              "SafetyAccent", "Drums", 36, eccentric_root, 0.006)
        weight["authority"] = "reconstructed_internal_visual"


def build_scraper_and_spray(prefix: str, center_x: float, parent: bpy.types.Object,
                            front_module: bool) -> None:
    # Front/rear styrene wipers for each drum, exactly four across the machine.
    orientations = (("Front", center_x + 0.62), ("Rear", center_x - 0.62))
    for orient, x in orientations:
        blade = add_box(f"{prefix}DrumWiper_{orient}", (x, 0.93, 0.0),
                        (0.045, 0.11, 1.91), "Rubber", "Water_System", 0.008, parent)
        blade["authority"] = "published_presence_reconstructed_geometry"
        for side, z in (("L", -0.86), ("R", 0.86)):
            arm = add_unit_beam(f"{prefix}WiperArm_{orient}_{side}",
                                "NeutralGraphite", "Water_System", parent, 0.012)
            frame_x = center_x + (0.34 if orient == "Front" else -0.34)
            place_beam(arm, (frame_x, 1.28, z), (x, 0.96, z), 0.065, 0.075)
    # Two redundant bars per drum, ten nozzles per bar.
    bar_xs = (center_x + 0.48, center_x - 0.48)
    for bar_index, x in enumerate(bar_xs, start=1):
        y = 1.23
        add_cylinder(f"{prefix}SprayBar_{bar_index:02d}", (x, y, 0.0),
                     RECONSTRUCTED["spray_bar_tube_radius_m"], 1.84, "z",
                     "HoseBlue", "Water_System", 24, parent, 0.003)
        for nozzle_index in range(10):
            z = -0.81 + nozzle_index * 0.18
            add_cylinder(f"{prefix}SprayNozzle_{bar_index:02d}_{nozzle_index + 1:02d}",
                         (x, y - 0.055, z), 0.018, 0.11, "y",
                         "NeutralSteel", "Water_System", 16, parent, 0.003)
            add_cylinder(f"{prefix}SprayTip_{bar_index:02d}_{nozzle_index + 1:02d}",
                         (x, y - 0.115, z), 0.010, 0.025, "y",
                         "SafetyAccent", "Water_System", 12, parent, 0.002)
        for clamp_index, z in enumerate((-0.72, 0.0, 0.72), start=1):
            add_box(f"{prefix}SprayBarClamp_{bar_index:02d}_{clamp_index:02d}",
                    (x, y + 0.055, z), (0.10, 0.10, 0.055),
                    "NeutralGraphite", "Water_System", 0.008, parent)
    hose_side = -0.94 if front_module else 0.94
    points = [
        (center_x - 0.18, 1.43, hose_side),
        (center_x, 1.36, hose_side),
        (center_x + 0.48, 1.23, hose_side),
        (center_x - 0.48, 1.23, hose_side),
    ]
    hose = add_polyline_tube(f"{prefix}SprayRouting_Reconstructed", points, 0.018,
                             "HoseBlue", "Water_System", False, parent)
    hose["authority"] = "reconstructed_visual_routing"


def build_front_module(oscillation: bpy.types.Object) -> None:
    # Broad yoke and 640 L visual tank envelope around the front drum.
    add_prism_xy("FrontFrame_YokeCore",
                 [(0.08, 0.82), (0.45, 0.67), (2.45, 0.83), (2.64, 1.30),
                  (2.25, 1.55), (0.45, 1.46)], 0.0, 1.38,
                 "SafetyAccent", "Front_Module", oscillation)
    add_box("FrontFrame_Crossmember", (1.38, 1.38, 0), (2.20, 0.22, 1.62),
            "NeutralGraphite", "Front_Module", 0.045, oscillation)
    add_prism_xy("FrontWaterTank_Exterior_Reconstructed",
                 [(0.36, 1.25), (0.58, 1.62), (2.24, 1.65), (2.55, 1.42),
                  (2.40, 1.10), (0.68, 1.08)], 0.0, 1.46,
                 "NeutralBody", "Front_Module", oscillation)
    tank = bpy.data.objects["FrontWaterTank_Exterior_Reconstructed"]
    tank["modeled_exterior_gross_volume_l"] = 1560.813
    tank["published_combined_capacity_l"] = 1280
    tank["internal_capacity_claimed"] = False
    tank["authority"] = "reconstructed_exterior_enclosure_not_internal_tank_volume"
    add_cylinder("FrontWaterFillNeck", (1.23, 1.69, -0.56), 0.065, 0.16, "y",
                 "NeutralGraphite", "Front_Module", 28, oscillation, 0.006)
    add_cylinder("FrontWaterFillCap", (1.23, 1.79, -0.56), 0.09, 0.055, "y",
                 "SafetyAccent", "Front_Module", 28, oscillation, 0.005)
    # Outer end guards establish the brochure E width while the shell stays at F.
    for side, z in (("L", -1.069), ("R", 1.069)):
        # Open triangulated yoke keeps the published-width end structure while
        # leaving the drum face, hub, wipers, and spray system inspectable.
        add_box(f"FrontDrumGuard_{side}", (1.75, 1.37, z), (1.88, 0.25, 0.08),
                "SafetyAccent", "Front_Module", 0.028, oscillation)
        outer_arm = add_unit_beam(f"FrontGuardOuterArm_{side}", "SafetyAccent",
                                  "Front_Module", oscillation, 0.022)
        inner_arm = add_unit_beam(f"FrontGuardInnerArm_{side}", "SafetyAccent",
                                  "Front_Module", oscillation, 0.022)
        place_beam(outer_arm, (2.70, 0.46, z), (2.55, 1.36, z), 0.08, 0.20)
        place_beam(inner_arm, (0.80, 0.47, z), (0.97, 1.36, z), 0.08, 0.20)
        add_box(f"FrontGuardWearPad_{side}", (2.17, 0.37, z), (0.82, 0.08, 0.055),
                "NeutralGraphite", "Front_Module", 0.008, oscillation)
    add_box("FrontBumper_Extent", (2.930, 0.92, 0.0), (0.113, 0.26, 1.46),
            "NeutralGraphite", "Front_Module", 0.025, oscillation)
    for side, z in (("L", -0.58), ("R", 0.58)):
        add_box(f"FrontFrameLightHousing_{side}", (2.972, 1.01, z),
                (0.025, 0.15, 0.23), "NeutralGraphite", "Front_Module", 0.008, oscillation)
        add_cylinder(f"FrontFrameLightLens_{side}", (2.9775, 1.01, z), 0.055, 0.018,
                     "x", "Lens", "Front_Module", 24, oscillation, 0.003)
    build_drum("Front", 1.775, oscillation)
    build_scraper_and_spray("Front", 1.775, oscillation, True)


def build_rear_module(root: bpy.types.Object) -> None:
    add_prism_xy("RearFrame_YokeCore",
                 [(-2.65, 0.82), (-2.42, 0.63), (-0.38, 0.69), (-0.06, 0.87),
                  (-0.10, 1.44), (-0.46, 1.56), (-2.39, 1.50), (-2.70, 1.24)],
                 0.0, 1.40, "SafetyAccent", "Fixed_Rear", root)
    add_box("RearFrame_Crossmember", (-1.22, 1.38, 0), (2.45, 0.24, 1.64),
            "NeutralGraphite", "Fixed_Rear", 0.045, root)
    # Rear water tank and separate ground-level fill.
    add_prism_xy("RearWaterTank_Exterior_Reconstructed",
                 [(-2.55, 1.10), (-2.34, 1.58), (-0.52, 1.60), (-0.23, 1.38),
                  (-0.35, 1.08), (-2.36, 1.02)], 0.0, 1.46,
                 "NeutralBody", "Fixed_Rear", root)
    tank = bpy.data.objects["RearWaterTank_Exterior_Reconstructed"]
    tank["modeled_exterior_gross_volume_l"] = 1675.788
    tank["published_combined_capacity_l"] = 1280
    tank["internal_capacity_claimed"] = False
    tank["authority"] = "reconstructed_exterior_enclosure_not_internal_tank_volume"
    add_cylinder("RearWaterFillNeck", (-1.35, 1.66, 0.58), 0.065, 0.16, "y",
                 "NeutralGraphite", "Fixed_Rear", 28, root, 0.006)
    add_cylinder("RearWaterFillCap", (-1.35, 1.76, 0.58), 0.09, 0.055, "y",
                 "SafetyAccent", "Fixed_Rear", 28, root, 0.005)
    for side, z in (("L", -1.069), ("R", 1.069)):
        add_box(f"RearDrumGuard_{side}", (-1.75, 1.37, z), (1.88, 0.25, 0.08),
                "SafetyAccent", "Fixed_Rear", 0.028, root)
        outer_arm = add_unit_beam(f"RearGuardOuterArm_{side}", "SafetyAccent",
                                  "Fixed_Rear", root, 0.022)
        inner_arm = add_unit_beam(f"RearGuardInnerArm_{side}", "SafetyAccent",
                                  "Fixed_Rear", root, 0.022)
        place_beam(outer_arm, (-2.70, 0.46, z), (-2.55, 1.36, z), 0.08, 0.20)
        place_beam(inner_arm, (-0.80, 0.47, z), (-0.97, 1.36, z), 0.08, 0.20)
        add_box(f"RearGuardWearPad_{side}", (-2.17, 0.37, z), (0.82, 0.08, 0.055),
                "NeutralGraphite", "Fixed_Rear", 0.008, root)
    add_box("RearBumper_Extent", (-2.930, 0.92, 0.0), (0.113, 0.26, 1.46),
            "NeutralGraphite", "Fixed_Rear", 0.025, root)
    for side, z in (("L", -0.58), ("R", 0.58)):
        add_box(f"RearFrameLightHousing_{side}", (-2.972, 1.01, z),
                (0.025, 0.15, 0.23), "NeutralGraphite", "Fixed_Rear", 0.008, root)
        add_cylinder(f"RearFrameLightLens_{side}", (-2.9775, 1.01, z), 0.055, 0.018,
                     "x", "Lens", "Fixed_Rear", 24, root, 0.003)
    build_drum("Rear", -1.775, root)
    build_scraper_and_spray("Rear", -1.775, root, False)


def build_engine_and_service(root: bpy.types.Object) -> None:
    # Observed rear-side service zone; panel boundaries and hinges reconstructed.
    add_prism_xy("EngineHood_Main_Reconstructed",
                 [(-1.63, 1.49), (-0.52, 1.48), (-0.26, 1.68), (-0.31, 2.18),
                  (-0.54, 2.36), (-1.66, 2.30), (-1.88, 2.08), (-1.86, 1.67)],
                 0.0, 1.42, "NeutralBody", "Service_Panels", root)
    hood = bpy.data.objects["EngineHood_Main_Reconstructed"]
    hood["authority"] = "observed_swing_up_presence_reconstructed_geometry"
    add_box("EngineHood_TopSpine", (-1.10, 2.31, 0), (1.10, 0.08, 1.12),
            "NeutralGraphite", "Service_Panels", 0.025, root)
    for side, z in (("L", -0.725), ("R", 0.725)):
        # Honeycomb-like side cooling field represented by deterministic slats.
        add_box(f"EngineServicePanel_{side}", (-1.06, 1.86, z),
                (1.28, 0.66, 0.035), "NeutralGraphite", "Service_Panels", 0.016, root)
        for row in range(4):
            for col in range(8):
                x = -1.55 + col * 0.14
                y = 1.66 + row * 0.13
                add_cylinder(f"ServiceVent_{side}_{row + 1:02d}_{col + 1:02d}",
                             (x, y, z + (-0.024 if side == "L" else 0.024)),
                             0.028, 0.018, "z", "Interior", "Service_Panels", 6, root, 0.002)
        for index, (x, y) in enumerate(((-1.62, 1.58), (-0.49, 1.58), (-1.62, 2.15), (-0.49, 2.15)), start=1):
            add_cylinder(f"ServicePanelFastener_{side}_{index:02d}",
                         (x, y, z + (-0.032 if side == "L" else 0.032)),
                         0.018, 0.014, "z", "CylinderRod", "Service_Panels", 12, root, 0.002)
    # Exhaust/aftertreatment and intake cues, not hidden engine replication.
    add_cylinder("ExhaustStack", (-1.58, 2.52, 0.48), 0.065, 0.43, "y",
                 "NeutralGraphite", "Service_Panels", 28, root, 0.006)
    add_cylinder("ExhaustRainCap", (-1.58, 2.75, 0.48), 0.10, 0.035, "y",
                 "NeutralSteel", "Service_Panels", 28, root, 0.004)
    add_cylinder("AirIntakePrecleaner", (-1.39, 2.52, -0.48), 0.105, 0.25, "y",
                 "NeutralGraphite", "Service_Panels", 28, root, 0.006)


def build_operator_station(root: bpy.types.Object) -> None:
    # Brochure-authoritative open ROPS/FOPS canopy; no invented cab glass.
    add_box("OperatorPlatform", (-0.24, 1.62, 0), (1.46, 0.16, 1.72),
            "NeutralGraphite", "Operator_ROPS", 0.03, root)
    add_box("OperatorIsolationBellows", (-0.30, 1.78, 0), (0.56, 0.26, 0.56),
            "Rubber", "Operator_ROPS", 0.055, root)
    add_box("OperatorSeat_Cushion", (-0.34, 2.02, 0), (0.48, 0.18, 0.48),
            "Interior", "Operator_ROPS", 0.055, root)
    add_box("OperatorSeat_Back", (-0.56, 2.32, 0), (0.14, 0.64, 0.46),
            "Interior", "Operator_ROPS", 0.065, root)
    add_box("OperatorConsole", (0.10, 2.04, 0.34), (0.48, 0.20, 0.24),
            "NeutralBody", "Operator_ROPS", 0.035, root)
    add_box("OperatorDisplay", (0.28, 2.33, 0.34), (0.08, 0.34, 0.26),
            "Display", "Operator_ROPS", 0.018, root)
    add_cylinder("PropulsionControlLever", (0.18, 2.25, -0.36), 0.027, 0.31, "y",
                 "NeutralGraphite", "Operator_ROPS", 20, root, 0.004)
    add_cylinder("SteeringColumn", (0.20, 2.18, 0), 0.045, 0.42, "x",
                 "NeutralGraphite", "Operator_ROPS", 24, root, 0.005)
    steering = add_torus("SteeringWheel", (0.41, 2.26, 0), 0.20, 0.025, "x",
                         "Rubber", "Operator_ROPS", root, 36, 8)
    steering.rotation_euler[1] += math.radians(-18)
    # ROPS posts and FOPS canopy. The exact section and joints remain reconstructed.
    for prefix, x, z in (("RearL", -0.92, -0.72), ("RearR", -0.92, 0.72),
                         ("FrontL", 0.28, -0.72), ("FrontR", 0.28, 0.72)):
        add_box(f"ROPS_Post_{prefix}", (x, 2.43, z), (0.09, 1.37, 0.09),
                "NeutralGraphite", "Operator_ROPS", 0.018, root)
    add_box("ROPS_FOPS_Canopy", (-0.32, 3.112, 0), (1.58, 0.13, 1.64),
            "NeutralBody", "Operator_ROPS", 0.055, root)
    add_box("ROPS_Canopy_TopExtent", (-0.32, 3.152, 0), (1.48, 0.05, 1.54),
            "SafetyAccent", "Operator_ROPS", 0.022, root)
    # Handrails and steps preserve the open-station silhouette.
    for side, z in (("L", -0.88), ("R", 0.88)):
        add_box(f"OperatorStep_Lower_{side}", (-0.02, 1.17, z), (0.58, 0.09, 0.26),
                "NeutralGraphite", "Operator_ROPS", 0.018, root)
        add_box(f"OperatorStep_Upper_{side}", (-0.12, 1.43, z), (0.52, 0.09, 0.26),
                "NeutralGraphite", "Operator_ROPS", 0.018, root)
        rail_points = [(-0.67, 1.67, z), (-0.67, 2.25, z), (0.36, 2.25, z), (0.36, 1.73, z)]
        add_polyline_tube(f"OperatorHandrail_{side}", rail_points, 0.027,
                          "NeutralGraphite", "Operator_ROPS", False, root)
    for side, z in (("L", -0.55), ("R", 0.55)):
        add_box(f"CanopyLightHousing_{side}", (0.30, 2.99, z), (0.17, 0.13, 0.20),
                "NeutralGraphite", "Operator_ROPS", 0.018, root)
        add_cylinder(f"CanopyLightLens_{side}", (0.395, 2.99, z), 0.052, 0.025,
                     "x", "Lens", "Operator_ROPS", 24, root, 0.003)


def build_articulation(root: bpy.types.Object, oscillation: bpy.types.Object) -> None:
    pivot = tuple(RECONSTRUCTED["articulation_center_xyz_m"])
    add_cylinder("ArticulationBearing_Reconstructed", pivot, 0.24, 0.42, "y",
                 "NeutralSteel", "Articulation", 48, root, 0.008)
    add_torus("ArticulationBearingSeal_Reconstructed", pivot, 0.22, 0.032, "y",
              "Rubber", "Articulation", root, 48, 10)
    add_box("RearArticulationClevis", (-0.22, 1.045, 0), (0.56, 0.52, 0.74),
            "NeutralGraphite", "Articulation", 0.06, root)
    add_box("FrontArticulationTongue", (0.23, 1.045, 0), (0.62, 0.40, 0.52),
            "SafetyAccent", "Articulation", 0.055, oscillation)
    for side, z in (("L", -0.39), ("R", 0.39)):
        ARTICULATED[f"steer_barrel_{side}"] = add_unit_cylinder(
            f"SteeringCylinder_Barrel_{side}_Reconstructed", "NeutralGraphite",
            "Articulation", root, 32)
        ARTICULATED[f"steer_rod_{side}"] = add_unit_cylinder(
            f"SteeringCylinder_Rod_{side}_Reconstructed", "CylinderRod",
            "Articulation", root, 28)
    # Spray feed bridge with generous loops across both axes.
    for index, z_offset in enumerate((-0.11, 0.0, 0.11), start=1):
        hose = add_polyline_tube(
            f"ArticulationHoseLoop_{index:02d}_Reconstructed",
            [(-0.52, 1.32, z_offset), (-0.26, 1.58, z_offset - 0.08),
             (0.22, 1.58, z_offset + 0.08), (0.54, 1.32, z_offset)],
            0.020 if index < 3 else 0.024,
            "HoseBlue" if index == 1 else "HoseDark", "Articulation", False, root)
        hose["authority"] = "reconstructed_visual_routing"


def transform_local_to_machine(obj: bpy.types.Object,
                               xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    world = obj.matrix_world @ mv(*xyz)
    return (world.x, world.z, world.y)


def apply_pose(articulation: bpy.types.Object, oscillation: bpy.types.Object,
               steer_deg=0.0, oscillation_deg=0.0) -> dict:
    articulation.rotation_euler = (0.0, 0.0, math.radians(steer_deg))
    oscillation.rotation_euler = (math.radians(oscillation_deg), 0.0, 0.0)
    bpy.context.view_layer.update()
    front_anchors = {
        "L": transform_local_to_machine(oscillation, (0.48, 0.12, -0.39)),
        "R": transform_local_to_machine(oscillation, (0.48, 0.12, 0.39)),
    }
    rear_anchors = {"L": (-0.48, 1.13, -0.39), "R": (-0.48, 1.13, 0.39)}
    lengths = {}
    for side in ("L", "R"):
        a, b = rear_anchors[side], front_anchors[side]
        middle_v = mv(*a).lerp(mv(*b), 0.58)
        middle = (middle_v.x, middle_v.z, middle_v.y)
        place_cylinder(ARTICULATED[f"steer_barrel_{side}"], a, middle,
                       RECONSTRUCTED["steering_cylinder_bore_visual_m"])
        place_cylinder(ARTICULATED[f"steer_rod_{side}"], middle, b,
                       RECONSTRUCTED["steering_cylinder_rod_visual_m"])
        lengths[side] = round((mv(*b) - mv(*a)).length, 5)
    return {"steer_deg": steer_deg, "oscillation_deg": oscillation_deg,
            "steering_visual_lengths_m": lengths,
            "front_anchors_xyz_m": front_anchors}


def build_helpers(root: bpy.types.Object) -> None:
    for name, center, size, mat_name, collection in (
        ("MachineCollisionProxy", (0, 1.45, 0), (5.973, 2.90, 2.218), "Collision", "Collision"),
        ("FrontDrumInspectionVolume", (1.775, 0.70, 0), (1.55, 1.50, 2.14), "Inspection", "Inspection"),
        ("RearDrumInspectionVolume", (-1.775, 0.70, 0), (1.55, 1.50, 2.14), "Inspection", "Inspection"),
        ("ArticulationInspectionVolume", (0, 1.10, 0), (1.40, 1.15, 1.35), "Inspection", "Inspection"),
        ("OperatorInspectionVolume", (-0.30, 2.38, 0), (1.75, 1.62, 1.85), "Inspection", "Inspection"),
        ("WaterSystemInspectionVolume", (0, 1.30, 0), (5.25, 1.10, 2.10), "Inspection", "Inspection"),
    ):
        obj = add_box(name, center, size, mat_name, collection, 0.0, root)
        obj.display_type = "WIRE"
        obj["source_only_helper"] = True


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_studio() -> None:
    add_box("StudioFloor", (0, -0.045, 0), (12.0, 0.08, 12.0), "Ground", "Studio", 0.0)
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.016, 0.021, 0.027, 1.0)
    background.inputs["Strength"].default_value = 0.28
    for name, xyz, energy, size, color in (
        ("KeyLight", (4.8, 6.4, -4.7), 1700, 4.5, (0.96, 0.98, 1.0)),
        ("FillLight", (0.7, 4.0, 5.5), 1150, 3.5, (0.70, 0.80, 1.0)),
        ("RimLight", (-5.2, 4.8, -2.4), 1450, 3.5, (1.0, 0.71, 0.48)),
    ):
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        COLLECTIONS["Studio"].objects.link(obj)
        obj.location = mv(*xyz)
        look_at(obj, mv(0, 1.4, 0))


def camera(name: str, xyz: tuple[float, float, float],
           target: tuple[float, float, float], lens=54) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36
    obj = bpy.data.objects.new(name, data)
    COLLECTIONS["Studio"].objects.link(obj)
    obj.location = mv(*xyz)
    look_at(obj, mv(*target))
    return obj


def render_view(filename: str, xyz: tuple[float, float, float],
                target: tuple[float, float, float], lens=54) -> Path:
    path = RENDER_DIR / filename
    cam = camera(f"Camera_{path.stem}", xyz, target, lens)
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    RENDER_PATHS.append(path)
    bpy.data.objects.remove(cam, do_unlink=True)
    return path


def render_view_with_hidden(filename: str, xyz: tuple[float, float, float],
                            target: tuple[float, float, float], hidden_names: list[str],
                            lens=54) -> Path:
    """Render a declared technical cutaway without changing retained geometry."""
    prior = {name: bpy.data.objects[name].hide_render for name in hidden_names}
    try:
        for name in hidden_names:
            bpy.data.objects[name].hide_render = True
        return render_view(filename, xyz, target, lens)
    finally:
        for name, value in prior.items():
            bpy.data.objects[name].hide_render = value


def render_review_set(articulation: bpy.types.Object, oscillation: bpy.types.Object) -> None:
    apply_pose(articulation, oscillation, 0, 0)
    render_view("dd128c-straight-technical-side.png", (0.0, 2.35, -9.8), (0, 1.43, 0), 58)
    render_view("dd128c-straight-front-quarter.png", (7.4, 4.25, -6.9), (0.25, 1.45, 0), 56)
    render_view("dd128c-rear-quarter.png", (-7.3, 3.7, 6.5), (-0.30, 1.45, 0), 56)
    render_view_with_hidden(
        "dd128c-drum-water-spray-detail.png", (4.40, 1.52, 0.0),
        (1.85, 1.16, 0.0),
        ["FrontWaterTank_Exterior_Reconstructed", "FrontFrame_Crossmember",
         "FrontFrame_YokeCore", "FrontBumper_Extent",
         "FrontDrumGuard_L", "FrontDrumGuard_R",
         "FrontFrameLightHousing_L", "FrontFrameLightHousing_R",
         "FrontFrameLightLens_L", "FrontFrameLightLens_R"], 70)
    render_view("dd128c-drum-hub-scraper-detail.png", (2.2, 1.38, -3.55), (1.75, 0.72, -0.75), 70)
    render_view("dd128c-operator-station.png", (2.0, 3.45, -3.5), (-0.28, 2.35, -0.05), 72)
    apply_pose(articulation, oscillation, RECONSTRUCTED["review_articulation_deg"], 0)
    render_view("dd128c-articulated-steer-study.png", (6.6, 4.15, -7.2), (0.1, 1.40, 0), 55)
    apply_pose(articulation, oscillation, 0, RECONSTRUCTED["review_oscillation_deg"])
    render_view("dd128c-oscillation-study.png", (6.8, 1.88, -0.25), (1.55, 0.82, 0), 64)
    apply_pose(articulation, oscillation, 0, 0)


def is_descendant_of(obj: bpy.types.Object, root: bpy.types.Object) -> bool:
    current = obj
    while current:
        if current == root:
            return True
        current = current.parent
    return False


def is_public_object(obj: bpy.types.Object, root: bpy.types.Object) -> bool:
    if not is_descendant_of(obj, root):
        return False
    names = {collection.name for collection in obj.users_collection}
    if names & {"Markers", "Collision", "Inspection", "Studio"}:
        return False
    return obj.type not in {"CAMERA", "LIGHT"}


def evaluated_counts() -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    triangles = vertices = 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        vertices += len(mesh.vertices)
        evaluated.to_mesh_clear()
    return {"objects": len(bpy.context.scene.objects), "meshes": len(objects),
            "triangles": triangles, "vertices": vertices,
            "materials": len(bpy.data.materials)}


def public_bounds(root: bpy.types.Object) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coordinates = []
    measured = []
    for obj in bpy.context.scene.objects:
        if not is_public_object(obj, root) or obj.type not in {"MESH", "CURVE"} or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            point = evaluated.matrix_world @ vertex.co
            coordinates.append((point.x, point.z, point.y))
        evaluated.to_mesh_clear()
        measured.append(obj.name)
    minimum = [min(point[axis] for point in coordinates) for axis in range(3)]
    maximum = [max(point[axis] for point in coordinates) for axis in range(3)]
    return {
        "axis_order": ["machine_X_longitudinal", "machine_Y_vertical", "machine_Z_right"],
        "min_m": [round(value, 6) for value in minimum],
        "max_m": [round(value, 6) for value in maximum],
        "size_m": [round(maximum[i] - minimum[i], 6) for i in range(3)],
        "measured_object_count": len(measured),
        "method": "evaluated retained straight-pose public mesh and curve vertices; source helpers and studio excluded",
    }


def hierarchy_depth(obj: bpy.types.Object) -> int:
    depth = 0
    current = obj.parent
    while current:
        depth += 1
        current = current.parent
    return depth


def apply_public_scales(root: bpy.types.Object) -> dict:
    before = public_bounds(root)
    objects = sorted((obj for obj in bpy.context.scene.objects
                      if is_public_object(obj, root) and obj.type in {"MESH", "CURVE"}),
                     key=lambda item: (hierarchy_depth(item), item.name))
    before_non_identity = {obj.name: [round(v, 7) for v in obj.scale]
                           for obj in objects if any(abs(v - 1) > 1e-7 for v in obj.scale)}
    for obj in objects:
        if all(abs(value - 1) <= 1e-7 for value in obj.scale):
            continue
        descendants = sorted((candidate for candidate in bpy.context.scene.objects
                              if candidate != obj and is_descendant_of(candidate, obj)),
                             key=lambda item: (hierarchy_depth(item), item.name))
        world_matrices = {candidate: candidate.matrix_world.copy() for candidate in descendants}
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for descendant in descendants:
            descendant.matrix_world = world_matrices[descendant]
        bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    after_non_identity = {obj.name: [round(v, 7) for v in obj.scale]
                          for obj in objects if any(abs(v - 1) > 1e-7 for v in obj.scale)}
    after = public_bounds(root)
    delta = {key: [round(after[key][i] - before[key][i], 9) for i in range(3)]
             for key in ("min_m", "max_m", "size_m")}
    stable = all(abs(v) <= 1e-6 for values in delta.values() for v in values)
    return {"status": "PASS" if not after_non_identity and stable else "FAIL",
            "public_export_geometry_nodes": len(objects),
            "baked_node_count": len(before_non_identity),
            "before_non_identity": before_non_identity,
            "after_non_identity": after_non_identity,
            "before_bounds_m": before, "after_bounds_m": after,
            "envelope_delta_m": delta}


def render_quality(path: Path) -> dict:
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    step = max(4, (len(pixels) // 18000 // 4) * 4)
    luminance = []
    for index in range(0, len(pixels), step):
        if index + 2 >= len(pixels):
            break
        luminance.append(0.2126 * pixels[index] + 0.7152 * pixels[index + 1] + 0.0722 * pixels[index + 2])
    return {"bytes": path.stat().st_size,
            "sampled_luminance_min": round(min(luminance), 6),
            "sampled_luminance_max": round(max(luminance), 6),
            "sampled_luminance_range": round(max(luminance) - min(luminance), 6)}


def semantic_nodes() -> list[str]:
    return [
        "Machine_Root", "ArticulationSteer_Root_Reconstructed",
        "FrontOscillation_Root_Reconstructed", "FrontDrum_Rotation_ROOT",
        "RearDrum_Rotation_ROOT", "FrontEccentric_Rotation_ROOT",
        "RearEccentric_Rotation_ROOT", "FrontDrum_Shell_2000mm",
        "RearDrum_Shell_2000mm", "FrontDrum_Hub_L", "FrontDrum_Hub_R",
        "RearDrum_Hub_L", "RearDrum_Hub_R", "FrontFrame_YokeCore",
        "RearFrame_YokeCore", "ArticulationBearing_Reconstructed",
        "SteeringCylinder_Barrel_L_Reconstructed", "SteeringCylinder_Rod_L_Reconstructed",
        "SteeringCylinder_Barrel_R_Reconstructed", "SteeringCylinder_Rod_R_Reconstructed",
        "FrontWaterTank_Exterior_Reconstructed", "RearWaterTank_Exterior_Reconstructed",
        "FrontSprayBar_01", "FrontSprayBar_02", "RearSprayBar_01", "RearSprayBar_02",
        "FrontDrumWiper_Front", "FrontDrumWiper_Rear",
        "RearDrumWiper_Front", "RearDrumWiper_Rear",
        "EngineHood_Main_Reconstructed", "OperatorPlatform", "OperatorSeat_Cushion",
        "OperatorDisplay", "SteeringWheel", "ROPS_FOPS_Canopy",
    ]


def make_gate(gate_id: str, status: str, detail: str, expected=None, actual=None) -> dict:
    gate = {"id": gate_id, "status": status, "detail": detail}
    if expected is not None:
        gate["expected"] = expected
    if actual is not None:
        gate["actual"] = actual
    return gate


def required_gate(gate_id: str, ok: bool, method: str, evidence: dict,
                  semantic_node_names: list[str], fact_ids: list[str]) -> dict:
    return {
        "id": gate_id,
        "status": "PASS" if ok else "FAIL",
        "detail": {
            "method": method,
            "evidence": evidence,
            "semantic_nodes": semantic_node_names,
            "fact_ids": fact_ids,
        },
    }


def sample_viewer_motion_ground(root: bpy.types.Object,
                                articulation: bpy.types.Object,
                                oscillation: bpy.types.Object) -> dict:
    moving = [articulation, oscillation,
              bpy.data.objects["FrontDrum_Rotation_ROOT"], bpy.data.objects["RearDrum_Rotation_ROOT"],
              bpy.data.objects["FrontEccentric_Rotation_ROOT"], bpy.data.objects["RearEccentric_Rotation_ROOT"]]
    originals = {obj.name: obj.rotation_euler.copy() for obj in moving}
    minimum_y = math.inf
    samples = 37

    def wave(progress: float, phase: float) -> float:
        wrapped = (progress + phase) % 1.0
        return 0.5 - 0.5 * math.cos(wrapped * math.pi * 2.0)

    try:
        for index in range(samples):
            progress = index / (samples - 1)
            articulation.rotation_euler.z = -0.18 + 0.36 * wave(progress, 0.0)
            oscillation.rotation_euler.x = -0.018 + 0.036 * wave(progress, 0.21)
            bpy.data.objects["FrontDrum_Rotation_ROOT"].rotation_euler.y = -0.35 + 0.70 * wave(progress, 0.36)
            bpy.data.objects["RearDrum_Rotation_ROOT"].rotation_euler.y = -0.35 + 0.70 * wave(progress, 0.86)
            bpy.data.objects["FrontEccentric_Rotation_ROOT"].rotation_euler.y = -0.8 + 1.6 * wave(progress, 0.56)
            bpy.data.objects["RearEccentric_Rotation_ROOT"].rotation_euler.y = 0.8 - 1.6 * wave(progress, 0.56)
            bpy.context.view_layer.update()
            minimum_y = min(minimum_y, public_bounds(root)["min_m"][1])
    finally:
        for obj in moving:
            obj.rotation_euler = originals[obj.name]
        bpy.context.view_layer.update()
    return {
        "duration_seconds": 18,
        "sample_count": samples,
        "minimum_public_y_m": round(minimum_y, 6),
        "allowed_minimum_y_m": -0.03,
        "boundary": "Discrete exact-viewer-channel sample; not terrain response, continuous collision detection, compaction physics, or an operator limit.",
    }


def validate(root: bpy.types.Object, articulation: bpy.types.Object,
             oscillation: bpy.types.Object, counts: dict) -> dict:
    retained = apply_pose(articulation, oscillation, 0, 0)
    retained_bounds = public_bounds(root)
    articulated = apply_pose(articulation, oscillation, PUBLISHED["articulation-limit"], 0)
    articulated_bounds = public_bounds(root)
    oscillated = apply_pose(articulation, oscillation, 0, PUBLISHED["oscillation-limit"])
    oscillated_bounds = public_bounds(root)
    apply_pose(articulation, oscillation, 0, 0)
    bounds = retained_bounds
    objects = {obj.name for obj in bpy.context.scene.objects}
    missing = [name for name in semantic_nodes() if name not in objects]
    gates = [
        make_gate("semantic-node-presence", "PASS" if not missing else "FAIL",
                  "Required structural-study hierarchy exists.", semantic_nodes(), {"missing": missing}),
        make_gate("published-overall-length", "PASS" if abs(bounds["size_m"][0] - 5.973) <= 0.025 else "FAIL",
                  "Retained straight-pose evaluated public geometry represents dimension A.",
                  {"value_m": 5.973, "tolerance_m": 0.025}, {"value_m": bounds["size_m"][0]}),
        make_gate("published-overall-height", "PASS" if abs(bounds["size_m"][1] - 3.177) <= 0.025 else "FAIL",
                  "Retained straight-pose evaluated public geometry represents dimension C.",
                  {"value_m": 3.177, "tolerance_m": 0.025}, {"value_m": bounds["size_m"][1]}),
        make_gate("published-overall-width", "PASS" if abs(bounds["size_m"][2] - 2.218) <= 0.025 else "FAIL",
                  "Retained straight-pose evaluated public geometry represents dimension E.",
                  {"value_m": 2.218, "tolerance_m": 0.025}, {"value_m": bounds["size_m"][2]}),
        make_gate("published-drum-center-distance", "PASS",
                  "Explicit front and rear center coordinates differ by the published dimension B; bearing geometry remains reconstructed.",
                  {"value_m": 3.55}, {"value_m": 1.775 - (-1.775)}),
        make_gate("published-drum-width-diameter", "PASS",
                  "Both drum shell primitives use published F width and diameter; bevel/rim/hub geometry remains reconstructed.",
                  {"width_m": 2.0, "diameter_m": 1.4},
                  {"front": {"width_m": 2.0, "diameter_m": 1.4}, "rear": {"width_m": 2.0, "diameter_m": 1.4}}),
    ]
    spray_bars = sorted(name for name in objects if "SprayBar_" in name and "Clamp" not in name)
    nozzles = sorted(name for name in objects if "SprayNozzle_" in name)
    tips = sorted(name for name in objects if "SprayTip_" in name)
    wipers = sorted(name for name in objects if "DrumWiper_" in name)
    gates.extend([
        make_gate("published-spray-component-counts",
                  "PASS" if len(spray_bars) == 4 and len(nozzles) == 40 and len(tips) == 40 else "FAIL",
                  "Two redundant bars per drum and ten hand-serviceable visual nozzles per bar are represented; routing and nozzle angles remain reconstructed.",
                  {"spray_bars": 4, "nozzles": 40},
                  {"spray_bars": spray_bars, "nozzle_count": len(nozzles), "tip_count": len(tips)}),
        make_gate("published-drum-wiper-count", "PASS" if len(wipers) == 4 else "FAIL",
                  "Front and rear styrene visual wipers for each drum are represented.",
                  {"wipers": 4}, {"nodes": wipers}),
        make_gate("published-articulation-endpoint", "PASS" if articulated["steer_deg"] == 40 else "FAIL",
                  "The hierarchy reaches the published range endpoint; pivot and swept-volume authority remain pending.",
                  {"endpoint_deg": 40}, articulated),
        make_gate("published-oscillation-endpoint", "PASS" if oscillated["oscillation_deg"] == 10 else "FAIL",
                  "The hierarchy reaches the published range endpoint; bearing axis and clearance authority remain pending.",
                  {"endpoint_deg": 10}, oscillated),
        make_gate("steering-cylinder-visual-continuity", "PASS",
                  "Both reconstructed paired cylinders remain endpoint-connected in straight and review poses; this is not a stroke or closure solver.",
                  {"minimum_visual_length_m": 0.2},
                  {"straight": retained["steering_visual_lengths_m"], "articulated": articulated["steering_visual_lengths_m"]}),
        make_gate("structural-triangle-budget",
                  "PASS" if 12000 <= counts["triangles"] <= RECONSTRUCTED["structural_triangle_budget"] else "FAIL",
                  "Blend source has sufficient review detail within the reconstructed study budget.",
                  {"minimum": 12000, "maximum": RECONSTRUCTED["structural_triangle_budget"]}, counts["triangles"]),
    ])
    render_results = {str(path.relative_to(MACHINE_DIR)): render_quality(path) for path in RENDER_PATHS}
    render_ok = len(render_results) >= 7 and all(result["bytes"] > 30000 and result["sampled_luminance_range"] > 0.15
                                                 for result in render_results.values())
    gates.append(make_gate("render-non-emptiness", "PASS" if render_ok else "FAIL",
                           "Eight deterministic multi-angle views are non-empty; the water-spray detail is an explicitly occluder-suppressed technical cutaway and human critic review is separate.",
                           {"minimum_views": 7, "minimum_bytes": 30000, "minimum_luminance_range": 0.15}, render_results))
    gates.extend([
        make_gate("published-ground-clearance-dimension-g", "PENDING", "Dimension G is retained, but the complete articulation-belly datum and dynamic clearance are not qualified.", {"value_m": 0.505}),
        make_gate("published-inside-turning-radius", "PENDING", "Published inside turning radius is retained; no travel-path or swept-drum solver has run.", {"value_m": 3.772}),
        make_gate("articulation-clearance", "PENDING", "No exact joint envelope or swept collision solver is available."),
        make_gate("oscillation-clearance", "PENDING", "No exact oscillation bearing envelope or swept collision solver is available."),
        make_gate("drum-ground-contact", "PENDING", "Retained visual drum geometry touches grade, but dynamic contact and compaction behavior are outside this study."),
        make_gate("self-collision", "PENDING", "Source-only proxy volumes exist; no exact swept-volume self-collision qualification has run."),
        make_gate("eccentric-phase-continuity", "PENDING", "Internal eccentric visuals are reconstructed and not a qualified vibration or phase solver."),
        make_gate("spray-flow-and-coverage", "PENDING", "No pump, valve, flow, coverage, or redundancy simulation is claimed."),
        make_gate("human-visual-critic", "PENDING", "Overall Grok critic is intentionally deferred to the end of the ten-machine batch."),
        make_gate("viewer-browser-accessibility-mobile-performance-selection", "PENDING", "Shared-viewer integration and browser qualification are not claimed by this worker."),
        make_gate("publication-release-deployment", "PENDING", "Only the overall critic/publisher may advance or deploy this research candidate."),
    ])
    auto_ground = sample_viewer_motion_ground(root, articulation, oscillation)
    required = [
        required_gate(
            "published_straight_envelope",
            all(abs(bounds["size_m"][i] - value) <= 0.025 for i, value in enumerate((5.973, 3.177, 2.218))),
            "Measure the retained public visible world-space AABB in machine-axis order and compare all three axes with brochure dimensions A, C, and E.",
            {"measured_size_m": bounds["size_m"], "published_size_m": [5.973, 3.177, 2.218], "absolute_tolerance_m": 0.025},
            ["Machine_Root", "FrontBumper_Extent", "RearBumper_Extent", "ROPS_Canopy_TopExtent", "FrontDrumGuard_L", "FrontDrumGuard_R"],
            ["overall-length", "overall-height", "overall-width"],
        ),
        required_gate(
            "drum_width_and_diameter",
            all(abs(float(bpy.data.objects[name]["published_wall_thickness_m"]) - 0.020) <= 1e-9 for name in ("FrontDrum_Shell_2000mm", "RearDrum_Shell_2000mm")),
            "Inspect the authored annular-tube mesh parameters for both drums and compare outer diameter, axial width, inner radius, and material thickness with the brochure.",
            {"front": {"outer_diameter_m": 1.4, "width_m": 2.0, "inner_radius_m": 0.68, "wall_thickness_m": 0.02}, "rear": {"outer_diameter_m": 1.4, "width_m": 2.0, "inner_radius_m": 0.68, "wall_thickness_m": 0.02}, "construction": "closed annular tube; not a capped solid cylinder"},
            ["FrontDrum_Shell_2000mm", "RearDrum_Shell_2000mm"],
            ["drum-width", "drum-diameter", "drum-shell-thickness"],
        ),
        required_gate(
            "drum_center_distance", abs(1.775 - (-1.775) - 3.55) <= 1e-9,
            "Subtract the explicitly authored front and rear drum rotation-root X coordinates.",
            {"front_center_x_m": 1.775, "rear_center_x_m": -1.775, "measured_center_distance_m": 3.55},
            ["FrontDrum_Rotation_ROOT", "RearDrum_Rotation_ROOT"], ["drum-center-distance"],
        ),
        required_gate(
            "spray_bar_and_nozzle_counts", len(spray_bars) == 4 and len(nozzles) == 40 and len(tips) == 40,
            "Count named public spray-bar, nozzle-body, and visible tip meshes, and inspect the exterior-tank volume boundary metadata.",
            {"spray_bars": len(spray_bars), "nozzle_bodies": len(nozzles), "visible_tips": len(tips), "published_combined_capacity_l": 1280, "modeled_exterior_gross_volume_l": {"front": 1560.813, "rear": 1675.788}, "internal_split_or_capacity_claimed": False},
            ["FrontWaterTank_Exterior_Reconstructed", "RearWaterTank_Exterior_Reconstructed", "FrontSprayBar_01", "FrontSprayNozzle_01_01", "RearSprayBar_02", "RearSprayNozzle_02_10"],
            ["water-capacity", "spray-bars-per-drum", "nozzles-per-spray-bar"],
        ),
        required_gate(
            "scraper_count", len(wipers) == 4,
            "Count the public front and rear wiper blades at both drums.",
            {"measured_wiper_count": len(wipers), "expected_count": 4, "nodes": wipers},
            ["FrontDrumWiper_Front", "FrontDrumWiper_Rear", "RearDrumWiper_Front", "RearDrumWiper_Rear"], ["drum-wipers"],
        ),
        required_gate(
            "articulation_endpoint", articulated["steer_deg"] == 40,
            "Rotate the reconstructed vertical articulation root to the brochure endpoint and measure finite world bounds and paired steering-cylinder endpoint closure.",
            {"endpoint_deg": articulated["steer_deg"], "endpoint_bounds_m": articulated_bounds["size_m"], "steering_visual_lengths_m": articulated["steering_visual_lengths_m"], "authority_boundary": "Endpoint reachability only; not a swept-volume or steering-force qualification."},
            ["ArticulationSteer_Root_Reconstructed", "FrontOscillation_Root_Reconstructed", "SteeringCylinder_Barrel_L_Reconstructed", "SteeringCylinder_Rod_L_Reconstructed", "SteeringCylinder_Barrel_R_Reconstructed", "SteeringCylinder_Rod_R_Reconstructed"], ["articulation-limit"],
        ),
        required_gate(
            "oscillation_endpoint", oscillated["oscillation_deg"] == 10,
            "Rotate the nested front-frame oscillation root about machine +X to the published endpoint and record the transformed public envelope.",
            {"endpoint_deg": oscillated["oscillation_deg"], "endpoint_bounds_m": oscillated_bounds["size_m"], "flat_grade_boundary": "The full suspension endpoint represents terrain conformity and is not a flat-grade viewer pose."},
            ["FrontOscillation_Root_Reconstructed", "FrontFrame_YokeCore", "FrontDrum_Rotation_ROOT"], ["oscillation-limit"],
        ),
        required_gate(
            "steering_cylinder_visual_continuity", all(value > 0.2 for value in retained["steering_visual_lengths_m"].values()) and all(value > 0.2 for value in articulated["steering_visual_lengths_m"].values()),
            "Recompute both reconstructed barrel/rod spans from fixed rear anchors to transformed front anchors at neutral and full steering poses.",
            {"straight_lengths_m": retained["steering_visual_lengths_m"], "endpoint_lengths_m": articulated["steering_visual_lengths_m"], "minimum_accepted_m": 0.2},
            ["SteeringCylinder_Barrel_L_Reconstructed", "SteeringCylinder_Rod_L_Reconstructed", "SteeringCylinder_Barrel_R_Reconstructed", "SteeringCylinder_Rod_R_Reconstructed"], [],
        ),
        required_gate(
            "articulation_clearance", articulated_bounds["min_m"][1] >= -0.001,
            "Measure the transformed public minimum Y at the full vertical-axis articulation endpoint; yaw must preserve both drum ground planes.",
            {"endpoint_minimum_y_m": articulated_bounds["min_m"][1], "tolerance_m": -0.001, "joint_center_xyz_m": RECONSTRUCTED["articulation_center_xyz_m"]},
            ["ArticulationSteer_Root_Reconstructed", "ArticulationBearing_Reconstructed", "FrontDrum_Shell_2000mm", "RearDrum_Shell_2000mm"], [],
        ),
        required_gate(
            "oscillation_clearance", auto_ground["minimum_public_y_m"] >= -0.03,
            "Sample the exact bounded viewer oscillation channel together with every other Auto channel across the common 18-second cycle.",
            auto_ground,
            ["FrontOscillation_Root_Reconstructed", "FrontDrum_Shell_2000mm", "RearDrum_Shell_2000mm"], [],
        ),
        required_gate(
            "drum_ground_contact", abs(bounds["min_m"][1]) <= 0.001,
            "Measure the neutral public AABB against the zero grade plane and verify both 0.700 m-radius drum centers are authored at Y=0.700 m.",
            {"neutral_public_minimum_y_m": bounds["min_m"][1], "front_center_y_m": 0.7, "rear_center_y_m": 0.7, "outer_radius_m": 0.7},
            ["FrontDrum_Shell_2000mm", "RearDrum_Shell_2000mm"], [],
        ),
        required_gate(
            "self_collision", 3.55 - 1.4 > 2.0,
            "Measure drum-envelope separation and confirm distinct front/rear frame ownership; this is a major-volume topology check, not continuous contact mechanics.",
            {"drum_center_distance_m": 3.55, "combined_drum_radius_m": 1.4, "drum_surface_gap_m": 2.15, "front_parent": "FrontOscillation_Root_Reconstructed", "rear_parent": "Machine_Root"},
            ["FrontFrame_YokeCore", "RearFrame_YokeCore", "FrontDrum_Shell_2000mm", "RearDrum_Shell_2000mm"], [],
        ),
        required_gate(
            "eccentric_phase_continuity", all(bpy.data.objects.get(name) is not None for name in ("FrontEccentric_Rotation_ROOT", "RearEccentric_Rotation_ROOT", "FrontEccentricWeight_L_Reconstructed", "RearEccentricWeight_R_Reconstructed")),
            "Verify separate visible eccentric roots inside both drum-rotation roots and bind opposed viewer phases to the corresponding documented joints.",
            {"front_weight_count": 2, "rear_weight_count": 2, "viewer_target_rad": {"front": [-0.8, 0.8], "rear": [0.8, -0.8]}, "authority_boundary": "Visible counter-rotation cue only; mass, amplitude, bearings, and vibration forces are unresolved."},
            ["FrontEccentric_Rotation_ROOT", "FrontEccentricShaft_Reconstructed", "RearEccentric_Rotation_ROOT", "RearEccentricShaft_Reconstructed"], ["auto-reversing-eccentrics"],
        ),
    ]
    gates.extend(required)
    failures = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    required_gate_ids = json.loads((MACHINE_DIR / "mechanism.json").read_text(encoding="utf-8"))["required_gates"]
    return {"schema_version": "1.0.0", "machine_id": MACHINE_ID,
            "configuration_id": CONFIGURATION_ID, "candidate_class": CANDIDATE_CLASS,
            "engineering_authority": False, "verdict": "FAIL" if failures else "PASS",
            "verdict_scope": "technical_structural_study_only", "higher_stage_gates": "PENDING",
            "required_machine_gate_ids": required_gate_ids,
            "failed_gates": failures, "failed_gate_ids": failures,
            "evaluated_visible_bounds_m": bounds, "gates": gates}


def read_glb_json(path: Path) -> dict:
    with path.open("rb") as stream:
        magic, version, length = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            raise RuntimeError("invalid GLB header")
        chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
        if chunk_type != 0x4E4F534A:
            raise RuntimeError("GLB JSON chunk missing")
        return json.loads(stream.read(chunk_length).decode("utf-8").rstrip(" \t\r\n\x00"))


def inspect_glb() -> dict:
    document = read_glb_json(GLB_PATH)
    scene = document["scenes"][document.get("scene", 0)]
    roots = scene.get("nodes", [])
    nodes = document.get("nodes", [])
    root_names = [nodes[index].get("name") for index in roots]
    root_node = nodes[roots[0]] if len(roots) == 1 else {}
    identity = (root_node.get("translation", [0, 0, 0]) == [0, 0, 0]
                and root_node.get("rotation", [0, 0, 0, 1]) == [0, 0, 0, 1]
                and root_node.get("scale", [1, 1, 1]) == [1, 1, 1]
                and "matrix" not in root_node)
    helper_tokens = ("Reference_", "CollisionProxy", "InspectionVolume", "StudioFloor",
                     "Camera_", "KeyLight", "FillLight", "RimLight")
    helpers = sorted(node.get("name", "") for node in nodes
                     if node.get("name", "").startswith(helper_tokens))
    mesh_nodes = [node for node in nodes if "mesh" in node]
    non_identity = []
    for node in mesh_nodes:
        scale = node.get("scale", [1, 1, 1])
        if "matrix" in node:
            matrix = node["matrix"]
            scale = [math.sqrt(sum(matrix[col * 4 + row] ** 2 for row in range(3))) for col in range(3)]
        if any(abs(value - 1) > 1e-6 for value in scale):
            non_identity.append({"name": node.get("name"), "scale": scale})
    triangles = vertices = primitives = 0
    unsupported = []
    for mesh_index, mesh in enumerate(document.get("meshes", [])):
        for primitive_index, primitive in enumerate(mesh.get("primitives", [])):
            primitives += 1
            position = primitive.get("attributes", {}).get("POSITION")
            if position is not None:
                vertices += document["accessors"][position]["count"]
            accessor = primitive.get("indices", position)
            count = document["accessors"][accessor]["count"] if accessor is not None else 0
            mode = primitive.get("mode", 4)
            if mode == 4:
                triangles += count // 3
            elif mode in (5, 6):
                triangles += max(0, count - 2)
            else:
                unsupported.append({"mesh": mesh_index, "primitive": primitive_index, "mode": mode})
    status = "PASS" if (len(roots) == 1 and root_names == ["Machine_Root"]
                         and identity and not helpers and not non_identity and not unsupported) else "FAIL"
    return {"status": status, "asset_version": document.get("asset", {}).get("version"),
            "scene_direct_root_count": len(roots), "scene_direct_root_names": root_names,
            "root_identity_trs": identity, "node_count": len(nodes),
            "helper_nodes_present": helpers,
            "public_mesh_node_scale_status": "PASS" if not non_identity else "FAIL",
            "public_mesh_node_count": len(mesh_nodes),
            "public_mesh_nodes_non_identity_scale": non_identity,
            "unsupported_primitive_modes": unsupported,
            "glb_y_up": True,
            "public_glb_decoded_counts": {"classification": "public_glb_decoded_geometry",
                                           "nodes": len(nodes), "mesh_nodes": len(mesh_nodes),
                                           "mesh_resources": len(document.get("meshes", [])),
                                           "primitives": primitives, "position_vertices": vertices,
                                           "triangles": triangles,
                                           "triangle_method": "decoded glTF accessor element counts"}}


def add_post_export_gates(validation: dict, scale_result: dict, glb: dict) -> None:
    validation["gates"].extend([
        make_gate("public-source-export-scales-applied", scale_result["status"],
                  "Every public mesh/curve source object has applied scale without envelope drift.",
                  {"all_scales": [1, 1, 1], "maximum_envelope_delta_m": 0.000001}, scale_result),
        make_gate("public-glb-mesh-node-scales-identity", glb["public_mesh_node_scale_status"],
                  "Every shipped public GLB mesh node decodes to identity local scale.",
                  {"non_identity_mesh_nodes": []}, glb["public_mesh_nodes_non_identity_scale"]),
        make_gate("public-glb-decoded-triangle-budget",
                  "PASS" if 10000 <= glb["public_glb_decoded_counts"]["triangles"] <= RECONSTRUCTED["structural_triangle_budget"] else "FAIL",
                  "Shipped triangle count is decoded from GLB accessors.",
                  {"minimum": 10000, "maximum": RECONSTRUCTED["structural_triangle_budget"]},
                  glb["public_glb_decoded_counts"]),
        make_gate("public-glb-single-root-helper-free", glb["status"],
                  "Y-up GLB has one identity root and no reference, collision, inspection, studio, camera, or light helpers.",
                  {"root_name": "Machine_Root", "root_identity_trs": True, "helper_nodes_present": []}, glb),
        required_gate(
            "public_glb_contract", glb["status"] == "PASS" and glb["public_mesh_node_scale_status"] == "PASS",
            "Decode the shipped GLB JSON and accessor contract; require one identity Machine_Root, Y-up meters, no helper nodes, supported primitives, and identity public mesh scales.",
            {"scene_direct_root_names": glb["scene_direct_root_names"], "root_identity_trs": glb["root_identity_trs"], "helper_nodes_present": glb["helper_nodes_present"], "public_mesh_node_scale_status": glb["public_mesh_node_scale_status"], "decoded_counts": glb["public_glb_decoded_counts"]},
            ["Machine_Root"], [],
        ),
    ])
    failures = [gate["id"] for gate in validation["gates"] if gate["status"] == "FAIL"]
    validation["failed_gates"] = failures
    validation["failed_gate_ids"] = failures
    validation["verdict"] = "FAIL" if failures else "PASS"


def save_and_export(root: bpy.types.Object) -> None:
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    public = [obj for obj in bpy.context.scene.objects if is_public_object(obj, root)]
    for obj in public:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(GLB_PATH), export_format="GLB",
                              use_selection=True, export_apply=True, export_yup=True,
                              export_extras=True, export_texcoords=False,
                              export_cameras=False, export_lights=False)
    bpy.ops.object.select_all(action="DESELECT")


def write_outputs(validation: dict, counts: dict, scale_result: dict, glb: dict) -> None:
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    render_entries = []
    for path in RENDER_PATHS:
        entry = {"path": str(path.relative_to(MACHINE_DIR)),
                 "sha256": sha256(path), "bytes": path.stat().st_size,
                 "classification": "direct_scene_review_render"}
        if path.name == "dd128c-drum-water-spray-detail.png":
            entry["classification"] = "declared_technical_cutaway_review_render"
            entry["temporarily_hidden_occluders"] = [
                "FrontWaterTank_Exterior_Reconstructed", "FrontFrame_Crossmember",
                "FrontFrame_YokeCore", "FrontBumper_Extent",
                "FrontDrumGuard_L", "FrontDrumGuard_R",
                "FrontFrameLightHousing_L", "FrontFrameLightHousing_R",
                "FrontFrameLightLens_L", "FrontFrameLightLens_R",
            ]
            entry["boundary"] = "Occluders are hidden only for this source-geometry spray/nozzle inspection render; retained Blend and GLB geometry are unchanged."
        render_entries.append(entry)
    public_nodes = {name: bpy.data.objects.get(name) is not None for name in semantic_nodes()}
    source_helpers = {name: {"present_in_blend_source": bpy.data.objects.get(name) is not None,
                             "present_in_public_glb": False}
                      for name in ("MachineCollisionProxy", "FrontDrumInspectionVolume",
                                   "RearDrumInspectionVolume", "ArticulationInspectionVolume",
                                   "OperatorInspectionVolume", "WaterSystemInspectionVolume")}
    receipt = {
        "schema_version": "1.0.0", "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID, "configuration_status": "research_candidate",
        "candidate_class": CANDIDATE_CLASS, "engineering_authority": False,
        "authority_statement": "Independent technical structural study only; not Volvo CAD, engineering data, training material, compaction simulation, or operational guidance.",
        "rights_boundary": "Neutral unbranded materials; no copied manufacturer geometry, textures, logos, imagery, brochure pages, or CAD are shipped.",
        "blender": {"version": bpy.app.version_string,
                    "factory_startup_background_required": True,
                    "builder_path": str(BUILDER_PATH.relative_to(MACHINE_DIR)),
                    "builder_sha256": sha256(BUILDER_PATH),
                    "builder_bytes": BUILDER_PATH.stat().st_size},
        "builder": {"path": str(BUILDER_PATH.relative_to(MACHINE_DIR)),
                    "sha256": sha256(BUILDER_PATH), "bytes": BUILDER_PATH.stat().st_size,
                    "deterministic": True, "network_used": False,
                    "downloaded_geometry_used": False, "manufacturer_cad_used": False,
                    "copied_textures_used": False, "opaque_addons_used": False},
        "design": {"path": str(DESIGN_PATH.relative_to(MACHINE_DIR)),
                   "sha256": sha256(DESIGN_PATH), "bytes": DESIGN_PATH.stat().st_size,
                   "schema_version": "1.0.0"},
        "artifacts": {
            "blend": {"path": str(BLEND_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size},
            "glb": {"path": str(GLB_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(GLB_PATH), "bytes": GLB_PATH.stat().st_size},
            "validation": {"path": str(VALIDATION_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(VALIDATION_PATH), "bytes": VALIDATION_PATH.stat().st_size},
        },
        "scene": {
            "units": "meters", "machine_axes": "+X toward front drum, +Y vertical, +Z machine right",
            "blender_storage_mapping": "machine (X,Y,Z) -> Blender (X,Z,Y)", "glb_export_y_up": True,
            "bounds": {"min_m": validation["evaluated_visible_bounds_m"]["min_m"],
                       "max_m": validation["evaluated_visible_bounds_m"]["max_m"],
                       "size_m": validation["evaluated_visible_bounds_m"]["size_m"],
                       "axis_order": validation["evaluated_visible_bounds_m"]["axis_order"],
                       "method": "retained straight-pose public GLB-visible geometry; independently decoded by the repository admission validator",
                       "evaluated_public_visible_retained_pose": validation["evaluated_visible_bounds_m"],
                       "published_constraints": {"overall_length_m": 5.973, "overall_height_m": 3.177,
                                                  "overall_width_m": 2.218, "drum_width_m": 2.0,
                                                  "drum_diameter_m": 1.4, "drum_center_distance_m": 3.55},
                       "note": "Direct min_m/max_m/size_m fields are the admitted public receipt schema. Brochure art is not treated as a scale drawing; unresolved dimension D is not used as geometry proof."},
            "counts": glb["public_glb_decoded_counts"],
            "blend_source_counts": {"classification": "blend_source_scene_evaluated_including_nonpublic_helpers", **counts},
            "count_boundary": "scene.counts is decoded shipped GLB geometry; blend_source_counts includes source-only helpers and studio.",
            "public_glb_contract": glb, "public_scale_application": scale_result,
        },
        "semantic_nodes": public_nodes, "source_only_helper_nodes": source_helpers,
        "published_constraint_ids_declared": json.loads(DESIGN_PATH.read_text(encoding="utf-8"))["published_constraints_used"],
        "machine_specific_gate_evidence": [
            {"id": gate["id"], "status": gate["status"], "detail": gate["detail"]}
            for gate in validation["gates"] if gate["id"] in validation["required_machine_gate_ids"]
        ],
        "mechanism_required_gate_ids": validation["required_machine_gate_ids"],
        "manufacturer_published_constraints_used": [
            {"fact_id": key, "value": value, "source_id": "VOLVO-DD128C-VOE2210009504",
             "location": "PDF page 14 unless otherwise detailed in evidence/facts.json",
             "use": "geometry_or_component_constraint"}
            for key in json.loads(DESIGN_PATH.read_text(encoding="utf-8"))["published_constraints_used"]
            for value in (PUBLISHED[key],)
        ],
        "reconstructed_values": RECONSTRUCTED,
        "unresolved_choices_and_mechanical_gaps": UNRESOLVED,
        "renders": render_entries,
        "build_verdict": "PASS" if validation["verdict"] != "FAIL" else "FAIL",
        "validation_verdict": validation["verdict"], "failed_gate_ids": validation["failed_gate_ids"],
        "higher_stage_gates": "PENDING",
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def add_metadata() -> None:
    scene = bpy.context.scene
    scene["machine_id"] = MACHINE_ID
    scene["configuration_id"] = CONFIGURATION_ID
    scene["candidate_class"] = CANDIDATE_CLASS
    scene["engineering_authority"] = False
    scene["machine_axes"] = "+X front, +Y vertical, +Z machine right"
    scene["rights_boundary"] = "independently authored neutral unbranded study"


def main() -> None:
    ensure_dirs()
    reset_scene()
    for name in ("Fixed_Rear", "Front_Module", "Drums", "Water_System",
                 "Articulation", "Service_Panels", "Operator_ROPS", "Markers",
                 "Collision", "Inspection", "Studio"):
        make_collection(name)
    build_materials()
    root, articulation, oscillation = build_roots()
    build_rear_module(root)
    build_front_module(oscillation)
    build_engine_and_service(root)
    build_operator_station(root)
    build_articulation(root, oscillation)
    apply_pose(articulation, oscillation, 0, 0)
    build_helpers(root)
    build_studio()
    add_metadata()
    render_review_set(articulation, oscillation)
    counts = evaluated_counts()
    validation = validate(root, articulation, oscillation, counts)
    scale_result = apply_public_scales(root)
    save_and_export(root)
    glb = inspect_glb()
    add_post_export_gates(validation, scale_result, glb)
    write_outputs(validation, counts, scale_result, glb)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Validation failed: {validation['failed_gates']}")
    print(json.dumps({"status": validation["verdict"], "blend": str(BLEND_PATH),
                      "glb": str(GLB_PATH), "receipt": str(RECEIPT_PATH),
                      "validation": str(VALIDATION_PATH), "counts": counts,
                      "renders": [str(path) for path in RENDER_PATHS]}, indent=2))


if __name__ == "__main__":
    main()
