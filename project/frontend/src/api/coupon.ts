/**
 * src/api/coupon.ts —— 优惠券模块后端接口（预埋，未启用）
 * ----------------------------------------------------------------
 * 对应 stores/coupons.ts（当前 localStorage shop_coupons）。
 * 前端三个 computed（available/used/expired）迁到后端后，
 * 改为用 status 参数向后端要对应分组的列表。
 *
 * store → api 迁移对应（将来联调时替换）：
 *   availableCoupons/usedCoupons/expiredCoupons → apiGetCoupons('available'|'used'|'expired')
 *   claimCoupon  → apiClaimCoupon
 *   useCoupon    → apiUseCoupon（下单核销）
 */
import { request } from './request'

/** 优惠券适用范围（与 stores/coupons.ts 的 CouponScope 对齐） */
export type ApiCouponScope = 'all' | 'digital' | 'fashion' | 'homegoods' | 'newuser'

/** 后端优惠券结构（对齐 stores/coupons.ts 的 Coupon） */
export interface ApiCoupon {
  id: string
  title: string
  value: number        // 面额（元）
  threshold: number    // 使用门槛（0=无门槛）
  scope: ApiCouponScope
  desc?: string
  claimedAt: number
  startAt: number
  endAt: number
  usedAt?: number
}

/** 我的优惠券列表；status 不传 = 全部 */
export function apiGetCoupons(status?: 'available' | 'used' | 'expired') {
  return request<{coupons: ApiCoupon[]}>('GET', '/coupons', undefined, { status })
}

/** 领取优惠券（生效时间/有效期由后端计算） */
export function apiClaimCoupon(
  data: Pick<ApiCoupon, 'title' | 'value' | 'threshold' | 'scope'> & {
    desc?: string
    durationDays?: number
  }
) {
  return request<ApiCoupon>('POST', '/coupons', { ...data, duration_days: data.durationDays })
}

/** 核销优惠券（下单时使用；orderId 用于对账，可选） */
export function apiUseCoupon(id: string, orderId?: string) {
  return request<ApiCoupon>('POST', `/coupons/${id}/use`, { orderId })
}
