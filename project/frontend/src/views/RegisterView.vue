<script setup lang="ts">
/**
 * RegisterView.vue - 独立注册页
 * ----------------------------------------------------------------
 * 功能与 LoginView 的注册标签一致，注册成功后跳转登录页
 * （主要用于 /register 路由直接访问）
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '@/stores/user'

const router = useRouter()

const regForm = reactive({ username: '', password: '', confirm: '' })
const regMsg = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

const handleRegister = async () => {
  regMsg.value = null
  if (regForm.password !== regForm.confirm) {
    regMsg.value = { type: 'err', text: '两次密码输入不一致' }
    return
  }
  const result = await register(regForm.username, regForm.password)
  if (result.ok) {
    regMsg.value = { type: 'ok', text: result.msg }
    setTimeout(() => {
      router.push({ path: '/login', query: { username: regForm.username } })
    }, 800)
  } else {
    regMsg.value = { type: 'err', text: result.msg }
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="9" cy="21" r="1" />
          <circle cx="20" cy="21" r="1" />
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
        </svg>
        <span>注册账号</span>
      </div>

      <form class="auth-form" @submit.prevent="handleRegister">
        <div class="auth-field">
          <label>账号</label>
          <input v-model="regForm.username" type="text" placeholder="至少 2 个字符" />
        </div>
        <div class="auth-field">
          <label>密码</label>
          <input v-model="regForm.password" type="password" placeholder="至少 4 个字符" />
        </div>
        <div class="auth-field">
          <label>确认密码</label>
          <input v-model="regForm.confirm" type="password" placeholder="再次输入密码" />
        </div>
        <div v-if="regMsg" class="auth-msg" :class="regMsg.type">
          {{ regMsg.text }}
        </div>
        <button type="submit" class="auth-submit">注 册</button>
        <p class="auth-switch">
          已有账号？<a href="javascript:void(0)" @click="router.push('/login')">去登录</a>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 64px - 49px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  background-color: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

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
