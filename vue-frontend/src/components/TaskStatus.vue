<template>
  <div class="task-status">
    <el-card :body-style="{ padding: '16px' }">
      <template #header>
        <div class="card-header">
          <span>{{ title }}</span>
          <el-button v-if="refreshable" type="primary" size="small" @click="$emit('refresh')">
            <el-icon><Refresh /></el-icon>
            {{ refreshText }}
          </el-button>
        </div>
      </template>
      
      <div v-if="loading" class="loading-container">
        <el-spinner size="40" />
        <p>{{ loadingText }}</p>
      </div>
      
      <div v-else-if="error" class="error-container">
        <el-alert
          :title="error"
          type="error"
          show-icon
          :closable="false"
        />
        <el-button type="primary" size="small" @click="$emit('refresh')">
          {{ retryText }}
        </el-button>
      </div>
      
      <div v-else-if="tasks.length === 0" class="empty-container">
        <el-empty description="{{ emptyText }}" />
      </div>
      
      <div v-else class="tasks-list">
        <div class="tasks-scroll">
          <el-collapse v-model="activeNames" @change="onCollapseChange">
            <el-collapse-item v-for="task in tasks" :key="task.task_id" :name="task.task_id">
              <template #title>
                <span class="task-title-wrapper">
                  <span class="task-title-text">{{ getTaskTitle(task) }}</span>
                  <el-icon v-if="tasksStore.isNewlyCompleted(task.task_id)"
                           class="new-star-icon">
                    <StarFilled />
                  </el-icon>
                </span>
              </template>
              <div class="task-details">
                <div class="task-info">
                  <div class="info-item" v-if="task.sequence_number">
                    <span class="label">{{ sequenceNumberText }}:</span>
                    <el-tag type="primary">#{{ task.sequence_number }}</el-tag>
                  </div>
                  <div class="info-item">
                    <span class="label">{{ statusText }}:</span>
                    <transition name="fade" mode="out-in">
                      <el-tag :key="task.status" :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
                    </transition>
                  </div>
                  <div class="info-item">
                    <span class="label">{{ taskIdText }}:</span>
                    <span>{{ task.task_id }}</span>
                    <el-button
                      link
                      size="small"
                      :title="t('Copy Task ID')"
                      @click="copyToClipboard(task.task_id)"
                    >
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                  </div>
                  <div class="info-item" v-if="task.title_text !== undefined || canEditTitle(task)">
                    <span class="label">{{ titleTextLabel }}:</span>
                    <template v-if="editingTitleTaskId === task.task_id">
                      <el-input
                        v-model="editingTitleValue"
                        size="small"
                        @keyup.enter="saveTitle(task)"
                        @keyup.escape="cancelEditTitle"
                        @blur="saveTitle(task)"
                        class="title-edit-input"
                      />
                    </template>
                    <template v-else>
                      <span v-if="task.title_enabled === false" class="title-disabled">
                        {{ t('Title Disabled') }}
                      </span>
                      <span v-else :class="{ 'no-title': !task.title_text }">
                        {{ task.title_text || t('No Title') }}
                      </span>
                      <el-button
                        v-if="canEditTitle(task)"
                        link
                        size="small"
                        @click="startEditTitle(task)"
                        :title="t('Edit Title')"
                      >
                        <el-icon><Edit /></el-icon>
                      </el-button>
                    </template>
                  </div>
                  <div class="info-item" v-if="task.task_type">
                    <span class="label">{{ taskTypeText }}:</span>
                    <el-tag type="info">{{ getTaskTypeText(task.task_type) }}</el-tag>
                  </div>
                  <div class="info-item" v-if="task.progress !== undefined">
                    <span class="label">{{ progressText }}:</span>
                    <transition name="fade">
                      <el-progress :key="task.progress" :percentage="task.progress" :format="formatProgress" />
                    </transition>
                  </div>
                  <div class="info-item" v-if="task.created_at">
                    <span class="label">{{ createdAtText }}:</span>
                    <span>{{ formatDate(task.created_at) }}</span>
                  </div>
                  <div class="info-item" v-if="task.updated_at">
                    <span class="label">{{ updatedAtText }}:</span>
                    <span>{{ formatDate(task.updated_at) }}</span>
                  </div>
                  <div class="info-item" v-if="task.start_time">
                    <span class="label">{{ startTimeText }}:</span>
                    <span>{{ formatDate(task.start_time) }}</span>
                  </div>
                  <div class="info-item" v-if="task.end_time">
                    <span class="label">{{ endTimeText }}:</span>
                    <span>{{ formatDate(task.end_time) }}</span>
                  </div>
                  <div class="info-item" v-if="task.error">
                    <span class="label">{{ errorText }}:</span>
                    <span class="error-message">{{ task.error }}</span>
                  </div>
                </div>

                <div v-if="task.status === 'completed' && task.scene_loss_warning" class="scene-loss-banner">
                  <el-alert
                    :title="task.scene_loss_warning"
                    type="warning"
                    show-icon
                    :closable="false"
                  >
                    <template #default>
                      <span>{{ t('Some scenes were lost during generation. You can recover them via Scene Integration.') }}</span>
                    </template>
                  </el-alert>
                  <el-button
                    v-if="task.videos && task.videos.length > 0"
                    type="primary"
                    size="small"
                    class="recover-btn"
                    @click="navigateToSceneIntegration(task.task_id)"
                  >
                    {{ t('Recover Lost Scenes') }}
                  </el-button>
                </div>
                
                <div class="task-actions">
                  <transition name="fade">
                    <el-button v-if="task.status === 'completed' && task.videos && task.videos.length > 0" :key="'download-'+task.task_id" type="primary" size="small" @click="handleDownload(task)">
                      <el-icon><Download /></el-icon>
                      {{ downloadText }}
                    </el-button>
                  </transition>
                  
                  <transition name="fade">
                    <el-button v-if="task.status === 'running'" :key="'cancel-'+task.task_id" type="warning" size="small" @click="$emit('cancel', task.task_id)">
                      <el-icon><Close /></el-icon>
                      {{ cancelText }}
                    </el-button>
                    <el-button v-else-if="task.status === 'cancelling'" :key="'cancelling-'+task.task_id" type="warning" size="small" disabled>
                      <el-icon><Loading /></el-icon>
                      {{ t('Cancelling...') }}
                    </el-button>
                  </transition>
                  
                  <el-button type="danger" size="small" @click.stop="$emit('delete', task.task_id)">
                    <el-icon><Delete /></el-icon>
                    {{ deleteText }}
                  </el-button>
                  
                  <el-button
                    v-if="shouldShowImproveButton(task)"
                    :key="'improve-'+task.task_id"
                    type="success"
                    size="small"
                    @click="navigateToSceneIntegration(task.task_id)"
                  >
                    {{ t('Improve Scenes') }}
                  </el-button>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { Refresh, Download, Delete, Close, Loading, StarFilled, CopyDocument, Edit } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { useI18nStore } from '../stores/i18n';
