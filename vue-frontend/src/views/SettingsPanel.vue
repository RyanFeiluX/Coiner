<template>
  <div class="settings-panel">
    <el-dialog
      v-model="visible"
      :title="t('Settings')"
      width="800px"
      destroy-on-close
    >
      <el-tabs v-model="activeTab" class="settings-tabs">
        <el-tab-pane :label="t('LLM Settings')" name="llm">
          <el-form :model="form" label-width="150px">
            <el-form-item :label="t('LLM Provider')">
              <el-select v-model="form.llmProvider" @change="handleLLMProviderChange">
                <el-option v-for="provider in llmProviders" :key="provider.value" :label="provider.label" :value="provider.value" />
              </el-select>
            </el-form-item>
          </el-form>
          
          <div v-if="llmTips" class="llm-tips">
            <el-alert
              :title="llmTips.title"
              :type="llmTips.type"
              :closable="false"
              show-icon
            >
              <div v-html="llmTips.content"></div>
            </el-alert>
          </div>
          
          <el-form :model="form" label-width="150px">
            <el-form-item>
              <template #label>
                <span>{{ t('API Key') }} <span style="color: red;">*</span></span>
              </template>
              <el-input v-model="form.llmApiKey" type="password" />
            </el-form-item>
            
            <el-form-item :label="t('Base Url')">
              <el-input v-model="form.llmBaseUrl" />
            </el-form-item>
            
            <el-form-item v-if="form.llmProvider !== 'ernie'">
              <template #label>
                <el-tooltip :content="t('Model Name Tooltip')" placement="top">
                  <span>{{ t('Model Name') }}</span>
                </el-tooltip>
              </template>
              <el-input v-model="form.llmModelName" />
            </el-form-item>
            
            <el-form-item :label="t('Secret Key')" v-if="form.llmProvider === 'ernie'">
              <el-input v-model="form.llmSecretKey" type="password" />
            </el-form-item>
            
            <el-form-item :label="t('Account ID')" v-if="form.llmProvider === 'cloudflare'">
              <el-input v-model="form.llmAccountId" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('Video Source Settings')" name="video-source">
          <el-form :model="form" label-position="top">
            <el-form-item>
              <template #label>
                <span v-html="t('Pexels API Key')"></span>
              </template>
              <div v-for="(_, index) in form.pexelsApiKeys" :key="index" class="api-key-input-group">
                <el-input v-model="form.pexelsApiKeys[index]" type="password">
                  <template #append>
                    <el-button 
                      v-if="form.pexelsApiKeys.length > 1" 
                      type="danger" 
                      circle 
                      @click="removePexelsApiKey(index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-input>
              </div>
              <el-button type="primary" plain @click="addPexelsApiKey" class="mt-2">
                <el-icon><Plus /></el-icon>
                {{ t('Add') }}
              </el-button>
            </el-form-item>
            
            <el-form-item>
              <template #label>
                <span v-html="t('Pixabay API Key')"></span>
              </template>
              <div v-for="(_, index) in form.pixabayApiKeys" :key="index" class="api-key-input-group">
                <el-input v-model="form.pixabayApiKeys[index]" type="password">
                  <template #append>
                    <el-button 
                      v-if="form.pixabayApiKeys.length > 1" 
                      type="danger" 
                      circle 
                      @click="removePixabayApiKey(index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-input>
              </div>
              <el-button type="primary" plain @click="addPixabayApiKey" class="mt-2">
                <el-icon><Plus /></el-icon>
                {{ t('Add') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('Whisper Settings')" name="whisper">
          <el-form :model="form" label-width="150px">
            <el-form-item :label="t('Whisper Device')">
              <el-select v-model="form.whisperDevice">
                <el-option :label="t('CPU')" value="CPU" />
                <el-option :label="t('GPU')" value="GPU" />
                <el-option :label="t('Auto')" value="auto" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('Video Encoder Settings')" name="video-encoder">
          <el-form :model="form" label-width="150px">
            <el-form-item :label="t('Video Encoder')">
              <el-select v-model="form.videoEncoder">
                <el-option :label="t('CPU')" value="CPU" />
                <el-option :label="t('GPU')" value="GPU" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('Video Synthesis')" name="video-synthesis">
          <el-form :model="form" label-width="150px">
            <el-form-item :label="t('Silence Prefix')">
              <el-slider
                v-model="form.silenceDuration"
                :min="0.0"
                :max="5.0"
                :step="0.1"
                :show-input="true"
                :input-size="'small'"
              />
            </el-form-item>
            
            <el-form-item :label="t('Host Visible')">
              <el-switch v-model="form.hostVisible" :active-text="t('Visible')" :inactive-text="t('Hidden')" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('Web Search Settings')" name="web-search">
          <el-form :model="form" label-width="150px">
            <el-form-item :label="t('Tavily API Key')">
              <el-input v-model="form.tavilyApiKey" type="password" placeholder="tmpl_xxx" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('TTS Model Settings')" name="tts-model">
          <el-form :model="form" label-width="120px">
            <el-form-item :label="t('TTS Provider')">
              <el-select v-model="form.ttsProvider" style="width: 100%">
                <el-option :label="t('Azure TTS V2')" value="azure-tts-v2" />
                <el-option :label="t('SiliconFlow TTS')" value="siliconflow" />
                <el-option :label="t('Google Gemini TTS')" value="gemini-tts" />
                <el-option :label="t('Coze TTS')" value="coze-tts" />
                <el-option :label="t('Bailian TTS')" value="bailian-tts" />
                <el-option :label="t('Aliyun Bailian Token Plan')" value="bailian-token-plan" />
              </el-select>
            </el-form-item>
          </el-form>

          <!-- Azure TTS V2 -->
          <div v-if="form.ttsProvider === 'azure-tts-v2'" class="tts-provider-config">
            <el-form :model="form" label-width="120px">
              <el-form-item :label="t('Speech Region')">
                <el-input v-model="form.azureSpeechRegion" placeholder="eastasia" />
              </el-form-item>
              <el-form-item :label="t('Speech Key')">
                <el-input v-model="form.azureSpeechKey" type="password" show-password />
              </el-form-item>
            </el-form>
          </div>

          <!-- SiliconFlow TTS -->
          <div v-if="form.ttsProvider === 'siliconflow'" class="tts-provider-config">
            <el-form :model="form" label-width="120px">
              <el-form-item :label="t('SiliconFlow API Key')">
                <el-input v-model="form.siliconflowApiKey" type="password" show-password />
              </el-form-item>
            </el-form>
          </div>

          <!-- Google Gemini TTS -->
          <div v-if="form.ttsProvider === 'gemini-tts'" class="tts-provider-config">
            <el-form :model="form" label-width="120px">
              <el-form-item :label="t('Gemini API Key')">
                <el-input v-model="form.geminiApiKey" type="password" show-password />
              </el-form-item>
            </el-form>
          </div>

          <!-- Coze TTS -->
          <div v-if="form.ttsProvider === 'coze-tts'" class="tts-provider-config">
            <el-form :model="form" label-width="120px">
              <el-form-item :label="t('Coze API Key')">
                <el-input v-model="form.cozeApiKey" type="password" show-password />
              </el-form-item>
            </el-form>
          </div>

          <!-- Bailian TTS -->
          <div v-if="form.ttsProvider === 'bailian-tts'" class="tts-provider-config">
            <el-form :model="form" label-width="120px">
              <el-form-item>
                <template #label>
                  <span>{{ t('Bailian API Key') }} <span style="color: red;">*</span></span>
                </template>
                <el-input v-model="form.bailianApiKey" type="password" show-password />
              </el-form-item>
              <el-form-item :label="t('Bailian TTS Model')">
                <div style="display: flex; align-items: center; gap: 8px; width: 100%">
                  <el-select v-model="form.bailianModelName" style="flex: 1">
                    <el-option-group :label="t('Qwen3-TTS-Flash')">
                      <el-option label="qwen3-tts-flash (Stable)" value="qwen3-tts-flash" />
                      <el-option label="qwen3-tts-flash-2025-11-27" value="qwen3-tts-flash-2025-11-27" />
                      <el-option label="qwen3-tts-flash-2025-09-18" value="qwen3-tts-flash-2025-09-18" />
                    </el-option-group>
                    <el-option-group :label="t('Qwen3-TTS-Instruct-Flash')">
                      <el-option label="qwen3-tts-instruct-flash (Stable)" value="qwen3-tts-instruct-flash" />
                      <el-option label="qwen3-tts-instruct-flash-2026-01-26" value="qwen3-tts-instruct-flash-2026-01-26" />
                    </el-option-group>
                    <el-option-group :label="t('Qwen3-TTS-VD')">
                      <el-option label="qwen3-tts-vd-2026-01-26" value="qwen3-tts-vd-2026-01-26" />
                    </el-option-group>
                    <el-option-group :label="t('Qwen3-TTS-VC')">
                      <el-option label="qwen3-tts-vc-2026-01-22" value="qwen3-tts-vc-2026-01-22" />
                    </el-option-group>
                    <el-option-group :label="t('Qwen-TTS')">
                      <el-option label="qwen-tts (Stable)" value="qwen-tts" />
                      <el-option label="qwen-tts-latest" value="qwen-tts-latest" />
                      <el-option label="qwen-tts-2025-05-22" value="qwen-tts-2025-05-22" />
                      <el-option label="qwen-tts-2025-04-10" value="qwen-tts-2025-04-10" />
                    </el-option-group>
                  </el-select>
                  <el-popover placement="right" :width="400" trigger="click">
                    <template #reference>
                      <el-button :icon="InfoFilled" circle />
                    </template>
                    <div>
                      <p style="font-weight: bold; margin-bottom: 8px;">{{ t('Bailian TTS Model Info') }}</p>
                      <ul style="margin: 0; padding-left: 20px;">
                        <li>{{ t('Qwen3-TTS-Flash Info') }}</li>
                        <li>{{ t('Qwen3-TTS-Instruct-Flash Info') }}</li>
                        <li>{{ t('Qwen3-TTS-VD Info') }}</li>
                        <li>{{ t('Qwen3-TTS-VC Info') }}</li>
                        <li>{{ t('Qwen-TTS Info') }}</li>
                      </ul>
                    </div>
                  </el-popover>
                </div>
              </el-form-item>
            </el-form>
          </div>

          <!-- Aliyun Bailian Token Plan -->
          <div v-if="form.ttsProvider === 'bailian-token-plan'" class="tts-provider-config">
            <el-form :model="form" label-width="120px">
              <el-form-item :label="t('Token Plan API Key')">
                <el-input v-model="form.bailianTokenPlanApiKey" type="password" show-password />
              </el-form-item>
              <el-form-item :label="t('Token Plan TTS Model')">
                <el-select v-model="form.bailianTokenPlanModelName" style="width: 100%">
                  <el-option label="qwen-audio-3.0-tts-plus" value="qwen-audio-3.0-tts-plus" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="t('Cloned Voices Setting')" name="cloned-voices">
          <div class="voice-actions">
            <el-button 
              type="primary" 
              plain 
              size="small" 
              @click="showAddVoiceModal = true"
            >
              <el-icon><Plus /></el-icon>
              {{ t('Add Voice') }}
            </el-button>
            <label class="el-button el-button--success el-button--plain el-button--small ml-2">
              <el-icon><Upload /></el-icon>
              {{ t('Import JSON') }}
              <input 
                type="file" 
                accept=".json" 
                class="voice-file-upload"
                @change="handleFileUpload"
              />
            </label>
          </div>
          
          <div v-if="clonedVoices.length === 0" class="empty-state">
            <el-empty 
              :description="t('No cloned voices configured')"
            />
          </div>
          
          <el-table 
            v-else 
            :data="clonedVoices" 
            border 
            class="mt-4"
            :max-height="300"
          >
            <el-table-column :label="t('Display Name')" prop="displayName" />
            <el-table-column :label="t('Voice ID')" prop="voiceId" width="300" />
            <el-table-column :label="t('Gender')" prop="gender" />
            <el-table-column :label="t('Model')" prop="model" width="200" />
            <el-table-column :label="t('Actions')" width="120">
              <template #default="scope">
                <el-button 
                  size="small" 
                  @click="editVoice(scope.row)"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="deleteVoice(scope.row.voiceId)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
      
      <!-- Add/Edit Voice Modal -->
      <el-dialog 
        v-model="showAddVoiceModal" 
        :title="editingVoice ? t('Edit Voice') : t('Add Cloned Voice')"
        width="500px"
      >
        <el-form :model="voiceForm" label-width="120px">
          <el-form-item :label="t('Display Name')" required>
            <el-input v-model="voiceForm.displayName" />
          </el-form-item>
          <el-form-item :label="t('Voice ID')" required>
            <el-input v-model="voiceForm.voiceId" placeholder="e.g., qwen-tts-vc-xxx" />
          </el-form-item>
          <el-form-item :label="t('Gender')">
            <el-select v-model="voiceForm.gender">
              <el-option :label="t('Male')" value="Male" />
              <el-option :label="t('Female')" value="Female" />
              <el-option :label="t('Unknown')" value="" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('Model')" required>
            <el-input v-model="voiceForm.model" placeholder="e.g., qwen3-tts-vc-2026-01-22" />
          </el-form-item>
          <el-form-item :label="t('Brief')">
            <el-input v-model="voiceForm.brief" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item :label="t('Provider')">
            <el-input v-model="voiceForm.provider" />
          </el-form-item>
          <el-form-item :label="t('Region')">
            <el-input v-model="voiceForm.region" />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button @click="showAddVoiceModal = false">{{ t('Cancel') }}</el-button>
          <el-button type="primary" @click="saveVoice">{{ t('Save') }}</el-button>
        </template>
      </el-dialog>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="visible = false">{{ t('Cancel') }}</el-button>
          <el-button type="primary" @click="saveSettings">{{ t('Save') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, watch } from 'vue';
import { useSettingsStore } from '../stores/settings';
import { useI18nStore } from '../stores/i18n';
import { Delete, Plus, Edit, Upload, InfoFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { apiService } from '../services/api';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'settings-saved'): void;
}>();

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const i18nStore = useI18nStore();
const t = i18nStore.t;

const settingsStore = useSettingsStore();

const activeTab = ref('llm');

// Load settings into form
const loadSettingsToForm = () => {
  form.llmProvider = settingsStore.app.llmProvider;
  
  // Load LLM configuration
  const llmConfig = settingsStore.getLLMConfig(form.llmProvider);
  form.llmApiKey = llmConfig.apiKey || '';
  form.llmBaseUrl = llmConfig.baseUrl || '';
  form.llmModelName = llmConfig.modelName || '';
  
  // Load video source configuration
  const pexelsKeys = settingsStore.getVideoSourceConfig('pexels');
  form.pexelsApiKeys = pexelsKeys.length > 0 ? pexelsKeys : [''];
  
  const pixabayKeys = settingsStore.getVideoSourceConfig('pixabay');
  form.pixabayApiKeys = pixabayKeys.length > 0 ? pixabayKeys : [''];
  
  // Load Whisper configuration
  form.whisperDevice = settingsStore.whisper.device || 'CPU';
  
  // Load video encoder configuration
  form.videoEncoder = settingsStore.app.useGpu ? 'GPU' : 'CPU';
  
  // Load Silence Prefix configuration
  form.silenceDuration = settingsStore.video.silenceDuration;
  
  // Load Host Visible configuration
  form.hostVisible = settingsStore.video.hostVisible;
  
  // Load Tavily API Key
  form.tavilyApiKey = settingsStore.audio.tavilyApiKey || '';
  
  // Load TTS Provider config
  form.ttsProvider = settingsStore.audio.ttsServer || 'bailian-tts';
  form.azureSpeechRegion = settingsStore.audio.speechRegion || '';
  form.azureSpeechKey = settingsStore.audio.speechKey || '';
  form.siliconflowApiKey = settingsStore.audio.siliconflowApiKey || '';
  form.geminiApiKey = settingsStore.audio.geminiApiKey || '';
  form.cozeApiKey = settingsStore.audio.cozeApiKey || '';
  form.bailianApiKey = settingsStore.audio.bailianApiKey || '';
  form.bailianModelName = settingsStore.audio.bailianModelName || 'qwen3-tts-instruct-flash';
  form.bailianTokenPlanApiKey = settingsStore.audio.bailianTokenPlanApiKey || '';
  form.bailianTokenPlanModelName = settingsStore.audio.bailianTokenPlanModelName || 'qwen-audio-3.0-tts-plus';
};

const form = reactive({
  llmProvider: 'openai',
  llmApiKey: '',
  llmBaseUrl: '',
  llmModelName: '',
  llmSecretKey: '',
  llmAccountId: '',
  pexelsApiKeys: [''],
  pixabayApiKeys: [''],
  whisperDevice: 'CPU',
  videoEncoder: 'CPU',
  silenceDuration: 0.3,
  hostVisible: true,
  tavilyApiKey: '',
  ttsProvider: 'bailian-tts',
  azureSpeechRegion: '',
  azureSpeechKey: '',
  siliconflowApiKey: '',
  geminiApiKey: '',
  cozeApiKey: '',
  bailianModelName: 'qwen3-tts-instruct-flash',
  bailianApiKey: '',
  bailianTokenPlanApiKey: '',
  bailianTokenPlanModelName: 'qwen-audio-3.0-tts-plus',
});

// Cloned voices data
const clonedVoices = reactive<Array<{
  voiceId: string;
  displayName: string;
  gender: string;
  model: string;
  brief?: string;
  provider?: string;
  region?: string;
}>>([]);

const showAddVoiceModal = ref(false);
const editingVoice = ref<typeof clonedVoices[0] | null>(null);

const voiceForm = reactive({
  voiceId: '',
  displayName: '',
  gender: '',
  model: '',
  brief: '',
  provider: '',
  region: ''
});

// Cloned voices methods
const loadClonedVoices = async () => {
  try {
    const response = await apiService.getClonedVoices();
    if (response.data && response.data.voices) {
      clonedVoices.splice(0, clonedVoices.length, ...response.data.voices);
    }
  } catch (error) {
    console.error('Failed to load cloned voices:', error);
  }
};

const editVoice = (voice: typeof clonedVoices[0]) => {
  editingVoice.value = voice;
  voiceForm.voiceId = voice.voiceId;
  voiceForm.displayName = voice.displayName;
  voiceForm.gender = voice.gender || '';
  voiceForm.model = voice.model;
  voiceForm.brief = voice.brief || '';
  voiceForm.provider = voice.provider || '';
  voiceForm.region = voice.region || '';
  showAddVoiceModal.value = true;
};

const saveVoice = async () => {
  if (!voiceForm.voiceId || !voiceForm.displayName || !voiceForm.model) {
    ElMessage.error('Voice ID, Display Name, and Model are required');
    return;
  }
  
  try {
    const voiceData = {
      voiceId: voiceForm.voiceId,
      displayName: voiceForm.displayName,
      gender: voiceForm.gender,
      model: voiceForm.model,
      brief: voiceForm.brief,
      provider: voiceForm.provider,
      region: voiceForm.region
    };
    
    const response = await apiService.saveClonedVoice(voiceData);
    if (response.data && response.data.voices) {
      clonedVoices.splice(0, clonedVoices.length, ...response.data.voices);
    }
    
    ElMessage.success(editingVoice.value ? 'Voice updated successfully' : 'Voice added successfully');
    showAddVoiceModal.value = false;
    editingVoice.value = null;
    resetVoiceForm();
  } catch (error: any) {
    console.error('Failed to save voice:', error);
    ElMessage.error('Failed to save voice: ' + (error?.message || 'Unknown error'));
  }
};

const deleteVoice = async (voiceId: string) => {
  try {
    const response = await apiService.deleteClonedVoice(voiceId);
    if (response.data && response.data.voices) {
      clonedVoices.splice(0, clonedVoices.length, ...response.data.voices);
    }
    ElMessage.success('Voice deleted successfully');
  } catch (error: any) {
    console.error('Failed to delete voice:', error);
    ElMessage.error('Failed to delete voice: ' + (error?.message || 'Unknown error'));
  }
};

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  
  if (!file) {
    return;
  }
  
  if (!file.name.endsWith('.json')) {
    ElMessage.error('Please select a JSON file');
    target.value = '';
    return;
  }
  
  try {
    const reader = new FileReader();
    
    reader.onload = async (e) => {
      try {
        const jsonData = e.target?.result as string;
        const response = await apiService.importClonedVoices(jsonData);
        
        if (response.data && response.data.voices) {
          clonedVoices.splice(0, clonedVoices.length, ...response.data.voices);
        }
        
        ElMessage.success('Voices imported successfully');
      } catch (error: any) {
        console.error('Failed to import voices:', error);
        ElMessage.error('Failed to import voices: ' + (error?.message || 'Unknown error'));
      }
    };
    
    reader.onerror = () => {
      ElMessage.error('Failed to read file');
    };
    
    reader.readAsText(file);
  } catch (error: any) {
    console.error('Failed to handle file:', error);
    ElMessage.error('Failed to process file: ' + (error?.message || 'Unknown error'));
  }
  
  target.value = '';
};

const resetVoiceForm = () => {
  voiceForm.voiceId = '';
  voiceForm.displayName = '';
  voiceForm.gender = '';
  voiceForm.model = '';
  voiceForm.brief = '';
  voiceForm.provider = '';
  voiceForm.region = '';
};

// API Key management methods
const addPexelsApiKey = () => {
  form.pexelsApiKeys.push('');
};

const removePexelsApiKey = (index: number) => {
  if (form.pexelsApiKeys.length > 1) {
    form.pexelsApiKeys.splice(index, 1);
  }
};

const addPixabayApiKey = () => {
  form.pixabayApiKeys.push('');
};

const removePixabayApiKey = (index: number) => {
  if (form.pixabayApiKeys.length > 1) {
    form.pixabayApiKeys.splice(index, 1);
  }
};

const llmProviders = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Moonshot', value: 'moonshot' },
  { label: 'Azure', value: 'azure' },
  { label: 'Qwen', value: 'qwen' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'ModelScope', value: 'modelscope' },
  { label: 'Gemini', value: 'gemini' },
  { label: 'Ollama', value: 'ollama' },
  { label: 'G4f', value: 'g4f' },
  { label: 'OneAPI', value: 'oneapi' },
  { label: 'Cloudflare', value: 'cloudflare' },
  { label: 'ERNIE', value: 'ernie' },
  { label: 'Pollinations', value: 'pollinations' }
];

