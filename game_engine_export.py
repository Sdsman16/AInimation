"""
Game Engine Export Module

Handles export to Unreal Engine and Unity with proper settings.
Includes skeleton validation, FBX export, and animation compression.
"""
import bpy
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EngineTarget(Enum):
    """Target game engine."""
    UNREAL = "unreal"
    UNITY = "unity"
    GENERIC = "generic"


@dataclass
class ExportSettings:
    """Export configuration for game engines."""
    engine: EngineTarget
    fbx_version: str = "7.4"  # Blender 3.x+ uses FBX 7.4
    scale: float = 1.0
    apply_scale: bool = True
    export_transform: bool = True
    export_armature: bool = True
    export_mesh: bool = True
    export_animation: bool = True
    export_normals: bool = True
    export_uvs: bool = True
    use_mesh_modifiers: bool = True
    use_armature_deform_only: bool = True
    add_leaf_bones: bool = False
    export_bone_visibility: bool = False

    # Animation specific
    export_only_deform: bool = True
    export_all_actions: bool = False
    export_current_action: bool = True
    export_nla_strips: bool = False

    # Optimization
    simplify_animation: float = 0.0  # 0 = no simplification
    animation_bitflag: int = 0

    # Unity specific
    unity_use_existing_armature: bool = False
    unity_force armature_resolution: bool = False

    # Unreal specific
    unreal_use_file_resolution: bool = False
    unreal_preserve_imported_armature: bool = True


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    file_path: str = ""
    message: str = ""
    warnings: List[str] = None
    errors: List[str] = None


