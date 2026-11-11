/**
 * src/api/config.ts —— 后端接口全局配置（整个接口层的"唯一开关"文件）
 * ----------------------------------------------------------------
 * 作用：
 *   1. 集中管理后端地址、接口前缀、超时时间、token 存储键
 *   2. USE_BACKEND 开关决定整个前端的数据来源：
 *        false = 纯前端模式（现在）：stores 继续用 localStorage，不发任何网络请求
 *        true  = 真实后端模式：request.ts 会真正发出 fetch 请求
 *
 * ★ 现在默认 false（不连后端）。将来后端就绪时只需改本文件两行：
 *     export const USE_BACKEND = true
 *     export const API_BASE_URL = ''   // 配合 vite proxy 走代理时留空即可
 */

/** 是否启用真实后端：false 时 request.ts 会直接抛"后端未开启"错误，不发任何请求 */
export const USE_BACKEND = true

/** 后端 API 基础地址（末尾不带 /；走 vite 代理时改为 ''） */
export const API_BASE_URL = 'http://127.0.0.1:8000'

/** 所有接口的统一路由前缀（后端约定所有业务接口都以 /api 开头） */
export const API_PREFIX = '/api'

/** 请求超时时间（毫秒），超时后 AbortController 中止请求 */
// Agent 需要等待大模型响应；普通数据库请求通常会更快返回。
export const REQUEST_TIMEOUT = 60000

/** 登录 token 在 localStorage 的存储键（登录成功写入，401/登出清除） */
export const TOKEN_KEY = 'shop_token'
