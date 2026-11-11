/**
 * src/api/user.ts —— 用户模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/user.ts（当前 localStorage 存账号）。
 * 假定的后端接口约定（可按真实后端调整路径）：
 *   POST /api/auth/register  {username, password} → User
 *   POST /api/auth/login     {username, password} → { token, user }
 *   POST /api/auth/logout    → null
 *   GET  /api/user/profile   → User
 *
 * store → api 迁移对应（将来联调时替换）：
 *   register() → apiRegister    login() → apiLogin    logout() → apiLogout
 */
import { request, setToken, clearToken } from './request'

/** 后端用户结构（字段对齐 stores/user.ts 的 User，迁移成本最低） */
export interface ApiUser {
  username: string
  createdAt?: number
}

/** 注册新用户 */
export function apiRegister(username: string, password: string) {
  return request<ApiUser>('POST', '/auth/register', { username, password })
}

/** 登录：成功后自动把 token 存入 localStorage（之后 request() 每次自动带上） */
export function apiLogin(username: string, password: string) {
  return request<{ token: string; user: ApiUser }>('POST', '/auth/login', {
    username,
    password
  }).then(res => {
    setToken(res.token)
    return res
  })
}

/** 登出：通知后端作废 token + 清本地 token */
export function apiLogout() {
  return request<null>('POST', '/auth/logout').then(res => {
    clearToken()
    return res
  })
}

/** 获取当前登录用户的个人信息 */
export function apiGetProfile() {
  return request<ApiUser>('GET', '/user/profile')
}
