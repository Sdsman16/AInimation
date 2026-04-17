"""
Animation analysis for loop detection and suggestions
"""
import bpy


def detect_seamless_loop(action) -> bool:
    """Check if animation is designed to loop seamlessly."""
    if not action.use_cyclic:
        return False

    # Compare first and last keyframe values for all FCurves
    tolerance = 0.001

    for fcurve in action.fcurves:
        if len(fcurve.keyframe_points) < 2:
            continue

        first_kf = fcurve.keyframe_points[0]
        last_kf = fcurve.keyframe_points[-1]

        # Check if first and last values match
        if abs(first_kf.co[1] - last_kf.co[1]) > tolerance:
            return False

        # Also check handles for smooth interpolation at loop point
        if abs(first_kf.handle_left[1] - last_kf.handle_right[1]) > tolerance:
            return False

    return True


def get_loop_suggestions(action) -> str:
    """Generate AI-friendly analysis of animation loop quality."""

    if not action:
        return "No action selected."

    suggestions = []
    suggestions.append(f"Action: {action.name}")
    suggestions.append(f"Frame Range: {action.frame_start} to {action.frame_end}")

    # Check cyclic setting
    if action.use_cyclic:
        suggestions.append("Cyclic: Enabled")
    else:
        suggestions.append("Cyclic: Disabled (animation plays once)")

    # Analyze keyframe continuity
    seamless = detect_seamless_loop(action)
    if seamless:
        suggestions.append("Loop Quality: Seamless (first/last keyframes match)")
    else:
        suggestions.append("Loop Quality: Not seamless (first/last keyframes differ)")

    # FCurve analysis
    rotation_curves = []
    location_curves = []
    scale_curves = []

    for fcurve in action.fcurves:
        if 'rotation' in fcurve.data_path:
            rotation_curves.append(fcurve)
        elif 'location' in fcurve.data_path:
            location_curves.append(fcurve)
        elif 'scale' in fcurve.data_path:
            scale_curves.append(fcurve)

    if rotation_curves:
        suggestions.append(f"Rotation F-Curves: {len(rotation_curves)}")
    if location_curves:
        suggestions.append(f"Location F-Curves: {len(location_curves)}")
    if scale_curves:
        suggestions.append(f"Scale F-Curves: {len(scale_curves)}")

    # Keyframe count
    total_keyframes = sum(len(fc.keyframe_points) for fc in action.fcurves)
    suggestions.append(f"Total Keyframes: {total_keyframes}")

    return "\n".join(suggestions)


def get_action_summary(action) -> dict:
    """Get detailed summary of an action."""

    if not action:
        return {}

    summary = {
        'name': action.name,
        'frame_start': action.frame_start,
        'frame_end': action.frame_end,
        'duration': action.frame_end - action.frame_start,
        'use_cyclic': action.use_cyclic,
        'is_seamless_loop': detect_seamless_loop(action),
        'fcurves': [],
    }

    for fcurve in action.fcurves:
        fc_info = {
            'data_path': fcurve.data_path,
            'array_index': fcurve.array_index,
            'keyframe_count': len(fcurve.keyframe_points),
        }

        # Get value range
        if fcurve.keyframe_points:
            values = [kf.co[1] for kf in fcurve.keyframe_points]
            fc_info['min_value'] = min(values)
            fc_info['max_value'] = max(values)
            fc_info['first_value'] = values[0]
            fc_info['last_value'] = values[-1]

        summary['fcurves'].append(fc_info)

    return summary


def get_available_actions() -> list:
    """Get list of all available actions."""
    return [{'name': a.name, 'frame_range': (a.frame_start, a.frame_end)} for a in bpy.data.actions]