import { useTasksStore } from '../stores/tasks';
import { apiService } from '../services/api';

const i18nStore = useI18nStore();
const t = i18nStore.t;
const tasksStore = useTasksStore();

interface Task {
  task_id: string;
  status: string;
  task_type?: string;
  progress?: number;
  videos?: string[];
  combined_videos?: string[];
  error?: string;
  created_at?: string;
  updated_at?: string;
  start_time?: string;
  end_time?: string;
  sequence_number?: number;
  title_enabled?: boolean;
  title_text?: string;
  video_title?: string;
  scene_loss_warning?: string;
  failed_scene_indices?: number[];
}

interface Props {
  tasks: Task[];
  loading?: boolean;
  error?: string;
  title?: string;
  refreshable?: boolean;
  refreshText?: string;
  loadingText?: string;
  retryText?: string;
  emptyText?: string;
  statusText?: string;
  taskTypeText?: string;
  progressText?: string;
  createdAtText?: string;
  updatedAtText?: string;
  startTimeText?: string;
  endTimeText?: string;
  errorText?: string;
  downloadText?: string;
  deleteText?: string;
  cancelText?: string;
  sequenceNumberText?: string;
  taskIdText?: string;
  titleTextLabel?: string;
}

withDefaults(defineProps<Props>(), {
  tasks: () => [],
  loading: false,
  error: '',
  title: 'Task Status',
  refreshable: true,
  refreshText: 'Refresh',
  loadingText: 'Loading tasks...',
  retryText: 'Retry',
  emptyText: 'No tasks',
  statusText: 'Status',
  taskTypeText: 'Task Type',
  progressText: 'Progress',
  createdAtText: 'Created At',
  updatedAtText: 'Updated At',
  startTimeText: 'Start Time',
  endTimeText: 'End Time',
  errorText: 'Error',
  downloadText: 'Download',
  deleteText: 'Delete',
  cancelText: 'Cancel',
  sequenceNumberText: 'Task #',
  taskIdText: 'Task ID',
  titleTextLabel: 'Title Text'
});

const emit = defineEmits(['refresh', 'delete', 'cancel']);

// Title editing state
const editingTitleTaskId = ref<string | null>(null);
const editingTitleValue = ref('');

const canEditTitle = (task: Task): boolean => {
  return task.status === 'pending';
};

const startEditTitle = (task: Task) => {
  editingTitleTaskId.value = task.task_id;
  editingTitleValue.value = task.title_text || '';
};

const cancelEditTitle = () => {
  editingTitleTaskId.value = null;
  editingTitleValue.value = '';
};

