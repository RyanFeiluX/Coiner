import os
import subprocess
import time
from typing import List, Optional

from loguru import logger
from moviepy import (
    AudioFileClip,
    concatenate_videoclips,
    concatenate_audioclips,
    VideoFileClip,
    TextClip,
    AudioClip,
    ColorClip,
    ImageClip,
)
from app.utils.composite_clip_factory import create_composite_video_clip, safe_concatenate_videoclips, ensure_clip_duration
from app.config.config import load_config
from app.utils import utils
from app.services.video_utils import wrap_text, parse_color

from app.services.video_utils import (
    close_clip,
    get_video_codec,
    get_video_encoding_params,
    audio_codec,
    fps,
    create_encoding_progress_monitor,
)


def _get_ffmpeg_exe() -> str:
    """Return the FFmpeg executable path, respecting the IMAGEIO_FFMPEG_EXE env var."""
    return os.environ.get("IMAGEIO_FFMPEG_EXE", "ffmpeg")


def _get_font_family_name(font_path: str) -> str:
    """
    Extract the font family name from a font file using PIL.
    
    FFmpeg's subtitles filter (libass) needs a font family name (e.g. 'ST Heiti Medium')
    for the FontName style property, not a filename. PIL can read this from the font
    metadata reliably.
    
    Args:
        font_path: Absolute path to the font file (TTF or TTC).
    
    Returns:
        Font family name string. Falls back to filename stem on error.
    """
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(font_path, 12)
        # getname() returns (family_name, style_name)
        return font.getname()[0]
    except Exception:
        # Fallback: use the filename without extension
        return os.path.splitext(os.path.basename(font_path))[0]


def _generate_pink_noise(duration: float, sample_rate: int, amplitude: float = 0.0005) -> "np.ndarray":
    """
    Generate pink noise using FFT-based 1/f filtering.
    
    Pink noise (1/f spectrum) at very low amplitude prevents AAC encoder
    from producing clicks/pops on the transition from silence to voice.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Peak amplitude (default 0.0005 for near-silence)
        
    Returns:
        1D numpy array of audio samples
    """
    import numpy as np
    n = int(duration * sample_rate)
    if n <= 0:
        return np.array([], dtype=np.float64)

    white = np.random.randn(n)
    fft = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1 / sample_rate)
    freqs[0] = freqs[1] if len(freqs) > 1 else 1  # avoid DC division by zero
    pink = np.fft.irfft(fft / np.sqrt(freqs + 1e-10), n=n)
    peak = np.max(np.abs(pink))
    if peak > 0:
        pink = pink / peak * amplitude
    return pink


def create_silence_prefix_video(task_id: str, params, duration: float = 0.5, first_scene_video_path: str = None, sample_rate: int = 44100, channels: int = 2) -> str:
    """
    Create a silence prefix video clip as a standalone scene using MoviePy.
    
    Args:
        task_id: Task ID for file paths
        params: Video parameters (for resolution, background color, etc.)
        duration: Duration of silence prefix in seconds
        first_scene_video_path: Path to the first scene video (used to get first frame)
        sample_rate: Audio sample rate in Hz (must match scene videos for stream-copy)
        channels: Number of audio channels (must match scene videos for stream-copy)
        
    Returns:
        Path to the silence prefix video file, or None if failed
    """
    import numpy as np
    try:
        output_path = os.path.join(utils.task_dir(task_id), "silence_prefix.mp4")

        # ── A. Create the video clip ──
        if first_scene_video_path and os.path.exists(first_scene_video_path):
            scene = VideoFileClip(first_scene_video_path)
            try:
                frame = scene.get_frame(0)
            finally:
                scene.close()
            video_clip = ImageClip(frame, duration=duration)
            logger.info(f"Creating silence prefix video from first frame: {first_scene_video_path}")
        else:
            target_width = 1080
            target_height = 1920

            if hasattr(params, 'video_aspect') and params.video_aspect:
                from app.models.schema import VideoAspect
                video_aspect = params.video_aspect
                if isinstance(video_aspect, str):
                    try:
                        video_aspect = VideoAspect(video_aspect)
                    except ValueError:
                        video_aspect = None

                if video_aspect == VideoAspect.portrait_3_4:
                    target_width, target_height = 1080, 1440
                elif video_aspect == VideoAspect.landscape_16_9:
                    target_width, target_height = 1920, 1080
                elif video_aspect == VideoAspect.square:
                    target_width, target_height = 1080, 1080

            output_bg_color = getattr(params, 'output_bg_color', None) or 'black'
            bg_color = parse_color(output_bg_color)

            if isinstance(bg_color, (list, tuple)):
                color_rgb = tuple(int(c) for c in bg_color[:3])
            else:
                color_rgb = (0, 0, 0)

            video_clip = ColorClip(size=(target_width, target_height), color=color_rgb, duration=duration)
            logger.info(f"Creating silence prefix video with color: {duration}s, {target_width}x{target_height}, color={color_rgb}")

        # ── B. Generate pink noise audio to temp WAV, load with AudioFileClip ──
        pink = _generate_pink_noise(duration, sample_rate, amplitude=0.0005)
        n_samples = len(pink)

        if n_samples == 0:
            logger.error(f"Silence prefix duration too short: {duration}s")
            video_clip.close()
            return None

        import tempfile
        import wave

        temp_wav = None
        try:
            temp_wav = tempfile.mktemp(suffix='.wav', prefix='coiner_silence_')
            with wave.open(temp_wav, 'w') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(sample_rate)
                scaled = np.int16(pink * 32767)
                if channels == 1:
                    wf.writeframes(scaled.tobytes())
                else:
                    stereo = np.column_stack([scaled, scaled])
                    wf.writeframes(stereo.tobytes())

            audio_clip = AudioFileClip(temp_wav)

            # ── C. Combine and write ──
            video_clip = video_clip.with_audio(audio_clip)

            enc_params = get_video_encoding_params()
            ffmpeg_params = ["-pix_fmt", "yuv420p"]
            if enc_params["crf"] is not None:
                ffmpeg_params.extend(["-crf", str(enc_params["crf"])])

            video_clip.write_videofile(
                filename=output_path,
                threads=2,
                logger=None,
                temp_audiofile_path=os.path.dirname(output_path),
                audio_codec=audio_codec,
                fps=fps,
                codec=get_video_codec(),
                bitrate=enc_params["bitrate"],
                preset=enc_params["preset"],
                ffmpeg_params=ffmpeg_params,
            )

            audio_clip.close()
            video_clip.close()

            # ── D. Verify duration ──
            try:
                clip = VideoFileClip(output_path)
                actual_duration = clip.duration
                clip.close()
                logger.info(f"Created silence prefix video: {output_path} (actual duration: {actual_duration:.3f}s, requested: {duration}s)")
            except Exception as e:
                logger.warning(f"Could not verify silence prefix duration: {e}")

            return output_path

        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except:
                    pass

    except Exception as e:
        logger.error(f"Failed to create silence prefix video: {e}")
        return None


