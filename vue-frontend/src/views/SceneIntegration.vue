<template>
  <div class="scene-integration">
    <el-card :body-style="{ padding: '20px' }">
      <template #header>
        <div class="card-header">
          <h2 class="title">🎬 {{ t('Scene Integration') }}</h2>
        </div>
      </template>
      
      <div class="integration-content">
        <!-- Input Type Selection -->
        <div class="form-item">
          <label class="form-label">{{ t('Input Type') }}</label>
          <el-radio-group v-model="inputType">
            <el-radio label="taskId">{{ t('Task ID') }}</el-radio>
            <el-radio label="directory">{{ t('Task Directory') }}</el-radio>
          </el-radio-group>
        </div>
        
        <!-- Task Input -->
        <div class="form-item">
          <label class="form-label" v-if="inputType === 'taskId'">{{ t('Task ID') }}</label>
          <label class="form-label" v-else>{{ t('Task Directory') }}</label>
          <el-input
            v-model="taskInput"
            :placeholder="inputType === 'taskId' ? t('Enter task ID to recover integration') : t('Enter task directory path')"
            class="form-input"
          />
          <div v-if="inputType === 'directory'" class="tip">{{ t('Please enter the full path to the task directory') }}</div>
        </div>
        
        <!-- Scan Button -->
        <div class="form-item">
          <el-button type="primary" class="form-button" @click="scanTask">{{ t('Scan') }}</el-button>
        </div>
        
        <!-- Scan Results -->
        <div v-if="taskFiles" class="scan-results">
          <h3 class="section-title">{{ t('Detected Files') }}</h3>
          
          <div class="file-status">
            <el-alert
              v-if="taskFiles.sceneVideos > 0"
              type="success"
              :title="`✅ ${t('Scene Videos')}: ${taskFiles.sceneVideos} ${t('items')}`"
              :closable="false"
            />
            <el-alert
              v-else
              type="error"
              :title="t('No valid scene videos found in task directory')"
              :closable="false"
            />
            
            <el-alert
              :type="taskFiles.sceneAudio > 0 ? 'success' : 'warning'"
              :title="taskFiles.sceneAudio > 0 ? `✅ ${t('Scene Audio')}: ${taskFiles.sceneAudio} ${t('items')}` : '⚠️ ' + t('No scene audio found')"
              :closable="false"
            />
          </div>
          
          <!-- Scene Range Selection -->
          <div v-if="taskFiles.sceneVideos > 0" class="scene-range">
            <h3 class="section-title">{{ t('Scene Range Selection') }}</h3>
            <div class="range-selectors">
              <div class="form-item">
                <label class="form-label">{{ t('Start Scene') }}</label>
                <el-select v-model="startScene" class="form-select">
                  <el-option
                    v-for="i in taskFiles.sceneNums"
                    :key="i"
                    :label="i"
                    :value="i"
                  />
                </el-select>
              </div>
              <div class="form-item">
                <label class="form-label">{{ t('End Scene') }}</label>
                <el-select v-model="endScene" class="form-select">
                  <el-option
                    v-for="i in taskFiles.sceneNums"
                    :key="i"
                    :label="i"
                    :value="i"
                    :disabled="i < startScene"
                  />
                </el-select>
              </div>
            </div>
          </div>
          
          <!-- Scene Details Collapse -->
          <div v-if="taskFiles.sceneVideos > 0 && taskFiles.scenes" class="scene-details-section">
            <el-divider />
            <el-collapse>
              <el-collapse-item :title="`${t('Scene Details')} (${taskFiles.scenes.length})`">
                <div v-for="scene in taskFiles.scenes" :key="scene.sceneNum" class="scene-row">
                  <div class="scene-row-header">
                    <span class="scene-num">{{ t('Scene') }} {{ scene.sceneNum }}</span>
                    <span class="status-badge" :class="scene.video ? 'status-ok' : 'status-missing'">
                      {{ scene.video ? '✅' : '❌' }} {{ t('Video') }}
                    </span>
                    <span class="status-badge" :class="scene.audio ? 'status-ok' : 'status-missing'">
                      {{ scene.audio ? '✅' : '❌' }} {{ t('Audio') }}
                    </span>
                    <span class="status-badge" :class="scene.subtitle ? 'status-ok' : 'status-missing'">
                      {{ scene.subtitle ? '✅' : '❌' }} {{ t('Subtitle') }}
                    </span>
                    <el-switch
                      v-model="forceRebuildScenes[scene.sceneNum]"
                      :disabled="isRunning"
                      size="small"
                      active-text=""
                      inactive-text=""
                    />
                    <span class="rebuild-label">{{ t('Rebuild') }}</span>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- Improve Integration Toggle -->
          <div v-if="taskFiles.sceneVideos > 0" class="improve-section">
            <el-divider />
            <div class="improve-toggle">
              <el-switch v-model="improveIntegration" />
              <span class="improve-label">{{ t('Improve Integration') }}</span>
              <el-tooltip :content="t('Apply current config instead of original task config')" placement="top">
                <el-icon class="improve-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
            <div v-if="improveIntegration" class="improve-items">
              <el-checkbox v-model="improveSubtitle">{{ t('Subtitle Settings') }}</el-checkbox>
              <el-checkbox v-model="improveBgm">{{ t('Background Music') }}</el-checkbox>
              <el-checkbox v-model="improveTitle">{{ t('Title Settings') }}</el-checkbox>
              <el-checkbox v-model="improveVideoEnhancement">{{ t('Video Enhancement') }}</el-checkbox>
            </div>
          </div>

          <!-- Start Integration Button -->
          <div v-if="taskFiles.sceneVideos > 0" class="form-item">
            <el-button
              type="primary"
              class="form-button"
              @click="startIntegration"
              :disabled="isRunning || isCompleted"
            >
              {{ isCompleted ? t('Integration Completed') : (isRunning ? t('Integrating...') : t('Start Integration')) }}
            </el-button>
          </div>
          
          <!-- Progress Bar -->
          <div v-if="isRunning || isCompleted" class="progress-container">
            <el-progress
              :percentage="progress"
              :status="progress === 100 ? 'success' : ''"
            />
            <div class="progress-status">{{ status }}</div>
          </div>
          
          <!-- Integration Result -->
          <div v-if="integrationResult" class="integration-result">
            <h3 class="section-title">{{ t('Generated Video') }}</h3>
            <div class="video-preview">
              <!-- Video preview would go here -->
              <div class="result-info">
                <span>{{ t('Video path') }}: {{ integrationResult }}</span>
                <el-button type="primary" size="small" @click="downloadVideo">{{ t('Download Video') }}</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, onMounted } from 'vue';
