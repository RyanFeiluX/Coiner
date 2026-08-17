<template>
  <div class="video-splitter">
    <el-card :body-style="{ padding: '20px' }">
      <template #header>
        <div class="card-header">
          <h2 class="title">✂️ {{ t('Video Split') }}</h2>
        </div>
      </template>

      <div class="splitter-content">
        <!-- Task Input -->
        <div class="form-item">
          <label class="form-label">{{ t('Source Task ID') }}</label>
          <el-input
            v-model="taskInput"
            :placeholder="t('Enter task ID to scan for splitting')"
            class="form-input"
          />
        </div>

        <!-- Scan Button -->
        <div class="form-item">
          <el-button type="primary" class="form-button" @click="scanTask" :disabled="isScanning">
            {{ isScanning ? t('Scanning...') : t('Scan & Analyze') }}
          </el-button>
        </div>

        <!-- Scan Results -->
        <div v-if="scanResult" class="scan-results">
          <!-- Scene Analysis -->
          <div class="analysis-summary">
            <el-alert
              type="success"
              :closable="false"
              :title="`${t('Total')}: ${scanResult.scenes.length} ${t('scenes')} | ${t('Duration')}: ${scanResult.total_duration}s | ${t('Suggested segments')}: ${scanResult.suggested_segments.length}`"
            />
          </div>

          <!-- Scene Table -->
          <div class="scene-table-section">
            <h3 class="section-title">{{ t('Scene Analysis') }}</h3>
            <el-table :data="scanResult.scenes" size="small" stripe>
              <el-table-column prop="scene_num" :label="t('Scene #')" width="80" />
              <el-table-column :label="t('Duration')" width="100">
                <template #default="{ row }">
                  {{ row.duration }}s
                </template>
              </el-table-column>
              <el-table-column prop="script_preview" :label="t('Script Preview')" show-overflow-tooltip />
            </el-table>
          </div>

          <!-- Split Config -->
          <div class="split-config">
            <h3 class="section-title">{{ t('Split Configuration') }}</h3>
            <div class="config-row">
              <div class="form-item config-item">
                <label class="form-label">{{ t('Min Duration') }} (s)</label>
                <el-input-number v-model="minDuration" :min="10" :max="300" :step="5" />
              </div>
              <div class="form-item config-item">
                <label class="form-label">{{ t('Max Duration') }} (s)</label>
                <el-input-number v-model="maxDuration" :min="10" :max="300" :step="5" />
              </div>
              <div class="form-item config-item">
                <el-button type="primary" @click="autoPlan" :disabled="isScanning">
                  {{ t('Auto Plan') }}
                </el-button>
              </div>
            </div>
          </div>

          <!-- Title Config -->
          <div class="title-config" v-if="scanResult">
            <h3 class="section-title">{{ t('Title Settings') }}</h3>
            <div class="config-row">
              <div class="form-item config-item">
                <div class="title-toggle">
                  <el-switch v-model="titleEnabled" />
                  <span class="toggle-label">{{ t('Enable Video Title') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Segment Plan -->
          <div class="segment-plan">
            <div class="section-header">
              <h3 class="section-title">{{ t('Segment Plan') }}</h3>
              <el-button size="small" @click="addSegment">+ {{ t('Add Segment') }}</el-button>
            </div>

            <div v-if="segments.length === 0" class="empty-segments">
              <el-alert type="info" :closable="false" :title="t('No segments planned. Click Auto Plan or add manually.')" />
            </div>

            <div v-else class="segment-list">
              <div
                v-for="(segment, segIdx) in segments"
                :key="segIdx"
                class="segment-card"
              >
                <div class="segment-header">
                  <span class="segment-title">{{ t('Segment') }} {{ segIdx + 1 }}</span>
                  <span class="segment-duration">{{ segment.duration }}s</span>
                  <el-button size="small" type="danger" text @click="removeSegment(segIdx)">
                    {{ t('Delete') }}
                  </el-button>
                </div>
                <div v-if="titleEnabled" class="segment-title-edit">
                  <el-input
                    v-model="segment.title"
                    :placeholder="t('Enter video title')"
                    size="small"
                    clearable
                    maxlength="60"
                    show-word-limit
                  />
                </div>
                <div class="segment-scenes">
                  <div class="scene-chips">
                    <el-tag
                      v-for="sceneNum in segment.scene_nums"
                      :key="sceneNum"
                      closable
                      size="small"
                      @close="removeSceneFromSegment(segIdx, sceneNum)"
                    >
                      {{ t('Scene') }} {{ sceneNum }} ({{ getSceneDuration(sceneNum) }}s)
                    </el-tag>
                    <el-button size="small" text @click="openAddSceneDialog(segIdx)">
                      + {{ t('Add Scene') }}
                    </el-button>
                  </div>
                  <div v-if="segment.script_preview" class="segment-script">
                    {{ segment.script_preview }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Execute Button -->
          <div v-if="segments.length > 0" class="form-item">
            <el-button
              type="primary"
              class="form-button"
              @click="executeSplit"
              :disabled="isRunning || isCompleted"
            >
              {{ isCompleted ? t('Split Completed') : (isRunning ? t('Splitting...') : t('Start Split')) }}
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

          <!-- Split Results -->
          <div v-if="splitResults.length > 0" class="split-results">
            <div class="section-header">
              <h3 class="section-title">{{ t('Generated Short Videos') }}</h3>
              <el-checkbox v-model="selectAll" :indeterminate="isIndeterminate">{{ t('Select All') }}</el-checkbox>
            </div>
            <div v-for="(result, idx) in splitResults" :key="idx" class="result-item">
              <el-checkbox v-model="result.selected" />
              <span class="result-name">{{ result.name }}</span>
              <span class="result-duration">{{ result.duration }}</span>
              <el-button type="primary" size="small" @click="downloadSingle(result)">
                {{ t('Download') }}
              </el-button>
            </div>
            <div class="download-actions">
              <el-button type="primary" :disabled="selectedResults.length === 0" @click="downloadSelected">
                {{ t('Download Selected') }} ({{ selectedResults.length }})
              </el-button>
              <el-button @click="downloadAll">
                {{ t('Download All') }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Add Scene Dialog -->
    <el-dialog v-model="showAddSceneDialog" :title="t('Add Scene to Segment')" width="400px">
      <div class="dialog-content">
        <el-select v-model="sceneToAdd" :placeholder="t('Select Scene')" style="width: 100%">
          <el-option
            v-for="scene in availableScenes"
            :key="scene.scene_num"
            :label="`${t('Scene')} ${scene.scene_num} (${scene.duration}s)`"
            :value="scene.scene_num"
          />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showAddSceneDialog = false">{{ t('Cancel') }}</el-button>
        <el-button type="primary" @click="confirmAddScene" :disabled="!sceneToAdd">{{ t('Confirm') }}</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useI18nStore } from '../stores/i18n';
import { apiService } from '../services/api';

const i18nStore = useI18nStore();
const t = i18nStore.t;

const STORAGE_KEY = 'coiner-video-splitter';

// Input
const taskInput = ref('');
// Scan result
const scanResult = ref<any>(null);
// Config
const minDuration = ref(30);
const maxDuration = ref(90);
// Title toggle
const titleEnabled = ref(false);
// Segments
const segments = ref<any[]>([]);
// Scanning state
const isScanning = ref(false);
// Execution state
const isRunning = ref(false);
const isCompleted = ref(false);
const progress = ref(0);
const status = ref('');
// Split results
const splitResults = ref<any[]>([]);
// Current task ID for polling
const currentTaskId = ref('');
// Polling
let pollInterval: number | null = null;

// Add scene dialog
const showAddSceneDialog = ref(false);
const sceneToAdd = ref<number | null>(null);
const targetSegmentIdx = ref(0);

// Computed: available scenes not yet in any segment
const availableScenes = computed(() => {
  if (!scanResult.value) return [];
  const usedScenes = new Set<number>();
  for (const seg of segments.value) {
    for (const num of seg.scene_nums) {
      usedScenes.add(num);
    }
  }
  return scanResult.value.scenes.filter((s: any) => !usedScenes.has(s.scene_num));
});

// Get scene duration by number
const getSceneDuration = (sceneNum: number): number => {
  if (!scanResult.value) return 0;
  const scene = scanResult.value.scenes.find((s: any) => s.scene_num === sceneNum);
  return scene ? scene.duration : 0;
};

// Load from localStorage
const loadFromLocalStorage = () => {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      taskInput.value = parsed.taskInput || '';
      minDuration.value = parsed.minDuration || 30;
      maxDuration.value = parsed.maxDuration || 90;
      titleEnabled.value = parsed.titleEnabled ?? false;
    } catch (e) {
      console.error('Failed to load video splitter settings:', e);
    }
  }
};

const saveToLocalStorage = () => {
  const data = {
    taskInput: taskInput.value,
    minDuration: minDuration.value,
    maxDuration: maxDuration.value,
    titleEnabled: titleEnabled.value,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
};

watch(taskInput, () => saveToLocalStorage());
watch(minDuration, () => saveToLocalStorage());
watch(maxDuration, () => saveToLocalStorage());
watch(titleEnabled, () => saveToLocalStorage());

onMounted(() => {
  loadFromLocalStorage();
  // Pre-fill from route query
  const route = useRoute();
  const sourceTaskId = route.query.source_task_id;
  if (sourceTaskId && typeof sourceTaskId === 'string') {
    taskInput.value = sourceTaskId;
  }
});

onUnmounted(() => {
  stopPolling();
});

// Scan task
const scanTask = async () => {
  if (!taskInput.value) return;

  isScanning.value = true;
  try {
    const response = await apiService.scanVideoSplit(taskInput.value, minDuration.value, maxDuration.value);
    if (response.status === 200 && response.data) {
      scanResult.value = response.data;
      // Auto-apply suggested segments
      titleEnabled.value = response.data.original_title_enabled ?? false;
      segments.value = (response.data.suggested_segments || []).map((seg: any) => ({
        scene_nums: [...seg.scene_nums],
        duration: seg.duration,
        script_preview: seg.script_preview || '',
        title: seg.title || '',
      }));
    } else {
      scanResult.value = null;
    }
  } catch (error) {
    console.error('Error scanning task:', error);
    scanResult.value = null;
  } finally {
    isScanning.value = false;
  }
};

// Auto plan segments
const autoPlan = async () => {
  if (!scanResult.value) return;

  try {
    const response = await apiService.planVideoSplit(scanResult.value.scenes, minDuration.value, maxDuration.value);
    if (response.status === 200 && response.data) {
      segments.value = response.data.segments || [];
    }
  } catch (error) {
    console.error('Error planning segments:', error);
  }
};

// Add segment
const addSegment = () => {
  segments.value.push({
    scene_nums: [],
    duration: 0,
    script_preview: '',
  });
};

// Remove segment
const removeSegment = (segIdx: number) => {
  segments.value.splice(segIdx, 1);
};

// Remove scene from segment
const removeSceneFromSegment = (segIdx: number, sceneNum: number) => {
  const seg = segments.value[segIdx];
  const idx = seg.scene_nums.indexOf(sceneNum);
  if (idx !== -1) {
    seg.scene_nums.splice(idx, 1);
    // Recalculate duration
    seg.duration = seg.scene_nums.reduce((sum: number, num: number) => sum + getSceneDuration(num), 0);
  }
};

// Open add scene dialog
const openAddSceneDialog = (segIdx: number) => {
  targetSegmentIdx.value = segIdx;
  sceneToAdd.value = null;
  showAddSceneDialog.value = true;
};

// Confirm add scene
const confirmAddScene = () => {
  if (sceneToAdd.value === null) return;
  const seg = segments.value[targetSegmentIdx.value];
  if (!seg.scene_nums.includes(sceneToAdd.value)) {
    seg.scene_nums.push(sceneToAdd.value);
    seg.scene_nums.sort((a: number, b: number) => a - b);
    seg.duration = seg.scene_nums.reduce((sum: number, num: number) => sum + getSceneDuration(num), 0);
  }
  showAddSceneDialog.value = false;
  sceneToAdd.value = null;
};

// Execute split
const executeSplit = async () => {
  if (!taskInput.value || segments.value.length === 0) return;

  isRunning.value = true;
  isCompleted.value = false;
  progress.value = 0;
  status.value = t('Starting...');
  splitResults.value = [];

  try {
    const response = await apiService.executeVideoSplit(
      taskInput.value,
      segments.value,
      minDuration.value,
      maxDuration.value,
      titleEnabled.value,
    );

    if (response.status === 200 && response.data && response.data.task_id) {
      currentTaskId.value = response.data.task_id;
      status.value = t('Split in progress...');
      startPolling();
    } else {
      status.value = t('Video split failed');
      isRunning.value = false;
    }
  } catch (error) {
    console.error('Error starting split:', error);
    status.value = t('Video split failed');
    isRunning.value = false;
  }
};

// Start polling
const startPolling = () => {
  stopPolling();
  pollInterval = window.setInterval(async () => {
    try {
      const response = await apiService.getTask(currentTaskId.value);
      if (response.status === 200 && response.data) {
        const task = response.data;

        if (task.progress !== undefined) {
          progress.value = task.progress;
        }

        if (task.status === 'completed') {
          progress.value = 100;
          status.value = t('Video split completed');
          isCompleted.value = true;
          if (task.videos && task.videos.length > 0) {
            splitResults.value = task.videos.map((path: string, idx: number) => ({
              name: `segment_${idx + 1}.mp4`,
              path: path,
              duration: segments.value[idx] ? `${segments.value[idx].duration}s` : '',
              selected: false,
            }));
          }
          stopPolling();
          isRunning.value = false;
        } else if (task.status === 'failed') {
          status.value = t('Video split failed');
          isCompleted.value = false;
          stopPolling();
          isRunning.value = false;
        } else {
          status.value = t('Split in progress...');
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

// Selected results
const selectedResults = computed(() => splitResults.value.filter((r: any) => r.selected));

const selectAll = computed({
  get: () => splitResults.value.length > 0 && splitResults.value.every((r: any) => r.selected),
  set: (val: boolean) => {
    splitResults.value.forEach((r: any) => { r.selected = val; });
  },
});

const isIndeterminate = computed(() => {
  const total = splitResults.value.length;
  const selected = selectedResults.value.length;
  return selected > 0 && selected < total;
});

// Extract task-relative path from URL for ZIP API
const getTaskRelativePath = (path: string): string => {
  return path.replace(/.*\/tasks\//, '');
};

// Single download: open in new tab
const downloadSingle = (result: any) => {
  window.open(result.path, '_blank');
};

// Download multiple files as ZIP
const downloadAsZip = async (files: any[]) => {
  console.log('[Download] downloadAsZip called, files:', files.length);
  try {
    const filePaths = files.map((f: any) => getTaskRelativePath(f.path));
    console.log('[Download] ZIP files:', filePaths);
    ElMessage.info(t('Preparing download...'));
    const blob = await apiService.downloadZip(filePaths);
    console.log('[Download] ZIP blob size:', blob.size);
    ElMessage.success(t('Download ready'));
    // Use <a download> instead of window.open to avoid popup blocker
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = 'segments.zip';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(blobUrl);
      document.body.removeChild(a);
    }, 5000);
  } catch (e: any) {
    console.error('[Download] ZIP download failed:', e?.code, e?.message, e?.response?.status, e?.response?.data?.constructor?.name);
    ElMessage.error(t('Download failed'));
  }
};

// Download selected
const downloadSelected = async () => {
  console.log('[Download] downloadSelected called, count:', selectedResults.value.length);
  ElMessage.info(t('Preparing download...'));
  const files = selectedResults.value;
  if (files.length === 0) return;
  if (files.length === 1) {
    downloadSingle(files[0]);
    return;
  }
  await downloadAsZip(files);
};

// Download all
const downloadAll = async () => {
  console.log('[Download] downloadAll called, count:', splitResults.value.length);
  ElMessage.info(t('Preparing download...'));
  const files = splitResults.value;
  if (files.length === 0) return;
  if (files.length === 1) {
    downloadSingle(files[0]);
    return;
  }
  await downloadAsZip(files);
};
</script>

<style scoped>
.video-splitter {
  width: 100%;
}

.video-splitter :deep(.el-card) {
  display: flex;
  flex-direction: column;
  overflow: visible;
}

.video-splitter :deep(.el-card__header) {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
  background: white;
}

.video-splitter :deep(.el-card__body) {
  overflow-y: visible;
}

.card-header {
  margin-bottom: 4px;
}

.splitter-content {
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

.scan-results {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e0e0e0;
}

.analysis-summary {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: bold;
  margin: 15px 0 10px 0;
  color: #333;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 15px 0 10px 0;
}

.section-header .section-title {
  margin: 0;
}

.scene-table-section {
  margin-bottom: 16px;
}

.split-config {
  margin-bottom: 16px;
}

.config-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.config-item {
  flex: 1;
}

.empty-segments {
  margin: 10px 0;
}

.segment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.segment-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
  background-color: #fafafa;
}

.segment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.segment-title {
  font-weight: 600;
  font-size: 14px;
}

.segment-duration {
  color: #409eff;
  font-weight: 500;
  font-size: 14px;
}

.segment-scenes {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.scene-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.title-config {
  margin-bottom: 16px;
}

.title-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.segment-title-edit {
  margin-bottom: 8px;
}

.segment-title-edit :deep(.el-input) {
  width: 100%;
}

.segment-script {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 4px;
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

.split-results {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #e0e0e0;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 8px;
  background-color: #f9f9f9;
}

.result-name {
  font-weight: 500;
  font-size: 14px;
  flex: 1;
}

.result-duration {
  color: #909399;
  font-size: 13px;
  margin-right: auto;
}

.dialog-content {
  padding: 10px 0;
}

.download-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e0e0e0;
}
</style>
