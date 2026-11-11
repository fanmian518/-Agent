/**
 * stores/orders.ts - 订单管理
 * ----------------------------------------------------------------
 * 生成订单（从购物车结算），持久化到 localStorage
 * 支持：取消订单、恢复/继续支付、退款申请、修改备注、复制订单号、
 *       状态流转时间（付款时间/发货时间/完成时间）、物流轨迹、发票信息
 */
import { reactive } from 'vue'
import type { CartItem } from './cart'
import { clearCart } from './cart'
import { apiCreateOrder, apiPayOrder, apiCancelOrder, apiUpdateOrderRemark, apiApplyRefund, apiConfirmReceive } from '@/api/order'
import { apiGetOrderList } from '@/api/order'
import { getToken } from '@/api/request'

/**
 * 订单商品条目（从 CartItem 精简映射而来：只保留渲染订单所需字段）
 */
export interface OrderItem {
  id: number       // 商品 id（便于跳详情 / 再次购买）
  name: string     // 商品名快照
  price: number    // 下单时商品单价快照（商品后续改价不影响历史订单）
  emoji: string    // emoji 图标快照
  quantity: number // 购买数量
}

/**
 * 订单生命周期状态
 *  pending  待付款（createOrder 初始状态）
 *  paid     已付款   -> 用户在 CheckoutView 里点「立即支付」
 *  shipped  已发货   -> Demo：paid 后 2 秒自动变成 shipped
 *  done     已完成   -> 用户在订单 Tab 里点「确认收货」
 *  cancelled 已取消  -> cancelOrder()
 *  refunding 退款中  -> applyRefund()
 *  refunded  已退款  -> Demo：refunding 后 2 秒自动变成 refunded
 */
export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'done' | 'cancelled' | 'refunding' | 'refunded'

/** 物流单条节点（用于 ProfileView 订单 Tab 中「🚚 物流信息」弹窗展示） */
export interface LogisticsNode {
  time: string     // 格式化时间文案 YYYY-MM-DD HH:mm:ss
  status: string   // 节点描述：如"快递员已揽收"
  isNew?: boolean  // 是否为最新节点（渲染时左侧蓝点 + 蓝字高亮）
}

/** 发票信息（订单维度一张票；Demo：下单时可手动生成，后续在"发票查看"弹窗展示） */
export interface InvoiceInfo {
  type: '个人' | '企业'  // 发票类型
  title: string          // 发票抬头（个人=姓名，企业=公司名）
  taxNo?: string         // 税号（仅企业需要）
  content: string        // 开票内容：如"商品明细"、"办公用品"
  issued: boolean        // 是否已开具（true=展示"已开具"，false=提示未申请）
}

/** 退款申请详情（订单内最多 1 条） */
export interface RefundInfo {
  appliedAt: number                 // 申请时间戳
  reason: string                    // 用户填写的退款原因
  amount: number                    // 退款金额（=下单时订单总额）
  status: '审核中' | '已同意' | '已拒绝'  // 审核状态
}

/** 订单主体：购物车结算 createOrder 生成一份 */
export interface Order {
  id: string                 // 订单号：YYYYMMDDhhmmss + 4 位随机
  addressId?: number         // 创建订单时实际使用的收货地址 ID
  items: OrderItem[]         // 订单明细条目
  totalAmount: number        // 实付金额 = Σ(price * quantity)
  status: OrderStatus        // 订单状态
  createdAt: number          // 下单时间（= createOrder 执行时间）
  paidAt?: number            // 付款时间（paid 后写入）
  shippedAt?: number         // 发货时间（shipped 后写入；或 paid 2s 后自动）
  doneAt?: number            // 完成时间（用户点确认收货后写入）
  cancelledAt?: number       // 取消时间（pending 被 cancelOrder 后写入）
  logistics?: LogisticsNode[]// 物流节点数组（paid/shipped 自动 mock 生成）
  remark?: string            // 订单备注（用户在订单 Tab 弹窗里输入）
  invoice?: InvoiceInfo      // 发票信息（如有）
  refund?: RefundInfo        // 退款申请信息（applyRefund 后写入）
  payMethod?: string         // 支付方式文案（如"微信支付"/"支付宝"）
}

// localStorage 持久化键
const STORAGE_KEY = 'shop_orders'

