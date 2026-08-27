"""
TTS 公共模块：公共工具函数、硅基流动/Gemini（未拆分项）、tts 分发器。
各供应商专属实现见 voice_azure.py / voice_qwen.py / voice_coze.py，
本文件在末尾再导出这些函数，保持原有 voice.xxx() 调用方式不变。
"""
import os
import re
from datetime import timedelta
from typing import Union
from xml.sax.saxutils import unescape

import requests
from edge_tts import SubMaker, submaker
from loguru import logger
from moviepy.video.tools import subtitles
from moviepy.audio.io.AudioFileClip import AudioFileClip

# 替代edge_tts.submaker中的mktimestamp函数
def mktimestamp(seconds: float) -> str:
    """将秒数转换为SRT格式的时间戳"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

from app.config import config
from app.utils import utils

def get_siliconflow_voices() -> list[str]:
    """
    获取硅基流动的声音列表

    Returns:
        声音列表，格式为 ["siliconflow:FunAudioLLM/CosyVoice2-0.5B:alex", ...]
    """
    api_key = config.siliconflow.get("api_key", "")
    if not api_key:
        logger.warning("SiliconFlow API key is NOT set, using HARDCODED voice list")
    else:
        logger.info("SiliconFlow API key is set, using HARDCODED voice list")
    
    logger.info("Loading SiliconFlow voices from HARDCODED list")
    # 硅基流动的声音列表和对应的性别（用于显示）
    voices_with_gender = [
        ("FunAudioLLM/CosyVoice2-0.5B", "alex", "Male"),
        ("FunAudioLLM/CosyVoice2-0.5B", "anna", "Female"),
        ("FunAudioLLM/CosyVoice2-0.5B", "bella", "Female"),
        ("FunAudioLLM/CosyVoice2-0.5B", "benjamin", "Male"),
        ("FunAudioLLM/CosyVoice2-0.5B", "charles", "Male"),
        ("FunAudioLLM/CosyVoice2-0.5B", "claire", "Female"),
        ("FunAudioLLM/CosyVoice2-0.5B", "david", "Male"),
        ("FunAudioLLM/CosyVoice2-0.5B", "diana", "Female"),
    ]

    # 添加siliconflow:前缀，并格式化为显示名称
    result = [
        f"siliconflow:{model}:{voice}-{gender}"
        for model, voice, gender in voices_with_gender
    ]
    logger.info(f"SiliconFlow loaded {len(result)} hardcoded voices: {result}")
    return result

def get_gemini_voices() -> list[str]:
    """
    获取Gemini TTS的声音列表
    
    Returns:
        声音列表，格式为 ["gemini:Zephyr-Female", "gemini:Puck-Male", ...]
    """
    api_key = config.app.get("gemini_api_key", "")
    if not api_key:
        logger.warning("Gemini API key is NOT set, using HARDCODED voice list")
    else:
        logger.info("Gemini API key is set, using HARDCODED voice list")
    
    logger.info("Loading Gemini voices from HARDCODED list")
    # Gemini TTS支持的语音列表
    voices_with_gender = [
        ("Zephyr", "Female"),
        ("Puck", "Male"), 
        ("Charon", "Male"),
        ("Kore", "Female"),
        ("Fenrir", "Male"),
        ("Aoede", "Female"),
        ("Thalia", "Female"),
        ("Sage", "Male"),
        ("Echo", "Female"),
        ("Harmony", "Female"),
        ("Lux", "Female"),
        ("Nova", "Female"),
        ("Vale", "Male"),
        ("Orion", "Male"),
        ("Atlas", "Male"),
    ]
    
    # 添加gemini:前缀，并格式化为显示名称
    result = [
        f"gemini:{voice}-{gender}"
        for voice, gender in voices_with_gender
    ]
    logger.info(f"Gemini loaded {len(result)} hardcoded voices: {result}")
    return result


def is_siliconflow_voice(voice_name: str):
    """检查是否是硅基流动的声音"""
    return voice_name.startswith("siliconflow:")


def is_gemini_voice(voice_name: str):
    """检查是否是Gemini TTS的声音"""
    return voice_name.startswith("gemini:")


def tts(
    text: str,
    voice_name: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.8,
    emotion: str = "",
    is_preview: bool = False,
) -> Union[SubMaker, None]:
    if is_azure_v2_voice(voice_name):
        result = azure_tts_v2(text, voice_name, voice_file)
    elif is_siliconflow_voice(voice_name):
        # 从voice_name中提取模型和声音
        # 格式: siliconflow:model:voice-Gender
        parts = voice_name.split(":")
        if len(parts) >= 3:
            model = parts[1]
            # 移除性别后缀，例如 "alex-Male" -> "alex"
            voice_with_gender = parts[2]
            voice = voice_with_gender.split("-")[0]
            # 构建完整的voice参数，格式为 "model:voice"
            full_voice = f"{model}:{voice}"
            result = siliconflow_tts(
                text, model, full_voice, voice_rate, voice_file, voice_volume
            )
        else:
            logger.error(f"Invalid siliconflow voice name format: {voice_name}")
            result = None
    elif is_gemini_voice(voice_name):
        # 从voice_name中提取声音名称
        # 格式: gemini:voice-Gender
        parts = voice_name.split(":")
        if len(parts) >= 2:
            # 移除性别后缀，例如 "Zephyr-Female" -> "Zephyr"
            voice_with_gender = parts[1]
            voice = voice_with_gender.split("-")[0]
            result = gemini_tts(text, voice, voice_rate, voice_file, voice_volume)
        else:
            logger.error(f"Invalid gemini voice name format: {voice_name}")
            result = None
    elif is_coze_voice(voice_name):
        # 从voice_name中提取voice_id、preview_audio和preview_text
        # 格式: coze|voice_id|voice_name-gender|preview_audio|preview_text|emotions
        parts = voice_name.split("|")
        if len(parts) >= 2:
            # 提取voice_id，例如 "coze|7426720361732915209|xiaoyi-Female|https://...|preview_text|emotions" -> "7426720361732915209"
            voice_id = parts[1]
            # 提取preview_audio URL (parts[3])
            preview_audio = parts[3] if len(parts) > 3 else ""
            # 提取preview_text (parts[4])
            preview_text = parts[4] if len(parts) > 4 else ""
            # 使用传入的emotion参数
            result = coze_tts(text, voice_id, voice_rate, voice_file, voice_volume, preview_audio, preview_text, emotion, is_preview)
        else:
            logger.error(f"Invalid coze voice name format: {voice_name}")
            result = None
    elif is_qwen_voice(voice_name):
        # 从voice_name中提取voice_id、target_model、preview_audio和preview_text
        # 格式: qwen|voice_id|voice_name-gender|target_model或preview_audio|preview_text
        parts = voice_name.split("|")
        if len(parts) >= 2:
            voice_id = parts[1]
            # 判断是否为克隆声音（voice_id包含qwen-tts-vc-）
            is_cloned = "qwen-tts-vc-" in voice_id
            
            if is_cloned:
                # 克隆声音格式: qwen|voice_id|name-gender|target_model|
                target_model = parts[3] if len(parts) > 3 else ""
                preview_audio = ""
                preview_text = ""
                result = qwen_tts(text, voice_id, voice_rate, voice_file, voice_volume, preview_audio, preview_text, is_preview, target_model)
            else:
                # 普通声音格式: qwen|voice_id|voice_name-gender|preview_audio|preview_text
                preview_audio = parts[3] if len(parts) > 3 else ""
                preview_text = parts[4] if len(parts) > 4 else ""
                result = qwen_tts(text, voice_id, voice_rate, voice_file, voice_volume, preview_audio, preview_text, is_preview)
        else:
            logger.error(f"Invalid qwen voice name format: {voice_name}")
            result = None
    elif is_bailian_token_plan_voice(voice_name):
        # 从voice_name中提取voice_id
        # 格式: BailianTokenPlan|voice_id|voice_name-gender||
        parts = voice_name.split("|")
        if len(parts) >= 2:
            voice_id = parts[1]
            result = qwen_tts(text, voice_id, voice_rate, voice_file, voice_volume, "", "", is_preview, "", provider="bailian_token_plan")
        else:
            logger.error(f"Invalid token plan voice name format: {voice_name}")
            result = None
    else:
        # Default to Azure TTS v1 (Edge TTS)
        logger.info(f"[TTS] Using Azure TTS v1 for voice: {voice_name}")
        result = azure_tts_v1(text, voice_name, voice_rate, voice_file, voice_volume)
    
    # --- Speed post-processing for providers that don't support native speed ---
    # Coze, SiliconFlow apply speed via their APIs. Qwen applies speed internally
    # via pitch-preserving time-stretching. Edge TTS (Azure v1) applies speed via rate=.
    # Gemini and Azure v2 do NOT support speed natively — apply via pydub.
    _native_speed_providers = (
        is_coze_voice(voice_name) or
        is_siliconflow_voice(voice_name) or
        is_qwen_voice(voice_name) or
        is_bailian_token_plan_voice(voice_name) or
        not (is_azure_v2_voice(voice_name) or is_gemini_voice(voice_name))
    )

    if not _native_speed_providers and voice_rate != 1.0 and os.path.exists(voice_file):
        try:
            from pydub import AudioSegment
            audio_seg = AudioSegment.from_file(voice_file)
            duration_before = len(audio_seg) / 1000
            logger.info(f"Speed post-processing: voice={voice_name[:30]}, rate={voice_rate}x, duration_before={duration_before:.1f}s")
            # Change speed by resampling: higher rate = higher pitch + shorter duration
            new_frame_rate = int(audio_seg.frame_rate * voice_rate)
            adjusted = audio_seg._spawn(audio_seg.raw_data, overrides={'frame_rate': new_frame_rate})
            adjusted = adjusted.set_frame_rate(audio_seg.frame_rate)
            adjusted.export(voice_file, format="mp3")
            duration_after = len(adjusted) / 1000
            logger.info(f"Speed post-processing done: duration {duration_before:.1f}s → {duration_after:.1f}s")
        except Exception as e:
            logger.warning(f"Failed to apply speed adjustment: {e}")

    # Apply volume adjustment only for providers that do NOT handle volume internally.
    # SiliconFlow applies volume natively via the 'gain' API parameter.
    # Coze and Qwen apply volume via pydub inside their own functions (and return None).
    # Azure v1/v2 and Gemini do NOT handle volume, so the generic post-processing applies it here.
    _volume_handled_internally = (
        is_siliconflow_voice(voice_name) or
        is_coze_voice(voice_name) or
        is_qwen_voice(voice_name)
    )
    if not _volume_handled_internally and voice_volume != 1.0 and os.path.exists(voice_file):
        try:
            from moviepy.audio.fx.MultiplyVolume import MultiplyVolume
            logger.info(f"Applying volume adjustment: {voice_volume}x")
            audio_clip = AudioFileClip(voice_file)
            audio_clip = audio_clip.with_effects([MultiplyVolume(voice_volume)])
            temp_file = voice_file + ".temp.mp3"
            audio_clip.write_audiofile(temp_file, codec='mp3')
            audio_clip.close()
            os.replace(temp_file, voice_file)
            logger.info(f"Volume adjustment applied successfully")
        except Exception as e:
            logger.warning(f"Failed to apply volume adjustment: {e}")
    
    return result

def _format_text(text: str) -> str:
    # text = text.replace("\n", " ")
    text = text.replace("[", " ")
    text = text.replace("]", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("{", " ")
    text = text.replace("}", " ")
    text = text.strip()
    return text

def create_subtitle(sub_maker: submaker.SubMaker, text: str, subtitle_file: str):
    """
    优化字幕文件
    1. 将字幕文件按照标点符号分割成多行
    2. 逐行匹配字幕文件中的文本
    3. 生成新的字幕文件
    """

    text = _format_text(text)

    def formatter(idx: int, start_time: float, end_time: float, sub_text: str) -> str:
        """
        1
        00:00:00,000 --> 00:00:02,360
        跑步是一项简单易行的运动
        """
        start_t = mktimestamp(start_time).replace(".", ",")
        end_t = mktimestamp(end_time).replace(".", ",")
        return f"{idx}\n{start_t} --> {end_t}\n{sub_text}\n"

    start_time = -1.0
    sub_items = []
    sub_index = 0

    script_lines = utils.split_string_by_punctuations(text)

    def match_line(_sub_line: str, _sub_index: int):
        if len(script_lines) <= _sub_index:
            return ""

        _line = script_lines[_sub_index]
        if _sub_line == _line:
            return script_lines[_sub_index].strip()

        _sub_line_ = re.sub(r"[^\w\s]", "", _sub_line)
        _line_ = re.sub(r"[^\w\s]", "", _line)
        if _sub_line_ == _line_:
            return _line_.strip()

        _sub_line_ = re.sub(r"\W+", "", _sub_line)
        _line_ = re.sub(r"\W+", "", _line)
        if _sub_line_ == _line_:
            return _line.strip()

        return ""

    sub_line = ""

    try:
        for _, (offset, sub) in enumerate(zip(sub_maker.offset, sub_maker.subs)):
            _start_time, end_time = offset
            if start_time < 0:
                start_time = _start_time

            sub = unescape(sub)
            sub_line += sub
            sub_text = match_line(sub_line, sub_index)
            if sub_text:
                sub_index += 1
                line = formatter(
                    idx=sub_index,
                    start_time=start_time,
                    end_time=end_time,
                    sub_text=sub_text,
                )
                sub_items.append(line)
                start_time = -1.0
                sub_line = ""

        if len(sub_items) == len(script_lines):
            with open(subtitle_file, "w", encoding="utf-8") as file:
                file.write("\n".join(sub_items) + "\n")
            try:
                sbs = subtitles.file_to_subtitles(subtitle_file, encoding="utf-8")
                duration = max([tb for ((ta, tb), txt) in sbs])
                logger.info(
                    f"completed, subtitle file created: {subtitle_file}, duration: {duration}"
                )
            except Exception as e:
                logger.error(f"failed, error: {str(e)}")
                os.remove(subtitle_file)
        else:
            logger.warning(
                f"failed, sub_items len: {len(sub_items)}, script_lines len: {len(script_lines)}"
            )

    except Exception as e:
        logger.error(f"failed, error: {str(e)}")

def _get_audio_duration_from_submaker(sub_maker: submaker.SubMaker):
    """
    获取音频时长
    """
    if not sub_maker.offset:
        return 0.0
    return sub_maker.offset[-1][1] / 10000000

def _get_audio_duration_from_mp3(mp3_file: str) -> float:
    """
    获取MP3音频时长
    """
    if not os.path.exists(mp3_file):
        logger.error(f"MP3 file does not exist: {mp3_file}")
        return 0.0

    try:
        # Use moviepy to get the duration of the MP3 file
        with AudioFileClip(mp3_file) as audio:
            return audio.duration  # Duration in seconds
    except Exception as e:
        logger.error(f"Failed to get audio duration from MP3: {str(e)}")
        return 0.0

def get_audio_duration( target: Union[str, submaker.SubMaker]) -> float:
    """
    获取音频时长
    如果是SubMaker对象，则从SubMaker中获取时长
    如果是MP3文件，则从MP3文件中获取时长
    """
    if isinstance(target, submaker.SubMaker):
        return _get_audio_duration_from_submaker(target)
    elif isinstance(target, str) and target.endswith(".mp3"):
        return _get_audio_duration_from_mp3(target)
    else:
        logger.error(f"Invalid target type: {type(target)}")
        return 0.0
# ---------------------------------------------------------------------------
# 供应商专属模块：此处仅在文件末尾再导出（不在顶部导入），
# 避免子模块反向导入本文件时产生循环依赖。
# ---------------------------------------------------------------------------
from app.services.voice_azure import (
    get_azure_voices,
    get_all_azure_voices,
    parse_voice_name,
    is_azure_v2_voice,
    azure_tts_v1,
    azure_tts_v2,
)
from app.services.voice_coze import (
    get_coze_voices,
    is_coze_voice,
    coze_tts,
)
from app.services.voice_qwen import (
    get_qwen_voices,
    get_bailian_token_plan_voices,
    is_qwen_voice,
    is_bailian_token_plan_voice,
    qwen_tts,
)