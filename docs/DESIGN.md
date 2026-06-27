# 多场景视频处理系统设计规范

## 1. 系统概述

多场景视频处理系统是一个用于处理和生成多场景视频的综合性系统，支持从单个场景视频到完整视频的生成过程。系统通过一系列模块化的函数，实现了视频处理、音频合成、字幕添加等功能，最终生成高质量的视频内容。

## 2. 关键函数职责

### 2.1 场景内部处理函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `process_scene_videos` | 处理单个场景内的视频片段，应用连接模式和过渡效果 | scene_video_paths, video_aspect, video_concat_mode, video_transition_mode, max_clip_duration, local_video_paths | 处理后的视频片段列表 |
| `combine_scene_clips` | 合并单个场景的视频片段，处理时长匹配 | scene_clips, audio_duration | 处理后的视频片段列表 |

### 2.2 字幕处理函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `burn_subtitles_to_scene_video` | 将字幕烧录到单个场景视频中 | scene_video_path, subtitle_file, output_path, params | 布尔值（是否成功） |

### 2.3 静默前缀函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `create_silence_prefix_video` | 创建静默前缀视频（参数与场景一致） | task_id, params, duration, first_scene_video_path, sample_rate, channels | 静默前缀视频路径 |
| `analyze_audio_params` | 分析视频文件的音频参数（ffprobe） | video_path | dict（sample_rate, channels, codec） |

### 2.4 多场景处理函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `concat_videos_stream_copy` | FFmpeg stream-copy 快速合并（零重编码） | video_paths, output_path | 布尔值（是否成功） |
| `combine_early_scenes` | 合并多个场景的视频，保持场景顺序 | scene_clips_list, audio_duration | 合并后的视频片段列表 |
| `combine_all_scenes` | 目标视频级别的视频合并，协调整个多场景视频的生成 | task_id, params, scene_results | 最终视频文件路径 |

### 2.5 最终合成函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `finalize_video` | 处理最终合成，添加音频和字幕 | processed_clips, combined_video_path, audio_file, threads | 最终视频文件路径 |
| `process_final_video` | 最终视频处理（pillarbox/标题/BGM/响度归一化） | video_path, output_file, params, skip_subtitles, subtitle_file | 最终视频文件路径 |
| `_ffmpeg_fast_encode` | FFmpeg 快速编码（filter_complex 流水线） | video_path, bgm_file, subtitle_file, output_file, params | 最终视频文件路径 |
| `generate_video` | 视频生成任务的高级协调函数，协调整个视频生成过程 | video_path, audio_path, subtitle_path, output_file, params, progress_callback | 最终视频文件路径 |

### 2.6 场景级入口函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `build_scene_video` | 场景级别的视频处理入口，协调单个场景的视频生成 | combined_video_path, video_paths, audio_file, video_aspect, video_concat_mode, video_transition_mode, max_clip_duration, threads, scene_info, local_video_paths, intro_video_path | 场景视频文件路径 |

### 2.7 场景集成入口函数

| 函数名 | 职责 | 输入参数 | 输出结果 |
|--------|------|----------|----------|
| `recover_video_synthesis` | 场景集成任务主函数，协调整个场景合成流程 | task_id, params, start_scene, end_scene | 最终视频文件路径 |

## 3. 函数调用关系

> **Note**: Task types (e.g., 视频生成任务, 场景集成任务) refer to how tasks are initiated, while task levels (e.g., 场景级任务, 目标视频级任务) refer to the scope of the task. These are distinct classifications and both terminologies are valid.

### 3.1 场景级视频生成流程

```
generate_video (场景级任务)
    ↓
build_scene_video
    ↓
process_scene_videos
    ↓
combine_scene_clips
    ↓
finalize_video
    ↓
场景视频文件
```

### 3.2 目标视频级生成流程

