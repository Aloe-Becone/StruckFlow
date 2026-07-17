<template>
  <div class="app-container dark">
    <!-- 左侧边栏：对话记录 -->
    <transition name="slide">
      <ChatSidebar
        v-show="sidebarVisible"
        :sessions="sessions"
        :current-session="currentSession"
        :chat-records="chatRecords"
        @new-session="handleNewSession"
        @resume-session="handleResumeSession"
        @close="sidebarVisible = false"
      />
    </transition>

    <!-- 主区域 -->
    <div class="main-area">
      <!-- 顶栏 -->
      <header class="top-bar">
        <div class="top-bar-left">
          <el-button
            :icon="sidebarVisible ? 'Fold' : 'Expand'"
            text
            @click="sidebarVisible = !sidebarVisible"
          />
          <span class="app-title">StruckFlow</span>
          <el-tag size="small" type="success" effect="dark" class="mode-tag">
            SemanticObject 三层协议
          </el-tag>
        </div>
        <div class="top-bar-right">
          <el-button
            :icon="metricsVisible ? 'Hide' : 'DataLine'"
            text
            @click="metricsVisible = !metricsVisible"
          >指标</el-button>
          <el-button
            :icon="compareResult ? 'Close' : 'ScaleToOriginal'"
            text
            :type="compareResult ? 'primary' : ''"
            @click="toggleComparePanel"
          >对比</el-button>
        </div>
      </header>

      <!-- 对话区域 -->
      <div class="chat-body">
        <MessageList
          ref="messageListRef"
          :messages="messages"
          :loading="loading"
        />
      </div>

      <!-- 输入区域 -->
      <ChatInput
        :loading="loading"
        @send="handleSend"
        @compare="handleCompare"
      />
    </div>

    <!-- 指标面板 -->
    <transition name="slide">
      <MetricsPanel
        v-show="metricsVisible"
        :metrics="lastMetrics"
        @close="metricsVisible = false"
      />
    </transition>

    <!-- 对比面板 -->
    <el-drawer
      v-model="compareDrawerVisible"
      title="结构化 vs 纯文本 对比"
      direction="rtl"
      size="520px"
      :append-to-body="true"
    >
      <ComparePanel v-if="compareResult" :result="compareResult" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import axios from 'axios'

import ChatSidebar from '@/components/ChatSidebar.vue'
import MessageList from '@/components/MessageList.vue'
import ChatInput from '@/components/ChatInput.vue'
import MetricsPanel from '@/components/MetricsPanel.vue'
import ComparePanel from '@/components/ComparePanel.vue'

const http = axios.create({ timeout: 300000 })

// ── 状态 ──
const sidebarVisible = ref(true)
const metricsVisible = ref(false)
const compareDrawerVisible = ref(false)
const loading = ref(false)

const messages = reactive([])
const sessions = reactive([])
const chatRecords = reactive([])
const currentSession = ref(null)
const lastMetrics = ref(null)
const compareResult = ref(null)
const messageListRef = ref(null)

// ── 方法 ──
function addMessage(role, content, extra = {}) {
  messages.push({
    id: Date.now() + Math.random(),
    role,
    content,
    timestamp: new Date().toLocaleTimeString(),
    ...extra,
  })
  nextTick(() => {
    if (messageListRef.value) messageListRef.value.scrollToBottom()
  })
}

async function handleSend(question) {
  if (loading.value) return
  addMessage('user', question)
  loading.value = true
  addMessage('system', '正在思考中...')

  try {
    const res = await http.post('/api/chat', { question })
    const data = res.data
    // 移除 "正在思考" 占位消息
    messages.pop()

    // 添加 Agent 步骤
    if (data.agent_steps && data.agent_steps.length > 0) {
      for (const step of data.agent_steps) {
        addMessage('agent', '', {
          agentName: step.agent,
          action: step.action,
          step: step.step,
          precise: step.precise,
          control: step.control,
          semantic: step.semantic,
          stepMetrics: step.step_metrics || null,
        })
      }
    }

    // 添加最终答案
    addMessage('assistant', data.final_answer || '未生成答案', {
      traceId: data.trace_id,
      metrics: data.metrics,
    })

    lastMetrics.value = data.metrics
    metricsVisible.value = true
  } catch (err) {
    messages.pop()
    addMessage('error', `请求失败: ${err.response?.data?.error || err.message}`)
  } finally {
    loading.value = false
  }
}

async function handleCompare(question) {
  if (loading.value) return
  addMessage('user', question)
  loading.value = true
  addMessage('system', '对比模式运行中（结构化 + 纯文本）...')

  try {
    const res = await http.post('/api/chat/compare', { question })
    const data = res.data
    messages.pop()

    // 结构化结果
    if (data.structured?.agent_steps?.length) {
      for (const step of data.structured.agent_steps) {
        addMessage('agent', '', {
          agentName: step.agent,
          action: step.action,
          step: step.step,
          precise: step.precise,
          stepMetrics: step.step_metrics || null,
        })
      }
    }
    addMessage('assistant', data.structured?.final_answer || '未生成答案', {
      traceId: data.structured?.trace_id,
      metrics: data.structured?.metrics,
    })

    lastMetrics.value = data.structured?.metrics
    compareResult.value = data
    compareDrawerVisible.value = true
    metricsVisible.value = true
  } catch (err) {
    messages.pop()
    addMessage('error', `对比请求失败: ${err.response?.data?.error || err.message}`)
  } finally {
    loading.value = false
  }
}

async function handleNewSession() {
  try {
    const res = await http.post('/api/sessions')
    currentSession.value = res.data
    messages.length = 0
    chatRecords.length = 0
    addMessage('system', '已开启新对话')
    await loadSessions()
  } catch (err) {
    console.error('新建会话失败:', err)
  }
}

async function handleResumeSession(session) {
  try {
    await http.post(`/api/sessions/${session.index}/resume`)
    currentSession.value = session
    await loadChatRecords()
    // 将对话记录转为消息
    messages.length = 0
    for (const record of chatRecords) {
      addMessage('user', record.user_question || '')
      if (record.final_answer) {
        addMessage('assistant', record.final_answer, { metrics: record.metrics })
      }
    }
  } catch (err) {
    console.error('恢复会话失败:', err)
  }
}

async function loadSessions() {
  try {
    const res = await http.get('/api/sessions')
    sessions.length = 0
    sessions.push(...res.data)
  } catch (_) {}
}

async function loadChatRecords() {
  try {
    const res = await http.get('/api/chats')
    chatRecords.length = 0
    chatRecords.push(...res.data)
  } catch (_) {}
}

function toggleComparePanel() {
  if (compareResult.value) {
    compareDrawerVisible.value = !compareDrawerVisible.value
  }
}

onMounted(async () => {
  try {
    await http.get('/api/health')
    addMessage('system', '系统已连接，请输入问题开始对话')
    await loadSessions()
  } catch (_) {
    addMessage('system', '正在连接后端服务...')
  }
})
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--sf-bg-base);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--sf-bg-base);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--sf-border-light);
  background: var(--sf-bg-overlay);
  height: 48px;
  flex-shrink: 0;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--sf-primary);
  letter-spacing: 0.5px;
}

.mode-tag {
  font-size: 11px;
}

.chat-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}
</style>