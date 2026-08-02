import { defineStore } from 'pinia';

interface Scene {
  id: string;
  title: string;
  duration: number;
  visual_requirement: string;
  keywords: string;
  script: string;
  introVideo?: string;
  introVideoOriginalPath?: string;
  introVideoDuration?: number;
  introVideoCoverFull?: boolean;
  useLocallens?: boolean;
}

export interface ScriptSettings {
  videoSubject: string;
  videoScript: string;
  language: string;
  videoTitle: string;
  scenes: Scene[];
  scriptPreset: string;
  webSearchEnabled: boolean;
  searchResultsCount: number;
  searchRounds: number;
  searchSourcePreference: string;
  expansionDepth: string;
  paragraphDetail: string;
  scriptStyle: string;
}

export const useScriptStore = defineStore('script', {
  state: (): ScriptSettings => ({
    videoSubject: '',
    videoScript: '',
    language: 'auto',
    videoTitle: '',
    scenes: [],
    scriptPreset: 'standard',
    webSearchEnabled: false,
    searchResultsCount: 5,
    searchRounds: 1,
    searchSourcePreference: 'balanced',
    expansionDepth: 'moderate',
    paragraphDetail: 'normal',
    scriptStyle: 'general',
  }),
  
  actions: {
    updateVideoSubject(value: string) {
      this.videoSubject = value;
      this.saveToLocalStorage();
    },
    
    updateVideoScript(value: string) {
      this.videoScript = value;
      this.saveToLocalStorage();
    },
    
    updateLanguage(value: string) {
      this.language = value;
      this.saveToLocalStorage();
    },
    
    updateVideoTitle(value: string) {
      this.videoTitle = value;
      this.saveToLocalStorage();
    },
    
    updateScenes(value: Scene[]) {
      this.scenes = value;
      this.saveToLocalStorage();
    },
    
    addScene(scene: Scene) {
      this.scenes.push(scene);
      this.saveToLocalStorage();
    },
    
    removeScene(index: number) {
      this.scenes.splice(index, 1);
      this.saveToLocalStorage();
    },
    
    updateScene(index: number, scene: Scene) {
      this.scenes[index] = scene;
      this.saveToLocalStorage();
    },
    
    loadFromLocalStorage() {
      const savedScript = localStorage.getItem('coiner-script');
      if (savedScript) {
        try {
          const parsed = JSON.parse(savedScript);
          Object.assign(this, parsed);
        } catch (e) {
          console.error('Failed to load script from localStorage:', e);
        }
      }
    },
    
    updateScriptPreset(value: string) {
      this.scriptPreset = value;
      this.saveToLocalStorage();
    },

    updateWebSearchEnabled(value: boolean) {
      this.webSearchEnabled = value;
      this.saveToLocalStorage();
    },

    updateSearchResultsCount(value: number) {
      this.searchResultsCount = value;
      this.saveToLocalStorage();
    },

    updateSearchRounds(value: number) {
      this.searchRounds = value;
      this.saveToLocalStorage();
    },

    updateSearchSourcePreference(value: string) {
      this.searchSourcePreference = value;
      this.saveToLocalStorage();
    },

    updateExpansionDepth(value: string) {
      this.expansionDepth = value;
      this.saveToLocalStorage();
    },

    updateParagraphDetail(value: string) {
      this.paragraphDetail = value;
      this.saveToLocalStorage();
    },

    updateScriptStyle(value: string) {
      this.scriptStyle = value;
      this.saveToLocalStorage();
    },

    saveToLocalStorage() {
      const data = {
        videoSubject: this.videoSubject,
        videoScript: this.videoScript,
        language: this.language,
        videoTitle: this.videoTitle,
        scenes: JSON.parse(JSON.stringify(this.scenes)),
        scriptPreset: this.scriptPreset,
        webSearchEnabled: this.webSearchEnabled,
        searchResultsCount: this.searchResultsCount,
        searchRounds: this.searchRounds,
        searchSourcePreference: this.searchSourcePreference,
        expansionDepth: this.expansionDepth,
        paragraphDetail: this.paragraphDetail,
        scriptStyle: this.scriptStyle,
      };
      localStorage.setItem('coiner-script', JSON.stringify(data));
    }
  }
});
