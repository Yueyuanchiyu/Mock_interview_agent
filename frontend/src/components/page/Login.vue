<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Message, Promotion } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const sending = ref(false)
const loggingIn = ref(false)
const loginEmail = ref('')
const loginCode = ref('')

const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/


function showLoginError(error, fallbackText = '操作失败，请稍后重试') {
  console.error(error)
  const detail =
    error?.response?.data?.msg ||
    error?.response?.data?.detail ||
    error?.message ||
    fallbackText
  ElMessage.error(detail)
}

function validateEmail(email) {
  if (!email) {
    ElMessage.warning('请输入邮箱地址')
    return false
  }
  if (!emailReg.test(email)) {
    ElMessage.warning('请输入正确的邮箱格式')
    return false
  }
  return true
}

async function sendCode() {
  if (sending.value) return

  const email = loginEmail.value.trim()
  if (!validateEmail(email)) return

  sending.value = true
  try {
    const { data } = await request.post('/sendCode', { email }, { timeout: 120000 })
    if (data?.code === 200) {
      ElMessage.success(data.msg || '验证码已发送，请注意查收邮箱')
    } else {
      ElMessage.error(data?.msg || '验证码发送失败，请稍后重试')
    }
  } catch (error) {
    console.error(error)
    if (error?.code === 'ECONNABORTED') {
      ElMessage.warning('请求时间较长，请先查看邮箱，验证码可能已经发送成功')
    } else {
      showLoginError(error, '验证码发送失败，请稍后重试')
    }
  } finally {
    sending.value = false
  }
}

async function login() {
  if (loggingIn.value) return

  const email = loginEmail.value.trim()
  const code = loginCode.value.trim()

  if (!validateEmail(email)) return
  if (!code) {
    ElMessage.warning('请输入验证码')
    return
  }

  loggingIn.value = true
  try {
    const { data } = await request.post('/login', { email, code })
    if (data?.code === 200) {
      const auth = data?.data || {}
      localStorage.setItem('access_token', auth.access_token || '')
      localStorage.setItem('user_key', auth.user_key || email)
      localStorage.setItem('user_name', auth.user_name || email)
      ElMessage.success(data.msg || '登录成功')
      router.push('/chat')
    } else {
      ElMessage.error(data?.msg || '登录失败，请稍后重试')
    }
  } catch (error) {
    showLoginError(error, '登录失败，请稍后重试')
  } finally {
    loggingIn.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="brand-panel">
        <div class="brand-badge">智能模拟面试平台</div>
        <h1>智能面试助手</h1>
        <p>
          支持模拟面试、语音输入、结果分析与练习复盘，
          帮助你更高效地完成面试训练与能力提升。
        </p>

        <div class="brand-grid">
          <div class="brand-card">
            <div class="brand-card__title">模拟面试训练</div>
            <div class="brand-card__desc">围绕目标岗位与科目开展多轮问答练习，提升答题质量与表达能力。</div>
          </div>
          <div class="brand-card">
            <div class="brand-card__title">语音输入支持</div>
            <div class="brand-card__desc">支持语音识别输入，让面试训练更贴近真实交流场景。</div>
          </div>
          <div class="brand-card">
            <div class="brand-card__title">结果分析反馈</div>
            <div class="brand-card__desc">从内容、表达与综合表现等维度给出反馈建议，帮助你持续改进。</div>
          </div>
          <div class="brand-card">
            <div class="brand-card__title">练习过程沉淀</div>
            <div class="brand-card__desc">保留练习记录与分析结果，方便复盘总结和阶段性提升。</div>
          </div>
        </div>
      </section>

      <section class="form-panel">
        <div class="panel-header">
          <div>
            <div class="panel-caption">Welcome back</div>
            <h2>邮箱验证码登录</h2>
          </div>
          <div class="panel-dot"></div>
        </div>

        <div class="single-auth__tab">安全登录</div>

        <div class="form-body">
          <el-form label-position="top" @submit.prevent>
            <el-form-item label="邮箱地址">
              <el-input v-model.trim="loginEmail" placeholder="请输入常用邮箱" :disabled="sending || loggingIn">
                <template #prefix>
                  <el-icon><Message /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="验证码">
              <div class="code-row">
                <el-input v-model.trim="loginCode" placeholder="请输入邮箱验证码" :disabled="loggingIn" @keyup.enter="login">
                  <template #prefix>
                    <el-icon><Lock /></el-icon>
                  </template>
                </el-input>
                <el-button class="code-btn" :loading="sending" :disabled="sending || loggingIn" @click="sendCode">
                  {{ sending ? '发送中...' : '发送验证码' }}
                </el-button>
              </div>
            </el-form-item>

            <el-button class="submit-btn" type="primary" :loading="loggingIn" :disabled="loggingIn || sending" @click="login">
              <el-icon><Promotion /></el-icon>
              <span>立即登录</span>
            </el-button>
          </el-form>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px;
  background:
    linear-gradient(120deg, rgba(9, 19, 46, 0.55), rgba(18, 52, 86, 0.18)),
    url('../../assets/image/login.jpeg') center/cover no-repeat;
}

.login-page::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 20%, rgba(255, 255, 255, 0.16), transparent 22%),
    radial-gradient(circle at 80% 15%, rgba(109, 178, 255, 0.2), transparent 20%),
    radial-gradient(circle at 85% 75%, rgba(91, 232, 182, 0.18), transparent 16%);
  pointer-events: none;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1280px, 100%);
  min-height: 760px;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.14);
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(18px);
}

