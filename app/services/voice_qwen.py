"""
百炼 TTS / 阿里百炼 Token Plan 专用模块：克隆音色、语音列表、TTS 合成。
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

# 缓存字典，用于存储百炼 TTS/百炼Token Plan TTS音色信息
_voice_cache = {
    'bailian': {'voices': [], 'timestamp': None, 'api_key': None},
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

def get_bailian_voices(force_refresh=False) -> list[str]:
    """
    获取百炼 TTS的声音列表，包括克隆的声音
    
    Args:
        force_refresh: 是否强制刷新缓存
    
    Returns:
        声音列表，格式为: "bailian|voice_id|voice_name-gender|preview_audio|preview_text"
    """
    global _voice_cache
    
    # 检查缓存
    api_key = config.bailian.get("api_key", "")
    cache_entry = _voice_cache['bailian']
    
    # 检查缓存是否有效
    current_time = datetime.now().timestamp()
    if not force_refresh and cache_entry['voices'] and cache_entry['timestamp']:
        cache_age = current_time - cache_entry['timestamp']
        if cache_age < CACHE_DURATION and cache_entry['api_key'] == api_key:
            logger.info(f"Using cached Bailian voices (age: {cache_age:.1f}s)")
            return cache_entry['voices']
    
    logger.info("Loading Bailian voices from hardcoded list")
    
    # 定义中文声音列表 (Qwen-TTS 官方非实时语音列表)
    voices_with_id_gender = [
        ("Cherry", "芊悦", "Female", "阳光积极、亲切自然小姐姐"),
        ("Serena", "苏瑶", "Female", "温柔小姐姐"),
        ("Ethan", "晨煦", "Male", "标准普通话，阳光、温暖、活力、朝气"),
        ("Chelsie", "千雪", "Female", "二次元虚拟女友"),
        ("Momo", "茉兔", "Female", "撒娇搞怪，逗你开心"),
        ("Vivian", "十三", "Female", "拽拽的、可爱的小暴躁"),
        ("Moon", "月白", "Male", "率性帅气的月白"),
        ("Maia", "四月", "Female", "知性与温柔的碰撞"),
        ("Kai", "凯", "Male", "耳朵的一场SPA"),
        ("Nofish", "不吃鱼", "Male", "不会翘舌音的设计师"),
        ("Bella", "萌宝", "Female", "喝酒不打醉拳的小萝莉"),
        ("Jennifer", "詹妮弗", "Female", "品牌级、电影质感般美语女声"),
        ("Ryan", "甜茶", "Male", "节奏拉满，戏感炸裂，真实与张力共舞"),
        ("Katerina", "卡捷琳娜", "Female", "御姐音色，韵律回味十足"),
        ("Aiden", "艾登", "Male", "精通厨艺的美语大男孩"),
        ("Eldric Sage", "沧明子", "Male", "沉稳睿智的老者，沧桑如松却心明如镜"),
        ("Mia", "乖小妹", "Female", "温顺如春水，乖巧如初雪"),
        ("Mochi", "沙小弥", "Male", "聪明伶俐的小大人，童真未泯却早慧如禅"),
        ("Bellona", "燕铮莺", "Female", "声音洪亮，吐字清晰，人物鲜活"),
        ("Vincent", "田叔", "Male", "一口独特的沙哑烟嗓，尽显江湖豪情"),
        ("Bunny", "萌小姬", "Female", "萌属性爆棚的小萝莉"),
        ("Neil", "阿闻", "Male", "平直的基线语调，字正腔圆，最专业的新闻主持人"),
        ("Elias", "墨讲师", "Female", "既保持学科严谨性，又将复杂知识转化为可消化的认知模块"),
        ("Arthur", "徐大爷", "Male", "被岁月和旱烟浸泡过的质朴嗓音"),
        ("Nini", "邻家妹妹", "Female", "糯米糍一样又软又黏的嗓音"),
        ("Seren", "小婉", "Female", "温和舒缓的声线，助你更快地进入睡眠"),
        ("Pip", "顽屁小孩", "Male", "调皮捣蛋却充满童真的他来了"),
        ("Stella", "少女阿月", "Female", "平时是甜到发腻的迷糊少女音"),
        ("Bodega", "博德加", "Male", "热情的西班牙大叔"),
        ("Sonrisa", "索尼莎", "Female", "热情开朗的拉美大姐"),
        ("Alek", "阿列克", "Male", "一开口，是战斗民族的冷，也是毛呢大衣下的暖"),
        ("Dolce", "多尔切", "Male", "慵懒的意大利大叔"),
        ("Sohee", "素熙", "Female", "温柔开朗，情绪丰富的韩国欧尼"),
        ("Ono Anna", "小野杏", "Female", "鬼灵精怪的青梅竹马"),
        ("Lenn", "莱恩", "Male", "理性是底色，叛逆藏在细节里"),
        ("Emilien", "埃米尔安", "Male", "浪漫的法国大哥哥"),
        ("Andre", "安德雷", "Male", "声音磁性，自然舒服、沉稳男生"),
        ("Radio Gol", "拉迪奥·戈尔", "Male", "足球诗人，用激情解说足球"),
        ("Jada", "上海-阿珍", "Female", "风风火火的沪上阿姐"),
        ("Dylan", "北京-晓东", "Male", "北京胡同里长大的少年"),
        ("Li", "南京-老李", "Male", "耐心的瑜伽老师"),
        ("Marcus", "陕西-秦川", "Male", "面宽话短，心实声沉——老陕的味道"),
        ("Roy", "闽南-阿杰", "Male", "诙谐直爽、市井活泼的台湾哥仔形象"),
        ("Peter", "天津-李彼得", "Male", "天津相声，专业捧哏"),
        ("Sunny", "四川-晴儿", "Female", "甜到你心里的川妹子"),
        ("Eric", "四川-程川", "Male", "一个跳脱市井的四川成都男子"),
        ("Rocky", "粤语-阿强", "Male", "幽默风趣的阿强，在线陪聊"),
        ("Kiki", "粤语-阿清", "Female", "甜美的港妹闺蜜"),
    ]

    voices = []

    try:
        api_key = config.bailian.get("api_key", "")
        
        # 使用硬编码的语音列表
        logger.info("Using hardcoded Bailian voices")
        emotion_str = ",".join(f"{k}-{v[1]}" for k, v in BAILIAN_EMOTION_TAGS.items())
        for voice_id, voice_name, gender, description in voices_with_id_gender:
            voices.append(f"bailian|{voice_id}|{voice_name}-{gender}|{description}|||{emotion_str}")
        logger.info(f"Bailian loaded {len(voices)} hardcoded voices")
        
        # 加载克隆的声音 - 优先从独立配置文件加载，备用从API获取
        cloned_voices = []
        
        # 优先从独立配置文件加载克隆声音
        from app.config.cloned_voices import cloned_voices_config
        config_cloned_voices = cloned_voices_config.get_voices(provider="bailian")
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
                voices.append(f"bailian|{voice_id}|{display_name}-{gender}|{target_model}|||{emotion_str}")
            logger.info(f"Bailian loaded {len(cloned_voices)} cloned voices total: {[v[1] for v in cloned_voices]}")
        
        # 更新缓存
        _voice_cache['bailian'] = {
            'voices': voices,
            'timestamp': current_time,
            'api_key': api_key
        }
        logger.info(f"Bailian voices cached: {len(voices)} voices")
        
        return voices
    except Exception as e:
        # 发生异常，返回默认列表
        logger.error(f"Error getting Bailian voices: {str(e)}")
        emotion_str = ",".join(f"{k}-{v[1]}" for k, v in BAILIAN_EMOTION_TAGS.items())
        for voice_id, voice_name, gender, description in voices_with_id_gender:
            voices.append(f"bailian|{voice_id}|{voice_name}-{gender}|{description}|||{emotion_str}")
        logger.info(f"Bailian loaded {len(voices)} DEFAULT hardcoded voices (exception occurred): {voices}")
        
        # 即使发生异常，也更新缓存以避免重复失败
        _voice_cache['bailian'] = {
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

def is_bailian_voice(voice_name: str):
    """检查是否是百炼 TTS的声音"""
    return voice_name.startswith("bailian|")

def is_bailian_token_plan_voice(voice_name: str):
    """检查是否是阿里百炼Token Plan TTS的声音"""
    return voice_name.startswith("BailianTokenPlan|")

def build_bailian_instructions(voice_rate: float, voice_volume: float, emotion: str = "") -> str:
    """
    构建百炼TTS的指令控制字符串
    
    Args:
        voice_rate: 语音速率 (0.5-2.0)
        voice_volume: 音频音量 (0.1-2.0)
        emotion: 语音情感
    
    Returns:
        指令字符串
    """
    instructions_parts = []
    
    # 语速控制
    if voice_rate < 0.8:
        instructions_parts.append("语速稍慢")
    elif voice_rate > 1.2:
        instructions_parts.append("语速稍快")
    else:
        instructions_parts.append("语速正常")
    
    # 音量控制
    if voice_volume < 0.8:
        instructions_parts.append("音量稍小")
    elif voice_volume > 1.2:
        instructions_parts.append("音量稍大")
    else:
        instructions_parts.append("音量正常")
    
    # 情感控制
    if emotion:
        # emotion格式: "excited-兴奋"，取key部分
        emotion_key = emotion.split('-')[0] if '-' in emotion else emotion
        if emotion_key in BAILIAN_EMOTION_TAGS:
            instructions_parts.append(BAILIAN_EMOTION_TAGS[emotion_key][0])
    
    # 合并 instructions
    if instructions_parts:
        return "，".join(instructions_parts) + "。"
    return ""

def bailian_tts(
    text: str,
    voice_id: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.0,
    preview_audio: str = "",
    preview_text: str = "",
    is_preview: bool = False,
    target_model: str = "",
    provider: str = "bailian",
    emotion: str = "",
) -> Union[SubMaker, None]:
    """
    使用百炼 TTS生成语音（provider支持"bailian"和"bailian_token_plan"）

    Args:
        text: 要转换的文本
        voice_id: 语音ID，如 "7426720361732915209", "7426720361732915210" 等
        voice_rate: 语音速率
        voice_file: 输出音频文件路径
        voice_volume: 音频音量
        preview_audio: 预览音频URL（用于试听）
        preview_text: 预览文本（用于匹配试听）
        provider: 供应商，可选"bailian"或"bailian_token_plan"
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
        
        # 配置百炼 API (使用HTTP API)，支持bailian和bailian_token_plan两种provider
        if provider == "bailian_token_plan":
            api_key = config.bailian_token_plan.get("api_key", "")
            # Token Plan TTS 使用固定的 DashScope 原生端点
            endpoint = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
        else:
            api_key = config.bailian.get("api_key", "")
            base_url = "https://dashscope.aliyuncs.com/api/v1"  # 硬编码百炼 API端点
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
                    default_model = config.bailian.get("model_name", "qwen3-tts-instruct-flash")
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
                
                # 构建指令控制字符串（语速、音量、情感）
                instructions = build_bailian_instructions(voice_rate, voice_volume, emotion)
                if instructions:
                    payload["instructions"] = instructions
                    payload["optimize_instructions"] = True
                
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