/**
 * stores/cart.ts - 购物车状态管理
 * ----------------------------------------------------------------
 * 添加/删除/修改数量/选中状态，持久化到 localStorage
 * 支持批量操作：全选、批量删除、移入收藏
 */
import { reactive, computed } from 'vue'
import { apiGetCart, apiAddToCart, apiUpdateCartQuantity, apiRemoveCartItems, apiClearCart } from '@/api/cart'
import { getProductById } from './products'
import { getToken } from '@/api/request'

/**
 * 购物车单项结构
 *  字段较多是因为需要在购物车 / CheckoutView / Order 里都能直接渲染，
 *  避免每次渲染再去查一次 product registry。
 */
export interface CartItem {
  id: number
  name: string
  desc?: string              // 商品副标题/规格（如"12+256GB 曜石黑"）
  price: number              // 当前价格
  originalPrice?: number     // 原价（划线显示；用于展示优惠）
  emoji: string              // emoji 占位图
  bgColor: string            // 占位图渐变背景
  quantity: number           // 购买数量（1~999）
  selected: boolean          // 是否选中（结算 / 批量删除 / 批量移收藏都依赖这个字段）
  promotions?: string[]      // 促销标签数组：如 ["立减2元","7天无理由"]
}

const STORAGE_KEY = 'shop_cart'

/**
 * 加载本地购物车，容错脏数据 + 兼容"老数据没有 selected"的情况
 *  为什么默认 selected=true：用户新加购物车一般默认就要结算，避免每次加购后都要点 checkbox
 */
const load = (): CartItem[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const items = raw ? JSON.parse(raw) : []
    return items.map((it: CartItem) => ({
      ...it,
      selected: it.selected ?? true
    }))
  } catch {
    return []
  }
}

// 购物车响应式容器
const state = reactive<{ items: CartItem[] }>({ items: load() })

/** 从后端同步购物车，确保页面显示数据库真实内容。 */
export async function refreshCart() {
  const token = getToken()
  if (!token) { clearCartState(); return }
  const result = await apiGetCart()
  if (getToken() !== token) { clearCartState(); return }
  state.items.splice(0, state.items.length, ...result.items.map(row => {
    const p = getProductById(row.product_id)
    return { id: row.product_id, name: p?.name ?? `商品 ${row.product_id}`, desc: p?.desc, price: p?.price ?? 0,
      emoji: p?.emoji ?? '🛍️', bgColor: p?.bgColor ?? '#f3f4f6', quantity: row.quantity, selected: true }
  }))
  save()
}

/** 写回 localStorage（所有增删改后必须调用） */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.items))

/**
 * 加入购物车
 *   - 如果同一 id 已存在 → 数量 +qty（不改变 selected 状态，避免把用户已取消的勾上）
 *   - 不存在 → 新对象 push，默认 selected=true
 * @param item 商品信息（不含 quantity/selected）
 * @param qty 新增数量（ProductDetailView 的数量选择器传进来；首页/分类页默认为 1）
 */
export function addToCart(
  item: Omit<CartItem, 'quantity' | 'selected'>,
  qty = 1
) {
  apiAddToCart({ product_id: item.id }, qty).then(refreshCart).catch(() => undefined)
  const exist = state.items.find(i => i.id === item.id)
  if (exist) {
    exist.quantity += qty
  } else {
    state.items.push({ ...item, quantity: qty, selected: true })
  }
  save()
}

/**
 * 移除单个购物车项（按 id）
 * 触发源：CartView 单项「🗑️ 删除」按钮；数量减到 0 时 updateQuantity 也会调这个
 */
export function removeFromCart(id: number) {
  apiRemoveCartItems([id]).then(refreshCart).catch(() => undefined)
  const idx = state.items.findIndex(i => i.id === id)
  if (idx > -1) {
    state.items.splice(idx, 1)
    save()
  }
}

/**
 * 批量移除（批量删除按钮）
 * 触发源：CartView 顶栏「批量删除」
 */
export function removeFromCartBatch(ids: number[]) {
  apiRemoveCartItems(ids).then(refreshCart).catch(() => undefined)
  state.items = state.items.filter(i => !ids.includes(i.id))
  save()
}

/**
 * 修改数量
 *   - qty <= 0 → 移除（用户在 number input 中删成 0/负数的场景）
 *   - 其它 → 直接覆盖 quantity 并 save；CartView 还做了 min=1 max=999 的限制
 */
export function updateQuantity(id: number, qty: number) {
  if (qty > 0) apiUpdateCartQuantity(id, qty).then(refreshCart).catch(() => undefined)
  const item = state.items.find(i => i.id === id)
  if (!item) return
  if (qty <= 0) {
    removeFromCart(id)
  } else {
    item.quantity = qty
    save()
  }
}

/** 切换单条的 selected 状态（CartView 每行前面的 checkbox） */
export function toggleSelected(id: number) {
  const item = state.items.find(i => i.id === id)
  if (item) {
    item.selected = !item.selected
    save()
  }
}

/** 全选 / 取消全选（顶栏那个「全选」复选框） */
export function selectAll(checked: boolean) {
  state.items.forEach(i => { i.selected = checked })
  save()
}

/**
 * 批量移入收藏（用户要求"移入后仍保留在购物车"）
 *  所以这里不执行任何删除，只返回匹配到的 CartItem 数组给调用方去 addFavorite
 * @returns 传入 id 列表对应的 CartItem 子集
 */
export function moveToFavorites(ids: number[]): CartItem[] {
  return state.items.filter(i => ids.includes(i.id))
}

/** 清空购物车（在 createOrder 成功后触发，因为结算就要清空） */
export function clearCart() {
  apiClearCart().then(refreshCart).catch(() => undefined)
  clearCartState()
}

/**
 * 清空当前前端购物车状态。
 * 仅用于本地状态清理，例如退出登录；退出时不再向后端发送购物车请求。
 */
export function clearCartState() {
  state.items.splice(0, state.items.length)
  save()
}

/** 当前选中商品列表（CartView 右侧「去结算」按钮 + ProfileView 购物车 Tab 用） */
export const selectedItems = computed(() =>
  state.items.filter(i => i.selected)
)

/** 选中商品总价（CheckoutView 费用卡金额 = selectedTotal + 运费 - 优惠券） */
export const selectedTotal = computed(() =>
  selectedItems.value.reduce((sum, i) => sum + i.price * i.quantity, 0)
)

/** 是否全选（用于 CartView 顶部 checkbox 的 indeterminate 状态） */
export const isAllSelected = computed(() =>
  state.items.length > 0 && state.items.every(i => i.selected)
)

/** 返回 state 引用，让 View 遍历 items、显示数量角标等 */
export function useCart() {
  return state
}