/** localStorage 加载（容错脏数据） */
const load = (): Order[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// 所有订单的响应式容器（ProfileView /order/ 路由入口 / Checkout 都会引用）
const state = reactive<{ list: Order[] }>({ list: load() })

/** 从后端同步订单列表，确保“我的订单”展示真实订单状态。 */
export async function refreshOrders() {
  const token = getToken()
  if (!token) { clearOrdersState(); return }
  const result = await apiGetOrderList()
  if (getToken() !== token) { clearOrdersState(); return }
  const rows = (result as any).orders ?? result
  state.list.splice(0, state.list.length, ...(rows as any[]).map(row => ({
    id: row.order_id ?? row.id,
    addressId: row.address_id ?? row.addressId,
    items: (row.items ?? []).map((item: any) => ({ id: item.product_id ?? item.id, name: item.name ?? item.product_name, price: Number(item.price), emoji: '🛍️', quantity: item.quantity })),
    totalAmount: Number(row.payable_amount ?? row.total_amount ?? row.totalAmount ?? 0),
    status: row.status === 'pending_payment' ? 'pending' : row.status,
    createdAt: Date.parse(row.created_at ?? row.createdAt), payMethod: row.payment_method
  })))
  save()
}

/** 每次订单变化写回 localStorage */
const save = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(state.list))

/**
 * 生成订单号：YYYYMMDDhhmmss + 4 位随机码
 *   时间戳前缀便于排序；随机码避免同一秒多笔订单 id 相同
 */
const genOrderId = () => {
  const now = new Date()
  const pad = (n: number) => n.toString().padStart(2, '0')
  const base = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  const rand = Math.floor(Math.random() * 10000).toString().padStart(4, '0')
  return `${base}${rand}`
}

// ====== 时间格式化工具（仅本文件内部使用） ======
const padTime = (n: number) => n.toString().padStart(2, '0')
const fmt = (ts: number) => {
  const d = new Date(ts)
  return `${d.getFullYear()}-${padTime(d.getMonth() + 1)}-${padTime(d.getDate())} ${padTime(d.getHours())}:${padTime(d.getMinutes())}:${padTime(d.getSeconds())}`
}

/**
 * 根据订单状态生成 Mock 物流轨迹
 *   paid：刚支付，仅一个"等待商家发货"节点
 *   shipped/done：苏州转运中心 → 南京分拨 → 快递员派送
 *   其它状态：返回空数组
 */
const buildLogistics = (status: OrderStatus): LogisticsNode[] => {
  const base = Date.now()
  if (status === 'paid') {
    return [
      { time: fmt(base),            status: '订单已支付，等待商家发货', isNew: true }
    ]
  }
  if (status === 'shipped' || status === 'done') {
    return [
      { time: fmt(base - 1000 * 60 * 60 * 36), status: '【苏州转运中心】已发出' },
      { time: fmt(base - 1000 * 60 * 60 * 12), status: '【南京分拨中心】已到达' },
      { time: fmt(base - 1000 * 60 * 30),       status: '快递员 张师傅(138****1234) 正在派送中，电话保持畅通', isNew: true }
    ]
  }
  return []
}

/**
 * 从购物车勾选商品创建一笔订单
 *   - 空购物车 → null （调用方要做校验并提示）
 *   - 订单初始状态为 pending，时间戳 createdAt 写入
 *   - 成功后调用 clearCart() 清空已经选中的商品（真正的 Demo 购物车清空）
 *   - 调用方：CartView.vue「去结算」、ProductDetailView.vue「立即购买」
 */
export function createOrder(cartItems: CartItem[], opts?: { remark?: string; invoice?: InvoiceInfo }): Order | null {
  if (cartItems.length === 0) return null
  apiCreateOrder(cartItems.map(i => ({ id: i.id, name: i.name, price: i.price, emoji: i.emoji, quantity: i.quantity })), { remark: opts?.remark })
    .catch(() => undefined)
  const items: OrderItem[] = cartItems.map(i => ({
    id: i.id,
    name: i.name,
    price: i.price,
    emoji: i.emoji,
    quantity: i.quantity
  }))
  const totalAmount = items.reduce((sum, i) => sum + i.price * i.quantity, 0)
  const order: Order = {
    id: genOrderId(),
    items,
    totalAmount,
    status: 'pending',
    createdAt: Date.now(),
    remark: opts?.remark?.trim() || undefined,
    invoice: opts?.invoice
  }
  state.list.unshift(order)
  save()
  // 清空购物车（createOrder 仅在用户确认"去结算"时调用，清空是业务语义）
  clearCart()
  return order
}

/**
 * 更新订单状态（状态机核心函数），按新状态写入对应时间戳 / 物流节点
 *   - → paid：写 paidAt、payMethod、初始物流节点；并 2 秒后自动 shipped
 *   - → shipped：写 shippedAt、完整物流
 *   - → done：写 doneAt
 *   - → cancelled：写 cancelledAt
 * @param orderId 订单号
 * @param status 目标状态
 * @param extra 额外参数（支付方式等）
 */
