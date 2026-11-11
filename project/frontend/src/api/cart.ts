/**
 * src/api/cart.ts —— 购物车模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/cart.ts（当前 localStorage shop_cart）。
 * store → api 迁移对应（将来联调时替换）：
 *   useCart().items        → apiGetCart()
 *   addToCart              → apiAddToCart
 *   updateQuantity         → apiUpdateCartQuantity
 *   toggleSelected         → apiToggleCartSelected
 *   selectAll              → apiSelectAllCart
 *   removeFromCart(Batch)  → apiRemoveCartItems（单项=传 1 个元素的数组）
 *   clearCart              → apiClearCart
 */
import { request } from './request'

/** 后端购物车项结构（字段与 stores/cart.ts 的 CartItem 完全对齐） */
export interface ApiCartItem {
  product_id: number
  quantity: number
}

/** 获取当前用户购物车列表 */
export function apiGetCart() {
  return request<{items: ApiCartItem[]; total_items: number}>('GET', '/cart')
}

/** 加入购物车（后端负责"已存在则数量累加"逻辑） */
export function apiAddToCart(
  item: { product_id: number },
  qty = 1
) {
  return request<ApiCartItem>('POST', '/cart/items', { product_id: item.product_id, quantity: qty })
}

/** 修改数量（qty <= 0 时后端应视为删除该条） */
export function apiUpdateCartQuantity(id: number, qty: number) {
  return request<ApiCartItem>('PUT', `/cart/items/${id}`, { quantity: qty })
}

/** 切换单条的选中状态 */
export function apiToggleCartSelected(id: number, selected: boolean) {
  return request<ApiCartItem[]>('PUT', `/cart/${id}/selected`, { selected })
}

/** 全选 / 取消全选 */
export function apiSelectAllCart(checked: boolean) {
  return request<ApiCartItem[]>('PUT', '/cart/selected-all', { checked })
}

/** 批量删除（传 id 数组；单项删除也走这里，传一个元素的数组） */
export function apiRemoveCartItems(ids: number[]) {
  return Promise.all(ids.map(id => request<ApiCartItem>('DELETE', `/cart/items/${id}`)))
}

/** 清空购物车（结算成功后调用） */
export function apiClearCart() {
  return request<{message: string}>('DELETE', '/cart')
}
