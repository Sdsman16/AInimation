"""
Blend Space Animation Generator

Generate and manage blend spaces for smooth animation transitions.
Supports 1D (speed-based) and 2D (speed + direction) blend spaces.
"""
import bpy
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BlendSpacePoint:
    """A point in blend space with associated animation."""
    name: str
    speed: float  # Primary axis (X)
    direction: float = 0.0  # Secondary axis (Y) for 2D
    weight: float = 1.0
    threshold_min: float = 0.0  # Blend region min
    threshold_max: float = 1.0  # Blend region max


class BlendSpaceGenerator:
    """Generate and manage animation blend spaces."""

    def __init__(self, armature_name: str):
        self.armature = bpy.data.objects.get(armature_name)
        if not self.armature or self.armature.type != 'ARMATURE':
            raise ValueError(f"Armature '{armature_name}' not found")

        self.pose_bones = self.armature.pose.bones
        self.action = None

    def create_1d_blend_space(self, anim_type: str = "walk",
                               speeds: List[float] = None,
                               base_duration: float = 2.0,
                               fps: int = 24) -> str:
        """
        Create a 1D blend space for speed-based animation blending.

        Args:
            anim_type: Animation type (walk, run, etc.)
            speeds: List of speed values to generate (default: [0.5, 1.0, 1.5, 2.0])
            base_duration: Base animation duration at 1.0x speed
            fps: Frames per second

        Returns:
            Name of the blend space NLA track
        """
        if speeds is None:
            speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

        blend_space_name = f"{anim_type}_blend_space"
        track = self._get_or_create_nla_track(blend_space_name)

        # Clear existing strips
        track.strips.clear()

        # Generate animation at each speed point
        animations = []
        for speed in speeds:
            anim_name = self._generate_speed_variation(anim_type, speed, base_duration, fps)
            animations.append((speed, anim_name))

        # Create blend space strips
        for i, (speed, anim_name) in enumerate(animations):
            if anim_name not in bpy.data.actions:
                continue

            strip = track.strips.new(anim_name, start=int(i * base_duration * fps * 0.5), action=bpy.data.actions[anim_name])
            strip.name = f"{anim_type}_{speed:.2f}"
            strip.blend_type = 'BLEND'
            strip.use_animated_time = True
            strip.scale = 1.0

        # Create NLA control property for speed
        self._create_speed_control_property()

        return blend_space_name

    def _generate_speed_variation(self, anim_type: str, speed: float,
                                  duration: float, fps: int) -> str:
        """Generate animation at specific speed."""
        from .human_generator import HumanAnimationGenerator
        from .dino_generator import DinoAnimationGenerator

        generator = HumanAnimationGenerator(self.armature.name)

        if anim_type == "walk":
            return generator.generate_walk(speed=speed, duration=duration, fps=fps)
        elif anim_type == "run":
            return generator.generate_run(speed=speed, duration=duration / 1.5, fps=fps)
        elif anim_type == "idle":
            return generator.generate_idle("neutral", duration=duration, fps=fps)

        return ""

    def _get_or_create_nla_track(self, track_name: str) -> bpy.types.NlaTrack:
        """Get or create NLA track."""
        if self.armature.animation_data is None:
            self.armature.animation_data_create()

        # Find existing track or create new
        for track in self.armature.animation_data.nla_tracks:
            if track.name == track_name:
                return track

        track = self.armature.animation_data.nla_tracks.new()
        track.name = track_name
        track.lock = False
        track.mute = False
        return track

    def _create_speed_control_property(self):
        """Create or get the speed control property."""
        # This would create a custom property on the armature for NLA control
        # In practice, Blender handles this via NLA blend amount
        pass

    def create_2d_blend_space(self, anim_type: str,
                               speeds: List[float],
                               directions: List[float],
                               base_duration: float = 2.0,
                               fps: int = 24) -> str:
        """
        Create a 2D blend space (speed + direction).

        For game engines, this generates the corner animations and
        documents how to interpolate between them.
        """
        blend_space_name = f"{anim_type}_2d_blend"

        # Generate corner animations
        grid = []
        for speed in speeds:
            row = []
            for direction in directions:
                anim_name = self._generate_2d_variation(anim_type, speed, direction, base_duration, fps)
                row.append(anim_name)
            grid.append(row)

        # For Blender NLA, create tracks for each corner
        track = self._get_or_create_nla_track(blend_space_name)
        track.strips.clear()

        # Flatten grid and create staggered strips
        for i, row in enumerate(grid):
            for j, anim_name in enumerate(row):
                if anim_name not in bpy.data.actions:
                    continue

                start_frame = int((i * len(directions) + j) * base_duration * fps * 0.25)
                strip = track.strips.new(anim_name, start=start_frame, action=bpy.data.actions[anim_name])
                strip.name = f"spd{speeds[i]:.1f}_dir{directions[j]:.0f}"
                strip.blend_type = 'ADD'
                strip.use_animated_time = True

        return blend_space_name

    def _generate_2d_variation(self, anim_type: str, speed: float, direction: float,
                               duration: float, fps: int) -> str:
        """Generate animation with speed and direction influence."""
        from .human_generator import HumanAnimationGenerator

        generator = HumanAnimationGenerator(self.armature.name)

        # Apply direction influence to arm/leg poses
        anim_name = self._generate_speed_variation(anim_type, speed, duration, fps)

        # Post-process to add directional lean
        if abs(direction) > 0.1 and anim_name in bpy.data.actions:
            action = bpy.data.actions[anim_name]
            self._add_direction_influence(action, direction)

        return anim_name

    def _add_direction_influence(self, action: bpy.types.Action, direction: float):
        """Add directional lean to animation."""
        # Direction influence: positive = left, negative = right
        lean_angle = direction * 0.15  # Max 15 degrees lean

        fcurves = action.fcurves
        for fc in fcurves:
            # Add rotation offset based on direction
            pass  # Simplified - would need proper FCurve manipulation

    def extend_animation_frames(self, action_name: str, target_fps: int = 60,
                                scale_factor: float = 2.0) -> str:
        """
        Extend animation by interpolating additional frames.

        Takes an existing action and creates a new one with more frames
        by interpolating between original keyframes.

        Args:
            action_name: Source action to extend
            target_fps: Target frame rate
            scale_factor: How much to scale (2.0 = double frames)

        Returns:
            Name of new extended action
        """
        source_action = bpy.data.actions.get(action_name)
        if not source_action:
            raise ValueError(f"Action '{action_name}' not found")

        # Create new action
        new_action = bpy.data.actions.new(name=f"{action_name}_ext_{int(scale_factor)}x")
        new_action.use_cyclic = source_action.use_cyclic

        # Calculate frame ranges
        old_fps = 24  # Assume base animation is 24fps
        old_start = source_action.frame_start
        old_end = source_action.frame_end
        old_duration = old_end - old_start

        # New range
        new_start = old_start
        new_end = int(old_start + old_duration * scale_factor)
        new_action.frame_start = new_start
        new_action.frame_end = new_end

        # Set active on armature
        self.armature.animation_data.action = new_action

        # Resample keyframes with new timing
        old_frames = list(range(int(old_start), int(old_end) + 1))
        new_frames = []
        for f in old_frames:
            new_frame = old_start + (f - old_start) * scale_factor
            new_frames.append((new_frame, f))

        # Apply keyframes at new timing
        for new_f, old_f in new_frames:
            # Seek to old frame and capture pose
            self.armature.keyframe_delete(action=f"rotation_euler", frame=new_f)

        # Actually need to evaluate and re-keyframe
        bpy.context.scene.frame_set(old_start)
        self._capture_keyframe(new_action, old_start)

        for new_f, old_f in new_frames[1:-1]:
            bpy.context.scene.frame_set(old_f)
            self._capture_keyframe(new_action, new_f)

        bpy.context.scene.frame_set(old_end)
        self._capture_keyframe(new_action, new_end)

        return new_action.name

    def _capture_keyframe(self, action: bpy.types.Action, frame: float):
        """Capture current pose as keyframe."""
        for pb in self.pose_bones:
            try:
                pb.keyframe_insert(data_path="rotation_euler", frame=frame)
                pb.keyframe_insert(data_path="location", frame=frame)
            except:
                pass

    def resample_to_fps(self, action_name: str, target_fps: int = 60) -> str:
        """
        Resample animation to different FPS with smooth interpolation.

        Args:
            action_name: Source action
            target_fps: Target frames per second

        Returns:
            Name of resampled action
        """
        source_action = bpy.data.actions.get(action_name)
        if not source_action:
            raise ValueError(f"Action '{action_name}' not found")

        original_fps = 24  # Assumed
        scale = target_fps / original_fps

        return self.extend_animation_frames(action_name, target_fps, scale)

    def create_blend_space_1d_manual(self, animations: Dict[float, str]) -> str:
        """
        Manually create 1D blend space from pre-existing animations.

        Args:
            animations: Dict mapping speed -> action name

        Returns:
            Blend space description
        """
        # Sort by speed
        sorted_speeds = sorted(animations.keys())

        # Verify all actions exist
        for speed, action_name in animations.items():
            if action_name not in bpy.data.actions:
                raise ValueError(f"Action '{action_name}' not found")

        # Create blend space info
        info = f"1D Blend Space ({len(animations)} points):\n"
        for speed in sorted_speeds:
            info += f"  {speed:.2f} m/s: {animations[speed]}\n"

        info += "\nInterpolation: Linear between adjacent points.\n"
        info += "Recommended: Use with NLA track or export to game engine."

        return info

    def generate_interpolated_frames(self, action_name: str,
                                      multiplier: int = 4) -> List[Tuple[float, Dict]]:
        """
        Generate additional interpolated frames for smoother animation.

        Args:
            action_name: Source action
            multiplier: Generate multiplier * original frames

        Returns:
            List of (frame, pose_dict) tuples
        """
        source_action = bpy.data.actions.get(action_name)
        if not source_action:
            raise ValueError(f"Action '{action_name}' not found")

        # Get all keyframes
        keyframes = []
        for fc in source_action.fcurves:
            for kp in fc.keyframe_points:
                if kp.co.x not in [kf[0] for kf in keyframes]:
                    keyframes.append((kp.co.x, None))

        keyframes.sort(key=lambda x: x[0])

        if len(keyframes) < 2:
            return []

        # Generate interpolated frames
        new_frames = []
        for i in range(len(keyframes) - 1):
            t_start = keyframes[i][0]
            t_end = keyframes[i + 1][0]
            duration = t_end - t_start

            # Generate intermediate frames
            steps = multiplier + 1
            for step in range(steps):
                t = step / steps
                frame = t_start + t * duration

                # Get pose at this frame by interpolation
                pose = self._get_pose_at_frame(source_action, t_start, t_end, t)
                new_frames.append((frame, pose))

        return new_frames

    def _get_pose_at_frame(self, action: bpy.types.Action,
                           frame_start: float, frame_end: float,
                           t: float) -> Dict[str, Tuple]:
        """Get interpolated pose at a specific time point."""
        pose = {}

        for fc in action.fcurves:
            data_path = fc.data_path
            array_index = fc.array_index

            # Evaluate at start and end
            val_start = fc.evaluate(frame_start)
            val_end = fc.evaluate(frame_end)

            # Interpolate
            val = val_start + (val_end - val_start) * t

            # Store with bone name
            if 'pose.bones["' in data_path:
                start = data_path.find('pose.bones["') + 13
                end = data_path.find('"]', start)
                if end > start:
                    bone_name = data_path[start:end]
                    if bone_name not in pose:
                        pose[bone_name] = [0, 0, 0]
                    pose[bone_name][array_index] = val

        return pose


