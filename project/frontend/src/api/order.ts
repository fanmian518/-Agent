/**
 * src/api/order.ts —— 订单模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/orders.ts（当前 localStorage shop_orders，状态流转在前端模拟）。
 * store → api 迁移对应（将来联调时替换）：
 *   createOrder(...)                  → apiCreateOrder（订单号由后端生成）
 *   updateOrderStatus(id,'paid',{payMethod}) → apiPayOrder（真实支付走后端支付网关）
 *   cancelOrder(id)                   → apiCancelOrder
 *   applyRefund(id, reason)           → apiApplyRefund
 *   setOrderRemark(id, text)          → apiUpdateOrderRemark
 *   useOrders().list                  → apiGetOrderList() / apiGetOrderDetail(id)
 */
import { request } from './request'

/** 订单状态（与 stores/orders.ts 的 OrderStatus 完全对齐） */
export type ApiOrderStatus =
  | 'pending'     // 待付款
  | 'paid'        // 已付款
  | 'shipped'     // 已发货
  | 'done'        // 已完成
  | 'cancelled'   // 已取消
  | 'refunding'   // 退款中
  | 'refunded'    // 已退款

/** 后端订单单项结构（对齐 stores/orders.ts 的 OrderItem） */
export interface ApiOrderItem {
  id: number
  name: string
  price: number
  emoji: string
  quantity: number
}

/** 后端订单结构（对齐 stores/orders.ts 的 Order，字段按需增减） */
export interface ApiOrder {
  id: string              // 订单号（后端生成，如 20260905xxxx）
  address_id?: number     // 创建订单时实际使用的收货地址
  items: ApiOrderItem[]
  totalAmount: number
  status: ApiOrderStatus
  createdAt: number
  paidAt?: number
  payMethod?: string
  remark?: string
}

/** 创建订单（items 来自购物车选中项；后端负责生成订单号 + 清空已结算购物车项） */
export function apiCreateOrder(
  items: ApiOrderItem[],
  extra?: { remark?: string; address_id?: number; product_ids?: number[] }
) {
  return request<ApiOrder>('POST', '/orders', { ...extra, product_ids: extra?.product_ids ?? items.map(item => item.id) })
}

/** 我的订单列表（status 不传 = 全部状态） */
export function apiGetOrderList(status?: ApiOrderStatus) {
  return request<{orders: ApiOrder[]}>('GET', '/orders', undefined, { status })
}

/** 订单详情 */
export function apiGetOrderDetail(orderId: string) {
  return request<ApiOrder>('GET', `/orders/${orderId}`)
}

/** 支付订单（payMethod：微信/支付宝/银行卡；真实场景由后端对接支付网关） */
export function apiPayOrder(orderId: string, payMethod: string) {
  return request<ApiOrder>('POST', `/orders/${orderId}/pay`, { payment_method: payMethod })
}

/** 取消订单（后端校验：仅 pending 状态可取消） */
export function apiCancelOrder(orderId: string) {
  return request<ApiOrder>('POST', `/orders/${orderId}/cancel`)
}

export function apiConfirmReceive(orderId: string) {
  return request<ApiOrder>('POST', `/orders/${orderId}/receive`)
}

/** 申请退款（reason：退款原因） */
export function apiApplyRefund(orderId: string, reason: string) {
  return request<ApiOrder>('POST', `/orders/${orderId}/refund`, { reason })
}

/** 修改订单备注 */
export function apiUpdateOrderRemark(orderId: string, remark: string) {
  return request<ApiOrder>('PUT', `/orders/${orderId}/remark`, { remark })
}