import { InfoFilled } from '@element-plus/icons-vue';
import { useI18nStore } from '../stores/i18n';
import { useSettingsStore } from '../stores/settings';
import { useScriptStore } from '../stores/script';
import { apiService } from '../services/api';

const i18nStore = useI18nStore();
const t = i18nStore.t;
const settingsStore = useSettingsStore();

const STORAGE_KEY = 'coiner-scene-integration';

// Input type
const inputType = ref('taskId');
// Task input
const taskInput = ref('');
// Task file information
const taskFiles = ref<any>(null);
// Start scene
const startScene = ref(1);
// End scene
const endScene = ref(1);
// Whether it's running
const isRunning = ref(false);
// Improve integration toggle
const improveIntegration = ref(false);
const improveSubtitle = ref(true);
const improveBgm = ref(true);
const improveTitle = ref(true);
const improveVideoEnhancement = ref(true);
// Progress
const progress = ref(0);
// Status
const status = ref('');
// Integration result
const integrationResult = ref('');
// Integration completed flag
const isCompleted = ref(false);
// Force rebuild toggle per scene (keyed by scene number)
const forceRebuildScenes = ref<Record<number, boolean>>({});
// Current task ID for polling
const currentTaskId = ref('');
// Polling interval ID
let pollInterval: number | null = null;

const loadFromLocalStorage = () => {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      inputType.value = parsed.inputType || 'taskId';
      taskInput.value = parsed.taskInput || '';
      startScene.value = parsed.startScene || 1;
      endScene.value = parsed.endScene || 1;
    } catch (e) {
      console.error('Failed to load scene integration settings from localStorage:', e);
    }
  }
};

