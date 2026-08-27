"""
Coze 扣子专用模块：语音列表、TTS 合成。
从 voice.py 拆分而来，由 voice.py 在文件末尾再导出。
"""
from datetime import datetime
from typing import Union

import requests
from edge_tts import SubMaker
from loguru import logger

from app.config import config
from app.utils import utils

# 缓存字典，用于存储Coze TTS音色信息
_voice_cache = {
    'coze': {'voices': [], 'timestamp': None, 'api_key': None},
}

# 缓存有效期（秒）
CACHE_DURATION = 3600  # 1小时

def get_coze_voices(force_refresh=False) -> list[str]:
    """
    获取Coze TTS的中文声音列表
    
    Args:
        force_refresh: 是否强制刷新缓存
    
    Returns:
        声音列表，格式为: "coze|voice_id|voice_name-gender|preview_audio|preview_text"
    """
    global _voice_cache
    
    # 检查缓存
    api_key = config.coze.get("api_key", "")
    cache_entry = _voice_cache['coze']
    
    # 检查缓存是否有效
    current_time = datetime.now().timestamp()
    if not force_refresh and cache_entry['voices'] and cache_entry['timestamp']:
        cache_age = current_time - cache_entry['timestamp']
        if cache_age < CACHE_DURATION and cache_entry['api_key'] == api_key:
            logger.info(f"Using cached Coze voices (age: {cache_age:.1f}s)")
            return cache_entry['voices']
    
    logger.info("Fetching Coze voices from API")
    
    # 定义默认中文声音列表
    voices_with_id_gender = [
        ("7426720361732915209", "湾区大叔", "Male"),
        ("7426720361732915210", "财阀千金", "Female"),
        ("7426720361732915211", "青叔", "Male"),
        ("7426720361732915212", "御姐", "Female"),
        ("7426720361732915213", "阳光少年", "Male"),
        ("7426720361732915214", "可爱少女", "Female"),
        ("7426720361732915215", "温和大叔", "Male"),
        ("7426720361732915216", "甜美女生", "Female"),
        ("7426720361732915217", "成熟男声", "Male"),
        ("7426720361732915218", "温柔女声", "Female"),
    ]

    voices = []

    try:
        # 配置Coze API
        api_key = config.coze.get("api_key", "")
        if not api_key:
            # 如果没有API key，返回默认的语音列表
            logger.info("No Coze API key found, using DEFAULT hardcoded voices")
            for voice_id, voice_name, gender in voices_with_id_gender:
                voices.append(f"coze|{voice_id}|{voice_name}-{gender}||")
            logger.info(f"Coze loaded {len(voices)} DEFAULT hardcoded voices (no API key): {voices}")
            # 更新缓存
            _voice_cache['coze'] = {
                'voices': voices,
                'timestamp': current_time,
                'api_key': api_key
            }
            return voices
        
        # Coze TTS声音列表API endpoint
        url = "https://api.coze.cn/v1/audio/voices"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        page_num = 0
        params = {}

        has_more = True
        while has_more:
            page_num += 1
            params["page_num"] = page_num
            # Send request
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                # 解析响应
                data = response.json()
                logger.info(f"Coze voices API response: {data}")

                # Coze API响应格式: {"data": {"voices": [...]}, "code": 0, "msg": "success"}
                response_data = data.get("data", {})
                assert response_data, "Coze API response does not contain data"
                voice_list = response_data.get("voice_list", [])

                if len(voice_list) > 0:
                    for voice in voice_list:
                        # 根据Coze API文档，使用正确的字段名
                        voice_id = voice.get("voice_id", "")
                        voice_name = voice.get("name", "")
                        preview_audio = voice.get("preview_audio", "")
                        preview_text = voice.get("preview_text", "")
                        # 尝试从speaker_id中提取性别信息
                        speaker_id = voice.get("speaker_id", "")
                        gender = voice.get("gender", "")
                        # 获取语言代码
                        language_code = voice.get("language_code", "")
                        # 获取支持的情感
                        support_emotions = voice.get("support_emotions", [])
                        
                        # 只添加中文声音 (language_code 为 "zh")
                        if language_code != "zh":
                            continue
                        
                        # 处理情感列表，格式化为"emotion-display_name"
                        emotion_strings = []
                        for emotion in support_emotions:
                            if isinstance(emotion, dict):
                                # 如果是字典，提取emotion和display_name
                                emotion_value = emotion.get("emotion", "")
                                display_name = emotion.get("display_name", "")
                                if emotion_value:
                                    if display_name:
                                        emotion_strings.append(f"{emotion_value}-{display_name}")
                                    else:
                                        emotion_strings.append(emotion_value)
                            else:
                                # 如果不是字典，直接使用
                                emotion_strings.append(str(emotion))
                        
                        if not gender and speaker_id:
                            # speaker_id格式如: "zh_female_cancan_tob" 或 "zh_male_xxx"
                            if "_female_" in speaker_id.lower():
                                gender = "Female"
                            elif "_male_" in speaker_id.lower():
                                gender = "Male"
                        # 如果speaker_id中没有性别信息，尝试从name中提取
                        if not gender and voice_name:
                            # 检查name中是否包含"男"或"女"
                            if any(gender_term in voice_name.lower() for gender_term in ["女", "姐", "妹","美","靓"]):
                                gender = "Female"
                            elif any(gender_term in voice_name.lower() for gender_term in ["男", "哥", "爷", "伙","婿","叔","兄","弟","俊","帅"]):
                                gender = "Male"
                        if not gender:
                            gender = "Unknown"
                        gender = gender.title()
                        
                        if voice_id and voice_name:
                            # 新格式: coze|voice_id|voice_name-gender|preview_audio|preview_text|emotions
                            # 使用|作为分隔符，避免与URL中的:冲突
                            emotions_str = ",".join(emotion_strings) if emotion_strings else ""
                            voices.append(f"coze|{voice_id}|{voice_name}-{gender}|{preview_audio}|{preview_text}|{emotions_str}")
                            logger.info(f"Found Chinese voice: {voice_id} - {voice_name} ({gender}) with preview audio, text, and emotions: {emotions_str}")

                    has_more = response_data.get("has_more", False)
                    continue
                else:
                    logger.warning(f"Coze API response does not contain voices data. Response: {data}")
                    break

                # 如果API返回的列表为空，使用默认列表
                if not voices:
                    logger.warning("Coze API returned empty voice list, using DEFAULT hardcoded voices")
                    for voice_id, voice_name, gender in voices_with_id_gender:
                        voices.append(f"coze|{voice_id}|{voice_name}-{gender}||")
                    logger.info(f"Coze loaded {len(voices)} DEFAULT hardcoded voices (API empty response): {voices}")
                    break
            else:
                # API调用失败，返回默认列表
                logger.error(f"Failed to get Coze voices from API: {response.status_code} {response.text}")
                for voice_id, voice_name, gender in voices_with_id_gender:
                    voices.append(f"coze|{voice_id}|{voice_name}-{gender}||")
                logger.info(f"Coze loaded {len(voices)} DEFAULT hardcoded voices (API call failed): {voices}")
                break
        
        # 如果没有从API获取到任何声音，使用默认列表
        if len(voices) == 0:
            logger.warning("No voices fetched from API, using DEFAULT hardcoded voices")
            for voice_id, voice_name, gender in voices_with_id_gender:
                voices.append(f"coze|{voice_id}|{voice_name}-{gender}||")
            logger.info(f"Coze loaded {len(voices)} DEFAULT hardcoded voices (no voices from API): {voices}")
        
        # 更新缓存
        _voice_cache['coze'] = {
            'voices': voices,
            'timestamp': current_time,
            'api_key': api_key
        }
        logger.info(f"Coze voices cached: {len(voices)} voices")
        
        return voices
    except Exception as e:
        # 发生异常，返回默认列表
        logger.error(f"Error getting Coze voices from API: {str(e)}")
        for voice_id, voice_name, gender in voices_with_id_gender:
            voices.append(f"coze|{voice_id}|{voice_name}-{gender}||")
        logger.info(f"Coze loaded {len(voices)} DEFAULT hardcoded voices (exception occurred): {voices}")
        
        # 即使发生异常，也更新缓存以避免重复失败
        _voice_cache['coze'] = {
            'voices': voices,
            'timestamp': current_time,
            'api_key': api_key
        }
        return voices

