import { defineStore } from 'pinia';
import { apiService, type ApiResponse } from '../services/api';

export interface Task {
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
  scene_loss_warning?: string;
  failed_scene_indices?: number[];
}

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [] as Task[],
    currentTask: null as Task | null,
    loading: false,
    error: null as string | null,
    unviewedCompletedIds: JSON.parse(localStorage.getItem('coiner_unviewed_tasks') || '[]') as string[],
    _initialLoadDone: false
  }),
  
  getters: {
    getTaskById: (state) => (taskId: string) => {
      return state.tasks.find(task => task.task_id === taskId) || null;
    },
    
    pendingTasks: (state) => {
      return state.tasks.filter(task => task.status === 'pending');
    },
    
    runningTasks: (state) => {
      return state.tasks.filter(task => task.status === 'running');
    },
    
    cancellingTasks: (state) => {
      return state.tasks.filter(task => task.status === 'cancelling');
    },
    
    completedTasks: (state) => {
      return state.tasks.filter(task => task.status === 'completed');
    },
    
    failedTasks: (state) => {
      return state.tasks.filter(task => task.status === 'failed');
    },
    
    isNewlyCompleted: (state) => (taskId: string) => {
      return state.unviewedCompletedIds.includes(taskId);
    }
  },
  
  actions: {
    _saveUnviewedToStorage() {
      try {
        localStorage.setItem('coiner_unviewed_tasks', JSON.stringify(this.unviewedCompletedIds));
      } catch {
        // localStorage full or unavailable - silently ignore
      }
    },

    markTaskViewed(taskId: string) {
      this.unviewedCompletedIds = this.unviewedCompletedIds.filter(id => id !== taskId);
      this._saveUnviewedToStorage();
    },

    async fetchAllTasks(page: number = 1, pageSize: number = 100, showLoading: boolean = true) {
      if (showLoading) {
        this.loading = true;
      }
      this.error = null;
      
      try {
        const response = await apiService.getAllTasks(page, pageSize);
        if (response.status === 200 && response.data) {
          const newTasks: Task[] = response.data.tasks || [];
          const newTaskIds = new Set(newTasks.map((task: Task) => task.task_id));

          this.tasks = this.tasks.filter((task: Task) => newTaskIds.has(task.task_id));

          newTasks.forEach((newTask: Task) => {
            const existingIndex = this.tasks.findIndex((task: Task) => task.task_id === newTask.task_id);
            let wasAlreadyCompleted = false;
            if (existingIndex !== -1) {
              const existingTask = this.tasks[existingIndex];
              wasAlreadyCompleted = existingTask.status === 'completed';
              if (existingTask.status !== newTask.status || existingTask.progress !== newTask.progress) {
                this.tasks[existingIndex] = newTask;
              }
            } else {
              this.tasks.push(newTask);
            }

            // Detect newly completed tasks with videos — only during polling, not on initial load
            if (this._initialLoadDone && newTask.status === 'completed' && newTask.videos && newTask.videos.length > 0) {
              if (!wasAlreadyCompleted && !this.unviewedCompletedIds.includes(newTask.task_id)) {
                this.unviewedCompletedIds.push(newTask.task_id);
                this._saveUnviewedToStorage();
              }
            }
          });
          
          // 按任务编号升序排列
          this._initialLoadDone = true;

          this.tasks.sort((a, b) => (a.sequence_number ?? 0) - (b.sequence_number ?? 0));
        }
      } catch (error) {
        this.error = 'Failed to fetch tasks';
        console.error('Error fetching tasks:', error);
      } finally {
        if (showLoading) {
          this.loading = false;
        }
      }
    },
    
    async fetchTask(taskId: string) {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await apiService.getTask(taskId);
        if (response.status === 200 && response.data) {
          const task = response.data;
          this.currentTask = task;
          
          // Update the corresponding task in the task list
          const index = this.tasks.findIndex(t => t.task_id === taskId);
          if (index !== -1) {
            this.tasks[index] = task;
          } else {
            this.tasks.push(task);
          }
        }
      } catch (error) {
        this.error = 'Failed to fetch task';
        console.error('Error fetching task:', error);
      } finally {
        this.loading = false;
      }
    },
    
    async createTask(params: any, type: 'video' | 'subtitle' | 'audio' = 'video') {
      this.loading = true;
      this.error = null;
      
      try {
        let response: ApiResponse;
        if (type === 'video') {
          response = await apiService.createVideo(params);
        } else if (type === 'subtitle') {
          response = await apiService.createSubtitle(params);
        } else {
          response = await apiService.createAudio(params);
        }
        
        if (response.status === 200 && response.data) {
          const task = response.data;
          console.log('Task created:', task);
          this.tasks.unshift(task);
          this.currentTask = task;
          return task;
        } else {
          console.log('Invalid response:', response);
        }
      } catch (error: any) {
        // Get the error message from the backend response, or use a generic message
        const errorMessage = error?.response?.data?.message || error?.message || 'Failed to create task';
        this.error = errorMessage;
        console.error('Error creating task:', errorMessage);
      } finally {
        this.loading = false;
      }
      
      return null;
    },
    
    async deleteTask(taskId: string) {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await apiService.deleteTask(taskId);
        if (response.status === 200) {
          this.tasks = this.tasks.filter(task => task.task_id !== taskId);
          if (this.currentTask?.task_id === taskId) {
            this.currentTask = null;
          }
          this.unviewedCompletedIds = this.unviewedCompletedIds.filter(id => id !== taskId);
          this._saveUnviewedToStorage();
          return true;
        }
      } catch (error) {
        this.error = 'Failed to delete task';
        console.error('Error deleting task:', error);
      } finally {
        this.loading = false;
      }
      
      return false;
    },
    
    async cancelTask(taskId: string) {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await apiService.cancelTask(taskId);
        if (response.status === 200) {
          // 更新任务状态为 cancelling（最终状态由后端线程退出时更新）
          const task = this.getTaskById(taskId);
          if (task) {
            task.status = 'cancelling';
          }
          return true;
        }
      } catch (error) {
        this.error = 'Failed to cancel task';
        console.error('Error cancelling task:', error);
      } finally {
        this.loading = false;
      }
      
      return false;
    },
    
    updateTaskStatus(taskId: string, status: string, progress?: number) {
      const task = this.getTaskById(taskId);
      if (task) {
        task.status = status;
        if (progress !== undefined) {
          task.progress = progress;
        }
        task.updated_at = new Date().toISOString();
      }
    },
    
    clearError() {
      this.error = null;
    }
  }
});