const saveToLocalStorage = () => {
  const data = {
    inputType: inputType.value,
    taskInput: taskInput.value,
    startScene: startScene.value,
    endScene: endScene.value
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
};

onMounted(() => {
  loadFromLocalStorage();
});

// Watch start scene changes, update end scene
watch(startScene, (newStart) => {
  if (endScene.value < newStart) {
    endScene.value = newStart;
  }
  saveToLocalStorage();
});

watch(inputType, () => saveToLocalStorage());
watch(taskInput, () => saveToLocalStorage());
watch(endScene, () => saveToLocalStorage());

// Scan task
const scanTask = async () => {
  if (!taskInput.value) {
    return;
  }
  
  status.value = t('Scanning task directory...');
  isRunning.value = true;
  isCompleted.value = false;
  
  try {
    const response = await apiService.scanSceneIntegration(taskInput.value);
    if (response.status === 200 && response.data) {
      const rawScenesData = response.data.scenesData || [];
      taskFiles.value = {
        sceneVideos: response.data.sceneVideos,
        sceneAudio: response.data.sceneAudio,
        subtitle: response.data.subtitle,
        totalScenes: response.data.totalScenes,
        isValid: response.data.isValid,
        taskDir: response.data.taskDir,
        sceneNums: response.data.sceneNums,
        scenes: response.data.scenes || [],
        scenesData: rawScenesData,
      };

      if (response.data.sceneNums && response.data.sceneNums.length > 0) {
        startScene.value = response.data.sceneNums[0];
        endScene.value = response.data.sceneNums[response.data.sceneNums.length - 1];
      } else {
        startScene.value = 1;
        endScene.value = response.data.sceneVideos || 1;
      }
    } else {
      taskFiles.value = null;
    }
  } catch (error) {
    console.error('Error scanning task:', error);
    taskFiles.value = null;
    status.value = t('Failed to scan task directory');
  } finally {
    isRunning.value = false;
    if (!status.value) {
      status.value = '';
    }
  }
};

// Start integration
const startIntegration = async () => {
  if (!taskInput.value || !taskFiles.value) {
    return;
  }
  
  isRunning.value = true;
  isCompleted.value = false;
  progress.value = 0;
  status.value = t('Starting...');
  integrationResult.value = '';
  
  // Get latest subtitle settings from settings store
  const subtitleParams = {
    subtitle_enabled: settingsStore.subtitle.enable,
    font_name: settingsStore.subtitle.font,
    font_size: settingsStore.subtitle.fontSize,
    text_fore_color: settingsStore.subtitle.color,
    text_background_color: 'transparent',
    stroke_color: settingsStore.subtitle.outlineColor,
    stroke_width: settingsStore.subtitle.outlineWidth,
    subtitle_position: settingsStore.subtitle.position,
    custom_position: settingsStore.subtitle.customPosition ?? 70.0
  };
  
  // Get latest BGM settings from settings store
  const bgmParams = {
    bgm_type: settingsStore.audio.backgroundMusic || 'none',
    bgm_file: '',
    bgm_volume: parseFloat(settingsStore.audio.backgroundMusicVolume) || 0.2
  };
  
  // Get latest video enhancement settings from settings store
  const videoEnhanceParams = {
    output_bg_color: settingsStore.video.outputBgColor,
    silence_duration: settingsStore.video.silenceDuration,
  };

  // Get latest title settings from settings store
  const titleParams = {
    title_enabled: settingsStore.video.title.enabled,
    title_text: settingsStore.video.title.text,
    title_duration: settingsStore.video.title.duration,
    title_font_name: settingsStore.video.title.font,
    title_font_size: settingsStore.video.title.fontSize,
    title_text_color: settingsStore.video.title.color,
    title_stroke_color: settingsStore.video.title.strokeColor,
    title_stroke_width: settingsStore.video.title.strokeWidth,
    title_background_color: settingsStore.video.title.backgroundColor,
    title_position: settingsStore.video.title.position,
    title_margin: settingsStore.video.title.margin,
    title_margin_left: settingsStore.video.title.marginLeft,
    title_margin_right: settingsStore.video.title.marginRight,
    title_animation: settingsStore.video.title.animation,
    title_animation_duration: settingsStore.video.title.animationDuration,
    title_background_overlay: settingsStore.video.title.backgroundOverlay,
    title_overlay_color: settingsStore.video.title.overlayColor,
    title_align: settingsStore.video.title.align,
  };
  
  // Map UI aspect names to backend VideoAspect values
  const aspectMap: Record<string, string> = {
    'landscape': '16:9',
    'portrait': '9:16',
    'square': '1:1',
    'portrait_3_4': '3:4',
    'landscape_4_3': '4:3'
  };
  const uiAspect = settingsStore.video.aspect;
  const mappedAspect = aspectMap[uiAspect] || uiAspect || '9:16';

  // Collect scenes with force rebuild toggle enabled
  const forceScenes = Object.entries(forceRebuildScenes.value)
    .filter(([_, on]) => on)
    .map(([num]) => parseInt(num));

  const scriptStore = useScriptStore();

  // If force-rebuild scenes are selected, persist latest scene data to script.json first
  if (forceScenes.length > 0) {
    const sceneUpdates: any[] = [];
    const scenesDataFallback = taskFiles.value.scenesData || [];

    for (const num of forceScenes) {
      const idx = num - 1;
      // Prefer scriptStore.scenes (camelCase, latest from ScriptSettings)
      const storeScene = scriptStore.scenes[idx];
      const fallback = scenesDataFallback.find((s: any) => s.sceneNum === num);

      if (storeScene) {
        // Map camelCase → snake_case (same pattern as App.vue)
        sceneUpdates.push({
          scene_num: num,
          scene_data: {
            id: storeScene.id,
            title: storeScene.title,
            duration: storeScene.duration,
            visual_requirement: storeScene.visual_requirement,
            keywords: storeScene.keywords,
            script: storeScene.script,
            intro_video: storeScene.introVideo || '',
            intro_video_original_path: storeScene.introVideoOriginalPath || '',
            intro_duration: storeScene.introVideoDuration || 10,
            intro_video_cover_full: storeScene.introVideoCoverFull || false,
          },
          search_terms: (storeScene.keywords || '')
            .split(',')
            .map((k: string) => k.trim())
            .filter((k: string) => k),
        });
      } else if (fallback) {
        // Fallback to scan data (already snake_case from backend)
        sceneUpdates.push({
          scene_num: num,
          scene_data: { ...fallback.sceneData },
          search_terms: [...(fallback.searchTerms || [])],
        });
      }
    }

    if (sceneUpdates.length > 0) {
      await apiService.updateSceneIntegrationScenes(taskInput.value, sceneUpdates);
    }
  }

  try {
    // Build request params: only include param groups selected in improve mode
    const requestParams: Record<string, any> = {};
    if (improveIntegration.value) {
      if (improveSubtitle.value) Object.assign(requestParams, subtitleParams);
      if (improveBgm.value) Object.assign(requestParams, bgmParams);
      if (improveTitle.value) Object.assign(requestParams, titleParams);
      if (improveVideoEnhancement.value) Object.assign(requestParams, videoEnhanceParams);
    }
    // When toggle is OFF, requestParams is empty → backend uses original_task config / defaults

    // Always include force rebuild params when scenes are selected
    if (forceScenes.length > 0) {
      requestParams.force_rebuild_scenes = forceScenes;
      requestParams.voice_name = settingsStore.audio.speechSynthesis;
      requestParams.voice_rate = parseFloat(settingsStore.audio.speechRate) || 1.0;
      requestParams.voice_volume = parseFloat(settingsStore.audio.speechVolume) || 1.0;
      requestParams.voice_emotion = settingsStore.audio.voiceEmotion || '';
      requestParams.video_source = settingsStore.video.source || 'pexels';
      requestParams.video_aspect = mappedAspect;
      requestParams.video_concat_mode = settingsStore.video.concatMode || 'random';
      requestParams.video_clip_duration = settingsStore.video.clipDuration || 5;
    }

    const response = await apiService.recoverSceneIntegration(
      taskInput.value, 
      startScene.value, 
      endScene.value,
      requestParams
    );
    
    if (response.status === 200 && response.data && response.data.task_id) {
      currentTaskId.value = response.data.task_id;
      status.value = t('Integration in progress...');
      startPolling();
    } else {
      status.value = t('Video integration failed');
      isRunning.value = false;
    }
  } catch (error) {
    console.error('Error starting integration:', error);
    status.value = t('Video integration failed');
    isRunning.value = false;
  }
};

// Start polling task status
const startPolling = () => {
  stopPolling();
  
  pollInterval = window.setInterval(async () => {
    try {
      const response = await apiService.getTask(currentTaskId.value);
      if (response.status === 200 && response.data) {
        const task = response.data;
        
        if (task.progress !== undefined) {
          progress.value = task.progress;
          
          if (progress.value >= 100 && !isCompleted.value) {
            progress.value = 100;
            status.value = t('Scene integration completed');
            isCompleted.value = true;
            if (task.videos && task.videos.length > 0) {
              integrationResult.value = task.videos[0];
            }
            stopPolling();
            isRunning.value = false;
            return;
          }
        }
        
        if (task.state === 'processing' || task.state === 1) {
          status.value = t('Integration in progress...');
        } else if (task.state === 'complete' || task.state === 2) {
          progress.value = 100;
          status.value = t('Scene integration completed');
          isCompleted.value = true;
          if (task.videos && task.videos.length > 0) {
            integrationResult.value = task.videos[0];
          }
          stopPolling();
          isRunning.value = false;
        } else if (task.state === 'failed' || task.state === 3) {
          status.value = t('Video integration failed');
          isCompleted.value = false;
          stopPolling();
          isRunning.value = false;
        }
      }
    } catch (error: any) {
      console.error('Error polling task status:', error);
      if (error?.response?.status === 404) {
        stopPolling();
        isRunning.value = false;
        status.value = t('Task no longer exists');
      }
    }
  }, 3000);
};

// Stop polling
const stopPolling = () => {
  if (pollInterval !== null) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
};

// Cleanup on unmount
onUnmounted(() => {
  stopPolling();
});

// Download video
const downloadVideo = () => {
  // Simulate download
  console.log('Downloading video:', integrationResult.value);
};

defineExpose({
  inputType,
  taskInput,
  taskFiles,
  startScene,
  endScene,
  isRunning,
  isCompleted,
  progress,
  status,
  integrationResult
});
</script>

<style scoped>
.scene-integration {
  width: 100%;
}

.card-header {
  margin-bottom: 4px;
}



.integration-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 0px;
}

