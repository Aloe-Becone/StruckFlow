<template>
  <div class="compare-panel">
    <!-- 对比摘要 -->
    <div class="compare-summary">
      <h4 class="section-title">对比摘要</h4>
      <div class="summary-grid">
        <div class="summary-card structured">
          <span class="card-label">结构化模式</span>
          <span class="card-value">{{ result.structured?.metrics?.total_tokens ?? '-' }} tok</span>
          <span class="card-sub">{{ formatDuration(result.structured?.metrics?.duration_seconds) }}</span>
        </div>
        <div class="summary-card text-mode">
          <span class="card-label">纯文本模式</span>
          <span class="card-value">{{ result.text_mode?.metrics?.total_tokens ?? '-' }} tok</span>
          <span class="card-sub">{{ formatDuration(result.text_mode?.metrics?.duration_seconds) }}</span>
        </div>
      </div>
    </div>

    <!-- 详细对比表 -->
    <div v-if="result.comparison" class="compare-detail">
      <h4 class="section-title">详细对比</h4>
      <el-table :data="comparisonRows" size="small" stripe>
        <el-table-column prop="label" label="指标" width="100" />
        <el-table-column prop="structured" label="结构化" />
        <el-table-column prop="textMode" label="纯文本" />
        <el-table-column prop="diff" label="差异" width="80">
          <template #default="{ row }">
            <span :class="row.diffClass">{{ row.diff }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 答案对比 -->
    <div class="answer-compare">
      <h4 class="section-title">答案对比</h4>
      <div class="answer-grid">
        <div class="answer-block">
          <span class="block-label">结构化答案</span>
          <div class="block-content" v-html="renderMD(result.structured?.final_answer || '无')"></div>
        </div>
        <div class="answer-block">
          <span class="block-label">纯文本答案</span>
          <div class="block-content" v-html="renderMD(result.text_mode?.final_answer || '无')"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: { type: Object, required: true },
})

const comparisonRows = computed(() => {
  const c = props.result.comparison
  if (!c) return []
  const rows = []
  const s = props.result.structured?.metrics || {}
  const t = props.result.text_mode?.metrics || {}

  const addRow = (label, sVal, tVal, unit = '') => {
    const sv = sVal ?? '-'
    const tv = tVal ?? '-'
    const diffNum = (typeof sVal === 'number' && typeof tVal === 'number') ? sVal - tVal : null
    const diff = diffNum !== null ? (diffNum > 0 ? `+${diffNum}` : `${diffNum}`) + unit : '-'
    const diffClass = diffNum !== null
      ? (diffNum < 0 ? 'diff-good' : diffNum > 0 ? 'diff-bad' : 'diff-neutral')
      : ''
    rows.push({ label, structured: sv + unit, textMode: tv + unit, diff, diffClass })
  }

  addRow('Token', s.total_tokens, t.total_tokens)
  addRow('字符', s.total_chars, t.total_chars)
  addRow('消息', s.total_messages, t.total_messages)
  addRow('耗时', s.duration_seconds, t.duration_seconds, 's')

  return rows
})

function formatDuration(seconds) {
  if (!seconds) return '-'
  return seconds.toFixed(2) + 's'
}

function renderMD(text) {
  if (!text) return ''
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}
</script>

<style scoped>
.compare-panel {
  padding: 0 4px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--sf-text-muted);
  text-transform: uppercase;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.compare-summary {
  margin-bottom: 20px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.summary-card {
  background: var(--sf-bg-elevated);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-top: 3px solid;
}

.summary-card.structured {
  border-top-color: var(--sf-primary);
}

.summary-card.text-mode {
  border-top-color: #e6a23c;
}

.card-label {
  font-size: 12px;
  color: var(--sf-text-muted);
  margin-bottom: 4px;
}

.card-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--sf-text-primary);
}

.card-sub {
  font-size: 11px;
  color: var(--sf-text-secondary);
  margin-top: 2px;
}

.compare-detail {
  margin-bottom: 20px;
}

.diff-good {
  color: #67c23a;
  font-weight: 600;
}

.diff-bad {
  color: #f56c6c;
  font-weight: 600;
}

.diff-neutral {
  color: var(--sf-text-muted);
}

.answer-compare {
  margin-bottom: 16px;
}

.answer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.answer-block {
  background: var(--sf-bg-elevated);
  border-radius: 8px;
  padding: 12px;
}

.block-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--sf-primary);
  margin-bottom: 6px;
  text-transform: uppercase;
}

.block-content {
  font-size: 13px;
  color: var(--sf-text-primary);
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
}

.block-content :deep(.code-block) {
  background: var(--sf-bg-base);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 12px;
  margin: 4px 0;
  overflow-x: auto;
}
</style>