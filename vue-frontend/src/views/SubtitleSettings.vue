<template>
  <div class="subtitle-settings">
    <el-card :body-style="{ padding: '20px' }">
      <template #header>
        <div class="card-header">
          <h2 class="title">📝 {{ t('Subtitle Settings') }}</h2>
        </div>
      </template>
      
      <div class="settings-form">
        <div class="form-item">
          <el-checkbox v-model="form.enableSubtitles">{{ t('Enable Subtitles') }}</el-checkbox>
        </div>

        <div class="form-item" v-if="form.enableSubtitles">
          <label class="form-label">{{ t('Subtitle Engine') }}</label>
          <el-tooltip :content="t('Subtitle Engine Tooltip')" placement="top">
            <el-radio-group v-model="form.subtitleEngine" @change="handleSubtitleEngineChange">
              <el-radio value="edge">Edge-TTS</el-radio>
              <el-radio value="whisper">Whisper</el-radio>
            </el-radio-group>
          </el-tooltip>
        </div>

        <div class="form-item" v-if="form.enableSubtitles">
          <label class="form-label">{{ t('Font') }}</label>
          <el-select v-model="form.subtitleFont" :placeholder="t('Select font')" class="form-select">
            <el-option label="STHeitiMedium.ttc" value="STHeitiMedium.ttc" />
            <el-option label="MicrosoftYaHeiBold.ttc" value="MicrosoftYaHeiBold.ttc" />
            <el-option label="MicrosoftYaHeiNormal.ttc" value="MicrosoftYaHeiNormal.ttc" />
            <el-option label="STHeitiLight.ttc" value="STHeitiLight.ttc" />
          </el-select>
        </div>
        
        <div class="form-item" v-if="form.enableSubtitles">
          <label class="form-label">{{ t('Position') }}</label>
          <el-select v-model="form.subtitlePosition" :placeholder="t('Select position')" class="form-select">
            <el-option :label="t('Top')" value="top" />
            <el-option :label="t('Middle')" value="middle" />
            <el-option :label="t('Bottom')" value="bottom" />
            <el-option :label="t('Custom')" value="custom" />
          </el-select>
        </div>
        
        <div class="form-item" v-if="form.enableSubtitles && form.subtitlePosition === 'custom'">
          <label class="form-label">{{ t('Custom Position') }} (%)</label>
          <div class="slider-control">
            <el-slider
              v-model="form.subtitleCustomPosition"
              :min="0"
              :max="100"
              :step="1"
              :show-input="true"
              :input-size="'small'"
            />
          </div>
        </div>
        
        <div class="form-item" v-if="form.enableSubtitles">
          <div style="display: flex; justify-content: space-between; gap: 20px;">
            <div style="flex: 1;">
              <label class="form-label">{{ t('Font Color') }}</label>
              <div class="color-picker-container">
                <el-color-picker v-model="form.subtitleColor" show-alpha />
              </div>
            </div>
            <div style="flex: 2;">
              <label class="form-label">{{ t('Font Size') }}</label>
              <el-slider
                v-model="form.subtitleFontSize"
                :min="5"
                :max="100"
                :step="1"
                show-input
              />
            </div>
          </div>
        </div>
        
        <div class="form-item" v-if="form.enableSubtitles">
          <div style="display: flex; justify-content: space-between; gap: 20px;">
            <div style="flex: 1;">
              <label class="form-label">{{ t('Stroke Color') }}</label>
              <div class="color-picker-container">
                <el-color-picker v-model="form.subtitleOutlineColor" show-alpha />
              </div>
            </div>
            <div style="flex: 2;">
              <label class="form-label">{{ t('Stroke Width') }}</label>
              <el-slider
                v-model="form.subtitleOutlineWidth"
                :min="0"
                :max="10"
                :step="0.1"
                show-input
              />
            </div>
          </div>
        </div>
        
        <div class="form-item" v-if="form.enableSubtitles">
          <el-tooltip :content="t('Auto-fit info')" placement="top">
            <el-checkbox v-model="form.autoFit">
              {{ t('Prevent Line Breaks') }}
              <span class="hint-text">({{ t('Auto-fit desc') }})</span>
            </el-checkbox>
          </el-tooltip>
        </div>
        
        <div v-if="form.enableSubtitles" class="preview-section">
          <h3>{{ t('Preview') }} <span v-if="isLoadingPreview" style="font-size:12px;color:#909399;font-weight:normal;">(loading...)</span></h3>
          <div class="preview-container">
            <div class="preview-video-frame" :style="previewFrameStyle">
              <div 
                class="preview-subtitle"
                :style="previewStyle"
                v-show="!previewImageUrl"
              >
                {{ previewText }}
              </div>
              <img 
                v-if="previewImageUrl" 
                :src="previewImageUrl" 
                class="preview-image"
                @error="previewImageUrl = null"
              />
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style>
@font-face {
  font-family: 'Microsoft YaHei Bold';
  src: url('/fonts/MicrosoftYaHeiBold.ttc') format('truetype');
  font-weight: bold;
  font-display: swap;
}