.form-label {
  font-weight: normal;
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
  line-height: 1.4;
}

.form-input {
  width: 100%;
  padding: 6px 8px;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-input :deep(.el-input) {
  width: 100%;
}

.form-select {
  width: 100%;
  padding: 6px 8px;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-select :deep(.el-select) {
  width: 100%;
}

.form-button {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border-radius: 4px;
  transition: all 0.3s;
}

.form-button:hover {
  opacity: 0.9;
}

.tip {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.scan-results {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e0e0e0;
}

.section-title {
  font-size: 16px;
  font-weight: bold;
  margin: 15px 0 10px 0;
  color: #333;
}

.file-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 15px;
}

.scene-range {
  margin: 15px 0;
}

.range-selectors {
  display: flex;
  gap: 15px;
}

.range-selectors .form-item {
  flex: 1;
}

.improve-section {
  margin: 8px 0;
}

.improve-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.improve-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.improve-info {
  font-size: 14px;
  color: #909399;
  cursor: help;
}

.improve-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-left: 4px;
  padding-left: 12px;
  border-left: 2px solid #e0e0e0;
}

.progress-container {
  margin: 15px 0;
}

.progress-status {
  text-align: center;
  margin-top: 5px;
  font-size: 14px;
  color: #606266;
}

.scene-details-section {
  margin: 8px 0;
}

.scene-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
  border-bottom: 1px solid #f0f0f0;
}

.scene-row:last-child {
  border-bottom: none;
}

.scene-num {
  font-weight: 600;
  min-width: 70px;
  font-size: 14px;
}

.status-badge {
  font-size: 13px;
  min-width: 80px;
}

.status-ok {
  color: #67c23a;
}

.status-missing {
  color: #f56c6c;
}

.rebuild-label {
  font-size: 13px;
  color: #909399;
  margin-left: 2px;
}

.integration-result {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #e0e0e0;
}

.video-preview {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 15px;
  background-color: #f9f9f9;
}

.result-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>