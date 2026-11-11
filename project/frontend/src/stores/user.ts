/**
 * stores/user.ts - 用户状态管理
 * ----------------------------------------------------------------
 * 账号注册、登录、登出，状态持久化到 localStorage
 * 注册数据也存 localStorage（仅用于 demo，不做后端校验）
 */
import { reactive, computed } from 'vue'
import { apiLogin, apiRegister, apiLogout } from '@/api/user'
import { clearToken } from '@/api/request'
import { clearCartState } from './cart'
import { clearFavoritesState } from './favorites'
import { clearOrdersState } from './orders'
import { clearCouponsState } from './coupons'
import { clearReviewsState } from './reviews'
import { clearFollowedShopsState } from './shops'
import { clearHistoryState } from './history'

// ====== 类型定义 ======
export interface User {
  username: string
  password: string  // demo 明文存储，实际应加密
  createdAt: number
}

export interface CurrentUser {
  username: string
  loginAt: number
}

// ====== localStorage 键名 ======
const USERS_KEY = 'shop_users'
const CURRENT_KEY = 'shop_current_user'

// ====== 工具函数 ======
const loadFromStorage = <T>(key: string, fallback: T): T => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

const saveToStorage = (key: string, value: unknown) => {
  localStorage.setItem(key, JSON.stringify(value))
}

// ====== 响应式状态 ======
const state = reactive({
  // 当前登录用户（null 表示未登录）
  current: loadFromStorage<CurrentUser | null>(CURRENT_KEY, null),
  // 已注册用户列表
  users: loadFromStorage<User[]>(USERS_KEY, [])
})

// ====== 计算属性 ======
export const isLoggedIn = computed(() => state.current !== null)
export const currentUsername = computed(() => state.current?.username ?? '')

// ====== 方法 ======

/** 注册 */
export async function register(username: string, password: string): Promise<{ ok: boolean; msg: string }> {
  // 校验
  if (!username.trim() || !password.trim()) {
    return { ok: false, msg: '账号和密码不能为空' }
  }
  if (username.length < 2) {
    return { ok: false, msg: '账号至少 2 个字符' }
  }
  if (password.length < 4) {
    return { ok: false, msg: '密码至少 4 个字符' }
  }
  // 检查是否已存在
  try { await apiRegister(username, password) } catch (e: any) { return { ok: false, msg: e.message || '注册失败' } }
  // 写入
  const user: User = { username, password, createdAt: Date.now() }
  state.users.push(user)
  saveToStorage(USERS_KEY, state.users)
  return { ok: true, msg: '注册成功，请登录' }
}

/** 登录 */
export async function login(username: string, password: string): Promise<{ ok: boolean; msg: string }> {
  let remote: any
  try { remote = await apiLogin(username, password) } catch (e: any) { return { ok: false, msg: e.message || '账号或密码错误' } }
  state.current = { username: remote.user.phone, loginAt: Date.now() }
  saveToStorage(CURRENT_KEY, state.current)
  return { ok: true, msg: '登录成功' }
}

/** 登出 */
export async function logout() {
  // 后端登出失败也不能阻止本地登出，否则残留 token 会继续读取旧账号数据。
  // request() 会在这里同步读取当前 token，因此先启动请求再清理本地会话。
  const remoteLogout = apiLogout().catch(() => undefined)

  // 先清理本地会话，避免网络延迟期间旧账号数据仍可见。
  clearToken()
  state.current = null
  localStorage.removeItem(CURRENT_KEY)

  // 清理所有只属于当前账号的前端响应式状态及其本地缓存。
  clearCartState()
  clearFavoritesState()
  clearOrdersState()
  clearCouponsState()
  clearReviewsState()
  clearFollowedShopsState()
  clearHistoryState()

  // 后端登出失败不影响本地退出结果。
  await remoteLogout
}
