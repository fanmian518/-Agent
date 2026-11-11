/**
 * stores/coupons.ts - 优惠券状态管理
 * ----------------------------------------------------------------
 * 优惠券数据模型：面额、使用门槛、适用范围、有效期
 * 分类状态：可用（未使用未过期）、已使用、已过期
 * 持久化到 localStorage
 */
import { reactive, computed } from 'vue'
import { apiClaimCoupon, apiUseCoupon } from '@/api/coupon'
import { apiGetCoupons } from '@/api/coupon'
import { getToken } from '@/api/request'

/**
 * 优惠券适用范围：与 ProductCategory 对齐；多出来的 all 表示全品类通用
 */
export type CouponScope = 'all' | 'digital' | 'fashion' | 'homegoods' | 'newuser'

/** 适用范围 → Tab 显示名称（ProfileView 优惠券子 Tab 用） */
export const scopeLabel: Record<CouponScope, string> = {
  all: '全品类',
  digital: '数码爆款',
  fashion: '潮流穿搭',
  homegoods: '家居好物',
  newuser: '新人专享'
}

/** 适用范围 → 卡片左侧主题色（ProfileView 优惠券渐变色块） */
export const scopeColor: Record<CouponScope, string> = {
  all: '#4f46e5',
  digital: '#0ea5e9',
  fashion: '#ec4899',
  homegoods: '#f59e0b',
  newuser: '#ef4444'
}

/**
 * 优惠券结构
 *  生命周期：
 *    claimedAt（领取时间） → startAt（生效时间） → endAt（失效时间）
 *    如果在此期间 usedAt 被写入 → 已使用；否则过 endAt → 已过期
 */
export interface Coupon {
  id: string            // 优惠券唯一 id
  title: string         // 券名：如"新人无门槛券"
  value: number         // 优惠金额（元）
  threshold: number     // 使用门槛；满 threshold 可用；0 表示无门槛
  scope: CouponScope    // 适用范围（对齐 scopeLabel / scopeColor）
  desc?: string         // 优惠券使用说明
  claimedAt: number     // 领取时间戳
  startAt: number       // 生效起始时间
  endAt: number         // 失效时间
  usedAt?: number       // 使用时间（没使用则 undefined；用于判断已使用分组）
}

const STORAGE_KEY = 'shop_coupons'

/** 加载本地优惠券列表（容错脏数据） */
const load = (): Coupon[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}
/** 写回 localStorage */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.items))

// 响应式容器
const state = reactive<{ items: Coupon[] }>({ items: load() })
export async function refreshCoupons() {
  const token = getToken()
  if (!token) { clearCouponsState(); return }
  try {
    const result = await apiGetCoupons()
    if (getToken() !== token) { clearCouponsState(); return }
    const rows = (result as any).coupons ?? []
    state.items.splice(0, state.items.length, ...rows.map((c:any) => ({ id:c.id,title:c.title,value:Number(c.value),threshold:Number(c.threshold),scope:c.scope,desc:c.desc,claimedAt:c.claimedAt,startAt:c.startAt,endAt:c.endAt,usedAt:c.usedAt })))
  } catch { /* 保留本地兼容数据 */ }
}

/** 可用券：未使用 + 已在有效期内（startAt ≤ now ≤ endAt） */
export const availableCoupons = computed(() => {
  const now = Date.now()
  return state.items.filter(c =>
    !c.usedAt && c.startAt <= now && now <= c.endAt
  )
})

/** 已使用：usedAt 有值（使用过期的情况也会归到这里） */
export const usedCoupons = computed(() =>
  state.items.filter(c => !!c.usedAt)
)

/** 已过期：未使用但已超过 endAt */
export const expiredCoupons = computed(() => {
  const now = Date.now()
  return state.items.filter(c => !c.usedAt && c.endAt < now)
})

/**
 * 领取一张优惠券
 * @param data 基础券参数（不含 id/领取时间/生效失效时间）
 * @param data.durationDays 有效期天数（默认 30 天）
 * @param data.startDelayHours 延迟生效小时数（默认立即生效 = 0）
 */
