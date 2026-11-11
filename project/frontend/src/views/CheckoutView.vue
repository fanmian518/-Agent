<script setup lang="ts">
/**
 * CheckoutView.vue - 付款跳转界面
 * ----------------------------------------------------------------
 * 路由：/checkout?orderId=xxx
 * 入口：购物车页面"去结算" → createOrder 后携带订单号跳转到此
 * 功能：
 *   - 展示订单号 / 下单时间 / 15 分钟支付倒计时
 *   - 展示收货地址（Mock）、商品清单、费用明细
 *   - 选择支付方式（微信 / 支付宝 / 银行卡）
 *   - 点击"立即支付"→ 将订单状态改为 paid → 跳转用户中心订单
 */
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrders, updateOrderStatus } from '@/stores/orders'
import type { Order } from '@/stores/orders'
import { isLoggedIn, currentUsername } from '@/stores/user'
import { defaultAddress, useAddresses, addAddress, refreshAddresses } from '@/stores/addresses'
import type { Address } from '@/stores/addresses'
import { apiGetOrderDetail } from '@/api/order'

const route = useRoute()
const router = useRouter()
const orders = useOrders()
const addresses = useAddresses()  // 保持响应式依赖，地址变更时列表实时更新

// ====== 订单信息（从路由 query + orders store 取） ======
const order = ref<Order | null>(null)
const notFound = ref(false)

const mapRemoteOrder = (row: any): Order => {
  const rawCreatedAt = row.created_at ?? row.createdAt
  const createdAt = typeof rawCreatedAt === 'number' ? rawCreatedAt : (Date.parse(String(rawCreatedAt)) || Date.now())
  const rawStatus = row.status === 'pending_payment' ? 'pending' : row.status
  const status: Order['status'] = ['pending', 'paid', 'shipped', 'done', 'cancelled', 'refunding', 'refunded'].includes(rawStatus)
    ? rawStatus as Order['status']
    : 'pending'
  return {
    id: String(row.order_id ?? row.id),
    addressId: row.address_id ?? row.addressId,
    items: (row.items ?? []).map((item: any) => ({
      id: Number(item.product_id ?? item.id),
      name: item.name ?? item.product_name ?? `商品 ${item.product_id ?? item.id}`,
      price: Number(item.price ?? item.unit_price ?? 0),
      emoji: item.emoji ?? '🛍️',
      quantity: Number(item.quantity ?? 1)
    })),
    totalAmount: Number(row.payable_amount ?? row.total_amount ?? row.totalAmount ?? 0),
    status,
    createdAt,
    paidAt: row.paid_at ? Date.parse(row.paid_at) : undefined,
    payMethod: row.payment_method ?? row.payMethod,
    remark: row.remark
  }
}

const loadOrder = async () => {
  const orderId = route.query.orderId as string | undefined
  if (!orderId) {
    notFound.value = true
    return
  }
  const found = orders.list.find(o => o.id === orderId)
  if (found) {
    order.value = found
    if (found.addressId != null) selectedAddressId.value = String(found.addressId)
    notFound.value = false
    return
  }

  // Store 刷新存在竞态或订单刚创建尚未写入列表时，直接按订单号读取后端详情。
  try {
    const remote = await apiGetOrderDetail(orderId)
    const loaded = mapRemoteOrder(remote)
    orders.list.unshift(loaded)
    order.value = loaded
    if (loaded.addressId != null) selectedAddressId.value = String(loaded.addressId)
    notFound.value = false
  } catch {
    notFound.value = true
  }
}

onMounted(async () => {
  await refreshAddresses().catch(() => undefined)
  await loadOrder()
})
// 同一组件内路由参数变化（虽然少见，但保持健壮）
watch(() => route.query.orderId, loadOrder)

// ====== 15 分钟支付倒计时 ======
const EXPIRE_SECONDS = 15 * 60 // 15 分钟
const remainSeconds = ref(EXPIRE_SECONDS)
let timer: number | null = null

