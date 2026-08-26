import { defineStore } from 'pinia';
import { apiService } from '../services/api';

interface LLMConfig {
  apiKey: string;
  baseUrl: string;
  modelName: string;
}

interface LLMConfigs {
  [key: string]: LLMConfig;
  openai: LLMConfig;
  moonshot: LLMConfig;
  deepseek: LLMConfig;
}

interface TitleSettings {
  enabled: boolean;
  text: string;
  duration: number;
  font: string;
  fontSize: number;
  color: string;
  strokeColor: string;
  strokeWidth: number;
  backgroundColor: string;
  position: string;
  margin: number;
  marginLeft: number;
  marginRight: number;
  animation: string;
  animationDuration: number;
  backgroundOverlay: boolean;
  overlayColor: string;
  style: string;
  align: string;
}

interface VideoSettings {
  source: string;
  concatMode: string;
  transitionMode: string;
  aspect: string;
  clipDuration: number;
  count: number;
  style: string;
  quality: string;
  bitrate: string;
  brightness: number;
  contrast: number;
  outputBgColor: string;
  introVideoBgType: string;
  introVideoBgBlur: number;
  introVideoBgColor: string;
  silenceDuration: number;
  hostVisible: boolean;
  localFiles: Array<{ name: string; url?: string; status?: string; uid: string }>;
  title: TitleSettings;
}

interface AudioSettings {
  ttsServer: string;
  speechSynthesis: string;
  speechRegion: string;
  speechKey: string;
  siliconflowApiKey: string;
  cozeApiKey: string;
  qwenApiKey: string;
  qwenModelName: string;
  geminiApiKey: string;
  bailianTokenPlanApiKey: string;
  bailianTokenPlanModelName: string;
  bailianTokenPlanBaseUrl: string;
  tavilyApiKey: string;
  voiceEmotion: string;
  speechVolume: string;
  speechRate: string;
  backgroundMusic: string;
  backgroundMusicVolume: string;
}

interface SubtitleSettings {
  enable: boolean;
  font: string;
  position: string;
  customPosition: number;
  color: string;
  fontSize: number;
  outlineColor: string;
  outlineWidth: number;
  autoFit: boolean;
  margin: number;
}

interface AppSettings {
  llmProvider: string;
  subtitleProvider: string;
  videoSource: string;
  useGpu: boolean;
}

interface VideoSources {
  pexelsApiKeys: string[];
  pixabayApiKeys: string[];
}

interface WhisperSettings {
  device: string;
}

interface UISettings {
  language: string;
  hideLog: boolean;
}

interface VersionInfo {
  name: string;
  version: string;
}

type BackendStatus = 'unknown' | 'checking' | 'online' | 'offline';
type LocallensStatus = 'unknown' | 'online' | 'offline';

