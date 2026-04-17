"""
Dinosaur Animation Knowledge Base

Reference data for bipedal and quadrupedal dinosaur animation.
Includes pose libraries, gait timing, and procedural generation helpers.
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class DinoPose:
    """A single keyframe pose for a dinosaur."""
    name: str
    phase: str  # 'contact', 'passing', 'top', 'bottom'
    frame: float
    bones: Dict[str, tuple]  # bone_name -> (rotation_euler)


@dataclass
class GaitCycle:
    """Complete gait cycle for a dino type."""
    dino_type: str  # 'bipedal', 'quadrupedal'
    species: str
    step_count: int  # feet touching ground per cycle
    cycle_duration: float  # frames at 24fps
    poses: List[DinoPose]
    spine_wave: float  # amplitude of spinal movement
    tail_sway: float  # amplitude of tail movement


# BIPEDAL DINOSAUR GAITS
# Based on motion study references (noting stylized game animation differs from realism)

BIPEDAL_WALK = GaitCycle(
    dino_type="bipedal",
    species="generic_raptor",
    step_count=2,  # one foot always on ground (trot-like)
    cycle_duration=48,  # 2 seconds at 24fps
    spine_wave=0.08,  # radians of rotation
    tail_sway=0.15,
    poses=[
        # Raptor walk cycle - simplified 8 keyframe cycle
        # Frame 0: Left foot contact, right foot passing
        DinoPose("left_contact", "contact", 0, {
            "thigh.L": (0.1, 0, 0),
            "shin.L": (0.3, 0, 0),
            "thigh.R": (-0.4, 0, 0.1),
            "shin.R": (-0.2, 0, 0),
            "spine_01": (0.05, 0, 0),
            "spine_02": (0.03, 0, 0),
            "tail_01": (0, 0.1, 0),
        }),
        # Frame 6: Passing phase
        DinoPose("right_pass", "passing", 6, {
            "thigh.L": (0.05, 0, 0),
            "shin.L": (0.15, 0, 0),
            "thigh.R": (0.0, 0, 0),
            "shin.R": (0.1, 0, 0),
            "spine_01": (0.02, 0, 0),
            "spine_02": (0.01, 0, 0),
        }),
        # Frame 12: Right foot contact, left passing
        DinoPose("right_contact", "contact", 12, {
            "thigh.R": (0.1, 0, 0),
            "shin.R": (0.3, 0, 0),
            "thigh.L": (-0.4, 0, -0.1),
            "shin.L": (-0.2, 0, 0),
            "spine_01": (-0.05, 0, 0),
            "spine_02": (-0.03, 0, 0),
            "tail_01": (0, -0.1, 0),
        }),
        # Frame 18: Left passing
        DinoPose("left_pass", "passing", 18, {
            "thigh.R": (0.05, 0, 0),
            "shin.R": (0.15, 0, 0),
            "thigh.L": (0.0, 0, 0),
            "shin.L": (0.1, 0, 0),
            "spine_01": (-0.02, 0, 0),
            "spine_02": (-0.01, 0, 0),
        }),
        # Frame 24: Back to start (full cycle)
        DinoPose("reset", "contact", 24, {
            "thigh.L": (0.1, 0, 0),
            "shin.L": (0.3, 0, 0),
            "thigh.R": (-0.4, 0, 0.1),
            "shin.R": (-0.2, 0, 0),
            "spine_01": (0.05, 0, 0),
            "spine_02": (0.03, 0, 0),
            "tail_01": (0, 0.1, 0),
        }),
    ]
)

BIPEDAL_RUN = GaitCycle(
    dino_type="bipedal",
    species="generic_raptor",
    step_count=2,
    cycle_duration=24,  # faster
    spine_wave=0.15,
    tail_sway=0.25,
    poses=[
        # Running - more extreme poses, body leans forward
        DinoPose("left_contact", "contact", 0, {
            "thigh.L": (0.4, 0, 0.1),
            "shin.L": (0.6, 0, 0),
            "thigh.R": (-0.6, 0, 0.2),
            "shin.R": (0.1, 0, 0),
            "spine_01": (0.15, 0, 0),
            "spine_02": (0.1, 0, 0),
            "tail_01": (0, 0.2, 0),
            "neck": (-0.2, 0, 0),
        }),
        # Frame 6: Mid-air, both feet off ground
        DinoPose("airborne", "top", 6, {
            "thigh.L": (0.1, 0, 0),
            "shin.L": (0.4, 0, 0),
            "thigh.R": (0.1, 0, 0),
            "shin.R": (0.4, 0, 0),
            "spine_01": (0.08, 0, 0),
            "spine_02": (0.05, 0, 0),
        }),
        # Frame 12: Right foot contact
        DinoPose("right_contact", "contact", 12, {
            "thigh.R": (0.4, 0, -0.1),
            "shin.R": (0.6, 0, 0),
            "thigh.L": (-0.6, 0, -0.2),
            "shin.L": (0.1, 0, 0),
            "spine_01": (-0.15, 0, 0),
            "spine_02": (-0.1, 0, 0),
            "tail_01": (0, -0.2, 0),
            "neck": (0.1, 0, 0),
        }),
        # Frame 18: Mid-air
        DinoPose("airborne", "top", 18, {
            "thigh.R": (0.1, 0, 0),
            "shin.R": (0.4, 0, 0),
            "thigh.L": (0.1, 0, 0),
            "shin.L": (0.4, 0, 0),
            "spine_01": (-0.08, 0, 0),
            "spine_02": (-0.05, 0, 0),
        }),
        # Frame 24: Back to start
        DinoPose("reset", "contact", 24, {
            "thigh.L": (0.4, 0, 0.1),
            "shin.L": (0.6, 0, 0),
            "thigh.R": (-0.6, 0, 0.2),
            "shin.R": (0.1, 0, 0),
            "spine_01": (0.15, 0, 0),
            "spine_02": (0.1, 0, 0),
            "tail_01": (0, 0.2, 0),
            "neck": (-0.2, 0, 0),
        }),
    ]
)

# QUADRUPEDAL DINOSAUR GAITS
QUADRUPEDAL_WALK = GaitCycle(
    dino_type="quadrupedal",
    species="generic_sauropod",
    step_count=4,  # trot: front-left + back-right together
    cycle_duration=64,  # slower, heavier
    spine_wave=0.05,  # subtle wave for large bodies
    tail_sway=0.1,
    poses=[
        # Quadruped walk - 4-beat trot
        # Frame 0: Front-left + Back-right contact (diagonal gait)
        DinoPose("diag_contact_1", "contact", 0, {
            "front_leg.L.upper": (0.1, 0, 0.05),
            "front_leg.L.lower": (0.2, 0, 0),
            "back_leg.R.upper": (0.15, 0, -0.05),
            "back_leg.R.lower": (0.25, 0, 0),
            "spine": (0.02, 0, 0),
            "neck": (0.05, 0, 0),
            "tail": (0, 0.08, 0),
        }),
        # Frame 16: Front-right + Back-left contact
        DinoPose("diag_contact_2", "contact", 16, {
            "front_leg.R.upper": (0.1, 0, -0.05),
            "front_leg.R.lower": (0.2, 0, 0),
            "back_leg.L.upper": (0.15, 0, 0.05),
            "back_leg.L.lower": (0.25, 0, 0),
            "spine": (-0.02, 0, 0),
            "neck": (-0.05, 0, 0),
            "tail": (0, -0.08, 0),
        }),
        # Frame 32: Back to first diagonal
        DinoPose("diag_contact_1", "contact", 32, {
            "front_leg.L.upper": (0.1, 0, 0.05),
            "front_leg.L.lower": (0.2, 0, 0),
            "back_leg.R.upper": (0.15, 0, -0.05),
            "back_leg.R.lower": (0.25, 0, 0),
            "spine": (0.02, 0, 0),
            "neck": (0.05, 0, 0),
            "tail": (0, 0.08, 0),
        }),
    ]
)

QUADRUPEDAL_RUN = GaitCycle(
    dino_type="quadrupedal",
    species="generic_theropod",
    step_count=4,
    cycle_duration=32,  # faster
    spine_wave=0.12,
    tail_sway=0.2,
    poses=[
        # Faster quadruped gallop
        DinoPose("gather", "passing", 0, {
            "front_leg.L.upper": (-0.2, 0, 0),
            "front_leg.R.upper": (0.1, 0, 0),
            "back_leg.L.upper": (-0.1, 0, 0),
            "back_leg.R.upper": (0.2, 0, 0),
            "spine": (0.1, 0, 0),
            "neck": (0.15, 0, 0),
        }),
        DinoPose("push", "contact", 8, {
            "back_leg.R.upper": (0.3, 0, 0),
            "back_leg.R.lower": (0.4, 0, 0),
            "spine": (0.05, 0, 0),
            "tail": (0, 0.15, 0),
        }),
        DinoPose("extend", "passing", 16, {
            "front_leg.L.upper": (0.3, 0, 0),
            "front_leg.R.upper": (-0.2, 0, 0),
            "back_leg.L.upper": (0.1, 0, 0),
            "back_leg.R.upper": (-0.1, 0, 0),
            "spine": (0, 0, 0),
        }),
        DinoPose("collect", "passing", 24, {
            "front_leg.R.upper": (-0.2, 0, 0),
            "back_leg.L.upper": (-0.1, 0, 0),
            "spine": (-0.08, 0, 0),
            "neck": (-0.1, 0, 0),
        }),
        DinoPose("reset", "passing", 32, {
            "front_leg.L.upper": (-0.2, 0, 0),
            "front_leg.R.upper": (0.1, 0, 0),
            "back_leg.L.upper": (-0.1, 0, 0),
            "back_leg.R.upper": (0.2, 0, 0),
            "spine": (0.1, 0, 0),
            "neck": (0.15, 0, 0),
        }),
    ]
)

# IDLE POSES - critical for game animators
IDLE_POSES = {
    "bipedal_idle_light": [  # Raptor alert idle - subtle shifts
        {"name": "neutral", "weight": 0.4, "spine_bend": 0.0, "head_tilt": 0.0, "breath_depth": 0.02},
        {"name": "shift_left", "weight": 0.2, "spine_bend": 0.03, "head_tilt": 0.05, "breath_depth": 0.01},
        {"name": "shift_right", "weight": 0.2, "spine_bend": -0.03, "head_tilt": -0.05, "breath_depth": 0.01},
        {"name": "head_up", "weight": 0.1, "spine_bend": 0.02, "head_tilt": 0.1, "breath_depth": 0.03},
        {"name": "head_down", "weight": 0.1, "spine_bend": -0.02, "head_tilt": -0.08, "breath_depth": 0.02},
    ],
    "bipedal_idle_heavy": [  # T-Rex heavy idle - slow, weight shifts
        {"name": "neutral", "weight": 0.5, "spine_bend": 0.0, "head_tilt": 0.0, "breath_depth": 0.04},
        {"name": "sway", "weight": 0.3, "spine_bend": 0.05, "head_tilt": 0.02, "breath_depth": 0.03},
        {"name": "sway", "weight": 0.2, "spine_bend": -0.05, "head_tilt": -0.02, "breath_depth": 0.03},
    ],
    "quadrupedal_idle_standing": [  # Standard quad standing
        {"name": "neutral", "weight": 0.5, "spine_bend": 0.0, "neck_raise": 0.0, "tail_sway": 0.0},
        {"name": "shift_fl", "weight": 0.15, "spine_bend": 0.02, "neck_raise": 0.05, "tail_sway": 0.05},
        {"name": "shift_fr", "weight": 0.15, "spine_bend": -0.02, "neck_raise": -0.05, "tail_sway": -0.05},
        {"name": "head_check", "weight": 0.2, "spine_bend": 0.01, "neck_raise": 0.1, "tail_sway": 0.02},
    ],
}

# SPEED METERS - for blending animations
GAIT_SPEEDS = {
    "bipedal": {
        "idle": (0, 0.5),
        "walk": (0.5, 4.0),  # units/sec
        "trot": (4.0, 8.0),
        "run": (8.0, 15.0),
        "sprint": (15.0, 30.0),
    },
    "quadrupedal": {
        "idle": (0, 0.3),
        "walk": (0.3, 3.0),
        "trot": (3.0, 7.0),
        "gallop": (7.0, 14.0),
        "sprint": (14.0, 25.0),
    }
}


def get_gait_cycle(dino_type: str, speed: str) -> Optional[GaitCycle]:
    """Get appropriate gait cycle for dino type and speed."""
    if dino_type == "bipedal":
        if speed in ("walk", "slow"):
            return BIPEDAL_WALK
        elif speed in ("run", "trot", "fast"):
            return BIPEDAL_RUN
    elif dino_type == "quadrupedal":
        if speed in ("walk", "slow"):
            return QUADRUPEDAL_WALK
        elif speed in ("run", "gallop", "fast"):
            return QUADRUPEDAL_RUN
    return None


def get_idle_preset(dino_type: str, weight: str = "medium") -> List[dict]:
    """Get idle pose sequence for dino type."""
    if dino_type == "bipedal":
        if weight == "heavy":
            return IDLE_POSES["bipedal_idle_heavy"]
        else:
            return IDLE_POSES["bipedal_idle_light"]
    else:
        return IDLE_POSES["quadrupedal_idle_standing"]


def interpolate_pose(pose_a: DinoPose, pose_b: DinoPose, t: float) -> Dict[str, tuple]:
    """Linear interpolate between two poses."""
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


def get_animation_summary(dino_type: str) -> str:
    """Get AI-friendly summary of dino animation characteristics."""
    summary = []

    if dino_type == "bipedal":
        summary.append("BIPEDAL LOCOMOTION:")
        summary.append("- Heavy reliance on tail for balance")
        summary.append("- Spine acts as lever, slight wave during movement")
        summary.append("- Head movement counterbalances step cycles")
        summary.append("- Arms are secondary locators (smaller range)")
        summary.append("")
        summary.append("IDLE BEHAVIORS:")
        summary.append("- Weight shifts from side to side (3-5 sec cycles)")
        summary.append("- Subtle spine breathing (slow, 4-6 sec)")
        summary.append("- Head scans environment (head only rotation)")
        summary.append("- Tail slight sway (0.5-1 sec, higher priority than walk)")
    else:  # quadrupedal
        summary.append("QUADRUPEDAL LOCOMOTION:")
        summary.append("- Diagonal gait pattern (trot: opposite legs sync)")
        summary.append("- Spine undulates front-to-back, subtle wave amplitude")
        summary.append("- Neck and tail counterbalance each other")
        summary.append("- More stable base, less tail involvement than bipedal")
        summary.append("")
        summary.append("IDLE BEHAVIORS:")
        summary.append("- Four-legged stance, weight distributed")
        summary.append("- Slow neck scan (env scanning)")
        summary.append("- Tail swish (insects, weather)")
        summary.append("- Ear/twitch animations (quick, 0.5-1 sec)")

    return "\n".join(summary)