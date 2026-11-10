<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  ArrowRight,
  Check,
  DataAnalysis,
  Document,
  Microphone,
  Opportunity,
  Position,
  Refresh,
  SwitchButton,
  User
} from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const userKey = ref('')
const roleCode = ref('java_backend')
const questionCount = ref(3)
const sessionId = ref(null)
const currentQuestionNo = ref(0)
const currentFollowupNo = ref(0)
const currentFollowupTurns = ref([])
const currentQuestion = ref(null)
const inputMessage = ref('')
const reportData = ref(null)
const analysisData = ref(null)
const historyList = ref([])
const growthData = ref({
  labels: [],
  scores: [],
  technical_scores: [],
  depth_scores: [],
  logic_scores: [],
  role_match_scores: [],
  speech_rate_scores: [],
  clarity_scores: [],
  confidence_scores: [],
  expression_scores: [],
  sessions: []
})
const starting = ref(false)
const submitting = ref(false)
const finishing = ref(false)
const nexting = ref(false)
const status = ref('idle')
const pendingFollowup = ref('')
const messages = ref([])
const recognition = ref(null)
const speechAvailable = ref(false)
const isVoiceRecording = ref(false)
const manualStop = ref(false)
const speechStartAt = ref(0)
const confidenceList = ref([])
const pauseCount = ref(0)
const lastSpeechEndAt = ref(0)
const voiceCommittedText = ref('')
const lastExpressionMetrics = ref(null)
const growthChartRef = ref(null)
let growthChartInstance = null

const roleOptions = [
  { label: 'Java后端开发', value: 'java_backend' },
  { label: 'Web前端开发', value: 'web_frontend' }
]

const growthMetricOptions = [
  { label: '综合', value: 'scores' },
  { label: '技术', value: 'technical_scores' },
  { label: '深度', value: 'depth_scores' },
  { label: '逻辑', value: 'logic_scores' },
  { label: '匹配', value: 'role_match_scores' },
  { label: '表达', value: 'expression_scores' },
  { label: '语速', value: 'speech_rate_scores' },
  { label: '清晰度', value: 'clarity_scores' },
  { label: '自信度', value: 'confidence_scores' }
]
const selectedGrowthMetric = ref('scores')

const currentRoleLabel = computed(() => roleOptions.find(item => item.value === roleCode.value)?.label || roleCode.value)
const anyBusy = computed(() => starting.value || submitting.value || nexting.value || finishing.value)
const canSendAnswer = computed(() => !!sessionId.value && !!currentQuestion.value && !submitting.value && !nexting.value && !finishing.value && !isVoiceRecording.value && inputMessage.value.trim())
const canNextQuestion = computed(() => !!sessionId.value && status.value === 'answered' && !pendingFollowup.value && !nexting.value && !submitting.value && !finishing.value)
const canFinish = computed(() => !!sessionId.value && (status.value === 'answered' || status.value === 'completed') && !finishing.value && !submitting.value && !nexting.value)
const growthSeriesValues = computed(() => {
  const values = growthData.value?.[selectedGrowthMetric.value] || []
  return Array.isArray(values) ? values.map(v => Number(v || 0)) : []
})
const growthMetricLabel = computed(() => growthMetricOptions.find(item => item.value === selectedGrowthMetric.value)?.label || '综合')
const growthMetricSummary = computed(() => {
  const values = growthSeriesValues.value
  if (!values.length) return { latest: 0, avg: 0, max: 0 }
  const latest = Number(values[values.length - 1] || 0)
  const avg = values.reduce((sum, item) => sum + Number(item || 0), 0) / values.length
  const max = Math.max(...values)
  return {
    latest: Number(latest.toFixed(2)),
    avg: Number(avg.toFixed(2)),
    max: Number(max.toFixed(2))
  }
})

function getRoleLabel(role) {
  return roleOptions.find(item => item.value === role)?.label || role || '未知岗位'
}

function showRequestError(error, fallbackText = '请求失败') {
  console.error(error)
  const detail = error?.response?.data?.detail || error?.response?.data?.msg || error?.message || fallbackText
  ElMessage.error(`${fallbackText}：${detail}`)
}

function formatHistoryStatus(item) {
  return item?.status === 'finished' ? '已完成' : '进行中'
}

function formatHistoryScore(item) {
  if (item?.status !== 'finished') return '进行中'
  if (item?.total_score === null || item?.total_score === undefined) return '--'
  return item.total_score
}

