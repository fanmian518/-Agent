/**
 * src/api/favorite.ts —— 收藏夹模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/favorites.ts（当前 localStorage shop_favorites）。
 * store → api 迁移对应（将来联调时替换）：
 *   useFavorites().items   → apiGetFavorites()
 *   addToFavorite          → apiAddFavorite（后端做去重）
 *   removeFromFavorite     → apiRemoveFavorite
 */
import { request } from './request'

/** 后端收藏项结构（对齐 stores/favorites.ts 的 FavoriteItem） */
export interface ApiFavoriteItem {
  id: number
  name: string
  price: number
  emoji: string
  bgColor: string
  addedAt: number
}

/** 收藏列表 */
export function apiGetFavorites() {
  return request<{items: Array<{product_id: number}>}>('GET', '/favorites')
}

/** 添加收藏（已收藏时后端返回业务错误码或幂等成功，前端无需先去重） */
export function apiAddFavorite(item: {product_id: number}) {
  return request<ApiFavoriteItem>('POST', '/favorites/items', item)
}

/** 取消收藏 */
export function apiRemoveFavorite(id: number) {
  return request<ApiFavoriteItem>('DELETE', `/favorites/items/${id}`)
}

export function apiFollowShop(shop_id: number) { return request('POST', '/favorites/shops', { shop_id }) }
export function apiUnfollowShop(shop_id: number) { return request('DELETE', `/favorites/shops/${shop_id}`) }
export function apiGetFollowedShops() { return request<{items: Array<{shop_id:number}>}>('GET', '/favorites/shops') }
