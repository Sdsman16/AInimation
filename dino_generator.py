"""
Procedural Dinosaur Animation Generator

Generate locomotion and idle animations for bipedal/quadrupedal dinosaurs.
"""
import bpy
import math
from typing import Optional, Dict, List
from .dino_knowledge import (
    get_gait_cycle, get_idle_preset, interpolate_pose, get_animation_summary,
    GaitCycle, DinoPose
)


class DinoAnimationGenerator:
    """Generate and apply dinosaur animations to Blender armatures."""

    def __init__(self, armature_name: str):
        self.armature = bpy.data.objects.get(armature_name)
        if not self.armature or self.armature.type != 'ARMATURE':
            raise ValueError(f"Armature '{armature_name}' not found")

        self.pose_bones = self.armature.pose.bones
        self.action = None

    def generate_walk(self, dino_type: str, speed: str = "walk",
                      duration: float = 2.0, fps: int = 24) -> str:
        """Generate walk animation for dino type."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        gait = get_gait_cycle(dino_type, speed)
        if not gait:
            raise ValueError(f"No gait found for {dino_type}/{speed}")

        # Create action
        action_name = f"{dino_type}_{speed}_walk"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = True
        self.action.frame_start = 1
        self.action.frame_end = int(duration * fps)

        self.armature.animation_data.action = self.action

        # Set keyframes based on poses
        for i, pose in enumerate(gait.poses):
            frame = int(pose.frame / 24 * fps) if pose.frame < 24 else int(pose.frame / 24 * duration * fps)
            if frame > self.action.frame_end:
                frame = self.action.frame_end

            self._apply_pose_to_armature(pose)

            # Insert keyframes for all bones
            self._insert_keyframes(frame)

        # Add spinal wave between poses
        self._add_spine_wave(gait.spine_wave, fps)

        # Add tail sway
        self._add_tail_sway(gait.tail_sway, fps, dino_type)

        return action_name

    def generate_idle(self, dino_type: str, weight: str = "medium",
                      duration: float = 4.0, fps: int = 24) -> str:
        """Generate idle animation with breathing and subtle movements."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        preset = get_idle_preset(dino_type, weight)
        action_name = f"{dino_type}_idle_{weight}"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = True
        self.action.frame_start = 1
        self.action.frame_end = int(duration * fps)

        self.armature.animation_data.action = self.action

        # Create idle keyframes at strategic points
        total_frames = self.action.frame_end

        # Frame 1 - neutral
        self._apply_idle_pose(preset[0])
        self._insert_keyframes(1)

        # Breathing cycle - spine + slight lift
        breath_frames = [int(total_frames * 0.25), int(total_frames * 0.5),
                        int(total_frames * 0.75), total_frames]
        breath_depths = [0.015, 0.025, 0.02, 0.01]

        for bf, bd in zip(breath_frames, breath_depths):
            if bf < total_frames:
                self._apply_breathing(bd, dino_type)
                self._insert_keyframes(bf)

        # Head scan - subtle rotation
        head_frames = [int(total_frames * 0.3), int(total_frames * 0.7)]
        for hf in head_frames:
            if hf < total_frames:
                self._apply_head_scan(0.05, hf, total_frames)
                self._insert_keyframes(hf)

        # Final frame matches first for clean loop
        self._apply_idle_pose(preset[0])
        self._insert_keyframes(total_frames)

        return action_name

    def generate_run(self, dino_type: str, speed: str = "run",
                     duration: float = 1.0, fps: int = 24) -> str:
        """Generate run animation with more extreme poses and body lean."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        gait = get_gait_cycle(dino_type, speed)
        if not gait:
            raise ValueError(f"No gait found for {dino_type}/{speed}")

        action_name = f"{dino_type}_{speed}_run"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = True
        self.action.frame_start = 1
        self.action.frame_end = int(duration * fps)

        self.armature.animation_data.action = self.action

        # Run has more extreme poses, add body lean
        for pose in gait.poses:
            frame = int(pose.frame / 24 * duration * fps)
            if frame > self.action.frame_end:
                frame = self.action.frame_end

            self._apply_run_pose(pose, dino_type)
            self._insert_keyframes(frame)

        # More pronounced spine movement
        self._add_spine_wave(gait.spine_wave * 1.5, fps)
        self._add_tail_sway(gait.tail_sway * 1.3, fps, dino_type)

        return action_name

    def _apply_pose_to_armature(self, pose: DinoPose):
        """Apply a DinoPose's rotations to armature bones."""
        for bone_name, rotation in pose.bones.items():
            if bone_name in self.pose_bones:
                pb = self.pose_bones[bone_name]
                pb.rotation_euler = rotation
                pb.keyframe_insert(data_path="rotation_euler", frame=1)

    def _apply_idle_pose(self, pose_data: dict):
        """Apply an idle pose to armature."""
        # For bipedal, spine is main breathing axis
        if "spine_bend" in pose_data:
            spine_bone = self._find_bone("spine", "spine_01", "torso", "spine02")
            if spine_bone and spine_bone in self.pose_bones:
                self.pose_bones[spine_bone].rotation_euler[2] = pose_data["spine_bend"]

        # Head tilt
        if "head_tilt" in pose_data:
            head_bone = self._find_bone("head", "head", "neck_01", "jaw")
            if head_bone and head_bone in self.pose_bones:
                self.pose_bones[head_bone].rotation_euler[2] = pose_data["head_tilt"]

    def _apply_breathing(self, depth: float, dino_type: str):
        """Apply breathing offset to spine."""
        spine_bone = self._find_bone("spine", "spine_01", "torso", "spine02")
        if spine_bone and spine_bone in self.pose_bones:
            self.pose_bones[spine_bone].rotation_euler[0] += depth

    def _apply_head_scan(self, angle: float, frame: int, total: float):
        """Add head scanning movement."""
        head_bone = self._find_bone("head", "head", "neck_01", "jaw")
        if head_bone and head_bone in self.pose_bones:
            t = frame / total
            scan_angle = math.sin(t * math.pi * 2) * angle
            self.pose_bones[head_bone].rotation_euler[2] = scan_angle

    def _apply_run_pose(self, pose: DinoPose, dino_type: str):
        """Apply run pose with extra body lean forward."""
        for bone_name, rotation in pose.bones.items():
            if bone_name in self.pose_bones:
                pb = self.pose_bones[bone_name]
                # Add forward lean for running
                adjusted = list(rotation)
                if "thigh" in bone_name or "shin" in bone_name:
                    adjusted[0] += 0.15  # lean forward
                pb.rotation_euler = tuple(adjusted)

    def _insert_keyframes(self, frame: int):
        """Insert keyframes for all modified bones at current frame."""
        for pb in self.pose_bones:
            try:
                pb.keyframe_insert(data_path="location", frame=frame)
                pb.keyframe_insert(data_path="rotation_euler", frame=frame)
            except:
                pass

    def _add_spine_wave(self, amplitude: float, fps: int):
        """Add spinal wave motion via FCurve modification."""
        if not self.action:
            return

        # Find spine bones and add sine wave to their rotation
        spine_bones = [bn for bn in self.pose_bones if "spine" in bn.lower()]

        for spine_bone in spine_bones:
            fcurve = self.action.fcurves.find("rotation_euler", index=0, data_path=f'pose.bones["{spine_bone}"].rotation_euler')
            if fcurve:
                # Add wave via keyframe modulation
                pass  # Simplified - would need proper keyframe insertion

    def _add_tail_sway(self, amplitude: float, fps: int, dino_type: str):
        """Add tail sway motion."""
        tail_bones = [bn for bn in self.pose_bones if "tail" in bn.lower()]

        if not tail_bones:
            return

        tail_bone = tail_bones[0]
        start = self.action.frame_start
        end = self.action.frame_end

        # Add gentle sine wave rotation
        for frame in range(start, end + 1, fps // 4):  # Every quarter second
            t = (frame - start) / (end - start)
            angle = amplitude * math.sin(t * math.pi * 4)

            if tail_bone in self.pose_bones:
                self.pose_bones[tail_bone].rotation_euler[2] = angle
                self.pose_bones[tail_bone].keyframe_insert(
                    data_path="rotation_euler", frame=frame, index=2
                )

    def _find_bone(self, *names) -> Optional[str]:
        """Find a bone by trying multiple possible names."""
        for name in names:
            if name in self.pose_bones:
                return name
        # Try partial match
        for pb_name in self.pose_bones:
            for name in names:
                if name.lower() in pb_name.lower():
                    return pb_name
        return None

    def verify_armature(self) -> Dict[str, any]:
        """Check armature for expected dinosaur bones."""
        expected_bones = {
            "bipedal": ["spine", "thigh", "shin", "foot", "head", "neck", "tail"],
            "quadrupedal": ["front_leg", "back_leg", "spine", "neck", "tail", "head"]
        }

        found = {"spine": [], "legs": [], "head": [], "tail": []}
        missing = []

        for pb_name in self.pose_bones:
            lower = pb_name.lower()
            if "spine" in lower or "torso" in lower:
                found["spine"].append(pb_name)
            elif "thigh" in lower or "leg" in lower or "shin" in lower or "foot" in lower:
                found["legs"].append(pb_name)
            elif "head" in lower or "neck" in lower:
                found["head"].append(pb_name)
            elif "tail" in lower:
                found["tail"].append(pb_name)

        return {
            "found": found,
            "bone_count": len(self.pose_bones),
            "complete": len(found["spine"]) > 0 and len(found["legs"]) >= 2
        }


def generate_animation(armature_name: str, dino_type: str, anim_type: str,
                       speed: str = "walk", duration: float = 2.0) -> str:
    """Main entry point for animation generation."""
    generator = DinoAnimationGenerator(armature_name)
    verification = generator.verify_armature()

    if not verification["complete"]:
        return f"WARNING: Armature may be incomplete. Found: {verification['found']}"

    if anim_type == "walk":
        return generator.generate_walk(dino_type, speed, duration)
    elif anim_type == "idle":
        return generator.generate_idle(dino_type, speed, duration)  # speed used as weight here
    elif anim_type == "run":
        return generator.generate_run(dino_type, speed, duration)
    else:
        return f"Unknown animation type: {anim_type}"