function resetInterviewState() {
  stopVoiceRecognitionSilently()
  sessionId.value = null
  currentQuestionNo.value = 0
  currentFollowupNo.value = 0
  currentFollowupTurns.value = []
  currentQuestion.value = null
  inputMessage.value = ''
  reportData.value = null
  analysisData.value = null
  pendingFollowup.value = ''
  messages.value = []
  status.value = 'idle'
  voiceCommittedText.value = ''
  speechStartAt.value = 0
  confidenceList.value = []
  pauseCount.value = 0
  lastSpeechEndAt.value = 0
  lastExpressionMetrics.value = null
}

function stopVoiceRecognitionSilently() {
  if (!recognition.value) return
  manualStop.value = true
  isVoiceRecording.value = false
  try {
    recognition.value.stop()
  } catch (e) {
    console.warn('停止语音识别失败：', e)
  }
}

function logout() {
  stopVoiceRecognitionSilently()
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_key')
  localStorage.removeItem('user_name')
  ElMessage.success('已退出登录')
  router.push('/')
}

function pushMessage(role, content) {
  messages.value.push({ id: `${Date.now()}-${Math.random()}`, role, content })
}

async function loadHistory() {
  if (!userKey.value) return
  try {
    const { data } = await request.get('/interview/history')
    historyList.value = data?.data || []
  } catch (error) {
    console.error(error)
  }
}

async function loadGrowth() {
  if (!userKey.value) return
  try {
    const { data } = await request.get('/interview/growth', { params: { role_code: roleCode.value } })
    growthData.value = data?.data || {
      labels: [], scores: [], technical_scores: [], depth_scores: [], logic_scores: [], role_match_scores: [], speech_rate_scores: [], clarity_scores: [], confidence_scores: [], expression_scores: [], sessions: []
    }
  } catch (error) {
    console.error(error)
  }
}

function buildGrowthOption() {
  const labels = growthData.value?.labels || []
  const values = growthSeriesValues.value
  return {
    animation: true,
    grid: { left: 32, right: 20, top: 30, bottom: 34 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15,23,42,0.92)',
      borderWidth: 0,
      textStyle: { color: '#fff' },
      formatter(params) {
        const item = params?.[0]
        if (!item) return ''
        return `${item.axisValue}<br/>${growthMetricLabel.value}：${item.data}`
      }
    },
    xAxis: {
      type: 'category',
      data: labels,
      boundaryGap: false,
      axisLabel: {
        show: false
      },
      axisLine: { lineStyle: { color: '#dbe5f5' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 10,
      interval: 2,
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e5edf8' } }
    },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { width: 4, color: '#3b82f6' },
      itemStyle: { color: '#2563eb', borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(59,130,246,0.28)' },
        { offset: 1, color: 'rgba(59,130,246,0.02)' }
      ]) }
    }]
  }
}

function renderGrowthChart() {
  if (!growthChartRef.value) return
  if (!growthChartInstance) {
    growthChartInstance = echarts.init(growthChartRef.value)
  }
  growthChartInstance.setOption(buildGrowthOption(), true)
}

function handleResize() {
  growthChartInstance?.resize()
}

async function startInterview() {
  if (!userKey.value) {
    ElMessage.warning('请先登录')
    return
  }
  if (sessionId.value) {
    try {
      await ElMessageBox.confirm('当前有未结束面试，重新开始会清空当前页面记录，是否继续？', '提示', { type: 'warning' })
    } catch {
      return
    }
  }
  stopVoiceRecognitionSilently()
  starting.value = true
  try {
    const { data } = await request.post('/interview/start', {
      role_code: roleCode.value,
      question_count: questionCount.value
    })
    const res = data?.data
    resetInterviewState()
    sessionId.value = res.session_id
    currentQuestionNo.value = res.question_no
    currentQuestion.value = res.question
    status.value = 'running'
    pushMessage('assistant', `欢迎参加 ${res.role_name} 模拟面试。第 ${res.question_no} 题：${res.question.title}`)
    ElMessage.success('面试开始成功')
  } catch (error) {
    showRequestError(error, '面试开始失败')
  } finally {
    starting.value = false
  }
}