class SkeletonValidator:
    """Validate skeleton for game engine compatibility."""

    # Standard bone naming conventions
    UNITY_BONE_MAP = {
        'root': ['root', 'hips', 'pelvis'],
        'spine': ['spine', 'spine_01', 'spine_02', 'spine_03'],
        'chest': ['chest', 'spine_03'],
        'neck': ['neck', 'neck_01'],
        'head': ['head', 'head_01'],
        'left_shoulder': ['shoulder.L', 'shoulder_l', 'clavicle.L'],
        'left_upper_arm': ['upper_arm.L', 'upperarm_l', 'arm_l'],
        'left_forearm': ['forearm.L', 'forearm_l', 'lowerarm_l'],
        'left_hand': ['hand.L', 'hand_l', 'wrist_l'],
        'left_thigh': ['thigh.L', 'thigh_l', 'upleg_l'],
        'left_shin': ['shin.L', 'shin_l', 'lowerleg_l'],
        'left_foot': ['foot.L', 'foot_l', 'ankle_l'],
        'left_toes': ['toes.L', 'toe_l', 'ball_l'],
        'right_shoulder': ['shoulder.R', 'shoulder_r', 'clavicle.R'],
        'right_upper_arm': ['upper_arm.R', 'upperarm_r', 'arm_r'],
        'right_forearm': ['forearm.R', 'forearm_r', 'lowerarm_r'],
        'right_hand': ['hand.R', 'hand_r', 'wrist_r'],
        'right_thigh': ['thigh.R', 'thigh_r', 'upleg_r'],
        'right_shin': ['shin.R', 'shin_r', 'lowerleg_r'],
        'right_foot': ['foot.R', 'foot_r', 'ankle_r'],
        'right_toes': ['toes.R', 'toe_r', 'ball_r'],
    }

    UNREAL_BONE_MAP = {
        'root': ['root', 'pelvis', 'hips'],
        'spine_01': ['spine_01', 'spine'],
        'spine_02': ['spine_02'],
        'spine_03': ['spine_03'],
        'clavicle_l': ['clavicle_l', 'shoulder_l', 'shoulder.L'],
        'upperarm_l': ['upperarm_l', 'upper_arm_l', 'arm_l'],
        'lowerarm_l': ['lowerarm_l', 'forearm_l', 'forearm.L'],
        'hand_l': ['hand_l', 'hand.L', 'wrist_l'],
        'clavicle_r': ['clavicle_r', 'shoulder_r', 'shoulder.R'],
        'upperarm_r': ['upperarm_r', 'upper_arm_r', 'arm_r'],
        'lowerarm_r': ['lowerarm_r', 'forearm_r', 'forearm.R'],
        'hand_r': ['hand_r', 'hand.R', 'wrist_r'],
        'thigh_l': ['thigh_l', 'thigh.L', 'upleg_l'],
        'calf_l': ['calf_l', 'shin_l', 'shin.L', 'lowerleg_l'],
        'foot_l': ['foot_l', 'foot.L', 'ankle_l'],
        'ball_l': ['ball_l', 'toe_l', 'toes.L'],
        'thigh_r': ['thigh_r', 'thigh.R', 'upleg_r'],
        'calf_r': ['calf_r', 'shin_r', 'shin.R', 'lowerleg_r'],
        'foot_r': ['foot_r', 'foot.R', 'ankle_r'],
        'ball_r': ['ball_r', 'toe_r', 'toes.R'],
    }

    def __init__(self, armature_name: str):
        self.armature = bpy.data.objects.get(armature_name)
        if not self.armature or self.armature.type != 'ARMATURE':
            raise ValueError(f"Armature '{armature_name}' not found")

        self.bone_names = [b.name for b in self.armature.data.bones]
        self.missing_bones = {}
        self.matched_bones = {}

    def validate_for_engine(self, engine: EngineTarget) -> Tuple[bool, List[str]]:
        """
        Validate skeleton for specific engine.

        Returns:
            (is_valid, warnings_or_issues)
        """
        if engine == EngineTarget.UNITY:
            return self._validate_unity()
        elif engine == EngineTarget.UNREAL:
            return self._validate_unreal()
        return True, []

    def _validate_unity(self) -> Tuple[bool, List[str]]:
        """Validate for Unity skeleton requirements."""
        issues = []
        warnings = []

        # Check for required root bone
        has_root = any(self._matches_any(b, self.UNITY_BONE_MAP['root']) for b in self.bone_names)
        if not has_root:
            warnings.append("No root bone found - Unity may need one at (0,0,0)")

        # Check for hip/pelvis bone
        has_hips = any(self._matches_any(b, self.UNITY_BONE_MAP['root']) for b in self.bone_names)
        if not has_hips:
            warnings.append("No hip/pelvis bone - may cause import issues in Unity")

        # Check for spine chain
        spine_count = sum(1 for b in self.bone_names if 'spine' in b.lower())
        if spine_count < 2:
            warnings.append(f"Only {spine_count} spine bones - Unity Humanoids prefer 3+ spine bones")

        # Check for complete arm chains
        for arm_suffix in ['.L', '_l', '_L', 'left']:
            has_arm = any(f'upper_arm{arm_suffix}' in b or f'arm{arm_suffix}' in b for b in self.bone_names)
            if not has_arm:
                warnings.append(f"Incomplete arm chain for {arm_suffix}")

        # Check naming convention (should use .L / .R or _L / _R)
        has_proper_naming = any('.' in b or '_' in b for b in self.bone_names if any(x in b.lower() for x in ['left', 'right', 'l', 'r']))
        if not has_proper_naming:
            warnings.append("Bone naming may not follow Unity convention (.L/.R or _L/_R)")

        return len([i for i in issues if 'ERROR' in i]) == 0, warnings + issues

    def _validate_unreal(self) -> Tuple[bool, List[str]]:
        """Validate for Unreal Engine skeleton requirements."""
        issues = []
        warnings = []

        # Unreal prefers specific naming without dots (uses _l, _r)
        has_dot_naming = any('.' in b for b in self.bone_names)
        if has_dot_naming:
            warnings.append("Bones use '.' naming - Unreal prefers '_l', '_r' suffixes")

        # Check for standard Unreal bone hierarchy
        # Unreal mannequin has specific structure
        required_chains = ['pelvis', 'spine', 'clavicle', 'upperarm', 'lowerarm', 'hand',
                          'thigh', 'calf', 'foot', 'ball']

        for chain in required_chains:
            found = any(chain in b.lower() for b in self.bone_names)
            if not found:
                warnings.append(f"Missing '{chain}' bone chain - Unreal may not recognize skeleton")

        return len([i for i in issues if 'ERROR' in i]) == 0, warnings + issues

    def _matches_any(self, bone: str, options: List[str]) -> bool:
        """Check if bone matches any of the options."""
        bone_lower = bone.lower()
        for opt in options:
            if opt.lower() in bone_lower or bone_lower in opt.lower():
                return True
        return False

    def rename_bones_for_engine(self, engine: EngineTarget, preserve_original: bool = True) -> List[str]:
        """
        Rename bones to match engine conventions.

        Args:
            engine: Target engine
            preserve_original: If True, add suffix to original names instead of replacing

        Returns:
            List of renamed bones
        """
        renamed = []
        name_map = self.UNITY_BONE_MAP if engine == EngineTarget.UNITY else self.UNREAL_BONE_MAP

        if bpy.context.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        edit_bones = self.armature.data.edit_bones

        for canonical_name, variations in name_map.items():
            for bone_name in self.bone_names:
                if self._matches_any(bone_name, variations):
                    if preserve_original:
                        # Add prefix/suffix
                        if engine == EngineTarget.UNITY:
                            new_name = f"Bip01_{canonical_name}" if 'L' not in canonical_name and 'R' not in canonical_name else bone_name
                        else:  # Unreal
                            new_name = bone_name.replace('.', '_')
                    else:
                        new_name = canonical_name

                    if new_name != bone_name and new_name not in edit_bones:
                        edit_bones[bone_name].name = new_name
                        renamed.append(f"{bone_name} -> {new_name}")

        bpy.ops.object.mode_set(mode='OBJECT')
        return renamed

    def get_bone_mapping_report(self, engine: EngineTarget) -> str:
        """Generate a report of bone mapping status."""
        report = [f"=== Bone Mapping Report for {engine.value.upper()} ===\n"]

        if engine == EngineTarget.UNITY:
            bone_map = self.UNITY_BONE_MAP
        else:
            bone_map = self.UNREAL_BONE_MAP

        for canonical, variations in bone_map.items():
            matched = None
            for var in variations:
                for bone in self.bone_names:
                    if self._matches_any(bone, [var]):
                        matched = bone
                        break
                if matched:
                    break

            status = f"[OK] {matched}" if matched else f"[MISSING] {canonical}"
            report.append(f"  {canonical}: {status}")

        return "\n".join(report)


