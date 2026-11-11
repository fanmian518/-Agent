/**
 * stores/history.ts - 浏览历史管理
 * ----------------------------------------------------------------
 * 记录用户访问过的商品，最多保留 50 条，持久化到 localStorage
 */
import { reactive } from 'vue'
import { apiRecordHistory, apiClearHistory, apiGetHistory } from '@/api/userData'
import { getToken } from '@/api/request'

/**
 * 浏览历史单项结构（用于渲染用户中心「🕐 浏览历史」Tab、列表跳详情）
 */
export interface HistoryItem {
  id: number           // 商品 id，保证和 products registry 一致，方便跳转详情
  name: string         // 商品名称（展示用）
  emoji: string        // 商品占位 emoji 图标
  bgColor: string      // 商品卡占位渐变背景
  viewedAt: number     // 浏览时间戳（毫秒），可拓展为"x分钟前"格式化展示
}

// localStorage 持久化键（Demo：所有历史共用一个 key，未按用户隔离）
const STORAGE_KEY = 'shop_history'
// 最大保留 50 条（超出后按时间裁剪最老的记录，避免 localStorage 膨胀）
const MAX_ITEMS = 50

/**
 * 页面加载时从 localStorage 读取浏览历史
 * （容错：JSON 解析失败时返回空数组，避免因脏数据导致整页白屏）
 */
const load = (): HistoryItem[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 响应式容器：所有 View 组件通过 useHistory() 引用同一个 reactive state
const state = reactive<{ items: HistoryItem[] }>({ items: load() })
export async function refreshHistory() {
  const token = getToken()
  if (!token) { clearHistoryState(); return }
  try {
    const result = await apiGetHistory()
    if (getToken() !== token) { clearHistoryState(); return }
    state.items.splice(0, state.items.length, ...(result.items as any[]).map(row => ({ id: row.product_id, name: `商品 ${row.product_id}`, emoji: '🛍️', bgColor: '#f3f4f6', viewedAt: Date.parse(row.viewed_at) || Date.now() })))
  } catch { /* 保留本地兼容数据 */ }
}

/** 把当前 items 数组写回 localStorage（每次修改后都调用） */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.items))

/**
 * 记录一次商品浏览
 * 策略：
 *   - 先删除该商品的旧浏览记录（按 id 去重）
 *   - 再把本次浏览 unshift 到数组最前面（用户中心浏览历史 Tab 默认按时间最新优先）
 *   - 超过 MAX_ITEMS 时裁剪尾部；最后 save 持久化
 * @param item 浏览商品的基础信息（不需要带 viewedAt，由函数内部自动写入当前时间戳）
 */
export function recordView(item: Omit<HistoryItem, 'viewedAt'>) {
  apiRecordHistory(item.id).catch(() => undefined)
  // 先移除旧记录，保证同一商品只出现一次且停留在最顶部
  const idx = state.items.findIndex(i => i.id === item.id)
  if (idx > -1) state.items.splice(idx, 1)
  // 插入到最前，写入时间戳
  state.items.unshift({ ...item, viewedAt: Date.now() })
  // 超出上限则裁剪（保持最近 50 条）
  if (state.items.length > MAX_ITEMS) {
    state.items.splice(MAX_ITEMS)
  }
  save()
}

/**
 * 清空浏览历史
 * 触发源：ProfileView.vue -> 浏览历史 Tab -> 底部「清空历史」按钮（带 confirm）
 */
export function clearHistory() {
  apiClearHistory().catch(() => undefined)
  state.items.splice(0, state.items.length)
  save()
}

/** 清空当前前端浏览历史状态，例如退出登录时使用。 */
export function clearHistoryState() {
  state.items.splice(0, state.items.length)
  save()
}

/**
 * 获取响应式 state 引用（供 View 层使用：v-for="h in history.items" 等）
 * 为什么用函数而不是直接导出 state：保持与其他 store 文件一致的 "useXxx()" 风格调用
 */
export function useHistory() {
  return state
}
