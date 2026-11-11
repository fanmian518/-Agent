<script setup lang="ts">
/**
 * ProfileView.vue - 用户中心
 * ----------------------------------------------------------------
 * 顶部：用户信息卡 + 返回首页 + 退出登录
 * 主体：4 个标签页切换
 *   - 购物车：修改数量 / 删除 / 清空 / 结算
 *   - 收藏夹：查看 / 取消收藏
 *   - 浏览历史：查看 / 清空
 *   - 订单：查看订单列表（从购物车结算生成）
 */
import { ref, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUsername, logout } from '@/stores/user'
import { useCart, removeFromCart, updateQuantity, clearCart } from '@/stores/cart'
import { useFavorites, removeFromFavorite } from '@/stores/favorites'
import { useHistory, clearHistory } from '@/stores/history'
import {
  useOrders,
  createOrder,
  cancelOrder,
  updateOrderStatus,
  applyRefund,
  setOrderRemark,
  copyOrderId
} from '@/stores/orders'
import type { Order, OrderStatus } from '@/stores/orders'
import { useShops, getFollowedShops, toggleFollow, isFollowed } from '@/stores/shops'
import { useReviews, addReview, deleteReview } from '@/stores/reviews'
import {
  useCoupons,
  availableCoupons,
  usedCoupons,
  expiredCoupons,
  scopeLabel,
  scopeColor,
  formatCouponDate,
  remainingDays,
  removeCoupon,
  ensureInitCoupons
} from '@/stores/coupons'
import {
  useAddresses,
  addAddress,
  updateAddress,
  deleteAddress,
  setDefaultAddress
} from '@/stores/addresses'
import type { Address } from '@/stores/addresses'

// 初始化：确保新用户有默认优惠券
ensureInitCoupons()

const route = useRoute()
const router = useRouter()

type ProfileTabKey = 'cart' | 'coupons' | 'favorites' | 'history' | 'orders' | 'shops' | 'reviews' | 'addresses'
const VALID_TABS: ProfileTabKey[] = ['cart', 'coupons', 'favorites', 'addresses', 'shops', 'history', 'orders', 'reviews']

// 当前激活标签（新增：addresses 地址管理）
// 路由 query 里带 ?tab=xxx 时自动切到对应 Tab（如收银台点"去添加地址"跳回）
const initialTab = (): ProfileTabKey => {
  const q = route.query.tab as string | undefined
  return VALID_TABS.includes(q as any) ? (q as ProfileTabKey) : 'cart'
}
const activeTab = ref<ProfileTabKey>(initialTab())

// 各 store 响应式访问
const cart = useCart()
const favorites = useFavorites()
const history = useHistory()
const orders = useOrders()
const shops = useShops()
const reviews = useReviews()
const coupons = useCoupons()
const addresses = useAddresses()

// ============================================================
// 地址管理：新增 / 编辑 / 删除 / 设默认
// ============================================================

// 弹窗：null=关闭；{mode:'add'} | {mode:'edit', id}
const addrDialog = ref<{ show: boolean; mode: 'add' | 'edit'; id?: string; error: string }>({
  show: false, mode: 'add', id: undefined, error: ''
})
// 地址表单（新增/编辑共用）
const addrForm = reactive<{
  name: string
  phone: string
  region: string
  detail: string
  isDefault: boolean
}>({
  name: '', phone: '', region: '', detail: '', isDefault: false
})

const openAddAddress = () => {
  addrForm.name = ''
  addrForm.phone = ''
  addrForm.region = ''
  addrForm.detail = ''
  addrForm.isDefault = addresses.list.length === 0
  addrDialog.value = { show: true, mode: 'add', error: '' }
}
const openEditAddress = (addr: Address) => {
  addrForm.name = addr.name
  addrForm.phone = addr.phone
  addrForm.region = addr.region
  addrForm.detail = addr.detail
  addrForm.isDefault = addr.isDefault
  addrDialog.value = { show: true, mode: 'edit', id: addr.id, error: '' }
}
const closeAddrDialog = () => {
  addrDialog.value = { show: false, mode: 'add', error: '' }
}

// 提交表单：新增 or 编辑
const submitAddress = () => {
  addrDialog.value.error = ''
  if (addrDialog.value.mode === 'add') {
    const r = addAddress({
      name: addrForm.name,
      phone: addrForm.phone,
      region: addrForm.region,
      detail: addrForm.detail,
      isDefault: addrForm.isDefault
    })
    if (!r.ok) { addrDialog.value.error = r.msg; return }
    closeAddrDialog()
  } else {
    if (!addrDialog.value.id) return
    const r = updateAddress(addrDialog.value.id, {
      name: addrForm.name,
      phone: addrForm.phone,
      region: addrForm.region,
      detail: addrForm.detail,
      isDefault: addrForm.isDefault
    })
    if (!r.ok) { addrDialog.value.error = r.msg; return }
    closeAddrDialog()
  }
}

const onDeleteAddress = (addr: Address) => {
  if (!confirm(`确定删除 ${addr.name} 的收货地址吗？`)) return
  const r = deleteAddress(addr.id)
  if (!r.ok) alert(r.msg)
}

const onSetDefault = (addr: Address) => {
  if (addr.isDefault) return
  const r = setDefaultAddress(addr.id)
  if (!r.ok) alert(r.msg)
}

// 格式化地址卡的手机号中间 4 位打码
const maskPhone = (p: string) =>
  p.length === 11 ? p.slice(0, 3) + '****' + p.slice(7) : p

// ====== 浏览历史：带确认弹窗的清空按钮 ======
// （放在 script 里而不是模板内联 confirm()，避免 Vue+TS 严格模板检查报错）
const handleClearHistory = () => {
  if (window.confirm('确定要清空全部浏览历史吗？')) clearHistory()
}

// ====== 优惠券子标签 ======
const couponSubTab = ref<'available' | 'used' | 'expired'>('available')

// ====== 购物车 ======
const cartTotal = computed(() =>
  cart.items.reduce((sum, i) => sum + i.price * i.quantity, 0)
)

const handleCheckout = () => {
  if (cart.items.length === 0) return
  const order = createOrder(cart.items)
  if (order) {
    alert(`下单成功！订单号：${order.id}`)
    activeTab.value = 'orders'
  }
}

// ====== 退出登录 ======
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    logout()
    router.push('/')
  }
}

// ====== 返回首页 ======
const goHome = () => router.push('/')

// ====== 时间格式化 ======
const formatTime = (ts: number) => {
  const d = new Date(ts)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ====== 订单状态映射（新增：退款中/已退款） ======
const statusLabel: Record<OrderStatus, string> = {
  pending: '待付款',
  paid: '已付款',
  shipped: '已发货',
  done: '已完成',
  cancelled: '已取消',
  refunding: '退款中',
  refunded: '已退款'
}

const statusClass: Record<OrderStatus, string> = {
  pending: 'st-pending',
  paid: 'st-paid',
  shipped: 'st-shipped',
  done: 'st-done',
  cancelled: 'st-cancelled',
  refunding: 'st-refunding',
  refunded: 'st-refunded'
}

// ====== 订单：状态筛选 Tab ======
type OrderFilter = 'all' | OrderStatus
const orderFilter = ref<OrderFilter>('all')
const ORDER_FILTER_TABS: Array<{ key: OrderFilter; label: string }> = [
  { key: 'all',        label: '全部' },
  { key: 'pending',    label: '待付款' },
  { key: 'paid',       label: '已付款' },
  { key: 'shipped',    label: '已发货' },
  { key: 'done',       label: '已完成' },
  { key: 'refunding',  label: '退款中' },
  { key: 'refunded',   label: '已退款' },
  { key: 'cancelled',  label: '已取消' }
]
const orderCountByStatus = computed(() => {
  const map: Record<string, number> = { all: orders.list.length }
  for (const s of ['pending', 'paid', 'shipped', 'done', 'refunding', 'refunded', 'cancelled'] as OrderStatus[]) {
    map[s] = orders.list.filter(o => o.status === s).length
  }
  return map
})

// ====== 订单：关键字搜索（按订单号 / 商品名） ======
const orderSearch = ref('')

// ====== 订单：筛选 + 搜索 后的最终列表 ======
const filteredOrders = computed<Order[]>(() => {
  let list = orders.list
  if (orderFilter.value !== 'all') {
    list = list.filter(o => o.status === orderFilter.value)
  }
  const kw = orderSearch.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(o =>
      o.id.toLowerCase().includes(kw) ||
      o.items.some(it => it.name.toLowerCase().includes(kw))
    )
  }
  return list
})

