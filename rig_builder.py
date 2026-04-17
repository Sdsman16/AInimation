"""
Automatic Dinosaur Rig Builder

Build bone structure for dinosaur models based on mesh analysis.
Supports bipedal (raptor/T-Rex style) and quadrupedal (sauropod style).
"""
import bpy
from mathutils import Vector, Euler, Matrix
from typing import Dict, List, Optional, Tuple
from .mesh_analyzer import DinoMeshAnalysis, BodySegment


class DinoRigBuilder:
    """Build dinosaur rig based on mesh analysis."""

    def __init__(self, mesh_obj: bpy.types.Object, analysis: DinoMeshAnalysis):
        self.mesh = mesh_obj
        self.analysis = analysis
        self.armature = None
        self.bone_positions = {}
        self.created_bones = []

    def build_rig(self, rig_name: str = "DinoRig") -> bpy.types.Object:
        """Main entry point - build complete rig."""

        # Create armature
        arm_data = bpy.data.armatures.new(name=rig_name)
        self.armature = bpy.data.objects.new(name=rig_name, object_data=arm_data)
        bpy.context.scene.collection.objects.link(self.armature)

        # Enter edit mode to create bones
        bpy.context.view_layer.objects.active = self.armature
        bpy.ops.object.mode_set(mode='EDIT')

        if self.analysis.detected_type == "bipedal":
            self._build_bipedal_rig()
        elif self.analysis.detected_type == "quadrupedal":
            self._build_quadrupedal_rig()
        else:
            # Fallback to basic rig
            self._build_basic_rig()

        # Create parent relationships
        self._create_parenting()

        # Exit edit mode
        bpy.ops.object.mode_set(mode='OBJECT')

        return self.armature

    def _build_bipedal_rig(self):
        """Build bipedal rig (raptor/T-Rex style)."""
        # Get mesh bounds
        bounds = self._get_mesh_bounds()

        # Spine chain (main axis)
        spine_count = 5
        spine_length = bounds['length'] * 0.6
        spine_start = bounds['front'] * 0.35  # Start behind head

        for i in range(spine_count):
            y_pos = spine_start + (i / (spine_count - 1)) * spine_length
            z_pos = bounds['center_z'] + bounds['height'] * 0.4
            x_pos = bounds['center_x']

            bone_name = f"spine_{i:02d}" if i > 0 else "spine_01"
            self._create_bone(bone_name, (x_pos, y_pos, z_pos), length=bounds['length'] * 0.15)

        # Pelvis / hip area
        hip_y = bounds['back'] * 0.7
        hip_z = bounds['center_z'] + bounds['height'] * 0.3
        self._create_bone("pelvis", (bounds['center_x'], hip_y, hip_z),
                         length=bounds['length'] * 0.2)

        # Tail chain
        tail_count = 8
        tail_length = abs(bounds['back'] - bounds['front']) * 0.35
        tail_start = bounds['back'] * 0.85

        for i in range(tail_count):
            y_pos = tail_start - (i / (tail_count - 1)) * tail_length
            z_pos = bounds['center_z'] + bounds['height'] * 0.25 - (i * bounds['height'] * 0.03)
            # Taper tail (z extent decreases)
            z_extent = bounds['height'] * (1 - i / tail_count * 0.7)

            bone_name = f"tail_{i:02d}" if i > 0 else "tail_01"
            self._create_bone(bone_name, (bounds['center_x'], y_pos, z_pos),
                             length=tail_length / tail_count * 1.5)

        # Back leg (thigh + shin + foot)
        leg_y = hip_y
        leg_z = bounds['bottom'] + bounds['height'] * 0.35

        # Thigh
        thigh_len = bounds['height'] * 0.4
        self._create_bone("thigh.R", (bounds['center_x'] + bounds['width'] * 0.4, leg_y, leg_z),
                         length=thigh_len, roll=0)

        # Shin
        shin_len = bounds['height'] * 0.35
        shin_z = bounds['bottom'] + shin_len * 0.9
        self._create_bone("shin.R", (bounds['center_x'] + bounds['width'] * 0.4, leg_y, shin_z),
                         length=shin_len)

        # Foot
        foot_z = bounds['bottom']
        self._create_bone("foot.R", (bounds['center_x'] + bounds['width'] * 0.5, leg_y + thigh_len * 0.2, foot_z),
                         length=thigh_len * 0.4)

        # Mirror to left side
        self._mirror_bone("thigh.R", "thigh.L")
        self._mirror_bone("shin.R", "shin.L")
        self._mirror_bone("foot.R", "foot.L")

        # Neck and head
        neck_count = 3
        neck_start = bounds['front'] * 0.25
        neck_length = bounds['front'] * 0.2

        for i in range(neck_count):
            y_pos = neck_start - i * neck_length / neck_count
            z_pos = bounds['center_z'] + bounds['height'] * 0.5 + i * bounds['height'] * 0.05
            bone_name = f"neck_{i:02d}" if i > 0 else "neck_01"
            self._create_bone(bone_name, (bounds['center_x'], y_pos, z_pos),
                             length=neck_length / neck_count * 1.3)

        # Head
        head_y = bounds['front'] * 0.95
        head_z = bounds['center_z'] + bounds['height'] * 0.6
        self._create_bone("head", (bounds['center_x'], head_y, head_z),
                         length=bounds['height'] * 0.5)

        # Jaw (if applicable)
        jaw_y = bounds['front'] * 0.9
        self._create_bone("jaw", (bounds['center_x'], jaw_y, head_z - bounds['height'] * 0.15),
                         length=bounds['height'] * 0.25)

        # Small arms (if bipedal raptor style)
        arm_y = spine_start + bounds['length'] * 0.05
        arm_z = bounds['center_z'] + bounds['height'] * 0.35

        self._create_bone("upper_arm.R", (bounds['center_x'] + bounds['width'] * 0.35, arm_y, arm_z),
                         length=bounds['height'] * 0.12)
        self._create_bone("forearm.R", (bounds['center_x'] + bounds['width'] * 0.4, arm_y - 0.05, arm_z - 0.05),
                         length=bounds['height'] * 0.1)
        self._mirror_bone("upper_arm.R", "upper_arm.L")
        self._mirror_bone("forearm.R", "forearm.L")

    def _build_quadrupedal_rig(self):
        """Build quadrupedal rig (sauropod style)."""
        bounds = self._get_mesh_bounds()

        # Long spine
        spine_count = 7
        spine_length = bounds['length'] * 0.75
        spine_start = bounds['front'] * 0.4

        for i in range(spine_count):
            y_pos = spine_start + (i / (spine_count - 1)) * spine_length
            z_pos = bounds['center_z'] + bounds['height'] * 0.55 + (i * bounds['height'] * 0.02)

            bone_name = f"spine_{i:02d}" if i > 0 else "spine_01"
            self._create_bone(bone_name, (bounds['center_x'], y_pos, z_pos),
                             length=spine_length / spine_count * 1.5)

        # Very long neck
        neck_count = 5
        neck_length = bounds['front'] * 0.35
        neck_start = bounds['front'] * 0.3

        for i in range(neck_count):
            y_pos = neck_start - i * neck_length / neck_count
            z_pos = bounds['center_z'] + bounds['height'] * 0.65 + i * bounds['height'] * 0.08
            bone_name = f"neck_{i:02d}" if i > 0 else "neck_01"
            self._create_bone(bone_name, (bounds['center_x'], y_pos, z_pos),
                             length=neck_length / neck_count * 1.2)

        # Head
        head_y = bounds['front'] * 0.9
        head_z = bounds['center_z'] + bounds['height'] * 0.9
        self._create_bone("head", (bounds['center_x'], head_y, head_z),
                         length=bounds['height'] * 0.35)

        # Long tail
        tail_count = 10
        tail_length = abs(bounds['back'] - bounds['front']) * 0.4
        tail_start = bounds['back'] * 0.8

        for i in range(tail_count):
            y_pos = tail_start - (i / (tail_count - 1)) * tail_length
            z_pos = bounds['center_z'] + bounds['height'] * 0.4 - i * bounds['height'] * 0.02

            bone_name = f"tail_{i:02d}" if i > 0 else "tail_01"
            self._create_bone(bone_name, (bounds['center_x'], y_pos, z_pos),
                             length=tail_length / tail_count * 1.3)

        # Front legs (2 pairs)
        front_leg_y = bounds['front'] * 0.15
        front_leg_z = bounds['bottom'] + bounds['height'] * 0.35

        self._create_bone("front_leg.R.upper", (bounds['center_x'] + bounds['width'] * 0.5, front_leg_y, front_leg_z),
                         length=bounds['height'] * 0.3)
        self._create_bone("front_leg.R.lower", (bounds['center_x'] + bounds['width'] * 0.5, front_leg_y - 0.05, front_leg_z - bounds['height'] * 0.25),
                         length=bounds['height'] * 0.28)
        self._create_bone("front_leg.R.foot", (bounds['center_x'] + bounds['width'] * 0.55, front_leg_y + 0.1, bounds['bottom']),
                         length=bounds['height'] * 0.15)

        self._mirror_bone("front_leg.R.upper", "front_leg.L.upper")
        self._mirror_bone("front_leg.R.lower", "front_leg.L.lower")
        self._mirror_bone("front_leg.R.foot", "front_leg.L.foot")

        # Back legs
        back_leg_y = bounds['back'] * 0.7
        back_leg_z = bounds['bottom'] + bounds['height'] * 0.35

        self._create_bone("back_leg.R.upper", (bounds['center_x'] + bounds['width'] * 0.5, back_leg_y, back_leg_z),
                         length=bounds['height'] * 0.35)
        self._create_bone("back_leg.R.lower", (bounds['center_x'] + bounds['width'] * 0.5, back_leg_y - 0.05, back_leg_z - bounds['height'] * 0.28),
                         length=bounds['height'] * 0.32)
        self._create_bone("back_leg.R.foot", (bounds['center_x'] + bounds['width'] * 0.55, back_leg_y + 0.1, bounds['bottom']),
                         length=bounds['height'] * 0.15)

        self._mirror_bone("back_leg.R.upper", "back_leg.L.upper")
        self._mirror_bone("back_leg.R.lower", "back_leg.L.lower")
        self._mirror_bone("back_leg.R.foot", "back_leg.L.foot")

    def _build_basic_rig(self):
        """Build basic fallback rig."""
        bounds = self._get_mesh_bounds()

        # Simple spine chain
        spine_count = 4
        for i in range(spine_count):
            y_pos = bounds['front'] * 0.3 + i * (bounds['back'] - bounds['front']) / spine_count
            z_pos = bounds['center_z'] + bounds['height'] * 0.45
            bone_name = f"bone_{i:02d}"
            self._create_bone(bone_name, (bounds['center_x'], y_pos, z_pos),
                             length=bounds['length'] * 0.15)

        # Head
        self._create_bone("head", (bounds['center_x'], bounds['front'] * 0.9, bounds['center_z'] + bounds['height'] * 0.55),
                         length=bounds['height'] * 0.3)

    def _create_bone(self, name: str, head_pos: Tuple, length: float = 0.1, roll: float = 0):
        """Create a bone at position."""
        edit_bones = self.armature.data.edit_bones
        bone = edit_bones.new(name=name)
        bone.head = Vector(head_pos)
        bone.tail = Vector(head_pos) + Vector((0, length, 0))
        bone.roll = roll

        self.bone_positions[name] = head_pos
        self.created_bones.append(name)

    def _mirror_bone(self, source: str, target: str):
        """Mirror a bone across X axis."""
        if source not in self.bone_positions:
            return

        src_pos = self.bone_positions[source]
        edit_bones = self.armature.data.edit_bones
        source_bone = edit_bones.get(source)

        # Get the source bone length for the tail offset
        source_length = 0.1  # Default
        if source_bone:
            source_length = (source_bone.tail - source_bone.head).length

        bone = edit_bones.new(target)
        bone.head = Vector((-src_pos[0], src_pos[1], src_pos[2]))
        bone.tail = bone.head + Vector((0, source_length, 0))
        bone.roll = -bone.roll if source_bone else 0

        self.bone_positions[target] = bone.head.to_tuple()
        self.created_bones.append(target)

    def _create_parenting(self):
        """Create bone parent relationships."""
        edit_bones = self.armature.data.edit_bones

        # Spine parenting
        spine_bones = [n for n in self.created_bones if n.startswith("spine_")]
        for i, bone_name in enumerate(spine_bones):
            if i > 0 and bone_name in edit_bones and spine_bones[i-1] in edit_bones:
                edit_bones[bone_name].parent = edit_bones[spine_bones[i-1]]

        # Tail parenting (follow last spine)
        tail_bones = [n for n in self.created_bones if n.startswith("tail_")]
        if tail_bones and spine_bones:
            last_spine = spine_bones[-1]
            if last_spine in edit_bones and tail_bones[0] in edit_bones:
                edit_bones[tail_bones[0]].parent = edit_bones[last_spine]
        for i, bone_name in enumerate(tail_bones):
            if i > 0 and bone_name in edit_bones and tail_bones[i-1] in edit_bones:
                edit_bones[bone_name].parent = edit_bones[tail_bones[i-1]]

        # Neck follows first spine
        neck_bones = [n for n in self.created_bones if n.startswith("neck_")]
        if neck_bones and spine_bones and spine_bones[0] in edit_bones:
            if neck_bones[0] in edit_bones:
                edit_bones[neck_bones[0]].parent = edit_bones[spine_bones[0]]

        # Head follows last neck
        if "head" in edit_bones and neck_bones and neck_bones[-1] in edit_bones:
            edit_bones["head"].parent = edit_bones[neck_bones[-1]]

        # Leg parenting (thigh -> shin -> foot)
        for side in ['.R', '.L']:
            thigh_name = f"thigh{side}"
            shin_name = f"shin{side}"
            foot_name = f"foot{side}"

            if thigh_name in edit_bones:
                if shin_name in edit_bones:
                    edit_bones[shin_name].parent = edit_bones[thigh_name]
                if foot_name in edit_bones:
                    edit_bones[foot_name].parent = edit_bones[shin_name] if shin_name in edit_bones else edit_bones[thigh_name]

        # Quadruped leg parenting
        for prefix in ['front_leg', 'back_leg']:
            for side in ['.R', '.L']:
                upper = f"{prefix}{side}.upper"
                lower = f"{prefix}{side}.lower"
                foot = f"{prefix}{side}.foot"

                if upper in edit_bones:
                    if lower in edit_bones:
                        edit_bones[lower].parent = edit_bones[upper]
                    if foot in edit_bones:
                        edit_bones[foot].parent = edit_bones[lower] if lower in edit_bones else edit_bones[upper]

    def _get_mesh_bounds(self) -> Dict[str, float]:
        """Get mesh bounding dimensions."""
        verts = [v.co @ self.mesh.matrix_world for v in self.mesh.data.vertices]

        y_vals = [v.y for v in verts]
        z_vals = [v.z for v in verts]
        x_vals = [v.x for v in verts]

        return {
            'front': max(y_vals),
            'back': min(y_vals),
            'top': max(z_vals),
            'bottom': min(z_vals),
            'left': min(x_vals),
            'right': max(x_vals),
            'center_x': (min(x_vals) + max(x_vals)) / 2,
            'center_z': (min(z_vals) + max(z_vals)) / 2,
            'length': max(y_vals) - min(y_vals),
            'height': max(z_vals) - min(z_vals),
            'width': (max(x_vals) - min(x_vals)) / 2,
        }

    def get_rig_summary(self) -> str:
        """Get summary of created rig."""
        lines = []
        lines.append("=== RIG CREATED ===")
        lines.append(f"Bones Created: {len(self.created_bones)}")
        lines.append(f"Rig Type: {self.analysis.detected_type}")

        # Categorize bones
        categories = {
            'spine': [n for n in self.created_bones if 'spine' in n],
            'tail': [n for n in self.created_bones if 'tail' in n],
            'neck': [n for n in self.created_bones if 'neck' in n],
            'legs': [n for n in self.created_bones if 'leg' in n or 'thigh' in n or 'shin' in n or 'foot' in n],
            'head': [n for n in self.created_bones if 'head' in n or 'jaw' in n],
        }

        for cat, bones in categories.items():
            if bones:
                lines.append(f"  {cat}: {len(bones)} bones ({', '.join(bones[:5])}{'...' if len(bones) > 5 else ''})")

        return "\n".join(lines)


def auto_rig_from_mesh(mesh_name: str, rig_name: str = None) -> Tuple[bpy.types.Object, str]:
    """
    Main entry point - analyze mesh and build rig.

    Returns: (armature_object, summary_string)
    """
    mesh_obj = bpy.data.objects.get(mesh_name)
    if not mesh_obj or mesh_obj.type != 'MESH':
        raise ValueError(f"Mesh '{mesh_name}' not found")

    # Analyze mesh
    from .mesh_analyzer import analyze_mesh, get_analysis_summary
    analysis = analyze_mesh(mesh_obj)

    if not analysis.is_valid_dino:
        return None, f"Mesh does not appear to be a valid dinosaur shape. Detected: {analysis.detected_type}"

    # Build rig
    builder = DinoRigBuilder(mesh_obj, analysis)
    rig_name_final = rig_name or f"{mesh_name}_Rig"
    armature = builder.build_rig(rig_name_final)

    return armature, builder.get_rig_summary()