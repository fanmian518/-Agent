/**
 * src/api/address.ts —— 收货地址模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/addresses.ts（当前 localStorage 按用户名隔离存储）。
 * 前端"按用户隔离"的逻辑迁到后端后天然成立：后端根据 token 识别用户。
 *
 * store → api 迁移对应（将来联调时替换）：
 *   addresses.list       → apiGetAddressList()
 *   addAddress           → apiCreateAddress
 *   updateAddress        → apiUpdateAddress
 *   deleteAddress        → apiDeleteAddress
 *   setDefaultAddress    → apiSetDefaultAddress
 */
import { request } from './request'

/** 后端地址结构（对齐 stores/addresses.ts 的 Address） */
export interface ApiAddress {
  id: number
  contact_name: string
  phone: string       // 手机号
  province: string
  city: string
  district: string
  street?: string
  community: string
  note?: string
  is_default: boolean
  use_count: number
  last_used_at?: string
}

/** 地址列表（后端排好序：默认在前，其余按 updatedAt 倒序） */
export function apiGetAddressList() {
  return request<{addresses: ApiAddress[]}>('GET', '/addresses')
}

/** 新建地址（isDefault=true 时后端负责把其他地址取消默认） */
export function apiCreateAddress(
  data: Omit<ApiAddress, 'id' | 'is_default' | 'use_count' | 'last_used_at'> & { is_default?: boolean }
) {
  return request<ApiAddress>('POST', '/addresses', data)
}

/** 修改地址（partial：只传要改的字段） */
export function apiUpdateAddress(
  id: string,
  partial: Partial<Pick<ApiAddress, 'contact_name' | 'phone' | 'province' | 'city' | 'district' | 'street' | 'community' | 'note' | 'is_default'>>
) {
  return request<ApiAddress[]>('PUT', `/addresses/${id}`, partial)
}

/** 删除地址（若删的是默认地址，后端自动把剩余第一条升为默认） */
export function apiDeleteAddress(id: string) {
  return request<ApiAddress[]>('DELETE', `/addresses/${id}`)
}

/** 设为默认地址（后端保证全用户只有一个默认） */
export function apiSetDefaultAddress(id: string) {
  return request<ApiAddress[]>('PUT', `/addresses/${id}/default`)
}