const saveTitle = async (task: Task) => {
  if (!editingTitleValue.value.trim()) {
    ElMessage.warning(t('Title cannot be empty'));
    return;
  }
  try {
    const response = await apiService.updateTaskTitle(task.task_id, editingTitleValue.value);
    if (response.status === 200) {
      task.title_text = editingTitleValue.value;
      task.video_title = editingTitleValue.value;
      ElMessage.success(t('Title updated'));
    }
  } catch (error) {
    console.error('Failed to update title:', error);
    ElMessage.error(t('Failed to update title'));
  }
  cancelEditTitle();
};

const activeNames = ref<string[]>([]);
const prevActiveNames = ref<string[]>([]);

const onCollapseChange = (newNames: string | string[]) => {
  const arr = typeof newNames === 'string' ? [newNames] : newNames;
  const newlyOpened = arr.filter(name => !prevActiveNames.value.includes(name));
  newlyOpened.forEach(taskId => tasksStore.markTaskViewed(taskId));
  prevActiveNames.value = arr;
};

const getTaskTitle = (task: Task): string => {
  const taskNumber = task.sequence_number ? `#${task.sequence_number}` : '';
  const displayTitle = task.video_title?.trim() || task.task_id;
  return `${taskNumber} ${displayTitle} - ${getStatusText(task.status)}`;
};

const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: t('Pending'),
    running: t('Running'),
    cancelling: t('Cancelling...'),
    completed: t('Completed'),
    failed: t('Failed')
  };
  return statusMap[status] || status;
};

const getStatusType = (status: string): string => {
  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    cancelling: 'warning',
    completed: 'success',
    failed: 'danger'
  };
  return typeMap[status] || 'info';
};

const getTaskTypeText = (taskType: string): string => {
  const taskTypeMap: Record<string, string> = {
    video_generation: t('Video Generation'),
    scene_integration: t('Scene Integration')
  };
  return taskTypeMap[taskType] || taskType;
};

const formatProgress = (percentage: number): string => {
  return `${percentage}%`;
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success(t('Copied'));
  } catch (err) {
    ElMessage.error(t('Copy failed'));
  }
};

const handleDownload = (task: Task) => {
  if (task.videos && task.videos.length > 0) {
    tasksStore.markTaskViewed(task.task_id);
    window.open(task.videos[0], '_blank');
  }
};

const router = useRouter();
const navigateToSceneIntegration = (taskId: string) => {
  router.push({ name: 'SceneIntegration', query: { original_task_id: taskId } });
};

const shouldShowImproveButton = (task: Task): boolean => {
  const show = task.status === 'completed' &&
               !!task.videos && task.videos.length > 0 &&
               !task.scene_loss_warning;
  console.log(`[TaskStatus] task_id=${task.task_id}, status=${task.status}, videos=${task.videos?.length}, scene_loss_warning=${task.scene_loss_warning}, showImprove=${show}`);
  return show;
};
</script>

<style scoped>
.task-status {
  width: 100%;
  flex: 1;
  overflow: hidden;
}

.task-status :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.task-status :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
}

.error-container {
  padding: 20px 0;
}

.empty-container {
  padding: 40px 0;
}

.tasks-list {
  margin-top: 10px;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.tasks-scroll {
  overflow-y: auto;
  flex: 1;
}

.task-details {
  padding: 10px 0;
}

.task-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 16px;
  margin-bottom: 12px;
}

.info-item {
  display: flex;
  align-items: center;
}

.label {
  font-weight: 500;
  width: 80px;
  flex-shrink: 0;
}

.error-message {
  color: #f56c6c;
  word-break: break-all;
}

.task-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.scene-loss-banner {
  margin-bottom: 12px;
}

.scene-loss-banner .recover-btn {
  margin-top: 8px;
}

.task-title-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.task-title-text {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.new-star-icon {
  color: #E6A23C;
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
  animation: star-pulse 1.5s ease-in-out infinite;
  transition: transform 0.2s ease;
}

.new-star-icon:hover {
  transform: scale(1.3);
}

@keyframes star-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.15); }
}

/* 过渡效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 进度条过渡效果 */
:deep(.el-progress__bar) {
  transition: width 0.5s ease;
}

/* 标签过渡效果 */
:deep(.el-tag) {
  transition: all 0.3s ease;
}

/* 按钮过渡效果 */
:deep(.el-button) {
  transition: all 0.3s ease;
}

/* 标题编辑输入框 */
.title-edit-input {
  width: 200px;
}

.title-edit-input :deep(.el-input__inner) {
  font-size: 13px;
}

/* 无标题占位符样式 */
.no-title {
  color: #909399;
  font-style: italic;
}

/* 标题已禁用样式 */
.title-disabled {
  color: #909399;
  text-decoration: line-through;
}
</style>