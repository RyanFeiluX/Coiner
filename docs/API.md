# Coiner 后端 API 文档

## 概述

Coiner 提供了一套完整的 RESTful API 接口，用于视频生成、配置管理、任务管理等功能。

**基础 URL**: `http://localhost:8000`

**API 前缀**: `/api/v1`

---

## 目录

- [健康检查](#健康检查)
- [任务管理](#任务管理)
- [场景集成](#场景集成--扫描)
- [视频分割](#视频分割--扫描)
- [脚本生成](#脚本生成)
- [配置管理](#配置管理)
- [语音服务](#语音服务)
- [日志服务](#日志服务)
- [资源管理](#资源管理)

---

## 健康检查

### 1. Ping

检查服务可用性。

**端点**: `GET /api/ping`

**标签**: Health Check

**响应示例**:
```json
"pong"
```

### 2. 获取版本信息

获取服务的名称和版本信息。

**端点**: `GET /api/version`

**标签**: Health Check

**响应示例**:
```json
{
  "name": "Coiner",
  "version": "1.2.59",
  "code": 0,
  "message": "success"
}
```

---

## 任务管理

### 1. 生成视频

创建一个新的视频生成任务。

**端点**: `POST /api/v1/videos`

**摘要**: Generate a short video

**请求体** (`TaskVideoRequest`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_subject | string | 否 | 视频主题 |
| video_script | string | 否 | 视频脚本 |
| video_terms | string \| array | 否 | 视频关键词 |
| video_aspect | string | 否 | 视频比例 (16:9, 9:16, 1:1, 3:4) |
| video_concat_mode | string | 否 | 视频拼接模式 (random, sequential) |
| video_transition_mode | string | 否 | 过渡模式 (None, Shuffle, FadeIn, FadeOut, SlideIn, SlideOut) |
| video_clip_duration | integer | 否 | 视频剪辑时长（秒） |
| video_count | integer | 否 | 视频数量 |
| video_source | string | 否 | 视频来源 (pexels, pixabay, local) |
| video_style | string | 否 | 视频风格 |
| voice_name | string | 否 | 语音名称 |
| voice_volume | float | 否 | 语音音量 (0.1-2.0) |
| voice_rate | float | 否 | 语音语速 (0.5-2.0) |
| voice_emotion | string | 否 | 语音情感 |
| tts_server | string | 否 | TTS 服务器 (azure-tts-v1, azure-tts-v2, siliconflow, gemini-tts, coze-tts) |
| bgm_type | string | 否 | BGM 类型 (random) |
| bgm_file | string | 否 | BGM 文件路径 |
| bgm_volume | float | 否 | BGM 音量 (0.1-2.0) |
| subtitle_enabled | boolean | 否 | 是否启用字幕 |
| subtitle_position | string | 否 | 字幕位置 (top, bottom, center) |
| font_name | string | 否 | 字体名称 |
| text_fore_color | string | 否 | 字幕前景色 (#FFFFFF) |
| text_background_color | boolean \| string | 否 | 字幕背景色 |
| font_size | integer | 否 | 字体大小 |
| stroke_color | string | 否 | 描边颜色 |
| stroke_width | float | 否 | 描边宽度 |
| scenes | array | 否 | 多场景数据 |
| language | string | 否 | 语言 (zh, en) |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "task_id": "6c85c8cc-a77a-42b9-bc30-947815aa0558"
  }
}
```

### 2. 仅生成字幕

创建一个仅生成字幕的任务。

**端点**: `POST /api/v1/subtitle`

**摘要**: Generate subtitle only

**请求体** (`SubtitleRequest`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_script | string | 是 | 视频脚本 |
| video_language | string | 否 | 视频语言 |
| voice_name | string | 否 | 语音名称 |
| voice_volume | float | 否 | 语音音量 |
| voice_rate | float | 否 | 语音语速 |
| bgm_type | string | 否 | BGM 类型 |
| bgm_file | string | 否 | BGM 文件路径 |
| bgm_volume | float | 否 | BGM 音量 |
| subtitle_position | string | 否 | 字幕位置 |
| font_name | string | 否 | 字体名称 |
| text_fore_color | string | 否 | 字幕前景色 |
| text_background_color | boolean \| string | 否 | 字幕背景色 |
| font_size | integer | 否 | 字体大小 |
| stroke_color | string | 否 | 描边颜色 |
| stroke_width | float | 否 | 描边宽度 |
| video_source | string | 否 | 视频来源 |
| subtitle_enabled | string | 否 | 是否启用字幕 |

### 3. 仅生成音频

创建一个仅生成音频的任务。

**端点**: `POST /api/v1/audio`

**摘要**: Generate audio only

**请求体** (`AudioRequest`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_script | string | 是 | 视频脚本 |
| video_language | string | 否 | 视频语言 |
| voice_name | string | 否 | 语音名称 |
| voice_volume | float | 否 | 语音音量 |
| voice_rate | float | 否 | 语音语速 |
| bgm_type | string | 否 | BGM 类型 |
| bgm_file | string | 否 | BGM 文件路径 |
| bgm_volume | float | 否 | BGM 音量 |
| video_source | string | 否 | 视频来源 |

### 4. 获取所有任务

分页获取所有任务列表。

**端点**: `GET /api/v1/tasks`

**摘要**: Get all tasks

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 10 | 每页数量 |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "tasks": [
      {
        "task_id": "6c85c8cc-a77a-42b9-bc30-947815aa0558",
        "status": "completed",
        "progress": 100,
        "videos": ["http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/final-1.mp4"]
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

### 5. 获取单个任务状态

根据任务 ID 查询任务状态和详细信息。

**端点**: `GET /api/v1/tasks/{task_id}`

**摘要**: Query task status

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "task_id": "6c85c8cc-a77a-42b9-bc30-947815aa0558",
    "status": "completed",
    "progress": 100,
    "videos": [
      "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/final-1.mp4"
    ],
    "combined_videos": [
      "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/combined-1.mp4"
    ]
  }
}
```

### 6. 删除任务

删除指定的任务及其相关文件。

**端点**: `DELETE /api/v1/tasks/{task_id}`

**摘要**: Delete a generated short video task

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": null
}
```

### 7. 取消任务

取消正在运行的任务。

**端点**: `POST /api/v1/tasks/{task_id}/cancel`

**摘要**: Cancel a running task

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": null
}
```

---

## 脚本生成

### 1. 生成视频脚本

根据主题生成视频脚本。

**端点**: `POST /api/v1/scripts`

**摘要**: Create a script for the video

**请求体** (`VideoScriptRequest`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_subject | string | 是 | 视频主题 |
| video_language | string | 否 | 视频语言 |
| paragraph_number | integer | 否 | 段落数量 |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "video_script": "春天的花海，是大自然的一幅美丽画卷..."
  }
}
```

### 2. 生成视频关键词

根据脚本生成视频搜索关键词。

**端点**: `POST /api/v1/terms`

**摘要**: Generate video terms based on the video script

**请求体** (`VideoTermsRequest`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_subject | string | 否 | 视频主题 |
| video_script | string | 否 | 视频脚本 |
| amount | integer | 否 | 关键词数量 |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "video_terms": ["sky", "tree", "flower"]
  }
}
```

### 3. 解析脚本为场景

将视频脚本解析为多场景格式。

**端点**: `POST /api/v1/parse-script`

**摘要**: Parse video script into scenes

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_script | string | 是 | 视频脚本 |
| language | string | 否 | 语言 |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "status": "success",
    "scenes": [
      {
        "id": "scene_1",
        "script": "春天的花海...",
        "camera": "",
        "start_time": 0.0,
        "end_time": 5.0,
        "title": "场景1",
        "keywords": ["flower", "spring"],
        "video_clips": null,
        "audio_file": null,
        "subtitle_file": null
      }
    ],
    "evaluation": {}
  }
}
```

---

## 配置管理

### 1. 获取配置

获取当前的配置信息。

**端点**: `GET /api/v1/config`

**摘要**: Get configuration

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "ui": {
      "hide_log": false,
      "language": "zh"
    },
    "app": {
      "llm_provider": "deepseek",
      "subtitle_provider": "edge",
      "video_source": "pexels",
      "use_gpu": true,
      "pexels_api_keys": ["Ra5z3Yw0ZUwPy..."],
      "pixabay_api_keys": ["54923197-..."],
      "openai_api_key": "",
      "openai_base_url": "",
      "openai_model_name": "gpt-3.5-turbo",
      "moonshot_api_key": "sk-5ZAQbXRl...",
      "moonshot_base_url": "https://api.moonshot.cn/v1",
      "moonshot_model_name": "moonshot-v1-128k",
      "deepseek_api_key": "sk-0b0650da992d...",
      "deepseek_base_url": "https://api.deepseek.com",
      "deepseek_model_name": "deepseek-chat"
    },
    "azure": {
      "speech_region": "",
      "speech_key": ""
    },
    "siliconflow": {
      "api_key": "sk-ehmjzsdq..."
    },
    "coze": {
      "api_key": "sat_5QQV8lPJC..."
    },
    "whisper": {
      "device": "GPU"
    }
  }
}
```

### 2. 更新配置

更新配置信息。

**端点**: `PUT /api/v1/config`

**摘要**: Update configuration

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app | object | 否 | 应用配置 (llm_provider, subtitle_provider, video_source 等) |
| ui | object | 否 | UI 配置 |
| azure | object | 否 | Azure TTS 配置 |
| siliconflow | object | 否 | SiliconFlow 配置 |
| coze | object | 否 | Coze 配置 |
| whisper | object | 否 | Whisper 配置 (device) |

**请求示例**:
```json
{
  "ui": {
    "language": "zh",
    "hide_log": false
  },
  "azure": {
    "speech_region": "eastasia",
    "speech_key": "your-api-key"
  }
}
```

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "message": "Config saved successfully"
  }
}
```

---

## 语音服务

### 1. 获取语音列表

获取可用语音列表。

**端点**: `GET /api/v1/voices`

**摘要**: Get voice list based on TTS server

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tts_server | string | 否 | azure-tts-v1 | TTS 服务器类型 |
| force_refresh | boolean | 否 | false | 是否强制刷新缓存 |

**TTS 服务器类型**:
- `azure-tts-v1`: Azure TTS v1
- `azure-tts-v2`: Azure TTS v2
- `siliconflow`: SiliconFlow TTS
- `gemini-tts`: Google Gemini TTS
- `coze-tts`: Coze TTS

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "voices": [
      "zh-CN-XiaoxiaoNeural",
      "zh-CN-YunxiNeural",
      "en-US-JennyNeural"
    ]
  }
}
```

### 2. 预览语音

生成并返回语音预览。

**端点**: `POST /api/v1/audio/preview`

**摘要**: Preview audio (play voice)

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要合成的文本 |
| voice_name | string | 是 | 语音标识符 |
| voice_rate | float | 否 | 语音速度 (0.5-2.0) |
| voice_volume | float | 否 | 语音音量 (0.1-2.0) |
| voice_emotion | string | 否 | 语音情感（用于 Coze TTS） |

**响应**: 音频文件 (audio/mp3)

---

## 日志服务

### 1. 获取日志

获取任务日志。

**端点**: `GET /api/v1/logs`

**摘要**: Get logs

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| level | string | 否 | null | 日志级别过滤 (INFO, WARNING, ERROR) |
| task_id | string | 否 | null | 任务 ID 过滤 |
| limit | integer | 否 | 100 | 返回日志数量 |
| offset | integer | 否 | 0 | 分页偏移量 |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "logs": [
      {
        "timestamp": "2024-01-15 10:30:00",
        "level": "INFO",
        "message": "Task started",
        "task_id": "6c85c8cc-a77a-42b9-bc30-947815aa0558"
      }
    ],
    "total": 1
  }
}
```

### 2. 清除日志

清除所有日志。

**端点**: `DELETE /api/v1/logs`

**摘要**: Clear logs

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "message": "Logs cleared successfully"
  }
}
```

---

## 资源管理

### 1. 获取 BGM 列表

获取本地 BGM 文件列表。

**端点**: `GET /api/v1/musics`

**摘要**: Retrieve local BGM files

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "files": [
      {
        "name": "output013.mp3",
        "size": 1891269,
        "file": "/Coiner/resource/songs/output013.mp3"
      }
    ]
  }
}
```

### 2. 上传 BGM 文件

上传 BGM 文件到 songs 目录。

**端点**: `POST /api/v1/musics`

**摘要**: Upload the BGM file to the songs directory

**请求体**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | MP3 文件 |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "file": "/Coiner/resource/songs/example.mp3"
  }
}
```