async function submitAnswer() {
  const content = inputMessage.value.trim()
  if (isVoiceRecording.value) {
    ElMessage.warning('请先点击“结束语音输入”，再提交回答')
    return
  }
  if (!content || !sessionId.value || !currentQuestion.value) {
    ElMessage.warning('请先输入回答内容')
    return
  }
  submitting.value = true
  try {
    if (pendingFollowup.value) {
      const currentNo = currentFollowupNo.value || 1
      const currentTurn = currentFollowupTurns.value.find(item => item.followup_no === currentNo)
      if (currentTurn) currentTurn.answer_text = content
      const { data } = await request.post('/interview/followup-answer', {
        session_id: sessionId.value,
        question_no: currentQuestionNo.value,
        followup_no: currentNo,
        followup_answer: content
      })
      pushMessage('user', content)
      const res = data?.data || {}
      inputMessage.value = ''
      voiceCommittedText.value = ''
      lastExpressionMetrics.value = null
      if (res.need_followup && res.followup_question) {
        pendingFollowup.value = res.followup_question
        currentFollowupNo.value = res.followup_no || currentNo + 1
        currentFollowupTurns.value.push({ followup_no: currentFollowupNo.value, question_text: res.followup_question, answer_text: '' })
        pushMessage('assistant', `【追问 ${currentFollowupNo.value}】${res.followup_question}`)
        status.value = 'running'
        ElMessage.success(res.message || '请继续回答追问')
      } else {
        pendingFollowup.value = ''
        currentFollowupNo.value = 0
        pushMessage('assistant', res.message || '本题追问已完成。你可以点击“下一题”，继续后续面试。')
        status.value = 'answered'
        ElMessage.success(res.message || '追问回答已保存')
      }
      return
    }
    const payload = {
      session_id: sessionId.value,
      question_no: currentQuestionNo.value,
      answer_text: content,
      expression_metrics: lastExpressionMetrics.value || { input_mode: 'text' }
    }
    const { data } = await request.post('/interview/answer', payload)
    pushMessage('user', content)
    const res = data?.data
    analysisData.value = res?.round_analysis || null
    inputMessage.value = ''
    voiceCommittedText.value = ''
    lastExpressionMetrics.value = null
    if (res?.need_followup && res?.followup_question) {
      pendingFollowup.value = res.followup_question
      currentFollowupNo.value = res.followup_no || 1
      currentFollowupTurns.value = [{ followup_no: currentFollowupNo.value, question_text: res.followup_question, answer_text: '' }]
      pushMessage('assistant', `【追问 ${currentFollowupNo.value}】${res.followup_question}`)
      status.value = 'running'
      ElMessage.success('系统已生成追问，请继续回答')
    } else {
      pendingFollowup.value = ''
      currentFollowupNo.value = 0
      currentFollowupTurns.value = []
      pushMessage('assistant', '本题已分析完成。你可以点击“下一题”继续，也可以在最后点击“结束并生成报告”。')
      status.value = 'answered'
    }
  } catch (error) {
    showRequestError(error, '提交回答失败')
  } finally {
    submitting.value = false
  }
}

async function nextQuestion() {
  if (!sessionId.value) return
  nexting.value = true
  try {
    const { data } = await request.get('/interview/next-question', { params: { session_id: sessionId.value } })
    const res = data?.data
    if (res?.finished) {
      status.value = 'completed'
      currentQuestion.value = null
      pushMessage('assistant', res.message || '题目已全部完成，请结束面试生成报告。')
      ElMessage.success('当前面试题目已全部完成')
      return
    }
    currentQuestionNo.value = res.question_no
    currentFollowupNo.value = 0
    currentFollowupTurns.value = []
    currentQuestion.value = res.question
    pendingFollowup.value = ''
    analysisData.value = null
    inputMessage.value = ''
    status.value = 'running'
    pushMessage('assistant', `第 ${res.question_no} 题：${res.question.title}`)
  } catch (error) {
    showRequestError(error, '获取下一题失败')
  } finally {
    nexting.value = false
  }
}

async function finishInterview() {
  if (!sessionId.value) return
  finishing.value = true
  try {
    const { data } = await request.post('/interview/finish', { session_id: sessionId.value })
    reportData.value = data?.data || null
    status.value = 'completed'
    pushMessage('assistant', '面试已结束，系统已生成综合报告。请在下方查看评分、追问复盘和推荐资源。')
    ElMessage.success('报告生成成功')
    await loadHistory()
    await loadGrowth()
  } catch (error) {
    showRequestError(error, '生成报告失败')
  } finally {
    finishing.value = false
  }
}

