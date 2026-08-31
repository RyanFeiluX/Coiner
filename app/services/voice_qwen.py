"""
Qwen 千问 / 阿里百炼 Token Plan 专用模块：克隆音色、语音列表、TTS 合成。
从 voice.py 拆分而来，由 voice.py 在文件末尾再导出。
"""
import os
from datetime import datetime
from typing import Union

import requests
from edge_tts import SubMaker
from loguru import logger

from app.config import config
from app.utils import utils

# 缓存字典，用于存储Qwen/百炼Token Plan TTS音色信息
_voice_cache = {
    'qwen': {'voices': [], 'timestamp': None, 'api_key': None},
    'bailian_token_plan': {'voices': [], 'timestamp': None, 'api_key': None},
}

# 缓存有效期（秒）
CACHE_DURATION = 3600  # 1小时

# Qwen-Audio-TTS 情感控制标签 (仅 qwen-audio-3.0-tts-plus / qwen-audio-3.0-tts-flash 支持)
# 格式: {emotion_key: (text_tag, display_name)}
# 通过在 text 参数中嵌入标签控制语音情感，标签作用于其后所有文本直到下一个标签
BAILIAN_EMOTION_TAGS = {
    "excited":       ("[excited]",       "兴奋"),
    "sad":           ("[sad]",           "悲伤"),
    "angry":         ("[angry]",         "愤怒"),
    "curious":       ("[curious]",       "好奇"),
    "serious":       ("[serious]",       "严肃"),
    "empathetic":    ("[empathetic]",    "共情"),
    "whispers":      ("[whispers]",      "耳语"),
    "mischievously": ("[mischievously]", "调皮"),
    "bored":         ("[bored]",         "无聊"),
    "tired":         ("[tired]",         "疲惫"),
    "crying":        ("[crying]",        "哭泣"),
    "panicked":      ("[panicked]",      "恐慌"),
    "laughing":      ("[laughing]",      "大笑"),
    "sighing":       ("[sighing]",       "叹息"),
}

def load_cloned_voices_from_files() -> list:
    """
    从本地JSON文件加载克隆的声音列表
    
    JSON文件格式示例：
    [
        {
            "voiceId": "qwen-tts-vc-myvoice-voice-xxx",
            "displayName": "擎苍",
            "gender": "Male",
            "model": "qwen3-tts-vc-2026-01-22",
            "brief": "Created via qwen3-tts-vc-2026-01-22",
            "provider": "Qwen",
            "region": "Beijing"
        }
    ]
    
    Returns:
        克隆声音列表，每个元素包含 (voice_id, display_name, gender, target_model)
    """
    cloned_voices = []
    
    import json
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    for filename in os.listdir(project_root):
        if filename.endswith('.json'):
            json_path = os.path.join(project_root, filename)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        voice_id = item.get('voiceId', '') or item.get('voice_id', '')
                        display_name = item.get('displayName', '') or item.get('name', '') or item.get('display_name', '')
                        gender = item.get('gender', '') or 'Unknown'
                        target_model = item.get('model', '') or item.get('target_model', '')
                        
                        if voice_id and display_name:
                            if not any(v[0] == voice_id for v in cloned_voices):
                                cloned_voices.append((voice_id, display_name, gender, target_model))
                                logger.info(f"Loaded cloned voice from file: {display_name} ({gender}) - {voice_id} (model: {target_model})")
                elif isinstance(data, dict):
                    voice_id = data.get('voiceId', '') or data.get('voice_id', '')
                    display_name = data.get('displayName', '') or data.get('name', '') or data.get('display_name', '')
                    gender = data.get('gender', '') or 'Unknown'
                    target_model = data.get('model', '') or data.get('target_model', '')
                    
                    if voice_id and display_name:
                        cloned_voices.append((voice_id, display_name, gender, target_model))
                        logger.info(f"Loaded cloned voice from file: {display_name} ({gender}) - {voice_id} (model: {target_model})")
            except Exception as e:
                logger.warning(f"Failed to load cloned voices from {filename}: {str(e)}")
    
    return cloned_voices

