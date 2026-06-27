# Video/Audio/Subtitle Synchronization Timing Chart

This document illustrates the timing synchronization between video, audio, subtitles, and BGM in the current scene subtitle pre-burning architecture.

---

## Current Architecture (Scene Subtitle Pre-Burning)

The current approach burns subtitles into each scene video BEFORE merging, ensuring perfect audio-subtitle synchronization within each scene.

### Processing Order

1. **Create Silence Prefix FIRST** (extract clean first frame without subtitles)
2. **Burn subtitles into each scene video** (audio + subtitles embedded together)
3. **Combine all scenes via FFmpeg stream-copy** (silence prefix + scene videos, no re-encoding)
4. **Add pillarbox** (if needed, 3:4 → 9:16)
5. **Add title** (starts from beginning)
6. **Add BGM** (mixed with scene audio)
7. **Loudness normalization + final encode**

```
╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                    TIMING CHART - SCENE SUBTITLE PRE-BURNING ARCHITECTURE                          ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                      ║
║ TIME (sec):    0.0      0.5      1.0      1.5      2.0      2.5      3.0      3.5      4.0      4.5 ║
║                │        │        │        │        │        │        │        │        │        │   ║
║                ↓        ↓        ↓        ↓        ↓        ↓        ↓        ↓        ↓        ↓   ║
║                                                                                                      ║
║ VIDEO:        [SILENCE PREFIX              ][Scene1                    ][Scene2                    ]║
║               0.0-3.0s                       3.0-6.0s                    6.0-9.0s                  ║
║               (no subtitles)                (subtitles burned in)      (subtitles burned in)        ║
║                                                                                                      ║
║ AUDIO:        [SILENCE (pink noise)        ][Scene1 Audio              ][Scene2 Audio              ]║
║               0.0-3.0s                       3.0-6.0s                    6.0-9.0s                  ║
║               (very quiet, ~-66dB)          (TTS voice)                 (TTS voice)                 ║
║                                                                                                      ║
║ SUBTITLE:     [SILENCE - NO SUBTITLES       ][Sub1                     ][Sub2                     ]║
║               0.0-3.0s                       3.2-4.5s                   6.2-7.5s                  ║
║               ↑ CORRECT: No subtitles in silence prefix!             ↑ PERFECT: Subtitles are     ║
║                                                                          embedded in scene video,   ║
║                                                                          perfectly synced with audio ║
║                                                                                                      ║
║ BGM:          [FADE IN BGM...                                                                       ║
║               0.0-... (looped to match video duration)                                               ║
║                                                                                                      ║
║ TITLE:        [TITLE OVERLAY...                                                                      ║
║               0.0-... (starts from beginning)                                                        ║
║                                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Processing Order Summary

| Step | Operation | Description |
|------|-----------|-------------|
| 1 | **Silence Prefix** | Create silence prefix from first scene's first frame (no subtitles) with matching audio/video parameters |
| 2 | **Scene Subtitle Burning** | Burn subtitles into each individual scene video (audio copied, no re-encoding) |
| 3 | **Scene Merging** | FFmpeg stream-copy concat (fast path) — silence prefix + all scenes, no re-encoding |
| 4 | Pillarbox | Add pillarbox bars for aspect ratio conversion (3:4 → 9:16) |
| 5 | Title | Add title overlay |
| 6 | BGM | Add background music mixed with existing audio |
| 7 | **Final Encode** | Loudness normalization + final encoding |

> **Key Innovation**: Subtitles are burned into each scene BEFORE merging. This eliminates the complex subtitle timestamp offset calculation and guarantees perfect audio-subtitle synchronization within each scene.

---

## Key Technical Details

### 1. Silence Prefix Video

**Purpose**: Add a silent still frame at the beginning of the video.

**Parameters Consistency** (Critical for FFmpeg stream-copy):
- **Frame rate**: 30 fps (explicit `-r` parameter)
- **Resolution**: Same as scene video (extracted from first frame)
- **Video codec**: H.264 (same as scene videos)
- **Pixel format**: yuv420p
- **Audio sample rate**: Matches first scene video (dynamically detected via ffprobe)
- **Audio channels**: Matches first scene video (dynamically detected via ffprobe)
- **Audio codec**: AAC (same as scene videos)

**Audio Implementation — Pink Noise Instead of Pure Silence**:

```bash
# Before (problematic): pure silence gets extremely compressed by AAC
anullsrc=channel_layout=stereo:sample_rate=44100:d=3