function resetPage() { resetInterviewState() }

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    speechAvailable.value = false
    return
  }
  speechAvailable.value = true
  recognition.value = new SpeechRecognition()
  recognition.value.lang = 'zh-CN'
  recognition.value.continuous = false
  recognition.value.interimResults = true
  recognition.value.maxAlternatives = 1
  recognition.value.onresult = (event) => {
    let interimText = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i]
      const transcript = result[0]?.transcript || ''
      const confidence = result[0]?.confidence
      if (typeof confidence === 'number' && confidence > 0) confidenceList.value.push(confidence)
      if (result.isFinal) voiceCommittedText.value += transcript
      else interimText += transcript
    }
    inputMessage.value = `${voiceCommittedText.value}${interimText}`.trim()
  }
  recognition.value.onend = () => {
    const now = Date.now()
    if (lastSpeechEndAt.value) {
      const gap = now - lastSpeechEndAt.value
      if (gap > 800) pauseCount.value += 1
    }
    lastSpeechEndAt.value = now
    if (!manualStop.value && isVoiceRecording.value) {
      setTimeout(() => { try { recognition.value?.start() } catch (e) { console.warn('语音识别自动重启失败：', e) } }, 200)
    }
  }
  recognition.value.onerror = (event) => {
    const err = event?.error || ''
    console.warn('浏览器语音识别错误：', err, event)
    if (err === 'not-allowed' || err === 'service-not-allowed') {
      ElMessage.error('语音权限未开启，请允许浏览器使用麦克风')
      manualStop.value = true
      isVoiceRecording.value = false
      return
    }
    if (err === 'audio-capture') {
      ElMessage.error('未检测到可用麦克风，请检查设备')
      manualStop.value = true
      isVoiceRecording.value = false
    }
  }
}

function startVoiceInput() {
  if (!speechAvailable.value || !recognition.value) {
    ElMessage.warning('当前浏览器不支持语音识别，建议使用 Chrome 或 Edge')
    return
  }
  if (isVoiceRecording.value) return
  manualStop.value = false
  isVoiceRecording.value = true
  speechStartAt.value = Date.now()
  confidenceList.value = []
  pauseCount.value = 0
  lastSpeechEndAt.value = 0
  voiceCommittedText.value = inputMessage.value ? `${inputMessage.value} ` : ''
  lastExpressionMetrics.value = null
  try {
    recognition.value.start()
    ElMessage.success('语音输入已开始，请说话。停顿不会结束，结束时请手动点击“结束语音输入”')
  } catch (e) {
    console.warn('启动语音识别失败：', e)
    isVoiceRecording.value = false
    ElMessage.error('启动语音输入失败')
  }
}

function stopVoiceInput() {
  if (!recognition.value || !isVoiceRecording.value) return
  manualStop.value = true
  isVoiceRecording.value = false
  try { recognition.value.stop() } catch (e) { console.warn('停止语音识别失败：', e) }
  const durationSec = speechStartAt.value ? (Date.now() - speechStartAt.value) / 1000 : 0
  const avgConfidence = confidenceList.value.length ? confidenceList.value.reduce((a, b) => a + b, 0) / confidenceList.value.length : 0
  lastExpressionMetrics.value = {
    input_mode: 'voice',
    duration_sec: Number(durationSec.toFixed(2)),
    recognized_text_length: (voiceCommittedText.value || inputMessage.value || '').replace(/\s+/g, '').length,
    avg_confidence: Number(avgConfidence.toFixed(3)),
    pause_count: pauseCount.value
  }
  ElMessage.success('语音输入已结束')
}

watch(roleCode, async () => {
  if (userKey.value) await loadGrowth()
})
watch([growthData, selectedGrowthMetric], async () => {
  await nextTick()
  renderGrowthChart()
}, { deep: true })

onMounted(async () => {
  userKey.value = localStorage.getItem('user_key') || localStorage.getItem('user_name') || ''
  initSpeechRecognition()
  await loadHistory()
  await loadGrowth()
  await nextTick()
  renderGrowthChart()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  stopVoiceRecognitionSilently()
  window.removeEventListener('resize', handleResize)
  if (growthChartInstance) {
    growthChartInstance.dispose()
    growthChartInstance = null
  }
})
</script>