const llmTips = computed(() => {
  const provider = form.llmProvider;
  let title = '';
  let content = '';
  
  switch (provider) {
    case 'deepseek':
      title = t('DeepSeek Configuration');
      content = `
        <p>${t('API Key')}: ${t('DeepSeek API Key Tip').replace('API Key: ', '')}</p>
        <p>${t('Base Url')}: ${t('DeepSeek Base Url Tip').replace('Base Url: ', '')}</p>
        <p>${t('Model Name')}: ${t('DeepSeek Model Name Tip').replace('Model Name: ', '')}</p>
      `;
      break;
    case 'moonshot':
      title = t('Moonshot Configuration');
      content = `
        <p>${t('API Key')}: ${t('Moonshot API Key Tip').replace('API Key: ', '')}</p>
        <p>${t('Base Url')}: ${t('Moonshot Base Url Tip').replace('Base Url: ', '')}</p>
        <p>${t('Model Name')}: ${t('Moonshot Model Name Tip').replace('Model Name: ', '')}</p>
      `;
      break;
    case 'openai':
      title = t('OpenAI Configuration');
      content = `
        <p>${t('OpenAI VPN Tip')}</p>
        <p>${t('API Key')}: ${t('OpenAI API Key Tip').replace('API Key: ', '')}</p>
        <p>${t('Base Url')}: ${t('OpenAI Base Url Tip').replace('Base Url: ', '')}</p>
        <p>${t('Model Name')}: ${t('OpenAI Model Name Tip').replace('Model Name: ', '')}</p>
      `;
      break;
    case 'ollama':
      title = t('Ollama Configuration');
      content = `
        <p>${t('API Key')}: ${t('Ollama API Key Tip').replace('API Key: ', '')}</p>
        <p>${t('Base Url')}: ${t('Ollama Base Url Tip').replace('Base Url: ', '')}</p>
        <p>- ${t('Ollama Base Url Tip 2')}</p>
        <p>- ${t('Ollama Base Url Tip 3')}</p>
        <p>${t('Model Name')}: ${t('Ollama Model Name Tip').replace('Model Name: ', '')}</p>
      `;
      break;
    default:
      title = t('LLM Configuration');
      content = `
        <p>${t('API Key')}: ${t('Please Enter LLM API Key')}</p>
        <p>${t('Base Url')}: ${t('Base Url Tooltip')}</p>
        <p>${t('Model Name')}: ${t('Model Name Tooltip')}</p>
      `;
  }
  
  return {
    title: title,
    type: 'info',
    content: content
  };
});