class AnimationExporter:
    """Export animations with game engine optimizations."""

    def __init__(self, armature_name: str):
        self.armature = bpy.data.objects.get(armature_name)
        if not self.armature:
            raise ValueError(f"Armature '{armature_name}' not found")

    def get_export_actions(self) -> List[bpy.types.Action]:
        """Get all actions suitable for export."""
        actions = []

        if self.armature.animation_data and self.armature.animation_data.action:
            actions.append(self.armature.animation_data.action)

        # Get all actions from bpy.data.actions that affect this armature
        for action in bpy.data.actions:
            if self._action_affects_armature(action):
                if action not in actions:
                    actions.append(action)

        return actions

    def _action_affects_armature(self, action: bpy.types.Action) -> bool:
        """Check if action has FCurves for this armature."""
        if not action:
            return False

        for fc in action.fcurves:
            if 'pose.bones' in fc.data_path:
                return True
        return False

    def export_fbx(self,
                   output_path: str,
                   engine: EngineTarget,
                   settings: ExportSettings = None,
                   mesh_names: List[str] = None) -> ExportResult:
        """
        Export armature and optionally mesh to FBX.

        Args:
            output_path: Destination FBX file path
            engine: Target engine
            settings: Export configuration
            mesh_names: Optional list of mesh names to include

        Returns:
            ExportResult with status
        """
        if settings is None:
            settings = ExportSettings(engine=engine)

        # Validate
        validator = SkeletonValidator(self.armature.name)
        is_valid, issues = validator.validate_for_engine(engine)
        if not is_valid and engine != EngineTarget.GENERIC:
            return ExportResult(
                success=False,
                message=f"Skeleton validation failed: {issues}"
            )

        # Prepare selection
        objects_to_export = [self.armature]

        if mesh_names:
            for name in mesh_names:
                obj = bpy.data.objects.get(name)
                if obj and obj.type == 'MESH':
                    objects_to_export.append(obj)
        else:
            # Find meshes with this armature modifier
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for mod in obj.modifiers:
                        if mod.type == 'ARMATURE' and mod.object == self.armature:
                            objects_to_export.append(obj)
                            break

        # Select for export
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects_to_export:
            obj.select_set(True)

        bpy.context.view_layer.objects.active = self.armature

        # Build FBX export arguments
        keywords = self._get_fbx_export_keywords(engine, settings)

        try:
            bpy.ops.export_scene.fbx(
                filepath=output_path,
                use_selection=True,
                **keywords
            )

            return ExportResult(
                success=True,
                file_path=output_path,
                message=f"Exported to {output_path}",
                warnings=issues if issues else None
            )

        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Export failed: {str(e)}",
                errors=[str(e)]
            )

    def _get_fbx_export_keywords(self, engine: EngineTarget, settings: ExportSettings) -> dict:
        """Build FBX export keyword arguments based on engine."""
        keywords = {
            'fbx_version': settings.fbx_version,
            'use_mesh_modifiers': settings.use_mesh_modifiers,
            'use_armature_deform_only': settings.use_armature_deform_only,
            'add_leaf_bones': settings.add_leaf_bones,
            'apply_scale_options': 'FBX_SCALE_ALL' if settings.apply_scale else 'FBX_SCALE_NONE',
            'axis_forward': '-Y' if engine == EngineTarget.UNITY else '-X',
            'axis_up': 'Z' if engine == EngineTarget.UNITY else 'Z',
        }

        if engine == EngineTarget.UNITY:
            keywords.update({
                'mesh_smooth_type': 'FACE',
                'use_mesh_edges': False,
                'use_tspace': False,
            })
        elif engine == EngineTarget.UNREAL:
            keywords.update({
                'mesh_smooth_type': 'EDGE',
                'use_mesh_edges': True,
                'use_tspace': True,
            })

        return keywords

    def export_nla_as_animations(self, output_dir: str, engine: EngineTarget,
                                  settings: ExportSettings = None) -> List[ExportResult]:
        """Export NLA tracks as individual animation files."""
        if settings is None:
            settings = ExportSettings(engine=engine)

        results = []

        if not self.armature.animation_data:
            return [ExportResult(success=False, message="No animation data")]

        for track in self.armature.animation_data.nla_tracks:
            for strip in track.strips:
                # Set active action
                if strip.action:
                    self.armature.animation_data.action = strip.action

                    # Export each action
                    output_path = os.path.join(output_dir, f"{strip.action.name}.fbx")
                    result = self.export_fbx(output_path, engine, settings)
                    results.append(result)

        return results


