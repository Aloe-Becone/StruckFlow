<template>
  <div class="message-list" ref="scrollContainer">
    <div class="message-inner">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-row"
        :class="[`msg-${msg.role}`]"
      >
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="msg-bubble user-bubble">
          <div class="msg-content">{{ msg.content }}</div>
          <span class="msg-time">{{ msg.timestamp }}</span>
        </div>

        <!-- 系统消息 -->
        <div v-else-if="msg.role === 'system'" class="msg-bubble system-bubble">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ msg.content }}</span>
        </div>

        <!-- 错误消息 -->
        <div v-else-if="msg.role === 'error'" class="msg-bubble error-bubble">
          <el-icon><CircleCloseFilled /></el-icon>
          <span>{{ msg.content }}</span>
        </div>

        <!-- Agent 步骤 -->
        <div v-else-if="msg.role === 'agent'" class="msg-bubble agent-bubble">
          <div class="agent-header">
            <el-tag size="small" :type="agentTagType(msg.agentName)" effect="dark">
              {{ msg.agentName || 'Agent' }}
            </el-tag>
            <span class="agent-action">{{ msg.action || '' }}</span>
            <span class="agent-step" v-if="msg.step">Step {{ msg.step }}</span>
          </div>
          <!-- 每步性能指标 -->
          <div v-if="msg.stepMetrics" class="step-metrics">
            <el-tag size="small" type="info" effect="plain">
              {{ msg.stepMetrics.total_tokens ?? 0 }} tok
            </el-tag>
            <el-tag size="small" type="info" effect="plain" v-if="msg.stepMetrics.duration_seconds">
              {{ msg.stepMetrics.duration_seconds.toFixed(2) }}s
            </el-tag>
            <el-tag size="small" type="info" effect="plain" v-if="msg.stepMetrics.memory_hits">
              {{ msg.stepMetrics.memory_hits }} hits
            </el-tag>
          </div>
          <div class="agent-layers" v-if="msg.precise || msg.semantic || msg.control">
            <el-collapse>
              <el-collapse-item title="三层协议详情" name="layers">
                <div v-if="msg.control" class="layer-item">
                  <span class="layer-label">Control</span>
                  <pre class="layer-code">{{ formatJSON(msg.control) }}</pre>
                </div>
                <div v-if="msg.semantic" class="layer-item">
                  <span class="layer-label">Semantic</span>
                  <pre class="layer-code">{{ formatJSON(msg.semantic) }}</pre>
                </div>
                <div v-if="msg.precise" class="layer-item">
                  <span class="layer-label">Precise</span>
                  <pre class="layer-code">{{ formatJSON(msg.precise) }}</pre>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>

        <!-- 助手最终答案 -->
        <div v-else-if="msg.role === 'assistant'" class="msg-bubble assistant-bubble">
          <div class="assistant-header">
            <el-icon><Monitor /></el-icon>
            <span class="assistant-name">StruckFlow</span>
            <span class="msg-time">{{ msg.timestamp }}</span>
          </div>
          <div class="msg-content markdown-body" v-html="renderMarkdown(msg.content)"></div>
          <div v-if="msg.metrics" class="msg-metrics">
            <el-tag size="small" type="info" effect="plain">
              Token: {{ msg.metrics.total_tokens ?? '-' }}
            </el-tag>
            <el-tag size="small" type="info" effect="plain">
              耗时: {{ msg.metrics.duration_seconds ? msg.metrics.duration_seconds.toFixed(2) + 's' : '-' }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 加载动画 -->
      <div v-if="loading" class="message-row">
        <div class="msg-bubble assistant-bubble loading-bubble">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { InfoFilled, CircleCloseFilled, Monitor } from '@element-plus/icons-vue'

defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const scrollContainer = ref(null)

function scrollToBottom() {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
  }
}

function agentTagType(name) {
  const map = { 任务分配: 'primary', 资料搜索: 'success', 任务执行: 'warning', 总结验证: 'danger' }
  return map[name] || 'info'
}

function formatJSON(obj) {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

function renderMarkdown(text) {
  if (!text) return ''
  // 简易 Markdown 渲染：代码块、粗体、换行
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.message-list {
  height: 100%;
  overflow-y: auto;
  padding: 16px 20px;
  scroll-behavior: smooth;
}

.message-inner {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-row {
  display: flex;
}

.msg-user {
  justify-content: flex-end;
}

.msg-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.user-bubble {
  background: var(--sf-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.user-bubble .msg-time {
  display: block;
  text-align: right;
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
}

.system-bubble,
.error-bubble {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 6px;
  align-self: center;
}

.system-bubble {
  background: var(--sf-bg-elevated);
  color: var(--sf-text-muted);
}

.error-bubble {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.agent-bubble {
  background: var(--sf-bg-overlay);
  border: 1px solid var(--sf-border-light);
  border-radius: 8px;
  max-width: 90%;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.agent-action {
  font-size: 12px;
  color: var(--sf-text-secondary);
}

.agent-step {
  font-size: 11px;
  color: var(--sf-text-muted);
  margin-left: auto;
}

.agent-layers {
  margin-top: 6px;
}

.step-metrics {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.layer-item {
  margin-bottom: 6px;
}

.layer-label {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: var(--sf-primary);
  margin-bottom: 2px;
  text-transform: uppercase;
}

.layer-code {
  background: var(--sf-bg-base);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 11px;
  color: var(--sf-text-secondary);
  overflow-x: auto;
  margin: 0;
}

.assistant-bubble {
  background: var(--sf-bg-overlay);
  border: 1px solid var(--sf-border-light);
  border-top-left-radius: 4px;
  max-width: 90%;
}

.assistant-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  color: var(--sf-primary);
}

.assistant-name {
  font-weight: 600;
  font-size: 13px;
}

.assistant-header .msg-time {
  font-size: 11px;
  color: var(--sf-text-muted);
  margin-left: auto;
}

.msg-content {
  color: var(--sf-text-primary);
  word-break: break-word;
}

.msg-metrics {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.markdown-body :deep(.code-block) {
  background: var(--sf-bg-base);
  border-radius: 6px;
  padding: 10px 12px;
  overflow-x: auto;
  font-size: 13px;
  margin: 8px 0;
}

.loading-bubble {
  padding: 12px 18px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sf-primary);
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}
</style>