```
generate_video (目标视频级任务)
    ↓
combine_all_scenes
    ↓
concat_videos_stream_copy (快速路径) / combine_early_scenes (fallback)
    ↓
process_final_video
    ↓
完整视频文件
```

### 3.3 场景集成任务流程

```
recover_video_synthesis (场景集成任务)
    ↓
analyze_audio_params → 获取第一个场景音频参数
    ↓
create_silence_prefix_video → 创建静默前缀视频
    ↓
【循环每个场景】burn_subtitles_to_scene_video → 字幕预烧录
    ↓
combine_all_scenes → 合并所有场景（stream-copy 优先）
    ↓
process_final_video (skip_subtitles=True) → 最终处理
    ↓
最终视频文件 (scenes_X_to_Y.mp4)
```

### 3.4 详细调用关系

1. **场景内部处理**：
   - `process_scene_videos` 处理单个场景的视频片段，应用连接模式和过渡效果
   - 返回处理后的视频片段列表给 `combine_scene_clips`

2. **场景级别处理**：
   - `combine_scene_clips` 接收 `process_scene_videos` 的输出
   - 处理视频时长与音频时长的匹配
   - 返回处理后的视频片段列表给 `finalize_video`

3. **多场景级别处理**：
   - `combine_early_scenes` 接收多个场景的视频片段列表
   - 按场景顺序合并视频片段
   - 返回合并后的视频片段列表给 `finalize_video`

4. **最终合成**：
   - `finalize_video` 接收 `combine_scene_clips` 或 `combine_early_scenes` 的输出
   - 添加音频和字幕
   - 生成最终视频文件

5. **入口函数**：
   - `build_scene_video` 作为场景级别的入口，调用 `process_scene_videos` → `combine_scene_clips` → `finalize_video`
   - `combine_all_scenes` 作为多场景级别的入口，调用 `combine_early_scenes` → `finalize_video`
   - `generate_video` 作为任务级别的入口，协调整个视频生成过程，根据任务类型调用相应的函数

## 4. 系统流程图

```
┌─────────────────┐     ┌────────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ process_scene_  │     │ combine_scene_     │     │ finalize_       │     │ 场景视频文件     │
│ videos         │────>│ clips             │────>│ video          │────>│                 │
└─────────────────┘     └────────────────────┘     └─────────────────┘     └─────────────────┘
          ↑                      ↑
          │                      │
┌─────────────────┐              │
│ build_scene_    │──────────────┘
│ video          │
└─────────────────┘
          ↑
          │
┌─────────────────┐
│ generate_video  │
│ (场景级任务)    │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 多个场景视频     │     │ combine_early_  │     │ finalize_       │     │ 完整视频文件     │
│ 文件            │────>│ scenes         │────>│ video          │────>│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
          ↑                      ↑
          │                      │
┌─────────────────┐              │
│ combine_all_    │──────────────┘
│ scenes         │
└─────────────────┘
          ↑
          │
┌─────────────────┐
│ generate_video  │
│ (目标视频级任务) │
└─────────────────┘
```

## 5. 数据结构

### 5.1 视频参数结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `video_subject` | str | 视频主题 |
| `video_aspect` | VideoAspect | 视频 aspect ratio |
| `video_concat_mode` | VideoConcatMode | 视频连接模式 |
| `subtitle_enabled` | bool | 是否启用字幕 |
| `font_name` | str | 字体名称 |
| `font_size` | int | 字体大小 |
| `text_fore_color` | str | 文本前景色 |
| `text_background_color` | str | 文本背景色 |
| `stroke_color` | str | 描边颜色 |
| `stroke_width` | int | 描边宽度 |
| `subtitle_position` | str | 字幕位置 |

### 5.2 场景结果结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `scene_id` | str | 场景 ID |
| `scene_index` | int | 场景索引 |
| `audio_file` | str | 音频文件路径 |
| `audio_duration` | float | 音频时长 |
| `subtitle_path` | str | 字幕文件路径 |
| `combined_video_path` | str | 合并后的视频文件路径 |

