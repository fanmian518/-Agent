/**
 * stores/reviews.ts - 评价管理
 * ----------------------------------------------------------------
 * 添加/编辑/删除评价，持久化到 localStorage
 * 支持：商品评价、评分（1-5星）、文字内容
 */
import { reactive } from 'vue'
import { apiAddReview, apiDeleteReview } from '@/api/userData'
import { apiGetReviews } from '@/api/userData'
import { getToken } from '@/api/request'

/**
 * 用户评价实体
 *  商品维度的冗余字段（productName/productEmoji）让 ProfileView「评价管理」在脱离商品详情页时也能独立渲染卡片
 */
export interface Review {
  id: string              // 评价主键（用 genReviewId 生成）
  productId: number       // 关联商品 id（对齐 products registry）
  productName: string     // 关联商品名称（展示用快照）
  productEmoji: string    // 关联商品 emoji 图标（展示用）
  productBgColor: string  // 关联商品渐变背景（展示用）
  orderId?: string        // 可选：关联订单号（当前按钮逻辑未强制要求）
  rating: number          // 1-5 星评分，整数或 .5 小数
  content: string         // 评价正文
  createdAt: number       // 评价时间戳
}

const STORAGE_KEY = 'shop_reviews'

/** 加载本地评价列表（容错脏数据） */
const load = (): Review[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 评价响应式容器（所有评价 Tab / 商品详情页评价列表共享同一个引用）
const state = reactive<{ list: Review[] }>({ list: load() })
export async function refreshReviews() {
  const token = getToken()
  if (!token) { clearReviewsState(); return }
  try {
    const result = await apiGetReviews()
    if (getToken() !== token) { clearReviewsState(); return }
    state.list.splice(0, state.list.length, ...(result.reviews as any[]).map((r:any) => ({ id:r.id, productId:r.productId, productName:`商品 ${r.productId}`, productEmoji:'🛍️', productBgColor:'#f3f4f6', orderId:r.orderId, rating:r.rating, content:r.content, createdAt:r.createdAt })))
  } catch { /* 保留本地兼容数据 */ }
}

/** 写回 localStorage */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.list))

/**
 * 生成全局唯一评价 ID：r_ + 毫秒时间（36 进制）+ 4 位随机码
 *  避免用户连续评价多个商品出现 id 冲突
 */
const genReviewId = () => {
  return 'r_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

/**
 * 新增一条评价（自动写入 id 与 createdAt）
 * 触发源：
 *   - 订单 Tab -> 已完成 ->「⭐ 评价」按钮打开评价弹窗确认后
 *   - ProfileView ⭐ 评价管理 -> 「+ 添加 Demo 评价」
 * @param review 不含 id 与 createdAt 的评价载荷
 * @returns 已填充 id / createdAt 的完整评价对象
 */
export function addReview(review: Omit<Review, 'id' | 'createdAt'>): Review {
  const newReview: Review = {
    ...review,
    id: genReviewId(),
    createdAt: Date.now()
  }
  apiAddReview({ product_id: review.productId, order_id: review.orderId, rating: review.rating, content: review.content }).catch(() => undefined)
  // 最新的评价排到最前面
  state.list.unshift(newReview)
  save()
  return newReview
}

/**
 * 更新评价（只能改评分 / 内容，防止改 productId / orderId 等业务主键）
 */
export function updateReview(reviewId: string, patch: Partial<Pick<Review, 'rating' | 'content'>>) {
  const review = state.list.find(r => r.id === reviewId)
  if (review) {
    Object.assign(review, patch)
    save()
  }
}

/**
 * 删除指定评价
 * 触发源：ProfileView 评价管理 Tab -> 单项「删除」（带 confirm）
 */
export function deleteReview(reviewId: string) {
  apiDeleteReview(reviewId).catch(() => undefined)
  const idx = state.list.findIndex(r => r.id === reviewId)
  if (idx > -1) {
    state.list.splice(idx, 1)
    save()
  }
}

/** 清空当前前端评价状态，例如退出登录时使用。 */
export function clearReviewsState() {
  state.list.splice(0, state.list.length)
  save()
}

/**
 * 判断某个商品是否已经被当前用户评价过（用于"已完成订单"列表
 * 的"去评价/已评价"按钮显示不同状态）
 */
export function hasReviewed(productId: number): boolean {
  return state.list.some(r => r.productId === productId)
}

/** 获取响应式 state 引用（供视图层渲染） */
export function useReviews() {
  return state
}