### 3. 获取视频素材列表

获取本地视频素材列表。

**端点**: `GET /api/v1/video_materials`

**摘要**: Retrieve local video materials

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "files": [
      {
        "name": "example.mp4",
        "size": 12345678,
        "file": "/Coiner/resource/videos/example.mp4"
      }
    ]
  }
}
```

### 4. 上传视频素材

上传视频素材到本地视频目录。

**端点**: `POST /api/v1/video_materials`

**摘要**: Upload the video material file to the local videos directory

**请求体**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 视频文件 (mp4, mov, avi, flv, mkv, jpg, jpeg, png) |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "file": "/Coiner/resource/videos/example.mp4"
  }
}
```

### 5. 流式播放视频

流式播放视频文件（支持断点续传）。

**端点**: `GET /api/v1/stream/{file_path}`

**摘要**: Stream video with range support

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_path | string | 是 | 文件路径 |

**响应**: 视频文件流 (video/mp4)

### 7. 场景集成 — 扫描

扫描任务目录，检测场景文件完整性，用于后续的场景合成恢复。

**端点**: `POST /api/v1/scene-integration/scan`

**摘要**: Scan task directory for scene integration

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 否 | 任务 ID（与 task_path 二选一） |
| task_path | string | 否 | 任务目录路径（与 task_id 二选一） |

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "sceneVideos": 5,
    "sceneAudio": 5,
    "subtitle": true,
    "totalScenes": 5,
    "isValid": true,
    "taskDir": "/Coiner/storage/tasks/abc123",
    "sceneNums": [1, 2, 3, 4, 5],
    "scenes": [
      {"sceneNum": 1, "video": true, "audio": true, "subtitle": true},
      {"sceneNum": 2, "video": true, "audio": true, "subtitle": false},
      {"sceneNum": 3, "video": true, "audio": true, "subtitle": true},
      {"sceneNum": 4, "video": true, "audio": true, "subtitle": true},
      {"sceneNum": 5, "video": true, "audio": true, "subtitle": true}
    ]
  }
}
```

**新增字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| sceneNums | int[] | 所有场景编号数组 |
| scenes | object[] | 每个场景的详细信息 |
| scenes[].sceneNum | int | 场景编号 |
| scenes[].video | bool | 场景视频文件是否存在 |
| scenes[].audio | bool | 场景音频文件是否存在 |
| scenes[].subtitle | bool | 场景字幕文件是否存在 |
| scenesData | object[] | 每个场景的完整数据（来自 script.json），用于前端编辑后提交强制重建 |
| scenesData[].sceneNum | int | 场景编号 |
| scenesData[].sceneData | object | 场景参数字典（script, audio, intro_video, intro_duration, intro_video_cover_full 等） |
| scenesData[].searchTerms | string[] | 场景搜索关键词列表 |

### 8. 场景集成 — 更新场景数据

在强制重建前，将最新逐场景数据写入目标任务的 `script.json`。

**端点**: `POST /api/v1/scene-integration/update-scenes`

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |
| scene_updates | object[] | 是 | 场景更新列表 |
| scene_updates[].scene_num | integer | 是 | 场景编号（1-based） |
| scene_updates[].scene_data | object | 是 | 场景数据字典，**整体覆盖** `params.scenes[i]` |
| scene_updates[].search_terms | string[] | 否 | 搜索关键词列表，**整体覆盖** `search_terms[i]` |

**响应示例**:
```json
{
  "status": 200,
  "data": { "updated": 3 }
}
```

### 9. 场景集成 — 恢复合成

从已有场景文件恢复视频合成，支持选择性合并场景范围，并覆盖字幕/BGM/标题参数。

**端点**: `POST /api/v1/scene-integration/recover`

**摘要**: Recover video synthesis from existing scene files

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 否 | 任务 ID（与 task_path 二选一） |
| task_path | string | 否 | 任务目录路径（与 task_id 二选一） |
| start_scene | integer | 否 | 起始场景编号，默认 1 |
| end_scene | integer | 否 | 结束场景编号，默认最后一个场景 |
| force_rebuild_scenes | int[] | 否 | 强制重建场景列表（用当前 UI 参数重新生成音频、素材、字幕后再合并） |
| voice_name | string | 否 | 强制重建时使用的语音名称 |
| voice_rate | float | 否 | 强制重建时使用的语速 |
| voice_volume | float | 否 | 强制重建时使用的音量 |
| voice_emotion | string | 否 | 强制重建时使用的语音情感 |
| video_source | string | 否 | 强制重建时使用的视频素材来源 (pexels, pixabay) |
| video_aspect | string | 否 | 强制重建时使用的视频比例 (9:16, 16:9, 1:1, 3:4, 4:3) |
| video_concat_mode | string | 否 | 强制重建时使用的拼接模式 (random, sequential) |
| video_clip_duration | integer | 否 | 强制重建时使用的片段最大时长（秒） |
**字幕参数（场景级，优先使用原始 script.json 中的值）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subtitle_enabled | boolean | 否 | 是否启用字幕 |
| font_name | string | 否 | 字体名称 |
| font_size | integer | 否 | 字体大小 |
| text_fore_color | string | 否 | 字幕前景色 |
| text_background_color | string | 否 | 字幕背景色 |
| stroke_color | string | 否 | 描边颜色 |
| stroke_width | float | 否 | 描边宽度 |
| subtitle_position | string | 否 | 字幕位置 (top, bottom, center, custom) |
| custom_position | float | 否 | 自定义位置百分比 (0-100) |

**BGM 参数（合成级，来自当前设置）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bgm_type | string | 否 | BGM 类型 (random, none, 或文件名) |
| bgm_file | string | 否 | BGM 文件路径 |
| bgm_volume | float | 否 | BGM 音量 |

**标题参数（合成级，来自当前设置）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title_enabled | boolean | 否 | 是否启用标题 |
| title_text | string | 否 | 标题文字 |
| title_duration | float | 否 | 标题持续时间（秒） |
| title_font_name | string | 否 | 标题字体 |
| title_font_size | integer | 否 | 标题字号 |
| title_text_color | string | 否 | 标题文字颜色 |
| title_stroke_color | string | 否 | 标题描边颜色 |
| title_stroke_width | float | 否 | 标题描边宽度 |
| title_background_color | string | 否 | 标题背景色 |
| title_position | string | 否 | 标题位置 (center, top, bottom) |
| title_margin | float | 否 | 标题边距 |
| title_margin_left | float | 否 | 标题左边距 |
| title_margin_right | float | 否 | 标题右边距 |
| title_animation | string | 否 | 标题动画 (none, fade, slide, zoom) |
| title_animation_duration | float | 否 | 标题动画持续时间 |
| title_background_overlay | boolean | 否 | 是否启用背景叠加 |
| title_overlay_color | string | 否 | 背景叠加颜色 |
| title_align | string | 否 | 标题对齐方式 (center, left, right) |

**参数优先级说明**：

- **常规恢复**：字幕参数优先使用 `script.json` 中的原始值（保证恢复场景与原场景一致），BGM 和标题参数仅使用请求体传入值（给予用户调整自由度），最终兜底为 `config.toml` 配置。
- **强制重建**：使用前先调用 `POST /scene-integration/update-scenes` 接口将最新逐场景数据写入 `script.json`。重建时系统将请求体中的 `voice_name/voice_rate/video_source/video_aspect` 等顶层参数更新到 `script.json` 的顶层 params，然后复用原 `process_scene` 流水线重新处理该场景（音频合成 → 字幕生成 → 素材下载 → 视频合成，含 intro video 处理）。任一子步骤失败则整个场景重建失败（不中断其他场景的处理）。

**响应示例**:
```json
{
  "status": 200,
  "message": "success",
  "data": {
    "task_id": "6c85c8cc-a77a-42b9-bc30-947815aa0558"
  }
}
```

任务创建后，通过 `GET /api/v1/tasks/{task_id}` 轮询进度。

### 10. 视频分割 — 扫描

扫描任务目录，返回场景信息和自动分段建议。

**端点**: `POST /api/v1/video-split/scan`

**摘要**: Scan task for video splitting

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 源任务 ID 或目录路径 |
| min_duration | float | 否 | 最小分段时长（秒），默认 30 |
| max_duration | float | 否 | 最大分段时长（秒），默认 90 |

**响应示例**:
```json
{
  "status": 200,
  "data": {
    "task_id": "xxx",
    "scenes": [
      { "scene_num": 1, "duration": 15.2, "script_preview": "今天我们来聊聊..." },
      { "scene_num": 2, "duration": 20.1, "script_preview": "首先，什么是..." }
    ],
    "total_duration": 180.5,
    "suggested_segments": [
      { "scene_nums": [1, 2, 3], "duration": 45.3, "script_preview": "..." },
      { "scene_nums": [4, 5], "duration": 52.1, "script_preview": "..." }
    ]
  }
}
```

### 11. 视频分割 — 规划分段

根据场景列表和时长约束规划分段方案。

**端点**: `POST /api/v1/video-split/plan`

**摘要**: Plan segments from scenes

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scenes | array | 是 | 场景列表，每个包含 scene_num 和 duration |
| min_duration | float | 否 | 最小分段时长（秒），默认 30 |
| max_duration | float | 否 | 最大分段时长（秒），默认 90 |

**响应示例**:
```json
{
  "status": 200,
  "data": {
    "segments": [
      { "scene_nums": [1, 2, 3], "duration": 45.3 },
      { "scene_nums": [4, 5], "duration": 52.1 }
    ],
    "total_segments": 2
  }
}
```

### 12. 视频分割 — 执行

执行视频分割，将源任务的场景视频拆分为多个短视频。

**端点**: `POST /api/v1/video-split/execute`

**摘要**: Execute video split

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 源任务 ID 或目录路径 |
| segments | array | 是 | 分段方案，每项包含 scene_nums 列表 |
| min_duration | float | 否 | 最小时长（秒） |
| max_duration | float | 否 | 最大时长（秒） |
| subtitle_* | - | 否 | 字幕参数（同场景集成） |
| bgm_* | - | 否 | BGM 参数（同场景集成） |
| title_* | - | 否 | 标题参数（同场景集成） |

**响应示例**:
```json
{
  "status": 200,
  "data": {
    "task_id": "new-uuid-for-split-task",
    "task_type": "video_split",
    "original_task_id": "source-task-id"
  }
}
```

任务创建后，通过 `GET /api/v1/tasks/{task_id}` 轮询进度。完成后，`videos` 字段包含所有短视频的路径。

### 13. 下载视频

下载视频文件。

**端点**: `GET /api/v1/download/{file_path}`

**摘要**: Download video

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_path | string | 是 | 文件路径，例如: /cd1727ed-3473-42a2-a7da-4faafafec72b/final-1.mp4 |

**响应**: 视频文件下载

---

## 通用响应格式

所有 API 响应都遵循以下格式：

```json
{
  "status": 200,
  "message": "success",
  "data": { ... }
}
```

**状态码说明**:

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 错误处理

当发生错误时，响应格式如下：

```json
{
  "status": 400,
  "message": "Error message description",
  "data": null
}
```

---

## CORS 跨域支持

API 支持 CORS 跨域请求，可以通过环境变量 `CORS_ALLOWED_ORIGINS` 配置允许的源，默认允许所有源。

---

## 认证

当前 API 未启用认证（代码中已注释掉认证依赖项）。如需启用，请修改 `app/controllers/v1/video.py` 中的 router 配置。

---

## 附录

### 视频比例枚举

| 值 | 说明 |
|----|------|
| 16:9 | 横屏（西瓜视频） |
| 9:16 | 竖屏（抖音） |
| 1:1 | 方形（Instagram） |
| 3:4 | 竖屏（小红书） |

### 视频拼接模式

| 值 | 说明 |
|----|------|
| random | 随机拼接 |
| sequential | 顺序拼接 |

### 过渡模式

| 值 | 说明 |
|----|------|
| None | 无过渡 |
| Shuffle | 随机打乱 |
| FadeIn | 淡入 |
| FadeOut | 淡出 |
| SlideIn | 滑入 |
| SlideOut | 滑出 |

### 任务状态

| 值 | 说明 |
|----|------|
| pending | 等待中 |
| running | 运行中 |
| completed | 已完成 |
| failed | 失败 |
| cancelled | 已取消 |

### TTS 服务器类型

| 值 | 说明 |
|----|------|
| azure-tts-v1 | Azure TTS v1 |
| azure-tts-v2 | Azure TTS v2 |
| siliconflow | SiliconFlow TTS |
| gemini-tts | Google Gemini TTS |
| coze-tts | Coze TTS |

### LLM 提供商

| 值 | 说明 |
|----|------|
| openai | OpenAI |
| moonshot | 月之暗面 |
| azure | Azure OpenAI |
| qwen | 通义千问 |
| deepseek | DeepSeek |
| gemini | Google Gemini |
| ollama | Ollama |
| g4f | GPT4Free |
| oneapi | OneAPI |
| cloudflare | Cloudflare Workers AI |
| ernie | 百度文心一言 |
| modelscope | 魔搭社区 |
| pollinations | Pollinations AI |
