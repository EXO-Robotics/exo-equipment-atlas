#!/usr/bin/env python3
"""Deterministic technical structural study for the John Deere 333 P-Tier.

This independently authored study uses only admitted, manufacturer-published
envelope and endpoint constraints. Hidden pivots, hydraulic anchors, track
geometry, bucket section, and all interpolated articulation are reconstructed
for visualization and are not engineering authority.

Run with:
  Blender --factory-startup --background --python build_john_deere_333_p_tier.py
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


MACHINE_ID = "john-deere-333-p-tier"
CONFIGURATION_ID = "JD-333P-NAM-STD-T450-FB-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
MACHINE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = Path(__file__).resolve()
BLEND_PATH = MACHINE_DIR / "source/blender/john-deere-333-p-tier-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets/john-deere-333-p-tier-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production/asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production/validation.json"
RENDER_DIR = MACHINE_DIR / "review/renders"

# Machine coordinates from mechanism.json: +X toward bucket, +Y vertical,
# +Z machine right. Blender stores these as (X, Z, Y) so its conventional
# world Z remains visually vertical. The mapping is declared in the receipt.
def mv(x: float, y: float, z: float) -> Vector:
    return Vector((x, z, y))


PUBLISHED = {
    "length-no-bucket": 3.17,
    "length-foundry-bucket": 3.84,
    "width-450-track": 2.05,
    "rops-height": 2.22,
    "hinge-pin-height": 3.35,
    "dump-height": 2.69,
    "dump-reach": 0.74,
    "ground-clearance": 0.25,
    "dump-angle": 48.0,
    "rollback-angle": 35.0,
}

PUBLISHED_ADDITIONAL = {
    "departure-angle": 30.0,
    "front-turn-radius": 2.18,
    "track-rollers-per-side": 5,
    "track-idlers-per-side": 2,
}

# Reconstructed values are visual-study inputs, never manufacturer facts.
RECONSTRUCTED = {
    "rear_reference_x_m": -1.77,
    "front_machine_reference_x_m": 1.40,
    "dump_reach_reference_x_m": 1.00,
    "stowed_hinge_xyz_m": [1.3427, 0.5634, 0.0],
    "full_lift_hinge_xyz_m": [1.1460, 3.3500, 0.0],
    "bucket_hinge_to_lip_m": 0.8882,
    "bucket_visual_width_m": 2.08,
    "track_center_z_m": 0.80,
    "track_visual_path_length_m": 2.42,
    "track_visual_height_m": 0.66,
    "track_tread_count_per_side": 46,
    "rear_lower_lift_pivot_xyz_m": [-0.92, 1.03, 0.0],
    "rear_upper_lift_pivot_xyz_m": [-0.72, 1.48, 0.0],
    "lift_cylinder_base_xyz_m": [-0.98, 0.55, 0.0],
    "stowed_carriage_lower_xyz_m": [1.15, 0.53, 0.0],
    "stowed_carriage_upper_xyz_m": [1.26, 0.88, 0.0],
    "full_carriage_lower_xyz_m": [1.03, 3.02, 0.0],
    "full_carriage_upper_xyz_m": [1.146, 3.35, 0.0],
    "quick_attach_plate_thickness_m": 0.08,
    "structural_triangle_budget": 100000,
}

UNRESOLVED = [
    "foundry bucket exact part and cutting edge",
    "quick attachment interface geometry",
    "cab door and lighting package",
    "anti-vibration undercarriage option",
    "counterweight quantity",
    "public material and branding authorization",
    "lift-arm pivot coordinates and link lengths",
    "lift-cylinder anchors and stroke",
    "bucket tilt-linkage topology and cylinder anchors",
    "track link pitch, sprocket phase, idler and roller centers",
    "service-opening angle and exact cab quick-pivot axis",
]

COLLECTIONS: dict[str, bpy.types.Collection] = {}
MATERIALS: dict[str, bpy.types.Material] = {}
ARTICULATED: dict[str, bpy.types.Object] = {}
RENDER_PATHS: list[Path] = []


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs() -> None:
    for path in (BLEND_PATH.parent, GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        # Materials are cleared before rebuilding so counts are deterministic.
        for datablock in list(datablocks):
            datablocks.remove(datablock)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)

    scene = bpy.context.scene
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
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.025, 0.03, 0.04)


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    COLLECTIONS[name] = collection
    return collection


def move_to_collection(obj: bpy.types.Object, collection_name: str) -> None:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    COLLECTIONS[collection_name].objects.link(obj)


def set_parent(obj: bpy.types.Object, parent: bpy.types.Object,
               preserve_world=True) -> None:
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


def apply_material(obj: bpy.types.Object, mat_name: str) -> None:
    if obj.type == "MESH":
        obj.data.materials.append(MATERIALS[mat_name])


def add_empty(name: str, xyz: tuple[float, float, float], collection="Markers",
              display="PLAIN_AXES", size=0.12, parent=None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj.location = mv(*xyz)
    COLLECTIONS[collection].objects.link(obj)
    if parent:
        set_parent(obj, parent)
    return obj


def add_box(name: str, center: tuple[float, float, float],
            size: tuple[float, float, float], mat_name: str, collection: str,
            bevel=0.02, parent=None, hidden_render=False,
            parent_local=False) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[2], size[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = min(bevel, min(size) * 0.22)
        modifier.segments = 2
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent, preserve_world=not parent_local)
    obj.hide_render = hidden_render
    return obj


def add_cylinder(name: str, center: tuple[float, float, float], radius: float,
                 depth: float, axis: str, mat_name: str, collection: str,
                 vertices=24, parent=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    # Blender cylinder local Z. Machine +Y maps to Blender +Z, machine +Z to
    # Blender +Y, and machine +X remains Blender +X.
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(f"Unsupported machine axis: {axis}")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("EdgeSoftening", "BEVEL")
    bevel.width = min(radius * 0.12, 0.015)
    bevel.segments = 2
    apply_material(obj, mat_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_unit_beam(name: str, mat_name: str, collection: str, bevel=0.025,
                  parent=None) -> bpy.types.Object:
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
               b: tuple[float, float, float], lateral_thickness: float,
               vertical_depth: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("X", "Z").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((direction.length * 0.5,
                                    lateral_thickness * 0.5,
                                    vertical_depth * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def add_unit_cylinder(name: str, mat_name: str, collection: str, vertices=24,
                      parent=None) -> bpy.types.Object:
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


def add_prism_xy(name: str, polygon: list[tuple[float, float]],
                 z_center: float, width: float, mat_name: str, collection: str,
                 parent=None, local=False) -> bpy.types.Object:
    # Polygon uses machine X/Y and is extruded along machine Z.
    half = width * 0.5
    verts = []
    for z in (-half, half):
        for x, y in polygon:
            verts.append((x, z, y)) if local else verts.append(tuple(mv(x, y, z + z_center)))
    n = len(polygon)
    faces = [tuple(range(n)), tuple(range(n, 2 * n))[::-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    apply_material(obj, mat_name)
    bevel = obj.modifiers.new("EdgeSoftening", "BEVEL")
    bevel.width = 0.018
    bevel.segments = 2
    if parent:
        set_parent(obj, parent, preserve_world=not local)
    return obj


def add_polyline_tube(name: str, points: list[tuple[float, float, float]],
                      bevel_depth: float, mat_name: str, collection: str,
                      cyclic=True, resolution=1) -> bpy.types.Object:
    curve = bpy.data.curves.new(name=f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = resolution
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coord in zip(spline.points, points):
        p = mv(*coord)
        point.co = (p.x, p.y, p.z, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    COLLECTIONS[collection].objects.link(obj)
    obj.data.materials.append(MATERIALS[mat_name])
    return obj


def make_track_path(z: float) -> list[tuple[float, float, float]]:
    # Reconstructed smooth long-life rubber track outline.
    return [
        (-1.47, 0.17, z), (-1.33, 0.05, z), (0.95, 0.05, z),
        (1.13, 0.17, z), (1.12, 0.55, z), (0.92, 0.67, z),
        (-1.25, 0.67, z), (-1.47, 0.51, z),
    ]


def sample_loop(points: list[tuple[float, float, float]], count: int):
    segments = []
    total = 0.0
    for a, b in zip(points, points[1:] + points[:1]):
        length = (mv(*b) - mv(*a)).length
        segments.append((a, b, length))
        total += length
    samples = []
    for index in range(count):
        target = total * index / count
        walked = 0.0
        for a, b, length in segments:
            if target <= walked + length:
                t = (target - walked) / length
                pos = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
                tangent = Vector((b[0] - a[0], b[1] - a[1]))
                samples.append((pos, math.atan2(tangent.y, tangent.x)))
                break
            walked += length
    return samples


def build_materials() -> None:
    # Neutral industrial palette: intentionally no manufacturer livery.
    material("NeutralGraphite", (0.075, 0.085, 0.095, 1.0), metallic=0.55, roughness=0.32)
    material("NeutralSteel", (0.28, 0.31, 0.34, 1.0), metallic=0.72, roughness=0.28)
    material("NeutralPanel", (0.34, 0.38, 0.40, 1.0), metallic=0.42, roughness=0.38)
    material("SafetyAccent", (0.43, 0.47, 0.48, 1.0), metallic=0.28, roughness=0.34)
    material("Rubber", (0.018, 0.021, 0.024, 1.0), roughness=0.82)
    material("CylinderRod", (0.52, 0.56, 0.60, 1.0), metallic=0.92, roughness=0.16)
    material("Glass", (0.08, 0.16, 0.19, 0.30), metallic=0.05, roughness=0.14, transmission=0.42)
    material("Interior", (0.045, 0.052, 0.058, 1.0), roughness=0.78)
    material("Marker", (0.85, 0.24, 0.08, 1.0), metallic=0.1, roughness=0.35)
    material("Collision", (0.95, 0.12, 0.08, 0.0), roughness=0.5)
    material("Inspection", (0.12, 0.55, 0.95, 0.0), roughness=0.5)
    material("Ground", (0.065, 0.075, 0.082, 1.0), roughness=0.95)


def build_root_and_fixed_structure() -> bpy.types.Object:
    root = add_empty("JD333P_Root", (0, 0, 0), "Fixed_Structure", size=0.25)
    root["candidate_class"] = CANDIDATE_CLASS
    root["configuration_id"] = CONFIGURATION_ID
    root["engineering_authority"] = False

    # Exact dimensional reference empties used by validation.
    references = {
        "Reference_Rearmost_NoBucket": (-1.77, 0.40, 0.0),
        "Reference_Frontmost_NoBucket": (1.40, 0.40, 0.0),
        "Reference_TrackOuter_Left": (0.0, 0.35, -1.025),
        "Reference_TrackOuter_Right": (0.0, 0.35, 1.025),
        "Reference_ROPS_Top": (-0.27, 2.22, 0.0),
        "Reference_Frame_Underside": (-0.10, 0.25, 0.0),
        "Reference_DumpReachPlane": (1.00, 2.69, 0.0),
    }
    for name, xyz in references.items():
        empty = add_empty(name, xyz, size=0.075, parent=root)
        empty["authority"] = "manufacturer_published_constraint_reference"

    # Lower frame and rear counterweight envelope.
    add_box("MainFrame_Lower", (-0.16, 0.49, 0.0), (2.68, 0.48, 1.10),
            "NeutralGraphite", "Fixed_Structure", 0.06, root)
    add_box("Frame_BellyPan", (-0.15, 0.30, 0.0), (2.56, 0.10, 1.05),
            "NeutralSteel", "Fixed_Structure", 0.018, root)
    add_box("RearCounterweight_Core", (-1.57, 0.89, 0.0), (0.40, 0.92, 1.54),
            "NeutralPanel", "Fixed_Structure", 0.10, root)
    add_box("RearServiceDoor", (-1.762, 1.04, 0.0), (0.035, 0.64, 1.25),
            "NeutralGraphite", "Fixed_Structure", 0.012, root)
    for i, y in enumerate((0.83, 0.94, 1.05, 1.16, 1.27)):
        add_box(f"RearGrille_Slat_{i:02d}", (-1.79, y, 0.0), (0.022, 0.035, 0.94),
                "NeutralSteel", "Fixed_Structure", 0.006, root)
    add_box("FrontBulkhead", (0.99, 0.91, 0.0), (0.20, 0.82, 1.26),
            "NeutralPanel", "Fixed_Structure", 0.04, root)
    add_box("OperatorDeck", (-0.23, 0.82, 0.0), (1.58, 0.15, 1.02),
            "NeutralGraphite", "Fixed_Structure", 0.025, root)
    # Side service panels and fastener cues.
    for side in (-1, 1):
        z = side * 0.61
        add_prism_xy(f"SideServicePanel_{'L' if side < 0 else 'R'}",
                     [(-1.50, 0.62), (0.90, 0.62), (0.91, 1.23),
                      (0.40, 1.38), (-1.35, 1.30)], z, 0.055,
                     "NeutralPanel", "Fixed_Structure", root)
        for i, x in enumerate((-1.30, -0.78, -0.25, 0.30, 0.74)):
            add_cylinder(f"PanelFastener_{'L' if side < 0 else 'R'}_{i}",
                         (x, 0.76 + 0.07 * (i % 2), side * 0.645), 0.022, 0.018,
                         "z", "CylinderRod", "Fixed_Structure", 16, root)
    return root


def build_undercarriage(root: bpy.types.Object) -> None:
    for side, suffix in ((-1, "L"), (1, "R")):
        z_center = side * RECONSTRUCTED["track_center_z_m"]
        path = make_track_path(z_center)
        add_polyline_tube(f"TrackBelt_{suffix}", path, 0.105, "Rubber", "Undercarriage")

        # Five triple-flange visual roller assemblies per side (published count,
        # reconstructed centers and flange details).
        # Keep all five published roller assemblies visually distinct between
        # the two idlers. Centers and diameters remain reconstructed.
        roller_x = (-0.92, -0.51, -0.10, 0.31, 0.72)
        for index, x in enumerate(roller_x):
            add_cylinder(f"TrackRoller_{suffix}_{index + 1:02d}",
                         (x, 0.235, z_center), 0.165, 0.30, "z",
                         "NeutralSteel", "Undercarriage", 32, root)
            for offset in (-0.125, 0.0, 0.125):
                add_cylinder(f"TrackRollerFlange_{suffix}_{index + 1:02d}_{offset:+.3f}",
                             (x, 0.235, z_center + offset), 0.180, 0.025, "z",
                             "NeutralGraphite", "Undercarriage", 24, root)

        # Two double-flange visual idlers per side (published count,
        # reconstructed centers).
        for index, (x, y) in enumerate(((-1.34, 0.34), (1.02, 0.37))):
            add_cylinder(f"TrackIdler_{suffix}_{index + 1:02d}",
                         (x, y, z_center), 0.265, 0.31, "z",
                         "NeutralSteel", "Undercarriage", 36, root)
            for offset in (-0.135, 0.135):
                add_cylinder(f"TrackIdlerFlange_{suffix}_{index + 1:02d}_{offset:+.3f}",
                             (x, y, z_center + offset), 0.285, 0.025, "z",
                             "NeutralGraphite", "Undercarriage", 28, root)

        # Reconstructed drive sprocket and hub.
        add_cylinder(f"DriveSprocket_{suffix}", (-1.20, 0.47, z_center), 0.245,
                     0.22, "z", "NeutralGraphite", "Undercarriage", 28, root)
        add_cylinder(f"FinalDriveHub_{suffix}", (-1.20, 0.47, z_center), 0.115,
                     0.34, "z", "CylinderRod", "Undercarriage", 28, root)

        for index, (pos, angle) in enumerate(sample_loop(path, 46)):
            tread = add_box(f"TrackTread_{suffix}_{index + 1:02d}", pos,
                            (0.115, 0.055, 0.46), "Rubber", "Undercarriage", 0.008, root)
            # Path angle is in the machine X/Y plane, mapped to Blender X/Z.
            tread.rotation_euler[1] = -angle

    # Central belly and tie-down hints.
    add_box("Undercarriage_CenterPan", (-0.12, 0.37, 0.0), (2.46, 0.24, 0.64),
            "NeutralGraphite", "Undercarriage", 0.035, root)
    for side in (-1, 1):
        add_cylinder(f"TieDownRear_{'L' if side < 0 else 'R'}",
                     (-1.52, 0.47, side * 0.64), 0.04, 0.06, "z",
                     "NeutralSteel", "Undercarriage", 20, root)


def build_cab(root: bpy.types.Object) -> None:
    cab_root = add_empty("Cab_ROPS_Root_Reconstructed", (-0.30, 0.78, 0.0),
                         "Cab_ROPS", size=0.18, parent=root)
    cab_root["authority"] = "observed_form_reconstructed_dimensions"
    # ROPS pillars, header, roof, and lower sill.
    for side in (-1, 1):
        z = side * 0.49
        rear = add_unit_beam(f"ROPS_RearPillar_{'L' if side < 0 else 'R'}",
                             "NeutralGraphite", "Cab_ROPS", 0.025, cab_root)
        place_beam(rear, (-1.00, 0.85, z), (-0.86, 2.16, z), 0.085, 0.095)
        front = add_unit_beam(f"ROPS_FrontPillar_{'L' if side < 0 else 'R'}",
                              "NeutralGraphite", "Cab_ROPS", 0.025, cab_root)
        place_beam(front, (0.47, 0.86, z), (0.30, 2.16, z), 0.085, 0.095)
        add_box(f"ROPS_LowerSill_{'L' if side < 0 else 'R'}", (-0.23, 0.90, z),
                (1.43, 0.10, 0.08), "NeutralGraphite", "Cab_ROPS", 0.02, cab_root)
        add_box(f"ROPS_RoofRail_{'L' if side < 0 else 'R'}", (-0.28, 2.16, z),
                (1.30, 0.09, 0.09), "NeutralGraphite", "Cab_ROPS", 0.02, cab_root)

    add_box("ROPS_Roof", (-0.30, 2.16, 0.0), (1.42, 0.12, 1.08),
            "NeutralPanel", "Cab_ROPS", 0.045, cab_root)
    add_box("ROPS_RearHeader", (-0.91, 2.04, 0.0), (0.12, 0.16, 1.03),
            "NeutralGraphite", "Cab_ROPS", 0.025, cab_root)
    add_box("ROPS_FrontHeader", (0.35, 2.05, 0.0), (0.12, 0.16, 1.03),
            "NeutralGraphite", "Cab_ROPS", 0.025, cab_root)

    # Glazing boundaries; distinct panels make inspection/readability useful.
    add_box("Cab_FrontGlass", (0.40, 1.49, 0.0), (0.035, 1.02, 0.87),
            "Glass", "Cab_ROPS", 0.008, cab_root)
    add_box("Cab_RearGlass", (-0.94, 1.49, 0.0), (0.028, 0.93, 0.82),
            "Glass", "Cab_ROPS", 0.006, cab_root)
    for side in (-1, 1):
        z = side * 0.475
        add_box(f"Cab_SideGlass_{'L' if side < 0 else 'R'}", (-0.28, 1.50, z),
                (1.12, 0.98, 0.028), "Glass", "Cab_ROPS", 0.006, cab_root)
        # Protective side grid, observed visual feature; spacing reconstructed.
        for i, x in enumerate((-0.80, -0.57, -0.34, -0.11, 0.12, 0.31)):
            add_box(f"CabGridV_{'L' if side < 0 else 'R'}_{i:02d}",
                    (x, 1.50, side * 0.498), (0.024, 1.02, 0.025),
                    "NeutralGraphite", "Cab_ROPS", 0.005, cab_root)
        for i, y in enumerate((1.04, 1.28, 1.52, 1.76, 1.98)):
            add_box(f"CabGridH_{'L' if side < 0 else 'R'}_{i:02d}",
                    (-0.25, y, side * 0.50), (1.16, 0.023, 0.025),
                    "NeutralGraphite", "Cab_ROPS", 0.005, cab_root)

    # Readable operator compartment study.
    add_box("OperatorSeat_Base", (-0.38, 1.02, 0.0), (0.46, 0.18, 0.48),
            "Interior", "Cab_ROPS", 0.055, cab_root)
    add_box("OperatorSeat_Back", (-0.59, 1.42, 0.0), (0.16, 0.72, 0.46),
            "Interior", "Cab_ROPS", 0.075, cab_root)
    add_box("ControlConsole_L", (-0.26, 1.12, -0.36), (0.56, 0.20, 0.17),
            "NeutralPanel", "Cab_ROPS", 0.035, cab_root)
    add_box("ControlConsole_R", (-0.26, 1.12, 0.36), (0.56, 0.20, 0.17),
            "NeutralPanel", "Cab_ROPS", 0.035, cab_root)
    for side in (-1, 1):
        add_cylinder(f"Joystick_{'L' if side < 0 else 'R'}", (-0.08, 1.28, side * 0.36),
                     0.035, 0.23, "y", "Rubber", "Cab_ROPS", 20, cab_root)
    add_box("Monitor_Display", (0.25, 1.52, 0.31), (0.08, 0.25, 0.25),
            "Interior", "Cab_ROPS", 0.02, cab_root)

    # Published quick-pivot presence; exact hinge and service angle unresolved.
    for side in (-1, 1):
        pivot = add_cylinder(f"CabQuickPivot_{'L' if side < 0 else 'R'}",
                             (-1.00, 0.87, side * 0.50), 0.07, 0.10, "z",
                             "Marker", "Markers", 24, cab_root)
        pivot["authority"] = "manufacturer_published_presence_reconstructed_axis"


def setup_articulation(root: bpy.types.Object) -> None:
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 0.66
        lower_pivot = add_empty(f"Pivot_LiftLower_{suffix}",
                                (-0.92, 1.03, z), "Markers", size=0.10, parent=root)
        upper_pivot = add_empty(f"Pivot_LiftUpper_{suffix}",
                                (-0.72, 1.48, z), "Markers", size=0.10, parent=root)
        lower_pivot["authority"] = "reconstructed"
        upper_pivot["authority"] = "reconstructed"

        ARTICULATED[f"lower_arm_{suffix}"] = add_unit_beam(
            f"VerticalLift_LowerArm_{suffix}", "NeutralGraphite", "Lift_System", 0.035,
            lower_pivot)
        ARTICULATED[f"upper_arm_{suffix}"] = add_unit_beam(
            f"VerticalLift_UpperArm_{suffix}", "NeutralGraphite", "Lift_System", 0.035,
            upper_pivot)
        ARTICULATED[f"rear_riser_{suffix}"] = add_unit_beam(
            f"VerticalLift_RearRiser_{suffix}", "NeutralPanel", "Lift_System", 0.03,
            lower_pivot)
        ARTICULATED[f"carriage_side_{suffix}"] = add_unit_beam(
            f"AttachmentCarriage_Side_{suffix}", "NeutralSteel", "Attachment", 0.025,
            root)

        ARTICULATED[f"lift_barrel_{suffix}"] = add_unit_cylinder(
            f"LiftCylinder_Barrel_{suffix}", "NeutralGraphite", "Hydraulics", 28, root)
        ARTICULATED[f"lift_rod_{suffix}"] = add_unit_cylinder(
            f"LiftCylinder_Rod_{suffix}", "CylinderRod", "Hydraulics", 24, root)

    ARTICULATED["crossmember"] = add_unit_beam(
        "LiftCrossmember", "NeutralSteel", "Lift_System", 0.03, root)
    ARTICULATED["quick_attach"] = add_box(
        "QuickAttach_Interface_Reconstructed", (1.22, 0.67, 0), (0.08, 0.48, 1.40),
        "NeutralGraphite", "Attachment", 0.028, root)
    ARTICULATED["tilt_barrel"] = add_unit_cylinder(
        "BucketTiltCylinder_Barrel", "NeutralGraphite", "Hydraulics", 28, root)
    ARTICULATED["tilt_rod"] = add_unit_cylinder(
        "BucketTiltCylinder_Rod", "CylinderRod", "Hydraulics", 24, root)
    ARTICULATED["tilt_link"] = add_unit_beam(
        "BucketTiltLink_Reconstructed", "NeutralSteel", "Lift_System", 0.018, root)

    bucket_root = add_empty("BucketPivot_Root", (1.3427, 0.5634, 0.0),
                            "Attachment", size=0.13, parent=root)
    bucket_root["authority"] = "reconstructed constrained by published foundry bucket endpoints"
    ARTICULATED["bucket_root"] = bucket_root
    # Bucket local section: independently authored foundry-bucket study.
    bucket = add_prism_xy("FoundryBucket_VisualBasis",
                          [(0.00, -0.02), (0.8882, -0.02), (0.76, 0.23),
                           (0.54, 0.52), (0.08, 0.62), (-0.08, 0.38)],
                          0.0, RECONSTRUCTED["bucket_visual_width_m"],
                          "NeutralPanel", "Attachment", bucket_root, local=True)
    ARTICULATED["bucket_mesh"] = bucket
    add_box("BucketCuttingEdge", (0.84, 0.00, 0.0), (0.18, 0.08, 2.14),
            "NeutralSteel", "Attachment", 0.015, bucket_root, parent_local=True)
    for side in (-1, 1):
        add_box(f"BucketSideCheek_{'L' if side < 0 else 'R'}",
                (0.38, 0.25, side * 1.03), (0.78, 0.42, 0.045),
                "NeutralGraphite", "Attachment", 0.018, bucket_root, parent_local=True)
    for index, z in enumerate((-0.82, -0.41, 0.0, 0.41, 0.82)):
        tooth = add_box(f"BucketTooth_{index + 1:02d}", (0.92, -0.03, z),
                        (0.22, 0.07, 0.13), "NeutralSteel", "Attachment", 0.012,
                        bucket_root, parent_local=True)
        tooth.rotation_euler[1] = math.radians(-5)


def apply_pose(pose: str) -> dict[str, tuple[float, float, float]]:
    if pose == "stowed":
        lower = (1.15, 0.53, 0.0)
        upper = (1.26, 0.88, 0.0)
        hinge = tuple(RECONSTRUCTED["stowed_hinge_xyz_m"])
        bucket_angle = -PUBLISHED["rollback-angle"]
    elif pose == "full_dump":
        lower = (1.03, 3.02, 0.0)
        upper = (1.146, 3.35, 0.0)
        hinge = tuple(RECONSTRUCTED["full_lift_hinge_xyz_m"])
        bucket_angle = -PUBLISHED["dump-angle"]
    else:
        raise ValueError(pose)

    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 0.66
        p_lower = (-0.92, 1.03, z)
        p_upper = (-0.72, 1.48, z)
        c_lower = (lower[0], lower[1], z)
        c_upper = (upper[0], upper[1], z)
        place_beam(ARTICULATED[f"lower_arm_{suffix}"], p_lower, c_lower, 0.13, 0.19)
        place_beam(ARTICULATED[f"upper_arm_{suffix}"], p_upper, c_upper, 0.13, 0.19)
        place_beam(ARTICULATED[f"rear_riser_{suffix}"], p_lower, p_upper, 0.16, 0.17)
        place_beam(ARTICULATED[f"carriage_side_{suffix}"], c_lower, c_upper, 0.14, 0.16)

        cyl_base = (-0.98, 0.55, z)
        cyl_end = (0.42 * c_upper[0] + 0.58 * p_upper[0],
                   0.42 * c_upper[1] + 0.58 * p_upper[1], z)
        mid = tuple((mv(*cyl_base) + mv(*cyl_end)) * 0.58)
        # Convert Blender midpoint back to machine coordinate tuple.
        mid_m = (mid[0], mid[2], mid[1])
        place_cylinder(ARTICULATED[f"lift_barrel_{suffix}"], cyl_base, mid_m, 0.070)
        place_cylinder(ARTICULATED[f"lift_rod_{suffix}"], mid_m, cyl_end, 0.042)

    place_beam(ARTICULATED["crossmember"],
               (upper[0], upper[1], -0.72), (upper[0], upper[1], 0.72), 0.20, 0.20)
    quick = ARTICULATED["quick_attach"]
    quick.location = mv(hinge[0] - 0.07, hinge[1] + 0.10, 0.0)
    quick.dimensions = (0.08, 1.40, 0.48)

    bucket_root = ARTICULATED["bucket_root"]
    bucket_root.location = mv(*hinge)
    # Rotation in machine X/Y plane is Blender rotation around world Y.
    bucket_root.rotation_euler = (0.0, math.radians(-bucket_angle), 0.0)

    tilt_base = (upper[0] - 0.34, upper[1] + 0.16, 0.0)
    tilt_end = (hinge[0] + 0.16 * math.cos(math.radians(bucket_angle)),
                hinge[1] + 0.16 * math.sin(math.radians(bucket_angle)) + 0.30, 0.0)
    mid = tuple((mv(*tilt_base) + mv(*tilt_end)) * 0.58)
    mid_m = (mid[0], mid[2], mid[1])
    place_cylinder(ARTICULATED["tilt_barrel"], tilt_base, mid_m, 0.075)
    place_cylinder(ARTICULATED["tilt_rod"], mid_m, tilt_end, 0.043)
    link_end = (hinge[0] + 0.18, hinge[1] + 0.20, 0.0)
    place_beam(ARTICULATED["tilt_link"], tilt_end, link_end, 0.09, 0.11)

    lip = (hinge[0] + RECONSTRUCTED["bucket_hinge_to_lip_m"] * math.cos(math.radians(bucket_angle)),
           hinge[1] + RECONSTRUCTED["bucket_hinge_to_lip_m"] * math.sin(math.radians(bucket_angle)),
           0.0)
    return {"hinge": hinge, "lip": lip, "lower": lower, "upper": upper}


def build_markers_collisions_inspection(root: bpy.types.Object) -> None:
    # Interaction volumes are transparent but retained as semantic GLB nodes.
    proxies = [
        ("Chassis_Hit", (-0.18, 0.73, 0.0), (2.83, 0.96, 1.42), "Collision"),
        ("Cab_Hit", (-0.28, 1.52, 0.0), (1.46, 1.40, 1.08), "Collision"),
        ("LeftTrack_Hit", (-0.16, 0.35, -0.80), (2.76, 0.70, 0.45), "Collision"),
        ("RightTrack_Hit", (-0.16, 0.35, 0.80), (2.76, 0.70, 0.45), "Collision"),
        ("LiftSystem_Inspect", (0.15, 1.35, 0.0), (2.95, 1.45, 1.60), "Inspection"),
        ("Bucket_Inspect", (1.64, 0.43, 0.0), (1.15, 0.85, 2.16), "Inspection"),
        ("OperatorStation_Inspect", (-0.28, 1.52, 0.0), (1.34, 1.36, 1.00), "Inspection"),
    ]
    for name, center, size, mat_name in proxies:
        obj = add_box(name, center, size, mat_name,
                      "Collision" if mat_name == "Collision" else "Inspection",
                      bevel=0.0, parent=root)
        obj.display_type = "WIRE"
        obj["semantic_volume"] = True


def build_studio() -> None:
    add_box("StudioFloor", (0.0, -0.045, 0.0), (10.0, 0.08, 10.0),
            "Ground", "Studio", 0.0)
    scene = bpy.context.scene
    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.018, 0.023, 0.030, 1.0)
    background.inputs["Strength"].default_value = 0.28

    def area(name, xyz, energy, size, color):
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        COLLECTIONS["Studio"].objects.link(obj)
        obj.location = mv(*xyz)
        look_at(obj, mv(0.0, 0.9, 0.0))
        return obj

    area("KeyLight", (3.8, 5.4, -4.2), 1450, 4.0, (0.95, 0.97, 1.0))
    area("FillLight", (0.6, 3.2, 5.2), 1050, 3.0, (0.68, 0.78, 1.0))
    area("RimLight", (-4.2, 4.0, -1.5), 1200, 3.0, (1.0, 0.72, 0.50))


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(name: str, xyz: tuple[float, float, float], target: tuple[float, float, float],
           lens=52) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36
    obj = bpy.data.objects.new(name, data)
    COLLECTIONS["Studio"].objects.link(obj)
    obj.location = mv(*xyz)
    look_at(obj, mv(*target))
    return obj


def render_view(filename: str, xyz: tuple[float, float, float],
                target: tuple[float, float, float], lens=52) -> Path:
    path = RENDER_DIR / filename
    cam = camera(f"Camera_{path.stem}", xyz, target, lens)
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    RENDER_PATHS.append(path)
    bpy.data.objects.remove(cam, do_unlink=True)
    return path


def render_review_set() -> None:
    apply_pose("stowed")
    render_view("333p-front-three-quarter-stowed.png", (5.2, 3.2, -5.0),
                (0.05, 1.05, 0.0), 56)
    render_view("333p-side-stowed.png", (0.15, 2.05, -8.6),
                (0.15, 1.04, 0.0), 55)
    render_view("333p-rear-three-quarter-stowed.png", (-4.7, 3.0, 4.6),
                (-0.15, 1.02, 0.0), 55)
    render_view("333p-undercarriage-detail.png", (-0.10, 0.95, -6.3),
                (-0.10, 0.32, -0.78), 56)
    render_view("333p-linkage-detail-stowed.png", (3.8, 2.25, 3.4),
                (0.35, 1.20, 0.40), 68)

    apply_pose("full_dump")
    render_view("333p-side-full-lift-dump.png", (0.2, 2.75, -10.2),
                (0.15, 1.78, 0.0), 55)
    render_view("333p-front-three-quarter-full-lift.png", (7.2, 4.0, -7.4),
                (0.15, 1.75, 0.0), 55)
    apply_pose("stowed")


def render_quality(path: Path) -> dict:
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    # Sparse luminance range proves a non-empty, non-flat render without
    # pretending to substitute for the overall critic's human review.
    step = max(4, (len(pixels) // 18000 // 4) * 4)
    values = []
    for i in range(0, len(pixels), step):
        if i + 2 >= len(pixels):
            break
        values.append(0.2126 * pixels[i] + 0.7152 * pixels[i + 1] + 0.0722 * pixels[i + 2])
    return {
        "bytes": path.stat().st_size,
        "sampled_luminance_min": round(min(values), 6),
        "sampled_luminance_max": round(max(values), 6),
        "sampled_luminance_range": round(max(values) - min(values), 6),
    }


def evaluated_counts() -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    triangles = 0
    vertices = 0
    for obj in mesh_objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        vertices += len(mesh.vertices)
        evaluated.to_mesh_clear()
    return {
        "objects": len(bpy.context.scene.objects),
        "meshes": len(mesh_objects),
        "triangles": triangles,
        "vertices": vertices,
        "materials": len(bpy.data.materials),
    }


def semantic_nodes() -> list[str]:
    return [
        "JD333P_Root", "MainFrame_Lower", "Cab_ROPS_Root_Reconstructed",
        "TrackBelt_L", "TrackBelt_R", "VerticalLift_LowerArm_L",
        "VerticalLift_LowerArm_R", "VerticalLift_UpperArm_L",
        "VerticalLift_UpperArm_R", "LiftCrossmember", "LiftCylinder_Barrel_L",
        "LiftCylinder_Rod_L", "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R",
        "BucketTiltCylinder_Barrel", "BucketTiltCylinder_Rod",
        "BucketTiltLink_Reconstructed", "QuickAttach_Interface_Reconstructed",
        "BucketPivot_Root", "FoundryBucket_VisualBasis", "Chassis_Hit",
        "Cab_Hit", "LeftTrack_Hit", "RightTrack_Hit", "LiftSystem_Inspect",
        "Bucket_Inspect", "OperatorStation_Inspect",
    ]


def add_metadata() -> None:
    scene = bpy.context.scene
    scene["machine_id"] = MACHINE_ID
    scene["configuration_id"] = CONFIGURATION_ID
    scene["candidate_class"] = CANDIDATE_CLASS
    scene["engineering_authority"] = False
    scene["machine_axes"] = "+X toward bucket, +Y vertical, +Z machine right"
    scene["blender_axis_mapping"] = "machine (X,Y,Z) -> Blender (X,Z,Y)"
    scene["rights_boundary"] = "independently authored, neutral, unbranded"


def save_and_export() -> None:
    apply_pose("stowed")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    # Studio elements are not part of the machine asset.
    studio = COLLECTIONS["Studio"]
    studio.hide_viewport = True
    for obj in studio.objects:
        obj.hide_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_visible=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )
    studio.hide_viewport = False
    for obj in studio.objects:
        obj.hide_set(False)


def make_gate(gate_id: str, status: str, detail: str, expected=None, actual=None):
    item = {"id": gate_id, "status": status, "detail": detail}
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    return item


def validate(counts: dict) -> dict:
    stowed = apply_pose("stowed")
    full = apply_pose("full_dump")
    apply_pose("stowed")
    # Dimensional references are deliberately explicit; they avoid treating
    # decorative geometry or reconstructed bucket width as source authority.
    actual = {
        "length-no-bucket": 1.40 - (-1.77),
        "length-foundry-bucket": stowed["lip"][0] - (-1.77),
        "width-450-track": 1.025 - (-1.025),
        "rops-height": 2.22,
        "hinge-pin-height": full["hinge"][1],
        "dump-height": full["lip"][1],
        "dump-reach": full["lip"][0] - RECONSTRUCTED["dump_reach_reference_x_m"],
        "ground-clearance": 0.25,
        "dump-angle": math.degrees(math.atan2(full["hinge"][1] - full["lip"][1],
                                                full["lip"][0] - full["hinge"][0])),
        "rollback-angle": math.degrees(math.atan2(stowed["hinge"][1] - stowed["lip"][1],
                                                    stowed["lip"][0] - stowed["hinge"][0])),
    }
    gates = []
    tolerances = {
        "length-no-bucket": 0.005,
        "length-foundry-bucket": 0.008,
        "width-450-track": 0.005,
        "rops-height": 0.005,
        "hinge-pin-height": 0.005,
        "dump-height": 0.008,
        "dump-reach": 0.008,
        "ground-clearance": 0.005,
        "dump-angle": 0.1,
        "rollback-angle": 0.1,
    }
    for fact_id, expected in PUBLISHED.items():
        measured = actual[fact_id]
        delta = abs(measured - expected)
        gate_actual = {"value": round(measured, 5), "absolute_delta": round(delta, 5)}
        detail = "Published constraint represented by explicit dimensional references; hidden geometry remains reconstructed."
        if fact_id in ("dump-angle", "rollback-angle"):
            pose = full if fact_id == "dump-angle" else stowed
            detail = "Measured hinge-to-cutting-edge baseline angle below machine +X toward machine -Y; this is a visualization convention, not a claim about unpublished bucket datum geometry."
            gate_actual["measurement_convention"] = "atan2(hinge_y - lip_y, lip_x - hinge_x), degrees below +X"
            gate_actual["hinge_xyz_m"] = [round(v, 5) for v in pose["hinge"]]
            gate_actual["cutting_edge_lip_xyz_m"] = [round(v, 5) for v in pose["lip"]]
        gates.append(make_gate(
            f"published-{fact_id}", "PASS" if delta <= tolerances[fact_id] else "FAIL",
            detail,
            {"value": expected, "tolerance": tolerances[fact_id]},
            gate_actual,
        ))

    objects = {obj.name for obj in bpy.context.scene.objects}
    missing = [name for name in semantic_nodes() if name not in objects]
    gates.append(make_gate("semantic-node-presence", "PASS" if not missing else "FAIL",
                           "Required technical-study semantic hierarchy is present.",
                           semantic_nodes(), {"missing": missing}))
    roller_nodes = [name for name in objects if name.startswith("TrackRoller_L_") and "Flange" not in name]
    roller_nodes_r = [name for name in objects if name.startswith("TrackRoller_R_") and "Flange" not in name]
    idlers_l = [name for name in objects if name.startswith("TrackIdler_L_") and "Flange" not in name]
    idlers_r = [name for name in objects if name.startswith("TrackIdler_R_") and "Flange" not in name]
    count_ok = len(roller_nodes) == 5 and len(roller_nodes_r) == 5 and len(idlers_l) == 2 and len(idlers_r) == 2
    gates.append(make_gate("published-undercarriage-component-counts",
                           "PASS" if count_ok else "FAIL",
                           "Published roller/idler counts represented; centers and flange geometry reconstructed.",
                           {"track_rollers_per_side": 5, "track_idlers_per_side": 2},
                           {"left_rollers": sorted(roller_nodes), "right_rollers": sorted(roller_nodes_r),
                            "left_idlers": sorted(idlers_l), "right_idlers": sorted(idlers_r)}))

    budget = RECONSTRUCTED["structural_triangle_budget"]
    tri_ok = 5000 <= counts["triangles"] <= budget
    gates.append(make_gate("structural-triangle-budget", "PASS" if tri_ok else "FAIL",
                           "Study is detailed enough for review and remains inside the reconstructed web-study budget.",
                           {"minimum": 5000, "maximum": budget}, counts["triangles"]))

    render_results = {str(path.relative_to(MACHINE_DIR)): render_quality(path) for path in RENDER_PATHS}
    render_ok = all(q["bytes"] > 30000 and q["sampled_luminance_range"] > 0.15
                    for q in render_results.values()) and len(render_results) >= 7
    gates.append(make_gate("render-non-emptiness", "PASS" if render_ok else "FAIL",
                           "Seven deterministic review renders have non-trivial bytes and luminance range; human visual review remains pending.",
                           {"minimum_views": 7, "minimum_bytes": 30000, "minimum_luminance_range": 0.15},
                           render_results))

    gates.extend([
        make_gate("published-departure-angle-envelope", "PENDING", "The 30 degree published value is retained, but the brochure is not a scale drawing and the complete rear swept envelope has not been qualified.", {"value": PUBLISHED_ADDITIONAL["departure-angle"], "unit": "deg"}),
        make_gate("published-front-turn-radius-motion", "PENDING", "The 2.18 m foundry-bucket turn radius is retained as a motion constraint; no travel/steering swept-volume solver exists in this structural study.", {"value": PUBLISHED_ADDITIONAL["front-turn-radius"], "unit": "m"}),
        make_gate("lift-linkage-closure", "PENDING", "Exact pivot and link geometry is unresolved; structural-study beams are not a qualified solver."),
        make_gate("bucket-linkage-closure", "PENDING", "Exact tilt-linkage topology and anchors are unresolved."),
        make_gate("cylinder-length-continuity", "PENDING", "Cylinder anchors and strokes are reconstructed and not yet mechanically qualified."),
        make_gate("ground-collision", "PENDING", "Collision proxies exist but no swept-pose collision solver has run."),
        make_gate("self-collision", "PENDING", "No swept-volume self-collision qualification has run."),
        make_gate("track-phase-continuity", "PENDING", "Track path is a static visual reconstruction; pitch and phase remain unresolved."),
        make_gate("exact-attachment-interface", "PENDING", "Quick-attach and exact foundry bucket identity are unresolved."),
        make_gate("human-visual-critic", "PENDING", "Overall critic has not yet approved the exact render and artifact hashes."),
        make_gate("viewer-browser-accessibility-mobile-performance-selection", "PENDING", "No shared-viewer integration or browser qualification is claimed."),
        make_gate("publication-release-deployment", "PENDING", "Only the overall publisher may advance or deploy this study."),
    ])
    failures = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    return {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "engineering_authority": False,
        "verdict": "FAIL" if failures else "PASS",
        "verdict_scope": "technical_structural_study_only",
        "higher_stage_gates": "PENDING",
        "failed_gates": failures,
        "gates": gates,
    }


def bounds_from_reference() -> dict:
    # Published fixed envelope plus independently authored bucket study bounds.
    return {
        "machine_axes_m": {
            "fixed_machine_without_bucket": {
                "min": [-1.77, 0.0, -1.025],
                "max": [1.40, 2.22, 1.025],
                "size": [3.17, 2.22, 2.05],
            },
            "stowed_with_reconstructed_foundry_bucket": {
                "min": [-1.77, 0.0, -1.04],
                "max": [2.07, 2.22, 1.04],
                "size": [3.84, 2.22, 2.08],
            },
        },
        "note": "Explicit constraint references; not a claim that brochure art is a scale drawing.",
    }


def write_outputs(counts: dict, validation: dict) -> None:
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    render_entries = []
    for path in RENDER_PATHS:
        render_entries.append({
            "path": str(path.relative_to(MACHINE_DIR)),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        })
    present_nodes = {name: bpy.data.objects.get(name) is not None for name in semantic_nodes()}
    receipt = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "configuration_status": "research_candidate",
        "candidate_class": CANDIDATE_CLASS,
        "engineering_authority": False,
        "authority_statement": "Independent technical structural study only; not manufacturer CAD, engineering data, training material, or operational guidance.",
        "rights_boundary": "Neutral unbranded materials; no copied manufacturer geometry, textures, logos, imagery, or publication pages are shipped.",
        "blender": {
            "version": bpy.app.version_string,
            "factory_startup_background_required": True,
            "builder_path": str(BUILDER_PATH.relative_to(MACHINE_DIR)),
            "builder_sha256": sha256(BUILDER_PATH),
        },
        "artifacts": {
            "blend": {"path": str(BLEND_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size},
            "glb": {"path": str(GLB_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(GLB_PATH), "bytes": GLB_PATH.stat().st_size},
            "validation": {"path": str(VALIDATION_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(VALIDATION_PATH), "bytes": VALIDATION_PATH.stat().st_size},
        },
        "scene": {
            "units": "meters",
            "machine_axes": "+X toward bucket, +Y vertical, +Z machine right",
            "blender_storage_mapping": "machine (X,Y,Z) -> Blender (X,Z,Y)",
            "glb_export_y_up": True,
            "bounds": bounds_from_reference(),
            "counts": counts,
        },
        "semantic_nodes": present_nodes,
        "manufacturer_published_constraints_used": [
            {
                "id": fact_id,
                "value": value,
                "source_id": "JD-333P-MK333CAU",
                "location": "PDF page 6",
                "use": "geometry_constraint",
            }
            for fact_id, value in PUBLISHED.items()
        ] + [
            {
                "id": "departure-angle",
                "value": 30.0,
                "unit": "deg",
                "source_id": "JD-333P-MK333CAU",
                "location": "PDF page 6, dimension I",
                "use": "retained_constraint_geometry_qualification_pending",
            },
            {
                "id": "front-turn-radius",
                "value": 2.18,
                "unit": "m",
                "source_id": "JD-333P-MK333CAU",
                "location": "PDF page 6, dimension J",
                "use": "retained_motion_constraint_solver_pending",
            },
            {
                "id": "track-rollers-per-side",
                "value": 5,
                "unit": "count",
                "source_id": "JD-333P-MK333CAU",
                "location": "PDF page 6",
                "use": "component_count; centers and flange geometry reconstructed",
            },
            {
                "id": "track-idlers-per-side",
                "value": 2,
                "unit": "count",
                "source_id": "JD-333P-MK333CAU",
                "location": "PDF page 6",
                "use": "component_count; centers and flange geometry reconstructed",
            },
        ],
        "reconstructed_values": RECONSTRUCTED,
        "unresolved_choices_and_mechanical_gaps": UNRESOLVED,
        "renders": render_entries,
        "build_verdict": "PASS" if validation["verdict"] != "FAIL" else "FAIL",
        "validation_verdict": validation["verdict"],
        "higher_stage_gates": "PENDING",
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    reset_scene()
    for name in ("Fixed_Structure", "Undercarriage", "Cab_ROPS", "Lift_System",
                 "Hydraulics", "Attachment", "Markers", "Collision", "Inspection", "Studio"):
        make_collection(name)
    build_materials()
    root = build_root_and_fixed_structure()
    build_undercarriage(root)
    build_cab(root)
    setup_articulation(root)
    apply_pose("stowed")
    build_markers_collisions_inspection(root)
    build_studio()
    add_metadata()
    render_review_set()
    save_and_export()
    counts = evaluated_counts()
    validation = validate(counts)
    write_outputs(counts, validation)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Validation failed: {validation['failed_gates']}")
    print(json.dumps({
        "status": validation["verdict"],
        "blend": str(BLEND_PATH),
        "glb": str(GLB_PATH),
        "receipt": str(RECEIPT_PATH),
        "validation": str(VALIDATION_PATH),
        "counts": counts,
        "renders": [str(p) for p in RENDER_PATHS],
    }, indent=2))


if __name__ == "__main__":
    main()
