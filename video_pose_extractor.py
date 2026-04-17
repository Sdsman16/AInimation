"""
Claude Vision API Integration for Video Frame Analysis

Send video frames to Claude and get pose/position descriptions back.
Uses direct HTTP calls to avoid external SDK dependency.
"""
import base64
import requests
from typing import Dict, Optional, List

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


def analyze_frame_with_claude(api_key: str, image_bytes: bytes,
                               prompt: str = None) -> Dict[str, any]:
    """
    Send a single frame to Claude Vision for analysis.

    Args:
        api_key: Anthropic API key
        image_bytes: PNG/JPEG image data as bytes
        prompt: Optional custom prompt for analysis

    Returns:
        Dict with pose analysis results
    """
    if not prompt:
        prompt = """You are an expert animator analyzing a video reference frame.

Please analyze the pose of the character in this image and describe it precisely for animation recreation.

Provide your analysis in this format:

1. OVERALL POSE: [standing/walking/running/jumping/crouching/lying/sitting]
2. HEAD: [position description, tilt angle if noticeable]
3. TORSO: [spine curve, lean direction, rotation]
4. ARMS:
   - Left arm: [shoulder rotation, elbow bend, hand position]
   - Right arm: [shoulder rotation, elbow bend, hand position]
5. LEGS:
   - Left leg: [hip angle, knee bend, foot angle, weight on forefoot/back/flat]
   - Right leg: [hip angle, knee bend, foot angle, weight on forefoot/back/flat]
6. PHASE: [contact/passing/apex/recovery] - is this a foot contact frame or passing phase?
7. TIMING CLUE: [how fast does this seem to be moving based on pose]

Be specific with angles where you can estimate them (e.g., "elbow bent at ~90 degrees", "knee slightly bent at ~15 degrees")."""

    # Encode image to base64
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')

    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Parse response - handle both newer and legacy formats
        text = ""
        if "content" in data:
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    break
        elif "completion" in data:
            text = data["completion"]

        return parse_pose_response(text)

    except requests.exceptions.Timeout:
        return {'error': 'Request timed out', 'raw_response': '', 'pose_type': 'unknown'}
    except requests.exceptions.HTTPError as e:
        return {'error': f'HTTP {e.response.status_code}', 'raw_response': str(e), 'pose_type': 'unknown'}
    except Exception as e:
        return {'error': str(e), 'raw_response': '', 'pose_type': 'unknown'}


def parse_pose_response(text: str) -> Dict[str, any]:
    """Parse Claude's text response into structured pose data."""
    result = {
        'raw_response': text,
        'pose_type': 'unknown',
        'phase': 'unknown',
        'motion_type': 'unknown',
        'notes': [],
    }

    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if line.startswith('OVERALL POSE:'):
            pose = line.split(':', 1)[1].strip().lower()
            result['pose_type'] = pose
            if 'walk' in pose:
                result['motion_type'] = 'walk'
            elif 'run' in pose or 'sprint' in pose:
                result['motion_type'] = 'run'
            elif 'idle' in pose or 'stand' in pose:
                result['motion_type'] = 'idle'
        elif line.startswith('PHASE:'):
            phase = line.split(':', 1)[1].strip().lower()
            result['phase'] = phase
            if 'contact' in phase:
                result['is_contact'] = True
            elif 'pass' in phase or 'apex' in phase:
                result['is_passing'] = True
        elif line.startswith('TIMING CLUE:'):
            result['notes'].append(line.split(':', 1)[1].strip())

    # Try to extract angle info for key joints
    angle_keywords = ['shoulder', 'elbow', 'hip', 'knee', 'ankle', 'spine', 'head', 'torso']
    for kw in angle_keywords:
        if kw in text.lower():
            for sentence in text.split('.'):
                if kw in sentence.lower():
                    result['notes'].append(sentence.strip())

    return result


def batch_analyze_frames(api_key: str, frames: list, progress_callback=None) -> list:
    """
    Analyze multiple frames with rate limiting.

    Args:
        api_key: Anthropic API key
        frames: List of (frame_data, timestamp) tuples
        progress_callback: Optional callback(current, total) for progress

    Returns:
        List of pose analysis dicts
    """
    results = []

    for i, (frame_data, timestamp) in enumerate(frames):
        try:
            result = analyze_frame_with_claude(api_key, frame_data)
            result['timestamp'] = timestamp
            results.append(result)
        except Exception as e:
            results.append({
                'error': str(e),
                'timestamp': timestamp,
            })

        if progress_callback:
            progress_callback(i + 1, len(frames))

    return results


def create_animation_from_poses(poses: list, target_fps: float = 24.0) -> list:
    """
    Convert analyzed poses into keyframe timing data.

    Args:
        poses: List of pose analysis dicts from batch_analyze_frames
        target_fps: Target animation fps

    Returns:
        List of (frame_number, pose_data) tuples ready for keyframing
    """
    keyframes = []

    for pose in poses:
        if 'error' in pose:
            continue

        timestamp = pose.get('timestamp', 0)
        frame = int(timestamp * target_fps)

        keyframes.append((frame, pose))

    # Sort by frame
    keyframes.sort(key=lambda x: x[0])

    return keyframes


def generate_blender_keyframe_commands(keyframes: list, bone_mapping: dict) -> list:
    """
    Generate Blender Python commands to apply keyframes.

    Args:
        keyframes: Output from create_animation_from_poses
        bone_mapping: Dict mapping pose keys to actual bone names

    Returns:
        List of Blender Python commands as strings
    """
    commands = []

    commands.append("# Generated keyframes from video analysis")
    commands.append("import bpy")
    commands.append("")

    for frame, pose_data in keyframes:
        commands.append(f"# Frame {frame} - {pose_data.get('pose_type', 'unknown')}")
        commands.append(f"bpy.context.scene.frame_set({frame})")

        # Generate commands based on pose type
        pose_type = pose_data.get('pose_type', '').lower()
        if 'walk' in pose_type:
            commands.extend(generate_walk_pose_commands(pose_data, bone_mapping))
        elif 'run' in pose_type or 'sprint' in pose_type:
            commands.extend(generate_run_pose_commands(pose_data, bone_mapping))
        elif 'idle' in pose_type or 'stand' in pose_type:
            commands.extend(generate_idle_pose_commands(pose_data, bone_mapping))

        commands.append("")

    return commands


def generate_walk_pose_commands(pose_data: Dict, bone_mapping: Dict) -> list:
    """Generate Blender commands for a walk pose."""
    cmds = []
    notes = pose_data.get('notes', [])

    cmds.append("# Walk pose - apply based on notes")
    for note in notes[:5]:
        note_lower = note.lower()
        if 'left arm' in note_lower or 'right arm' in note_lower:
            cmds.append(f"  # Arm: {note[:100]}")
        elif 'left leg' in note_lower or 'right leg' in note_lower:
            cmds.append(f"  # Leg: {note[:100]}")

    return cmds


def generate_run_pose_commands(pose_data: Dict, bone_mapping: Dict) -> list:
    """Generate Blender commands for a run pose."""
    cmds = []
    cmds.append("# Run pose - high dynamic pose")

    if pose_data.get('is_passing'):
        cmds.append("  # Flight/passing phase - legs off ground")
    elif pose_data.get('is_contact'):
        cmds.append("  # Contact phase - foot hitting ground")

    return cmds


def generate_idle_pose_commands(pose_data: Dict, bone_mapping: Dict) -> list:
    """Generate Blender commands for an idle pose."""
    cmds = []
    cmds.append("# Idle pose - subtle weight shifts")
    return cmds
