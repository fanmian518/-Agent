/**
 * stores/favorites.ts - 收藏夹状态管理
 * ----------------------------------------------------------------
 * 添加/移除收藏，持久化到 localStorage
 */
import { reactive } from 'vue'
import { apiGetFavorites, apiAddFavorite, apiRemoveFavorite } from '@/api/favorite'
import { getProductById } from './products'
import { getToken } from '@/api/request'

/**
 * 收藏夹单项结构
 * 注：为了脱离后端也能在收藏列表展示完整卡片，这里冗余存了 name/price/emoji/bgColor；
 * 若后续接入真实后端，可只存 id 再在 View 中 join 商品注册表。
 */
export interface FavoriteItem {
  id: number           // 商品 id（与 products registry 对齐）
  name: string         // 商品名
  price: number        // 当前收藏时的价格快照
  emoji: string        // 占位 emoji 图标
  bgColor: string      // 占位渐变背景
  addedAt: number      // 收藏时间戳
}

const STORAGE_KEY = 'shop_favorites'

/** localStorage 读取（容错脏数据） */
const load = (): FavoriteItem[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 所有收藏列表的响应式容器（单一数据真相）
const state = reactive<{ items: FavoriteItem[] }>({ items: load() })

/** 从后端同步收藏夹，供页面实时显示最新数据。 */
export async function refreshFavorites() {
  const token = getToken()
  if (!token) { clearFavoritesState(); return }
  const result = await apiGetFavorites()
  if (getToken() !== token) { clearFavoritesState(); return }
  state.items.splice(0, state.items.length, ...result.items.map(row => {
    const p = getProductById(row.product_id)
    return { id: row.product_id, name: p?.name ?? `商品 ${row.product_id}`, price: p?.price ?? 0, emoji: p?.emoji ?? '🛍️', bgColor: p?.bgColor ?? '#f3f4f6', addedAt: Date.now() }
  }))
  save()
}

/** 写回 localStorage，每次修改收藏后都需要调用 */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.items))

/**
 * 判断一个商品是否已被收藏
 * 触发源：
 *   - 商品详情页 ProductDetailView 的"❤️ 已收藏/未收藏"按钮显隐
 *   - 加入收藏前避免重复写入
 * @param id 商品 id
 */
export function isFavorite(id: number): boolean {
  return state.items.some(i => i.id === id)
}

/**
 * 添加商品到收藏夹
 * 若该 id 已存在则什么都不做（保证列表不重复）
 * @param item 收藏商品的基础字段；addedAt 由函数写入
 */
export function addToFavorite(item: Omit<FavoriteItem, 'addedAt'>) {
  apiAddFavorite({ product_id: item.id }).then(refreshFavorites).catch(() => undefined)
  if (isFavorite(item.id)) return
  state.items.push({ ...item, addedAt: Date.now() })
  save()
}

/**
 * 从收藏夹移除一个商品
 * 触发源：
 *   - FavoritesView.vue 单条"取消收藏"（带确认弹窗）/ 批量取消
 *   - ProfileView.vue 收藏 Tab 单条取消
 * @param id 商品 id
 */
export function removeFromFavorite(id: number) {
  apiRemoveFavorite(id).then(refreshFavorites).catch(() => undefined)
  const idx = state.items.findIndex(i => i.id === id)
  if (idx > -1) {
    state.items.splice(idx, 1)
    save()
  }
}

/**
 * 切换收藏状态（未收藏 → 加；已收藏 → 取消）
 * 触发源：商品卡片右下角 ❤️、详情页顶部收藏按钮
 */
export function toggleFavorite(item: Omit<FavoriteItem, 'addedAt'>) {
  if (isFavorite(item.id)) {
    removeFromFavorite(item.id)
  } else {
    addToFavorite(item)
  }
}

/** 批量取消收藏并同步后端结果。 */
export function removeFromFavoritesBatch(ids: number[]) {
  Promise.all(ids.map(id => apiRemoveFavorite(id))).then(refreshFavorites).catch(() => undefined)
  state.items = state.items.filter(item => !ids.includes(item.id))
  save()
}

/** 清空当前前端收藏夹状态，例如退出登录时使用。 */
export function clearFavoritesState() {
  state.items.splice(0, state.items.length)
  save()
}

/** 返回响应式 state 引用，供 v-for 渲染 / 数量角标使用 */
export function useFavorites() {
  return state
}
