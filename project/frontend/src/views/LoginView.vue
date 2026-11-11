<script setup lang="ts">
/**
 * LoginView.vue - 登录/注册页
 * ----------------------------------------------------------------
 * 上方切换标签页：登录 / 注册
 * 登录成功 → 跳转 redirect 参数或 /profile
 * 注册成功 → 切换回登录标签并预填账号
 */
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login, register } from '@/stores/user'

const route = useRoute()
const router = useRouter()

// 当前激活的标签：'login' | 'register'
const activeTab = ref<'login' | 'register'>('login')

// 登录表单
const loginForm = reactive({ username: '', password: '' })
const loginMsg = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

// 注册表单
const regForm = reactive({ username: '', password: '', confirm: '' })
const regMsg = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

// 提交登录
const handleLogin = async () => {
  loginMsg.value = null
  const result = await login(loginForm.username, loginForm.password)
  if (result.ok) {
    loginMsg.value = { type: 'ok', text: result.msg }
    // 延迟跳转，让用户看到成功提示
    setTimeout(() => {
      const redirect = (route.query.redirect as string) || '/profile'
      router.push(redirect)
    }, 500)
  } else {
    loginMsg.value = { type: 'err', text: result.msg }
  }
}

// 提交注册
const handleRegister = async () => {
  regMsg.value = null
  if (regForm.password !== regForm.confirm) {
    regMsg.value = { type: 'err', text: '两次密码输入不一致' }
    return
  }
  const result = await register(regForm.username, regForm.password)
  if (result.ok) {
    regMsg.value = { type: 'ok', text: result.msg }
    // 注册成功 → 切换到登录标签，预填账号
    setTimeout(() => {
      loginForm.username = regForm.username
      loginForm.password = ''
      activeTab.value = 'login'
      regForm.username = ''
      regForm.password = ''
      regForm.confirm = ''
      regMsg.value = null
    }, 800)
  } else {
    regMsg.value = { type: 'err', text: result.msg }
  }
}

// 回车提交
onMounted(() => {
  // 聚焦用户名输入框
  const input = document.querySelector<HTMLInputElement>('#login-username')
  input?.focus()
})
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo -->
      <div class="auth-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="9" cy="21" r="1" />
          <circle cx="20" cy="21" r="1" />
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
        </svg>
        <span>优选商城</span>
      </div>

      <!-- 标签切换 -->
      <div class="auth-tabs">
        <button
          class="auth-tab"
          :class="{ active: activeTab === 'login' }"
          @click="activeTab = 'login'"
        >登录</button>
        <button
          class="auth-tab"
          :class="{ active: activeTab === 'register' }"
          @click="activeTab = 'register'"
        >注册</button>
      </div>

      <!-- 登录表单 -->
      <form
        v-if="activeTab === 'login'"
        class="auth-form"
        @submit.prevent="handleLogin"
      >
        <div class="auth-field">
          <label>账号</label>
          <input
            id="login-username"
            v-model="loginForm.username"
            type="text"
            placeholder="请输入账号"
            autocomplete="username"
          />
        </div>
        <div class="auth-field">
          <label>密码</label>
          <input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </div>
        <!-- 提示消息 -->
        <div v-if="loginMsg" class="auth-msg" :class="loginMsg.type">
          {{ loginMsg.text }}
        </div>
        <button type="submit" class="auth-submit">登 录</button>
        <p class="auth-switch">
          还没有账号？
          <a href="javascript:void(0)" @click="activeTab = 'register'">去注册</a>
        </p>
      </form>

      <!-- 注册表单 -->
      <form
        v-else
        class="auth-form"
        @submit.prevent="handleRegister"
      >
        <div class="auth-field">
          <label>账号</label>
          <input
            v-model="regForm.username"
            type="text"
            placeholder="至少 2 个字符"
            autocomplete="username"
          />
        </div>
        <div class="auth-field">
          <label>密码</label>
          <input
            v-model="regForm.password"
            type="password"
            placeholder="至少 4 个字符"
            autocomplete="new-password"
          />
        </div>
        <div class="auth-field">
          <label>确认密码</label>
          <input
            v-model="regForm.confirm"
            type="password"
            placeholder="再次输入密码"
            autocomplete="new-password"
          />
        </div>
        <!-- 提示消息 -->
        <div v-if="regMsg" class="auth-msg" :class="regMsg.type">
          {{ regMsg.text }}
        </div>
        <button type="submit" class="auth-submit">注 册</button>
        <p class="auth-switch">
          已有账号？
          <a href="javascript:void(0)" @click="activeTab = 'login'">去登录</a>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* ====== 页面背景 ====== */
.auth-page {
  min-height: calc(100vh - 64px - 49px); /* 减去 header 和 footer */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* ====== 卡片 ====== */
.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  background-color: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

/* ====== Logo ====== */
.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 28px;
  font-size: 22px;
  font-weight: 700;
  color: #4f46e5;
}

.auth-logo svg {
  width: 28px;
  height: 28px;
}

/* ====== 标签切换 ====== */
.auth-tabs {
  display: flex;
  margin-bottom: 24px;
  background-color: #f3f4f6;
  border-radius: 9999px;
  padding: 4px;
}

.auth-tab {
  flex: 1;
  padding: 8px 0;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  background: none;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.auth-tab.active {
  color: #4f46e5;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* ====== 表单 ====== */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.auth-field label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.auth-field input {
  padding: 10px 14px;
  font-size: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  outline: none;
  transition: all 0.15s ease;
}

.auth-field input:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(165, 180, 252, 0.3);
}

/* ====== 提示消息 ====== */
.auth-msg {
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 6px;
}

.auth-msg.ok {
  color: #065f46;
  background-color: #d1fae5;
}

.auth-msg.err {
  color: #991b1b;
  background-color: #fee2e2;
}

/* ====== 提交按钮 ====== */
.auth-submit {
  margin-top: 8px;
  padding: 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(to right, #6366f1, #7c3aed);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.auth-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
}

/* ====== 切换链接 ====== */
.auth-switch {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
  text-align: center;
}

.auth-switch a {
  color: #4f46e5;
  text-decoration: none;
  font-weight: 500;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