@font-face {
  font-family: 'Microsoft YaHei Normal';
  src: url('/fonts/MicrosoftYaHeiNormal.ttc') format('truetype');
  font-display: swap;
}

@font-face {
  font-family: 'STHeiti Light';
  src: url('/fonts/STHeitiLight.ttc') format('truetype');
  font-weight: 300;
  font-display: swap;
}

@font-face {
  font-family: 'STHeiti Medium';
  src: url('/fonts/STHeitiMedium.ttc') format('truetype');
  font-weight: 500;
  font-display: swap;
}
</style>

<script setup lang="ts">
import { reactive, ref, watch, onMounted, computed } from 'vue';
import { useI18nStore } from '../stores/i18n';
import { useSettingsStore } from '../stores/settings';
import { apiService } from '../services/api';

const i18nStore = useI18nStore();
const t = i18nStore.t;
const settingsStore = useSettingsStore();

const form = reactive({
  enableSubtitles: settingsStore.subtitle.enable,
  subtitleEngine: settingsStore.app.subtitleProvider,
  subtitleFont: settingsStore.subtitle.font,
  subtitlePosition: settingsStore.subtitle.position,
  subtitleCustomPosition: settingsStore.subtitle.customPosition,
  subtitleColor: settingsStore.subtitle.color,
  subtitleFontSize: settingsStore.subtitle.fontSize,
  subtitleOutlineColor: settingsStore.subtitle.outlineColor,
  subtitleOutlineWidth: settingsStore.subtitle.outlineWidth,
  autoFit: settingsStore.subtitle.autoFit,
  subtitleMargin: settingsStore.subtitle.margin
});

const handleSubtitleEngineChange = async (value: string) => {
  settingsStore.updateAppSetting('subtitleProvider', value);
  await settingsStore.saveSubtitleToBackend();
};

const previewImageUrl = ref<string | null>(null);
const isLoadingPreview = ref(false);
let previewTimer: ReturnType<typeof setTimeout> | null = null;
let previewRequestId = 0;

const previewText = '这是一段示例字幕文字\n用于展示字幕效果';

const fontNameMapping: { [key: string]: string } = {
  'MicrosoftYaHeiBold.ttc': 'Microsoft YaHei Bold',
  'MicrosoftYaHeiNormal.ttc': 'Microsoft YaHei Normal',
  'STHeitiLight.ttc': 'STHeiti Light',
  'STHeitiMedium.ttc': 'STHeiti Medium',
};

const previewFrameStyle = computed(() => {
  const aspect = settingsStore.video.aspect;
  const maxDim = 480;
  let width: number;
  let height: number;

  if (aspect === 'portrait' || aspect === 'portrait_9_16') {
    height = maxDim;
    width = Math.round(maxDim * 9 / 16);
  } else if (aspect === 'landscape' || aspect === 'landscape_16_9') {
    width = maxDim;
    height = Math.round(maxDim * 9 / 16);
  } else if (aspect === 'square') {
    width = maxDim;
    height = maxDim;
  } else if (aspect === 'portrait_3_4') {
    height = maxDim;
    width = Math.round(maxDim * 9 / 16);
  } else {
    height = maxDim;
    width = Math.round(maxDim * 9 / 16);
  }

  return {
    backgroundColor: '#000',
    width: `${width}px`,
    height: `${height}px`
  };
});