export function updateOrderStatus(orderId: string, status: OrderStatus, extra?: { payMethod?: string }) {
  if (status === 'paid') apiPayOrder(orderId, extra?.payMethod || '在线支付').catch(() => undefined)
  if (status === 'cancelled') apiCancelOrder(orderId).catch(() => undefined)
  if (status === 'done') apiConfirmReceive(orderId).catch(() => undefined)
  const order = state.list.find(o => o.id === orderId)
  if (!order) return
  order.status = status
  const now = Date.now()
  if (status === 'paid') {
    order.paidAt = now
    order.logistics = buildLogistics('paid')
    order.payMethod = extra?.payMethod
    // Mock：2 秒后自动发货（演示发货时间写入与物流变化）
    setTimeout(() => {
      const cur = state.list.find(o => o.id === orderId)
      if (cur && cur.status === 'paid') {
        cur.status = 'shipped'
        cur.shippedAt = Date.now()
        cur.logistics = buildLogistics('shipped')
        save()
      }
    }, 2000)
  } else if (status === 'shipped') {
    order.shippedAt = now
    order.logistics = buildLogistics('shipped')
  } else if (status === 'done') {
    order.doneAt = now
  } else if (status === 'cancelled') {
    order.cancelledAt = now
  }
  save()
}

/**
 * 取消订单：仅允许对待付款（pending）订单生效
 *   - 触发源：ProfileView 订单 Tab 待付款「❌取消订单」按钮
 *   - CheckoutView 倒计时结束也会直接调 updateOrderStatus cancel，不调这里
 */
export function cancelOrder(orderId: string): { ok: boolean; msg: string } {
  const order = state.list.find(o => o.id === orderId)
  if (!order) return { ok: false, msg: '订单不存在' }
  if (order.status !== 'pending') return { ok: false, msg: '仅待付款订单可取消' }
  apiCancelOrder(orderId).catch(() => undefined)
  order.status = 'cancelled'
  order.cancelledAt = Date.now()
  save()
  return { ok: true, msg: '订单已取消' }
}

/** 清空当前前端订单状态，例如退出登录时使用。 */
export function clearOrdersState() {
  state.list.splice(0, state.list.length)
  save()
}

/**
 * 修改订单备注（空字符串会清除 remark，避免存空白字符）
 * 触发源：ProfileView 订单卡片「📝备注」按钮弹窗
 */
export function setOrderRemark(orderId: string, remark: string) {
  apiUpdateOrderRemark(orderId, remark).catch(() => undefined)
  const order = state.list.find(o => o.id === orderId)
  if (!order) return
  order.remark = remark.trim() || undefined
  save()
}

/**
 * 申请退款（paid/shipped/done 三种状态允许）
 *   - 先切为 refunding，写入 refund 对象
 *   - Mock：2 秒后自动通过（status refunded + refund.status='已同意'）
 * 触发源：订单卡片「💰申请退款」按钮 → 弹窗输入原因 → confirm
 */
export function applyRefund(orderId: string, reason: string): { ok: boolean; msg: string } {
  const order = state.list.find(o => o.id === orderId)
  if (!order) return { ok: false, msg: '订单不存在' }
  if (!['paid', 'shipped', 'done'].includes(order.status)) {
    return { ok: false, msg: '当前状态不支持退款申请' }
  }
  if (!reason.trim()) return { ok: false, msg: '请填写退款原因' }
  apiApplyRefund(orderId, reason).catch(() => undefined)
  order.status = 'refunding'
  order.refund = {
    appliedAt: Date.now(),
    reason: reason.trim(),
    amount: order.totalAmount,
    status: '审核中'
  }
  save()
  // Mock：2 秒后自动审核通过
  setTimeout(() => {
    const cur = state.list.find(o => o.id === orderId)
    if (cur && cur.status === 'refunding' && cur.refund) {
      cur.status = 'refunded'
      cur.refund.status = '已同意'
      save()
    }
  }, 2000)
  return { ok: true, msg: '退款申请已提交，等待审核（演示：2 秒后自动通过）' }
}

/**
 * 复制订单号到剪贴板
 *   优先用 HTTPS 下 navigator.clipboard（安全），否则用 textarea + document.execCommand('copy') 回退
 *   触发源：订单卡片「📋复制单号」按钮
 */
export async function copyOrderId(orderId: string): Promise<{ ok: boolean; msg: string }> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(orderId)
    } else {
      const ta = document.createElement('textarea')
      ta.value = orderId
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    return { ok: true, msg: `订单号已复制：${orderId}` }
  } catch {
    return { ok: false, msg: '复制失败，请手动选中订单号复制' }
  }
}

/** 返回响应式 state.list（ProfileView 订单 Tab 遍历渲染） */
export function useOrders() {
  return state
}