def _srt_to_ass(srt_path: str, ass_path: str, video_height: int,
                font_name: str = "Arial", font_size_px: int = 60,
                primary_color: str = "&H00FFFFFF",
                outline_color: str = "&H00000000",
                outline_width: int = 2,
                alignment: int = 2,
                margin_v: int = None) -> bool:
    """
    Convert an SRT subtitle file to ASS with PlayResY matching video height,
    so FontSize is interpreted as video-pixel-relative units (1pt ≈ 1px at 72 DPI).

    Args:
        srt_path: Path to the source SRT file.
        ass_path: Path to write the generated ASS file.
        video_height: Video height in pixels (used as PlayResY).
        font_name: Font family name for the default style.
        font_size_px: Font size in pixels (already converted from points).
        primary_color: ASS colour string for the text (AABBGGRR).
        outline_color: ASS colour string for the outline.
        outline_width: Outline thickness.
        alignment: ASS alignment value (2 = bottom-centre).
        margin_v: Vertical margin from the edge.

    Returns:
        True on success, False on failure.
    """
    import re as _re

    if not srt_path or not os.path.isfile(srt_path):
        return False

    try:
        # ── Parse SRT ──
        entries = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = content.strip().split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 2:
                continue
            # Find the timing line (contains -->)
            timing_idx = None
            for i, line in enumerate(lines):
                if "-->" in line:
                    timing_idx = i
                    break
            if timing_idx is None:
                continue

            timing_line = lines[timing_idx]
            text_lines = lines[timing_idx + 1:]
            text = "\\N".join(l.strip() for l in text_lines if l.strip())
            if not text:
                continue

            # Convert SRT timing (HH:MM:SS,mmm) to ASS timing (H:MM:SS.cc)
            times = _re.findall(r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})", timing_line)
            if len(times) != 2:
                continue

            def _srt_to_ass_time(t: str) -> str:
                t = t.replace(",", ".")
                h, m, rest = t.split(":")
                s, ms = rest.split(".")
                cs = ms[:2]  # centiseconds
                return f"{int(h)}:{m}:{s}.{cs}"

            start = _srt_to_ass_time(times[0])
            end = _srt_to_ass_time(times[1])
            entries.append((start, end, text))

        if not entries:
            logger.warning(f"No valid subtitle entries found in {srt_path}")
            return False

        # ── Write ASS ──
        # Set default margin_v based on video height (5% of video height, matching MoviePy path)
        if margin_v is None:
            margin_v = max(30, int(video_height * 0.05))
        
        # Escape backslashes for the ASS style value
        ass_font_name = font_name.replace("\\", "\\\\")

        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{ass_font_name},{font_size_px},{primary_color},&H000000FF,{outline_color},&H80000000,0,0,0,0,100,100,0,0,1,{outline_width},1,{alignment},20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        for start, end, text in entries:
            ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

        with open(ass_path, "w", encoding="utf-8-sig") as f:
            f.write(ass_content)

        logger.debug(f"Converted SRT to ASS: {srt_path} -> {ass_path} (PlayResY={video_height})")
        return True

    except Exception as e:
        logger.error(f"Failed to convert SRT to ASS: {e}")
        return False


