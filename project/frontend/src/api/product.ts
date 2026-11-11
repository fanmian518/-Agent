/**
 * src/api/product.ts —— 商品模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/products.ts（当前是硬编码的 PRODUCTS 数组）。
 * store → api 迁移对应（将来联调时替换）：
 *   getProductById(id)            → apiGetProductDetail(id)
 *   getProductsByCategory(cat)    → apiGetProductList({ category: cat })
 *   allProducts                   → apiGetProductList()
 *   HeaderNav 搜索框（TODO /search）→ apiGetProductList({ keyword })
 */
import { request } from './request'

/** 后端商品结构（字段与 stores/products.ts 的 Product 完全对齐） */
export interface ApiProduct {
  id: number
  name: string
  desc?: string
  price: number
  originalPrice?: number
  emoji: string
  bgColor: string
  sales: number
  tag?: string
  category: 'digital' | 'fashion' | 'homegoods' | 'newuser' | 'daily'
}

/** 商品列表：支持分类过滤 / 关键字搜索 / 分页 */
export function apiGetProductList(params?: {
  category?: ApiProduct['category']
  keyword?: string
  page?: number
  pageSize?: number
}) {
  return request<{products: ApiProduct[]}>('GET', '/products', undefined, params)
}

/** 商品详情（id 不存在时后端应返回业务错误码） */
export function apiGetProductDetail(id: number) {
  return request<ApiProduct>('GET', `/products/${id}`)
}