class AnimationOptimizer:
    """Optimize animations for game engines."""

    @staticmethod
    def simplify_animation(action_name: str, tolerance: float = 0.001) -> str:
        """
        Simplify animation by reducing keyframes while preserving motion.

        Args:
            action_name: Name of action to simplify
            tolerance: Keyframe reduction tolerance

        Returns:
            Name of new optimized action
        """
        action = bpy.data.actions.get(action_name)
        if not action:
            return ""

        new_action = bpy.data.actions.new(name=f"{action_name}_optimized")
        new_action.use_cyclic = action.use_cyclic
        new_action.frame_start = action.frame_start
        new_action.frame_end = action.frame_end

        # Copy all FCurves and simplify
        for fc in action.fcurves:
            new_fc = new_action.fcurves.new(
                data_path=fc.data_path,
                index=fc.array_index
            )

            # Copy keyframe points with simplification
            keyframe_points = []
            for kp in fc.keyframe_points:
                keyframe_points.append(kp.co)

            # Simple reduction - keep every Nth keyframe based on tolerance
            if len(keyframe_points) > 10:
                step = max(1, int(len(keyframe_points) / (100 * tolerance)))
                keyframe_points = keyframe_points[::step]

            for kp in keyframe_points:
                new_fc.keyframe_points.add(1)
                new_fc.keyframe_points[-1].co = kp

        return new_action.name

    @staticmethod
    def resample_for_engine(action_name: str, target_fps: int = 30) -> str:
        """
        Resample animation to specific FPS.

        Args:
            action_name: Source action
            target_fps: Target frame rate

        Returns:
            Name of resampled action
        """
        from .blend_space import resample_animation_for_game

        armature = bpy.context.active_object
        if not armature or armature.type != 'ARMATURE':
            return ""

        return resample_animation_for_game(armature.name, action_name, target_fps)

    @staticmethod
    def compress_for_unreal(action_name: str, precision: int = 3) -> str:
        """
        Compress animation for Unreal Engine (reduce decimal places).

        Args:
            action_name: Action to compress
            precision: Number of decimal places to keep

        Returns:
            Name of compressed action
        """
        action = bpy.data.actions.get(action_name)
        if not action:
            return ""

        new_name = f"{action_name}_compressed"
        new_action = bpy.data.actions.new(name=new_name)
        new_action.use_cyclic = action.use_cyclic
        new_action.frame_start = action.frame_start
        new_action.frame_end = action.frame_end

        factor = 10 ** precision

        for fc in action.fcurves:
            new_fc = new_action.fcurves.new(
                data_path=fc.data_path,
                index=fc.array_index
            )

            for kp in fc.keyframe_points:
                new_kp = new_fc.keyframe_points.add(1)
                new_kp.co = (
                    round(kp.co.x),
                    round(kp.co.y * factor) / factor
                )
                new_kp.handle_left = kp.handle_left
                new_kp.handle_right = kp.handle_right

        return new_name

    @staticmethod
    def prepare_for_mixamo(action_names: List[str]) -> Dict[str, str]:
        """
        Prepare animations for Mixamo/Adobe services.
        Returns mapping of original to compatible names.

        Args:
            action_names: List of action names to prepare

        Returns:
            Dict mapping original -> compatible name
        """
        replacements = {
            ' ': '_',
            '.': '_',
            '(': '',
            ')': '',
        }

        mapping = {}
        for name in action_names:
            compatible = name
            for old, new in replacements.items():
                compatible = compatible.replace(old, new)

            action = bpy.data.actions.get(name)
            if action and compatible != name:
                action.name = compatible

            mapping[name] = compatible

        return mapping


