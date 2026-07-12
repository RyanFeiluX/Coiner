from moviepy import Clip, vfx


def fadein_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeIn(t)])


def fadeout_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeOut(t)])


def slidein_transition(clip: Clip, t: float, side: str) -> Clip:
    return clip.with_effects([vfx.SlideIn(t, side)])


def slideout_transition(clip: Clip, t: float, side: str) -> Clip:
    return clip.with_effects([vfx.SlideOut(t, side)])


def brightness_enhance(clip: Clip, factor: float = 1.1) -> Clip:
    return clip.with_effects([vfx.MultiplyColor(factor)])


def contrast_enhance(clip: Clip, factor: float = 1.1) -> Clip:
    return clip.with_effects([vfx.GammaCorrection(factor)])


def detect_brightness(clip: Clip, num_samples: int = 10) -> float:
    import numpy as np
    from moviepy.video.io.ffmpeg_reader import FFMPEG_VideoReader

    duration = clip.duration
    sample_times = np.linspace(0, duration, num_samples, endpoint=False)

    if hasattr(clip, 'reader') and isinstance(clip.reader, FFMPEG_VideoReader):
        reader = clip.reader
    else:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        if hasattr(clip, 'filename'):
            reader = VideoFileClip(clip.filename).reader
        else:
            return 0.5

    total_brightness = 0
    valid_samples = 0

    try:
        for t in sample_times:
            try:
                frame = reader.get_frame(t)

                if len(frame.shape) == 3:
                    gray_frame = np.mean(frame, axis=2)
                else:
                    gray_frame = frame

                brightness = np.mean(gray_frame) / 255.0
                total_brightness += brightness
                valid_samples += 1
            except Exception:
                continue
    finally:
        if 'reader' in locals() and reader != clip.reader:
            reader.close()

    if valid_samples > 0:
        return total_brightness / valid_samples
    else:
        return 0.5