const handleLLMProviderChange = () => {
  // Set default values based on selected LLM provider
  const provider = form.llmProvider;
  
  switch (provider) {
    case 'ollama':
      form.llmModelName = 'qwen:7b';
      form.llmBaseUrl = 'http://localhost:11434/v1';
      break;
    case 'openai':
      form.llmModelName = 'gpt-3.5-turbo';
      form.llmBaseUrl = '';
      break;
    case 'moonshot':
      form.llmModelName = 'moonshot-v1-8k';
      form.llmBaseUrl = 'https://api.moonshot.cn/v1';
      break;
    case 'deepseek':
      form.llmModelName = 'deepseek-chat';
      form.llmBaseUrl = 'https://api.deepseek.com';
      break;
    case 'qwen':
      form.llmModelName = 'qwen-max';
      form.llmBaseUrl = '';
      break;
    case 'gemini':
      form.llmModelName = 'gemini-1.0-pro';
      form.llmBaseUrl = '';
      break;
    case 'modelscope':
      form.llmModelName = 'Qwen/Qwen3-32B';
      form.llmBaseUrl = 'https://api-inference.modelscope.cn/v1/';
      break;
    case 'g4f':
      form.llmModelName = 'gpt-3.5-turbo';
      form.llmBaseUrl = '';
      break;
    case 'oneapi':
      form.llmModelName = 'claude-3-5-sonnet-20240620';
      form.llmBaseUrl = '';
      break;
    default:
      form.llmModelName = '';
      form.llmBaseUrl = '';
  }
};