def create_standard_walk_blend_space(armature_name: str) -> str:
    """Create standard walk blend space with 6 speed points."""
    generator = BlendSpaceGenerator(armature_name)

    # Standard walk speeds: slow -> fast
    speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    return generator.create_1d_blend_space("walk", speeds, base_duration=2.0, fps=24)


def create_standard_run_blend_space(armature_name: str) -> str:
    """Create standard run blend space with 5 speed points."""
    generator = BlendSpaceGenerator(armature_name)

    # Run speeds
    speeds = [3.0, 4.0, 5.0, 6.5, 8.0]

    return generator.create_1d_blend_space("run", speeds, base_duration=1.0, fps=24)


def resample_animation_for_game(armature_name: str, action_name: str,
                                 target_fps: int = 60) -> str:
    """
    Resample animation for game engine import.
    Game engines typically want 60fps animations.
    """
    generator = BlendSpaceGenerator(armature_name)
    return generator.resample_to_fps(action_name, target_fps)


def extend_animation_for_smoothness(armature_name: str, action_name: str,
                                    quality: int = 4) -> str:
    """
    Extend animation for smoother playback.
    Higher quality = more interpolated frames.
    """
    generator = BlendSpaceGenerator(armature_name)
    return generator.extend_animation_frames(action_name, 24, float(quality))