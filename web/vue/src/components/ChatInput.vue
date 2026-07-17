<template>
  <div class="chat-input-area">
    <div class="input-wrapper">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        :autosize="{ minRows: 1, maxRows: 6 }"
        placeholder="输入问题，按 Enter 发送..."
        resize="none"
        :disabled="loading"
        @keydown.enter.exact="handleEnter"
      />
      <div class="input-actions">
        <el-tooltip content="纯文本对比模式" placement="top" :show-after="400">
          <el-button
            :icon="'ScaleToOriginal'"
            size="small"
            circle
            :disabled="!inputText.trim() || loading"
            @click="handleCompare"
            class="compare-btn"
          />
        </el-tooltip>
        <el-button
          type="primary"
          :icon="'Promotion'"
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
          class="send-btn"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'compare'])

const inputText = ref('')

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  inputText.value = ''
}

function handleCompare() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  emit('compare', text)
  inputText.value = ''
}

function handleEnter(e) {
  if (e.shiftKey) return // Shift+Enter 换行
  e.preventDefault()
  handleSend()
}
</script>

<style scoped>
.chat-input-area {
  padding: 12px 20px 16px;
  background: var(--sf-bg-overlay);
  border-top: 1px solid var(--sf-border-light);
}

.input-wrapper {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-wrapper :deep(.el-textarea__inner) {
  background: var(--sf-bg-elevated);
  border-color: var(--sf-border-light);
  color: var(--sf-text-primary);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 14px;
}

.input-wrapper :deep(.el-textarea__inner):focus {
  border-color: var(--sf-primary);
  box-shadow: 0 0 0 1px var(--sf-primary);
}

.input-wrapper :deep(.el-textarea__inner::placeholder) {
  color: var(--sf-text-muted);
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.compare-btn {
  color: var(--sf-text-secondary);
  background: var(--sf-bg-elevated);
  border-color: var(--sf-border-light);
}

.compare-btn:hover:not(:disabled) {
  color: var(--sf-primary);
  border-color: var(--sf-primary);
}

.send-btn {
  border-radius: 8px;
}
</style>