const startTimer = () => {
  stopTimer()
  // 如果订单已创建过了很久，按实际剩余时间算，不足 0 直接置 0
  if (order.value) {
    const elapsed = Math.floor((Date.now() - order.value.createdAt) / 1000)
    remainSeconds.value = Math.max(0, EXPIRE_SECONDS - elapsed)
  }
  timer = window.setInterval(() => {
    if (remainSeconds.value > 0) remainSeconds.value--
  }, 1000)
}
const stopTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}
// 订单加载完毕（或切换）后重置倒计时
watch(order, (o) => {
  if (o) startTimer()
  else stopTimer()
}, { immediate: true })
onUnmounted(stopTimer)

// 倒计时文案：mm:ss
const remainText = computed(() => {
  const m = Math.floor(remainSeconds.value / 60)
  const s = remainSeconds.value % 60
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${pad(m)}:${pad(s)}`
})
const isExpired = computed(() => remainSeconds.value === 0)

// ===========================================================================
// 收货地址：
//   - 不跳用户中心；改为在本页弹出「下拉选择 + 新建」双模式弹窗
//   - 选择完全是当前订单级别的（selectedAddressId），不修改用户的「默认地址」标记
//   - 新建的地址会写回地址管理（持久化），但 isDefault = false，保证默认地址不变
// ===========================================================================
const maskPhone = (p: string) =>
  p.length === 11 ? p.slice(0, 3) + '****' + p.slice(7) : p

// 当前选中的地址 id（页面级状态，不写入 store，不影响全局默认地址）
const selectedAddressId = ref<string | null>(defaultAddress.value?.id ?? null)

// 当地址列表发生变化（比如新增）时，如果用户还没选过，自动选默认地址
watch(
  () => addresses.list.length,
  () => {
    if (selectedAddressId.value) return
    if (defaultAddress.value) selectedAddressId.value = defaultAddress.value.id
  },
  { immediate: false }
)
// 如果 defaultAddress 在加载过程中出现了（如登录刚完成、账号切换）且用户没选，自动选
watch(defaultAddress, (d) => {
  if (!selectedAddressId.value && d) selectedAddressId.value = d.id
})

// 选中的完整地址对象
const selectedAddress = computed<Address | null>(() => {
  if (!selectedAddressId.value) return null
  return addresses.list.find(a => a.id === selectedAddressId.value) ?? null
})

// 页面展示的地址对象（包装成模板直接用的结构）
const shippingAddress = computed(() => {
  const a = selectedAddress.value
  if (!a) return null
  return {
    id: a.id,
    name: a.name,
    phone: maskPhone(a.phone),
    region: a.region,
    detail: a.detail,
    full: `${a.region} ${a.detail}`,
    isDefault: a.isDefault
  }
})

// ---------- 地址选择 + 新建弹窗 ----------
type AddrDialogMode = 'select' | 'new'
const addrDialog = reactive<{
  show: boolean
  mode: AddrDialogMode
  error: string
}>({ show: false, mode: 'select', error: '' })

// 新建地址表单（isDefault 永远为 false，用户在本页面的选择不会改变全局默认）
const newAddrForm = reactive<{
  name: string; phone: string; region: string; detail: string
}>({ name: '', phone: '', region: '', detail: '' })

/** 打开弹窗并重置到「选择地址」模式 */
const openAddrDialog = () => {
  addrDialog.show = true
  addrDialog.mode = addresses.list.length === 0 ? 'new' : 'select'
  addrDialog.error = ''
}
const closeAddrDialog = () => {
  addrDialog.show = false
  addrDialog.error = ''
}
/** 切到新建模式 */
const switchToNew = () => {
  addrDialog.mode = 'new'
  addrDialog.error = ''
  newAddrForm.name = ''
  newAddrForm.phone = ''
  newAddrForm.region = ''
  newAddrForm.detail = ''
}
/** 从新建模式退回到选择模式（有可选地址时） */
const switchBackToSelect = () => {
  addrDialog.mode = 'select'
  addrDialog.error = ''
}

/** 用户在选择弹窗里点击一个选项 -> 立即应用并关闭弹窗 */
const pickAddress = (id: string) => {
  selectedAddressId.value = id
  closeAddrDialog()
}

/** 新建地址提交：写回 store（isDefault=false），然后自动选中，弹窗关闭 */
const submitNewAddress = () => {
  addrDialog.error = ''
  // 关键：强制 isDefault = false，保证用户中心默认地址不变
  const r = addAddress({
    name: newAddrForm.name,
    phone: newAddrForm.phone,
    region: newAddrForm.region,
    detail: newAddrForm.detail,
    isDefault: false
  })
  if (!r.ok) { addrDialog.error = r.msg; return }
  // 找到刚插入的地址 id，设为当前选中并自动选中
  const justAdded = addresses.list[0]   // 列表是 unshift 插入，最新的在最前面
  if (justAdded) {
    selectedAddressId.value = justAdded.id
  }
  closeAddrDialog()
}

// ====== 支付方式 ======
type PayMethod = 'wechat' | 'alipay' | 'card'
interface PayOption {
  key: PayMethod
  label: string
  desc: string
  icon: string
  color: string
}
const PAY_OPTIONS: PayOption[] = [
  { key: 'wechat', label: '微信支付', desc: '推荐使用，支付后即时到账', icon: '💚', color: '#07c160' },
  { key: 'alipay', label: '支付宝',  desc: '支持花呗、信用卡分期',   icon: '💙', color: '#1677ff' },
  { key: 'card',   label: '银行卡',  desc: '储蓄卡 / 信用卡 快捷支付', icon: '💳', color: '#6b7280' }
]
const payMethod = ref<PayMethod>('wechat')

// ====== 费用汇总 ======
const totalAmount = computed(() => order.value?.totalAmount ?? 0)
const shippingFee = computed(() => (totalAmount.value >= 99 || totalAmount.value === 0 ? 0 : 8))
const discount    = computed(() => 0) // 预留：优惠券抵扣
const payTotal    = computed(() => Math.max(0, totalAmount.value + shippingFee.value - discount.value))

// 订单商品数量合计
const totalQty = computed(() =>
  order.value ? order.value.items.reduce((s, i) => s + i.quantity, 0) : 0
)

// ====== 格式化时间 ======
const formatTime = (ts: number) => {
  const d = new Date(ts)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// ====== 立即支付 ======
const paying = ref(false)
const handlePay = async () => {
  if (!order.value) return
  if (!shippingAddress.value) {
    alert('请先添加或选择收货地址，再进行支付')
    openAddrDialog()   // 打开弹窗（空列表直接进入新建模式）
    return
  }
  if (order.value.status === 'paid') {
    alert('该订单已支付，请勿重复支付')
    router.push('/profile')
    return
  }
  if (isExpired.value) {
    alert('支付超时，订单已取消，请重新下单')
    updateOrderStatus(order.value.id, 'cancelled')
    router.push('/cart')
    return
  }
  paying.value = true
  // 模拟调用支付网关（0.8s 延时）
  await new Promise(r => setTimeout(r, 800))
  updateOrderStatus(order.value.id, 'paid')
  paying.value = false
  const methodName = PAY_OPTIONS.find(p => p.key === payMethod.value)?.label ?? ''
  alert(`✅ 支付成功\n\n订单号：${order.value.id}\n支付方式：${methodName}\n支付金额：¥${payTotal.value.toFixed(2)}\n\n即将跳转用户中心查看订单`)
  router.push('/profile')
}

// ====== 其他跳转 ======
const goCart = () => router.push('/cart')
const goHome = () => router.push('/')
</script>

<template>
  <div class="ck-page">
    <!-- ====== 订单不存在 / 未登录 兜底 ====== -->
    <template v-if="notFound || !order">
      <div class="ck-empty">
        <span class="ck-empty-icon">📋</span>
        <p class="ck-empty-title">{{ notFound ? '订单不存在或已过期' : '请选择商品后再结算' }}</p>
        <p class="ck-empty-desc">可以先去购物车挑选喜欢的商品</p>
        <div class="ck-empty-btns">
          <button class="btn-ghost"  @click="goHome">返回首页</button>
          <button class="btn-primary" @click="goCart">去购物车</button>
        </div>
      </div>
    </template>

    <!-- ====== 未登录兜底 ====== -->
    <template v-else-if="!isLoggedIn">
      <div class="ck-empty">
        <span class="ck-empty-icon">🔒</span>
        <p class="ck-empty-title">请先登录后再进行支付</p>
        <p class="ck-empty-desc">登录后可享受订单记录、售后保障等服务</p>
        <div class="ck-empty-btns">
          <button class="btn-primary" @click="router.push('/login')">去登录</button>
        </div>
      </div>
    </template>

    <!-- ====== 付款主内容 ====== -->
    <template v-else>
      <!-- 顶部：返回按钮 + 标题 -->
      <div class="ck-head">
        <button class="ck-back" @click="goCart">← 返回购物车</button>
        <h1 class="ck-title">收银台</h1>
        <span class="ck-order-tip">订单提交成功，请尽快完成支付</span>
      </div>

      <div class="ck-layout">
        <!-- ====== 左侧：订单主体 ====== -->
        <section class="ck-main">
          <!-- 订单信息条 -->
          <div class="ck-order-bar">
            <div>
              <span class="ck-order-label">订单号</span>
              <span class="ck-order-id">{{ order.id }}</span>
            </div>
            <div>
              <span class="ck-order-label">下单时间</span>
              <span>{{ formatTime(order.createdAt) }}</span>
            </div>
            <div class="ck-timer" :class="{ danger: isExpired }">
              <span class="ck-timer-icon">⏰</span>
              <span v-if="!isExpired">支付剩余时间 <b>{{ remainText }}</b></span>
              <span v-else>订单已超时，请重新下单</span>
            </div>
          </div>

          <!-- 收货地址：不跳用户中心；点击"修改"弹窗在页面内选择/新建 -->
          <div
            class="ck-card ck-address-card"
            :class="{
              'ck-card-empty': !shippingAddress,
              'picked': !!shippingAddress
            }"
            @click="openAddrDialog"
            title="点击选择或新建收货地址"
          >
            <div class="ck-card-title clickable">
              <span>📍 收货地址</span>
              <button
                v-if="shippingAddress"
                class="ck-link"
                @click.stop="openAddrDialog"
              >修改 ▾</button>
            </div>

            <template v-if="shippingAddress">
              <div class="ck-address">
                <span class="ck-address-name">
                  {{ shippingAddress.name }}
                  <span v-if="shippingAddress.isDefault" class="ck-address-default">默认</span>
                </span>
                <span class="ck-address-phone">{{ shippingAddress.phone }}</span>
                <p class="ck-address-detail">{{ shippingAddress.full }}</p>
              </div>
            </template>

            <template v-else>
              <div class="ck-no-address">
                <span class="ck-no-address-icon">📭</span>
                <p class="ck-no-address-tip">请选择一个收货地址，或新建一个地址</p>
                <button
                  class="btn-primary"
                  @click.stop="openAddrDialog"
                >+ 选择 / 新建收货地址</button>
              </div>
            </template>
          </div>

          <!-- ========== 地址选择 + 新建弹窗（遮罩） ========== -->
          <div v-if="addrDialog.show" class="ck-addr-mask" @click.self="closeAddrDialog">
            <div class="ck-addr-dialog">

              <!-- ===== 模式一：下拉式选择已有地址 ===== -->
              <template v-if="addrDialog.mode === 'select'">
                <div class="ck-addr-dialog-head">
                  <h3>📍 选择收货地址</h3>
                  <button class="ck-addr-dialog-close" @click="closeAddrDialog">×</button>
                </div>

                <div class="ck-addr-options">
                  <!-- 地址选项卡（每个像 radio 卡片） -->
                  <label
                    v-for="addr in addresses.list"
                    :key="addr.id"
                    class="ck-addr-opt"
                    :class="{ active: selectedAddressId === addr.id }"
                    @click="pickAddress(addr.id)"
                  >
                    <input
                      type="radio"
                      class="ck-addr-radio"
                      :checked="selectedAddressId === addr.id"
                      @click.prevent="pickAddress(addr.id)"
                    />
                    <span
                      v-if="addr.isDefault"
                      class="ck-addr-default-flag"
                    >默认</span>
                    <div class="ck-addr-opt-body">
                      <p class="ck-addr-opt-name">
                        {{ addr.name }}
                        <span class="ck-addr-opt-phone">{{ maskPhone(addr.phone) }}</span>
                      </p>
                      <p class="ck-addr-opt-detail">
                        <span class="ck-addr-opt-region">{{ addr.region }}</span>
                        {{ addr.detail }}
                      </p>
                    </div>
                    <span class="ck-addr-opt-check" v-if="selectedAddressId === addr.id">✓</span>
                  </label>

                  <!-- 尾部「+ 新建地址」选项 -->
                  <button
                    class="ck-addr-opt ck-addr-opt-new"
                    @click="switchToNew"
                  >
                    <span class="ck-addr-plus">＋</span>
                    <div class="ck-addr-opt-body">
                      <p class="ck-addr-opt-name">新建收货地址</p>
                      <p class="ck-addr-opt-detail">
                        如果上面没有您需要的地址，点这里快速新建，<br />
                        新建完成后自动选中当前订单使用。
                      </p>
                    </div>
                  </button>
                </div>
              </template>

              <!-- ===== 模式二：新建地址表单 ===== -->
              <template v-else-if="addrDialog.mode === 'new'">
                <div class="ck-addr-dialog-head">
                  <h3>➕ 新建收货地址</h3>
                  <button class="ck-addr-dialog-close" @click="closeAddrDialog">×</button>
                </div>

                <div v-if="addresses.list.length > 0" style="margin-bottom:10px">
                  <button
                    class="ck-addr-back"
                    @click="switchBackToSelect"
                  >‹ 返回选择已有地址</button>
                </div>

                <div class="ck-addr-fields">
                  <label class="ck-addr-field">
                    <span class="ck-addr-label"><i>*</i> 收货人</span>
                    <input
                      v-model="newAddrForm.name"
                      type="text"
                      maxlength="20"
                      class="ck-addr-input"
                      placeholder="请输入收货人姓名"
                    />
                  </label>

                  <label class="ck-addr-field">
                    <span class="ck-addr-label"><i>*</i> 手机号码</span>
                    <input
                      v-model="newAddrForm.phone"
                      type="tel"
                      maxlength="11"
                      class="ck-addr-input"
                      placeholder="请输入 11 位手机号"
                    />
                  </label>

                  <label class="ck-addr-field">
                    <span class="ck-addr-label"><i>*</i> 所在地区</span>
                    <input
                      v-model="newAddrForm.region"
                      type="text"
                      class="ck-addr-input"
                      placeholder="如：山东省 济南市 历下区"
                    />
                  </label>

                  <label class="ck-addr-field">
                    <span class="ck-addr-label"><i>*</i> 详细地址</span>
                    <textarea
                      v-model="newAddrForm.detail"
                      rows="3"
                      maxlength="120"
                      class="ck-addr-input ck-addr-textarea"
                      placeholder="街道、楼牌号、门牌号等（最多 120 字）"
                    ></textarea>
                  </label>

                  <p class="ck-addr-hint">
                    💡 新建后将加入您的「地址管理」中；为了不影响您平时的默认地址偏好，
                    本次新建的地址将<b>不会</b>改变"默认地址"标记。
                  </p>

                  <p v-if="addrDialog.error" class="ck-addr-error">⚠️ {{ addrDialog.error }}</p>
                </div>

                <div class="ck-addr-dialog-actions">
                  <button
                    class="btn-ghost"
                    v-if="addresses.list.length > 0"
                    @click="switchBackToSelect"
                  >返回选择</button>
                  <button class="btn-primary" @click="submitNewAddress">
                    保存并使用该地址
                  </button>
                </div>
              </template>

            </div>
          </div>

          <!-- 商品清单 -->
          <div class="ck-card">
            <div class="ck-card-title">
              <span>🛒 商品清单（共 {{ totalQty }} 件）</span>
            </div>
            <div class="ck-items">
              <div v-for="item in order.items" :key="item.id" class="ck-item">
                <div class="ck-item-img">
                  <span>{{ item.emoji }}</span>
                </div>
                <div class="ck-item-info">
                  <p class="ck-item-name">{{ item.name }}</p>
                  <p class="ck-item-qty">×{{ item.quantity }}</p>
                </div>
                <div class="ck-item-price">¥{{ (item.price * item.quantity).toFixed(2) }}</div>
              </div>
            </div>
          </div>

          <!-- 支付方式 -->
          <div class="ck-card">
            <div class="ck-card-title">
              <span>💰 选择支付方式</span>
            </div>
            <div class="ck-pay-list">
              <label
                v-for="opt in PAY_OPTIONS"
                :key="opt.key"
                class="ck-pay-item"
                :class="{ active: payMethod === opt.key }"
              >
                <input
                  type="radio"
                  name="pay-method"
                  :value="opt.key"
                  v-model="payMethod"
                  class="ck-pay-radio"
                />
                <span class="ck-pay-icon" :style="{ background: opt.color + '20', color: opt.color }">
                  {{ opt.icon }}
                </span>
                <div class="ck-pay-info">
                  <p class="ck-pay-name">{{ opt.label }}</p>
                  <p class="ck-pay-desc">{{ opt.desc }}</p>
                </div>
                <span class="ck-pay-check" v-if="payMethod === opt.key">✓</span>
              </label>
            </div>
          </div>
        </section>

        <!-- ====== 右侧：费用明细 + 支付按钮 ====== -->
        <aside class="ck-side">
          <div class="ck-summary">
            <h2 class="ck-summary-title">费用明细</h2>

            <div class="ck-row">
              <span>商品总额</span>
              <span>¥{{ totalAmount.toFixed(2) }}</span>
            </div>
            <div class="ck-row">
              <span>运费</span>
              <span>{{ shippingFee === 0 ? '免邮' : '¥' + shippingFee.toFixed(2) }}</span>
            </div>
            <div class="ck-row" v-if="discount > 0">
              <span>优惠券抵扣</span>
              <span class="ck-discount">-¥{{ discount.toFixed(2) }}</span>
            </div>

            <div class="ck-divider"></div>

            <div class="ck-row ck-row-total">
              <span>实付金额</span>
              <span class="ck-total">¥{{ payTotal.toFixed(2) }}</span>
            </div>

            <button
              class="ck-pay-btn"
              :class="{ disabled: paying || isExpired }"
              :disabled="paying || isExpired"
              @click="handlePay"
            >
              <span v-if="paying">支付中…</span>
              <span v-else-if="isExpired">订单已超时</span>
              <span v-else>立即支付 ¥{{ payTotal.toFixed(2) }}</span>
            </button>

            <p class="ck-tip-row">
              <span>🔒</span> 交易资金由平台担保，收货后 7 天内无理由退款
            </p>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ========== 页面容器 ========== */
.ck-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}

/* ========== 通用按钮 ========== */
.btn-primary {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
  background-color: #4f46e5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-primary:hover { background-color: #4338ca; }

.btn-ghost {
  padding: 9px 22px;
  font-size: 14px;
  color: #6b7280;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-ghost:hover { color: #4f46e5; border-color: #c7d2fe; }

/* ========== 空状态 ========== */
.ck-empty {
  padding: 100px 24px;
  text-align: center;
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
}
.ck-empty-icon { display: block; font-size: 64px; margin-bottom: 14px; }
.ck-empty-title { margin: 0 0 6px; font-size: 18px; font-weight: 600; color: #1f2937; }
.ck-empty-desc  { margin: 0 0 24px; font-size: 14px; color: #9ca3af; }
.ck-empty-btns  { display: flex; gap: 12px; justify-content: center; }

/* ========== 顶部头 ========== */
.ck-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 18px;
  margin-bottom: 16px;
}
.ck-back {
  padding: 6px 14px;
  font-size: 13px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}
.ck-back:hover { background-color: #e0e7ff; }

.ck-title { margin: 0; font-size: 22px; font-weight: 700; color: #1f2937; }
.ck-order-tip { margin-left: auto; font-size: 13px; color: #059669; background-color: #d1fae5; padding: 4px 12px; border-radius: 9999px; }

/* ========== 主布局 ========== */
.ck-layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
  align-items: start;
}
@media (max-width: 960px) {
  .ck-layout { grid-template-columns: 1fr; }
}

/* ========== 通用卡片 ========== */
.ck-card {
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 14px;
}
.ck-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}
.ck-link {
  font-size: 12px;
  color: #4f46e5;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.ck-link:hover { text-decoration: underline; }

/* ========== 订单信息条 ========== */
.ck-order-bar {
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border: 1px solid #c7d2fe;
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 24px;
  font-size: 13px;
  color: #374151;
}
.ck-order-label { color: #6b7280; margin-right: 6px; }
.ck-order-id { font-family: Menlo, Consolas, monospace; font-weight: 600; color: #1f2937; }
.ck-timer { margin-left: auto; font-weight: 500; color: #d97706; }
.ck-timer.danger { color: #dc2626; }
.ck-timer-icon { margin-right: 4px; }
.ck-timer b { font-size: 15px; }

/* ========== 收货地址 ========== */
.ck-card-empty { border: 1px dashed #fecaca; background: #fffaf8; }
.ck-address {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 12px;
  padding: 14px;
  background: #fafafa;
  border-radius: 10px;
}
.ck-address-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ck-address-default {
  display: inline-block;
  padding: 1px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border-radius: 9999px;
}
.ck-address-phone { font-size: 13px; color: #6b7280; }
.ck-address-detail { margin: 0; width: 100%; font-size: 13px; color: #4b5563; }

/* 无地址引导态 */
.ck-no-address {
  padding: 14px;
  text-align: center;
  background: #fff;
  border: 1px dashed #fecaca;
  border-radius: 10px;
}
.ck-no-address-icon { display: block; font-size: 32px; margin-bottom: 6px; }
.ck-no-address-tip {
  margin: 0 0 14px;
  font-size: 13px;
  color: #b91c1c;
  font-weight: 500;
}

/* ========== 地址卡片：整卡可点击 ========== */
.ck-address-card { cursor: pointer; transition: all 0.15s ease; }
.ck-address-card:hover { border-color: #c7d2fe; box-shadow: 0 4px 14px rgba(79,70,229,0.08); }
.ck-address-card.picked { border: 1.5px solid #c7d2fe; }
.ck-card-title.clickable { cursor: pointer; }

/* ========== 弹窗遮罩 & 主体 ========== */
.ck-addr-mask {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.45);
  z-index: 60;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 80px 16px 40px;
  overflow-y: auto;
  backdrop-filter: blur(2px);
}
.ck-addr-dialog {
  width: 100%;
  max-width: 560px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18);
  overflow: hidden;
}
.ck-addr-dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #f3f4f6;
  background: linear-gradient(180deg, #fafbff, #ffffff);
}
.ck-addr-dialog-head h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1f2937; }
.ck-addr-dialog-close {
  width: 28px; height: 28px;
  border: none; background: transparent;
  border-radius: 8px;
  font-size: 20px;
  line-height: 1;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ck-addr-dialog-close:hover { background: #f3f4f6; color: #1f2937; }

.ck-addr-back {
  padding: 4px 12px;
  margin: 0 0 2px 4px;
  font-size: 12px;
  color: #4f46e5;
  background: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}
.ck-addr-back:hover { background: #e0e7ff; }

/* ========== 选择模式：地址选项卡 ========== */
.ck-addr-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 18px 18px;
  max-height: 62vh;
  overflow-y: auto;
}
.ck-addr-opt {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  text-align: left;
  background: #fff;
  border: 1.5px solid #f3f4f6;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}
.ck-addr-opt:hover { border-color: #c7d2fe; background: #fafbff; }
.ck-addr-opt.active {
  border-color: #4f46e5;
  background: #eef2ff;
  box-shadow: 0 2px 8px rgba(79,70,229,0.15);
}
.ck-addr-radio {
  margin-top: 4px;
  width: 16px; height: 16px;
  accent-color: #4f46e5;
  cursor: pointer;
  flex-shrink: 0;
}
.ck-addr-default-flag {
  position: absolute;
  top: -6px;
  left: 32px;
  display: inline-block;
  padding: 1px 7px;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #f97316, #ef4444);
  border-radius: 9999px;
  letter-spacing: 0.5px;
}
.ck-addr-opt-body { flex: 1; min-width: 0; }
.ck-addr-opt-name {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}
.ck-addr-opt-phone {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 400;
  color: #6b7280;
}
.ck-addr-opt-detail {
  margin: 0;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.5;
}
.ck-addr-opt-region {
  display: inline-block;
  margin-right: 5px;
  padding: 1px 6px;
  font-size: 11px;
  color: #3730a3;
  background: #e0e7ff;
  border-radius: 4px;
}
.ck-addr-opt-check {
  position: absolute;
  right: 14px;
  top: 12px;
  width: 20px; height: 20px;
  line-height: 20px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: #4f46e5;
  border-radius: 9999px;
}

/* 尾部「+ 新建地址」选项卡 */
.ck-addr-opt-new {
  border: 1.5px dashed #c7d2fe;
  background: linear-gradient(180deg, #fafbff, #fff);
  color: #4f46e5;
}
.ck-addr-opt-new:hover { background: #eef2ff; border-style: solid; }
.ck-addr-plus {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  color: #4f46e5;
  background: #e0e7ff;
  border-radius: 10px;
  flex-shrink: 0;
}
.ck-addr-opt-new .ck-addr-opt-name { color: #4f46e5; }
.ck-addr-opt-new .ck-addr-opt-detail { color: #6366f1; }

/* ========== 新建模式：表单 ========== */
.ck-addr-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 18px 0;
}
.ck-addr-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ck-addr-label {
  font-size: 12px;
  color: #374151;
  font-weight: 500;
}
.ck-addr-label i {
  color: #ef4444;
  font-style: normal;
  margin-right: 2px;
}
.ck-addr-input {
  box-sizing: border-box;
  width: 100%;
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
.ck-addr-input:focus { border-color: #818cf8; }
.ck-addr-textarea { min-height: 72px; line-height: 1.5; }
.ck-addr-hint {
  margin: 2px 0 0;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.55;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
}
.ck-addr-error {
  margin: 2px 0 0;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.55;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
}
.ck-addr-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px 18px;
}

/* ========== 商品清单 ========== */
.ck-items { display: flex; flex-direction: column; }
.ck-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed #f3f4f6;
}
.ck-item:last-child { border-bottom: none; }
.ck-item-img {
  width: 56px; height: 56px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}
.ck-item-info { flex: 1; min-width: 0; }
.ck-item-name { margin: 0; font-size: 13px; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ck-item-qty  { margin: 4px 0 0; font-size: 12px; color: #9ca3af; }
.ck-item-price { font-size: 14px; font-weight: 600; color: #1f2937; white-space: nowrap; }

/* ========== 支付方式 ========== */
.ck-pay-list { display: flex; flex-direction: column; gap: 10px; }
.ck-pay-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1.5px solid #f3f4f6;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ck-pay-item:hover { border-color: #c7d2fe; background: #fafbff; }
.ck-pay-item.active { border-color: #4f46e5; background: #eef2ff; }
.ck-pay-radio { accent-color: #4f46e5; cursor: pointer; }
.ck-pay-icon {
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.ck-pay-info { flex: 1; min-width: 0; }
.ck-pay-name { margin: 0; font-size: 14px; font-weight: 600; color: #1f2937; }
.ck-pay-desc { margin: 3px 0 0; font-size: 12px; color: #6b7280; }
.ck-pay-check {
  position: absolute; top: 8px; right: 10px;
  font-size: 12px; color: #4f46e5; font-weight: 700;
}

/* ========== 右侧：费用明细 ========== */
.ck-side { position: sticky; top: 80px; }

.ck-summary {
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  padding: 20px;
}
.ck-summary-title { margin: 0 0 14px; font-size: 16px; font-weight: 700; color: #1f2937; }

.ck-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  color: #6b7280;
}
.ck-row-total { padding: 10px 0 0; font-size: 14px; color: #374151; font-weight: 500; }
.ck-divider { height: 1px; background: #f3f4f6; margin: 10px 0; }
.ck-discount { color: #ef4444; font-weight: 500; }
.ck-total {
  font-size: 26px;
  font-weight: 800;
  color: #ef4444;
  line-height: 1;
}

/* 支付按钮 */
.ck-pay-btn {
  width: 100%;
  margin-top: 16px;
  padding: 14px 0;
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #f97316, #ef4444);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ck-pay-btn:hover:not(.disabled) { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(239, 68, 68, 0.28); }
.ck-pay-btn.disabled { opacity: 0.55; cursor: not-allowed; }

.ck-tip-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 14px 0 0;
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
}
</style>
