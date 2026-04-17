"""
Human Animation Knowledge Base

Reference data for bipedal human animation including walk cycles,
run cycles, idle variations, and common motions.
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class HumanPose:
    """A single keyframe pose for human animation."""
    name: str
    phase: str  # 'contact', 'passing', 'apex', 'pass'
    frame: float
    bones: Dict[str, tuple]  # bone_name -> (rotation_euler XYZ in radians)


@dataclass
class HumanGaitCycle:
    """Complete gait cycle for human motion."""
    motion_type: str  # 'walk', 'jog', 'run', 'idle', '待机'
    speed: float  # m/s approximate
    cycle_duration: float  # frames at 24fps
    poses: List[HumanPose]
    hip_sway: float  # side-to-side hip motion amplitude
    shoulder_anticipation: float  # shoulder rotation direction
    arm_swing: float  # arm swing amplitude


# Human walk cycle - 8 keyframes over ~24 frames at 24fps (1 second)
HUMAN_WALK_CYCLE = HumanGaitCycle(
    motion_type="walk",
    speed=1.4,  # ~5 km/h
    cycle_duration=24,
    hip_sway=0.04,
    shoulder_anticipation=0.02,
    arm_swing=0.35,
    poses=[
        # Frame 0: Left foot contact, right leg passing behind
        HumanPose("left_contact", "contact", 0, {
            "pelvis": (0.0, 0.0, 0.02),  # slight hip drop
            "hip.L": (0.15, 0.05, -0.05),
            "knee.L": (0.1, 0, 0),
            "ankle.L": (0.0, 0, 0),
            "hip.R": (-0.2, -0.05, 0.1),
            "knee.R": (0.4, 0, 0),
            "ankle.R": (-0.15, 0, 0),
            "spine_01": (-0.02, 0, 0),
            "shoulder.L": (0.0, 0.1, 0.0),
            "shoulder.R": (0.0, -0.1, 0.0),
            "elbow.L": (0.3, 0, 0),
            "elbow.R": (-0.2, 0, 0),
        }),
        # Frame 3: Left foot flat, right leg advancing
        HumanPose("left_flat", "passing", 3, {
            "pelvis": (0.0, 0.01, -0.01),
            "hip.L": (0.05, 0, 0),
            "knee.L": (0.05, 0, 0),
            "ankle.L": (0.1, 0, 0),
            "hip.R": (0.0, -0.05, 0.05),
            "knee.R": (0.2, 0, 0),
            "ankle.R": (0.0, 0, 0),
            "spine_01": (-0.01, 0, 0),
        }),
        # Frame 6: Right foot passing left, left pushing off
        HumanPose("right_pass_left_stance", "passing", 6, {
            "pelvis": (0.0, -0.02, 0.02),
            "hip.L": (0.25, 0, 0.05),
            "knee.L": (0.0, 0, 0),
            "ankle.L": (-0.2, 0, 0),
            "hip.R": (0.0, 0.05, -0.05),
            "knee.R": (0.1, 0, 0),
            "ankle.R": (0.1, 0, 0),
            "spine_01": (0.02, 0, 0),
        }),
        # Frame 9: Opposite contact - right foot contact, left passing
        HumanPose("right_contact", "contact", 9, {
            "pelvis": (0.0, 0.0, -0.02),
            "hip.R": (0.15, -0.05, 0.05),
            "knee.R": (0.1, 0, 0),
            "ankle.R": (0.0, 0, 0),
            "hip.L": (-0.2, 0.05, -0.1),
            "knee.L": (0.4, 0, 0),
            "ankle.L": (-0.15, 0, 0),
            "spine_01": (0.02, 0, 0),
            "shoulder.L": (0.0, -0.1, 0.0),
            "shoulder.R": (0.0, 0.1, 0.0),
            "elbow.L": (-0.2, 0, 0),
            "elbow.R": (0.3, 0, 0),
        }),
        # Frame 12: Right foot flat
        HumanPose("right_flat", "passing", 12, {
            "pelvis": (0.0, -0.01, 0.01),
            "hip.R": (0.05, 0, 0),
            "knee.R": (0.05, 0, 0),
            "ankle.R": (0.1, 0, 0),
            "hip.L": (0.0, 0.05, -0.05),
            "knee.L": (0.2, 0, 0),
            "ankle.L": (0.0, 0, 0),
            "spine_01": (0.01, 0, 0),
        }),
        # Frame 15: Left passing, right pushing
        HumanPose("left_pass_right_stance", "passing", 15, {
            "pelvis": (0.0, 0.02, -0.02),
            "hip.R": (0.25, 0, -0.05),
            "knee.R": (0.0, 0, 0),
            "ankle.R": (-0.2, 0, 0),
            "hip.L": (0.0, -0.05, 0.05),
            "knee.L": (0.1, 0, 0),
            "ankle.L": (0.1, 0, 0),
            "spine_01": (-0.02, 0, 0),
        }),
        # Frame 24: Back to start (full cycle)
        HumanPose("reset", "contact", 24, {
            "pelvis": (0.0, 0.0, 0.02),
            "hip.L": (0.15, 0.05, -0.05),
            "knee.L": (0.1, 0, 0),
            "ankle.L": (0.0, 0, 0),
            "hip.R": (-0.2, -0.05, 0.1),
            "knee.R": (0.4, 0, 0),
            "ankle.R": (-0.15, 0, 0),
            "spine_01": (-0.02, 0, 0),
            "shoulder.L": (0.0, 0.1, 0.0),
            "shoulder.R": (0.0, -0.1, 0.0),
            "elbow.L": (0.3, 0, 0),
            "elbow.R": (-0.2, 0, 0),
        }),
    ]
)

# Human run cycle - faster, more dynamic
HUMAN_RUN_CYCLE = HumanGaitCycle(
    motion_type="run",
    speed=3.0,  # ~10 km/h
    cycle_duration=16,  # faster
    hip_sway=0.06,
    shoulder_anticipation=0.05,
    arm_swing=0.5,
    poses=[
        # Frame 0: Left foot contact, body forward lean
        HumanPose("left_contact", "contact", 0, {
            "pelvis": (0.1, 0.0, 0.05),
            "hip.L": (0.3, 0.1, -0.1),
            "knee.L": (0.5, 0, 0),
            "ankle.L": (0.2, 0, 0),
            "hip.R": (-0.4, -0.1, 0.2),
            "knee.R": (0.2, 0, 0),
            "ankle.R": (-0.3, 0, 0),
            "spine_01": (0.15, 0, 0),
            "spine_02": (0.1, 0, 0),
            "shoulder.L": (0.1, 0.15, 0),
            "shoulder.R": (-0.1, -0.15, 0),
            "elbow.L": (0.5, 0, 0),
            "elbow.R": (-0.1, 0, 0),
        }),
        # Frame 4: Flight phase - both feet off ground
        HumanPose("flight", "apex", 4, {
            "pelvis": (0.05, 0.0, 0.0),
            "hip.L": (-0.1, 0, 0),
            "knee.L": (0.6, 0, 0),
            "ankle.L": (-0.2, 0, 0),
            "hip.R": (-0.1, 0, 0),
            "knee.R": (0.6, 0, 0),
            "ankle.R": (-0.2, 0, 0),
            "spine_01": (0.08, 0, 0),
            "spine_02": (0.05, 0, 0),
            "shoulder.L": (0.2, 0, 0),
            "shoulder.R": (-0.2, 0, 0),
        }),
        # Frame 8: Right foot contact
        HumanPose("right_contact", "contact", 8, {
            "pelvis": (0.1, 0.0, -0.05),
            "hip.R": (0.3, -0.1, 0.1),
            "knee.R": (0.5, 0, 0),
            "ankle.R": (0.2, 0, 0),
            "hip.L": (-0.4, 0.1, -0.2),
            "knee.L": (0.2, 0, 0),
            "ankle.L": (-0.3, 0, 0),
            "spine_01": (0.15, 0, 0),
            "spine_02": (0.1, 0, 0),
            "shoulder.R": (0.1, 0.15, 0),
            "shoulder.L": (-0.1, -0.15, 0),
            "elbow.R": (0.5, 0, 0),
            "elbow.L": (-0.1, 0, 0),
        }),
        # Frame 12: Flight phase 2
        HumanPose("flight", "apex", 12, {
            "pelvis": (0.05, 0.0, 0.0),
            "hip.R": (-0.1, 0, 0),
            "knee.R": (0.6, 0, 0),
            "ankle.R": (-0.2, 0, 0),
            "hip.L": (-0.1, 0, 0),
            "knee.L": (0.6, 0, 0),
            "ankle.L": (-0.2, 0, 0),
            "spine_01": (0.08, 0, 0),
            "spine_02": (0.05, 0, 0),
            "shoulder.R": (0.2, 0, 0),
            "shoulder.L": (-0.2, 0, 0),
        }),
        # Frame 16: Back to start
        HumanPose("reset", "contact", 16, {
            "pelvis": (0.1, 0.0, 0.05),
            "hip.L": (0.3, 0.1, -0.1),
            "knee.L": (0.5, 0, 0),
            "ankle.L": (0.2, 0, 0),
            "hip.R": (-0.4, -0.1, 0.2),
            "knee.R": (0.2, 0, 0),
            "ankle.R": (-0.3, 0, 0),
            "spine_01": (0.15, 0, 0),
            "spine_02": (0.1, 0, 0),
            "shoulder.L": (0.1, 0.15, 0),
            "shoulder.R": (-0.1, -0.15, 0),
            "elbow.L": (0.5, 0, 0),
            "elbow.R": (-0.1, 0, 0),
        }),
    ]
)

# Human idle poses - breathing, weight shifts, subtle movements
HUMAN_IDLE_POSES = {
    "idle_neutral": [  # Standard idle - slight S-curve spine, relaxed arms
        {"name": "neutral", "frame": 0, "weight": 0.4,
         "pelvis tilt": 0.0, "spine curve": 0.02, "shoulder level": 0.0,
         "head tilt": 0.0, "arm hang": 0.0, "breath phase": 0.0},
        {"name": "inhale_top", "frame": 24, "weight": 0.2,
         "pelvis tilt": 0.01, "spine curve": 0.04, "shoulder level": 0.03,
         "head tilt": 0.0, "arm hang": 0.01, "breath phase": 0.5},
        {"name": "exhale_bottom", "frame": 48, "weight": 0.2,
         "pelvis tilt": -0.01, "spine curve": 0.0, "shoulder level": -0.02,
         "head tilt": 0.0, "arm hang": -0.01, "breath phase": 1.0},
        {"name": "shift_left", "frame": 72, "weight": 0.1,
         "pelvis tilt": 0.02, "spine curve": -0.01, "shoulder level": -0.01,
         "head tilt": 0.05, "arm hang": 0.0, "breath phase": 0.3},
        {"name": "shift_right", "frame": 96, "weight": 0.1,
         "pelvis tilt": -0.02, "spine curve": 0.01, "shoulder level": 0.01,
         "head tilt": -0.05, "arm hang": 0.0, "breath phase": 0.7},
        {"name": "reset", "frame": 120, "weight": 0.0,
         "pelvis tilt": 0.0, "spine curve": 0.02, "shoulder level": 0.0,
         "head tilt": 0.0, "arm hang": 0.0, "breath phase": 0.0},
    ],
    "idle_standing": [  # Alert standing - slightly more tension
        {"name": "neutral", "frame": 0, "weight": 0.5,
         "pelvis tilt": 0.01, "spine curve": 0.0, "shoulder level": 0.01,
         "head tilt": 0.0, "chest open": 0.02, "breath phase": 0.0},
        {"name": "weight_left", "frame": 40, "weight": 0.25,
         "pelvis tilt": 0.03, "spine curve": -0.01, "shoulder level": -0.01,
         "head tilt": 0.02, "chest open": 0.01, "breath phase": 0.3},
        {"name": "weight_right", "frame": 80, "weight": 0.25,
         "pelvis tilt": -0.03, "spine curve": 0.01, "shoulder level": 0.01,
         "head tilt": -0.02, "chest open": 0.01, "breath phase": 0.7},
    ],
    "idle_casual": [  # Relaxed casual - one hip higher, asymmetric
        {"name": "relaxed", "frame": 0, "weight": 0.4,
         "pelvis tilt": 0.03, "spine curve": 0.03, "shoulder level": -0.02,
         "head tilt": -0.03, "arm hang": 0.05, "breath phase": 0.0},
        {"name": "shift", "frame": 60, "weight": 0.3,
         "pelvis tilt": 0.01, "spine curve": 0.01, "shoulder level": 0.0,
         "head tilt": 0.0, "arm hang": 0.02, "breath phase": 0.5},
        {"name": "reset", "frame": 120, "weight": 0.3,
         "pelvis tilt": 0.03, "spine curve": 0.03, "shoulder level": -0.02,
         "head tilt": -0.03, "arm hang": 0.05, "breath phase": 1.0},
    ],
}

# SPEED REFERENCE for human locomotion
HUMAN_SPEED_RANGES = {
    "idle": (0, 0.5),  # standing still
    "slow_walk": (0.5, 1.2),  # leisurely
    "walk": (1.2, 2.0),  # normal
    "fast_walk": (2.0, 2.8),  # power walk
    "jog": (2.8, 4.5),  # light run
    "run": (4.5, 7.5),  # running
    "sprint": (7.5, 12.0),  # all out
}

# Standard human rig bone names
HUMAN_RIG_BONES = [
    "pelvis", "spine_01", "spine_02", "spine_03",
    "neck_01", "neck_02", "head",
    "shoulder.L", "upper_arm.L", "forearm.L", "hand.L",
    "shoulder.R", "upper_arm.R", "forearm.R", "hand.R",
    "hip.L", "thigh.L", "knee.L", "shin.L", "ankle.L", "foot.L",
    "hip.R", "thigh.R", "knee.R", "shin.R", "ankle.R", "foot.R",
]


def get_human_gait(speed: float) -> Optional[HumanGaitCycle]:
    """Get appropriate gait cycle for speed in m/s."""
    if speed < 0.5:
        return None  # idle
    elif speed < 2.8:
        return HUMAN_WALK_CYCLE
    else:
        return HUMAN_RUN_CYCLE


def get_idle_preset(preset: str = "neutral") -> List[dict]:
    """Get idle pose sequence."""
    if preset == "standing":
        return HUMAN_IDLE_POSES["idle_standing"]
    elif preset == "casual":
        return HUMAN_IDLE_POSES["idle_casual"]
    else:
        return HUMAN_IDLE_POSES["idle_neutral"]


def interpolate_human_pose(pose_a: HumanPose, pose_b: HumanPose, t: float) -> Dict[str, tuple]:
    """Linear interpolate between two human poses."""
    result = {}
    all_bones = set(pose_a.bones.keys()) | set(pose_b.bones.keys())

    for bone in all_bones:
        rot_a = pose_a.bones.get(bone, (0, 0, 0))
        rot_b = pose_b.bones.get(bone, (0, 0, 0))
        result[bone] = (
            rot_a[0] + (rot_b[0] - rot_a[0]) * t,
            rot_a[1] + (rot_b[1] - rot_a[1]) * t,
            rot_a[2] + (rot_b[2] - rot_a[2]) * t,
        )
    return result


def get_human_animation_summary() -> str:
    """Get AI-friendly summary of human animation characteristics."""
    lines = []

    lines.append("HUMAN BIPEDAL LOCOMOTION:")
    lines.append("")
    lines.append("WALK CYCLE (24 frames @ 24fps):")
    lines.append("- Diagonal gait: opposite arm/leg move together")
    lines.append("- Hip sway: ~4 degrees side-to-side")
    lines.append("- Counter-rotation: shoulders vs pelvis")
    lines.append("- Arm swing: ~35 degrees fore/aft")
    lines.append("- Single foot always on ground (no flight)")
    lines.append("")
    lines.append("RUN CYCLE (16 frames @ 24fps):")
    lines.append("- Flight phases: both feet off ground")
    lines.append("- Forward lean increases with speed")
    lines.append("- Arm swing amplitude increases")
    lines.append("- Hip bounce more pronounced")
    lines.append("")
    lines.append("IDLE ANIMATION (120 frames @ 24fps):")
    lines.append("- Breathing: 4-6 second cycle")
    lines.append("- Weight shifts: 3-5 second cycle")
    lines.append("- Subtle spine articulation")
    lines.append("- Head micro-movements")
    lines.append("")
    lines.append("SPEED TO GAIT MAPPING:")
    lines.append("- 0-0.5 m/s: idle (standing)")
    lines.append("- 0.5-2.8 m/s: walk cycle")
    lines.append("- 2.8-4.5 m/s: jog (transition)")
    lines.append("- 4.5+ m/s: run cycle")
    lines.append("")
    lines.append("HUMAN RIG BONES:")
    lines.append(", ".join(HUMAN_RIG_BONES[:15]) + "...")

    return "\n".join(lines)