<template>
  <div class="chat-page">
    <aside class="sidebar">
      <div class="brand-card">
        <div class="brand-tag">项目实战版</div>
        <h2>AI 模拟面试平台</h2>
        <p>面向技术岗位的多轮模拟面试系统，支持文本/语音回答、动态追问、多维评分与知识增强分析。</p>
      </div>

      <div class="panel-card compact-card">
        <div class="panel-title">面试配置</div>
        <el-form label-position="top">
          <el-form-item label="当前用户">
            <el-input :model-value="userKey || '未登录'" disabled />
          </el-form-item>
          <el-form-item label="目标岗位">
            <el-select v-model="roleCode" style="width: 100%" :disabled="(!!sessionId && status !== 'completed' && status !== 'idle') || anyBusy">
              <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="面试题数">
            <el-input-number v-model="questionCount" :min="1" :max="10" style="width: 100%" :disabled="anyBusy || !!sessionId" />
          </el-form-item>
          <div class="btn-column">
            <el-button type="primary" :loading="starting" :disabled="anyBusy" @click="startInterview"><el-icon><Position /></el-icon>开始面试</el-button>
            <el-button :disabled="anyBusy" @click="resetPage"><el-icon><Refresh /></el-icon>清空页面</el-button>
            <el-button type="danger" plain :disabled="anyBusy" @click="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-button>
          </div>
        </el-form>
      </div>

      <div class="panel-card compact-card">
        <div class="panel-title">历史记录</div>
        <div v-if="historyList.length" class="history-list">
          <div v-for="item in historyList.slice(0, 5)" :key="item.id" class="history-item">
            <div class="history-role">{{ getRoleLabel(item.role_code) }}</div>
            <div class="history-time">{{ item.start_time }}</div>
            <div class="history-score">{{ item.status === 'finished' ? '总分：' + formatHistoryScore(item) : '状态：' + formatHistoryStatus(item) }}</div>
            <a v-if="item.report_docx_url" :href="item.report_docx_url" target="_blank" class="history-link">查看报告</a>
          </div>
        </div>
        <el-empty v-else description="暂无历史记录" :image-size="64" />
      </div>

      <div class="panel-card growth-card">
        <div class="growth-header">
          <div class="panel-title growth-title">成长趋势</div>
          <div class="growth-metric-value">{{ growthMetricLabel }}</div>
        </div>
        <div class="growth-toolbar">
          <el-select v-model="selectedGrowthMetric" size="small" class="metric-select">
            <el-option v-for="item in growthMetricOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </div>
        <div v-if="growthSeriesValues.length" class="growth-chart-wrap">
          <div ref="growthChartRef" class="growth-chart"></div>
          <div class="growth-summary-row">
            <div class="growth-summary-item"><span>最近一次</span><strong>{{ growthMetricSummary.latest }}</strong></div>
            <div class="growth-summary-item"><span>平均分</span><strong>{{ growthMetricSummary.avg }}</strong></div>
            <div class="growth-summary-item"><span>最高分</span><strong>{{ growthMetricSummary.max }}</strong></div>
          </div>
        </div>
        <el-empty v-else description="完成面试后会显示趋势" :image-size="64" />
      </div>
    </aside>

    <main class="workspace">
      <section class="top-overview">
        <section class="interview-card current-question-card">
          <div class="question-top">
            <div>
              <div class="panel-tag">当前流程</div>
              <h3>{{ currentRoleLabel }}</h3>
              <p>状态：{{ status === 'idle' ? '未开始' : status === 'running' ? '面试进行中' : status === 'answered' ? '等待下一题/结束' : '已完成' }}</p>
            </div>
          </div>
          <div v-if="currentQuestion" class="question-box">
            <div class="question-no">第 {{ currentQuestionNo }} 题</div>
            <div class="question-text">{{ currentQuestion.title }}</div>
            <div class="question-meta">类型：{{ currentQuestion.question_type }} ｜ 难度：{{ currentQuestion.difficulty }}</div>
          </div>
          <el-empty v-else description="点击左侧“开始面试”后，题目会显示在这里" :image-size="90" />
        </section>

        <section class="panel-card quick-analysis-card">
          <div class="panel-title">本题评分</div>
          <div v-if="analysisData" class="score-grid compact-score-grid">
            <div class="score-item"><span>技术</span><strong>{{ analysisData.technical_score }}</strong></div>
            <div class="score-item"><span>深度</span><strong>{{ analysisData.depth_score }}</strong></div>
            <div class="score-item"><span>逻辑</span><strong>{{ analysisData.logic_score }}</strong></div>
            <div class="score-item"><span>匹配</span><strong>{{ analysisData.role_match_score }}</strong></div>
            <div class="score-item"><span>语速</span><strong>{{ analysisData.speech_rate_score }}</strong></div>
            <div class="score-item"><span>清晰度</span><strong>{{ analysisData.clarity_score }}</strong></div>
            <div class="score-item"><span>自信度</span><strong>{{ analysisData.confidence_score }}</strong></div>
          </div>
          <el-empty v-else description="提交回答后显示本题分析" :image-size="72" />
        </section>
      </section>

      <section class="interview-card dialogue-card">
        <div class="dialogue-head">
          <div class="panel-title">面试对话</div>
          <div class="dialogue-tip">支持文本输入，也支持浏览器语音识别</div>
        </div>
        <div class="dialogue-list">
          <div v-for="item in messages" :key="item.id" class="dialogue-item" :class="item.role">
            <div class="avatar"><el-icon v-if="item.role === 'assistant'"><Opportunity /></el-icon><el-icon v-else><User /></el-icon></div>
            <div class="bubble">{{ item.content }}</div>
          </div>
        </div>
        <div v-if="pendingFollowup" class="followup-banner">当前存在追问，请先回答追问：{{ pendingFollowup }}</div>
        <div class="composer">
          <el-input v-model="inputMessage" type="textarea" :rows="4" resize="none" maxlength="1200" show-word-limit :disabled="submitting || nexting || finishing || isVoiceRecording" :placeholder="pendingFollowup ? '请回答当前追问...' : '请输入你的回答内容...'" />
          <div v-if="isVoiceRecording" class="recording-tip">正在语音输入中。中途停顿不会结束，请点击“结束语音输入”完成本次语音回答。</div>
          <div class="composer-actions">
            <div class="left-actions">
              <el-button v-if="!isVoiceRecording" :disabled="!speechAvailable || anyBusy" @click="startVoiceInput"><el-icon><Microphone /></el-icon>开始语音输入</el-button>
              <el-button v-else type="danger" :disabled="submitting || nexting || finishing" @click="stopVoiceInput"><el-icon><Microphone /></el-icon>结束语音输入</el-button>
              <el-button type="primary" :disabled="!canSendAnswer" :loading="submitting" @click="submitAnswer"><el-icon><Position /></el-icon>{{ pendingFollowup ? '提交追问回答' : '提交当前回答' }}</el-button>
            </div>
            <div class="right-actions">
              <el-button :disabled="!canNextQuestion || isVoiceRecording" :loading="nexting" @click="nextQuestion"><el-icon><ArrowRight /></el-icon>下一题</el-button>
              <el-button type="success" :disabled="!canFinish || isVoiceRecording" :loading="finishing" @click="finishInterview"><el-icon><Check /></el-icon>结束并生成报告</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="report-grid">
        <section class="panel-card detail-card">
          <div class="panel-title">亮点 / 不足 / 建议</div>
          <div v-if="analysisData" class="analysis-detail">
            <div class="detail-block"><div class="detail-title">亮点</div><ul><li v-for="(item, index) in analysisData.strengths" :key="index">{{ item }}</li></ul></div>
            <div class="detail-block"><div class="detail-title">不足</div><ul><li v-for="(item, index) in analysisData.weaknesses" :key="index">{{ item }}</li></ul></div>
            <div class="detail-block"><div class="detail-title">建议</div><ul><li v-for="(item, index) in analysisData.suggestions" :key="index">{{ item }}</li></ul></div>
          </div>
          <el-empty v-else description="等待系统分析" :image-size="72" />
        </section>

        <section class="panel-card detail-card">
          <div class="panel-title">当前题追问记录</div>
          <div v-if="currentFollowupTurns.length" class="followup-turn-list">
            <div v-for="item in currentFollowupTurns" :key="item.followup_no" class="followup-turn-item">
              <div class="followup-turn-title">追问 {{ item.followup_no }}</div>
              <div class="followup-turn-question">问题：{{ item.question_text }}</div>
              <div class="followup-turn-answer">回答：{{ item.answer_text || '待回答' }}</div>
            </div>
          </div>
          <el-empty v-else description="当前题暂无追问记录" :image-size="72" />
        </section>

        <section class="panel-card final-report-card report-span-full">
          <div class="panel-title">综合报告</div>
          <div v-if="reportData" class="report-content">
            <div class="report-top-grid">
              <div class="report-summary-block">
                <div class="report-title-row"><el-icon><DataAnalysis /></el-icon><span>维度总分</span></div>
                <div class="modern-score-list">
                  <div class="report-score-chip">技术：{{ reportData.score_summary.technical_score }}</div>
                  <div class="report-score-chip">深度：{{ reportData.score_summary.depth_score }}</div>
                  <div class="report-score-chip">逻辑：{{ reportData.score_summary.logic_score }}</div>
                  <div class="report-score-chip">匹配：{{ reportData.score_summary.role_match_score }}</div>
                  <div class="report-score-chip">语速：{{ reportData.score_summary.speech_rate_score }}</div>
                  <div class="report-score-chip">清晰度：{{ reportData.score_summary.clarity_score }}</div>
                  <div class="report-score-chip">自信度：{{ reportData.score_summary.confidence_score }}</div>
                  <div class="report-score-chip report-score-chip-strong">综合：{{ reportData.score_summary.total_score }}</div>
                </div>
              </div>
              <div class="report-summary-block">
                <div class="report-title-row"><el-icon><Document /></el-icon><span>总结</span></div>
                <div class="summary-text">{{ reportData.summary }}</div>
              </div>
            </div>
            <div class="report-summary-block" v-if="reportData.rounds?.length">
              <div class="report-title-row"><el-icon><Opportunity /></el-icon><span>逐题追问复盘</span></div>
              <div v-for="round in reportData.rounds" :key="round.question_no" class="report-round-block">
                <div class="report-round-title">第 {{ round.question_no }} 题：{{ round.question_text }}</div>
                <div class="report-round-answer">主回答：{{ round.answer_text || '无' }}</div>
                <div v-if="round.followup_turns?.length" class="report-followup-turns">
                  <div v-for="turn in round.followup_turns" :key="turn.followup_no" class="report-followup-item">
                    <div>追问 {{ turn.followup_no }}：{{ turn.question_text }}</div>
                    <div>回答 {{ turn.followup_no }}：{{ turn.answer_text || '无' }}</div>
                  </div>
                </div>
                <div v-else class="report-followup-item">本题无追问</div>
              </div>
            </div>
            <div class="report-summary-block">
              <div class="report-title-row"><el-icon><Opportunity /></el-icon><span>推荐资源</span></div>
              <ul v-if="reportData.recommendations?.length" class="modern-resource-list">
                <li v-for="item in reportData.recommendations" :key="item.id" class="resource-card-item">
                  <div class="resource-title">{{ item.title }}</div>
                  <div class="resource-desc">{{ item.content }}</div>
                  <div v-if="item.reason" class="resource-reason">推荐原因：{{ item.reason }}</div>
                  <a v-if="item.link" :href="item.link" target="_blank">打开链接</a>
                </li>
              </ul>
              <el-empty v-else description="当前暂无推荐资源" :image-size="64" />
            </div>
            <el-button v-if="reportData.report_docx_url" type="primary" plain :href="reportData.report_docx_url" tag="a" target="_blank">下载 Word 报告</el-button>
          </div>
          <el-empty v-else description="结束面试后生成综合报告" :image-size="72" />
        </section>
      </section>
    </main>
  </div>