def quick_export_unreal(armature_name: str, output_path: str) -> ExportResult:
    """Quick export with Unreal Engine defaults."""
    exporter = AnimationExporter(armature_name)
    settings = ExportSettings(engine=EngineTarget.UNREAL)

    # Validate skeleton
    validator = SkeletonValidator(armature_name)
    is_valid, issues = validator.validate_for_engine(EngineTarget.UNREAL)

    # Export
    result = exporter.export_fbx(output_path, EngineTarget.UNREAL, settings)

    if issues:
        result.warnings = issues

    return result


def quick_export_unity(armature_name: str, output_path: str) -> ExportResult:
    """Quick export with Unity defaults."""
    exporter = AnimationExporter(armature_name)
    settings = ExportSettings(engine=EngineTarget.UNITY)

    # Validate
    validator = SkeletonValidator(armature_name)
    is_valid, issues = validator.validate_for_engine(EngineTarget.UNITY)

    result = exporter.export_fbx(output_path, EngineTarget.UNITY, settings)

    if issues:
        result.warnings = issues

    return result


def batch_export_animations(armature_name: str,
                            output_dir: str,
                            engine: EngineTarget,
                            include_strips: bool = True) -> List[ExportResult]:
    """Batch export all animations for an armature."""
    exporter = AnimationExporter(armature_name)

    results = []

    # Get all actions
    actions = exporter.get_export_actions()

    for action in actions:
        # Set as active
        if exporter.armature.animation_data:
            exporter.armature.animation_data.action = action

        # Export each
        name = action.name.replace(' ', '_')
        output_path = os.path.join(output_dir, f"{name}.fbx")

        settings = ExportSettings(engine=engine)
        result = exporter.export_fbx(output_path, engine, settings)
        results.append(result)

    return results


def get_engine_requirements(engine: EngineTarget) -> str:
    """Get engine-specific requirements documentation."""
    if engine == EngineTarget.UNITY:
        return """
UNITY ENGINE REQUIREMENTS:

1. SKELETON:
   - Root bone at origin (0,0,0)
   - Hip/pelvis bone as parent of spine
   - Naming: .L / .R suffix OR _L / _R suffix
   - Humanoid: 5+ bones in spine chain recommended

2. ANIMATIONS:
   - FBX format, binary preferred
   - 30 FPS standard, 60 FPS for high quality
   - Keyframe reduction enabled for mobile
   - Loop ready: first and last frames should match

3. EXPORT SETTINGS:
   - Scale: 1.0 (use Import Scale in Unity instead)
   - Animation: Key Linear
   - Anim End Include: Last frame
   - Filter: Animations only

4. NAMING CONVENTION:
   - Use Mixamo-compatible names (no spaces, underscores only)
   - Actions named: idle, walk, run, jump, etc.
"""

    elif engine == EngineTarget.UNREAL:
        return """
UNREAL ENGINE REQUIREMENTS:

1. SKELETON:
   - Use Unreal Mannequin bone naming as reference
   - No dots in names (use _l, _r not .L, .R)
   - Pelvis as root recommended
   - Complete chains: clavicle -> upperarm -> forearm -> hand

2. ANIMATIONS:
   - FBX format, ASCII for debugging
   - Resample to 30 FPS or keep original
   - Compress on export (Unreal handles this)
   - Use Pre-allocated memory for performance

3. EXPORT SETTINGS:
   - Force Front X-axis for forward direction
   - Z-up for axis orientation
   - Sample Rate: 30 FPS default

4. NAMING:
   - No special characters
   - Skeleton and Animations should match naming
"""

    return ""