const previewStyle = computed(() => {
  const subtitleMarginPercent = settingsStore.subtitle.margin * 100;
  const previewHeight = parseInt(previewFrameStyle.value.height);
  // Use correct reference height based on aspect ratio
  const aspect = settingsStore.video.aspect;
  const isPortrait = aspect === 'portrait' || aspect === 'portrait_9_16' || aspect === 'portrait_3_4';
  const refHeight = isPortrait ? 1920 : 1080;
  const scaleFactor = previewHeight / refHeight;
  const scaledFontSize = Math.round(form.subtitleFontSize * scaleFactor);
  const scaledStrokeWidth = Math.max(0, Math.round(form.subtitleOutlineWidth * scaleFactor));

  const maxWidthPercent = 100 - 2 * subtitleMarginPercent;

  let topPosition: string;
  let bottomPosition: string;
  let transform: string;

  if (form.subtitlePosition === 'top') {
    topPosition = `${subtitleMarginPercent}%`;
    bottomPosition = 'auto';
    transform = 'none';
  } else if (form.subtitlePosition === 'bottom') {
    topPosition = 'auto';
    bottomPosition = `${subtitleMarginPercent}%`;
    transform = 'none';
  } else if (form.subtitlePosition === 'custom') {
    const customPos = form.subtitleCustomPosition ?? 80;
    topPosition = `${customPos}%`;
    bottomPosition = 'auto';
    transform = 'translateY(-50%)';
  } else {
    topPosition = '50%';
    bottomPosition = 'auto';
    transform = 'translateY(-50%)';
  }

  const mappedFont = fontNameMapping[form.subtitleFont] || form.subtitleFont;
  let fontFamilyValue = mappedFont;
  
  if (mappedFont.includes('YaHei')) {
    fontFamilyValue = `${mappedFont}, "Microsoft YaHei", "PingFang SC", sans-serif`;
  } else if (mappedFont.includes('Heiti')) {
    fontFamilyValue = `${mappedFont}, "STHeiti", "SimHei", sans-serif`;
  } else {
    fontFamilyValue = `${mappedFont}, sans-serif`;
  }

  return {
    fontFamily: `${fontFamilyValue} !important`,
    color: form.subtitleColor,
    fontSize: `${scaledFontSize}px`,
    lineHeight: '1.2',
    position: 'absolute' as const,
    left: '50%',
    transform: `translateX(-50%) ${transform !== 'none' ? transform : ''}`,
    top: topPosition,
    bottom: bottomPosition,
    textAlign: 'center' as const,
    whiteSpace: 'pre-line' as const,
    maxWidth: `${maxWidthPercent}%`,
    wordBreak: 'break-word' as const,
    textShadow: form.subtitleOutlineWidth > 0 
      ? `${scaledStrokeWidth}px ${scaledStrokeWidth}px 0 ${form.subtitleOutlineColor}, -${scaledStrokeWidth}px -${scaledStrokeWidth}px 0 ${form.subtitleOutlineColor}, ${scaledStrokeWidth}px -${scaledStrokeWidth}px 0 ${form.subtitleOutlineColor}, -${scaledStrokeWidth}px ${scaledStrokeWidth}px 0 ${form.subtitleOutlineColor}`
      : 'none',
  };
});

async function updateSubtitlePreview() {
  if (!form.enableSubtitles) return;
  const reqId = ++previewRequestId;
  isLoadingPreview.value = true;
  try {
    const aspect = settingsStore.video.aspect;
    const res = await apiService.previewSubtitle({
      subtitle_enabled: form.enableSubtitles,
      subtitle_text: previewText,
      font_name: form.subtitleFont,
      font_size: form.subtitleFontSize,
      text_fore_color: form.subtitleColor,
      stroke_color: form.subtitleOutlineColor,
      stroke_width: form.subtitleOutlineWidth,
      subtitle_position: form.subtitlePosition,
      custom_position: form.subtitleCustomPosition ?? 80.0,
      subtitle_auto_fit: form.autoFit,
      subtitle_margin: settingsStore.subtitle.margin,
      video_aspect: aspect,
    });
    if (reqId !== previewRequestId) return;
    if (res.status === 200 && res.data?.preview_path) {
      previewImageUrl.value = `http://localhost:8000${res.data.preview_path}`;
    }
  } catch (e) {
    console.error('[SubtitlePreview] Failed to generate preview:', e);
  } finally {
    if (reqId === previewRequestId) isLoadingPreview.value = false;
  }
}

