import { request } from './request'
export interface AgentResponse {
  session_id?: string
  action?: string
  message?: string
  products?: any[]
  cart_result?: any
  favorites_result?: any
  order_result?: any
  address_required?: any
  error?: string
}
export function executeAgent(message: string, session_id?: string) { return request<AgentResponse>('POST', '/agent/execute', { message, session_id }) }