# After (correct): very quiet pink noise prevents extreme compression
anoisesrc=c=pink:a=0.0005:r=44100:d=3
```

**Why pink noise?**
- Pure silence gets compressed to ~6 bytes/frame by AAC → player buffer issues → audio starts early
- Pink noise at amplitude 0.0005 (~-66dB) is nearly inaudible
- Ensures normal audio frame sizes → proper player timing behavior
- Silence effect is still perceived by the user

### 2. Scene Subtitle Pre-Burning

**Function**: `burn_subtitles_to_scene_video()` in `video_target.py`

**Key properties**:
- Uses FFmpeg `subtitles` filter for hard subtitle burning
- Audio is stream-copied (`-c:a copy`) — no re-encoding, no quality loss
- Video encoding parameters match `build_scene_video` exactly → stream-copy safe
- Font size calculated based on scene video resolution (correct ratio after pillarbox)

**Benefits**:
- ✅ Perfect audio-subtitle synchronization within each scene
- ✅ No complex subtitle timestamp offset calculations
- ✅ No need to merge subtitle files across scenes
- ✅ Individual scene failure doesn't affect others (graceful fallback)

### 3. FFmpeg Stream-Copy Merging (Fast Path)

**Function**: `concat_videos_stream_copy()` in `video_target.py`

**How it works**:
1. Create a concat list file with all scene paths
2. Run FFmpeg with `-f concat -c copy`
3. Streams are directly copied — no decoding/re-encoding

**Requirements for success** (all must match):
- Video codec
- Resolution
- Frame rate
- Pixel format
- Audio codec
- Audio sample rate
- Audio channels

**Performance**: Near-instant (seconds vs minutes for re-encoding)

**Fallback**: If stream-copy fails, automatically falls back to MoviePy re-encoding.

### 4. BGM Mixing (amix)

BGM is mixed with the video's original audio using FFmpeg `amix` filter.

**Key parameters**:
- **`normalize=0`**: Disables automatic volume normalization based on number of active inputs
- **`dropout_transition=0`**: No fade transitions needed since both inputs are continuously active
- **`duration=first`**: Output duration follows the first input (video audio)

**Why normalize=0?** Default `normalize=1` behavior causes volume attenuation when transitioning from silence (only BGM active) to voice (both inputs active). The normalization factor changes from 1/1 to 1/2, reducing voice start volume by ~7 dB, making the first few words sound "truncated". With `normalize=0`, both inputs retain their original volume levels, and loudnorm handles the final normalization.

### 5. Loudness Normalization (EBU R128)

The `loudnorm` filter is always the **last** audio filter in the chain (after `amix` BGM mixing).

- **Integrated loudness**: -14 LUFS (YouTube/social-media standard)
- **True peak**: -1.5 dBTP
- **Loudness range**: 11 LU
- **Mode**: Two-pass linear (first pass measures, second pass applies fixed gain)
- **Applied only at final encode** — intermediate `combined.mp4` is intentionally unnormalized to avoid double-normalization

**Why -14 LUFS?** 
- The original TTS audio typically has higher loudness (~-13.5 LUFS)
- Using -16 LUFS target would require lowering overall gain by ~2.4 dB, which also attenuates voice start
- -14 LUFS is YouTube's recommended standard, providing good balance between loudness and voice clarity
- Combined with `normalize=0` in amix, voice start volume stays close to original level

---

## Architecture Evolution

### Old Architecture (Deprecated)

```
Merge scenes → Add silence prefix → Add title → Add subtitles (global) → Add BGM → Encode
```

**Problems**:
- Subtitle timestamps needed complex offset calculations
- Sync issues if scene durations had minor variations
- Global subtitle file merging was error-prone

### Current Architecture (Scene Pre-Burning)

```
Create silence prefix → Burn subtitles per scene → Merge all (stream-copy) → Pillarbox → Title → BGM → Encode
```

**Advantages**:
- ✅ Perfect audio-subtitle sync within each scene
- ✅ Simpler, more reliable
- ✅ Fast stream-copy merging
- ✅ Clean separation of concerns

---

## Files Modified

1. **`app/services/video_target.py`**:
   - `burn_subtitles_to_scene_video()` — new function for scene-level subtitle burning
   - `create_silence_prefix_video()` — parameter consistency + pink noise audio
   - `analyze_audio_params()` — new function for ffprobe audio parameter detection
   - `process_final_video()` — added `skip_subtitles` parameter
   - `_ffmpeg_fast_encode()` — fixed `-shortest` truncation issue, use `-t` instead
   - `concat_videos_stream_copy()` — fast path stream-copy merging

2. **`app/services/video_synthesis.py`**:
   - `recover_video_synthesis()` — major rework: silence prefix first, then subtitle burning, then merging
   - Variable naming fix: `scene_sub_video_path` instead of `output_path` to avoid override

3. **`app/services/task.py`**:
   - `build_multi_scene_video()` — updated silence prefix creation with audio parameter analysis
