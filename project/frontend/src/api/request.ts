/**
 * src/api/request.ts —— 底层 HTTP 请求封装（基于原生 fetch，零依赖，不引入 axios）
 * ----------------------------------------------------------------
 * 职责（所有业务接口文件都通过这里的 request() 发请求）：
 *   1. 开关拦截：USE_BACKEND=false 时直接抛"后端未开启"，不发任何网络请求
 *   2. 统一拼接 URL：API_BASE_URL + API_PREFIX + url + querystring
 *   3. 统一注入请求头：Content-Type: application/json + Authorization: Bearer <token>
 *   4. 统一超时控制（AbortController，10 秒）
 *   5. 统一解析后端响应约定 { code, message, data }：code===0 才算成功，返回 data
 *   6. 统一错误：HTTP 401 清 token 提示重新登录；网络异常/超时抛 ApiError
 *
 * 后端响应格式约定（所有接口统一）：
 *   成功：{ "code": 0, "message": "ok", "data": <业务数据> }
 *   失败：{ "code": 非0, "message": "错误提示", "data": null }
 */
import {
  USE_BACKEND,
  API_BASE_URL,
  API_PREFIX,
  REQUEST_TIMEOUT,
  TOKEN_KEY
} from './config'

/** 统一业务错误类型：调用方 catch 后可用 err.code / err.message 精确提示 */
export class ApiError extends Error {
  code: number    // 业务错误码（后端 code 或前端约定的 -1/-2/-100）
  status: number  // HTTP 状态码（0 表示请求根本没发出去）
  constructor(message: string, code = -1, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

/* ============ token 三件套（登录态的"钥匙"） ============ */

/** 读取本地 token（request() 每次发请求自动带上） */
export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

/** 保存 token（apiLogin 成功后自动调用） */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/** 清除 token（apiLogout / 收到 401 时自动调用） */
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** 后端统一响应包裹结构 */
interface ApiEnvelope<T = unknown> {
  code: number     // 0 = 成功；非 0 = 业务失败
  message: string  // 提示文案（失败时可直接 alert 给用户）
  data: T          // 业务数据
}

/**
 * 通用请求方法
 * @param method HTTP 方法
 * @param url    相对路径，如 '/products/1001'（自动拼上 API_BASE_URL + API_PREFIX）
 * @param body   请求体对象（仅 POST/PUT/PATCH 会发送；GET/DELETE 忽略）
 * @param params URL 查询参数（undefined 的项自动过滤掉）
 * @returns      后端 data 字段（已解包，调用方直接拿到业务数据）
 */
export async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  url: string,
  body?: unknown,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  /* ① 开关未打开 → 立即失败（避免"以为连了后端其实没连"的隐患） */
  if (!USE_BACKEND) {
    throw new ApiError(
      '后端未开启：请在 src/api/config.ts 中把 USE_BACKEND 改为 true 并配置 API_BASE_URL',
      -100
    )
  }

  /* ② 拼接最终 URL：基础地址 + 前缀 + 相对路径 + 查询串 */
  const query = params
    ? '?' + new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      ).toString()
    : ''
  const fullUrl = `${API_BASE_URL}${API_PREFIX}${url}${query}`

  /* ③ 请求头：JSON + 登录 token（有 token 才带 Authorization） */
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  /* ④ 超时控制：到时间自动 abort，防止请求永远挂起 */
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  try {
    const res = await fetch(fullUrl, {
      method,
      headers,
      signal: controller.signal,
      // 只有写操作才带请求体；GET/DELETE 一律不带
      body:
        body !== undefined && method !== 'GET' && method !== 'DELETE'
          ? JSON.stringify(body)
          : undefined
    })

    /* ⑤ HTTP 状态码错误处理 */
    if (!res.ok) {
      let detail = ''
      try { const errorBody = await res.json(); detail = typeof errorBody.detail === 'string' ? errorBody.detail : '' } catch { /* 非 JSON 错误 */ }
      if (res.status === 401) {
        // 登录接口的 401 是账号/密码校验结果，应展示后端详情；其他接口才表示会话失效。
        if (!url.startsWith('/auth/login')) clearToken()
        throw new ApiError(detail || (url.startsWith('/auth/login') ? '账号不存在或密码错误' : '登录已过期，请重新登录'), 401, 401)
      }
      throw new ApiError(detail || `服务器错误：HTTP ${res.status}`, res.status, res.status)
    }

    /* ⑥ 解析 JSON 并按约定解包 { code, message, data } */
    const json = await res.json()
    // 后端当前直接返回业务对象；同时兼容未来的 {code,message,data} 包装格式。
    if (json && typeof json === 'object' && 'code' in json && 'data' in json) {
      const envelope = json as ApiEnvelope<T>
      if (envelope.code !== 0) throw new ApiError(envelope.message || '业务处理失败', envelope.code, res.status)
      return envelope.data
    }
    return json as T
  } catch (e) {
    /* ⑦ 错误归类：ApiError 原样抛；超时/网络异常包装成友好提示 */
    if (e instanceof ApiError) throw e
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiError(`请求超时（${REQUEST_TIMEOUT}ms），请检查后端是否已启动`, -2)
    }
    throw new ApiError('网络异常，请检查后端服务是否已启动', -1)
  } finally {
    clearTimeout(timer) // 无论成功失败都要清掉超时定时器
  }
}
