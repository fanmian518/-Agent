/**
 * stores/shops.ts - 关注店铺管理
 * ----------------------------------------------------------------
 * 关注/取消关注店铺，持久化到 localStorage
 * 预设一些示例店铺供演示
 */
import { reactive, computed } from 'vue'
import { apiFollowShop, apiUnfollowShop } from '@/api/favorite'
import { apiGetFollowedShops } from '@/api/favorite'
import { getToken } from '@/api/request'

/**
 * 店铺对象结构（Demo：所有店铺都写在前端 defaultShops）
 */
export interface Shop {
  id: number
  name: string        // 店铺名称
  logo: string        // 店铺图标（emoji 占位）
  bgColor: string     // 卡片占位背景色（渐变）
  followers: number   // 粉丝数
  rating: number      // 0-5 评分
  followedAt?: number // 关注时间（Demo 仅字段预留，当前未写入使用）
}

const STORAGE_KEY = 'shop_followed_shops'

// ====== 预设店铺数据（Demo：店铺列表固定；真实业务应从后端拉取） ======
const defaultShops: Shop[] = [
  // 1 号：数码品类旗舰店，用于商品详情页商品 -> 所属店铺展示
  {
    id: 1,
    name: '极光官方旗舰店',
    logo: '📱',
    bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    followers: 128300,
    rating: 4.9
  },
  {
    id: 2,
    name: '潮牌服饰专营',
    logo: '👗',
    bgColor: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    followers: 89500,
    rating: 4.7
  },
  {
    id: 3,
    name: '数码配件优选',
    logo: '🎧',
    bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    followers: 56200,
    rating: 4.8
  },
  {
    id: 4,
    name: '北欧家居生活馆',
    logo: '🏠',
    bgColor: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
    followers: 43800,
    rating: 4.6
  },
  {
    id: 5,
    name: '运动户外官方店',
    logo: '⚽',
    bgColor: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    followers: 72100,
    rating: 4.8
  },
  {
    id: 6,
    name: '进口零食直营',
    logo: '🍫',
    bgColor: 'linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)',
    followers: 38600,
    rating: 4.5
  }
]
export async function refreshFollowedShops() {
  const token = getToken()
  if (!token) { clearFollowedShopsState(); return }
  try {
    const result = await apiGetFollowedShops()
    if (getToken() !== token) { clearFollowedShopsState(); return }
    state.followedIds.splice(0, state.followedIds.length, ...(result.items as any[]).map(x => x.shop_id)); save()
  } catch { /* 保留本地兼容数据 */ }
}

/**
 * 页面加载时从 localStorage 恢复「已关注的店铺 id 列表」
 * （只存 id，不存店铺整对象 —— 避免与 defaultShops 数据漂移）
 */
const loadFollowed = (): number[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 响应式 state：all 为全部店铺（固定），followedIds 为已关注 id 集合（可变）
const state = reactive({
  all: [...defaultShops],
  followedIds: loadFollowed()
})

/** 把 followedIds 持久化；任何关注关系变动后都需要调用 */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.followedIds))

/**
 * 计算属性：返回当前已关注的店铺数组（由 ProfileView 关注店铺 Tab 直接显示）
 * 放在这里方便多个视图复用（ProductDetailView「店铺条」也需要展示是否关注）
 */
export const followedShops = computed<Shop[]>(() =>
  state.all.filter(s => state.followedIds.includes(s.id))
)

/**
 * 指定 id 的店铺是否已被关注
 * 触发源：商品详情页店铺卡片「+关注」按钮 / 关注店铺 Tab 中按钮
 */
export function isFollowed(shopId: number): boolean {
  return state.followedIds.includes(shopId)
}

/**
 * 关注店铺
 *   - 幂等：若已关注则不做任何事
 *   - 成功后店铺粉丝数 +1（Demo 演示效果）
 */
export function followShop(shopId: number) {
  apiFollowShop(shopId).catch(() => undefined)
  if (isFollowed(shopId)) return
  state.followedIds.push(shopId)
  const shop = state.all.find(s => s.id === shopId)
  if (shop) shop.followers++
  save()
}

/**
 * 取消关注
 *   - 从 followedIds 中删除
 *   - 粉丝数 -1（至少为 0，避免负数展示）
 *   - （原代码 shop.followedAt 的判断是 bug，followedAt 从没写入过；这里移除多余判断）
 */
export function unfollowShop(shopId: number) {
  apiUnfollowShop(shopId).catch(() => undefined)
  const idx = state.followedIds.indexOf(shopId)
  if (idx > -1) {
    state.followedIds.splice(idx, 1)
    const shop = state.all.find(s => s.id === shopId)
    if (shop) shop.followers = Math.max(0, shop.followers - 1)
    save()
  }
}

/** 清空当前前端关注店铺状态，例如退出登录时使用。 */
export function clearFollowedShopsState() {
  state.followedIds.splice(0, state.followedIds.length)
  save()
}

/**
 * 切换关注状态（未关注→关注；已关注→取消）
 * 触发源：店铺卡片 + / - 关注按钮
 */
export function toggleFollow(shopId: number) {
  if (isFollowed(shopId)) {
    unfollowShop(shopId)
  } else {
    followShop(shopId)
  }
}

/** 兼容旧代码：返回已关注店铺列表（推荐外部直接用 computed followedShops） */
export function getFollowedShops(): Shop[] {
  return followedShops.value
}

/** 返回 state 原始引用（供 ProfileView 遍历 all 展示全部店铺并跟随状态） */
export function useShops() {
  return state
}