def fetch_cloned_voices_from_api(api_key: str) -> list:
    """
    通过HTTP API获取Qwen TTS克隆声音列表（作为本地文件的备用）
    
    根据官方文档：https://docs.qwencloud.com/api-reference/speech-synthesis/voice-cloning/qwen/list-voices
    
    Args:
        api_key: Qwen API key
        
    Returns:
        克隆声音列表，每个元素包含 (voice_id, display_name, gender, target_model)
    """
    cloned_voices = []
    
    if not api_key:
        logger.warning("Qwen API key is not set, skipping API fetch for cloned voices")
        return cloned_voices
    
    base_url = "https://dashscope.aliyuncs.com/api/v1"
    url = f"{base_url}/services/audio/tts/customization"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # 尝试获取Qwen克隆声音 (qwen-voice-enrollment)
    # 根据官方文档：https://docs.qwencloud.com/api-reference/speech-synthesis/voice-cloning/qwen/list-voices
    qwen_payload = {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "list",
            "page_size": 50,
            "page_index": 0
        }
    }
    
    # 尝试获取CosyVoice克隆声音 (voice-enrollment)
    # 根据官方文档：https://docs.qwencloud.com/api-reference/speech-synthesis/voice-cloning/cosyvoice/list-voices
    cosyvoice_payload = {
        "model": "voice-enrollment",
        "input": {
            "action": "list_voice",
            "page_size": 50,
            "page_index": 0
        }
    }
    
    for payload in [qwen_payload, cosyvoice_payload]:
        try:
            model_name = payload["model"]
            logger.info(f"Fetching cloned voices from Qwen TTS API (model: {model_name})")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.debug(f"Cloned voices API response ({model_name}): {response_data}")
                    
                    # 解析响应
                    voice_list = []
                    if response_data.get("output"):
                        voice_list = response_data["output"].get("voice_list", [])
                        if not voice_list and "voices" in response_data["output"]:
                            voice_list = response_data["output"]["voices"]
                    elif response_data.get("data"):
                        voice_list = response_data["data"].get("voice_list", []) or response_data["data"].get("voices", [])
                    
                    for voice in voice_list:
                        # 获取voice_id
                        voice_id = voice.get("voice_id", "") or voice.get("voice", "") or voice.get("voiceId", "")
                        
                        # 获取display_name
                        display_name = voice.get("name", "") or voice.get("display_name", "") or voice.get("displayName", "")
                        if not display_name and voice_id:
                            parts = voice_id.split("-")
                            if len(parts) >= 4:
                                display_name = parts[3]
                        
                        # 获取gender
                        gender = voice.get("gender", "") or "Unknown"
                        
                        # 获取target_model（克隆声音必需的合成模型）
                        target_model = voice.get("target_model", "") or ""
                        
                        if voice_id:
                            if not any(v[0] == voice_id for v in cloned_voices):
                                if not display_name:
                                    display_name = voice_id[:20] + "..." if len(voice_id) > 20 else voice_id
                                
                                cloned_voices.append((voice_id, display_name, gender, target_model))
                                logger.info(f"Fetched cloned voice from API: {display_name} ({gender}) - {voice_id} (model: {target_model})")
                    
                    if cloned_voices:
                        logger.info(f"Successfully fetched {len(cloned_voices)} cloned voices from API")
                        
                except ValueError as e:
                    logger.error(f"Failed to parse cloned voices API response ({model_name}): {e}")
            else:
                logger.debug(f"Cloned voices API request failed ({model_name}): {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            logger.debug(f"Error fetching cloned voices from API: {str(e)}")
    
    return cloned_voices

def get_qwen_voices(force_refresh=False) -> list[str]:
    """
    获取Qwen TTS的声音列表，包括克隆的声音
    
    Args:
        force_refresh: 是否强制刷新缓存
    
    Returns:
        声音列表，格式为: "qwen|voice_id|voice_name-gender|preview_audio|preview_text"
    """
    global _voice_cache
    
    # 检查缓存
    api_key = config.qwen.get("api_key", "")
    cache_entry = _voice_cache['qwen']
    
    # 检查缓存是否有效
    current_time = datetime.now().timestamp()
    if not force_refresh and cache_entry['voices'] and cache_entry['timestamp']:
        cache_age = current_time - cache_entry['timestamp']
        if cache_age < CACHE_DURATION and cache_entry['api_key'] == api_key:
            logger.info(f"Using cached Qwen voices (age: {cache_age:.1f}s)")
            return cache_entry['voices']
    
    logger.info("Loading Qwen voices from hardcoded list")
    
    # 定义默认中文声音列表 (Qwen-TTS 官方语音列表)
    voices_with_id_gender = [
        ("Cherry", "芊悦", "Female"),
        ("Serena", "苏瑶", "Female"),
        ("Ethan", "晨煦", "Male"),
        ("Chelsie", "千雪", "Female"),
        ("Momo", "茉兔", "Female"),
        ("Vivian", "十三", "Female"),
        ("Moon", "月白", "Male"),
        ("Maia", "四月", "Female"),
        ("Kai", "凯", "Male"),
        ("Nofish", "不吃鱼", "Male"),
        ("Bella", "萌宝", "Female"),
        ("Jennifer", "詹妮弗", "Female"),
        ("Ryan", "甜茶", "Male"),
        ("Katerina", "卡捷琳娜", "Female"),
        ("Aiden", "艾登", "Male"),
        ("Eldric Sage", "沧明子", "Male"),
        ("Mia", "乖小妹", "Female"),
        ("Mochi", "沙小弥", "Male"),
        ("Bellona", "燕铮莺", "Female"),
        ("Vincent", "田叔", "Male"),
        ("Bunny", "萌小姬", "Female"),
        ("Neil", "阿闻", "Male"),
        ("Elias", "墨讲师", "Female"),
        ("Arthur", "徐大爷", "Male"),
        ("Nini", "邻家妹妹", "Female"),
        ("Seren", "小婉", "Female"),
    ]

    voices = []

    try:
        api_key = config.qwen.get("api_key", "")
        
        # 使用硬编码的语音列表
        logger.info("Using hardcoded Qwen voices")
        for voice_id, voice_name, gender in voices_with_id_gender:
            voices.append(f"qwen|{voice_id}|{voice_name}-{gender}||")
        logger.info(f"Qwen loaded {len(voices)} hardcoded voices")
        
        # 加载克隆的声音 - 优先从独立配置文件加载，备用从API获取
        cloned_voices = []
        
        # 优先从独立配置文件加载克隆声音
        from app.config.cloned_voices import cloned_voices_config
        config_cloned_voices = cloned_voices_config.get_voices(provider="qwen")
        if config_cloned_voices:
            for voice_data in config_cloned_voices:
                voice_id = voice_data.get("voiceId", "")
                display_name = voice_data.get("displayName", "")
                gender = voice_data.get("gender", "") or "Unknown"
                target_model = voice_data.get("model", "")
                
                if voice_id and display_name:
                    cloned_voices.append((voice_id, display_name, gender, target_model))
            
            logger.info(f"Qwen loaded {len(cloned_voices)} cloned voices from cloned_voices.json")
        
        # 如果配置中没有，且有API key，则从API获取
        if not cloned_voices and api_key:
            api_cloned_voices = fetch_cloned_voices_from_api(api_key)
            if api_cloned_voices:
                cloned_voices.extend(api_cloned_voices)
                logger.info(f"Qwen loaded {len(api_cloned_voices)} cloned voices from API")
        
        # 如果都没有，记录信息
        if not cloned_voices:
            logger.info("No cloned voices found (neither in config nor API)")
        
        # 添加克隆声音到列表
        if cloned_voices:
            for voice_id, display_name, gender, target_model in cloned_voices:
                voices.append(f"qwen|{voice_id}|{display_name}-{gender}|{target_model}|")
            logger.info(f"Qwen loaded {len(cloned_voices)} cloned voices total: {[v[1] for v in cloned_voices]}")
        
        # 更新缓存
        _voice_cache['qwen'] = {
            'voices': voices,
            'timestamp': current_time,
            'api_key': api_key
        }
        logger.info(f"Qwen voices cached: {len(voices)} voices")
        
        return voices
    except Exception as e:
        # 发生异常，返回默认列表
        logger.error(f"Error getting Qwen voices: {str(e)}")
        for voice_id, voice_name, gender in voices_with_id_gender:
            voices.append(f"qwen|{voice_id}|{voice_name}-{gender}||")
        logger.info(f"Qwen loaded {len(voices)} DEFAULT hardcoded voices (exception occurred): {voices}")
        
        # 即使发生异常，也更新缓存以避免重复失败
        _voice_cache['qwen'] = {
            'voices': voices,
            'timestamp': current_time,
            'api_key': api_key
        }
        return voices

def get_bailian_token_plan_voices(force_refresh=False) -> list[str]:
    """
    获取阿里百炼Token Plan TTS的声音列表（SpeechSynthesizer端点专用）

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        声音列表，格式为: "BailianTokenPlan|voice_id|voice_name-gender|||emotions"
    """
    global _voice_cache

    api_key = config.bailian_token_plan.get("api_key", "")
    cache_entry = _voice_cache['bailian_token_plan']

    current_time = datetime.now().timestamp()
    if not force_refresh and cache_entry['voices'] and cache_entry['timestamp']:
        cache_age = current_time - cache_entry['timestamp']
        if cache_age < CACHE_DURATION and cache_entry['api_key'] == api_key:
            logger.info(f"Using cached Token Plan voices (age: {cache_age:.1f}s)")
            return cache_entry['voices']

    logger.info("Loading Bailian Token Plan voices from hardcoded list")

    # qwen-audio-3.0-tts-plus 官方系统音色
    voices_with_id_gender = [
        ("longanlingxin", "龙安灵心", "Female"),
        ("longanlufeng", "龙安鲁风", "Male"),
    ]

    # 将支持的情感列表编码到voice_name末尾，格式与Coze一致: parts[5]
    # (parts[3]=preview_audio, parts[4]=preview_text 保留为空占位)
    emotion_str = ",".join(f"{k}-{v[1]}" for k, v in BAILIAN_EMOTION_TAGS.items())

    voices = []
    for voice_id, voice_name, gender in voices_with_id_gender:
        voices.append(f"BailianTokenPlan|{voice_id}|{voice_name}-{gender}|||{emotion_str}")

    _voice_cache['bailian_token_plan'] = {
        'voices': voices,
        'timestamp': current_time,
        'api_key': api_key
    }
    logger.info(f"Bailian Token Plan voices cached: {len(voices)} voices")

    return voices

def is_qwen_voice(voice_name: str):
    """检查是否是Qwen TTS的声音"""
    return voice_name.startswith("qwen|")

def is_bailian_token_plan_voice(voice_name: str):
    """检查是否是阿里百炼Token Plan TTS的声音"""
    return voice_name.startswith("BailianTokenPlan|")

def qwen_tts(
    text: str,
    voice_id: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.0,
    preview_audio: str = "",
    preview_text: str = "",
    is_preview: bool = False,
    target_model: str = "",
    provider: str = "qwen",
    emotion: str = "",
) -> Union[SubMaker, None]:
    """
    使用Qwen TTS生成语音（provider支持"qwen"和"bailian_token_plan"）

    Args:
        text: 要转换的文本
        voice_id: 语音ID，如 "7426720361732915209", "7426720361732915210" 等
        voice_rate: 语音速率
        voice_file: 输出音频文件路径
        voice_volume: 音频音量
        preview_audio: 预览音频URL（用于试听）
        preview_text: 预览文本（用于匹配试听）
        provider: 供应商，可选"qwen"或"bailian_token_plan"
        emotion: 语音情感（bailian_token_plan时通过BAILIAN_EMOTION_TAGS映射为文本标签嵌入）

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
        is_preview_mode = is_preview and preview_text and text.strip() == preview_text.strip()
        
        if preview_audio and is_preview_mode:
            logger.info(f"Preview mode: downloading preview audio from: {preview_audio}")
            try:
                response = requests.get(preview_audio, timeout=60)
                if response.status_code == 200:
                    with open(voice_file, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Preview audio saved to: {voice_file}")
                    return None
                else:
                    logger.error(f"Failed to download preview audio: {response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading preview audio: {str(e)}")
        
        # 配置Qwen API (使用HTTP API)，支持qwen和bailian_token_plan两种provider
        if provider == "bailian_token_plan":
            api_key = config.bailian_token_plan.get("api_key", "")
            # Token Plan TTS 使用固定的 DashScope 原生端点
            endpoint = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
        else:
            api_key = config.qwen.get("api_key", "")
            base_url = "https://dashscope.aliyuncs.com/api/v1"  # 硬编码Qwen API端点
            endpoint = f"{base_url}/services/audio/tts/SpeechSynthesizer"
        
        if not api_key:
            logger.warning("Qwen API key is not set, using text-to-speech fallback")
            return None
        
        logger.debug(f"Using Qwen TTS ({provider}) with endpoint: {endpoint}")
        
        # Text segmentation processing - Qwen API limit is typically 5000 characters
        max_segment_length = 5000
        segments = []
        
        if len(text) <= max_segment_length:
            segments = [text]
        else:
            logger.info(f"Text length {len(text)} exceeds Qwen API limit, splitting into segments")
            sentences = utils.split_string_by_punctuations(text)
            
            current_segment = ""
            for sentence in sentences:
                if len(current_segment) + len(sentence) + 1 <= max_segment_length:
                    if current_segment:
                        current_segment += " " + sentence
                    else:
                        current_segment = sentence
                else:
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = sentence
            
            if current_segment:
                segments.append(current_segment)
            
            logger.info(f"Split text into {len(segments)} segments")
        
        # Process each text segment
        audio_segments = []
        for i, segment in enumerate(segments):
            logger.debug(f"Processing segment {i+1}/{len(segments)}, length: {len(segment)}")
            
            if provider == "bailian_token_plan":
                # 阿里百炼Token Plan语音合成：使用固定的SpeechSynthesizer端点，直接返回音频二进制流
                try:
                    url = endpoint
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }
                    default_model = config.bailian_token_plan.get("model_name", "qwen-audio-3.0-tts-plus")
                    model = target_model if target_model else default_model
                    # 情感标签注入: 将选中的emotion映射为Qwen-Audio-TTS文本标签
                    # 标签作用于其后所有文本，按segment注入确保每段都有情感控制
                    segment_text = segment
                    if emotion and emotion in BAILIAN_EMOTION_TAGS:
                        emotion_tag = BAILIAN_EMOTION_TAGS[emotion][0]
                        segment_text = f"{emotion_tag}{segment}"
                        logger.debug(f"Token Plan TTS emotion: {emotion} -> {emotion_tag}")
                    payload = {
                        "model": model,
                        "input": {
                            "text": segment_text,
                            "voice": voice_id,
                            "format": "mp3",
                            "sample_rate": 24000
                        }
                    }
                    logger.debug(f"Token Plan TTS segment {i+1}: model={model}, text_len={len(segment_text)}")
                    response = requests.post(url, json=payload, headers=headers, timeout=60)
                    logger.debug(f"Token Plan TTS API response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            logger.debug(f"Token Plan TTS response: {response_data}")
                            
                            audio_output = response_data.get("output", {}).get("audio", {})
                            audio_url = audio_output.get("url") if isinstance(audio_output, dict) else None
                            audio_data = audio_output.get("data") if isinstance(audio_output, dict) else None
                            
                            if audio_url:
                                logger.debug(f"Downloading audio from URL: {audio_url[:100]}...")
                                audio_response = requests.get(audio_url, timeout=60)
                                if audio_response.status_code == 200:
                                    audio_bytes = audio_response.content
                                else:
                                    logger.error(f"Failed to download audio: {audio_response.status_code}")
                                    return None
                            elif audio_data:
                                import base64
                                audio_bytes = base64.b64decode(audio_data)
                            else:
                                # 尝试作为原始二进制音频处理
                                audio_bytes = response.content
                            
                            logger.debug(f"Token Plan TTS audio size: {len(audio_bytes)} bytes")
                            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                            audio_segments.append(audio_segment)
                            logger.info(f"Segment {i+1} decoded: {len(audio_segment)/1000:.1f}s, text_len={len(segment)}")
                        except Exception as e:
                            logger.error(f"Failed to decode audio: {e}")
                            temp_file = "bailian_debug_audio.mp3"
                            with open(temp_file, 'wb') as f:
                                f.write(response.content)
                            logger.info(f"Saved response to {temp_file} for debugging")
                            return None
                    else:
                        api_key_masked = f"{api_key[:8]}...{api_key[-4:]}(len={len(api_key)})" if api_key else "empty"
                        logger.error(
                            f"Token Plan TTS API failed: status={response.status_code}\n"
                            f"  url={url}\n"
                            f"  api_key={api_key_masked}\n"
                            f"  model={model}\n"
                            f"  voice={voice_id}\n"
                            f"  text_len={len(segment)}\n"
                            f"  response={response.text}"
                        )
                        return None
                except Exception as e:
                    logger.error(
                        f"Token Plan TTS API exception for segment {i+1}: {str(e)}\n"
                        f"  url={url}\n"
                        f"  api_key={'set' if api_key else 'empty'}\n"
                        f"  model={model}, voice={voice_id}"
                    )
                    return None
                continue
            
            try:
                # 使用HTTP API调用Qwen TTS (Qwen-TTS)
                url = f"{base_url}/services/aigc/multimodal-generation/generation"
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                
                # 使用target_model（克隆声音）或从配置读取默认模型
                if provider == "bailian_token_plan":
                    default_model = config.bailian_token_plan.get("model_name", "qwen-audio-3.0-tts-plus")
                else:
                    default_model = config.qwen.get("model_name", "qwen3-tts-instruct-flash")
                model = target_model if target_model else default_model
                
                payload = {
                    "model": model,
                    "input": {
                        "text": segment,
                        "voice": voice_id,
                        "language_type": "Chinese"
                    },
                    "parameters": {
                        "format": "mp3",
                        "sample_rate": 48000
                    }
                }
                if emotion:
                    payload["instructions"] = emotion
                
                logger.debug(f"Qwen TTS segment {i+1}: model={model}, text_len={len(segment)}")
                
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                
                logger.debug(f"Qwen TTS API response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"Qwen TTS response: {response_data}")
                        
                        if response_data.get("output") and response_data["output"].get("audio"):
                            audio_output = response_data["output"]["audio"]
                            logger.debug(f"Audio output: {audio_output}")
                            
                            audio_url = audio_output.get("url") if isinstance(audio_output, dict) else getattr(audio_output, 'url', None)
                            audio_data = audio_output.get("data") if isinstance(audio_output, dict) else getattr(audio_output, 'data', None)
                            
                            if audio_url:
                                # 下载音频文件
                                logger.debug(f"Downloading audio from URL: {audio_url[:100]}...")
                                audio_response = requests.get(audio_url, timeout=60)
                                if audio_response.status_code == 200:
                                    audio_bytes = audio_response.content
                                    logger.debug(f"Downloaded audio, size: {len(audio_bytes)} bytes")
                                    try:
                                        audio_segment = AudioSegment.from_file(
                                            io.BytesIO(audio_bytes)
                                        )
                                        audio_segments.append(audio_segment)
                                        logger.info(f"Segment {i+1} decoded: {len(audio_segment)/1000:.1f}s, text_len={len(segment)}")
                                    except Exception as e:
                                        logger.error(f"Failed to decode audio: {e}")
                                        # 尝试保存到文件调试
                                        temp_file = "qwen_debug_audio.mp3"
                                        with open(temp_file, 'wb') as f:
                                            f.write(audio_bytes)
                                        logger.info(f"Saved audio to {temp_file} for debugging")
                                        return None
                                else:
                                    logger.error(f"Failed to download audio: {audio_response.status_code}")
                                    return None
                            elif audio_data:
                                # 解码base64音频数据
                                logger.debug(f"Decoding base64 audio, data size: {len(audio_data)} chars")
                                import base64
                                audio_bytes = base64.b64decode(audio_data)
                                audio_segment = AudioSegment.from_file(
                                    io.BytesIO(audio_bytes)
                                )
                                audio_segments.append(audio_segment)
                                logger.info(f"Segment {i+1} decoded: {len(audio_segment)/1000:.1f}s, text_len={len(segment)}")
                            else:
                                logger.error(f"No audio URL or data in response for segment {i+1}")
                                return None
                        else:
                            logger.error(f"Invalid response format for segment {i+1}")
                            return None
                    except (ValueError, KeyError) as e:
                        logger.error(f"Failed to parse Qwen TTS response: {e}")
                        return None
                else:
                    api_key_masked = f"{api_key[:8]}...{api_key[-4:]}(len={len(api_key)})" if api_key else "empty"
                    logger.error(
                        f"Qwen TTS API failed: status={response.status_code}\n"
                        f"  url={url}\n"
                        f"  api_key={api_key_masked}\n"
                        f"  model={model}\n"
                        f"  voice={voice_id}\n"
                        f"  response={response.text}"
                    )
                    return None
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Qwen TTS API exception for segment {i+1}: {error_msg}")
                return None
        
        # Merge audio segments and apply volume / speed adjustment
        def _adjust_speed(seg):
            """Pitch-preserving time-stretch via pydub speedup, fallback to frame-rate resampling."""
            try:
                from pydub.effects import speedup as _su
                return _su(seg, playback_speed=voice_rate)
            except Exception:
                new_fr = int(seg.frame_rate * voice_rate)
                return seg._spawn(seg.raw_data, overrides={'frame_rate': new_fr}).set_frame_rate(seg.frame_rate)

        if len(audio_segments) == 1:
            audio_segment = audio_segments[0]
            logger.info(f"Qwen TTS: 1 segment, duration={len(audio_segment)/1000:.1f}s")
            if voice_volume != 1.0:
                logger.info(f"Applying volume adjustment in Qwen TTS: {voice_volume}x")
                import math
                volume_change_db = 20 * math.log10(voice_volume)
                audio_segment = audio_segment + volume_change_db
            if voice_rate != 1.0:
                logger.info(f"Applying speed adjustment in Qwen TTS: {voice_rate}x")
                audio_segment = _adjust_speed(audio_segment)
            audio_segment.export(voice_file, format="mp3")
        else:
            durations = [f"{len(seg)/1000:.1f}s" for seg in audio_segments]
            logger.info(f"Merging {len(audio_segments)} audio segments: [{', '.join(durations)}]")
            combined = audio_segments[0]
            for i in range(1, len(audio_segments)):
                combined += audio_segments[i]
            logger.info(f"Qwen TTS: merged duration={len(combined)/1000:.1f}s")
            
            if voice_volume != 1.0:
                logger.info(f"Applying volume adjustment in Qwen TTS: {voice_volume}x")
                import math
                volume_change_db = 20 * math.log10(voice_volume)
                combined = combined + volume_change_db
            
            if voice_rate != 1.0:
                logger.info(f"Applying speed adjustment in Qwen TTS: {voice_rate}x")
                combined = _adjust_speed(combined)
            
            combined.export(voice_file, format="mp3")
        
        logger.info(f"completed, output file: {voice_file}")
        
        # Qwen TTS只负责音频生成，字幕由Whisper生成
        return None
        
    except ImportError as e:
        logger.error(f"Missing required package for Qwen TTS: {str(e)}. Please install: pip install pydub")
        return None
    except Exception as e:
        logger.error(f"Qwen TTS failed, error: {str(e)}")
        return None