const saveSettings = async () => {
  try {
    // Save settings to state management
    settingsStore.updateAppSetting('llmProvider', form.llmProvider);

    // Save LLM configuration
    settingsStore.updateLLMSetting(form.llmProvider, 'apiKey', form.llmApiKey);
    settingsStore.updateLLMSetting(form.llmProvider, 'baseUrl', form.llmBaseUrl);
    if (form.llmProvider !== 'ernie') {
      settingsStore.updateLLMSetting(form.llmProvider, 'modelName', form.llmModelName);
    }

    // Save video source configuration
    const pexelsKeys = form.pexelsApiKeys.map(key => key.trim()).filter(Boolean);
    const pixabayKeys = form.pixabayApiKeys.map(key => key.trim()).filter(Boolean);
    settingsStore.updateVideoSourceSetting('pexels', pexelsKeys);
    settingsStore.updateVideoSourceSetting('pixabay', pixabayKeys);

    // Save Whisper configuration
    settingsStore.updateWhisperSetting('device', form.whisperDevice);

    // Save video encoder configuration
    settingsStore.updateAppSetting('useGpu', form.videoEncoder === 'GPU');
    
    // Save Silence Prefix configuration
    settingsStore.updateVideoSetting('silenceDuration', form.silenceDuration);
    
    // Save Host Visible configuration
    settingsStore.updateVideoSetting('hostVisible', form.hostVisible);
    
    // Save Tavily API Key
    settingsStore.updateAudioSetting('tavilyApiKey', form.tavilyApiKey);
    
    // Save TTS Provider config
    settingsStore.updateAudioSetting('ttsServer', form.ttsProvider);
    settingsStore.updateAudioSetting('speechRegion', form.azureSpeechRegion);
    settingsStore.updateAudioSetting('speechKey', form.azureSpeechKey);
    settingsStore.updateAudioSetting('siliconflowApiKey', form.siliconflowApiKey);
    settingsStore.updateAudioSetting('geminiApiKey', form.geminiApiKey);
    settingsStore.updateAudioSetting('cozeApiKey', form.cozeApiKey);
    settingsStore.updateAudioSetting('bailianApiKey', form.bailianApiKey);
    settingsStore.updateAudioSetting('bailianModelName', form.bailianModelName);
    settingsStore.updateAudioSetting('bailianTokenPlanApiKey', form.bailianTokenPlanApiKey);
    settingsStore.updateAudioSetting('bailianTokenPlanModelName', form.bailianTokenPlanModelName);

    // Build app config based on LLM provider
    const appConfig: Record<string, any> = {
      llm_provider: form.llmProvider,
      pexels_api_keys: pexelsKeys,
      pixabay_api_keys: pixabayKeys,
      host_visible: form.hostVisible
    };

    // Add LLM specific configs based on provider
    switch (form.llmProvider) {
      case 'openai':
        appConfig.openai_api_key = form.llmApiKey;
        appConfig.openai_base_url = form.llmBaseUrl;
        appConfig.openai_model_name = form.llmModelName;
        break;
      case 'moonshot':
        appConfig.moonshot_api_key = form.llmApiKey;
        appConfig.moonshot_base_url = form.llmBaseUrl;
        appConfig.moonshot_model_name = form.llmModelName;
        break;
      case 'deepseek':
        appConfig.deepseek_api_key = form.llmApiKey;
        appConfig.deepseek_base_url = form.llmBaseUrl;
        appConfig.deepseek_model_name = form.llmModelName;
        break;
    }

    // Build video config
    const videoConfig: Record<string, any> = {
      use_gpu: form.videoEncoder === 'GPU',
      silence_duration: form.silenceDuration
    };

    // Prepare config object to send to backend - create plain object to avoid circular references
    const configToSave = JSON.parse(JSON.stringify({
      app: appConfig,
      video: videoConfig,
      whisper: {
        device: form.whisperDevice
      },
      azure: {
        speech_region: form.azureSpeechRegion,
        speech_key: form.azureSpeechKey
      },
      siliconflow: {
        api_key: form.siliconflowApiKey
      },
      gemini: {
        api_key: form.geminiApiKey
      },
      coze: {
        api_key: form.cozeApiKey
      },
      bailian: {
        api_key: form.bailianApiKey,
        model_name: form.bailianModelName
      },
      bailian_token_plan: {
        api_key: form.bailianTokenPlanApiKey,
        model_name: form.bailianTokenPlanModelName
      },
      tavily: {
        api_key: form.tavilyApiKey
      }
    }));

    // Send config to backend
    const response = await apiService.updateConfig(configToSave);
    console.log('[saveSettings] Response:', response.status, response.data);

    // Save to local storage
    settingsStore.saveToLocalStorage();

    // Show success message
    ElMessage.success(t('Settings saved successfully'));

    // Close dialog
    visible.value = false;

    // Trigger settings saved event
    emit('settings-saved');
  } catch (error: any) {
    console.error('Failed to save settings:', error?.message || error);
    ElMessage.error(t('Failed to save settings') + ': ' + (error?.message || 'Unknown error'));
  }
};

