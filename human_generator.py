"""
Procedural Human Animation Generator

Generate locomotion and idle animations for human bipedal characters.
"""
import bpy
import math
from typing import Optional, Dict, List
from .human_knowledge import (
    get_human_gait, get_idle_preset, interpolate_human_pose, get_human_animation_summary,
    HumanGaitCycle, HumanPose, HUMAN_RIG_BONES, HUMAN_WALK_CYCLE, HUMAN_RUN_CYCLE
)


class HumanAnimationGenerator:
    """Generate and apply human animations to Blender armatures."""

    def __init__(self, armature_name: str):
        self.armature = bpy.data.objects.get(armature_name)
        if not self.armature or self.armature.type != 'ARMATURE':
            raise ValueError(f"Armature '{armature_name}' not found")

        self.pose_bones = self.armature.pose.bones
        self.action = None
        self._original_mode = None

    def generate_walk(self, speed: float = 1.4, duration: float = 1.0, fps: int = 24) -> str:
        """Generate walk animation at given speed (m/s)."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        action_name = f"human_walk_{int(speed*10)}"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = True
        self.action.frame_start = 1
        self.action.frame_end = int(duration * fps)

        self.armature.animation_data.action = self.action

        gait = HUMAN_WALK_CYCLE

        # Calculate frame timing based on speed
        # Base walk cycle is 24 frames at 1.4 m/s
        speed_factor = 1.4 / speed if speed > 0 else 1.0
        cycle_frames = int(24 * speed_factor)

        for i, pose in enumerate(gait.poses):
            # Scale frame timing by speed
            original_frame = pose.frame
            frame = int(original_frame * speed_factor)
            if frame > self.action.frame_end:
                frame = self.action.frame_end

            self._apply_human_pose(pose)

            # Add hip sway
            if "hip" in pose.bones:
                t = original_frame / 24.0
                hip_sway = math.sin(t * math.pi * 2) * gait.hip_sway
                self._add_hip_sway(hip_sway, pose)

            self._insert_keyframes(frame)

        # Add arm swing (counter to legs)
        self._add_arm_swing(gait.arm_swing, speed_factor, fps)

        # Add shoulder counter-rotation
        self._add_shoulder_rotation(gait.shoulder_anticipation, speed_factor, fps)

        return action_name

    def generate_run(self, speed: float = 3.0, duration: float = 0.67, fps: int = 24) -> str:
        """Generate run animation at given speed (m/s)."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        action_name = f"human_run_{int(speed*10)}"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = True
        self.action.frame_start = 1
        self.action.frame_end = int(duration * fps)

        self.armature.animation_data.action = self.action

        gait = HUMAN_RUN_CYCLE

        # Base run cycle is 16 frames at 3.0 m/s
        speed_factor = 3.0 / speed if speed > 0 else 1.0
        cycle_frames = int(16 * speed_factor)

        for i, pose in enumerate(gait.poses):
            original_frame = pose.frame
            frame = int(original_frame * speed_factor)
            if frame > self.action.frame_end:
                frame = self.action.frame_end

            self._apply_human_pose(pose, run_mode=True)

            self._insert_keyframes(frame)

        # Add more pronounced arm swing for running
        self._add_arm_swing(gait.arm_swing * 1.5, speed_factor, fps)

        # Add body lean for running
        self._add_running_lean()

        return action_name

    def generate_idle(self, preset: str = "neutral", duration: float = 5.0, fps: int = 24) -> str:
        """Generate idle animation with breathing and subtle movements."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        action_name = f"human_idle_{preset}"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = True
        self.action.frame_start = 1
        self.action.frame_end = int(duration * fps)

        self.armature.animation_data.action = self.action

        poses = get_idle_preset(preset)
        total_frames = self.action.frame_end

        # Frame 1 - neutral
        self._apply_idle_values(poses[0])
        self._insert_keyframes(1)

        # Breathing cycle
        breath_cycle = 96  # ~4 seconds at 24fps
        for frame in range(1, total_frames + 1):
            breath_t = (frame % breath_cycle) / breath_cycle
            breath_depth = 0.03 * math.sin(breath_t * math.pi * 2)

            self._apply_breathing(breath_depth, poses[0])
            self._insert_keyframes(frame)

        # Weight shifts
        shift_cycle = 144  # ~6 seconds
        for frame in range(1, total_frames + 1, shift_cycle // 4):
            shift_t = (frame % shift_cycle) / shift_cycle
            shift_angle = 0.02 * math.sin(shift_t * math.pi * 2)

            self._apply_weight_shift(shift_angle)
            self._insert_keyframes(frame)

        # Head scan
        head_cycle = 120
        for frame in range(30, total_frames, head_cycle):
            t = (frame % head_cycle) / head_cycle
            head_tilt = 0.03 * math.sin(t * math.pi * 2)
            self._apply_head_movement(head_tilt, t)
            self._insert_keyframes(frame)

        # Final frame matches first
        self._apply_idle_values(poses[0])
        self._insert_keyframes(total_frames)

        return action_name

    def apply_video_keyframes(self, keyframes: List[tuple], fps: int = 24) -> str:
        """Apply keyframes extracted from video analysis."""
        # Ensure we're in POSE mode for keyframing
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        action_name = "video_reference_animation"
        self.action = bpy.data.actions.new(name=action_name)
        self.action.use_cyclic = False

        if not keyframes:
            return action_name

        self.action.frame_start = keyframes[0][0]
        self.action.frame_end = keyframes[-1][0]

        self.armature.animation_data.action = self.action

        for frame, pose_data in keyframes:
            bpy.context.scene.frame_set(frame)
            self._apply_video_pose(pose_data)
            self._insert_keyframes(frame)

        return action_name

    def _apply_human_pose(self, pose: HumanPose, run_mode: bool = False):
        """Apply a HumanPose's rotations to armature bones."""
        for bone_name, rotation in pose.bones.items():
            if bone_name in self.pose_bones:
                pb = self.pose_bones[bone_name]
                if run_mode:
                    adjusted = list(rotation)
                    adjusted[0] += 0.1  # Forward lean for running
                    pb.rotation_euler = tuple(adjusted)
                else:
                    pb.rotation_euler = rotation

    def _apply_idle_values(self, pose_data: dict):
        """Apply idle pose values to armature."""
        pelvis = self._find_bone("pelvis", "hip")
        if pelvis and pelvis in self.pose_bones:
            self.pose_bones[pelvis].rotation_euler[0] = pose_data.get('pelvis tilt', 0)

        spine = self._find_bone("spine_01", "spine")
        if spine and spine in self.pose_bones:
            self.pose_bones[spine].rotation_euler[2] = pose_data.get('spine curve', 0)

    def _apply_breathing(self, depth: float, base_pose: dict):
        """Apply breathing offset to spine and chest."""
        spine = self._find_bone("spine_01", "spine_02", "spine")
        if spine and spine in self.pose_bones:
            base = base_pose.get('spine curve', 0)
            self.pose_bones[spine].rotation_euler[0] = base + depth

    def _apply_weight_shift(self, angle: float):
        """Apply side-to-side weight shift to pelvis."""
        pelvis = self._find_bone("pelvis", "hip")
        if pelvis and pelvis in self.pose_bones:
            self.pose_bones[pelvis].rotation_euler[2] = angle

    def _apply_head_movement(self, tilt: float, phase: float):
        """Apply subtle head movement."""
        head = self._find_bone("head", "neck_01")
        if head and head in self.pose_bones:
            self.pose_bones[head].rotation_euler[2] = tilt
            # Slight up/down as well
            self.pose_bones[head].rotation_euler[0] = 0.01 * math.sin(phase * math.pi * 2)

    def _add_hip_sway(self, amount: float, pose: HumanPose):
        """Add hip sway to leg poses."""
        for side in ['.L', '.R']:
            hip_bone = self._find_bone(f"hip{side}", f"thigh{side}")
            if hip_bone and hip_bone in self.pose_bones:
                base = pose.bones.get(f"hip{side}", (0, 0, 0))[2]
                self.pose_bones[hip_bone].rotation_euler[2] = base + amount

    def _add_arm_swing(self, amplitude: float, speed_factor: float, fps: int):
        """Add natural arm swing to walk/run."""
        for side in ['.L', '.R']:
            shoulder = self._find_bone(f"shoulder{side}", f"upper_arm{side}")
            elbow = self._find_bone(f"elbow{side}", f"forearm{side}")

            if shoulder and shoulder in self.pose_bones:
                shoulder_pb = self.pose_bones[shoulder]
                shoulder_pb.rotation_euler[1] = amplitude * 0.5

            if elbow and elbow in self.pose_bones:
                elbow_pb = self.pose_bones[elbow]
                elbow_pb.rotation_euler[1] = -amplitude * 0.3  # Counter-swing

    def _add_shoulder_rotation(self, amount: float, speed_factor: float, fps: int):
        """Add counter-rotation to shoulders."""
        for side in ['.L', '.R']:
            shoulder = self._find_bone(f"shoulder{side}")
            if shoulder and shoulder in self.pose_bones:
                # Opposite to hip sway
                self.pose_bones[shoulder].rotation_euler[1] = -amount

    def _add_running_lean(self):
        """Add forward lean for running poses."""
        spine = self._find_bone("spine_01", "spine_02", "spine")
        if spine and spine in self.pose_bones:
            current = list(self.pose_bones[spine].rotation_euler)
            current[0] += 0.15  # Lean forward
            self.pose_bones[spine].rotation_euler = tuple(current)

    def _apply_video_pose(self, pose_data: Dict):
        """Apply a pose from video analysis."""
        raw = pose_data.get('raw_response', '')

        # Simple approach: set all bones to neutral, then apply parsed values
        for pb in self.pose_bones:
            pb.rotation_euler = (0, 0, 0)

        # Apply based on detected pose type
        pose_type = pose_data.get('pose_type', 'standing')
        phase = pose_data.get('phase', 'neutral')

        # Very simplified - real implementation would parse angles properly
        if 'walk' in pose_type:
            self._apply_video_walk_pose(phase)
        elif 'run' in pose_type or 'jog' in pose_type:
            self._apply_video_run_pose(phase)

    def _apply_video_walk_pose(self, phase: str):
        """Apply a walk pose from video."""
        # Left leg forward
        hip_l = self._find_bone("hip.L", "thigh.L")
        hip_r = self._find_bone("hip.R", "thigh.R")

        if phase == 'contact':
            if hip_l:
                self.pose_bones[hip_l].rotation_euler[0] = 0.15
            if hip_r:
                self.pose_bones[hip_r].rotation_euler[0] = -0.2
        elif phase == 'passing':
            if hip_l:
                self.pose_bones[hip_l].rotation_euler[0] = 0.0
            if hip_r:
                self.pose_bones[hip_r].rotation_euler[0] = 0.0

    def _apply_video_run_pose(self, phase: str):
        """Apply a run pose from video."""
        # More extreme angles for running
        hip_l = self._find_bone("hip.L", "thigh.L")
        hip_r = self._find_bone("hip.R", "thigh.R")

        if phase == 'contact':
            if hip_l:
                self.pose_bones[hip_l].rotation_euler[0] = 0.3
            if hip_r:
                self.pose_bones[hip_r].rotation_euler[0] = -0.4
        elif phase == 'apex' or 'passing':
            if hip_l:
                self.pose_bones[hip_l].rotation_euler[0] = -0.1
            if hip_r:
                self.pose_bones[hip_r].rotation_euler[0] = -0.1

    def _insert_keyframes(self, frame: int):
        """Insert keyframes for all modified bones."""
        for pb in self.pose_bones:
            try:
                pb.keyframe_insert(data_path="rotation_euler", frame=frame)
            except:
                pass

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

    def verify_human_rig(self) -> Dict[str, any]:
        """Check armature for expected human bones."""
        found = {
            "spine": [],
            "legs": [],
            "arms": [],
            "head": [],
        }

        for pb_name in self.pose_bones:
            lower = pb_name.lower()
            if any(x in lower for x in ['spine', 'pelvis', 'torso']):
                found["spine"].append(pb_name)
            elif any(x in lower for x in ['leg', 'thigh', 'knee', 'shin', 'foot', 'ankle', 'hip']):
                found["legs"].append(pb_name)
            elif any(x in lower for x in ['arm', 'shoulder', 'elbow', 'wrist', 'hand']):
                found["arms"].append(pb_name)
            elif any(x in lower for x in ['head', 'neck']):
                found["head"].append(pb_name)

        return {
            "found": found,
            "bone_count": len(self.pose_bones),
            "complete": (len(found["spine"]) >= 2 and
                        len(found["legs"]) >= 4 and
                        len(found["arms"]) >= 2)
        }


def generate_human_animation(armature_name: str, anim_type: str,
                              speed: float = 1.4, duration: float = 2.0) -> str:
    """Main entry point for human animation generation."""
    generator = HumanAnimationGenerator(armature_name)
    verification = generator.verify_human_rig()

    if not verification["complete"]:
        return f"WARNING: Rig may be incomplete. Found: {verification['found']}"

    if anim_type == "walk":
        return generator.generate_walk(speed, duration)
    elif anim_type == "idle":
        return generator.generate_idle("neutral", duration)
    elif anim_type == "run":
        return generator.generate_run(speed, duration / 1.5)
    else:
        return f"Unknown animation type: {anim_type}"


def apply_video_reference(armature_name: str, keyframes: List[tuple]) -> str:
    """Apply video-derived keyframes to armature."""
    generator = HumanAnimationGenerator(armature_name)
    return generator.apply_video_keyframes(keyframes)