</template>

<style scoped>
.chat-page { min-height: 100vh; display: grid; grid-template-columns: 320px minmax(0,1fr); gap: 20px; padding: 20px; background: linear-gradient(180deg,#f4f7fb 0%,#eef3fb 100%); box-sizing: border-box; }
.sidebar,.workspace { display:flex; flex-direction:column; gap:16px; }
.panel-card,.interview-card,.brand-card { background: rgba(255,255,255,0.96); border-radius: 22px; box-shadow: 0 12px 32px rgba(31,45,61,0.08); padding: 18px; backdrop-filter: blur(8px); }
.brand-card h2,.question-top h3 { margin:8px 0; }
.brand-card p { line-height:1.7; color:#516173; }
.brand-tag,.panel-tag { display:inline-block; padding:4px 10px; border-radius:999px; background:#edf4ff; color:#2b6de5; font-size:12px; }
.panel-title { font-size:16px; font-weight:700; margin-bottom:12px; }
.compact-card { padding:16px; }
.btn-column,.composer-actions,.left-actions,.right-actions,.report-title-row,.question-top,.dialogue-head,.growth-header { display:flex; align-items:center; gap:10px; }
.btn-column { flex-direction:column; align-items:stretch; }
.history-list { display:flex; flex-direction:column; gap:10px; }
.history-item { padding:12px; border-radius:16px; background:#f7f9fc; }
.history-role { font-weight:700; margin-bottom:4px; }
.history-time,.history-score,.history-link { font-size:12px; color:#667085; }
.growth-title { margin-bottom:0; }
.growth-metric-value { margin-left:auto; padding:4px 10px; border-radius:999px; background:#eef4ff; color:#1d4ed8; font-size:12px; font-weight:700; }
.metric-select { width:100%; }
.growth-chart-wrap { display:flex; flex-direction:column; gap:14px; }
.growth-chart { width:100%; height:280px; }
.growth-summary-row { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.growth-summary-item { padding:12px; border-radius:16px; background:#eef4ff; display:flex; flex-direction:column; gap:6px; }
.growth-summary-item span { font-size:12px; color:#64748b; }
.growth-summary-item strong { font-size:20px; color:#1d4ed8; }
.workspace { min-width:0; }
.top-overview { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(320px,0.8fr); gap:16px; }
.current-question-card .question-box { margin-top:12px; padding:18px; border-radius:18px; background: linear-gradient(135deg,#eff6ff,#f9fbff); }
.question-no { color:#2b6de5; font-weight:700; margin-bottom:8px; }
.question-text { font-size:18px; line-height:1.7; margin-bottom:8px; }
.question-meta { color:#667085; font-size:13px; }
.quick-analysis-card { height:100%; }
.compact-score-grid { grid-template-columns:repeat(2,1fr); }
.dialogue-card { display:flex; flex-direction:column; min-height:560px; }
.dialogue-tip { color:#64748b; font-size:13px; }
.dialogue-list { min-height:360px; max-height:560px; overflow:auto; padding:12px 4px; display:flex; flex-direction:column; gap:14px; }
.dialogue-item { display:flex; gap:10px; }
.dialogue-item.user { flex-direction:row-reverse; }
.avatar { width:38px; height:38px; border-radius:50%; background:#eef2ff; color:#2b6de5; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.bubble { max-width:78%; padding:12px 14px; border-radius:16px; line-height:1.75; background:#f5f7fb; color:#1f2937; white-space:pre-wrap; }
.dialogue-item.user .bubble { background: linear-gradient(135deg,#2b6de5,#4f8cff); color:#fff; }
.composer { border-top:1px solid #eef2f6; padding-top:16px; margin-top:auto; }
.followup-banner { margin:10px 0; padding:10px 12px; border-radius:14px; background:#fff7e8; color:#9a6700; }
.recording-tip { margin:10px 0; padding:10px 12px; border-radius:14px; background:#eef6ff; color:#1d4ed8; line-height:1.7; }
.left-actions,.right-actions { flex-wrap:wrap; }
.composer-actions { justify-content:space-between; flex-wrap:wrap; margin-top:12px; }
.score-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.score-item { padding:14px; border-radius:16px; background:#f7f9fc; display:flex; flex-direction:column; gap:8px; }
.score-item strong { font-size:22px; color:#2b6de5; }
.report-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px; }
.report-span-full { grid-column:1 / -1; }
.analysis-detail,.report-content,.followup-turn-list,.report-followup-turns { display:flex; flex-direction:column; gap:14px; }
.detail-block,.report-summary-block,.followup-turn-item,.report-round-block { padding:14px; border-radius:16px; background:#f7f9fc; }
.detail-title,.resource-title,.followup-turn-title,.report-round-title { font-weight:700; margin-bottom:8px; color:#2b6de5; }
.summary-text,.resource-desc,.followup-turn-question,.followup-turn-answer,.report-round-answer,.report-followup-item { white-space:pre-wrap; line-height:1.8; }
.report-top-grid { display:grid; grid-template-columns:320px minmax(0,1fr); gap:16px; }
.modern-score-list { display:flex; flex-wrap:wrap; gap:10px; }
.report-score-chip { padding:8px 12px; border-radius:999px; background:#edf4ff; color:#1d4ed8; font-weight:600; }
.report-score-chip-strong { background: linear-gradient(135deg,#2b6de5,#4f8cff); color:#fff; }
.modern-resource-list { list-style:none; padding-left:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }
.resource-card-item { padding:14px; border-radius:16px; background:#fff; border:1px solid #e8eef8; }
.resource-reason { margin-top:6px; color:#475467; font-size:13px; line-height:1.7; }
@media (max-width: 1400px) { .chat-page { grid-template-columns:300px minmax(0,1fr); } .top-overview,.report-top-grid { grid-template-columns:1fr; } }
@media (max-width: 1100px) { .chat-page { grid-template-columns:1fr; } .report-grid,.growth-summary-row { grid-template-columns:1fr; } .dialogue-card { min-height:460px; } }
</style>