watch(
  () => ({ ...form }),
  () => {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(updateSubtitlePreview, 300);
  },
  { deep: true }
);

watch(() => form.enableSubtitles, async (newValue) => {
  await settingsStore.updateSubtitleSetting('enable', newValue);
});

watch(() => settingsStore.app.subtitleProvider, (newValue) => {
  form.subtitleEngine = newValue;
});

watch(() => form.subtitleFont, async (newValue) => {
  await settingsStore.updateSubtitleSetting('font', newValue);
});

watch(() => form.subtitlePosition, async (newValue) => {
  await settingsStore.updateSubtitleSetting('position', newValue);
});

watch(() => form.subtitleCustomPosition, async (newValue) => {
  await settingsStore.updateSubtitleSetting('customPosition', newValue);
});

watch(() => form.subtitleColor, async (newValue) => {
  await settingsStore.updateSubtitleSetting('color', newValue);
});

watch(() => form.subtitleFontSize, async (newValue) => {
  await settingsStore.updateSubtitleSetting('fontSize', newValue);
});

watch(() => form.subtitleOutlineColor, async (newValue) => {
  await settingsStore.updateSubtitleSetting('outlineColor', newValue);
});

watch(() => form.subtitleOutlineWidth, async (newValue) => {
  await settingsStore.updateSubtitleSetting('outlineWidth', newValue);
});

watch(() => form.autoFit, async (newValue) => {
  await settingsStore.updateSubtitleSetting('autoFit', newValue);
});

watch(() => form.subtitleMargin, async (newValue) => {
  await settingsStore.updateSubtitleSetting('margin', newValue);
});

watch(() => settingsStore.subtitle, (newSubtitle) => {
  console.log('[SubtitleSettings] Store subtitle changed, updating form:', newSubtitle);
  form.enableSubtitles = newSubtitle.enable;
  form.subtitleFont = newSubtitle.font;
  form.subtitlePosition = newSubtitle.position;
  form.subtitleCustomPosition = newSubtitle.customPosition;
  form.subtitleColor = newSubtitle.color;
  form.subtitleFontSize = newSubtitle.fontSize;
  form.subtitleOutlineColor = newSubtitle.outlineColor;
  form.subtitleOutlineWidth = newSubtitle.outlineWidth;
  form.autoFit = newSubtitle.autoFit;
  form.subtitleMargin = newSubtitle.margin;
}, { deep: true });

onMounted(() => {
  form.enableSubtitles = settingsStore.subtitle.enable;
  form.subtitleEngine = settingsStore.app.subtitleProvider;
  form.subtitleFont = settingsStore.subtitle.font;
  form.subtitlePosition = settingsStore.subtitle.position;
  form.subtitleCustomPosition = settingsStore.subtitle.customPosition;
  form.subtitleColor = settingsStore.subtitle.color;
  form.subtitleFontSize = settingsStore.subtitle.fontSize;
  form.subtitleOutlineColor = settingsStore.subtitle.outlineColor;
  form.subtitleOutlineWidth = settingsStore.subtitle.outlineWidth;
  form.autoFit = settingsStore.subtitle.autoFit;
  form.subtitleMargin = settingsStore.subtitle.margin;
  updateSubtitlePreview();
});

defineExpose({
  form
});
</script>

<style scoped>
.subtitle-settings {
  width: 100%;
}

.card-header {
  margin-bottom: 4px;
}

.settings-form {
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
  font-size: 14px;
  margin-bottom: 4px;
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

.form-input {
  width: 100%;
  padding: 6px 8px;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-input :deep(.el-input) {
  width: 100%;
}

.color-picker-container {
  margin-top: 4px;
}

.hint-text {
  font-size: 12px;
  color: #909399;
}

.slider-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-section {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px dashed #e4e7ed;
}

.preview-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.preview-container {
  display: flex;
  justify-content: center;
}

.preview-video-frame {
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.preview-subtitle {
  color: #ffffff;
  font-family: inherit;
  z-index: 1;
}

.preview-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  z-index: 2;
}
</style>