// Watch for dialog opening to reload the form
watch(() => props.visible, async (newValue) => {
  if (newValue) {
    try {
      await settingsStore.fetchConfig();
      loadSettingsToForm();
      await loadClonedVoices();
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }
});

onMounted(async () => {
  try {
    await settingsStore.fetchConfig();
    loadSettingsToForm();
    await loadClonedVoices();
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
});
</script>

<style scoped>
.settings-panel {
  width: 100%;
}

.settings-tabs {
  margin-top: 8px;
}

.settings-tabs :deep(.el-tabs__content) {
  padding: 16px 8px;
}

.settings-tabs :deep(.el-tab-pane) {
  max-height: 400px;
  overflow-y: auto;
}

.mt-4 {
  margin-top: 16px;
}

.llm-tips {
  margin-top: 16px;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.api-key-input-group {
  margin-bottom: 12px;
  width: 100%;
}

.api-key-input-group:last-of-type {
  margin-bottom: 12px;
}

.api-key-input-group .el-input {
  width: 100%;
}

.el-input__inner {
  background-color: #f5f5f5;
  border-color: #d9d9d9;
}

.llm-tips {
  margin: 16px 0;
}

.llm-tips .el-alert {
  background-color: #e6f7ff;
  border-color: #91d5ff;
  border-radius: 4px;
}

.mt-2 {
  margin-top: 8px;
}

.voice-file-upload {
  display: none;
}

.voice-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tts-provider-config {
  margin-top: 16px;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
}
</style>