// ====== 订单：各状态的工具操作 ======

// 复制订单号
const onCopyId = async (id: string) => {
  const r = await copyOrderId(id)
  alert(r.msg)
}

// 取消订单（仅 pending）
const onCancelOrder = async (order: Order) => {
  if (!confirm(`确定要取消订单 ${order.id} 吗？`)) return
  const r = cancelOrder(order.id)
  alert(r.msg)
}

// 继续支付（pending → 跳收银台）
const onContinuePay = (order: Order) => {
  router.push({ path: '/checkout', query: { orderId: order.id } })
}

// 确认收货（shipped → done）
const onConfirmReceive = (order: Order) => {
  if (!confirm('确认已收到商品？确认后订单将转为已完成。')) return
  updateOrderStatus(order.id, 'done')
  alert('已确认收货，感谢您的购买！')
}

// ====== 通用弹窗：订单备注 / 退款申请 / 发票查看 / 物流信息 ======
type ModalType = 'remark' | 'refund' | 'invoice' | 'logistics' | null
const orderModal = reactive<{
  type: ModalType
  orderId: string
  // 备注
  remarkText: string
  // 退款
  refundReason: string
}>({
  type: null,
  orderId: '',
  remarkText: '',
  refundReason: ''
})
const findOrder = (id: string) => orders.list.find(o => o.id === id) || null
const activeModalOrder = computed(() => findOrder(orderModal.orderId))

const closeModal = () => {
  orderModal.type = null
  orderModal.orderId = ''
  orderModal.remarkText = ''
  orderModal.refundReason = ''
}

// 打开「订单备注」
const openRemark = (order: Order) => {
  orderModal.type = 'remark'
  orderModal.orderId = order.id
  orderModal.remarkText = order.remark ?? ''
}
const saveRemark = () => {
  if (!orderModal.orderId) return
  setOrderRemark(orderModal.orderId, orderModal.remarkText)
  alert('订单备注已保存')
  closeModal()
}

// 打开「退款申请」
const openRefund = (order: Order) => {
  orderModal.type = 'refund'
  orderModal.orderId = order.id
  orderModal.refundReason = ''
}
const submitRefund = () => {
  if (!orderModal.orderId) return
  const r = applyRefund(orderModal.orderId, orderModal.refundReason)
  alert(r.msg)
  if (r.ok) closeModal()
}

// 打开「发票查看」
const openInvoice = (order: Order) => {
  orderModal.type = 'invoice'
  orderModal.orderId = order.id
}

// 打开「物流信息」
const openLogistics = (order: Order) => {
  orderModal.type = 'logistics'
  orderModal.orderId = order.id
}

// 金额（分/角）格式
const yuan = (n: number) => `¥${n.toFixed(2)}`

// ====== 关注店铺 ======
const followedShops = computed(() => getFollowedShops())

// 格式化粉丝数
const formatFollowers = (n: number): string => {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toString()
}

// ====== 评价管理 ======
// 待评价商品（已完成的订单商品中未评价的）
const pendingReviews = computed(() => {
  const result: Array<{ productId: number; productName: string; productEmoji: string; productBgColor: string; orderId: string }> = []
  for (const order of orders.list) {
    if (order.status === 'done') {
      for (const item of order.items) {
        const alreadyReviewed = reviews.list.some(r => r.productId === item.id)
        if (!alreadyReviewed) {
          result.push({
            productId: item.id,
            productName: item.name,
            productEmoji: item.emoji,
            productBgColor: 'linear-gradient(135deg, #e0e7ff, #c7d2fe)',
            orderId: order.id
          })
        }
      }
    }
  }
  return result
})

// 评价表单状态
const reviewForm = reactive({
  show: false,
  productId: 0,
  productName: '',
  productEmoji: '',
  productBgColor: '',
  orderId: '',
  rating: 5,
  content: ''
})

// 打开评价弹窗
const openReviewForm = (item: typeof pendingReviews.value[number]) => {
  reviewForm.show = true
  reviewForm.productId = item.productId
  reviewForm.productName = item.productName
  reviewForm.productEmoji = item.productEmoji
  reviewForm.productBgColor = item.productBgColor
  reviewForm.orderId = item.orderId
  reviewForm.rating = 5
  reviewForm.content = ''
}

// 提交评价
const submitReview = () => {
  if (!reviewForm.content.trim()) {
    alert('请输入评价内容')
    return
  }
  addReview({
    productId: reviewForm.productId,
    productName: reviewForm.productName,
    productEmoji: reviewForm.productEmoji,
    productBgColor: reviewForm.productBgColor,
    orderId: reviewForm.orderId,
    rating: reviewForm.rating,
    content: reviewForm.content
  })
  reviewForm.show = false
}

// 快捷添加一条演示评价
const addDemoReview = () => {
  addReview({
    productId: 999,
    productName: '极光 Pro 5G 手机',
    productEmoji: '📱',
    productBgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    rating: 5,
    content: '手机很漂亮，续航给力，拍照效果也不错！物流很快，包装完好，推荐购买！'
  })
}
</script>

