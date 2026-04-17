"""
Video Reference Analyzer for Animation

Analyze video references to extract pose data, timing, and motion patterns.
Uses Claude's vision capability to understand poses from video frames.
"""
import bpy
import os
import subprocess
import tempfile
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from mathutils import Vector
import numpy as np

# Try to import CV2, fall back gracefully
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


@dataclass
class VideoFrame:
    """A single frame from video with extracted pose data."""
    frame_number: int
    timestamp: float  # seconds
    image_data: bytes  # PNG bytes
    pose_data: Optional[Dict[str, Vector]] = None
    motion_notes: str = ""


@dataclass
class VideoAnalysis:
    """Complete analysis of video reference."""
    video_path: str
    duration: float
    fps: float
    resolution: Tuple[int, int]
    frame_count: int
    detected_poses: List[Dict[str, any]] = field(default_factory=list)
    timing_data: Dict[str, float] = field(default_factory=dict)
    motion_type: str = "unknown"  # 'walk', 'run', 'idle', 'jump', 'custom'
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)


class VideoReferenceAnalyzer:
    """Analyze video references for animation."""

    def __init__(self, video_path: str = None):
        self.video_path = video_path
        self.frames: List[VideoFrame] = []
        self.analysis: Optional[VideoAnalysis] = None

    def load_video(self, video_path: str) -> bool:
        """Load video and extract metadata."""
        self.video_path = video_path

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not HAS_CV2:
            # Use ffprobe/ffmpeg directly
            return self._load_video_with_ffmpeg(video_path)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        self.metadata = {
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
        }
        cap.release()
        return True

    def _load_video_with_ffmpeg(self, video_path: str) -> bool:
        """Load video metadata using ffmpeg."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                if len(parts) >= 4:
                    width = int(parts[0])
                    height = int(parts[1])
                    fps_parts = parts[2].split('/')
                    fps = float(fps_parts[0]) / float(fps_parts[1]) if '/' in parts[2] else float(parts[2])
                    frame_count = int(parts[3])
                    duration = float(parts[4]) if len(parts) > 4 else frame_count / fps

                    self.metadata = {
                        'fps': fps,
                        'frame_count': frame_count,
                        'width': width,
                        'height': height,
                        'duration': duration,
                    }
                    return True
        except Exception as e:
            self.errors.append(f"ffprobe failed: {str(e)}")

        return False

    def extract_frames(self, interval_seconds: float = 0.5, max_frames: int = 20) -> List[VideoFrame]:
        """Extract frames at regular intervals for analysis."""
        if not self.video_path or not os.path.exists(self.video_path):
            raise ValueError("No video loaded")

        if not self.metadata:
            raise ValueError("Video metadata not loaded")

        frames = []
        duration = self.metadata.get('duration', 0)
        fps = self.metadata.get('fps', 30)

        # Calculate frame intervals
        current_time = 0.0
        frame_idx = 0

        while current_time < duration and len(frames) < max_frames:
            frame_data = self._extract_frame_at_time(current_time)
            if frame_data:
                frames.append(VideoFrame(
                    frame_number=frame_idx,
                    timestamp=current_time,
                    image_data=frame_data,
                ))
            current_time += interval_seconds
            frame_idx += 1

        self.frames = frames
        return frames

    def _extract_frame_at_time(self, timestamp: float) -> Optional[bytes]:
        """Extract a single frame at given timestamp."""
        if HAS_CV2:
            cap = cv2.VideoCapture(self.video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = cap.read()
            cap.release()

            if ret:
                # Encode as PNG
                encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
                _, img_encoded = cv2.imencode('.png', frame, encode_param)
                return img_encoded.tobytes()
        else:
            # Use ffmpeg
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                tmp_path = f.name

            cmd = [
                'ffmpeg', '-y', '-ss', str(timestamp),
                '-i', self.video_path,
                '-vframes', '1',
                '-f', 'image2pipe',
                '-vcodec', 'png',
                '-'
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return None

    def analyze_frames_with_vision(self, api_key: str, prompt: str = None) -> List[Dict]:
        """Send frames to Claude vision for pose analysis."""
        if not self.frames:
            raise ValueError("No frames extracted. Call extract_frames() first.")

        if not prompt:
            prompt = """Analyze this video frame for animation reference.
        Identify the pose of the character in this frame.
        For each visible body part, estimate the rotation angles if possible.
        Describe the overall pose phase (contact, passing, apex, etc).
        Focus on: head position, spine curve, arm angles, leg angles, foot placement.
        Return your analysis as a structured description."""

        from .video_pose_extractor import analyze_frame_with_claude

        results = []
        for frame in self.frames:
            try:
                pose_info = analyze_frame_with_claude(api_key, frame.image_data, prompt)
                frame.pose_data = pose_info
                results.append(pose_info)
            except Exception as e:
                self.errors.append(f"Frame {frame.frame_number} analysis failed: {str(e)}")

        return results

    def detect_motion_type(self) -> str:
        """Detect overall motion type from analyzed frames."""
        if not self.frames:
            return "unknown"

        # Analyze timing between key poses
        contact_frames = [f for f in self.frames if f.pose_data and f.pose_data.get('phase') == 'contact']

        if len(contact_frames) >= 2:
            avg_interval = (contact_frames[-1].timestamp - contact_frames[0].timestamp) / (len(contact_frames) - 1)

            if avg_interval > 0.8:
                return "walk"
            elif avg_interval > 0.4:
                return "run"
            else:
                return "sprint"

        # Check for flight phases (indicates running)
        flight_frames = [f for f in self.frames if f.pose_data and 'flight' in str(f.pose_data)]
        if flight_frames:
            return "run"

        # Check if mostly static (idle)
        if len(self.frames) <= 5:
            return "idle"

        return "custom"

    def generate_timing_report(self) -> Dict[str, float]:
        """Generate timing analysis from frames."""
        if not self.frames:
            return {}

        timing = {
            'total_duration': self.metadata.get('duration', 0),
            'fps': self.metadata.get('fps', 0),
            'frame_count': len(self.frames),
            'avg_frame_interval': 0,
        }

        if len(self.frames) > 1:
            intervals = [self.frames[i+1].timestamp - self.frames[i].timestamp for i in range(len(self.frames)-1)]
            timing['avg_frame_interval'] = sum(intervals) / len(intervals)

        timing['detected_motion'] = self.detect_motion_type()

        return timing

    def export_keyframes_for_blender(self) -> List[Tuple[float, Dict]]:
        """Export keyframes as (time, pose_dict) tuples for Blender."""
        keyframes = []

        for frame in self.frames:
            if frame.pose_data and frame.timestamp > 0:
                keyframes.append((frame.timestamp, frame.pose_data))

        return keyframes


def analyze_video_reference(video_path: str, api_key: str,
                            interval: float = 0.5, max_frames: int = 20) -> VideoAnalysis:
    """
    Main entry point - analyze video reference.

    Args:
        video_path: Path to video file
        api_key: Anthropic API key
        interval: Seconds between frames to analyze
        max_frames: Maximum frames to analyze

    Returns:
        VideoAnalysis object with pose data and timing
    """
    analyzer = VideoReferenceAnalyzer()

    # Load video
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    try:
        analyzer.load_video(video_path)
    except Exception as e:
        return VideoAnalysis(
            video_path=video_path,
            errors=[f"Failed to load video: {str(e)}"]
        )

    # Extract frames
    analyzer.extract_frames(interval_seconds=interval, max_frames=max_frames)

    # Analyze with vision
    analyzer.analyze_frames_with_vision(api_key)

    # Generate analysis
    motion_type = analyzer.detect_motion_type()
    timing = analyzer.generate_timing_report()

    analysis = VideoAnalysis(
        video_path=video_path,
        duration=analyzer.metadata.get('duration', 0),
        fps=analyzer.metadata.get('fps', 0),
        resolution=(analyzer.metadata.get('width', 0), analyzer.metadata.get('height', 0)),
        frame_count=len(analyzer.frames),
        detected_poses=[f.pose_data for f in analyzer.frames if f.pose_data],
        timing_data=timing,
        motion_type=motion_type,
        confidence=0.7 if analyzer.frames else 0.0,
        errors=analyzer.errors,
    )

    analyzer.analysis = analysis
    return analysis


def get_frame_thumbnail(frame: VideoFrame, max_size: int = 256) -> bytes:
    """Resize frame for thumbnail display."""
    if not HAS_CV2:
        return frame.image_data

    try:
        nparr = np.frombuffer(frame.image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        h, w = img.shape[:2]
        scale = max_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)

        thumb = cv2.resize(img, (new_w, new_h))
        _, encoded = cv2.imencode('.jpg', thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return encoded.tobytes()
    except:
        return frame.image_data