<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">对话历史</span>
      <el-button text :icon="'Close'" size="small" @click="$emit('close')" />
    </div>

    <div class="sidebar-actions">
      <el-button type="primary" :icon="'Plus'" @click="$emit('new-session')" style="width: 100%">
        新建对话
      </el-button>
    </div>

    <div class="session-list">
      <div
        v-for="session in sessions"
        :key="session.index"
        class="session-item"
        :class="{ active: currentSession?.index === session.index }"
        @click="$emit('resume-session', session)"
      >
        <el-icon><ChatDotRound /></el-icon>
        <span class="session-label">{{ session.label || `会话 ${session.index + 1}` }}</span>
        <span class="session-time">{{ session.time || '' }}</span>
      </div>
      <div v-if="sessions.length === 0" class="empty-hint">
        暂无对话记录
      </div>
    </div>

    <div class="sidebar-footer">
      <el-button text :icon="'Refresh'" size="small" @click="$emit('new-session')">刷新</el-button>
    </div>
  </aside>
</template>

<script setup>
import { ChatDotRound } from '@element-plus/icons-vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  currentSession: { type: Object, default: null },
  chatRecords: { type: Array, default: () => [] },
})

defineEmits(['new-session', 'resume-session', 'close'])
</script>

<style scoped>
.chat-sidebar {
  width: 260px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--sf-bg-overlay);
  border-right: 1px solid var(--sf-border-light);
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--sf-border-light);
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--sf-text-primary);
}

.sidebar-actions {
  padding: 12px 16px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  color: var(--sf-text-secondary);
  font-size: 13px;
}

.session-item:hover {
  background: var(--sf-bg-elevated);
}

.session-item.active {
  background: var(--sf-primary-dim);
  color: var(--sf-primary);
}

.session-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 11px;
  color: var(--sf-text-muted);
}

.empty-hint {
  text-align: center;
  padding: 24px 0;
  color: var(--sf-text-muted);
  font-size: 13px;
}

.sidebar-footer {
  padding: 8px 16px;
  border-top: 1px solid var(--sf-border-light);
  display: flex;
  justify-content: center;
}
</style>