<template>
  <div class="profile-container">
    <!-- 返回首页按钮 -->
    <button class="back-home" @click="goHome">
      ← 返回首页
    </button>

    <!-- ====== 用户信息卡 ====== -->
    <div class="profile-header">
      <div class="profile-avatar">
        <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${currentUsername}`" alt="头像" />
      </div>
      <div class="profile-info">
        <h2>{{ currentUsername }}</h2>
        <p>欢迎回到优选商城</p>
      </div>
      <button class="logout-btn" @click="handleLogout">退出登录</button>
    </div>

    <!-- ====== 标签页切换 ====== -->
    <div class="profile-tabs">
      <button
        v-for="t in [
          { key: 'cart', label: '🛒 购物车', count: cart.items.length },
          { key: 'coupons', label: '🎟️ 优惠券', count: availableCoupons.length },
          { key: 'favorites', label: '❤️ 收藏夹', count: favorites.items.length },
          { key: 'addresses', label: '📍 地址管理', count: addresses.list.length },
          { key: 'shops', label: '🏪 关注店铺', count: followedShops.length },
          { key: 'history', label: '🕐 浏览历史', count: history.items.length },
          { key: 'orders', label: '📦 我的订单', count: orders.list.length },
          { key: 'reviews', label: '⭐ 评价管理', count: reviews.list.length }
        ]"
        :key="t.key"
        class="profile-tab"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key as any"
      >
        {{ t.label }}
        <span v-if="t.count > 0" class="tab-badge">{{ t.count }}</span>
      </button>
    </div>

    <!-- ====== 标签页内容 ====== -->
    <div class="profile-content">

      <!-- 购物车 -->
      <div v-if="activeTab === 'cart'" class="tab-panel">
        <template v-if="cart.items.length === 0">
          <div class="empty-state">🛒<p>购物车空空如也</p><button @click="goHome">去逛逛</button></div>
        </template>
        <template v-else>
          <div class="item-list">
            <div v-for="item in cart.items" :key="item.id" class="item-row">
              <div class="item-img" :style="{ background: item.bgColor }">
                <span>{{ item.emoji }}</span>
              </div>
              <div class="item-detail">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-price">¥{{ item.price }}</div>
              </div>
              <div class="item-qty">
                <button @click="updateQuantity(item.id, item.quantity - 1)">-</button>
                <span>{{ item.quantity }}</span>
                <button @click="updateQuantity(item.id, item.quantity + 1)">+</button>
              </div>
              <button class="item-del" @click="removeFromCart(item.id)">删除</button>
            </div>
          </div>
          <div class="cart-footer">
            <span class="cart-total">合计：<em>¥{{ cartTotal.toFixed(2) }}</em></span>
            <div class="cart-actions">
              <button class="btn-ghost" @click="clearCart">清空</button>
              <button class="btn-primary" @click="handleCheckout">去结算</button>
            </div>
          </div>
        </template>
      </div>

      <!-- 优惠券 -->
      <div v-else-if="activeTab === 'coupons'" class="tab-panel">
        <!-- 子标签切换 -->
        <div class="coupon-sub-tabs">
          <button
            class="coupon-sub-tab"
            :class="{ active: couponSubTab === 'available' }"
            @click="couponSubTab = 'available'"
          >可用（{{ availableCoupons.length }}）</button>
          <button
            class="coupon-sub-tab"
            :class="{ active: couponSubTab === 'used' }"
            @click="couponSubTab = 'used'"
          >已使用（{{ usedCoupons.length }}）</button>
          <button
            class="coupon-sub-tab"
            :class="{ active: couponSubTab === 'expired' }"
            @click="couponSubTab = 'expired'"
          >已过期（{{ expiredCoupons.length }}）</button>
        </div>

        <!-- 可用优惠券 -->
        <template v-if="couponSubTab === 'available'">
          <div v-if="availableCoupons.length === 0" class="empty-state">
            🎟️<p>暂无可用优惠券</p>
            <button @click="router.push('/category/newuser')">去新人专享领券</button>
          </div>
          <div v-else class="coupon-list">
            <div
              v-for="cp in availableCoupons"
              :key="cp.id"
              class="coupon-card"
            >
              <div class="coupon-face">
                <span class="coupon-value">¥{{ cp.value }}</span>
                <span class="coupon-threshold" v-if="cp.threshold > 0">满{{ cp.threshold }}可用</span>
                <span class="coupon-threshold" v-else>无门槛</span>
              </div>
              <div class="coupon-body">
                <h4 class="coupon-title">{{ cp.title }}</h4>
                <div class="coupon-desc" v-if="cp.desc">{{ cp.desc }}</div>
                <div class="coupon-meta">
                  <span
                    class="coupon-scope"
                    :style="{ backgroundColor: scopeColor[cp.scope] + '1a', color: scopeColor[cp.scope] }"
                  >适用：{{ scopeLabel[cp.scope] }}</span>
                  <span class="coupon-period">有效期至 {{ formatCouponDate(cp.endAt) }}</span>
                </div>
                <span v-if="remainingDays(cp.endAt) <= 3" class="coupon-warn">
                  ⚠️ 仅剩 {{ remainingDays(cp.endAt) }} 天
                </span>
              </div>
              <button class="coupon-action" @click="router.push('/')">去使用</button>
            </div>
          </div>
        </template>

        <!-- 已使用优惠券 -->
        <template v-else-if="couponSubTab === 'used'">
          <div v-if="usedCoupons.length === 0" class="empty-state">
            ✅<p>还没有使用过优惠券</p>
          </div>
          <div v-else class="coupon-list">
            <div
              v-for="cp in usedCoupons"
              :key="cp.id"
              class="coupon-card used"
            >
              <div class="coupon-face">
                <span class="coupon-value">¥{{ cp.value }}</span>
                <span class="coupon-threshold" v-if="cp.threshold > 0">满{{ cp.threshold }}可用</span>
                <span class="coupon-threshold" v-else>无门槛</span>
              </div>
              <div class="coupon-body">
                <h4 class="coupon-title">{{ cp.title }}</h4>
                <div class="coupon-meta">
                  <span
                    class="coupon-scope"
                    :style="{ backgroundColor: scopeColor[cp.scope] + '1a', color: scopeColor[cp.scope] }"
                  >适用：{{ scopeLabel[cp.scope] }}</span>
                  <span class="coupon-period">使用时间 {{ formatTime(cp.usedAt!) }}</span>
                </div>
              </div>
              <span class="coupon-status used-tag">已使用</span>
            </div>
          </div>
        </template>

        <!-- 已过期优惠券 -->
        <template v-else-if="couponSubTab === 'expired'">
          <div v-if="expiredCoupons.length === 0" class="empty-state">
            ⏰<p>还没有过期的优惠券</p>
          </div>
          <div v-else class="coupon-list">
            <div
              v-for="cp in expiredCoupons"
              :key="cp.id"
              class="coupon-card expired"
            >
              <div class="coupon-face">
                <span class="coupon-value">¥{{ cp.value }}</span>
                <span class="coupon-threshold" v-if="cp.threshold > 0">满{{ cp.threshold }}可用</span>
                <span class="coupon-threshold" v-else>无门槛</span>
              </div>
              <div class="coupon-body">
                <h4 class="coupon-title">{{ cp.title }}</h4>
                <div class="coupon-meta">
                  <span
                    class="coupon-scope"
                    :style="{ backgroundColor: scopeColor[cp.scope] + '1a', color: scopeColor[cp.scope] }"
                  >适用：{{ scopeLabel[cp.scope] }}</span>
                  <span class="coupon-period">有效期至 {{ formatCouponDate(cp.endAt) }}</span>
                </div>
              </div>
              <button class="coupon-action-del" @click="removeCoupon(cp.id)">删除</button>
            </div>
          </div>
        </template>
      </div>

      <!-- 收藏夹 -->
      <div v-else-if="activeTab === 'favorites'" class="tab-panel">
        <template v-if="favorites.items.length === 0">
          <div class="empty-state">❤️<p>还没有收藏任何商品</p><button @click="goHome">去逛逛</button></div>
        </template>
        <div v-else class="item-list">
          <div v-for="item in favorites.items" :key="item.id" class="item-row">
            <div class="item-img" :style="{ background: item.bgColor }">
              <span>{{ item.emoji }}</span>
            </div>
            <div class="item-detail">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-price">¥{{ item.price }}</div>
              <div class="item-time">收藏于 {{ formatTime(item.addedAt) }}</div>
            </div>
            <button class="item-del" @click="removeFromFavorite(item.id)">取消收藏</button>
          </div>
        </div>
      </div>

      <!-- 浏览历史：点击图片/名称/整行跳商品详情页 -->
      <div v-else-if="activeTab === 'history'" class="tab-panel">
        <template v-if="history.items.length === 0">
          <div class="empty-state">🕐<p>暂无浏览记录</p><button @click="goHome">去逛逛</button></div>
        </template>
        <template v-else>
          <div class="item-list">
            <div
              v-for="item in history.items"
              :key="item.id"
              class="item-row history-row"
              @click="router.push(`/product/${item.id}`)"
              title="点击查看商品详情"
            >
              <div class="item-img history-img" :style="{ background: item.bgColor }">
                <span>{{ item.emoji }}</span>
              </div>
              <div class="item-detail">
                <div class="item-name history-name">{{ item.name }}</div>
                <div class="item-time">浏览于 {{ formatTime(item.viewedAt) }}</div>
              </div>
              <span class="history-go">查看详情 ›</span>
            </div>
          </div>
          <div class="cart-footer">
            <span class="cart-total">共 {{ history.items.length }} 条记录</span>
            <button
              class="btn-ghost"
              @click.stop="handleClearHistory"
            >清空历史</button>
          </div>
        </template>
      </div>

      <!-- ====== 地址管理：新增 / 编辑 / 删除 / 设默认 ====== -->
      <div v-else-if="activeTab === 'addresses'" class="tab-panel">
        <div class="addr-head">
          <div>
            <h3 class="addr-title">📍 收货地址</h3>
            <p class="addr-sub">管理您的收货地址，购买时一键选择默认地址</p>
          </div>
          <button class="btn-primary addr-add-btn" @click="openAddAddress">+ 新增地址</button>
        </div>

        <template v-if="addresses.list.length === 0">
          <div class="empty-state">
            🏡
            <p>还没有添加收货地址</p>
            <button @click="openAddAddress">新增地址</button>
          </div>
        </template>

        <div v-else class="addr-list">
          <div
            v-for="addr in addresses.list"
            :key="addr.id"
            class="addr-card"
            :class="{ default: addr.isDefault }"
          >
            <!-- 卡片头：默认角标 + 姓名 + 手机号 -->
            <div class="addr-card-head">
              <div class="addr-card-head-left">
                <span v-if="addr.isDefault" class="addr-default-tag">默认</span>
                <span class="addr-name">{{ addr.name }}</span>
                <span class="addr-phone">{{ maskPhone(addr.phone) }}</span>
              </div>
              <div class="addr-card-head-right">
                <button
                  class="addr-link"
                  :disabled="addr.isDefault"
                  :class="{ off: addr.isDefault }"
                  @click="onSetDefault(addr)"
                >设为默认</button>
                <button class="addr-link" @click="openEditAddress(addr)">编辑</button>
                <button class="addr-link danger" @click="onDeleteAddress(addr)">删除</button>
              </div>
            </div>
            <!-- 地址文本 -->
            <p class="addr-text">
              <span class="addr-region">{{ addr.region }}</span>
              <span class="addr-detail">{{ addr.detail }}</span>
            </p>
          </div>
        </div>

        <!-- ====== 新增 / 编辑地址共用弹窗 ====== -->
        <div v-if="addrDialog.show" class="review-modal-mask" @click.self="closeAddrDialog">
          <div class="review-modal addr-modal">
            <h3 class="review-modal-title">
              {{ addrDialog.mode === 'add' ? '➕ 新增收货地址' : '✏️ 编辑收货地址' }}
            </h3>

            <div class="addr-fields">
              <label class="addr-field">
                <span class="addr-label"><i>*</i> 收货人</span>
                <input
                  v-model="addrForm.name"
                  type="text"
                  maxlength="20"
                  class="addr-input"
                  placeholder="请输入收货人姓名"
                />
              </label>

              <label class="addr-field">
                <span class="addr-label"><i>*</i> 手机号码</span>
                <input
                  v-model="addrForm.phone"
                  type="tel"
                  maxlength="11"
                  class="addr-input"
                  placeholder="请输入 11 位手机号"
                />
              </label>

              <label class="addr-field">
                <span class="addr-label"><i>*</i> 所在地区</span>
                <input
                  v-model="addrForm.region"
                  type="text"
                  class="addr-input"
                  placeholder="如：江苏省 徐州市 云龙区"
                />
              </label>

              <label class="addr-field">
                <span class="addr-label"><i>*</i> 详细地址</span>
                <textarea
                  v-model="addrForm.detail"
                  rows="3"
                  maxlength="120"
                  class="addr-input addr-textarea"
                  placeholder="街道、楼牌号、门牌号等（最多 120 字）"
                ></textarea>
              </label>

              <label class="addr-default-row">
                <input type="checkbox" v-model="addrForm.isDefault" class="addr-check" />
                <span>设为默认收货地址（下单时自动选择）</span>
              </label>

              <p v-if="addrDialog.error" class="addr-error">⚠️ {{ addrDialog.error }}</p>
            </div>

            <div class="review-modal-actions">
              <button class="btn-ghost" @click="closeAddrDialog">取消</button>
              <button class="btn-primary" @click="submitAddress">
                {{ addrDialog.mode === 'add' ? '保存地址' : '保存修改' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 我的订单：搜索 + 状态筛选 + 订单卡片 + 通用弹窗 -->
      <div v-else-if="activeTab === 'orders'" class="tab-panel">

        <!-- 搜索 + 状态筛选工具条 -->
        <div class="order-toolbar">
          <input
            v-model="orderSearch"
            type="text"
            class="order-search"
            placeholder="搜索订单号 / 商品名称"
          />
          <button class="order-search-btn">🔍</button>
        </div>

        <div class="order-sub-tabs">
          <button
            v-for="t in ORDER_FILTER_TABS"
            :key="t.key"
            class="order-sub-tab"
            :class="{ active: orderFilter === t.key }"
            @click="orderFilter = t.key"
          >
            {{ t.label }}
            <span v-if="(orderCountByStatus[t.key] ?? 0) > 0" class="ost-badge">
              {{ orderCountByStatus[t.key] }}
            </span>
          </button>
        </div>

        <!-- 空状态 -->
        <template v-if="filteredOrders.length === 0">
          <div class="empty-state">
            📦
            <p>{{ orders.list.length === 0 ? '还没有订单' : '没有符合条件的订单' }}</p>
            <button @click="goHome">去购物</button>
          </div>
        </template>

        <!-- 订单卡片列表 -->
        <div v-else class="order-list">
          <div v-for="order in filteredOrders" :key="order.id" class="order-card">
            <!-- 卡片头：订单号（可点复制）+ 状态 + 复制按钮 -->
            <div class="order-head">
              <span class="order-id" @click="onCopyId(order.id)" title="点击复制订单号">
                📋 订单号：{{ order.id }}
              </span>
              <span class="order-status" :class="statusClass[order.status]">
                {{ statusLabel[order.status] }}
              </span>
            </div>

            <!-- 时间线：已付款订单显示 付款/发货/完成 时间 + 支付方式 -->
            <div v-if="order.paidAt || order.shippedAt || order.doneAt" class="order-timeline">
              <div class="ot-node done">
                <span class="ot-dot"></span>
                <div>
                  <p class="ot-title">下单</p>
                  <p class="ot-time">{{ formatTime(order.createdAt) }}</p>
                </div>
              </div>
              <div class="ot-node" :class="{ done: !!order.paidAt }">
                <span class="ot-dot"></span>
                <div>
                  <p class="ot-title">付款{{ order.payMethod ? `（${order.payMethod}）` : '' }}</p>
                  <p class="ot-time">{{ order.paidAt ? formatTime(order.paidAt) : '—' }}</p>
                </div>
              </div>
              <div class="ot-node" :class="{ done: !!order.shippedAt }">
                <span class="ot-dot"></span>
                <div>
                  <p class="ot-title">发货</p>
                  <p class="ot-time">{{ order.shippedAt ? formatTime(order.shippedAt) : '—' }}</p>
                </div>
              </div>
              <div class="ot-node" :class="{ done: !!order.doneAt }">
                <span class="ot-dot"></span>
                <div>
                  <p class="ot-title">完成</p>
                  <p class="ot-time">{{ order.doneAt ? formatTime(order.doneAt) : '—' }}</p>
                </div>
              </div>
            </div>

            <!-- 商品列表 -->
            <div class="order-items">
              <div v-for="oi in order.items" :key="oi.id" class="order-item">
                <div
                  class="item-img small order-item-img"
                  @click="router.push(`/product/${oi.id}`)"
                  title="查看商品详情"
                  style="background: linear-gradient(135deg, #e0e7ff, #c7d2fe); cursor: pointer;"
                >
                  <span>{{ oi.emoji }}</span>
                </div>
                <div class="item-detail">
                  <div
                    class="item-name order-item-name"
                    @click="router.push(`/product/${oi.id}`)"
                    title="查看商品详情"
                  >{{ oi.name }}</div>
                  <div class="item-price">¥{{ oi.price }} × {{ oi.quantity }}</div>
                </div>
                <!-- 已完成状态显示"评价"按钮 -->
                <button
                  v-if="order.status === 'done' && !reviews.list.some(r => r.productId === oi.id)"
                  class="item-review-btn"
                  @click="openReviewForm({ productId: oi.id, productName: oi.name, productEmoji: oi.emoji, productBgColor: 'linear-gradient(135deg, #e0e7ff, #c7d2fe)', orderId: order.id })"
                >评价</button>
              </div>
            </div>

            <!-- 备注展示 -->
            <div v-if="order.remark" class="order-remark">
              📝 订单备注：{{ order.remark }}
            </div>

            <!-- 退款状态展示 -->
            <div v-if="order.refund" class="order-refund">
              💰 退款：¥{{ order.refund.amount.toFixed(2) }} ·
              原因：{{ order.refund.reason }} ·
              状态：<b>{{ order.refund.status }}</b>
            </div>

            <!-- 卡片底部：时间 + 合计 + 操作按钮 -->
            <div class="order-foot">
              <span class="order-time">{{ formatTime(order.createdAt) }} 下单</span>
              <span class="order-total">合计：<em>¥{{ order.totalAmount.toFixed(2) }}</em></span>
            </div>

            <!-- 订单操作按钮：按状态显示不同组合 -->
            <div class="order-actions">
              <!-- 小工具按钮（所有状态通用，只要数据存在） -->
              <button class="oa-btn ghost" @click="onCopyId(order.id)">📋 复制单号</button>
              <button class="oa-btn ghost" @click="openRemark(order)">📝 备注</button>
              <button
                v-if="order.invoice"
                class="oa-btn ghost"
                @click="openInvoice(order)"
              >🧾 发票</button>
              <button
                v-if="order.logistics && order.logistics.length > 0"
                class="oa-btn ghost"
                @click="openLogistics(order)"
              >🚚 物流</button>

              <!-- 待付款：取消订单 + 继续支付 -->
              <template v-if="order.status === 'pending'">
                <button class="oa-btn danger" @click="onCancelOrder(order)">取消订单</button>
                <button class="oa-btn primary" @click="onContinuePay(order)">继续支付</button>
              </template>

              <!-- 已付款：申请退款 -->
              <template v-else-if="order.status === 'paid'">
                <button class="oa-btn warn" @click="openRefund(order)">申请退款</button>
              </template>

              <!-- 已发货：申请退款 + 确认收货 -->
              <template v-else-if="order.status === 'shipped'">
                <button class="oa-btn warn" @click="openRefund(order)">申请退款</button>
                <button class="oa-btn primary" @click="onConfirmReceive(order)">确认收货</button>
              </template>

              <!-- 已完成：申请退款/再次购买 -->
              <template v-else-if="order.status === 'done'">
                <button class="oa-btn warn" @click="openRefund(order)">申请退款</button>
                <button class="oa-btn primary" @click="goHome">再次购买</button>
              </template>
            </div>
          </div>
        </div>

        <!-- ====== 订单通用弹窗：备注 / 退款 / 发票 / 物流 ====== -->
        <div v-if="orderModal.type && activeModalOrder" class="review-modal-mask" @click.self="closeModal">
          <div class="review-modal om-modal">

            <!-- 备注弹窗 -->
            <template v-if="orderModal.type === 'remark'">
              <h3 class="review-modal-title">📝 订单备注</h3>
              <p class="om-sub-title">订单号：{{ activeModalOrder.id }}</p>
              <textarea
                v-model="orderModal.remarkText"
                class="review-textarea"
                rows="4"
                maxlength="100"
                placeholder="选填，如颜色、尺码、收货时间等说明"
              ></textarea>
              <div class="review-modal-actions">
                <button class="btn-ghost" @click="closeModal">取消</button>
                <button class="btn-primary" @click="saveRemark">保存</button>
              </div>
            </template>

            <!-- 退款申请弹窗 -->
            <template v-else-if="orderModal.type === 'refund'">
              <h3 class="review-modal-title">💰 申请退款</h3>
              <p class="om-sub-title">订单号：{{ activeModalOrder.id }} · 退款金额：<b style="color:#ef4444">¥{{ activeModalOrder.totalAmount.toFixed(2) }}</b></p>
              <textarea
                v-model="orderModal.refundReason"
                class="review-textarea"
                rows="4"
                maxlength="200"
                placeholder="请填写退款原因（必填）"
              ></textarea>
              <div class="review-modal-actions">
                <button class="btn-ghost" @click="closeModal">取消</button>
                <button class="btn-primary" @click="submitRefund">提交申请</button>
              </div>
            </template>

            <!-- 发票查看弹窗 -->
            <template v-else-if="orderModal.type === 'invoice'">
              <h3 class="review-modal-title">🧾 发票信息</h3>
              <template v-if="activeModalOrder.invoice">
                <table class="om-invoice-table">
                  <tr><th>发票类型</th><td>{{ activeModalOrder.invoice.type }}</td></tr>
                  <tr><th>发票抬头</th><td>{{ activeModalOrder.invoice.title }}</td></tr>
                  <tr v-if="activeModalOrder.invoice.type === '企业' && activeModalOrder.invoice.taxNo">
                    <th>税号</th><td>{{ activeModalOrder.invoice.taxNo }}</td>
                  </tr>
                  <tr><th>开票内容</th><td>{{ activeModalOrder.invoice.content }}</td></tr>
                  <tr>
                    <th>开票状态</th>
                    <td>
                      <span v-if="activeModalOrder.invoice.issued" class="om-flag ok">已开具 · 3 个工作日内发送至您的邮箱</span>
                      <span v-else class="om-flag wait">开具中</span>
                    </td>
                  </tr>
                </table>
              </template>
              <template v-else>
                <p class="om-sub-title">该订单未申请发票</p>
              </template>
              <div class="review-modal-actions">
                <button class="btn-primary" @click="closeModal">知道了</button>
              </div>
            </template>

            <!-- 物流信息弹窗 -->
            <template v-else-if="orderModal.type === 'logistics'">
              <h3 class="review-modal-title">🚚 物流信息</h3>
              <p class="om-sub-title">
                订单号：{{ activeModalOrder.id }} ·
                承运：优选快递 &nbsp;|&nbsp;
                单号：YD{{ activeModalOrder.id.slice(-10) }}
              </p>
              <template v-if="activeModalOrder.logistics && activeModalOrder.logistics.length > 0">
                <ul class="om-logistics">
                  <li
                    v-for="(node, i) in [...activeModalOrder.logistics].reverse()"
                    :key="i"
                    class="om-log"
                    :class="{ new: node.isNew }"
                  >
                    <span class="om-log-dot"></span>
                    <div>
                      <p class="om-log-status">{{ node.status }}</p>
                      <p class="om-log-time">{{ node.time }}</p>
                    </div>
                  </li>
                </ul>
              </template>
              <template v-else>
                <p class="om-sub-title">暂无物流信息，支付完成后将自动更新</p>
              </template>
              <div class="review-modal-actions">
                <button class="btn-primary" @click="closeModal">知道了</button>
              </div>
            </template>

          </div>
        </div>
      </div>

      <!-- 关注店铺 -->
      <div v-else-if="activeTab === 'shops'" class="tab-panel">
        <!-- 已关注店铺 -->
        <div class="shops-section">
          <h3 class="shops-section-title">我关注的店铺（{{ followedShops.length }}）</h3>
          <template v-if="followedShops.length === 0">
            <div class="empty-state">🏪<p>还没有关注任何店铺</p></div>
          </template>
          <div v-else class="shop-list">
            <div v-for="shop in followedShops" :key="shop.id" class="shop-card">
              <div class="shop-logo" :style="{ background: shop.bgColor }">
                <span>{{ shop.logo }}</span>
              </div>
              <div class="shop-info">
                <div class="shop-name">{{ shop.name }}</div>
                <div class="shop-meta">
                  <span>⭐ {{ shop.rating.toFixed(1) }}</span>
                  <span>粉丝 {{ formatFollowers(shop.followers) }}</span>
                </div>
              </div>
              <button class="shop-btn followed" @click="toggleFollow(shop.id)">已关注</button>
            </div>
          </div>
        </div>

        <!-- 推荐店铺 -->
        <div class="shops-section" style="margin-top: 24px">
          <h3 class="shops-section-title">推荐店铺</h3>
          <div class="shop-list">
            <div
              v-for="shop in shops.all.filter(s => !isFollowed(s.id))"
              :key="shop.id"
              class="shop-card"
            >
              <div class="shop-logo" :style="{ background: shop.bgColor }">
                <span>{{ shop.logo }}</span>
              </div>
              <div class="shop-info">
                <div class="shop-name">{{ shop.name }}</div>
                <div class="shop-meta">
                  <span>⭐ {{ shop.rating.toFixed(1) }}</span>
                  <span>粉丝 {{ formatFollowers(shop.followers) }}</span>
                </div>
              </div>
              <button class="shop-btn" @click="toggleFollow(shop.id)">+ 关注</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 评价管理 -->
      <div v-else-if="activeTab === 'reviews'" class="tab-panel">
        <!-- 待评价 -->
        <div v-if="pendingReviews.length > 0" class="shops-section">
          <h3 class="shops-section-title">待评价商品（{{ pendingReviews.length }}）</h3>
          <div class="shop-list">
            <div v-for="item in pendingReviews" :key="item.productId + item.orderId" class="shop-card">
              <div class="shop-logo" :style="{ background: item.productBgColor }">
                <span>{{ item.productEmoji }}</span>
              </div>
              <div class="shop-info">
                <div class="shop-name">{{ item.productName }}</div>
                <div class="shop-meta">
                  <span>订单 {{ item.orderId }}</span>
                </div>
              </div>
              <button class="shop-btn" @click="openReviewForm(item)">去评价</button>
            </div>
          </div>
        </div>

        <!-- 我的评价 -->
        <div class="shops-section" :style="{ marginTop: pendingReviews.length > 0 ? '24px' : '0' }">
          <h3 class="shops-section-title">
            我的评价（{{ reviews.list.length }}）
            <button v-if="reviews.list.length === 0" class="demo-btn" @click="addDemoReview">+ 添加演示评价</button>
          </h3>
          <template v-if="reviews.list.length === 0 && pendingReviews.length === 0">
            <div class="empty-state">⭐<p>还没有任何评价</p><button @click="goHome">去购物</button></div>
          </template>
          <div v-else-if="reviews.list.length === 0 && pendingReviews.length > 0">
            <p class="reviews-tip">完成订单后可以对商品进行评价</p>
          </div>
          <div v-else class="review-list">
            <div v-for="review in reviews.list" :key="review.id" class="review-card">
              <div class="review-head">
                <div class="review-product">
                  <div class="item-img small" :style="{ background: review.productBgColor }">
                    <span>{{ review.productEmoji }}</span>
                  </div>
                  <span class="review-product-name">{{ review.productName }}</span>
                </div>
                <div class="review-rating">
                  <span v-for="n in 5" :key="n" class="star" :class="{ on: n <= review.rating }">★</span>
                </div>
              </div>
              <div class="review-content">{{ review.content }}</div>
              <div class="review-foot">
                <span class="review-time">{{ formatTime(review.createdAt) }}</span>
                <button class="item-del" @click="deleteReview(review.id)">删除评价</button>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ====== 评价弹窗 ====== -->
    <div v-if="reviewForm.show" class="review-modal-mask" @click.self="reviewForm.show = false">
      <div class="review-modal">
        <h3 class="review-modal-title">发表评价</h3>
        <div class="review-modal-product">
          <div class="item-img" :style="{ background: reviewForm.productBgColor }">
            <span>{{ reviewForm.productEmoji }}</span>
          </div>
          <span>{{ reviewForm.productName }}</span>
        </div>
        <!-- 星级评分 -->
        <div class="review-rate">
          <label>评分：</label>
          <div class="rate-stars">
            <span
              v-for="n in 5"
              :key="n"
              class="rate-star"
              :class="{ active: n <= reviewForm.rating }"
              @click="reviewForm.rating = n"
            >★</span>
          </div>
        </div>
        <!-- 评价内容 -->
        <textarea
          v-model="reviewForm.content"
          class="review-textarea"
          rows="4"
          placeholder="分享一下你的使用感受..."
          maxlength="200"
        ></textarea>
        <div class="review-modal-actions">
          <button class="btn-ghost" @click="reviewForm.show = false">取消</button>
          <button class="btn-primary" @click="submitReview">提交评价</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ====== 容器 ====== */
.profile-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

/* ====== 返回首页 ====== */
.back-home {
  margin-bottom: 16px;
  padding: 6px 14px;
  font-size: 13px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.back-home:hover {
  background-color: #e0e7ff;
}

/* ====== 用户信息卡 ====== */
.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: linear-gradient(to right, #6366f1, #7c3aed);
  border-radius: 16px;
  color: #ffffff;
  box-shadow: 0 10px 20px rgba(99, 102, 241, 0.25);
}

.profile-avatar img {
  width: 60px;
  height: 60px;
  border-radius: 9999px;
  background-color: rgba(255, 255, 255, 0.2);
  border: 3px solid rgba(255, 255, 255, 0.4);
}

.profile-info {
  flex: 1;
}

.profile-info h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.profile-info p {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.logout-btn {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.logout-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

/* ====== 标签切换 ====== */
.profile-tabs {
  display: flex;
  gap: 4px;
  margin-top: 20px;
  padding: 4px;
  background-color: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow-x: auto;
}

.profile-tab {
  position: relative;
  flex: 1;
  min-width: 100px;
  padding: 10px 8px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.profile-tab:hover {
  color: #4f46e5;
}

.profile-tab.active {
  color: #4f46e5;
  background-color: #eef2ff;
  font-weight: 600;
}

.tab-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  background-color: #ef4444;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* ====== 内容区 ====== */
.profile-content {
  margin-top: 16px;
  background-color: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.tab-panel {
  padding: 16px;
}

/* ====== 空状态 ====== */
.empty-state {
  padding: 60px 0;
  text-align: center;
  color: #9ca3af;
}

.empty-state p {
  margin: 12px 0 20px;
  font-size: 14px;
}

.empty-state button {
  padding: 8px 24px;
  font-size: 13px;
  color: #ffffff;
  background-color: #4f46e5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

/* ====== 商品行 ====== */
.item-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #fafafa;
  border-radius: 10px;
}

.item-img {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.item-img.small {
  width: 44px;
  height: 44px;
  font-size: 22px;
}

.item-detail {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-price {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: #ef4444;
}

.item-time {
  margin-top: 2px;
  font-size: 11px;
  color: #9ca3af;
}

/* 数量控制 */
.item-qty {
  display: flex;
  align-items: center;
  gap: 4px;
}

.item-qty button {
  width: 28px;
  height: 28px;
  font-size: 16px;
  color: #4b5563;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.item-qty button:hover {
  color: #4f46e5;
  border-color: #c7d2fe;
}

.item-qty span {
  min-width: 28px;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.item-del {
  padding: 4px 10px;
  font-size: 12px;
  color: #ef4444;
  background: none;
  border: 1px solid #fecaca;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.item-del:hover {
  background-color: #fef2f2;
}

/* ====== 购物车底部 ====== */
.cart-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.cart-total {
  font-size: 13px;
  color: #6b7280;
}

.cart-total em {
  font-style: normal;
  font-size: 20px;
  font-weight: 700;
  color: #ef4444;
  margin-left: 4px;
}

.cart-actions {
  display: flex;
  gap: 8px;
}

.btn-ghost {
  padding: 8px 16px;
  font-size: 13px;
  color: #6b7280;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-ghost:hover {
  color: #4f46e5;
  border-color: #c7d2fe;
}

.btn-primary {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  background-color: #4f46e5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-primary:hover {
  background-color: #4338ca;
}

/* ====== 订单卡片 ====== */
.order-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-card {
  padding: 14px;
  background-color: #fafafa;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
}

.order-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px dashed #e5e7eb;
}

.order-id {
  font-size: 12px;
  color: #6b7280;
}

.order-status {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 9999px;
}

.st-pending { background-color: #fef3c7; color: #92400e; }
.st-paid { background-color: #dbeafe; color: #1e40af; }
.st-shipped { background-color: #e0e7ff; color: #3730a3; }
.st-done { background-color: #d1fae5; color: #065f46; }
.st-cancelled { background-color: #f3f4f6; color: #6b7280; }

.order-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.order-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}

.order-time {
  font-size: 11px;
  color: #9ca3af;
}

.order-total {
  font-size: 13px;
  color: #6b7280;
}

.order-total em {
  font-style: normal;
  font-size: 16px;
  font-weight: 700;
  color: #ef4444;
  margin-left: 4px;
}

/* 订单中"评价"按钮 */
.item-review-btn {
  padding: 4px 12px;
  font-size: 12px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.item-review-btn:hover {
  background-color: #4f46e5;
  color: #ffffff;
}

/* ====== 关注店铺 ====== */
.shops-section-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 12px;
}

.demo-btn {
  padding: 2px 10px;
  font-size: 11px;
  font-weight: 500;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}

.demo-btn:hover {
  background-color: #4f46e5;
  color: #ffffff;
}

.shop-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.shop-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #fafafa;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
}

.shop-logo {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.shop-info {
  flex: 1;
  min-width: 0;
}

.shop-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shop-meta {
  margin-top: 4px;
  font-size: 11px;
  color: #9ca3af;
  display: flex;
  gap: 12px;
}

.shop-btn {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.shop-btn:hover {
  background-color: #4f46e5;
  color: #ffffff;
}

.shop-btn.followed {
  color: #6b7280;
  background-color: #f3f4f6;
}

.shop-btn.followed:hover {
  background-color: #ef4444;
  color: #ffffff;
}

/* ====== 评价管理 ====== */
.reviews-tip {
  margin: 0;
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: #9ca3af;
  background-color: #fafafa;
  border-radius: 10px;
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-card {
  padding: 14px;
  background-color: #fafafa;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
}

.review-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.review-product {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
}

.review-product-name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.review-rating .star {
  color: #e5e7eb;
  font-size: 16px;
}

.review-rating .star.on {
  color: #f59e0b;
}

.review-content {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}

.review-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.review-time {
  font-size: 11px;
  color: #9ca3af;
}

/* ====== 评价弹窗 ====== */
.review-modal-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.review-modal {
  width: 90%;
  max-width: 440px;
  padding: 24px;
  background-color: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.review-modal-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.review-modal-product {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 16px;
  background-color: #fafafa;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
}

.review-rate {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.review-rate label {
  font-size: 13px;
  color: #6b7280;
}

.rate-stars {
  display: flex;
  gap: 4px;
}

.rate-star {
  font-size: 24px;
  color: #e5e7eb;
  cursor: pointer;
  transition: color 0.15s ease;
}

.rate-star:hover {
  color: #f59e0b;
}

.rate-star.active {
  color: #f59e0b;
}

.review-textarea {
  width: 100%;
  padding: 10px 12px;
  font-size: 13px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  outline: none;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color 0.15s ease;
  font-family: inherit;
}

.review-textarea:focus {
  border-color: #818cf8;
}

.review-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

/* ====== 优惠券子标签 ====== */
.coupon-sub-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  padding: 4px;
  background-color: #f9fafb;
  border-radius: 8px;
  width: fit-content;
}
.coupon-sub-tab {
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.coupon-sub-tab:hover { color: #4f46e5; }
.coupon-sub-tab.active {
  color: #4f46e5;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* ====== 优惠券卡片 ====== */
.coupon-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.coupon-card {
  display: flex;
  align-items: stretch;
  background-color: #ffffff;
  border: 1px solid #fde68a;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
  position: relative;
}
.coupon-card:hover {
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.12);
  transform: translateY(-1px);
}
.coupon-card.used,
.coupon-card.expired {
  border-color: #e5e7eb;
  opacity: 0.65;
}
.coupon-card.used:hover,
.coupon-card.expired:hover {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transform: none;
}

/* 左侧：券面（红色渐变） */
.coupon-face {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 110px;
  flex-shrink: 0;
  color: #ffffff;
  background: linear-gradient(135deg, #ff512f 0%, #f09819 100%);
  position: relative;
}
.coupon-card.used .coupon-face,
.coupon-card.expired .coupon-face {
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
}
.coupon-face::before,
.coupon-face::after {
  content: '';
  position: absolute;
  right: -6px;
  width: 12px;
  height: 12px;
  background-color: #ffffff;
  border-radius: 9999px;
}
.coupon-face::before { top: 20%; }
.coupon-face::after { bottom: 20%; }

.coupon-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}
.coupon-threshold {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.9;
}

/* 中间：信息区 */
.coupon-body {
  flex: 1;
  min-width: 0;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.coupon-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}
.coupon-desc {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}
.coupon-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  font-size: 11px;
}
.coupon-scope {
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 500;
}
.coupon-period {
  color: #9ca3af;
}
.coupon-warn {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 500;
  color: #ef4444;
}

/* 右侧：按钮/状态 */
.coupon-action {
  align-self: center;
  margin-right: 16px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  background: linear-gradient(135deg, #ff512f 0%, #f09819 100%);
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.coupon-action:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}
.coupon-action-del {
  align-self: center;
  margin-right: 16px;
  padding: 6px 14px;
  font-size: 12px;
  color: #9ca3af;
  background-color: #f3f4f6;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.coupon-action-del:hover {
  color: #ef4444;
  background-color: #fee2e2;
}
.coupon-status {
  align-self: center;
  margin-right: 16px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 9999px;
  flex-shrink: 0;
}
.used-tag {
  color: #9ca3af;
  background-color: #f3f4f6;
}

/* ========== 订单 Tab 新增：搜索 & 状态子标签 ========== */
.order-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.order-search {
  flex: 1;
  max-width: 320px;
  padding: 8px 14px;
  font-size: 13px;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  outline: none;
  transition: border-color 0.15s ease;
}
.order-search:focus { border-color: #818cf8; }
.order-search-btn {
  width: 34px;
  height: 34px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 9999px;
  cursor: pointer;
}
.order-search-btn:hover { border-color: #c7d2fe; }

.order-sub-tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 16px;
  background: #f9fafb;
  border-radius: 10px;
  overflow-x: auto;
}
.order-sub-tab {
  position: relative;
  padding: 6px 14px;
  font-size: 12px;
  color: #6b7280;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.order-sub-tab:hover { color: #4f46e5; }
.order-sub-tab.active {
  color: #4f46e5;
  background: #fff;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.ost-badge {
  display: inline-block;
  min-width: 16px;
  padding: 0 5px;
  margin-left: 4px;
  font-size: 10px;
  line-height: 14px;
  color: #fff;
  background: #ef4444;
  border-radius: 9999px;
  text-align: center;
}

/* ========== 订单状态：新增退款中 / 已退款 ========== */
.st-refunding  { background-color: #ffedd5; color: #c2410c; }
.st-refunded   { background-color: #ede9fe; color: #6d28d9; }

/* ========== 订单时间线（下单/付款/发货/完成） ========== */
.order-timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border-radius: 10px;
}
.ot-node {
  flex: 1 1 120px;
  min-width: 120px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  position: relative;
  opacity: 0.5;
}
.ot-node.done { opacity: 1; }
.ot-dot {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: #c7d2fe;
  margin-top: 6px;
  flex-shrink: 0;
}
.ot-node.done .ot-dot { background: #4f46e5; box-shadow: 0 0 0 3px #c7d2fe; }
.ot-title { margin: 0; font-size: 12px; color: #4b5563; font-weight: 600; }
.ot-time  { margin: 2px 0 0; font-size: 11px; color: #9ca3af; }
.ot-node.done .ot-time { color: #374151; }

/* ========== 订单备注 / 退款状态条 ========== */
.order-remark {
  margin-top: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px dashed #fde68a;
  border-radius: 6px;
}
.order-refund {
  margin-top: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: #6d28d9;
  background: #f5f3ff;
  border: 1px dashed #c4b5fd;
  border-radius: 6px;
}

/* ========== 订单操作按钮 ========== */
.order-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #f3f4f6;
}
.oa-btn {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}
.oa-btn.ghost   { color: #4b5563; background: #f3f4f6; }
.oa-btn.ghost:hover { background: #e5e7eb; }
.oa-btn.primary { color: #fff; background: #4f46e5; font-weight: 500; }
.oa-btn.primary:hover { background: #4338ca; }
.oa-btn.danger  { color: #fff; background: #ef4444; font-weight: 500; }
.oa-btn.danger:hover { background: #dc2626; }
.oa-btn.warn    { color: #fff; background: #f59e0b; font-weight: 500; }
.oa-btn.warn:hover   { background: #d97706; }

/* ========== 订单卡片里的商品点击跳转 ========== */
.order-item-img:hover,
.order-item-name:hover { color: #4f46e5 !important; }
.order-item-name { cursor: pointer; }

/* ========== 订单通用弹窗（备注/退款/发票/物流） ========== */
.om-modal { max-width: 480px; }
.om-sub-title {
  margin: 0 0 14px;
  font-size: 13px;
  color: #6b7280;
  word-break: break-all;
}
.om-invoice-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.om-invoice-table th,
.om-invoice-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #f3f4f6;
}
.om-invoice-table th {
  width: 90px;
  color: #6b7280;
  background: #f9fafb;
  font-weight: 400;
}
.om-invoice-table td { color: #1f2937; word-break: break-all; }
.om-flag {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  border-radius: 9999px;
  font-weight: 500;
}
.om-flag.ok   { background: #d1fae5; color: #065f46; }
.om-flag.wait { background: #fef3c7; color: #92400e; }

/* 物流节点列表 */
.om-logistics {
  list-style: none;
  padding: 0 0 0 6px;
  margin: 0;
}
.om-log {
  position: relative;
  padding: 0 0 14px 20px;
  border-left: 2px solid #e5e7eb;
  color: #6b7280;
}
.om-log:last-child { padding-bottom: 0; border-left-color: transparent; }
.om-log-dot {
  position: absolute;
  left: -7px;
  top: 2px;
  width: 12px;
  height: 12px;
  background: #e5e7eb;
  border-radius: 9999px;
}
.om-log.new { color: #1f2937; font-weight: 500; }
.om-log.new .om-log-dot { background: #4f46e5; box-shadow: 0 0 0 3px #c7d2fe; }
.om-log-status { margin: 0; font-size: 13px; line-height: 1.4; }
.om-log-time   { margin: 2px 0 0; font-size: 11px; color: #9ca3af; }

/* ========== 浏览历史点击跳转样式 ========== */
.history-row {
  cursor: pointer;
  transition: all 0.15s ease;
}
.history-row:hover {
  background: #eef2ff;
  transform: translateY(-1px);
}
.history-img { transition: transform 0.15s ease; }
.history-row:hover .history-img { transform: scale(1.05); }
.history-name:hover { color: #4f46e5; }
.history-go {
  font-size: 12px;
  color: #4f46e5;
  flex-shrink: 0;
  padding: 4px 10px;
  background: #eef2ff;
  border-radius: 9999px;
}
.history-row:hover .history-go { background: #4f46e5; color: #fff; }

/* =============================================================
 * 地址管理：头部 / 列表 / 卡片 / 弹窗表单 / 共用按钮样式
 * ============================================================= */
.addr-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.addr-title { margin: 0; font-size: 18px; font-weight: 700; color: #1f2937; }
.addr-sub   { margin: 6px 0 0; font-size: 13px; color: #6b7280; }
.addr-add-btn { border-radius: 10px; padding: 8px 18px; font-size: 13px; }

.addr-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.addr-card {
  position: relative;
  padding: 14px 16px 16px;
  background: #fff;
  border: 1.5px solid #f3f4f6;
  border-radius: 12px;
  transition: all 0.15s ease;
}
.addr-card:hover { border-color: #c7d2fe; box-shadow: 0 4px 14px rgba(79,70,229,0.08); }
.addr-card.default {
  border-color: #4f46e5;
  background: linear-gradient(180deg, #fafbff, #ffffff 60%);
}

.addr-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}
.addr-card-head-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}
.addr-default-tag {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border-radius: 9999px;
  flex-shrink: 0;
}
.addr-name  { font-size: 15px; font-weight: 700; color: #1f2937; }
.addr-phone { font-size: 12px; color: #6b7280; }

.addr-card-head-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  justify-content: flex-end;
}
.addr-link {
  font-size: 12px;
  color: #4f46e5;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 0;
  transition: opacity 0.15s ease;
}
.addr-link:hover { text-decoration: underline; }
.addr-link.danger { color: #ef4444; }
.addr-link.off { color: #9ca3af; cursor: not-allowed; opacity: 0.6; }
.addr-link.off:hover { text-decoration: none; }

.addr-text {
  margin: 0;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.55;
}
.addr-region {
  display: inline-block;
  margin-right: 6px;
  margin-bottom: 2px;
  padding: 1px 8px;
  font-size: 12px;
  color: #3730a3;
  background: #e0e7ff;
  border-radius: 4px;
}
.addr-detail { display: inline; }

/* ====== 地址弹窗表单 ====== */
.addr-modal { max-width: 480px; }
.addr-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 4px;
}
.addr-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.addr-label {
  font-size: 12px;
  color: #374151;
  font-weight: 500;
}
.addr-label i {
  color: #ef4444;
  font-style: normal;
  margin-right: 2px;
}
.addr-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  font-size: 13px;
  color: #1f2937;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.15s ease;
  font-family: inherit;
  resize: vertical;
}
.addr-input:focus { border-color: #818cf8; }
.addr-textarea { min-height: 72px; line-height: 1.5; }

.addr-default-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
  user-select: none;
}
.addr-check {
  width: 16px; height: 16px;
  accent-color: #4f46e5;
  cursor: pointer;
}
.addr-error {
  margin: 2px 0 0;
  padding: 8px 12px;
  font-size: 12px;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  line-height: 1.5;
}
</style>
