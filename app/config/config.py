import os
import shutil
import socket

import toml
from loguru import logger

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
# Check for config file in both locations (backward compatibility)
config_file = f"{root_dir}/config/config.toml"
if not os.path.isfile(config_file):
    config_file = f"{root_dir}/config.toml"

# Track if config has been loaded to avoid duplicate logs
_config_loaded = False

# Secrets file (not tracked by git)
secrets_file = f"{root_dir}/secrets.toml"

# Keys that belong to [audio] — used for migrating from legacy [ui] or [app] location
_AUDIO_KEYS = {
    "tts_server", "voice_name", "voice_volume", "voice_rate",
    "bgm_type", "bgm_volume",
}

# Keys that belong to [subtitle] — used for migrating from legacy [ui] or [app] location
_SUBTITLE_KEYS = {
    "subtitle_enabled", "subtitle_position", "subtitle_custom_position",
    "subtitle_margin", "subtitle_auto_fit",
    "font_name", "text_fore_color", "text_background_color",
    "font_size", "stroke_color", "stroke_width",
}

# Keys that should be moved from [ui] to [video]
_UI_TO_VIDEO_KEYS = {
    "output_bg_color",
}

# Keys that belong to [video] — used for migrating from legacy [app] location
_VIDEO_KEYS = {
    "video_source", "video_quality", "video_bitrate",
    "video_brightness", "video_contrast", "video_brightness_threshold",
    "video_concat_mode", "video_transition_mode", "video_aspect",
    "video_clip_duration", "video_count", "video_style",
    "use_gpu", "silence_duration",
    "intro_video_bg_type", "intro_video_bg_blur", "intro_video_bg_color",
    "intro_image_animation_enabled", "intro_image_zoom_amount",
    "min_scene_success_ratio", "material_directory", "max_parallel_scenes",
}

# Keys considered sensitive that should live in secrets.toml
SECRET_KEYS = {
    "app": [
        "pexels_api_keys", "pixabay_api_keys", "pollinations_api_key",
        "openai_api_key", "moonshot_api_key", "oneapi_api_key",
        "azure_api_key", "gemini_api_key", "qwen_api_key",
        "deepseek_api_key", "modelscope_api_key", "redis_password",
        "ollama_api_key",
    ],
    "azure": ["speech_key"],
    "siliconflow": ["api_key"],
    "coze": ["api_key"],
    "qwen": ["api_key"],
}


def load_config():
    global _config_loaded
    # fix: IsADirectoryError: [Errno 21] Is a directory: '/Coiner/config.toml'
    if os.path.isdir(config_file):
        shutil.rmtree(config_file)

    if not os.path.isfile(config_file):
        example_file = f"{root_dir}/config.example.toml"
        if os.path.isfile(example_file):
            shutil.copyfile(example_file, config_file)
            logger.info("copy config.example.toml to config.toml")

    # Only log on first load to avoid duplicate messages
    if not _config_loaded:
        logger.info(f"load config from file: {config_file}")
        _config_loaded = True

    try:
        _config_ = toml.load(config_file)
    except Exception as e:
        logger.warning(f"load config failed: {str(e)}, try to load as utf-8-sig")
        with open(config_file, mode="r", encoding="utf-8-sig") as fp:
            _cfg_content = fp.read()
            _config_ = toml.loads(_cfg_content)

    if os.path.isfile(secrets_file):
        try:
            secrets = toml.load(secrets_file)
            for section, keys in secrets.items():
                if section not in _config_:
                    _config_[section] = {}
                _config_[section].update(keys)
        except Exception as e:
            logger.warning(f"load secrets failed: {str(e)}")

    return _config_


def save_config():
    _cfg["app"] = app
    _cfg["whisper"] = whisper
    _cfg["azure"] = azure
    _cfg["siliconflow"] = siliconflow
    _cfg["coze"] = coze
    _cfg["qwen"] = qwen
    _cfg["audio"] = audio
    _cfg["subtitle"] = subtitle
    _cfg["ui"] = ui
    _cfg["video"] = video

    secrets_data = {}
    for section, keys in SECRET_KEYS.items():
        section_data = {}
        for key in keys:
            if key in _cfg.get(section, {}):
                section_data[key] = _cfg[section][key]
        if section_data:
            secrets_data[section] = section_data

    public_cfg = {}
    for section, section_cfg in _cfg.items():
        if not isinstance(section_cfg, dict):
            public_cfg[section] = section_cfg
            continue
        skipped = SECRET_KEYS.get(section, [])
        public_cfg[section] = {k: v for k, v in section_cfg.items() if k not in skipped}

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(toml.dumps(public_cfg))
        f.flush()

    with open(secrets_file, "w", encoding="utf-8") as f:
        f.write(toml.dumps(secrets_data))
        f.flush()


_cfg = load_config()
app = _cfg.get("app", {})
whisper = _cfg.get("whisper", {})
proxy = _cfg.get("proxy", {})
azure = _cfg.get("azure", {})
siliconflow = _cfg.get("siliconflow", {})
coze = _cfg.get("coze", {})
qwen = _cfg.get("qwen", {})
audio = _cfg.get("audio", {})
subtitle = _cfg.get("subtitle", {})

ui = _cfg.get(
    "ui",
    {
        "hide_log": False,
    },
)
video = _cfg.get("video", {})

# Migrate audio keys that may still be in [ui] or [app] from older configs
for key in list(ui.keys()):
    if key in _AUDIO_KEYS and key not in audio:
        audio[key] = ui.pop(key)
for key in list(app.keys()):
    if key in _AUDIO_KEYS and key not in audio:
        audio[key] = app.pop(key)

# Migrate subtitle keys that may still be in [ui] or [app] from older configs
for key in list(ui.keys()):
    if key in _SUBTITLE_KEYS and key not in subtitle:
        subtitle[key] = ui.pop(key)
for key in list(app.keys()):
    if key in _SUBTITLE_KEYS and key not in subtitle:
        subtitle[key] = app.pop(key)

# Migrate keys from [ui] to [video]
for key in list(ui.keys()):
    if key in _UI_TO_VIDEO_KEYS and key not in video:
        video[key] = ui.pop(key)

# Migrate video keys that may still be in [app] from older configs
for key in list(app.keys()):
    if key in _VIDEO_KEYS and key not in video:
        video[key] = app.pop(key)

hostname = socket.gethostname()

log_level = _cfg.get("log_level", "DEBUG")
listen_host = os.getenv("LISTEN_HOST", _cfg.get("listen_host", "0.0.0.0"))
listen_port = int(os.getenv("LISTEN_PORT", _cfg.get("listen_port", 8000)))
project_name = _cfg.get("project_name", "Coiner")
project_description = _cfg.get(
    "project_description",
    "<a href='https://github.com/RyanFeiluX/Coiner'>https://github.com/RyanFeiluX/Coiner</a>",
)
project_version = _cfg.get("project_version", "1.2.6")
reload_debug = False

# Silence Prefix duration — still frame at the very beginning of the final video
silence_duration = video.get("silence_duration", 0.3)

imagemagick_path = app.get("imagemagick_path", "")
if imagemagick_path and os.path.isfile(imagemagick_path):
    os.environ["IMAGEMAGICK_BINARY"] = imagemagick_path

ffmpeg_path = app.get("ffmpeg_path", "")
if ffmpeg_path and os.path.isfile(ffmpeg_path):
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path

logger.info(f"{project_name} v{project_version}")