.brand-panel {
  padding: 64px 56px;
  color: #f8fbff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(180deg, rgba(8, 15, 37, 0.3), rgba(8, 15, 37, 0.08));
}

.brand-badge {
  width: fit-content;
  margin-bottom: 24px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
  font-size: 13px;
  letter-spacing: 0.08em;
}

.brand-panel h1 {
  margin: 0;
  font-size: 46px;
  line-height: 1.2;
  letter-spacing: 0.02em;
}

.brand-panel p {
  max-width: 560px;
  margin: 22px 0 40px;
  font-size: 16px;
  line-height: 1.9;
  color: rgba(245, 250, 255, 0.85);
}

.brand-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: auto;
}

.brand-card {
  padding: 22px 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.brand-card__title {
  margin-bottom: 10px;
  font-size: 18px;
  font-weight: 700;
}

.brand-card__desc {
  font-size: 14px;
  line-height: 1.75;
  color: rgba(244, 250, 255, 0.8);
}

.form-panel {
  padding: 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: rgba(248, 251, 255, 0.9);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.panel-caption {
  margin-bottom: 10px;
  color: #4f6b95;
  font-size: 14px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.panel-header h2 {
  margin: 0;
  color: #11223f;
  font-size: 34px;
}

.panel-dot {
  width: 14px;
  height: 14px;
  margin-top: 14px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6a8dff, #68e1c6);
  box-shadow: 0 0 0 10px rgba(106, 141, 255, 0.08);
}

.single-auth__tab {
  display: inline-flex;
  margin-bottom: 24px;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(91, 120, 255, 0.12);
  color: #3152d9;
  font-weight: 700;
  font-size: 14px;
}

.form-body :deep(.el-form-item__label) {
  font-weight: 700;
  color: #0f172a;
}

.form-body :deep(.el-input__wrapper) {
  min-height: 50px;
  border-radius: 16px;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.2) inset;
}

.code-row {
  display: grid;
  grid-template-columns: 1fr 148px;
  gap: 14px;
}

.code-btn,
.submit-btn {
  height: 50px;
  border-radius: 16px;
}

.code-btn {
  border: 1px solid rgba(49, 82, 217, 0.12);
}

.submit-btn {
  width: 100%;
  margin-top: 10px;
  font-size: 16px;
  font-weight: 700;
}

.submit-btn :deep(.el-icon) {
  margin-right: 8px;
}

@media (max-width: 1100px) {
  .login-shell {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .brand-panel {
    display: none;
  }
}

@media (max-width: 768px) {
  .login-page {
    padding: 16px;
  }

  .form-panel {
    padding: 28px 20px;
  }

  .code-row {
    grid-template-columns: 1fr;
  }
}
</style>