export const useSettingsStore = defineStore('settings', {
  state: (): {
    app: AppSettings;
    llm: LLMConfigs;
    videoSources: VideoSources;
    whisper: WhisperSettings;
    ui: UISettings;
    video: VideoSettings;
    audio: AudioSettings;
    subtitle: SubtitleSettings;
    version: VersionInfo | null;
    backendStatus: BackendStatus;
    lastHealthCheck: number;
    locallensStatus: LocallensStatus;
    locallensBaseUrl: string;
    locallensEnabled: boolean;
    _locallensTimer: number | null;
  } => ({
    // Version information
    version: null,
    // Backend health status
    backendStatus: 'unknown',
    lastHealthCheck: 0,
    // LocalLens external server status
    locallensStatus: 'unknown',
    locallensBaseUrl: '',
    locallensEnabled: false,
    _locallensTimer: null,
    // App settings
    app: {
      llmProvider: 'openai',
      subtitleProvider: 'edge',
      videoSource: 'pexels',
      useGpu: false,
    },
    
    // Video settings
        video: {
          source: 'pexels',
          concatMode: 'sequential',
          transitionMode: 'none',
          aspect: 'landscape',
          clipDuration: 3,
          count: 1,
          style: 'none',
          quality: 'ultra',
          bitrate: '20M',
          brightness: 1.0,
          contrast: 1.0,
          outputBgColor: 'black',
          introVideoBgType: 'solid',
          introVideoBgBlur: 15,
          introVideoBgColor: 'black',
          silenceDuration: 0.3,
          hostVisible: true,
          localFiles: [],
          title: {
            enabled: false,
            text: '',
            duration: 3.0,
            font: 'MicrosoftYaHeiBold.ttc',
            fontSize: 72,
            color: '#FFFFFF',
            strokeColor: '#000000',
            strokeWidth: 2.0,
            backgroundColor: 'transparent',
            position: 'center',
            margin: 0.05,
            marginLeft: 0.05,
            marginRight: 0.05,
            animation: 'none',
            animationDuration: 0.5,
            backgroundOverlay: false,
            overlayColor: 'rgba(0,0,0,0.5)',
            style: 'classic',
            align: 'center'
          }
        },
    
    // Audio settings
    audio: {
      ttsServer: 'azure-tts-v1',
      speechSynthesis: '',
      speechRegion: '',
      speechKey: '',
      siliconflowApiKey: '',
      cozeApiKey: '',
      qwenApiKey: '',
      qwenModelName: 'qwen3-tts-flash',
      geminiApiKey: '',
      bailianTokenPlanApiKey: '',
      bailianTokenPlanModelName: 'qwen-audio-3.0-tts-plus',
      bailianTokenPlanBaseUrl: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',
      tavilyApiKey: '',
      voiceEmotion: '',
      speechVolume: '1.0',
      speechRate: '1.0',
      backgroundMusic: 'none',
      backgroundMusicVolume: '0.2'
    },
    
    // Subtitle settings
    subtitle: {
      enable: true,
      font: 'MicrosoftYaHeiBold.ttc',
      position: 'custom',
      customPosition: 80,
      color: '#FFFF00',
      fontSize: 60,
      outlineColor: '#000000',
      outlineWidth: 1.5,
      autoFit: false,
      margin: 0.05
    },
    
    // LLM configuration
    llm: {
      openai: {
        apiKey: '',
        baseUrl: '',
        modelName: 'gpt-3.5-turbo'
      },
      moonshot: {
        apiKey: '',
        baseUrl: 'https://api.moonshot.cn/v1',
        modelName: 'moonshot-v1-8k'
      },
      deepseek: {
        apiKey: '',
        baseUrl: 'https://api.deepseek.com',
        modelName: 'deepseek-chat'
      }
    },
    
    // Video source configuration
    videoSources: {
      pexelsApiKeys: [],
      pixabayApiKeys: []
    },
    
    // Whisper configuration
    whisper: {
      device: 'CPU'
    },
    
    // UI configuration
    ui: {
      language: 'zh',
      hideLog: false
    }
  }),
  
  getters: {
    getLLMConfig: (state) => (provider: string) => {
      return state.llm[provider as keyof typeof state.llm] || {};
    },
    
    getVideoSourceConfig: (state) => (source: string) => {
      if (source === 'pexels') {
        return state.videoSources.pexelsApiKeys;
      } else if (source === 'pixabay') {
        return state.videoSources.pixabayApiKeys;
      }
      return [];
    },

    locallensAvailable: (state): boolean => {
      return state.locallensStatus === 'online';
    },
  },
  
  actions: {
    updateAppSetting<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
      this.app[key] = value;
    },
    
    updateLLMSetting<P extends keyof LLMConfigs, K extends keyof LLMConfig>(provider: P, key: K, value: LLMConfig[K]) {
      if (this.llm[provider]) {
        this.llm[provider][key] = value;
      }
    },
    
    updateVideoSourceSetting(source: string, keys: string[]) {
      if (source === 'pexels') {
        this.videoSources.pexelsApiKeys = keys;
      } else if (source === 'pixabay') {
        this.videoSources.pixabayApiKeys = keys;
      }
    },
    
    updateWhisperSetting<K extends keyof WhisperSettings>(key: K, value: WhisperSettings[K]) {
      this.whisper[key] = value;
    },
    
    updateUISetting<K extends keyof UISettings>(key: K, value: UISettings[K]) {
      this.ui[key] = value;
    },
    
    updateVideoSetting<K extends keyof VideoSettings>(key: K, value: VideoSettings[K]) {
      this.video[key] = value;
      this.saveToLocalStorage();
    },
    
    async updateTitleSetting<K extends keyof TitleSettings>(key: K, value: TitleSettings[K]) {
      this.video.title[key] = value;
      this.saveToLocalStorage();
      await this.saveTitleToBackend();
    },

    async saveTitleToBackend() {
      console.log('[SettingsStore] Saving title settings to backend...');
      try {
        const titleConfig = {
          title: {
            title_enabled: this.video.title.enabled,
            title_text: this.video.title.text,
            title_duration: this.video.title.duration,
            title_font_name: this.video.title.font,
            title_font_size: this.video.title.fontSize,
            title_text_color: this.video.title.color,
            title_stroke_color: this.video.title.strokeColor,
            title_stroke_width: this.video.title.strokeWidth,
            title_background_color: this.video.title.backgroundColor,
            title_position: this.video.title.position,
            title_margin: this.video.title.margin,
            title_margin_left: this.video.title.marginLeft,
            title_margin_right: this.video.title.marginRight,
            title_animation: this.video.title.animation,
            title_animation_duration: this.video.title.animationDuration,
            title_background_overlay: this.video.title.backgroundOverlay,
            title_overlay_color: this.video.title.overlayColor,
            title_style: this.video.title.style,
            title_align: this.video.title.align,
          }
        };
        console.log('[SettingsStore] Sending config:', JSON.stringify(titleConfig, null, 2));
        const response = await apiService.updateConfig(titleConfig);
        console.log('[SettingsStore] Title settings saved successfully:', response);
      } catch (error) {
        console.error('[SettingsStore] Failed to save title settings to backend:', error);
        throw error;
      }
    },
    
    updateAudioSetting<K extends keyof AudioSettings>(key: K, value: AudioSettings[K]) {
      this.audio[key] = value;
      this.saveToLocalStorage();
    },
    
    async updateSubtitleSetting<K extends keyof SubtitleSettings>(key: K, value: SubtitleSettings[K]) {
      this.subtitle[key] = value;
      this.saveToLocalStorage();
      await this.saveSubtitleToBackend();
    },
    
    async saveSubtitleToBackend() {
      console.log('[SettingsStore] Saving subtitle settings to backend...');
      try {
        const subtitleConfig = {
          app: {
            subtitle_provider: this.app.subtitleProvider,
          },
          subtitle: {
            subtitle_enabled: this.subtitle.enable,
            subtitle_position: this.subtitle.position,
            subtitle_custom_position: this.subtitle.customPosition ?? 70.0,
            subtitle_margin: this.subtitle.margin,
            subtitle_auto_fit: this.subtitle.autoFit,
            font_name: this.subtitle.font,
            text_fore_color: this.subtitle.color,
            font_size: this.subtitle.fontSize,
            stroke_color: this.subtitle.outlineColor,
            stroke_width: this.subtitle.outlineWidth,
          }
        };
        console.log('[SettingsStore] Sending config:', JSON.stringify(subtitleConfig, null, 2));
        const response = await apiService.updateConfig(subtitleConfig);
        console.log('[SettingsStore] Subtitle settings saved successfully:', response);
      } catch (error) {
        console.error('[SettingsStore] Failed to save subtitle settings to backend:', error);
        throw error;
      }
    },
    
    loadFromLocalStorage() {
      const savedSettings = localStorage.getItem('coiner-settings');
      if (savedSettings) {
        try {
          const parsed = JSON.parse(savedSettings);
          Object.assign(this, parsed);
        } catch (e) {
          console.error('Failed to load settings from localStorage:', e);
        }
      }
    },
    
    saveToLocalStorage() {
      const dataToSave = {
        app: this.app,
        llm: this.llm,
        videoSources: this.videoSources,
        whisper: this.whisper,
        ui: this.ui,
        video: this.video,
        audio: this.audio,
        subtitle: this.subtitle,
        version: this.version
      };
      localStorage.setItem('coiner-settings', JSON.stringify(dataToSave));
    },

    async checkBackendHealth(): Promise<boolean> {
      this.backendStatus = 'checking';
      try {
        console.log('Checking backend health at:', new Date().toLocaleString());
        const response = await apiService.ping();
        console.log('Backend ping response:', response);
        this.backendStatus = 'online';
        this.lastHealthCheck = Date.now();
        console.log('Backend is online');
        return true;
      } catch (error: any) {
        console.error('Backend health check failed:', error);
        console.error('Error details:', {
          message: error.message,
          stack: error.stack,
          response: error.response,
          request: error.request,
          status: error.response?.status
        });
        this.backendStatus = 'offline';
        console.warn('Backend is offline');
        return false;
      }
    },

    async ensureBackendOnline(): Promise<boolean> {
      if (this.backendStatus === 'online') {
        return true;
      }
      return await this.checkBackendHealth();
    },

    async fetchLocallensStatus(): Promise<boolean> {
      try {
        const response = await apiService.getLocallensStatus();
        const data = response?.data;
        this.locallensStatus = data && data.available ? 'online' : 'offline';
        if (data?.base_url) {
          this.locallensBaseUrl = data.base_url;
        }
        if (typeof data?.enabled === 'boolean') {
          this.locallensEnabled = data.enabled;
        }
        return this.locallensStatus === 'online';
      } catch (error) {
        console.warn('Failed to fetch LocalLens status:', error);
        this.locallensStatus = 'offline';
        return false;
      }
    },

    startLocallensPolling(intervalMs: number = 10000) {
      this.stopLocallensPolling();
      this.fetchLocallensStatus();
      this._locallensTimer = window.setInterval(() => this.fetchLocallensStatus(), intervalMs);
    },

    stopLocallensPolling() {
      if (this._locallensTimer) {
        clearInterval(this._locallensTimer);
        this._locallensTimer = null;
      }
    },
    
    async fetchVersion() {
      if (!(await this.ensureBackendOnline())) {
        console.warn('Backend is offline, skipping fetchVersion');
        return;
      }
      try {
        const versionInfo = await apiService.getVersion();
        this.version = {
          name: versionInfo.name || 'Coiner',
          version: versionInfo.version || '0.0.0'
        };
      } catch (error: any) {
        console.error('Failed to fetch version:', error);
        if (error.response?.status === 404) {
          this.backendStatus = 'offline';
        }
        this.version = {
          name: 'Coiner',
          version: '0.0.0'
        };
      }
    },

    async fetchConfig() {
      console.log('[SettingsStore] fetchConfig called');
      if (!(await this.ensureBackendOnline())) {
        console.warn('Backend is offline, skipping fetchConfig');
        return;
      }
      try {
        console.log('[SettingsStore] Fetching config from backend...');
        console.log('[SettingsStore] API Base URL:', 'http://localhost:8000/api/v1');
        const response = await apiService.getConfig();
        console.log('[SettingsStore] Config response status:', response.status);
        console.log('[SettingsStore] Config response data:', response.data);
        if (response.status === 200 && response.data) {
          const data = response.data;
          console.log('Config data:', data);

            if (data.ui) {
                if (data.ui.language) {
                    this.ui.language = data.ui.language;
                    console.log('Updated language:', this.ui.language);
                }
                if (typeof data.ui.hide_log === 'boolean') {
                    this.ui.hideLog = data.ui.hide_log;
                    console.log('Updated hideLog:', this.ui.hideLog);
                }
                console.log('[SettingsStore] === Config UI Data ===');
                console.log('[SettingsStore] config.ui:', data.ui);
            }

            if (data.audio) {
                console.log('[SettingsStore] === Config Audio Data ===');
                console.log('[SettingsStore] config.audio:', data.audio);
                
                if (data.audio.tts_server) {
                    this.audio.ttsServer = data.audio.tts_server;
                    console.log('[SettingsStore] Updated ttsServer from config.audio:', this.audio.ttsServer);
                } else {
                    console.log('[SettingsStore] tts_server not found in config.audio');
                }
                if (data.audio.voice_name) {
                    this.audio.speechSynthesis = data.audio.voice_name;
                    console.log('[SettingsStore] Updated speechSynthesis from config.audio:', this.audio.speechSynthesis.substring(0, 100) + '...');
                } else {
                    console.log('[SettingsStore] voice_name not found in config.audio');
                }
                if (data.audio.voice_volume !== undefined) {
                    this.audio.speechVolume = String(data.audio.voice_volume);
                    console.log('[SettingsStore] Updated speechVolume from config.audio:', this.audio.speechVolume);
                }
                if (data.audio.voice_rate !== undefined) {
                    this.audio.speechRate = String(data.audio.voice_rate);
                    console.log('[SettingsStore] Updated speechRate from config.audio:', this.audio.speechRate);
                }
                if (data.audio.voice_emotion !== undefined) {
                    this.audio.voiceEmotion = data.audio.voice_emotion;
                    console.log('[SettingsStore] Updated voiceEmotion from config.audio:', this.audio.voiceEmotion);
                }
                if (data.audio.bgm_type !== undefined) {
                    const bgmType = data.audio.bgm_type === '' ? 'none' : data.audio.bgm_type;
                    this.audio.backgroundMusic = bgmType;
                    console.log('[SettingsStore] Updated backgroundMusic from config.audio:', this.audio.backgroundMusic);
                }
                if (data.audio.bgm_volume !== undefined) {
                    this.audio.backgroundMusicVolume = String(data.audio.bgm_volume);
                    console.log('[SettingsStore] Updated backgroundMusicVolume from config.audio:', this.audio.backgroundMusicVolume);
                }
            }

            if (data.subtitle) {
                console.log('[SettingsStore] === Config Subtitle Data ===');
                console.log('[SettingsStore] config.subtitle:', data.subtitle);
                
                if (typeof data.subtitle.subtitle_enabled === 'boolean') {
                  this.subtitle.enable = data.subtitle.subtitle_enabled;
                  console.log('[SettingsStore] Updated subtitle.enable from config.subtitle:', this.subtitle.enable);
                }
                if (data.subtitle.subtitle_position) {
                  this.subtitle.position = data.subtitle.subtitle_position;
                  console.log('[SettingsStore] Updated subtitle.position from config.subtitle:', this.subtitle.position);
                }
                if (data.subtitle.subtitle_custom_position !== undefined) {
                  this.subtitle.customPosition = Number(data.subtitle.subtitle_custom_position) ?? 80;
                  console.log('[SettingsStore] Updated subtitle.customPosition from config.subtitle:', this.subtitle.customPosition);
                }
                if (data.subtitle.subtitle_margin !== undefined) {
                  this.subtitle.margin = Number(data.subtitle.subtitle_margin);
                  console.log('[SettingsStore] Updated subtitle.margin from config.subtitle:', this.subtitle.margin);
                }
                if (typeof data.subtitle.subtitle_auto_fit === 'boolean') {
                  this.subtitle.autoFit = data.subtitle.subtitle_auto_fit;
                  console.log('[SettingsStore] Updated subtitle.autoFit from config.subtitle:', this.subtitle.autoFit);
                }
                if (data.subtitle.font_name) {
                  this.subtitle.font = data.subtitle.font_name;
                  console.log('[SettingsStore] Updated subtitle.font from config.subtitle:', this.subtitle.font);
                }
                if (data.subtitle.text_fore_color) {
                  this.subtitle.color = data.subtitle.text_fore_color;
                  console.log('[SettingsStore] Updated subtitle.color from config.subtitle:', this.subtitle.color);
                }
                if (typeof data.subtitle.text_background_color !== 'undefined') {
                  console.log('[SettingsStore] text_background_color from config.subtitle:', data.subtitle.text_background_color);
                }
                if (data.subtitle.font_size !== undefined) {
                  this.subtitle.fontSize = Number(data.subtitle.font_size);
                  console.log('[SettingsStore] Updated subtitle.fontSize from config.subtitle:', this.subtitle.fontSize);
                }
                if (data.subtitle.stroke_color) {
                  this.subtitle.outlineColor = data.subtitle.stroke_color;
                  console.log('[SettingsStore] Updated subtitle.outlineColor from config.subtitle:', this.subtitle.outlineColor);
                }
                if (data.subtitle.stroke_width !== undefined) {
                  this.subtitle.outlineWidth = Number(data.subtitle.stroke_width);
                  console.log('[SettingsStore] Updated subtitle.outlineWidth from config.subtitle:', this.subtitle.outlineWidth);
                }
            }

            if (data.video) {
                if (data.video.output_bg_color) {
                  this.video.outputBgColor = data.video.output_bg_color;
                  console.log('[SettingsStore] Updated video.outputBgColor from config.video:', this.video.outputBgColor);
                }
            }

            if (data.title) {
            // Load title settings from config.title
            console.log('[SettingsStore] === Config Title Data ===');
            console.log('[SettingsStore] config.title:', data.title);
            if (typeof data.title.title_enabled === 'boolean') {
              this.video.title.enabled = data.title.title_enabled;
              console.log('[SettingsStore] Updated video.title.enabled from config.title:', this.video.title.enabled);
            }
            if (data.title.title_text !== undefined) {
              this.video.title.text = data.title.title_text;
              console.log('[SettingsStore] Updated video.title.text from config.title:', this.video.title.text);
            }
            if (data.title.title_duration !== undefined) {
              this.video.title.duration = Number(data.title.title_duration);
              console.log('[SettingsStore] Updated video.title.duration from config.title:', this.video.title.duration);
            }
            if (data.title.title_font_name !== undefined) {
              this.video.title.font = data.title.title_font_name;
              console.log('[SettingsStore] Updated video.title.font from config.title:', this.video.title.font);
            }
            if (data.title.title_font_size !== undefined) {
              this.video.title.fontSize = Number(data.title.title_font_size);
              console.log('[SettingsStore] Updated video.title.fontSize from config.title:', this.video.title.fontSize);
            }
            if (data.title.title_text_color !== undefined) {
              this.video.title.color = data.title.title_text_color;
              console.log('[SettingsStore] Updated video.title.color from config.title:', this.video.title.color);
            }
            if (data.title.title_stroke_color !== undefined) {
              this.video.title.strokeColor = data.title.title_stroke_color;
              console.log('[SettingsStore] Updated video.title.strokeColor from config.title:', this.video.title.strokeColor);
            }
            if (data.title.title_stroke_width !== undefined) {
              this.video.title.strokeWidth = Number(data.title.title_stroke_width);
              console.log('[SettingsStore] Updated video.title.strokeWidth from config.title:', this.video.title.strokeWidth);
            }
            if (data.title.title_background_color !== undefined) {
              this.video.title.backgroundColor = data.title.title_background_color;
              console.log('[SettingsStore] Updated video.title.backgroundColor from config.title:', this.video.title.backgroundColor);
            }
            if (data.title.title_position !== undefined) {
              this.video.title.position = data.title.title_position;
              console.log('[SettingsStore] Updated video.title.position from config.title:', this.video.title.position);
            }
            if (data.title.title_margin !== undefined) {
              this.video.title.margin = Number(data.title.title_margin);
              console.log('[SettingsStore] Updated video.title.margin from config.title:', this.video.title.margin);
            }
            if (data.title.title_margin_left !== undefined) {
              this.video.title.marginLeft = Number(data.title.title_margin_left);
              console.log('[SettingsStore] Updated video.title.marginLeft from config.title:', this.video.title.marginLeft);
            }
            if (data.title.title_margin_right !== undefined) {
              this.video.title.marginRight = Number(data.title.title_margin_right);
              console.log('[SettingsStore] Updated video.title.marginRight from config.title:', this.video.title.marginRight);
            }
            if (data.title.title_animation !== undefined) {
              this.video.title.animation = data.title.title_animation;
              console.log('[SettingsStore] Updated video.title.animation from config.title:', this.video.title.animation);
            }
            if (data.title.title_animation_duration !== undefined) {
              this.video.title.animationDuration = Number(data.title.title_animation_duration);
              console.log('[SettingsStore] Updated video.title.animationDuration from config.title:', this.video.title.animationDuration);
            }
            if (typeof data.title.title_background_overlay === 'boolean') {
              this.video.title.backgroundOverlay = data.title.title_background_overlay;
              console.log('[SettingsStore] Updated video.title.backgroundOverlay from config.title:', this.video.title.backgroundOverlay);
            }
            if (data.title.title_overlay_color !== undefined) {
              this.video.title.overlayColor = data.title.title_overlay_color;
              console.log('[SettingsStore] Updated video.title.overlayColor from config.title:', this.video.title.overlayColor);
            }
            if (data.title.title_style !== undefined) {
              this.video.title.style = data.title.title_style;
              console.log('[SettingsStore] Updated video.title.style from config.title:', this.video.title.style);
            }
            if (data.title.title_align !== undefined) {
              this.video.title.align = data.title.title_align;
              console.log('[SettingsStore] Updated video.title.align from config.title:', this.video.title.align);
            }
          }

          if (data.video) {
            if (data.video.video_source) {
              this.app.videoSource = data.video.video_source;
              this.video.source = data.video.video_source;
            }
            if (data.video.video_quality) {
              this.video.quality = data.video.video_quality;
            }
            if (data.video.video_bitrate) {
              this.video.bitrate = data.video.video_bitrate;
            }
            if (data.video.video_brightness !== undefined) {
              this.video.brightness = Number(data.video.video_brightness);
            }
            if (data.video.video_contrast !== undefined) {
              this.video.contrast = Number(data.video.video_contrast);
            }
            if (data.video.video_concat_mode) {
              this.video.concatMode = data.video.video_concat_mode;
            }
            if (data.video.video_transition_mode) {
              this.video.transitionMode = data.video.video_transition_mode;
            }
            if (data.video.video_aspect) {
              this.video.aspect = data.video.video_aspect;
            }
            if (data.video.video_clip_duration !== undefined) {
              this.video.clipDuration = Number(data.video.video_clip_duration);
            }
            if (data.video.video_count !== undefined) {
              this.video.count = Number(data.video.video_count);
            }
            if (data.video.silence_duration !== undefined) {
              this.video.silenceDuration = Number(data.video.silence_duration);
            }
            if (data.video.video_style) {
              this.video.style = data.video.video_style;
            }
            if (data.video.intro_video_bg_type) {
              this.video.introVideoBgType = data.video.intro_video_bg_type;
            }
            if (data.video.intro_video_bg_blur !== undefined) {
              this.video.introVideoBgBlur = Number(data.video.intro_video_bg_blur);
            }
            if (data.video.intro_video_bg_color) {
              this.video.introVideoBgColor = data.video.intro_video_bg_color;
            }
            if (typeof data.video.use_gpu === 'boolean') {
              this.app.useGpu = data.video.use_gpu;
            }
          }

          if (data.app) {
            if (data.app.llm_provider) {
              this.app.llmProvider = data.app.llm_provider;
            }
            if (data.app.subtitle_provider) {
              this.app.subtitleProvider = data.app.subtitle_provider;
            }
            if (typeof data.app.host_visible === 'boolean') {
              this.video.hostVisible = data.app.host_visible;
            }
            if (Array.isArray(data.app.pexels_api_keys)) {
              this.videoSources.pexelsApiKeys = data.app.pexels_api_keys;
            }
            if (Array.isArray(data.app.pixabay_api_keys)) {
              this.videoSources.pixabayApiKeys = data.app.pixabay_api_keys;
            }

            // Update LLM configs
            if (data.app.openai_api_key) {
              this.llm.openai = this.llm.openai || { apiKey: '', baseUrl: '', modelName: '' };
              this.llm.openai.apiKey = data.app.openai_api_key;
              if (data.app.openai_base_url) {
                this.llm.openai.baseUrl = data.app.openai_base_url;
              }
              if (data.app.openai_model_name) {
                this.llm.openai.modelName = data.app.openai_model_name;
              }
            }

            if (data.app.moonshot_api_key) {
              this.llm.moonshot = this.llm.moonshot || { apiKey: '', baseUrl: '', modelName: '' };
              this.llm.moonshot.apiKey = data.app.moonshot_api_key;
              if (data.app.moonshot_base_url) {
                this.llm.moonshot.baseUrl = data.app.moonshot_base_url;
              }
              if (data.app.moonshot_model_name) {
                this.llm.moonshot.modelName = data.app.moonshot_model_name;
              }
            }

            if (data.app.deepseek_api_key) {
              this.llm.deepseek = this.llm.deepseek || { apiKey: '', baseUrl: '', modelName: '' };
              this.llm.deepseek.apiKey = data.app.deepseek_api_key;
              if (data.app.deepseek_base_url) {
                this.llm.deepseek.baseUrl = data.app.deepseek_base_url;
              }
              if (data.app.deepseek_model_name) {
                this.llm.deepseek.modelName = data.app.deepseek_model_name;
              }
            }
          }

          if (data.whisper && data.whisper.device) {
            this.whisper.device = data.whisper.device;
            console.log('Updated whisper device:', this.whisper.device);
          }

          if (data.azure) {
            if (data.azure.speech_region) {
              this.llm.azure = this.llm.azure || { apiKey: '', baseUrl: '', modelName: '' };
              this.llm.azure.baseUrl = data.azure.speech_region;
            }
            if (data.azure.speech_key) {
              this.llm.azure = this.llm.azure || { apiKey: '', baseUrl: '', modelName: '' };
              this.llm.azure.apiKey = data.azure.speech_key;
            }
            console.log('Updated azure config:', this.llm.azure);
          }

          if (data.siliconflow && data.siliconflow.api_key) {
            this.llm.siliconflow = this.llm.siliconflow || { apiKey: '', baseUrl: '', modelName: '' };
            this.llm.siliconflow.apiKey = data.siliconflow.api_key;
            console.log('Updated siliconflow config:', this.llm.siliconflow);
          }

          if (data.coze && data.coze.api_key) {
            this.llm.coze = this.llm.coze || { apiKey: '', baseUrl: '', modelName: '' };
            this.llm.coze.apiKey = data.coze.api_key;
            console.log('Updated coze config:', this.llm.coze);
          }
          
          // Load qwen config
          if (data.qwen) {
            if (data.qwen.api_key) {
              this.audio.qwenApiKey = data.qwen.api_key;
              console.log('[SettingsStore] Updated qwenApiKey from config:', this.audio.qwenApiKey);
            }
            if (data.qwen.model_name) {
              this.audio.qwenModelName = data.qwen.model_name;
              console.log('[SettingsStore] Updated qwenModelName from config:', this.audio.qwenModelName);
            }
          }

          // Load gemini config
          if (data.gemini && data.gemini.api_key) {
            this.audio.geminiApiKey = data.gemini.api_key;
            console.log('[SettingsStore] Updated geminiApiKey from config:', this.audio.geminiApiKey);
          }

          // Load bailian_token_plan config
          if (data.bailian_token_plan) {
            if (data.bailian_token_plan.api_key) {
              this.audio.bailianTokenPlanApiKey = data.bailian_token_plan.api_key;
              console.log('[SettingsStore] Updated bailianTokenPlanApiKey from config:', this.audio.bailianTokenPlanApiKey);
            }
            if (data.bailian_token_plan.model_name) {
              this.audio.bailianTokenPlanModelName = data.bailian_token_plan.model_name;
              console.log('[SettingsStore] Updated bailianTokenPlanModelName from config:', this.audio.bailianTokenPlanModelName);
            }
            if (data.bailian_token_plan.base_url) {
              this.audio.bailianTokenPlanBaseUrl = data.bailian_token_plan.base_url;
              console.log('[SettingsStore] Updated bailianTokenPlanBaseUrl from config:', this.audio.bailianTokenPlanBaseUrl);
            }
          }

          // Load tavily config
          if (data.tavily && data.tavily.api_key) {
            this.audio.tavilyApiKey = data.tavily.api_key;
            console.log('[SettingsStore] Updated tavilyApiKey from config:', this.audio.tavilyApiKey);
          }

          this.saveToLocalStorage();
          console.log('Config saved to localStorage');
        } else {
          console.error('Invalid config response:', response);
        }
      } catch (error: any) {
        console.error('Failed to fetch config:', error);
        console.error('Error details:', error.message);
        if (error.response) {
          console.error('Error response:', error.response);
        } else if (error.request) {
          console.error('Error request:', error.request);
        }
      }
    }
  }
});