export function claimCoupon(data: Omit<Coupon, 'id' | 'claimedAt' | 'startAt' | 'endAt'> & {
  durationDays?: number
  startDelayHours?: number
}) {
  apiClaimCoupon({ title: data.title, value: data.value, threshold: data.threshold, scope: data.scope, desc: data.desc, durationDays: data.durationDays }).catch(() => undefined)
  const id = 'cp_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
  const now = Date.now()
  const duration = (data.durationDays ?? 30) * 86400000
  const delay = (data.startDelayHours ?? 0) * 3600000
  const coupon: Coupon = {
    id,
    title: data.title,
    value: data.value,
    threshold: data.threshold,
    scope: data.scope,
    desc: data.desc,
    claimedAt: now,
    startAt: now + delay,
    endAt: now + delay + duration
  }
  state.items.push(coupon)
  save()
  return coupon
}

/**
 * 使用优惠券（成功返回 true，已使用或已过期返回 false）
 * 当前未在 CheckoutView UI 中接入使用优惠券选择器，仅用于 Demo 初始化和测试
 */
export function useCoupon(id: string) {
  apiUseCoupon(id).catch(() => undefined)
  const cp = state.items.find(c => c.id === id)
  if (!cp || cp.usedAt || Date.now() > cp.endAt) return false
  cp.usedAt = Date.now()
  save()
  return true
}

/**
 * 删除优惠券（用于 ProfileView 已使用 / 已过期 Tab 的清理按钮）
 */
export function removeCoupon(id: string) {
  const idx = state.items.findIndex(c => c.id === id)
  if (idx > -1) {
    state.items.splice(idx, 1)
    save()
  }
}

/** 清空当前前端优惠券状态，例如退出登录时使用。 */
export function clearCouponsState() {
  state.items.splice(0, state.items.length)
  save()
}

/** 返回 state 引用（ProfileView 优惠券 Tab 遍历） */
export function useCoupons() { return state }

/**
 * 格式化券生效 / 失效日期为 "YYYY.MM.DD"，用于券卡片的有效期文字
 */
export function formatCouponDate(ts: number) {
  const d = new Date(ts)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
}

/**
 * 距离 endAt 还有多少天（正数=还剩，0=今天到期，负数=已经过期）
 * ProfileView 里显示「还有 X 天到期」橘色警告用到
 */
export function remainingDays(endAt: number): number {
  return Math.ceil((endAt - Date.now()) / 86400000)
}

/**
 * 新用户首次进入 ProfileView 时初始化一批 Demo 券（可用 3 + 过期 1 + 已用 1）
 * 避免 Tab 数量角标空的情况
 */
export function ensureInitCoupons() {
  if (state.items.length > 0) return
  const now = Date.now()
  const day = 86400000
  const push = (c: Coupon) => state.items.push(c)

  push({
    id: 'cp_demo_1', title: '新人无门槛券', value: 10, threshold: 0, scope: 'all',
    desc: '全品类可用', claimedAt: now - 2 * day, startAt: now - 2 * day, endAt: now + 28 * day
  })
  push({
    id: 'cp_demo_2', title: '数码爆款满减券', value: 50, threshold: 299, scope: 'digital',
    desc: '满 299 元可用', claimedAt: now - 1 * day, startAt: now - 1 * day, endAt: now + 29 * day
  })
  push({
    id: 'cp_demo_3', title: '潮流穿搭满减券', value: 30, threshold: 199, scope: 'fashion',
    desc: '满 199 元可用', claimedAt: now, startAt: now, endAt: now + 30 * day
  })
  // 已过期示例
  push({
    id: 'cp_demo_4', title: '限时满 500 减 100', value: 100, threshold: 500, scope: 'homegoods',
    desc: '家居好物专用', claimedAt: now - 40 * day, startAt: now - 40 * day, endAt: now - 10 * day
  })
  // 已使用示例
  push({
    id: 'cp_demo_5', title: '限时无门槛券', value: 5, threshold: 0, scope: 'all',
    desc: '全品类可用', claimedAt: now - 5 * day, startAt: now - 5 * day, endAt: now + 25 * day,
    usedAt: now - 3 * day
  })
  save()
}
