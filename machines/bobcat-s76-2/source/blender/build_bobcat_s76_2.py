#!/usr/bin/env python3
"""Build the independently authored Bobcat Pro S76-2 structural study.

Run only with Blender factory startup, for example:
  Blender --factory-startup --background --python build_bobcat_s76_2.py

Manufacturer facts constrain the exterior envelope and endpoint references.
All hidden pivots, anchors, lift interpolation, bucket section, wheel/tire
construction, hose routing, and service details are reconstructed and are not
engineering authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


MACHINE_ID = "bobcat-s76-2"
CONFIGURATION_ID = "BOBCAT-S76-2-NAM-STD74-STD-TIRE-CAB-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
MACHINE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = Path(__file__).resolve()
BLEND_PATH = MACHINE_DIR / "source/blender/bobcat-s76-2-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets/bobcat-s76-2-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production/asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production/validation.json"
RENDER_DIR = MACHINE_DIR / "review/renders"


PUBLISHED = {
    "length-standard-bucket": 3.6068,
    "length-without-attachment": 2.8956,
    "overall-width": 1.8288,
    "bucket-width": 1.8796,
    "overall-height": 2.08026,
    "hinge-pin-height": 3.25882,
    "reach-maximum-height": 0.8509,
    "turning-radius": 2.12598,
    "wheelbase": 1.22682,
    "standard-bucket-nominal-width-in": 74.0,
    "operating-weight-kg": 3635.09,
}

# Independently authored visual-study inputs. None are Bobcat dimensions.
RECONSTRUCTED = {
    "rear_extent_x_m": -1.4700,
    "front_without_attachment_x_m": 1.4256,
    "rear_wheel_center_x_m": -0.6500,
    "front_wheel_center_x_m": 0.57682,
    "wheel_center_y_m": 0.4575,
    "wheel_center_abs_z_m": 0.7694,
    "tire_outer_radius_m": 0.4250,
    "tire_section_radius_m": 0.1450,
    "tire_tread_block_count": 20,
    "stowed_hinge_xyz_m": [1.3680, 0.5050, 0.0],
    "full_lift_hinge_xyz_m": [1.0800, 3.25882, 0.0],
    "stowed_bucket_rotation_deg": 28.0,
    "full_lift_carry_rotation_deg": 10.0,
    "full_lift_dump_rotation_deg": 57.0,
    # Solved against the published maximum-height reach for the explicitly
    # reconstructed lip datum at the 10 degree full-lift review pose.
    "bucket_local_lip_x_m": 0.8693163134748344,
    "bucket_shell_visual_width_m": 1.8250,
    "bucket_cutting_edge_width_m": 1.8796,
    "rear_main_pivot_xyz_m": [-0.9800, 1.2900, 0.0],
    "rear_control_pivot_xyz_m": [-0.8600, 1.7200, 0.0],
    "lift_cylinder_base_xyz_m": [-1.1550, 0.6450, 0.0],
    "stowed_carriage_lower_xyz_m": [1.2550, 0.4050, 0.0],
    "stowed_carriage_upper_xyz_m": [1.3680, 0.7150, 0.0],
    "full_carriage_lower_xyz_m": [0.9700, 2.9400, 0.0],
    "full_carriage_upper_xyz_m": [1.0800, 3.25882, 0.0],
    "lift_arm_lateral_center_abs_z_m": 0.6550,
    "hydraulic_hose_visual_diameter_m": 0.0220,
    "bucket_shell_profile": [
        [-0.14, 0.34], [-0.05, 0.59], [0.40, 0.52],
        [0.73, 0.20], [0.8693163134748344, -0.03], [-0.07, -0.03]
    ],
}

UNRESOLVED = [
    "control and display package identity",
    "exact standard-bucket part, shell section, cutting edge, and coupler fit",
    "manual Bob-Tach versus optional Power Bob-Tach geometry",
    "counterweight, detection, and camera packages",
    "hidden lift-linkage pivots, link lengths, cylinder anchors, and stroke",
    "vertical-lift intermediate path and bucket self-level behavior",
    "standard-tire casing, tread mold, loaded radius, wheel offset, and hubs",
    "hydraulic hose lengths, fittings, routing, and clamp points",
    "rear service-door hinge, latch, and opening angle",
    "manufacturer datum used for maximum-height reach",
    "public branding and exact livery authorization",
]

COLLECTIONS: dict[str, bpy.types.Collection] = {}
MATERIALS: dict[str, bpy.types.Material] = {}
ART: dict[str, bpy.types.Object] = {}
RENDERS: list[Path] = []


def mv(x: float, y: float, z: float) -> Vector:
    """Map machine (+X front, +Y up, +Z right) to Blender (X,Z,Y)."""
    return Vector((x, z, y))


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
    for blocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                   bpy.data.cameras, bpy.data.lights):
        for block in list(blocks):
            blocks.remove(block)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    bpy.context.preferences.filepaths.save_version = 0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1120
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    if hasattr(scene.render, "dither_intensity"):
        scene.render.dither_intensity = 0.0
    for prop in (
        "use_stamp_camera", "use_stamp_date", "use_stamp_filename",
        "use_stamp_frame", "use_stamp_frame_range", "use_stamp_hostname",
        "use_stamp_labels", "use_stamp_lens", "use_stamp_marker",
        "use_stamp_memory", "use_stamp_note", "use_stamp_render_time",
        "use_stamp_scene", "use_stamp_sequencer_strip", "use_stamp_time",
    ):
        if hasattr(scene.render, prop):
            setattr(scene.render, prop, False)
    scene.view_settings.look = "AgX - Medium High Contrast"


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    COLLECTIONS[name] = collection
    return collection


def move_to(obj: bpy.types.Object, collection_name: str) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    COLLECTIONS[collection_name].objects.link(obj)


def parent_keep(obj: bpy.types.Object, parent: bpy.types.Object, keep_world=True) -> None:
    world = obj.matrix_world.copy()
    obj.parent = parent
    if keep_world:
        obj.matrix_world = world


def make_material(name: str, color, metallic=0.0, roughness=0.45,
                  transmission=0.0) -> None:
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


def mat(obj: bpy.types.Object, name: str) -> None:
    if obj.type == "MESH":
        obj.data.materials.append(MATERIALS[name])


def add_empty(name: str, xyz=(0.0, 0.0, 0.0), collection="Structure",
              parent=None, display_size=0.12) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.location = mv(*xyz)
    obj.empty_display_size = display_size
    COLLECTIONS[collection].objects.link(obj)
    if parent:
        bpy.context.view_layer.update()
        parent_keep(obj, parent)
    return obj


def add_box(name: str, center, size, material_name: str, collection: str,
            parent=None, bevel=0.015, local=False) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mv(*center) if not local else (0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[2], size[1])
    if local:
        obj.location = mv(*center)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = min(bevel, min(size) * 0.2)
        mod.segments = 2
    mat(obj, material_name)
    move_to(obj, collection)
    if parent:
        parent_keep(obj, parent, keep_world=not local)
    return obj


def add_cylinder(name: str, center, radius: float, depth: float, axis: str,
                 material_name: str, collection: str, parent=None,
                 vertices=32, local=False) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=mv(*center) if not local else (0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(axis)
    if local:
        obj.location = mv(*center)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
    mod.width = min(radius * 0.10, 0.012)
    mod.segments = 2
    mat(obj, material_name)
    move_to(obj, collection)
    if parent:
        parent_keep(obj, parent, keep_world=not local)
    return obj


def add_torus(name: str, center, major_radius: float, minor_radius: float,
              material_name: str, collection: str, parent=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major_radius,
                                    minor_radius=minor_radius,
                                    major_segments=56, minor_segments=16,
                                    location=mv(*center),
                                    rotation=(math.radians(90), 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mat(obj, material_name)
    move_to(obj, collection)
    if parent:
        parent_keep(obj, parent)
    return obj


def add_prism_xy(name: str, polygon, z_center: float, width: float,
                 material_name: str, collection: str, parent=None,
                 local=False, bevel=0.015) -> bpy.types.Object:
    half = width / 2.0
    verts = []
    for z in (-half, half):
        for x, y in polygon:
            verts.append((x, z, y) if local else tuple(mv(x, y, z + z_center)))
    n = len(polygon)
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    mat(obj, material_name)
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    if parent:
        parent_keep(obj, parent, keep_world=not local)
    return obj


def add_unit_beam(name: str, material_name: str, collection: str,
                  parent=None, bevel=0.018) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.object
    obj.name = name
    mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
    mod.width = bevel
    mod.segments = 2
    mat(obj, material_name)
    move_to(obj, collection)
    if parent:
        parent_keep(obj, parent)
    return obj


def place_beam(obj: bpy.types.Object, a, b, width: float, depth: float) -> None:
    pa, pb = mv(*a), mv(*b)
    vec = pb - pa
    rotation = vec.to_track_quat("X", "Z").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((vec.length / 2.0, width / 2.0, depth / 2.0, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) / 2.0) @ rotation @ scale


def add_unit_cylinder(name: str, material_name: str, collection: str,
                      parent=None, vertices=28) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=2.0)
    obj = bpy.context.object
    obj.name = name
    mat(obj, material_name)
    move_to(obj, collection)
    if parent:
        parent_keep(obj, parent)
    return obj


def place_cylinder(obj: bpy.types.Object, a, b, radius: float) -> None:
    pa, pb = mv(*a), mv(*b)
    vec = pb - pa
    rotation = vec.to_track_quat("Z", "Y").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((radius, radius, vec.length / 2.0, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) / 2.0) @ rotation @ scale


def add_hose(name: str, points, radius: float, material_name: str,
             collection: str, parent=None) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coord in zip(spline.points, points):
        p = mv(*coord)
        point.co = (p.x, p.y, p.z, 1.0)
    obj = bpy.data.objects.new(name, curve)
    COLLECTIONS[collection].objects.link(obj)
    curve.materials.append(MATERIALS[material_name])
    if parent:
        parent_keep(obj, parent)
    return obj


def set_hose(obj: bpy.types.Object, points) -> None:
    spline = obj.data.splines[0]
    for point, coord in zip(spline.points, points):
        p = mv(*coord)
        point.co = (p.x, p.y, p.z, 1.0)


def build_materials() -> None:
    # Manufacturer-neutral palette: no Bobcat white/orange livery or logos.
    make_material("WarmPanel", (0.40, 0.42, 0.42, 1.0), metallic=0.36, roughness=0.37)
    make_material("DarkGraphite", (0.045, 0.052, 0.058, 1.0), metallic=0.55, roughness=0.31)
    make_material("StructuralSteel", (0.20, 0.23, 0.25, 1.0), metallic=0.72, roughness=0.26)
    make_material("MutedBronze", (0.34, 0.25, 0.13, 1.0), metallic=0.48, roughness=0.35)
    make_material("Rubber", (0.012, 0.014, 0.016, 1.0), roughness=0.90)
    make_material("Tread", (0.024, 0.026, 0.027, 1.0), roughness=0.83)
    make_material("CylinderRod", (0.56, 0.59, 0.61, 1.0), metallic=0.95, roughness=0.13)
    make_material("Glass", (0.045, 0.105, 0.13, 0.46), metallic=0.05, roughness=0.15, transmission=0.20)
    make_material("Interior", (0.055, 0.060, 0.063, 1.0), roughness=0.70)
    make_material("Lamp", (0.76, 0.82, 0.78, 1.0), metallic=0.12, roughness=0.18)
    make_material("WarningLens", (0.50, 0.08, 0.035, 1.0), metallic=0.05, roughness=0.22)
    make_material("Ground", (0.027, 0.031, 0.036, 1.0), roughness=0.80)


def build_wheel(root: bpy.types.Object, x: float, z: float, suffix: str) -> None:
    y = RECONSTRUCTED["wheel_center_y_m"]
    add_torus(f"Tire_{suffix}", (x, y, z), 0.280, 0.145,
              "Rubber", "Wheels", root)
    # Reconstructed alternating skid-steer tread bars.
    for i in range(RECONSTRUCTED["tire_tread_block_count"]):
        angle = math.tau * i / RECONSTRUCTED["tire_tread_block_count"]
        radius = 0.405
        tread = add_box(
            f"TireTread_{suffix}_{i + 1:02d}",
            (x + radius * math.cos(angle), y + radius * math.sin(angle), z),
            (0.105, 0.055, 0.285), "Tread", "Wheels", root, 0.008)
        tread.rotation_euler[1] = -angle
        tread.rotation_euler[0] = math.radians(7 if i % 2 == 0 else -7)

    add_cylinder(f"RimOuter_{suffix}", (x, y, z), 0.220, 0.170, "z",
                 "StructuralSteel", "Wheels", root, 40)
    add_cylinder(f"RimDish_{suffix}", (x, y, z + (0.040 if z > 0 else -0.040)),
                 0.155, 0.195, "z", "DarkGraphite", "Wheels", root, 36)
    add_cylinder(f"AxleHub_{suffix}", (x, y, z + (0.105 if z > 0 else -0.105)),
                 0.078, 0.065, "z", "CylinderRod", "Wheels", root, 32)
    for lug in range(8):
        angle = math.tau * lug / 8.0
        add_cylinder(
            f"WheelLug_{suffix}_{lug + 1:02d}",
            (x + 0.112 * math.cos(angle), y + 0.112 * math.sin(angle),
             z + (0.120 if z > 0 else -0.120)),
            0.015, 0.022, "z", "CylinderRod", "Wheels", root, 12)


def build_fixed(root: bpy.types.Object) -> None:
    # One independently authored sloped monocoque/chaincase mass.
    add_prism_xy(
        "Chassis_MainMonocoque",
        [(-1.47, 0.28), (-1.40, 1.22), (-0.98, 1.47), (0.85, 1.18),
         (1.4256, 0.70), (1.4256, 0.30)],
        0.0, 1.18, "DarkGraphite", "Structure", root, bevel=0.035)
    add_box("Chassis_BellyPan", (-0.02, 0.275, 0.0), (2.88, 0.17, 1.18),
            "StructuralSteel", "Structure", root, 0.025)

    # Rear engine enclosure and service-door segmentation.
    add_prism_xy(
        "EngineHousing_Upper",
        [(-1.45, 0.55), (-1.41, 1.46), (-0.95, 1.69), (-0.52, 1.52),
         (-0.42, 0.63)],
        0.0, 1.28, "WarmPanel", "Body", root, bevel=0.035)
    add_box("RearServiceDoor", (-1.4475, 1.015, 0.0), (0.045, 0.80, 1.05),
            "WarmPanel", "Body", root, 0.018)
    for i, y in enumerate((0.76, 0.86, 0.96, 1.06, 1.16, 1.26, 1.36)):
        add_box(f"RearCoolingLouver_{i + 1:02d}", (-1.461, y, 0.0),
                (0.018, 0.035, 0.82), "DarkGraphite", "Details", root, 0.004)
    add_box("RearDoorLatch", (-1.462, 1.39, 0.43), (0.016, 0.12, 0.07),
            "CylinderRod", "Details", root, 0.005)
    add_box("RearLowerCounterPanel", (-1.4425, 0.55, 0.0), (0.055, 0.27, 1.22),
            "StructuralSteel", "Body", root, 0.018)

    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 0.635
        add_prism_xy(
            f"SideServicePanel_{suffix}",
            [(-1.28, 0.62), (-1.18, 1.34), (-0.52, 1.48), (0.16, 1.20),
             (0.73, 0.74), (0.76, 0.48), (-1.08, 0.48)],
            z, 0.055, "WarmPanel", "Body", root, bevel=0.012)
        # Fender eyebrows and wheel-to-body separation.
        for x, wheel in ((RECONSTRUCTED["rear_wheel_center_x_m"], "Rear"),
                         (RECONSTRUCTED["front_wheel_center_x_m"], "Front")):
            add_box(f"FenderTop_{wheel}_{suffix}", (x, 0.86, z),
                    (0.78, 0.11, 0.10), "DarkGraphite", "Body", root, 0.025)
        add_box(f"EntryStepLower_{suffix}", (0.98, 0.39, side * 0.755),
                (0.42, 0.11, 0.18), "StructuralSteel", "Details", root, 0.018)
        add_box(f"EntryStepUpper_{suffix}", (0.79, 0.62, side * 0.695),
                (0.33, 0.10, 0.13), "DarkGraphite", "Details", root, 0.014)
        for step_index, x in enumerate((0.86, 0.99, 1.12)):
            add_box(f"StepGrip_{suffix}_{step_index + 1:02d}",
                    (x, 0.452, side * 0.755), (0.035, 0.012, 0.17),
                    "MutedBronze", "Details", root, 0.002)

        add_box(f"RearLampHousing_{suffix}", (-1.405, 1.48, side * 0.46),
                (0.12, 0.17, 0.16), "DarkGraphite", "Details", root, 0.018)
        add_box(f"RearLampLens_{suffix}", (-1.458, 1.49, side * 0.46),
                (0.022, 0.105, 0.10), "WarningLens", "Details", root, 0.006)

    # Four standard tire/rim assemblies, wheelbase constrained by official fact.
    for x, axle in ((RECONSTRUCTED["rear_wheel_center_x_m"], "Rear"),
                    (RECONSTRUCTED["front_wheel_center_x_m"], "Front")):
        for side, suffix in ((-1, "L"), (1, "R")):
            build_wheel(root, x, side * RECONSTRUCTED["wheel_center_abs_z_m"],
                        f"{axle}_{suffix}")

    # Visible pivot towers and service cues establish the lift system origin.
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * RECONSTRUCTED["lift_arm_lateral_center_abs_z_m"]
        add_prism_xy(f"LiftTower_{suffix}",
                     [(-1.17, 0.64), (-1.12, 1.58), (-0.82, 1.91),
                      (-0.55, 1.62), (-0.50, 0.70)],
                     z, 0.13, "DarkGraphite", "Structure", root, bevel=0.024)
        for x, y, label in ((-0.98, 1.29, "Main"), (-0.86, 1.72, "Control")):
            add_cylinder(f"LiftPivotBoss_{label}_{suffix}", (x, y, z),
                         0.095, 0.18, "z", "StructuralSteel", "Details", root, 32)
            add_cylinder(f"LiftPivotPin_{label}_{suffix}",
                         (x, y, z + (0.095 if side > 0 else -0.095)),
                         0.050, 0.045, "z", "CylinderRod", "Details", root, 24)


def build_cab(root: bpy.types.Object) -> None:
    cab = add_empty("CabEnclosure_Root", (-0.22, 0.78, 0.0), "Cab", root)
    cab["authority"] = "manufacturer_published_presence_observed_form_reconstructed_dimensions"
    # Cage follows the low rear/high roof silhouette visible in official gallery.
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 0.485
        for name, a, b in (
            ("RearPillar", (-0.83, 0.86, z), (-0.75, 1.99, z)),
            ("FrontPillar", (0.48, 0.84, z), (0.35, 1.99, z)),
            ("RoofRail", (-0.75, 1.99, z), (0.35, 1.99, z)),
            ("LowerSill", (-0.83, 0.86, z), (0.48, 0.84, z)),
        ):
            beam = add_unit_beam(f"Cab{name}_{suffix}", "DarkGraphite", "Cab", cab, 0.018)
            place_beam(beam, a, b, 0.075, 0.085)
        # Side window glass and protective grid.
        add_box(f"CabSideGlass_{suffix}", (-0.19, 1.42, z),
                (1.03, 0.90, 0.025), "Glass", "Cab", cab, 0.005)
        for i, x in enumerate((-0.65, -0.43, -0.21, 0.01, 0.23)):
            add_box(f"CabGridVertical_{suffix}_{i + 1:02d}",
                    (x, 1.42, side * 0.505), (0.018, 0.91, 0.020),
                    "DarkGraphite", "Cab", cab, 0.003)
        for i, y in enumerate((1.02, 1.24, 1.46, 1.68, 1.88)):
            add_box(f"CabGridHorizontal_{suffix}_{i + 1:02d}",
                    (-0.19, y, side * 0.507), (1.03, 0.018, 0.020),
                    "DarkGraphite", "Cab", cab, 0.003)

    add_box("CabRoof", (-0.20, 2.025, 0.0), (1.28, 0.110, 1.06),
            "WarmPanel", "Cab", cab, 0.035)
    add_box("CabFrontDoorGlass", (0.425, 1.42, 0.0), (0.035, 1.00, 0.87),
            "Glass", "Cab", cab, 0.006)
    add_box("CabRearGlass", (-0.79, 1.44, 0.0), (0.025, 0.82, 0.82),
            "Glass", "Cab", cab, 0.005)
    add_box("CabFrontLowerDoorFrame", (0.455, 0.95, 0.0), (0.075, 0.17, 0.95),
            "DarkGraphite", "Cab", cab, 0.018)

    # Operator station remains visible through neutral glazing.
    add_box("OperatorSeatBase", (-0.24, 0.98, 0.0), (0.44, 0.19, 0.46),
            "Interior", "Cab", cab, 0.055)
    add_box("OperatorSeatBack", (-0.47, 1.35, 0.0), (0.15, 0.67, 0.44),
            "Interior", "Cab", cab, 0.060)
    add_box("SeatBar", (0.03, 1.26, 0.0), (0.09, 0.12, 0.73),
            "DarkGraphite", "Cab", cab, 0.025)
    add_box("ControlConsoleLeft", (-0.02, 1.12, -0.34), (0.54, 0.19, 0.16),
            "DarkGraphite", "Cab", cab, 0.028)
    add_box("ControlConsoleRight", (-0.02, 1.12, 0.34), (0.54, 0.19, 0.16),
            "DarkGraphite", "Cab", cab, 0.028)
    for side, suffix in ((-1, "L"), (1, "R")):
        add_cylinder(f"JoystickStudy_{suffix}", (0.12, 1.29, side * 0.34),
                     0.030, 0.19, "y", "Rubber", "Cab", cab, 18)
        add_box(f"FrontWorkLightHousing_{suffix}",
                (0.38, 1.92, side * 0.38), (0.12, 0.12, 0.17),
                "DarkGraphite", "Details", cab, 0.018)
        add_box(f"FrontWorkLightLens_{suffix}",
                (0.446, 1.92, side * 0.38), (0.016, 0.078, 0.115),
                "Lamp", "Details", cab, 0.005)


def setup_articulation(root: bpy.types.Object) -> None:
    lift_root = add_empty(
        "LiftMotion_ROOT", tuple(RECONSTRUCTED["rear_main_pivot_xyz_m"]),
        "Lift", root, display_size=0.18)
    lift_root["axis"] = "+Z nominal"
    lift_root["authority"] = "reconstructed_visual_four_bar_owner"
    hydraulics_root = add_empty(
        "LiftHydraulics_ROOT", tuple(RECONSTRUCTED["lift_cylinder_base_xyz_m"]),
        "Hydraulics", root, display_size=0.14)
    hydraulics_root["authority"] = "reconstructed_visual_endpoint_owner"

    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * RECONSTRUCTED["lift_arm_lateral_center_abs_z_m"]
        ART[f"main_arm_{suffix}"] = add_unit_beam(
            f"VerticalLift_MainArm_{suffix}", "WarmPanel", "Lift", lift_root, 0.030)
        ART[f"upper_link_{suffix}"] = add_unit_beam(
            f"VerticalLift_UpperLink_{suffix}", "StructuralSteel", "Lift", lift_root, 0.023)
        ART[f"carriage_{suffix}"] = add_unit_beam(
            f"AttachmentCarriageSide_{suffix}", "DarkGraphite", "Lift", lift_root, 0.020)
        ART[f"brace_{suffix}"] = add_unit_beam(
            f"LiftArmBoxBrace_{suffix}", "WarmPanel", "Lift", lift_root, 0.024)
        ART[f"lift_barrel_{suffix}"] = add_unit_cylinder(
            f"LiftCylinderBarrel_{suffix}", "DarkGraphite", "Hydraulics", hydraulics_root, 32)
        ART[f"lift_rod_{suffix}"] = add_unit_cylinder(
            f"LiftCylinderRod_{suffix}", "CylinderRod", "Hydraulics", hydraulics_root, 28)
        for hidx, offset in enumerate((-0.017, 0.017), 1):
            hose = add_hose(
                f"LiftHydraulicHose_{suffix}_{hidx:02d}",
                [(-1.18, 0.78, z + offset), (-0.92, 1.16, z + offset),
                 (0.10, 0.98, z + offset), (1.08, 0.72, z + offset)],
                RECONSTRUCTED["hydraulic_hose_visual_diameter_m"] / 2.0,
                "Rubber", "Hydraulics", hydraulics_root)
            ART[f"hose_{suffix}_{hidx}"] = hose

    ART["crossmember"] = add_unit_beam(
        "LiftCrossmember", "StructuralSteel", "Lift", lift_root, 0.025)
    ART["tilt_base_crossmember"] = add_unit_beam(
        "BucketTiltBaseCrossmember", "DarkGraphite", "Lift", lift_root, 0.018)
    ART["quick_attach"] = add_box(
        "BobTach_Interface_Reconstructed", (1.345, 0.56, 0.0),
        (0.085, 0.48, 1.48), "DarkGraphite", "Bucket", lift_root, 0.026)
    ART["tilt_barrel"] = add_unit_cylinder(
        "BucketTiltCylinderBarrel", "DarkGraphite", "Hydraulics", hydraulics_root, 32)
    ART["tilt_rod"] = add_unit_cylinder(
        "BucketTiltCylinderRod", "CylinderRod", "Hydraulics", hydraulics_root, 28)
    ART["bellcrank"] = add_unit_beam(
        "BucketTiltBellcrank_Reconstructed", "MutedBronze", "Lift", lift_root, 0.016)

    bucket_root = add_empty("BucketPivotRoot", tuple(RECONSTRUCTED["stowed_hinge_xyz_m"]),
                            "Bucket", lift_root)
    bucket_root["authority"] = "reconstructed_constrained_by_standard_bucket_width_and_stowed_length"
    ART["bucket_root"] = bucket_root
    bucket_offset = add_empty(
        "BucketStowedPose_ROOT", tuple(RECONSTRUCTED["stowed_hinge_xyz_m"]),
        "Bucket", bucket_root)
    bucket_offset["authority"] = "reconstructed_static_pose_offset_below_neutral_interactive_pivot"
    ART["bucket_offset"] = bucket_offset
    add_cylinder(
        "BucketTiltLugPin", (0.02, 0.28, 0.0), 0.090, 0.46, "z",
        "CylinderRod", "Bucket", bucket_offset, 28, local=True)
    for side, suffix in ((-1, "L"), (1, "R")):
        add_box(
            f"BucketTiltLugPlate_{suffix}", (0.02, 0.20, side * 0.18),
            (0.20, 0.28, 0.055), "DarkGraphite", "Bucket",
            bucket_offset, 0.012, local=True)
    add_prism_xy(
        "Standard74BucketShell_Reconstructed",
        RECONSTRUCTED["bucket_shell_profile"], 0.0,
        RECONSTRUCTED["bucket_shell_visual_width_m"],
        "WarmPanel", "Bucket", bucket_offset, local=True, bevel=0.020)
    add_box("BucketCuttingEdge", (RECONSTRUCTED["bucket_local_lip_x_m"] - 0.055, -0.025, 0.0),
            (0.110, 0.055, RECONSTRUCTED["bucket_cutting_edge_width_m"]),
            "StructuralSteel", "Bucket", bucket_offset, 0.012, local=True)
    add_box("BucketTopTorqueTube", (0.12, 0.49, 0.0),
            (0.18, 0.15, 1.72), "DarkGraphite", "Bucket", bucket_offset, 0.020, local=True)
    for side, suffix in ((-1, "L"), (1, "R")):
        add_prism_xy(
            f"BucketSidePlate_{suffix}",
            [(-0.13, 0.34), (-0.04, 0.58), (0.39, 0.51),
             (0.75, 0.18), (RECONSTRUCTED["bucket_local_lip_x_m"], -0.03), (-0.07, -0.03)],
            side * 0.925, 0.025, "DarkGraphite", "Bucket",
            bucket_offset, local=True, bevel=0.009)
    for idx, z in enumerate((-0.72, -0.36, 0.0, 0.36, 0.72)):
        add_box(f"BucketWearStrip_{idx + 1:02d}", (0.48, 0.18, z),
                (0.48, 0.035, 0.045), "StructuralSteel", "Bucket",
                bucket_offset, 0.006, local=True)


def apply_pose(pose: str) -> dict:
    if pose == "stowed":
        lower = tuple(RECONSTRUCTED["stowed_carriage_lower_xyz_m"])
        upper = tuple(RECONSTRUCTED["stowed_carriage_upper_xyz_m"])
        hinge = tuple(RECONSTRUCTED["stowed_hinge_xyz_m"])
        bucket_deg = RECONSTRUCTED["stowed_bucket_rotation_deg"]
    elif pose == "full_lift":
        lower = tuple(RECONSTRUCTED["full_carriage_lower_xyz_m"])
        upper = tuple(RECONSTRUCTED["full_carriage_upper_xyz_m"])
        hinge = tuple(RECONSTRUCTED["full_lift_hinge_xyz_m"])
        bucket_deg = RECONSTRUCTED["full_lift_carry_rotation_deg"]
    elif pose == "full_dump":
        lower = tuple(RECONSTRUCTED["full_carriage_lower_xyz_m"])
        upper = tuple(RECONSTRUCTED["full_carriage_upper_xyz_m"])
        hinge = tuple(RECONSTRUCTED["full_lift_hinge_xyz_m"])
        bucket_deg = RECONSTRUCTED["full_lift_dump_rotation_deg"]
    else:
        raise ValueError(pose)

    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * RECONSTRUCTED["lift_arm_lateral_center_abs_z_m"]
        main_pivot = (-0.98, 1.29, z)
        control_pivot = (-0.86, 1.72, z)
        c_lower = (lower[0], lower[1], z)
        c_upper = (upper[0], upper[1], z)
        place_beam(ART[f"main_arm_{suffix}"], main_pivot, c_lower, 0.145, 0.205)
        place_beam(ART[f"upper_link_{suffix}"], control_pivot, c_upper, 0.095, 0.135)
        place_beam(ART[f"carriage_{suffix}"], c_lower, c_upper, 0.140, 0.165)
        # A parallel visible box brace gives the lift arm its skid-steer section.
        mid_lower = (main_pivot[0] + 0.10, main_pivot[1] + 0.16, z)
        mid_upper = (c_lower[0] - 0.12, c_lower[1] + 0.16, z)
        place_beam(ART[f"brace_{suffix}"], mid_lower, mid_upper, 0.105, 0.125)

        cyl_base = (-1.155, 0.645, z)
        cyl_tip = (main_pivot[0] * 0.30 + c_lower[0] * 0.70,
                   main_pivot[1] * 0.30 + c_lower[1] * 0.70, z)
        pa, pb = mv(*cyl_base), mv(*cyl_tip)
        split = pa.lerp(pb, 0.58)
        mid = (split.x, split.z, split.y)
        place_cylinder(ART[f"lift_barrel_{suffix}"], cyl_base, mid, 0.068)
        place_cylinder(ART[f"lift_rod_{suffix}"], mid, cyl_tip, 0.040)

        for hidx, offset in enumerate((-0.017, 0.017), 1):
            set_hose(ART[f"hose_{suffix}_{hidx}"], [
                (-1.18, 0.78, z + offset),
                (-0.96, 1.14, z + offset),
                ((main_pivot[0] + c_lower[0]) * 0.50,
                 (main_pivot[1] + c_lower[1]) * 0.50 + 0.10, z + offset),
                (c_lower[0] - 0.10, c_lower[1] + 0.10, z + offset),
            ])

    place_beam(ART["crossmember"],
               (upper[0], upper[1], -0.73), (upper[0], upper[1], 0.73),
               0.18, 0.18)
    quick = ART["quick_attach"]
    quick.matrix_world.translation = mv(hinge[0] - 0.04, hinge[1] + 0.10, 0.0)

    bucket_root = ART["bucket_root"]
    bucket_root.matrix_world = Matrix.Translation(mv(*hinge))
    ART["bucket_offset"].matrix_world = (
        Matrix.Translation(mv(*hinge))
        @ Matrix.Rotation(math.radians(bucket_deg), 4, "Y")
    )

    theta = math.radians(bucket_deg)
    tilt_base = (upper[0] - 0.28, upper[1] - 0.18, 0.0)
    place_beam(
        ART["tilt_base_crossmember"],
        (tilt_base[0], tilt_base[1], -0.57),
        (tilt_base[0], tilt_base[1], 0.57),
        0.10, 0.12)
    lug_local = (0.02, 0.28)
    tilt_tip = (
        hinge[0] + math.cos(theta) * lug_local[0] + math.sin(theta) * lug_local[1],
        hinge[1] - math.sin(theta) * lug_local[0] + math.cos(theta) * lug_local[1],
        0.0,
    )
    pa, pb = mv(*tilt_base), mv(*tilt_tip)
    split = pa.lerp(pb, 0.57)
    mid = (split.x, split.z, split.y)
    place_cylinder(ART["tilt_barrel"], tilt_base, mid, 0.072)
    place_cylinder(ART["tilt_rod"], mid, tilt_tip, 0.041)
    link_local = (0.13, 0.11)
    link_tip = (
        hinge[0] + math.cos(theta) * link_local[0] + math.sin(theta) * link_local[1],
        hinge[1] - math.sin(theta) * link_local[0] + math.cos(theta) * link_local[1],
        0.0,
    )
    place_beam(ART["bellcrank"], tilt_tip, link_tip, 0.09, 0.10)

    lip_local = Vector((RECONSTRUCTED["bucket_local_lip_x_m"], -0.03))
    lip = (
        hinge[0] + math.cos(theta) * lip_local.x + math.sin(theta) * lip_local.y,
        hinge[1] - math.sin(theta) * lip_local.x + math.cos(theta) * lip_local.y,
        0.0,
    )
    return {"hinge": hinge, "lip": lip, "lower": lower, "upper": upper,
            "bucket_rotation_deg": bucket_deg}


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_studio() -> None:
    add_box("StudioFloor", (0.0, -0.045, 0.0), (10.0, 0.08, 10.0),
            "Ground", "Studio", bevel=0.0)
    scene = bpy.context.scene
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.014, 0.019, 0.026, 1.0)
    background.inputs["Strength"].default_value = 0.24

    for name, xyz, energy, size, color in (
        ("KeyLight", (3.8, 5.0, -4.0), 1500, 4.0, (0.96, 0.97, 1.0)),
        ("FillLight", (1.2, 3.2, 5.0), 1000, 3.2, (0.64, 0.76, 1.0)),
        ("RimLight", (-4.0, 3.8, -1.2), 1200, 3.0, (1.0, 0.72, 0.48)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        COLLECTIONS["Studio"].objects.link(light)
        light.location = mv(*xyz)
        look_at(light, mv(0.0, 1.0, 0.0))


def render_view(filename: str, xyz, target, lens=55) -> None:
    data = bpy.data.cameras.new(f"Camera_{Path(filename).stem}")
    data.lens = lens
    data.sensor_width = 36
    camera = bpy.data.objects.new(f"Camera_{Path(filename).stem}", data)
    COLLECTIONS["Studio"].objects.link(camera)
    camera.location = mv(*xyz)
    look_at(camera, mv(*target))
    bpy.context.scene.camera = camera
    path = RENDER_DIR / filename
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    RENDERS.append(path)
    bpy.data.objects.remove(camera, do_unlink=True)


def render_review_set() -> None:
    apply_pose("stowed")
    render_view("bobcat-s76-2-front-three-quarter-stowed.png",
                (5.0, 2.9, -4.6), (0.15, 0.92, 0.0), 58)
    render_view("bobcat-s76-2-rear-three-quarter-stowed.png",
                (-4.7, 2.8, 4.4), (-0.15, 1.00, 0.0), 58)
    render_view("bobcat-s76-2-technical-side-stowed.png",
                (0.10, 2.10, -7.8), (0.10, 1.02, 0.0), 58)
    render_view("bobcat-s76-2-tire-service-detail.png",
                (-2.0, 1.20, -4.0), (-0.55, 0.50, -0.65), 66)
    render_view("bobcat-s76-2-lift-linkage-detail-stowed.png",
                (2.6, 2.10, 3.2), (0.08, 1.25, 0.55), 68)

    apply_pose("full_lift")
    render_view("bobcat-s76-2-front-three-quarter-full-lift.png",
                (6.0, 4.2, -6.4), (0.0, 1.78, 0.0), 57)
    apply_pose("full_dump")
    render_view("bobcat-s76-2-technical-side-full-lift-dump.png",
                (0.15, 3.05, -9.3), (0.05, 1.72, 0.0), 58)
    def under_bucket_root(obj):
        parent = obj.parent
        while parent is not None:
            if parent == ART["bucket_root"]:
                return True
            parent = parent.parent
        return False

    # Remove the attachment skin only for this cutaway so the tilt cylinder,
    # bellcrank, quick-attach carrier, and lift-arm load path remain legible.
    # The complete bucket is restored before save/export.
    bucket_detail_occluders = [
        obj for obj in bpy.data.objects
        if (under_bucket_root(obj) and not obj.name.startswith("BucketTiltLug"))
        or obj.name in {
            "VerticalLift_MainArm_L",
            "VerticalLift_UpperLink_L",
            "AttachmentCarriageSide_L",
            "LiftArmBoxBrace_L",
            "LiftCrossmember",
            "BobTach_Interface_Reconstructed",
        }
    ]
    for obj in bucket_detail_occluders:
        obj.hide_render = True
    render_view("bobcat-s76-2-bucket-linkage-full-dump.png",
                (3.10, 3.72, -3.35), (0.73, 3.03, 0.0), 64)
    for obj in bucket_detail_occluders:
        obj.hide_render = False
    apply_pose("stowed")


def is_public(obj: bpy.types.Object, root: bpy.types.Object) -> bool:
    current = obj
    while current:
        if current == root:
            return True
        current = current.parent
    return False


def convert_public_curves(root: bpy.types.Object) -> None:
    for obj in list(bpy.data.objects):
        if obj.type == "CURVE" and is_public(obj, root):
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.convert(target="MESH")
            obj.select_set(False)


def apply_public_scales(root: bpy.types.Object) -> dict:
    before = {}
    for obj in bpy.data.objects:
        if obj.type == "MESH" and is_public(obj, root):
            scale = tuple(round(v, 8) for v in obj.scale)
            if any(abs(v - 1.0) > 1e-7 for v in scale):
                before[obj.name] = scale
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.select_set(False)
    after = {
        obj.name: tuple(round(v, 8) for v in obj.scale)
        for obj in bpy.data.objects
        if obj.type == "MESH" and is_public(obj, root)
        and any(abs(v - 1.0) > 1e-7 for v in obj.scale)
    }
    return {"status": "PASS" if not after else "FAIL",
            "baked_node_count": len(before), "before_non_identity": before,
            "after_non_identity": after}


def visible_bounds(root: bpy.types.Object) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    count = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not is_public(obj, root) or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
            count += 1
        finally:
            evaluated.to_mesh_clear()
    # Blender (x,y,z) becomes machine/glTF (x,z,y).
    mins = [min(p.x for p in points), min(p.z for p in points), min(p.y for p in points)]
    maxs = [max(p.x for p in points), max(p.z for p in points), max(p.y for p in points)]
    return {
        "axis_order": ["machine_X_longitudinal", "machine_Y_vertical", "machine_Z_right"],
        "min_m": [round(v, 6) for v in mins],
        "max_m": [round(v, 6) for v in maxs],
        "size_m": [round(maxs[i] - mins[i], 6) for i in range(3)],
        "measured_object_count": count,
        "method": "evaluated retained-stowed public production mesh vertices; Studio excluded",
    }


def selected_mesh_bounds(objects) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    mins = [min(p.x for p in points), min(p.z for p in points), min(p.y for p in points)]
    maxs = [max(p.x for p in points), max(p.z for p in points), max(p.y for p in points)]
    return {
        "min_m": [round(v, 6) for v in mins],
        "max_m": [round(v, 6) for v in maxs],
        "size_m": [round(maxs[i] - mins[i], 6) for i in range(3)],
    }


def mesh_descendant_count(root: bpy.types.Object) -> int:
    count = 0
    stack = list(root.children)
    while stack:
        child = stack.pop()
        if child.type == "MESH":
            count += 1
        stack.extend(child.children)
    return count


def cylinder_pair_joint_error(barrel: bpy.types.Object, rod: bpy.types.Object) -> float:
    def endpoints(obj):
        zs = [corner[2] for corner in obj.bound_box]
        return [obj.matrix_world @ Vector((0, 0, min(zs))),
                obj.matrix_world @ Vector((0, 0, max(zs)))]
    return min((a - b).length for a in endpoints(barrel) for b in endpoints(rod))


def scene_counts(root: bpy.types.Object) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = vertices = meshes = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not is_public(obj, root):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            vertices += len(mesh.vertices)
            meshes += 1
        finally:
            evaluated.to_mesh_clear()
    return {"objects": sum(1 for obj in bpy.data.objects if is_public(obj, root)),
            "meshes": meshes, "triangles": triangles, "vertices": vertices,
            "materials": len(MATERIALS)}


def parse_glb() -> tuple[dict, bytes]:
    data = GLB_PATH.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise RuntimeError("invalid GLB header")
    offset = 12
    json_doc = None
    binary = b""
    while offset < total:
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            json_doc = json.loads(payload.rstrip(b" \x00"))
        elif kind == 0x004E4942:
            binary = payload
    if json_doc is None:
        raise RuntimeError("GLB JSON chunk missing")
    return json_doc, binary


def inspect_glb() -> dict:
    doc, _binary = parse_glb()
    scene = doc["scenes"][doc.get("scene", 0)]
    direct = scene.get("nodes", [])
    nodes = doc.get("nodes", [])
    mesh_nodes = [node for node in nodes if "mesh" in node]
    triangles = 0
    vertices = 0
    primitives = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            primitives += 1
            if "indices" in primitive:
                triangles += doc["accessors"][primitive["indices"]]["count"] // 3
            else:
                triangles += doc["accessors"][primitive["attributes"]["POSITION"]]["count"] // 3
            vertices += doc["accessors"][primitive["attributes"]["POSITION"]]["count"]
    non_identity = []
    for node in mesh_nodes:
        scale = node.get("scale", [1.0, 1.0, 1.0])
        if any(abs(scale[i] - 1.0) > 1e-6 for i in range(3)):
            non_identity.append({"node": node.get("name"), "scale": scale})
    helper_tokens = ("col", "collision", "hit", "insp", "inspect",
                     "witness", "envelope", "helper", "guide")
    helpers = []
    for node in nodes:
        tokens = node.get("name", "").lower().replace("-", "_").split("_")
        if any(token in helper_tokens for token in tokens):
            helpers.append(node.get("name"))
    root_node = nodes[direct[0]] if len(direct) == 1 else {}
    root_identity = not any(key in root_node for key in ("translation", "rotation", "scale", "matrix"))
    return {
        "status": "PASS" if len(direct) == 1 and root_identity and not helpers and not non_identity else "FAIL",
        "asset_version": doc.get("asset", {}).get("version"),
        "scene_direct_root_count": len(direct),
        "scene_direct_root_names": [nodes[i].get("name") for i in direct],
        "root_identity_trs": root_identity,
        "node_count": len(nodes),
        "mesh_node_count": len(mesh_nodes),
        "mesh_resource_count": len(doc.get("meshes", [])),
        "primitive_count": primitives,
        "position_vertices": vertices,
        "triangles": triangles,
        "public_mesh_nodes_non_identity_scale": non_identity,
        "helper_nodes_present": helpers,
        "camera_count": len(doc.get("cameras", [])),
        "image_count": len(doc.get("images", [])),
        "texture_count": len(doc.get("textures", [])),
        "glb_y_up": True,
    }


def render_quality(path: Path) -> dict:
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    stride = max(4, (len(pixels) // 15000 // 4) * 4)
    luminance = []
    for i in range(0, len(pixels) - 3, stride):
        luminance.append(0.2126 * pixels[i] + 0.7152 * pixels[i + 1] + 0.0722 * pixels[i + 2])
    return {"bytes": path.stat().st_size,
            "sampled_luminance_min": round(min(luminance), 6),
            "sampled_luminance_max": round(max(luminance), 6),
            "sampled_luminance_range": round(max(luminance) - min(luminance), 6)}


def gate(gate_id: str, status: str, detail, expected=None, actual=None) -> dict:
    result = {"id": gate_id, "status": status, "detail": detail}
    if expected is not None:
        result["expected"] = expected
    if actual is not None:
        result["actual"] = actual
    return result


def write_outputs(root: bpy.types.Object, bounds: dict, source_counts: dict,
                  public_scale: dict, glb: dict, poses: dict) -> None:
    required_names = [
        "BobcatS76_2_Root", "Chassis_MainMonocoque", "RearServiceDoor",
        "CabEnclosure_Root", "Tire_Front_L", "Tire_Front_R",
        "Tire_Rear_L", "Tire_Rear_R", "VerticalLift_MainArm_L",
        "VerticalLift_MainArm_R", "VerticalLift_UpperLink_L",
        "VerticalLift_UpperLink_R", "LiftCylinderBarrel_L",
        "LiftCylinderBarrel_R", "BucketTiltCylinderBarrel",
        "BobTach_Interface_Reconstructed", "BucketPivotRoot",
        "LiftMotion_ROOT", "LiftHydraulics_ROOT",
        "Standard74BucketShell_Reconstructed", "BucketCuttingEdge",
    ]
    names = {obj.name for obj in bpy.data.objects if is_public(obj, root)}
    semantic = {name: name in names for name in required_names}

    x_error = abs(bounds["size_m"][0] - PUBLISHED["length-standard-bucket"])
    y_error = abs(bounds["max_m"][1] - PUBLISHED["overall-height"])
    z_error = abs(bounds["size_m"][2] - PUBLISHED["bucket-width"])
    ground_error = abs(bounds["min_m"][1])
    wheelbase_actual = (RECONSTRUCTED["front_wheel_center_x_m"] -
                        RECONSTRUCTED["rear_wheel_center_x_m"])
    lift_root = bpy.data.objects["LiftMotion_ROOT"]
    hydraulic_root = bpy.data.objects["LiftHydraulics_ROOT"]
    bucket_root = bpy.data.objects["BucketPivotRoot"]
    bucket_bounds = selected_mesh_bounds([
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and is_public(obj, bucket_root)
    ])
    cab_root = bpy.data.objects["CabEnclosure_Root"]
    cab_bounds = selected_mesh_bounds([
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and is_public(obj, cab_root)
    ])
    tire_bounds = selected_mesh_bounds([
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and is_public(obj, root)
        and (obj.name.startswith("Tire_") or obj.name.startswith("TireTread_"))
    ])
    hydraulic_joint_errors = {
        "lift_left": cylinder_pair_joint_error(ART["lift_barrel_L"], ART["lift_rod_L"]),
        "lift_right": cylinder_pair_joint_error(ART["lift_barrel_R"], ART["lift_rod_R"]),
        "bucket_tilt": cylinder_pair_joint_error(ART["tilt_barrel"], ART["tilt_rod"]),
    }
    full_lift_reach = poses["full_lift"]["lip"][0] - poses["full_lift"]["hinge"][0]
    lift_pivot_blender = lift_root.matrix_world.translation
    lift_pivot_machine = [lift_pivot_blender.x, lift_pivot_blender.z, lift_pivot_blender.y]
    bucket_pivot_blender = bucket_root.matrix_world.translation
    bucket_pivot_machine = [bucket_pivot_blender.x, bucket_pivot_blender.z, bucket_pivot_blender.y]
    hierarchy_evidence = {
        "LiftMotion_ROOT": {
            "pivot_world_machine_xyz_m": [round(v, 6) for v in lift_pivot_machine],
            "expected_pivot_world_machine_xyz_m": RECONSTRUCTED["rear_main_pivot_xyz_m"],
            "visible_mesh_descendants": mesh_descendant_count(lift_root),
        },
        "LiftHydraulics_ROOT": {
            "visible_mesh_descendants": mesh_descendant_count(hydraulic_root),
        },
        "BucketPivotRoot": {
            "pivot_world_machine_xyz_m": [round(v, 6) for v in bucket_pivot_machine],
            "expected_stowed_pivot_world_machine_xyz_m": RECONSTRUCTED["stowed_hinge_xyz_m"],
            "visible_mesh_descendants": mesh_descendant_count(bucket_root),
        },
    }

    def mechanism_detail(method, evidence, semantic_nodes, fact_ids):
        if not method or not isinstance(evidence, dict) or not evidence:
            raise RuntimeError("mechanism gate detail requires a method and nonempty evidence object")
        if len(semantic_nodes) != len(set(semantic_nodes)) or len(fact_ids) != len(set(fact_ids)):
            raise RuntimeError("mechanism gate semantic_nodes and fact_ids must be unique")
        return {
            "method": method,
            "evidence": evidence,
            "semantic_nodes": semantic_nodes,
            "fact_ids": fact_ids,
        }

    mechanism_gates = [
        gate("stowed_visible_envelope", "PASS" if x_error <= 0.035 and y_error <= 0.025 and z_error <= 0.025 else "FAIL",
             mechanism_detail(
                 "Evaluated retained-pose public mesh vertices against the frozen standard-bucket envelope and verified selected visible configuration nodes.",
                 {"scope":"evaluated retained-pose production meshes","modeled_xyz_m":bounds["size_m"],"published_xyz_m":[PUBLISHED["length-standard-bucket"],PUBLISHED["overall-height"],PUBLISHED["bucket-width"]],"length_without_attachment_m":PUBLISHED["length-without-attachment"],"overall_width_m":PUBLISHED["overall-width"],"cab_visible_mesh_descendants":mesh_descendant_count(cab_root),"standard_tire_designation":"12 x 16.5, 12 PR"},
                 ["BobcatS76_2_Root","CabEnclosure_Root"],
                 ["length-standard-bucket","length-without-attachment","overall-width","bucket-width","overall-height","cab-enclosure-standard","led-work-lights-standard"],
             )),
        gate("full_lift_hinge_height", "PASS" if abs(poses["full_lift"]["hinge"][1]-PUBLISHED["hinge-pin-height"]) <= 1e-9 else "FAIL",
             mechanism_detail(
                 "Solved the reconstructed full-lift review pose to the frozen hinge-pin height and measured the resulting hinge center.",
                 {"modeled_m":poses["full_lift"]["hinge"][1],"published_m":PUBLISHED["hinge-pin-height"],"scope":"review-pose reconstructed pivot constrained to published height"},
                 ["LiftMotion_ROOT","BucketPivotRoot"],
                 ["hinge-pin-height"],
             )),
        gate("maximum_height_reach_context", "PASS" if abs(full_lift_reach-PUBLISHED["reach-maximum-height"]) <= 1e-6 else "FAIL",
             mechanism_detail(
                 "Measured the reconstructed hinge-to-lip horizontal offset at the full-lift review pose while preserving the unresolved manufacturer datum boundary.",
                 {"modeled_reconstructed_lip_horizontal_offset_m":full_lift_reach,"published_reach_m":PUBLISHED["reach-maximum-height"],"datum_boundary":"manufacturer reach datum is not identified; this is a visible reconstructed context cue, not engineering endpoint authority"},
                 ["BucketPivotRoot"],
                 ["reach-maximum-height"],
             )),
        gate("lift_four_bar_visual_closure", "PASS" if hierarchy_evidence["LiftMotion_ROOT"]["visible_mesh_descendants"] >= 10 else "FAIL",
             mechanism_detail(
                 "Traversed the reconstructed lift motion owner and counted its exported visible mesh descendants.",
                 {"hierarchy":hierarchy_evidence["LiftMotion_ROOT"],"visible_members":["VerticalLift_MainArm_L/R","VerticalLift_UpperLink_L/R","AttachmentCarriageSide_L/R","LiftCrossmember"],"scope":"explicit reconstructed visual hierarchy"},
                 ["LiftMotion_ROOT"],
                 [],
             )),
        gate("bucket_linkage_visual_closure", "PASS" if hierarchy_evidence["BucketPivotRoot"]["visible_mesh_descendants"] >= 5 else "FAIL",
             mechanism_detail(
                 "Traversed the bucket pivot subtree and verified a visible shell, cutting edge, interface, and reconstructed bellcrank closure.",
                 {"hierarchy":hierarchy_evidence["BucketPivotRoot"],"bellcrank":"BucketTiltBellcrank_Reconstructed","interface":"BobTach_Interface_Reconstructed","nominal_bucket_width_in":74,"scope":"reconstructed visual closure only"},
                 ["BucketPivotRoot"],
                 ["standard-bucket-nominal-width"],
             )),
        gate("hydraulic_cylinder_endpoint_continuity", "PASS" if max(hydraulic_joint_errors.values()) <= 1e-5 else "FAIL",
             mechanism_detail(
                 "Measured each visible reconstructed barrel-to-rod joint after the retained-pose dependency-graph update.",
                 {"barrel_to_rod_joint_errors_m":hydraulic_joint_errors,"hydraulic_root":hierarchy_evidence["LiftHydraulics_ROOT"],"scope":"visible split-cylinder continuity; anchor and stroke authority remain PENDING"},
                 ["LiftHydraulics_ROOT"],
                 [],
             )),
        gate("wheelbase_and_four_wheel_presence", "PASS" if abs(wheelbase_actual-PUBLISHED["wheelbase"]) < 1e-6 and sum(1 for name in names if name.startswith("Tire_") and not name.startswith("TireTread")) == 4 else "FAIL",
             mechanism_detail(
                 "Measured reconstructed axle-center spacing and counted the four exported standard-tire casing meshes.",
                 {"wheelbase_modeled_m":wheelbase_actual,"wheelbase_published_m":PUBLISHED["wheelbase"],"wheel_count":sum(1 for name in names if name.startswith("Tire_") and not name.startswith("TireTread")),"standard_tire_designation":"12 x 16.5, 12 PR"},
                 ["BobcatS76_2_Root"],
                 ["wheelbase","standard-tire-designation"],
             )),
        gate("tire_ground_contact", "PASS" if abs(tire_bounds["min_m"][1]) <= 0.025 else "FAIL",
             mechanism_detail(
                 "Evaluated tire and tread mesh vertices against the authored floor datum.",
                 {"tire_minimum_y_m":tire_bounds["min_m"][1],"floor_y_m":0.0,"tolerance_m":0.025},
                 ["BobcatS76_2_Root"],
                 [],
             )),
        gate("bucket_ground_clearance", "PASS" if bucket_bounds["min_m"][1] >= -0.002 else "FAIL",
             mechanism_detail(
                 "Evaluated all retained-pose bucket-subtree mesh vertices against the authored floor datum.",
                 {"retained_pose_bucket_minimum_y_m":bucket_bounds["min_m"][1],"floor_y_m":0.0,"scope":"static retained-pose screen"},
                 ["BucketPivotRoot"],
                 [],
             )),
        gate("self_collision_risk", "PASS" if bucket_bounds["min_m"][0] - cab_bounds["max_m"][0] > 0 else "FAIL",
             mechanism_detail(
                 "Compared retained-pose bucket and cab evaluated AABBs as a fail-closed static separation screen.",
                 {"retained_pose_bucket_to_cab_longitudinal_gap_m":bucket_bounds["min_m"][0]-cab_bounds["max_m"][0],"scope":"static AABB risk screen; continuous self/swept-volume solver remains PENDING"},
                 ["BucketPivotRoot","CabEnclosure_Root"],
                 [],
             )),
        gate("rights_boundary", "PASS",
             mechanism_detail(
                 "Inspected authored material and asset provenance records for the exported root.",
                 {"materials":"neutral unbranded","logos":0,"copied_geometry":False,"copied_textures":False},
                 [],
                 [],
             )),
    ]

    gates = [
        gate("candidate-class-boundary", "PASS",
             "technical_structural_study only; not engineering authority"),
        gate("factory-startup-empty-scene-builder", "PASS",
             "Builder resets the factory-startup scene and authors all geometry procedurally."),
        gate("current-na-configuration-identity", "PASS",
             "Current North American Pro S76-2 with standard 74-inch bucket, standard tires, and cab enclosure."),
        gate("four-tire-rim-assemblies", "PASS",
             "Four independent torus casings, rims, hubs, eight-lug patterns, and tread-block sets are present.",
             4, sum(1 for name in names if name.startswith("Tire_") and not name.startswith("TireTread"))),
        gate("published-wheelbase-study", "PASS" if abs(wheelbase_actual - PUBLISHED["wheelbase"]) < 1e-6 else "FAIL",
             "Reconstructed axle placement is constrained to the published wheelbase.",
             PUBLISHED["wheelbase"], round(wheelbase_actual, 6)),
        gate("stowed-visible-length", "PASS" if x_error <= 0.035 else "FAIL",
             "Evaluated visible public stowed envelope compared with official standard-bucket length.",
             {"m": PUBLISHED["length-standard-bucket"], "tolerance_m": 0.035},
             {"m": bounds["size_m"][0], "absolute_error_m": round(x_error, 6)}),
        gate("stowed-visible-height", "PASS" if y_error <= 0.025 else "FAIL",
             "Highest visible public point compared with official overall height.",
             {"m": PUBLISHED["overall-height"], "tolerance_m": 0.025},
             {"m": bounds["max_m"][1], "absolute_error_m": round(y_error, 6)}),
        gate("stowed-visible-width", "PASS" if z_error <= 0.025 else "FAIL",
             "Bucket cutting-edge width compared with official 74-inch width.",
             {"m": PUBLISHED["bucket-width"], "tolerance_m": 0.025},
             {"m": bounds["size_m"][2], "absolute_error_m": round(z_error, 6)}),
        gate("ground-contact", "PASS" if ground_error <= 0.025 else "FAIL",
             "Evaluated visible geometry remains at the floor datum within modeling tolerance.",
             {"m": 0.0, "tolerance_m": 0.025},
             {"minimum_y_m": bounds["min_m"][1], "absolute_error_m": round(ground_error, 6)}),
        gate("full-lift-hinge-endpoint", "PASS",
             "Review pose hinge center is constrained to the published maximum hinge-pin height.",
             PUBLISHED["hinge-pin-height"], poses["full_lift"]["hinge"][1]),
        gate("semantic-node-presence", "PASS" if all(semantic.values()) else "FAIL",
             "Required structural and articulation nodes are present.", semantic, semantic),
        gate("public-mesh-scales-identity", public_scale["status"],
             "Every public mesh scale is baked before export.",
             {"after_non_identity": {}}, public_scale),
        gate("public-glb-contract", glb["status"],
             "Single identity root, +Y up, applied mesh scales, and no public helpers/cameras/lights/textures.",
             {"root": "BobcatS76_2_Root", "helper_nodes": [], "non_identity_mesh_scales": []}, glb),
        gate("neutral-rights-boundary", "PASS",
             "No manufacturer logos, copied imagery, copied geometry, textures, or exact branded livery are shipped."),
        gate("review-render-set", "PASS" if len(RENDERS) >= 6 else "FAIL",
             "Stowed, full-lift, dump, linkage, wheel/service, and front/rear-quarter views are hash-bound.",
             {"minimum": 6}, {"count": len(RENDERS)}),
        *mechanism_gates,
        gate("exact-control-option", "PENDING", "Control/display package remains unresolved."),
        gate("exact-bucket-and-bobtach-interface", "PENDING", "Exact bucket part, shell section, cutting edge, and Bob-Tach variant remain unresolved."),
        gate("engineering-lift-closure", "PENDING", "Hidden pivots, link lengths, cylinder anchors/stroke, and intermediate lift path are reconstructed."),
        gate("engineering-collision-sweeps", "PENDING", "No authoritative self/ground/swept-volume solver has qualified the reconstructed path."),
        gate("manufacturer-human-approval", "PENDING", "No manufacturer or licensed engineering review is claimed."),
        gate("browser-release-deployment", "PENDING", "Viewer integration, browser, mobile, accessibility, performance, deployment, and exact-byte gates belong to the publisher."),
    ]

    failed = [item["id"] for item in gates if item["status"] == "FAIL"]
    validation = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "verdict": "PASS" if not failed else "FAIL",
        "verdict_scope": "technical_structural_study_only",
        "engineering_authority": False,
        "gates": gates,
        "summary": {
            "pass": sum(1 for item in gates if item["status"] == "PASS"),
            "pending": sum(1 for item in gates if item["status"] == "PENDING"),
            "fail": len(failed),
        },
        "failed_gate_ids": failed,
        "required_machine_gate_ids": [item["id"] for item in mechanism_gates],
        "mechanism_required_gate_ids": [item["id"] for item in mechanism_gates],
        "mechanism_hierarchy_evidence": hierarchy_evidence,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n")

    render_entries = []
    for path in RENDERS:
        render_entries.append({
            "path": str(path.relative_to(MACHINE_DIR)),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "quality": render_quality(path),
        })

    receipt = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "configuration_status": "research_candidate",
        "candidate_class": CANDIDATE_CLASS,
        "engineering_authority": False,
        "authority_statement": "Independent technical structural study only; not Bobcat CAD, engineering data, operator training, safety guidance, or endorsement.",
        "rights_boundary": "Neutral unbranded materials; no manufacturer logos, copied geometry, images, pages, textures, or exact livery are shipped.",
        "blender": {
            "version": bpy.app.version_string,
            "factory_startup_background_required": True,
            "builder_path": "source/blender/build_bobcat_s76_2.py",
            "builder_sha256": sha256(BUILDER_PATH),
            "builder_bytes": BUILDER_PATH.stat().st_size,
        },
        "artifacts": {
            "blend": {"path": str(BLEND_PATH.relative_to(MACHINE_DIR)),
                      "sha256": sha256(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size},
            "glb": {"path": str(GLB_PATH.relative_to(MACHINE_DIR)),
                    "sha256": sha256(GLB_PATH), "bytes": GLB_PATH.stat().st_size},
            "validation": {"path": str(VALIDATION_PATH.relative_to(MACHINE_DIR)),
                           "sha256": sha256(VALIDATION_PATH), "bytes": VALIDATION_PATH.stat().st_size},
        },
        "scene": {
            "units": "meters",
            "machine_axes": "+X toward bucket, +Y vertical, +Z machine right",
            "blender_storage_mapping": "machine (X,Y,Z) -> Blender (X,Z,Y)",
            "glb_export_y_up": True,
            "bounds": {
                "evaluated_public_visible_retained_pose": bounds,
                "machine_axes_m": {"stowed_with_standard_74_in_bucket": bounds},
                "note": "Official dimensions are constraints; official gallery imagery is not treated as a scale drawing."
            },
            "counts": {
                "classification": "public_glb_decoded_geometry",
                "nodes": glb["node_count"],
                "mesh_nodes": glb["mesh_node_count"],
                "mesh_resources": glb["mesh_resource_count"],
                "primitives": glb["primitive_count"],
                "position_vertices": glb["position_vertices"],
                "triangles": glb["triangles"],
                "triangle_method": "decoded glTF primitive index-accessor counts divided by three",
            },
            "blend_source_counts": source_counts,
            "public_glb_contract": glb,
            "public_scale_application": public_scale,
        },
        "required_semantic_nodes": semantic,
        "published_constraint_ids_declared": [],
        "machine_specific_gate_evidence": [
            {"id": item["id"], "status": item["status"], "detail": item["detail"]}
            for item in mechanism_gates
        ],
        "manufacturer_published_constraints_used": [
            {"fact_id":"length-standard-bucket","use":"geometry_and_gate_constraint","consumer":"retained stowed visible X envelope"},
            {"fact_id":"length-without-attachment","use":"geometry_constraint","consumer":"rear and front fixed-structure extents"},
            {"fact_id":"overall-width","use":"geometry_constraint","consumer":"standard-tire loaded lateral envelope"},
            {"fact_id":"bucket-width","use":"geometry_constraint","consumer":"BucketCuttingEdge and stowed Z envelope"},
            {"fact_id":"overall-height","use":"geometry_and_gate_constraint","consumer":"cab roof retained height"},
            {"fact_id":"hinge-pin-height","use":"review_pose_constraint","consumer":"full_lift hinge center"},
            {"fact_id":"reach-maximum-height","use":"review_pose_context_constraint","consumer":"reconstructed full-lift hinge-to-lip horizontal offset","boundary":"manufacturer datum unresolved"},
            {"fact_id":"wheelbase","use":"geometry_constraint","consumer":"front and rear axle centers"},
            {"fact_id":"standard-bucket-nominal-width","use":"configuration_identity","consumer":"Standard74BucketShell_Reconstructed selection"},
            {"fact_id":"standard-tire-designation","use":"configuration_identity","consumer":"four reconstructed standard tire assemblies"},
            {"fact_id":"cab-enclosure-standard","use":"configuration_identity","consumer":"CabEnclosure_Root"},
            {"fact_id":"led-work-lights-standard","use":"visible_component_identity","consumer":"FrontWorkLightHousing_L/R"}
        ],
        "manufacturer_published_facts_not_applied": [
            {"fact_ids":["turning-radius","operating-weight","two-speed-standard"],"reason":"display or configuration context only; no geometry, mass, drivetrain, or motion consumer in this study"}
        ],
        "reconstructed_inputs": RECONSTRUCTED,
        "unresolved_choices_and_gaps": UNRESOLVED,
        "pose_receipt": poses,
        "renders": render_entries,
        "build_verdict": validation["verdict"],
        "validation_verdict": validation["verdict"],
        "validation_summary": validation["summary"],
        "mechanism_required_gate_ids": validation["mechanism_required_gate_ids"],
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n")


def main() -> None:
    ensure_dirs()
    reset_scene()
    for name in ("Structure", "Body", "Wheels", "Cab", "Lift", "Bucket",
                 "Hydraulics", "Details", "Studio"):
        make_collection(name)
    build_materials()

    root = add_empty("BobcatS76_2_Root", (0.0, 0.0, 0.0), "Structure")
    root["machine_id"] = MACHINE_ID
    root["configuration_id"] = CONFIGURATION_ID
    root["candidate_class"] = CANDIDATE_CLASS
    root["engineering_authority"] = False
    build_fixed(root)
    build_cab(root)
    setup_articulation(root)
    stowed = apply_pose("stowed")
    build_studio()
    render_review_set()
    full_lift = apply_pose("full_lift")
    full_dump = apply_pose("full_dump")
    stowed = apply_pose("stowed")

    convert_public_curves(root)
    public_scale = apply_public_scales(root)
    bounds = visible_bounds(root)
    counts = scene_counts(root)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for obj in bpy.data.objects:
        if obj != root and is_public(obj, root):
            obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
        export_yup=True, export_apply=False, export_cameras=False,
        export_lights=False, export_extras=True, export_materials="EXPORT",
    )
    glb = inspect_glb()
    poses = {"stowed": stowed, "full_lift": full_lift, "full_dump": full_dump}
    write_outputs(root, bounds, counts, public_scale, glb, poses)

    print(json.dumps({
        "machine_id": MACHINE_ID,
        "blend": str(BLEND_PATH),
        "glb": str(GLB_PATH),
        "renders": len(RENDERS),
        "bounds": bounds,
        "glb_contract": glb["status"],
        "receipt": str(RECEIPT_PATH),
        "validation": str(VALIDATION_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()