def burn_subtitles_to_scene_video(
    scene_video_path: str,
    subtitle_file: str,
    output_path: str,
    params,
) -> bool:
    """
    Burn subtitles into a single scene video using FFmpeg.

    The audio stream is copied without re-encoding. Video is re-encoded
    with the same codec settings as build_scene_video so that the output
    remains compatible with the stream-copy concat fast-path.

    Args:
        scene_video_path: Path to the scene video (e.g. combined.mp4)
        subtitle_file: Path to the scene subtitle file (SRT format)
        output_path: Path for the output video with burned-in subtitles
        params: VideoParams object with font, color, position settings

    Returns:
        True on success, False on failure
    """
    from app.services.title import _get_valid_font_path
    from app.services.video_utils import hex_to_ass_color, get_video_codec, get_video_encoding_params

    if not scene_video_path or not os.path.exists(scene_video_path):
        logger.error(f"Scene video not found: {scene_video_path}")
        return False

    if not subtitle_file or not os.path.exists(subtitle_file):
        logger.warning(f"Subtitle file not found, skipping burn-in: {subtitle_file}")
        return False

    ffmpeg_exe = _get_ffmpeg_exe()

    try:
        clip = VideoFileClip(scene_video_path)
        video_width = clip.size[0]
        video_height = clip.size[1]
        close_clip(clip)
    except Exception as e:
        logger.error(f"Failed to get scene video dimensions: {e}")
        return False

    font_path = _get_valid_font_path(getattr(params, 'font_name', 'STHeitiMedium.ttc'))
    font_family = _get_font_family_name(font_path) if font_path else "Arial"

    font_size_pt = int(getattr(params, 'font_size', 60))
    _play_res_y = 1080
    font_size_px = max(1, int(font_size_pt * video_height / _play_res_y))

    text_fore_color = getattr(params, 'text_fore_color', '#FFFFFF')
    primary_color = hex_to_ass_color(text_fore_color)

    sub_params = {
        "font_name": font_family,
        "font_size": font_size_px,
        "primary_color": primary_color,
        "fonts_dir": os.path.dirname(font_path) if font_path else None,
    }

    pos = getattr(params, 'subtitle_position', 'bottom')
    align_map = {"bottom": 2, "top": 8, "center": 4, "custom": 2}
    sub_params["alignment"] = align_map.get(pos, 2)

    _ui_cfg = load_config().get("ui", {})
    if pos == 'custom':
        custom_pos = float(getattr(params, 'custom_position', 70.0))
        estimated_h = int(font_size_px * 1.5)

        # Check if pillarbox (3:4 -> 9:16) will be applied later
        # Position must be calculated relative to final output frame
        target_h = video_height
        pad_h = 0
        vasp = getattr(params, 'video_aspect', None)
        if vasp is not None:
            vasp_value = vasp.value if hasattr(vasp, 'value') else str(vasp)
            if vasp_value == "3:4":
                target_h = 1920
                pad_h = (target_h - video_height) // 2

        y_in_target = int((target_h - estimated_h) * (custom_pos / 100))
        y_in_scene = y_in_target - pad_h
        y_in_scene = max(0, min(y_in_scene, video_height - estimated_h))

        sub_params["margin_v"] = video_height - y_in_scene - estimated_h
        if sub_params["margin_v"] < 0:
            sub_params["margin_v"] = 0
    else:
        margin_ratio = _ui_cfg.get("subtitle_margin", 0.05)
        sub_params["margin_v"] = int(video_height * margin_ratio)

    stroke_w = int(getattr(params, 'stroke_width', 0) or 0)
    if stroke_w > 0:
        sc = getattr(params, 'stroke_color', 'black')
        sub_params["outline_color"] = hex_to_ass_color(sc)
        sub_params["outline_width"] = stroke_w

    import tempfile
    _temp_ass_file = tempfile.mktemp(suffix=".ass", prefix="coiner_scene_sub_")
    _srt_to_ass(
        srt_path=subtitle_file,
        ass_path=_temp_ass_file,
        video_height=video_height,
        font_name=sub_params.get("font_name", "Arial"),
        font_size_px=sub_params.get("font_size", 60),
        primary_color=sub_params.get("primary_color", "&H00FFFFFF"),
        outline_color=sub_params.get("outline_color", "&H00000000"),
        outline_width=sub_params.get("outline_width", 2),
        alignment=sub_params.get("alignment", 2),
        margin_v=sub_params.get("margin_v", None),
    )

    sub_file_to_use = _temp_ass_file if os.path.exists(_temp_ass_file) else subtitle_file

    try:
        escaped_sub = (sub_file_to_use
                       .replace("\\", "/")
                       .replace(":", "\\:")
                       .replace("'", "\\'"))

        fonts_dir_option = ""
        fonts_dir = sub_params.get("fonts_dir")
        if fonts_dir and os.path.isdir(fonts_dir):
            escaped_dir = (fonts_dir
                          .replace("\\", "/")
                          .replace(":", "\\:")
                          .replace("'", "\\'"))
            fonts_dir_option = f":fontsdir='{escaped_dir}'"

        codec = get_video_codec()
        enc_params = get_video_encoding_params()

        cmd = [
            ffmpeg_exe, "-y",
            "-i", scene_video_path,
            "-vf", f"subtitles='{escaped_sub}'{fonts_dir_option}",
            "-c:v", codec,
        ]

        if codec == "libx264":
            cmd.extend(["-crf", str(enc_params["crf"]), "-preset", enc_params["preset"]])
        elif codec in ("h264_nvenc", "h264_amf", "h264_qsv"):
            cmd.extend(["-b:v", enc_params["bitrate"], "-preset", enc_params["preset"]])
        else:
            cmd.extend(["-crf", str(enc_params.get("crf", 18)), "-preset", enc_params.get("preset", "medium")])

        cmd.extend([
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            "-fps_mode", "cfr",
            "-r", str(fps),
            output_path
        ])

        logger.info(f"Burning subtitles into scene video: {os.path.basename(scene_video_path)}")
        logger.debug(f"FFmpeg subtitle burn cmd: {' '.join(cmd[:8])}...")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            stderr_tail = result.stderr[-500:] if result.stderr else ""
            logger.error(f"FFmpeg subtitle burn failed (rc={result.returncode}): {stderr_tail}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return False

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error("Subtitle burn produced empty output")
            return False

        size_mb = os.path.getsize(output_path) / 1024 / 1024
        logger.success(f"Subtitles burned into scene video: {output_path} ({size_mb:.1f} MB)")
        return True

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg subtitle burn timed out (600s)")
        return False
    except Exception as e:
        logger.error(f"Failed to burn subtitles into scene video: {e}")
        return False
    finally:
        if _temp_ass_file and os.path.exists(_temp_ass_file):
            try:
                os.remove(_temp_ass_file)
            except OSError:
                pass


def analyze_audio_params(video_path: str) -> dict:
    """
    Analyze audio parameters from a video file using ffprobe.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        dict with keys: sample_rate, channels, codec
    """
    import json
    try:
        ffmpeg_exe = _get_ffmpeg_exe()
        ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
        cmd = [
            ffprobe_exe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    return {
                        "sample_rate": int(stream.get("sample_rate", 44100)),
                        "channels": int(stream.get("channels", 2)),
                        "codec": stream.get("codec_name", "aac")
                    }
    except Exception as e:
        logger.debug(f"Failed to analyze audio params: {e}")
    return {"sample_rate": 44100, "channels": 2, "codec": "aac"}


def concat_videos_stream_copy(
    video_paths: List[str],
    output_path: str,
) -> bool:
    """
    Concatenate MP4 files using FFmpeg's concat demuxer with -c copy (no re-encoding).

    This is dramatically faster than loading clips into MoviePy and re-encoding,
    but requires all inputs to share the same codec, resolution, fps and pixel format —
    which is guaranteed when they all come from the same build_scene_video() pipeline.

    Args:
        video_paths: Ordered list of absolute paths to scene MP4 files.
        output_path: Destination MP4 path.

    Returns:
        True on success, False on any failure (caller should fall back to slow path).
    """
    if len(video_paths) < 2:
        logger.debug("concat_videos_stream_copy: fewer than 2 paths, skipping fast-path")
        return False

    ffmpeg_exe = _get_ffmpeg_exe()
    list_path = output_path + ".concat.txt"

    try:
        # Write the concat list file (FFmpeg concat demuxer format)
        with open(list_path, "w", encoding="utf-8") as fh:
            for p in video_paths:
                # FFmpeg requires single-quoted paths with internal quotes escaped
                escaped = p.replace("'", r"'\''")
                fh.write(f"file '{escaped}'\n")
        logger.debug(f"concat_videos_stream_copy: wrote concat list to {list_path}")

        result = subprocess.run(
            [
                ffmpeg_exe,
                "-y",                       # overwrite without asking
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",               # zero re-encoding
                "-movflags", "+faststart",  # web-friendly moov atom placement
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.warning(
                f"concat_videos_stream_copy: FFmpeg exited with code {result.returncode}; "
                f"falling back to re-encode path. stderr: {result.stderr[:500]}"
            )
            return False

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.warning("concat_videos_stream_copy: output file is missing or empty; falling back")
            return False

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.success(
            f"concat_videos_stream_copy: {len(video_paths)} scenes stitched in "
            f"{output_path} ({size_mb:.1f} MB) — no re-encoding"
        )
        return True

    except subprocess.TimeoutExpired:
        logger.warning("concat_videos_stream_copy: FFmpeg timed out; falling back to re-encode path")
        return False
    except FileNotFoundError:
        logger.warning(
            f"concat_videos_stream_copy: FFmpeg not found at '{ffmpeg_exe}'; falling back"
        )
        return False
    except Exception as exc:
        logger.warning(f"concat_videos_stream_copy: unexpected error ({exc}); falling back")
        return False
    finally:
        # Always clean up the temporary concat list file
        try:
            if os.path.exists(list_path):
                os.remove(list_path)
        except OSError:
            pass


def finalize_video(
    processed_clips: List,
    combined_video_path: str,
    audio_file: str,
    threads: int,
) -> str:
    """
    Finalize video by concatenating clips and adding audio
    
    Args:
        processed_clips: List of processed video clips
        combined_video_path: Path to save the final video
        audio_file: Path to audio file
        threads: Number of threads to use
    
    Returns:
        Path to the final video
    """
    if not processed_clips:
        logger.warning("no clips available for merging")
        return None
    
    # Concatenate all clips in memory
    logger.debug(f"concatenating {len(processed_clips)} clips in memory")
    try:
        # Concatenate all clips at once (no intermediate encoding)
        final_video = safe_concatenate_videoclips(processed_clips)
        
        logger.info(f"clips concatenated, total duration: {final_video.duration:.2f}s")
        
        # Note: Pillarbox is now added at the final video generation stage (after subtitles)
        
        # Load audio if provided
        if audio_file:
            audio_clip = AudioFileClip(audio_file)
            
            # Trim video to match audio duration
            video_duration_final = final_video.duration
            audio_duration = audio_clip.duration
            if video_duration_final > audio_duration:
                final_video = final_video.subclipped(0, audio_duration)
                logger.info(f"video trimmed to match audio duration: {audio_duration:.2f}s")
            
            # Add audio to video
            final_video = final_video.with_audio(audio_clip)
        else:
            logger.info("Using existing audio from scene videos")
        
        # Write final video with audio (single encoding step)
        logger.info("writing final video with audio (single encoding step)")
        ffmpeg_params = ["-pix_fmt", "yuv420p"]
        if get_video_encoding_params()["crf"] is not None:
            ffmpeg_params.extend(["-crf", str(get_video_encoding_params()["crf"])])
        
        # Get the latest video codec (dynamic detection)
        current_codec = get_video_codec()
        current_encoding_params = get_video_encoding_params()
        
        output_dir = os.path.dirname(combined_video_path)
        
        try:
            final_video.write_videofile(
                filename=combined_video_path,
                threads=int(threads),
                logger=None,
                temp_audiofile_path=output_dir,
                audio_codec=audio_codec,
                fps=fps,
                codec=current_codec,
                bitrate=current_encoding_params["bitrate"],
                preset=current_encoding_params["preset"],
                ffmpeg_params=ffmpeg_params
            )
        except Exception as e:
            # If encoder not found, fallback to CPU encoder
            if "Unknown encoder" in str(e) or "Encoder not found" in str(e):
                logger.warning(f"Encoder {current_codec} not found, falling back to CPU encoder (libx264)")
                # Use CPU encoder
                current_codec = "libx264"
                # Get CPU encoding parameters
                current_encoding_params = get_video_encoding_params()
                # Try again with CPU encoder
                final_video.write_videofile(
                    filename=combined_video_path,
                    threads=int(threads),
                    logger=None,
                    temp_audiofile_path=output_dir,
                    audio_codec=audio_codec,
                    fps=fps,
                    codec=current_codec,
                    bitrate=current_encoding_params["bitrate"],
                    preset=current_encoding_params["preset"],
                    ffmpeg_params=ffmpeg_params
                )
            else:
                # Re-raise other exceptions
                raise
        
        logger.success(f"final video saved to: {combined_video_path}")
        
        # Verify the output file is valid before closing clips
        if os.path.exists(combined_video_path):
            file_size = os.path.getsize(combined_video_path)
            if file_size == 0:
                logger.error(f"Output video file is EMPTY: {combined_video_path}")
                close_clip(final_video)
                if audio_file:
                    close_clip(audio_clip)
                for clip in processed_clips:
                    close_clip(clip)
                return None
            # Quick validation: try to read the file back to ensure it's valid
            try:
                _verify_clip = VideoFileClip(combined_video_path)
                _verify_duration = _verify_clip.duration
                close_clip(_verify_clip)
                logger.info(f"Output file validated: {combined_video_path} ({file_size} bytes, {_verify_duration:.2f}s)")
            except Exception as ve:
                logger.error(f"Output video file validation failed: {combined_video_path} - {ve}")
                close_clip(final_video)
                if audio_file:
                    close_clip(audio_clip)
                for clip in processed_clips:
                    close_clip(clip)
                return None
        
        # Close all clips
        close_clip(final_video)
        if audio_file:
            close_clip(audio_clip)
        for clip in processed_clips:
            close_clip(clip)
        
    except Exception as e:
        logger.error(f"failed to merge clips and add audio: {str(e)}")
        return None
    
    logger.info("video combining completed")
    return combined_video_path


def _measure_loudnorm_params(
    video_path: str,
    bgm_file: str = None,
    bgm_volume: float = 0.2,
    silence_duration: float = 0,
    bgm_delay: float = 0,
    ffmpeg_exe: str = "ffmpeg",
) -> dict:
    """
    First pass of two-pass loudness normalization.
    Measures overall loudness of the final mixed audio so the second pass
    can apply linear gain instead of dynamic normalization (which would
    amplify silence prefix).

    Returns dict with keys: input_i, input_tp, input_lra, input_thresh, target_offset
    Returns None if measurement fails.
    """
    import subprocess
    import json

    try:
        filter_parts = []
        inputs = ["-i", video_path]

        if bgm_file and os.path.exists(bgm_file):
            inputs.extend(["-stream_loop", "-1", "-i", bgm_file])

            first_label = "0:a"

            bgm_delay_ms = int((bgm_delay or silence_duration) * 1000)
            bgm_filter = f"[1:a]volume={bgm_volume}"
            if bgm_delay_ms > 0:
                bgm_filter += f",adelay={bgm_delay_ms}|{bgm_delay_ms}"
            bgm_filter += "[1a_vol]"
            filter_parts.append(bgm_filter)

            filter_parts.append(
                f"[{first_label}][1a_vol]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_mixed]"
            )
            filter_parts.append(
                f"[a_mixed]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json"
            )
        else:
            if silence_duration > 0:
                filter_parts.append(
                    f"[0:a]adelay={int(silence_duration * 1000)}|{int(silence_duration * 1000)},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json"
                )
            else:
                filter_parts.append(
                    f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json"
                )

        filter_complex = ";".join(filter_parts)

        cmd = [ffmpeg_exe, "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-f", "null",
            "-"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        stderr = result.stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = stderr[json_start:json_end]
            params = json.loads(json_str)
            logger.debug(f"Loudnorm measurement: {params}")
            return params

        logger.warning("Failed to parse loudnorm measurement JSON, falling back to single-pass")
        return None

    except Exception as e:
        logger.warning(f"Loudnorm measurement failed: {e}, falling back to single-pass")
        return None


def _ffmpeg_fast_encode(
    video_path: str,
    output_file: str,
    silence_duration: float = 0,
    bgm_delay: float = 0,
    pillarbox: bool = False,
    pillarbox_bg_color: str = "black",
    subtitle_file: str = None,
    subtitle_params: dict = None,
    bgm_file: str = None,
    bgm_volume: float = 0.2,
    target_width: int = 1080,
    target_height: int = 1920,
    task_id: str = None,
    progress_callback=None,
) -> bool:
    """
    Use FFmpeg filter_complex to encode the final video in a single streaming pass,
    replacing MoviePy's frame-by-frame compositing.
    
    Handles: silence prefix, pillarbox, subtitle burn-in, BGM mixing, encoding.
    
    Args:
        video_path: Path to the combined scene video
        output_file: Output file path
        silence_duration: Seconds of still-frame prefix to prepend (use 0 when already in video)
        bgm_delay: Seconds of delay to apply to BGM start (independent of silence_duration)
        pillarbox: Whether to add pillarbox bars (3:4 in 9:16)
        pillarbox_bg_color: Background color for pillarbox
        subtitle_file: Path to SRT/ASS subtitle file to burn in
        subtitle_params: Dict with font_name, font_size, colors, position, margin
        bgm_file: Path to BGM audio file
        bgm_volume: BGM volume multiplier (0.0-1.0)
        target_width/height: Output resolution for pillarbox
        task_id: Task ID for progress monitoring
        progress_callback: Optional progress callback
    
    Returns:
        True on success, False on failure (caller should fall back to MoviePy)
    """
    ffmpeg_exe = os.environ.get("IMAGEIO_FFMPEG_EXE", "ffmpeg")
    
    # Build input args
    inputs = ["-i", video_path]
    filter_parts = []
    cur_label = "0:v"
    
    audio_label = "0:a?"  # optional audio from video
    extra_outputs = []
    
    # 1. Silence prefix — tpad clones the first frame
    if silence_duration > 0:
        filter_parts.append(
            f"[{cur_label}]tpad=start_mode=clone:start_duration={silence_duration}[v_tpad]"
        )
        cur_label = "v_tpad"
        # Offset the audio by silence_duration using adelay
        filter_parts.append(
            f"[{audio_label}]adelay={int(silence_duration * 1000)}|{int(silence_duration * 1000)}[a_delayed]"
        )
        audio_label = "a_delayed"
    
    # 2. Pillarbox — pad to target dimensions with background color
    if pillarbox:
        filter_parts.append(
            f"[{cur_label}]scale={target_width}:{target_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:"
            f"color={pillarbox_bg_color}[v_padded]"
        )
        cur_label = "v_padded"
    
    # 3. Subtitle burn-in via FFmpeg subtitles filter
    _temp_ass_file = None
    if subtitle_file and os.path.exists(subtitle_file):
        # Convert SRT to ASS so FontSize is relative to PlayResY = video height (1pt ≈ 1px).
        # This ensures consistent rendering regardless of video resolution.
        sub_file_to_use = subtitle_file
        if subtitle_file.lower().endswith(".srt") and subtitle_params:
            import tempfile
            _temp_ass_file = tempfile.mktemp(suffix=".ass", prefix="coiner_sub_")
            _srt_to_ass(
                srt_path=subtitle_file,
                ass_path=_temp_ass_file,
                video_height=target_height,
                font_name=subtitle_params.get("font_name", "Arial"),
                font_size_px=subtitle_params.get("font_size", 60),
                primary_color=subtitle_params.get("primary_color", "&H00FFFFFF"),
                outline_color=subtitle_params.get("outline_color", "&H00000000"),
                outline_width=subtitle_params.get("outline_width", 2),
                alignment=subtitle_params.get("alignment", 2),
                margin_v=subtitle_params.get("margin_v", None),
            )
            if os.path.exists(_temp_ass_file):
                sub_file_to_use = _temp_ass_file
                logger.debug(f"Using converted ASS subtitle: {_temp_ass_file}")
            else:
                logger.warning("SRT->ASS conversion failed, falling back to SRT with force_style")
                _temp_ass_file = None

        # Escape colons and backslashes in the path for FFmpeg's subtitles filter
        escaped_sub = (sub_file_to_use
                       .replace("\\", "/")
                       .replace(":", "\\:")
                       .replace("'", "\\'"))
        
        sub_style = ""
        fonts_dir_option = ""
        if subtitle_params:
            # When using converted ASS, styles are embedded; force_style is only
            # needed as a fallback when the conversion was skipped.
            if _temp_ass_file is None:
                style_parts = []
                if subtitle_params.get("font_name"):
                    style_parts.append(f"FontName={subtitle_params['font_name']}")
                if subtitle_params.get("font_size"):
                    style_parts.append(f"FontSize={subtitle_params['font_size']}")
                if subtitle_params.get("primary_color"):
                    style_parts.append(f"PrimaryColour={subtitle_params['primary_color']}")
                if subtitle_params.get("outline_color"):
                    style_parts.append(f"OutlineColour={subtitle_params['outline_color']}")
                if subtitle_params.get("outline_width"):
                    style_parts.append(f"Outline={subtitle_params['outline_width']}")
                if subtitle_params.get("alignment"):
                    style_parts.append(f"Alignment={subtitle_params['alignment']}")
                if subtitle_params.get("margin_v"):
                    style_parts.append(f"MarginV={subtitle_params['margin_v']}")
                if style_parts:
                    sub_style = f":force_style='{','.join(style_parts)}'"
            
            # If fonts_dir is provided, add it as a subtitles filter option
            # so libass can find the font by family name
            fonts_dir = subtitle_params.get("fonts_dir")
            if fonts_dir and os.path.isdir(fonts_dir):
                escaped_dir = (fonts_dir
                              .replace("\\", "/")
                              .replace(":", "\\:")
                              .replace("'", "\\'"))
                fonts_dir_option = f":fontsdir='{escaped_dir}'"
        
        filter_parts.append(
            f"[{cur_label}]subtitles='{escaped_sub}'{fonts_dir_option}{sub_style}[v_sub]"
        )
        cur_label = "v_sub"
    
    # 4. BGM mixing
    if bgm_file and os.path.exists(bgm_file):
        bgm_input_idx = len(inputs) // 2  # input index for BGM
        inputs.extend(["-stream_loop", "-1", "-i", bgm_file])
        
        bgm_delay_ms = int((bgm_delay or silence_duration) * 1000)
        bgm_filter = f"[{bgm_input_idx}:a]volume={bgm_volume}"
        if bgm_delay_ms > 0:
            bgm_filter += f",adelay={bgm_delay_ms}|{bgm_delay_ms}"
        bgm_filter += "[bgm_vol]"
        filter_parts.append(bgm_filter)
        
        # Mix with existing video audio (if any)
        # normalize=0 prevents automatic volume normalization that would
        # attenuate voice start when transitioning from silence (only BGM) to voice (2 inputs)
        filter_parts.append(
            f"[{audio_label}][bgm_vol]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_mixed]"
        )
        audio_label = "a_mixed"
    
    # 5. EBU R128 loudness normalization (two-pass / linear mode)
    #    First pass measures overall loudness, second pass applies fixed linear gain.
    #    This prevents dynamic gain from amplifying silence prefix (single-pass issue).
    loudnorm_params = _measure_loudnorm_params(
        video_path=video_path,
        bgm_file=bgm_file,
        bgm_volume=bgm_volume,
        silence_duration=silence_duration,
        bgm_delay=bgm_delay,
        ffmpeg_exe=ffmpeg_exe,
    )
    if loudnorm_params:
        filter_parts.append(
            f"[{audio_label}]loudnorm=I=-14:TP=-1.5:LRA=11"
            f":measured_I={loudnorm_params['input_i']}"
            f":measured_TP={loudnorm_params['input_tp']}"
            f":measured_LRA={loudnorm_params['input_lra']}"
            f":measured_thresh={loudnorm_params['input_thresh']}"
            f":offset={loudnorm_params['target_offset']}"
            f":linear=true:print_format=summary[a_loudnorm]"
        )
    else:
        filter_parts.append(
            f"[{audio_label}]loudnorm=I=-14:TP=-1.5:LRA=11[a_loudnorm]"
        )
    audio_label = "a_loudnorm"
    
    # Build -filter_complex string
    filter_complex = ";".join(filter_parts) if filter_parts else ""
    
    # Build encoding args
    enc_params = get_video_encoding_params()
    codec = get_video_codec()
    
    enc_args = ["-c:v", codec]
    if codec == "libx264":
        enc_args.extend(["-crf", str(enc_params["crf"]), "-preset", enc_params["preset"]])
    elif codec == "h264_nvenc":
        enc_args.extend(["-b:v", enc_params["bitrate"], "-preset", enc_params["preset"]])
    elif codec == "h264_amf":
        enc_args.extend(["-b:v", enc_params["bitrate"], "-quality", "quality"])
    elif codec == "h264_qsv":
        enc_args.extend(["-b:v", enc_params["bitrate"], "-preset", "medium"])
    else:
        enc_args.extend(["-crf", str(enc_params.get("crf", 18)), "-preset", enc_params.get("preset", "medium")])
    
    # Build the full FFmpeg command
    cmd = [ffmpeg_exe, "-y"] + inputs
    
    if filter_complex:
        cmd.extend(["-filter_complex", filter_complex])
    
    cmd.extend([
        "-map", f"[{cur_label}]",   # processed video
        "-map", f"[{audio_label}]",  # processed audio (optional)
        *enc_args,
        "-c:a", audio_codec,
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-fps_mode", "cfr",
        "-r", str(fps),
    ])
    
    # Get video duration to control output length (instead of -shortest which may truncate)
    video_duration = 0
    try:
        clip = VideoFileClip(video_path)
        video_duration = clip.duration
        clip.close()
    except Exception as e:
        logger.debug(f"Failed to get video duration: {e}")
    
    # Use -t to ensure output matches video duration (prevents truncation by -shortest)
    if video_duration > 0:
        cmd.extend(["-t", str(video_duration)])
    
    cmd.extend([
        "-movflags", "+faststart",
        output_file
    ])
    
    logger.info(f"FFmpeg fast encode: {' '.join(cmd[:10])}... ({len(filter_parts)} filters)")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            stderr_tail = result.stderr[-500:] if result.stderr else ""
            logger.warning(f"FFmpeg fast encode failed (rc={result.returncode}): {stderr_tail}")
            # Clean up partial output
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError:
                    pass
            return False
        
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            logger.warning("FFmpeg fast encode produced empty output")
            return False
        
        size_mb = os.path.getsize(output_file) / 1024 / 1024
        logger.success(f"FFmpeg fast encode complete: {output_file} ({size_mb:.1f} MB)")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg fast encode timed out (600s)")
        return False
    except Exception as e:
        logger.error(f"FFmpeg fast encode error: {e}")
        return False
    finally:
        # Clean up temporary ASS file if one was created
        if _temp_ass_file and os.path.exists(_temp_ass_file):
            try:
                os.remove(_temp_ass_file)
            except OSError:
                pass


def _fmt_duration(seconds):
    """Format seconds as HH:MM:SS string."""
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d}"


def _log_durations(end_time, task_create_time=None, task_start_time=None, scene_synthesis_start_time=None):
    """Log task lifecycle, task running duration, and scene synthesis duration."""
    if task_create_time:
        logger.info(f"Task lifecycle: {_fmt_duration(end_time - task_create_time)}")
    if task_start_time:
        logger.info(f"Task running duration: {_fmt_duration(end_time - task_start_time)}")
    if scene_synthesis_start_time:
        logger.info(f"Scene synthesis duration: {_fmt_duration(end_time - scene_synthesis_start_time)}")


def process_final_video(
    task_id: str,
    params,
    scene_results: list = None,
    combined_video_path: str = None,
    video_clip=None,
    subtitle_file: str = None,
    audio_file: str = None,
    output_file: str = None,
    progress_callback=None,
    task_create_time: float = None,
    task_start_time: float = None,
    scene_synthesis_start_time: float = None,
    skip_subtitles: bool = False,
    silence_duration: float = 0,
):
    """
    Shared function to process combined video after scene generation.
    Handles: silence prefix, title, subtitles, BGM, and final rendering.
    
    Args:
        task_id: Task ID
        params: Video parameters  
        scene_results: List of scene results (for subtitle merging)
        combined_video_path: Path to combined scene video (required if video_clip not provided)
        video_clip: Optional pre-loaded video clip
        subtitle_file: Path to subtitle file (optional, will be merged from scenes if not provided)
        audio_file: Optional BGM file
        output_file: Output file path (required)
        progress_callback: Optional callback function for progress updates
        task_create_time: Optional task creation time (time.time()). Used for "Task lifecycle" log.
        task_start_time: Optional task running start time (time.time()). Used for "Task running duration" log.
        scene_synthesis_start_time: Optional scene synthesis start time (time.time()). Used for "Scene synthesis duration" log.
        skip_subtitles: If True, skip subtitle burn-in entirely (subtitles already embedded in video)
    
    Returns:
        Final video path or None if failed
    """
    import time
    from loguru import logger
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, afx, ImageClip, TextClip
    import numpy as np
    from app.utils.composite_clip_factory import create_composite_video_clip, safe_concatenate_videoclips, ensure_clip_duration
    
    start_time = time.time()
    logger.info(f"Starting process_final_video for task: {task_id}")
    
    try:
        # Load video clip if not provided
        if video_clip is None:
            if not combined_video_path or not os.path.exists(combined_video_path):
                logger.error(f"Neither video_clip nor valid combined_video_path provided")
                return None
            
            video_clip = VideoFileClip(combined_video_path)
            logger.info(f"Loaded video clip: {combined_video_path}")
        
        # Validate that the video clip was loaded correctly
        try:
            _duration = video_clip.duration
        except AttributeError:
            logger.error(f"Failed to load video - clip duration not available")
            return None
        
        # Add pillarbox bars for 3:4 aspect ratio
        if hasattr(params, 'video_aspect') and params.video_aspect:
            from app.models.schema import VideoAspect
            
            video_aspect = params.video_aspect
            if isinstance(video_aspect, str):
                try:
                    video_aspect = VideoAspect(video_aspect)
                except ValueError:
                    video_aspect = None
            
            if video_aspect == VideoAspect.portrait_3_4:
                from app.services.video_utils import parse_color
                
                clip_w, clip_h = video_clip.size
                target_width, target_height = 1080, 1920
                
                scale_factor = target_width / clip_w
                new_width = round(clip_w * scale_factor)
                new_height = round(clip_h * scale_factor)
                
                scaled_clip = video_clip.resized(new_size=(new_width, new_height))
                y_offset = (target_height - new_height) // 2
                
                output_bg_color = getattr(params, 'output_bg_color', None) or 'black'
                bg_color = parse_color(output_bg_color)
                
                background = ColorClip(
                    size=(target_width, target_height),
                    color=bg_color,
                    duration=video_clip.duration
                )
                
                video_clip = create_composite_video_clip([
                    background,
                    scaled_clip.with_position(("center", y_offset))
                ])
                logger.info(f"Added pillarbox for 3:4 -> 9:16: {clip_w}x{clip_h} -> {target_width}x{target_height}")
        
        # Silence prefix is now added as a standalone scene before combine_all_scenes()
        # Keep the value for BGM delay calculation
        original_silence_duration = silence_duration
        silence_duration = 0
        
        # Add title AFTER Silence Prefix
        if hasattr(params, 'title_enabled') and params.title_enabled and hasattr(params, 'title_text') and params.title_text:
            logger.info("Adding title to video")
            video_clip = ensure_clip_duration(video_clip)
            from app.services.title import add_title_to_video
            
            try:
                video_clip = add_title_to_video(video_clip, params)
                logger.info(f"Title added, video duration: {getattr(video_clip, 'duration', 'NOT SET')}s")
            except Exception as e:
                logger.error(f"Failed to add title: {e}")
        
        # Add subtitle if enabled (and not already pre-burned into scene videos)
        if params.subtitle_enabled and not skip_subtitles:
            # Merge subtitles from scenes if no subtitle file provided
            using_merged_subtitle = False
            if not subtitle_file and scene_results:
                from app.services import subtitle
                merged_subtitle_path = subtitle.merge_scene_subtitles(
                    task_id, scene_results, silence_duration=silence_duration
                )
                if merged_subtitle_path and os.path.exists(merged_subtitle_path):
                    subtitle_file = merged_subtitle_path
                    using_merged_subtitle = True
                    logger.info(f"Using merged subtitle file (with silence duration offset): {subtitle_file}")
                elif scene_results:
                    subtitle_file = scene_results[0].get("subtitle_path")
                    logger.warning(f"Falling back to first scene subtitle (will add silence duration offset): {subtitle_file}")
            
            if subtitle_file and os.path.exists(subtitle_file):
                logger.info("Adding subtitles to video")
                try:
                    from app.services.title import _get_valid_font_path
                    from app.services.subtitle import file_to_subtitles, _srt_time_to_seconds
                    from app.services.video_utils import parse_color
                    
                    font_path = ""
                    if not params.font_name:
                        params.font_name = "STHeitiMedium.ttc"
                    font_path = _get_valid_font_path(params.font_name)
                    
                    subtitle_items = file_to_subtitles(subtitle_file)
                    logger.info(f"Loaded {len(subtitle_items)} subtitles from {subtitle_file}")
                    
                    subtitle_clips = []
                    video_width, video_height = video_clip.size
                    
                    if not font_path or not os.path.exists(font_path):
                        logger.warning(f"Font file not found: {font_path}, using default font")
                        font_path = None
                    
                    _cfg = load_config()
                    ui_config = _cfg.get("ui", {})
                    subtitle_margin = ui_config.get("subtitle_margin", 0.05)
                    max_width = video_width * (1 - 2 * subtitle_margin) * 0.95
                    subtitle_auto_fit = ui_config.get("subtitle_auto_fit", False)
                    
                    _play_res_y = 1080
                    font_size_pt = int(params.font_size)
                    font_size_px = max(1, int(font_size_pt * video_height / _play_res_y))
                    
                    for item in subtitle_items:
                        index, time_str, text = item
                        start_end = time_str.split(" --> ")
                        if len(start_end) == 2:
                            start_time_val = _srt_time_to_seconds(start_end[0])
                            end_time = _srt_time_to_seconds(start_end[1])
                            
                            # Adjust timestamps for silence duration
                            # Only add silence duration offset if subtitles are NOT already merged (i.e., using fallback or single video)
                            if not using_merged_subtitle and silence_duration > 0:
                                start_time_val += silence_duration
                                end_time += silence_duration
                                logger.debug(f"Added silence duration offset ({silence_duration}s) to subtitle")
                            
                            duration = end_time - start_time_val
                            if duration <= 0:
                                logger.warning(f"Skipping subtitle with invalid duration: {duration}s")
                                continue
                            
                            if not text or not text.strip():
                                logger.debug(f"Skipping subtitle with empty text at index {index}")
                                continue
                            
                            font_to_use = font_path if font_path and os.path.exists(font_path) else None
                            if font_to_use is None:
                                logger.warning(f"No valid font for subtitle, skipping entry {index}")
                                continue
                            
                            try:
                                wrapped_text, text_h, _ = wrap_text(
                                    text, max_width=max_width, font=font_to_use, 
                                    font_size_px=font_size_px, auto_fit=subtitle_auto_fit
                                )
                            except Exception as e:
                                logger.warning(f"wrap_text failed for subtitle {index}: {e}")
                                continue
                            
                            if not wrapped_text or not wrapped_text.strip():
                                logger.debug(f"Skipping subtitle with empty wrapped text at index {index}")
                                continue
                            
                            bg_color = params.text_background_color
                            if bg_color == 'transparent' or bg_color is False:
                                bg_color = None
                            elif isinstance(bg_color, str):
                                bg_color = parse_color(bg_color)
                            else:
                                bg_color = None
                            
                            try:
                                txt_clip = TextClip(
                                    text=wrapped_text,
                                    font=font_to_use,
                                    font_size=font_size_px,
                                    color=parse_color(params.text_fore_color),
                                    bg_color=bg_color,
                                    stroke_color=parse_color(params.stroke_color),
                                    stroke_width=int(params.stroke_width),
                                )
                            except Exception as e:
                                logger.warning(f"TextClip creation failed for subtitle {index}: {e}")
                                continue
                            
                            if txt_clip.h <= 0 or txt_clip.w <= 0:
                                logger.warning(f"Skipping zero-size subtitle clip at index {index}: {txt_clip.w}x{txt_clip.h}")
                                txt_clip.close()
                                continue
                            
                            margin_px = video_height * subtitle_margin
                            if params.subtitle_position == "bottom":
                                txt_clip = txt_clip.with_position(("center", video_height - margin_px - txt_clip.h))
                            elif params.subtitle_position == "top":
                                txt_clip = txt_clip.with_position(("center", margin_px))
                            elif params.subtitle_position == "custom":
                                max_y = video_height - txt_clip.h - margin_px
                                min_y = margin_px
                                custom_y = (video_height - txt_clip.h) * (params.custom_position / 100)
                                custom_y = max(min_y, min(custom_y, max_y))
                                txt_clip = txt_clip.with_position(("center", custom_y))
                            else:
                                txt_clip = txt_clip.with_position(("center", "center"))
                            
                            txt_clip = txt_clip.with_start(start_time_val).with_duration(duration)
                            subtitle_clips.append(txt_clip)
                    
                    logger.info(f"Created {len(subtitle_clips)} subtitle clips")
                    
                    if subtitle_clips:
                        video_clip = create_composite_video_clip([video_clip] + subtitle_clips)
                        logger.success("Subtitles added to video")
                except Exception as e:
                    logger.error(f"Failed to add subtitles: {e}")
        elif skip_subtitles:
            logger.info("Skipping subtitle addition - subtitles already pre-burned into scene videos")

        # Add BGM
        logger.info(f"Getting BGM file: bgm_type={getattr(params, 'bgm_type', 'none')}, bgm_file={getattr(params, 'bgm_file', '')}")
        bgm_file = None
        bgm_type = getattr(params, 'bgm_type', None)
        if bgm_type and bgm_type != 'none':
            from app.services.video_utils import get_bgm_file
            bgm_file = get_bgm_file(bgm_type=bgm_type, bgm_file=getattr(params, 'bgm_file', ''))
        
        # Also check audio_file parameter (for scene integration)
        if not bgm_file and audio_file and os.path.exists(audio_file):
            bgm_file = audio_file
        
        logger.info(f"BGM file result: {bgm_file}")
        
        if bgm_file and os.path.exists(bgm_file):
            try:
                bgm_clip = AudioFileClip(bgm_file).with_effects([
                    afx.MultiplyVolume(params.bgm_volume if hasattr(params, 'bgm_volume') else 0.2),
                    afx.AudioFadeOut(3),
                    afx.AudioLoop(duration=video_clip.duration),
                ])
                
                existing_audio = video_clip.audio
                if existing_audio:
                    combined_audio = CompositeAudioClip([existing_audio, bgm_clip])
                    video_clip = video_clip.with_audio(combined_audio)
                else:
                    video_clip = video_clip.with_audio(bgm_clip)
                
                logger.success("BGM added to video")
            except Exception as e:
                logger.error(f"Failed to add BGM: {e}")
        
        # Write final video
        logger.info(f"Writing final video to: {output_file}")
        
        # Ensure video_clip has valid duration
        if not hasattr(video_clip, 'duration') or video_clip.duration is None:
            logger.error("CRITICAL: video_clip has no duration attribute")
            return None
        
        # ── Determine whether title is enabled ──
        has_title = (hasattr(params, 'title_enabled') and params.title_enabled
                     and hasattr(params, 'title_text') and params.title_text)

        # ── Build shared FFmpeg params (used by both fast & hybrid paths) ──
        is_pillarbox = False
        if hasattr(params, 'video_aspect') and params.video_aspect:
            vasp = params.video_aspect
            logger.info(f"pillarbox check: raw video_aspect={vasp!r} (type={type(vasp).__name__})")
            if isinstance(vasp, str):
                from app.models.schema import VideoAspect as _VA
                try:
                    vasp = _VA(vasp)
                    logger.info(f"pillarbox check: converted via _VA -> {vasp!r} (value={vasp.value})")
                except ValueError:
                    logger.warning(f"pillarbox check: failed to parse video_aspect={vasp!r}")
                    vasp = None
            # Compare value "3:4" — use .value, NOT str() because Python 3.11+
            # str() on a str enum returns 'VideoAspect.portrait_3_4' (the repr),
            # not '3:4' (the actual value). .value always gives the raw value.
            if vasp is not None and hasattr(vasp, 'value') and vasp.value == "3:4":
                is_pillarbox = True
                logger.info("pillarbox check: IS 3:4 -> pillarbox enabled")
            else:
                vasp_val = getattr(vasp, 'value', str(vasp))
                logger.info(f"pillarbox check: vasp.value={vasp_val!r} != '3:4' -> pillarbox disabled")
        
        sub_params = None
        actual_sub_file = subtitle_file if subtitle_file and os.path.exists(subtitle_file) else None
        if actual_sub_file and params.subtitle_enabled and not skip_subtitles:
            from app.services.title import _get_valid_font_path
            font_path = _get_valid_font_path(getattr(params, 'font_name', 'STHeitiMedium.ttc'))
            
            # Use font family name (libass can't resolve filenames like 'STHeitiMedium.ttc')
            font_family = _get_font_family_name(font_path) if font_path else "Arial"
            
            _ui_cfg = load_config().get("ui", {})
            _video_height = video_clip.size[1] if video_clip else 1920
            
            font_size_pt = int(getattr(params, 'font_size', 60))
            _play_res_y = 1080
            font_size_px = max(1, int(font_size_pt * _video_height / _play_res_y))
            
            from app.services.video_utils import hex_to_ass_color
            
            text_fore_color = getattr(params, 'text_fore_color', '#FFFFFF')
            primary_color = hex_to_ass_color(text_fore_color)
            
            sub_params = {
                "font_name": font_family,
                "font_size": font_size_px,
                "primary_color": primary_color,
                "fonts_dir": os.path.dirname(font_path) if font_path else None,
            }
            
            pos = getattr(params, 'subtitle_position', 'bottom')
            align_map = {"bottom": 2, "top": 8, "center": 4, "custom": 2}
            sub_params["alignment"] = align_map.get(pos, 2)
            
            if pos == 'custom':
                # Approximate MoviePy custom position logic in FFmpeg path.
                # MoviePy: custom_y = (video_height - txt_clip.h) * (custom_position / 100)
                # We estimate txt_clip.h ≈ font_size_px * 1.5 for a typical line.
                custom_pos = float(getattr(params, 'custom_position', 70.0))
                estimated_h = int(font_size_px * 1.5)
                target_y = int((_video_height - estimated_h) * (custom_pos / 100))
                sub_params["margin_v"] = _video_height - target_y - estimated_h
                if sub_params["margin_v"] < 0:
                    sub_params["margin_v"] = 0
            else:
                margin_ratio = _ui_cfg.get("subtitle_margin", 0.05)
                sub_params["margin_v"] = int(_video_height * margin_ratio)
            
            stroke_w = int(getattr(params, 'stroke_width', 0) or 0)
            if stroke_w > 0:
                sc = getattr(params, 'stroke_color', 'black')
                sub_params["outline_color"] = hex_to_ass_color(sc)
                sub_params["outline_width"] = stroke_w
        
        bgm_vol = float(getattr(params, 'bgm_volume', 0.2))
        
        # ── Hybrid path: FFmpeg (pillarbox+subs+BGM) + MoviePy (title only) ──
        # Silence prefix is now added as a standalone scene before combine_all_scenes()
        # So hybrid path is safe to use - combined_video_path already has the silence prefix
        use_hybrid_path = has_title and combined_video_path and os.path.exists(combined_video_path)
        
        if use_hybrid_path:
            import uuid
            temp_no_title = os.path.join(
                os.path.dirname(output_file),
                f".no_title_{uuid.uuid4().hex[:8]}.mp4"
            )
            
            logger.info("Hybrid path: encoding base video via FFmpeg (pillarbox+subs+BGM)...")
            logger.info("Hybrid path: silence prefix already added as scene, skipping FFmpeg silence")
            
            ffmpeg_ok = _ffmpeg_fast_encode(
                video_path=combined_video_path,
                output_file=temp_no_title,
                silence_duration=0,
                bgm_delay=original_silence_duration,
                pillarbox=is_pillarbox,
                pillarbox_bg_color=getattr(params, 'output_bg_color', None) or 'black',
                subtitle_file=actual_sub_file,
                subtitle_params=sub_params,
                bgm_file=bgm_file,
                bgm_volume=bgm_vol,
                target_width=1080,
                target_height=1920,
                task_id=task_id,
                progress_callback=progress_callback,
            )
            
            if ffmpeg_ok:
                new_clip = None
                try:
                    logger.info("Hybrid path: loading FFmpeg-encoded base and applying title overlay...")
                    new_clip = VideoFileClip(temp_no_title)
                    from app.services.title import add_title_to_video
                    new_clip = add_title_to_video(new_clip, params)
                    
                    video_clip.close()
                    video_clip = new_clip
                    new_clip = None
                    logger.success("Hybrid path: title overlay applied successfully, proceeding to MoviePy write")
                except Exception as e:
                    logger.warning(f"Hybrid title overlay failed: {e}, falling back to full MoviePy")
                    if new_clip is not None:
                        new_clip.close()
                finally:
                    try:
                        if os.path.exists(temp_no_title):
                            os.remove(temp_no_title)
                    except OSError:
                        pass
            else:
                logger.warning("Hybrid path FFmpeg encode failed, falling back to full MoviePy")
        
        # ── Fast FFmpeg path (skip MoviePy compositing when no title) ──
        if not has_title and combined_video_path and os.path.exists(combined_video_path):
            ffmpeg_success = _ffmpeg_fast_encode(
                video_path=combined_video_path,
                output_file=output_file,
                silence_duration=0,
                bgm_delay=original_silence_duration,
                pillarbox=is_pillarbox,
                pillarbox_bg_color=getattr(params, 'output_bg_color', None) or 'black',
                subtitle_file=actual_sub_file,
                subtitle_params=sub_params,
                bgm_file=bgm_file,
                bgm_volume=bgm_vol,
                target_width=1080,
                target_height=1920,
                task_id=task_id,
                progress_callback=progress_callback,
            )
            
            if ffmpeg_success:
                video_clip.close()
                end_time = time.time()
                logger.success(f"Video generated (fast FFmpeg): {output_file}")
                _log_durations(end_time, task_create_time, task_start_time, scene_synthesis_start_time)
                return output_file
            
            logger.warning("FFmpeg fast encode failed, falling back to MoviePy")
        
        # ── MoviePy encoding path (fallback or title requires TextClip) ──
        ffmpeg_params = ["-pix_fmt", "yuv420p"]
        if get_video_encoding_params()["crf"] is not None:
            ffmpeg_params.extend(["-crf", str(get_video_encoding_params()["crf"])])
        # EBU R128 loudness normalization for consistent playback on WeChat etc.
        # Must force audio re-encoding (-c:a aac) because MoviePy muxes pre-encoded
        # temp audio with -c:a copy by default, which is incompatible with -af filters.
        ffmpeg_params.extend(["-c:a", audio_codec, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"])
        
        progress_monitor = create_encoding_progress_monitor(
            task_id=task_id,
            output_file=output_file,
            progress_callback=progress_callback,
            log_interval=60
        )
        progress_monitor.start_monitoring()
        
        try:
            video_clip.write_videofile(
                filename=output_file,
                threads=2,
                logger=None,
                temp_audiofile_path=os.path.dirname(output_file),
                audio_codec=audio_codec,
                fps=fps,
                codec=get_video_codec(),
                bitrate=get_video_encoding_params()["bitrate"],
                preset=get_video_encoding_params()["preset"],
                ffmpeg_params=ffmpeg_params
            )
        finally:
            progress_monitor.stop_monitoring()
        
        video_clip.close()
        
        end_time = time.time()
        logger.success(f"Video generated successfully: {output_file}")
        _log_durations(end_time, task_create_time, task_start_time, scene_synthesis_start_time)
        
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to process final video: {e}")
        raise