def is_coze_voice(voice_name: str):
    """检查是否是Coze TTS的声音"""
    return voice_name.startswith("coze|")

def coze_tts(
    text: str,
    voice_id: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.0,
    preview_audio: str = "",
    preview_text: str = "",
    emotion: str = "",
    is_preview: bool = False,
) -> Union[SubMaker, None]:
    """
    使用Coze TTS生成语音
    
    Args:
        text: 要转换的文本
        voice_id: 语音ID，如 "7426720361732915209", "7426720361732915210" 等
        voice_rate: 语音速率
        voice_file: 输出音频文件路径
        voice_volume: 音频音量
        preview_audio: 预览音频URL（用于试听）
        preview_text: 预览文本（用于匹配试听）
        emotion: 语音情感（如果支持）
        
    Returns:
        SubMaker对象或None
    """
    import io
    
    try:
        from pydub import AudioSegment
    except ImportError as e:
        logger.error(f"Failed to import pydub: {str(e)}")
        logger.error("Please install pydub and its dependencies: pip install pydub")
        return None
    
    try:
        # 只有在试听时才使用预览音频
        # 试听时传入的文本就是预览文本本身，且长度较短
        # 正式生成时，即使文本较短，也应该使用TTS API生成
        is_preview_mode = is_preview and preview_text and text.strip() == preview_text.strip()
        
        if preview_audio and is_preview_mode:
            logger.info(f"Preview mode: downloading preview audio from: {preview_audio}")
            try:
                response = requests.get(preview_audio, timeout=60)
                if response.status_code == 200:
                    with open(voice_file, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Preview audio saved to: {voice_file}")
                    # 预览音频时不需要创建字幕，直接返回None
                    return None
                else:
                    logger.error(f"Failed to download preview audio: {response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading preview audio: {str(e)}")
            # If download fails, continue trying TTS API
        
        # 配置Coze API
        api_key = config.coze.get("api_key", "")
        if not api_key:
            logger.error("Coze API key is not set")
            return None
        
        # Coze TTS API endpoint
        url = "https://api.coze.cn/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Text segmentation processing - Coze API has length limit
        # Split text by punctuation, each segment not exceeding 1024 characters
        max_segment_length = 1024
        segments = []
        
        if len(text) <= max_segment_length:
            # Text length within limit, process directly
            segments = [text]
        else:
            # Text length exceeds limit, need segmentation
            logger.info(f"Text length {len(text)} exceeds Coze API limit, splitting into segments")
            
            # Use utils.split_string_by_punctuations to split text
            sentences = utils.split_string_by_punctuations(text)
            
            current_segment = ""
            for sentence in sentences:
                if len(current_segment) + len(sentence) + 1 <= max_segment_length:
                    # Current segment plus new sentence won't exceed limit, add to current segment
                    if current_segment:
                        current_segment += " " + sentence
                    else:
                        current_segment = sentence
                else:
                    # Current segment plus new sentence will exceed limit, save current segment and start new segment
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = sentence
            
            # Save the last segment
            if current_segment:
                segments.append(current_segment)
            
            logger.info(f"Split text into {len(segments)} segments")
        
        # Process each text segment
        audio_segments = []
        for i, segment in enumerate(segments):
            logger.debug(f"Processing segment {i+1}/{len(segments)}, length: {len(segment)}")
            
            # Build request parameters - use correct parameter names and types
            payload = {
                "voice_id": voice_id,
                "speed": float(voice_rate),  # Coze API expects float
                "sample_rate": 48000,  # Updated to 48kHz for better audio quality
                "input": segment,  # Use input parameter instead of text
                "language_code": "zh"  # Apply Chinese language code for all Coze voices
            }
            
            # If emotion parameter is provided, add to request
            if emotion:
                payload["emotion"] = emotion
            
            # Send request
            response = requests.post(url, json=payload, headers=headers)
            
            # Record complete API response information (for debugging)
            logger.debug(f"Coze TTS API response status for segment {i+1}: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Coze TTS API response body for segment {i+1}: {response.text}")
                return None
            
            # Get audio data
            audio_bytes = response.content
            
            # Try different audio formats - Coze may return different formats
            try:
                # Try to load audio directly
                audio_segment = AudioSegment.from_file(
                    io.BytesIO(audio_bytes),
                    format="mp3"  # Assume Coze returns MP3 format
                )
                audio_segments.append(audio_segment)
                logger.info(f"Segment {i+1} decoded: {len(audio_segment)/1000:.1f}s, text_len={len(segment)}, speed={float(voice_rate)}")
            except Exception as e:
                logger.error(f"Failed to load audio for segment {i+1}: {e}")
                logger.error(f"Audio data length: {len(audio_bytes)} bytes")
                return None
        
        # Merge audio segments and apply volume adjustment
        if len(audio_segments) == 1:
            # Only one segment, apply volume and export
            audio_segment = audio_segments[0]
            logger.info(f"Coze TTS: 1 segment, duration={len(audio_segment)/1000:.1f}s")
            if voice_volume != 1.0:
                logger.info(f"Applying volume adjustment in Coze TTS: {voice_volume}x")
                # pydub uses dB, convert volume multiplier to dB
                # volume_multiplier = 10^(dB/20) => dB = 20*log10(volume_multiplier)
                import math
                volume_change_db = 20 * math.log10(voice_volume)
                audio_segment = audio_segment + volume_change_db
            audio_segment.export(voice_file, format="mp3")
        else:
            # Multiple segments, merge, apply volume, and export
            durations = [f"{len(seg)/1000:.1f}s" for seg in audio_segments]
            logger.info(f"Merging {len(audio_segments)} audio segments: [{', '.join(durations)}]")
            combined = audio_segments[0]
            for i in range(1, len(audio_segments)):
                combined += audio_segments[i]
            logger.info(f"Coze TTS: merged duration={len(combined)/1000:.1f}s")
            
            if voice_volume != 1.0:
                logger.info(f"Applying volume adjustment in Coze TTS: {voice_volume}x")
                import math
                volume_change_db = 20 * math.log10(voice_volume)
                combined = combined + volume_change_db
            
            combined.export(voice_file, format="mp3")
        
        logger.info(f"completed, output file: {voice_file}")
        
        # Coze TTS只负责音频生成，字幕由Whisper生成
        # 返回None，让generate_subtitle函数使用Whisper生成字幕
        return None
        
    except ImportError as e:
        logger.error(f"Missing required package for Coze TTS: {str(e)}. Please install: pip install pydub")
        return None
    except Exception as e:
        logger.error(f"Coze TTS failed, error: {str(e)}")
        return None