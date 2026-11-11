import { request } from './request'
export function apiGetReviews() { return request<{reviews: any[]}>('GET', '/reviews') }
export function apiAddReview(data: any) { return request('POST', '/reviews', data) }
export function apiDeleteReview(id: string) { return request('DELETE', `/reviews/${id}`) }
export function apiGetHistory() { return request<{items: any[]}>('GET', '/history') }
export function apiRecordHistory(product_id: number) { return request('POST', '/history', { product_id }) }
export function apiClearHistory() { return request('DELETE', '/history') }