## 6. 实现细节

### 6.1 视频处理流程

1. **视频片段处理**：
   - 对每个视频片段应用缩放、裁剪等处理
   - 根据需要应用过渡效果
   - 处理视频时长，确保与音频时长匹配

2. **音频处理**：
   - 加载音频文件
   - 调整音频时长以匹配视频时长
   - 将音频添加到视频中

3. **字幕处理**（场景级预烧录）：
   - 解析字幕文件（SRT → ASS）
   - 烧录字幕到每个场景视频中（硬字幕）
   - 音频 stream-copy，不重新编码
   - 视频编码参数与原始场景一致，确保 stream-copy 合并安全

4. **静默前缀处理**：
   - 从第一个场景的第一帧提取画面（确保无字幕）
   - 使用 ffprobe 分析场景视频音频参数
   - 使用相同参数创建静默前缀（帧率、采样率、声道数）
   - 使用微弱粉红噪声替代纯静默（防止 AAC 极端压缩导致播放器时序异常）

5. **场景合并**：
   - 优先使用 FFmpeg stream-copy（快速路径，零重编码）
   - 构建 concat list 文件，执行 `-f concat -c copy`
   - 失败时自动回退到 MoviePy 重编码（慢路径）

6. **最终合成**：
   - Pillarbox（3:4 → 9:16）
   - 标题叠加
   - BGM 混合
   - 响度归一化（EBU R128, -16 LUFS）
   - 最终编码输出

### 6.2 字幕同步策略

**原策略（已废弃）**：
- 合并所有场景后在最终视频上统一添加字幕
- 需要计算复杂的时间偏移
- 容易出现音字幕不同步问题

**当前策略（场景预烧录）**：
- 字幕预先烧录到每个场景视频中
- 音频与字幕在同一场景内生成，时间轴完全一致
- 合并时只需简单的视频拼接，字幕自然跟随
- 彻底解决同步问题

### 6.3 静默前缀设计

**关键原则**：
1. **顺序正确**：静默前缀必须在字幕预烧录之前创建，确保静默部分无字幕
2. **参数一致**：所有参数与场景视频一致，确保 FFmpeg stream-copy 成功
3. **音频正常**：使用微弱粉红噪声替代纯静默，确保播放器时序正常

**参数一致性要求**：
- 视频：帧率、分辨率、编码格式、像素格式
- 音频：采样率、声道数、编码格式

### 6.4 错误处理

- 对视频文件加载失败的情况进行处理
- 对音频文件加载失败的情况进行处理
- 对字幕文件解析失败的情况进行处理
- 对视频合成失败的情况进行处理
- 单个场景字幕烧录失败时回退到无字幕版本，不影响整体
- FFmpeg stream-copy 失败时自动回退到 MoviePy 重编码

### 6.5 性能优化

- 使用 FFmpeg stream-copy 快速路径（零重编码）
- 合理管理内存，及时释放不再使用的资源
- 优化视频编码参数，提高编码效率
- 字幕预烧录时音频 stream-copy，避免重新编码
- 响度归一化仅在最终编码阶段执行一次，避免多次归一化

## 7. 扩展点

- 支持更多视频过渡效果
- 支持更多字幕样式和位置选项
- 支持视频特效和滤镜
- 支持批量处理多个视频任务
- 支持多语言字幕轨道切换
- 支持场景级 BGM 切换
- 支持智能场景转场检测

## 8. 总结

多场景视频处理系统通过模块化的设计，实现了从单个场景视频到完整视频的生成过程。系统采用**场景字幕预烧录**架构，确保音字幕完美同步；通过**FFmpeg stream-copy 快速路径**实现高效的场景合并；通过**参数一致性设计**保证静默前缀与场景视频无缝衔接。系统的函数职责清晰，调用关系合理，代码结构模块化，便于维护和扩展。