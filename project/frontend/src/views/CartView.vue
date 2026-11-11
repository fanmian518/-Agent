<script setup lang="ts">
/**
 * CartView.vue - 购物车页面
 * ----------------------------------------------------------------
 * 功能：
 *   - 全选 / 单选 / 批量删除 / 批量移入收藏
 *   - 数量 +/- 修改
 *   - 搜索购物车内商品
 *   - 结算明细（右侧固定面板）
 *   - 去结算 → 生成订单
 *   - 猜你喜欢（推荐商品）
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  useCart,
  toggleSelected,
  selectAll,
  removeFromCart,
  removeFromCartBatch,
  updateQuantity,
  moveToFavorites,
  selectedItems,
  selectedTotal,
  isAllSelected
} from '@/stores/cart'
import { addToFavorite, isFavorite } from '@/stores/favorites'
import { createOrder } from '@/stores/orders'
import { isLoggedIn } from '@/stores/user'
import { addToCart } from '@/stores/cart'
import { apiCreateOrder } from '@/api/order'
import { defaultAddress, refreshAddresses } from '@/stores/addresses'
import { refreshOrders } from '@/stores/orders'

const router = useRouter()
const cart = useCart()

// 搜索关键字
const searchKeyword = ref('')

// 批量操作确认
const batchAction = ref<null | 'delete' | 'favorites'>(null)

// ====== 筛选后的商品 ======
const filteredItems = computed(() => {
  if (!searchKeyword.value.trim()) return cart.items
  const kw = searchKeyword.value.trim().toLowerCase()
  return cart.items.filter(
    i => i.name.toLowerCase().includes(kw) || (i.desc?.toLowerCase().includes(kw) ?? false)
  )
})

// ====== 选中数量 ======
const selectedCount = computed(() =>
  selectedItems.value.reduce((sum, i) => sum + i.quantity, 0)
)

// ====== 已选中的 ID 列表 ======
const selectedIds = computed(() =>
  selectedItems.value.map(i => i.id)
)

// ====== 操作方法 ======

// 批量删除
const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) {
    alert('请先选择商品')
    return
  }
  batchAction.value = 'delete'
}
const confirmBatchDelete = () => {
  removeFromCartBatch(selectedIds.value)
  batchAction.value = null
}

// 批量移入收藏
const handleBatchFavorites = () => {
  if (selectedIds.value.length === 0) {
    alert('请先选择商品')
    return
  }
  batchAction.value = 'favorites'
}
const confirmBatchFavorites = () => {
  const moved = moveToFavorites(selectedIds.value)
  let added = 0
  let skipped = 0
  moved.forEach(i => {
    if (isFavorite(i.id)) {
      skipped++
    } else {
      addToFavorite({
        id: i.id,
        name: i.name,
        price: i.price,
        emoji: i.emoji,
        bgColor: i.bgColor
      })
      added++
    }
  })
  alert(`已加入收藏 ${added} 件${skipped ? `，${skipped} 件已在收藏夹中` : ''}\n商品仍保留在购物车`)
  batchAction.value = null
}

// 单项移入收藏（保留购物车商品）
const moveOneToFavorites = (id: number) => {
  const item = cart.items.find(i => i.id === id)
  if (!item) return
  if (isFavorite(item.id)) {
    alert('该商品已在收藏夹中')
    return
  }
  addToFavorite({
    id: item.id,
    name: item.name,
    price: item.price,
    emoji: item.emoji,
    bgColor: item.bgColor
  })
  alert('已加入收藏夹')
}

// 去结算：先 createOrder → 再跳转付款页 /checkout?orderId=xxx
const handleCheckout = async () => {
  if (selectedItems.value.length === 0) {
    alert('请先选择要结算的商品')
    return
  }
  if (!isLoggedIn.value) {
    alert('请先登录后再进行结算')
    router.push({ path: '/login', query: { redirect: '/cart' } })
    return
  }
  await refreshAddresses()
  if (!defaultAddress.value) {
    alert('请先选择或新建收货地址')
    router.push('/profile?tab=addresses')
    return
  }
  try {
    const order = await apiCreateOrder(selectedItems.value.map(i => ({ id: i.id, name: i.name, price: i.price, emoji: i.emoji, quantity: i.quantity })), { address_id: Number(defaultAddress.value.id) } as any)
    await refreshOrders()
    // 订单创建成功 → 跳转到付款跳转界面（收银台），由用户选择支付方式再付款
    router.push({ path: '/checkout', query: { orderId: (order as any).order_id ?? (order as any).id } })
  } catch (error: any) {
    alert(error?.message || '订单创建失败')
  }
}

// ====== 猜你喜欢（推荐商品） ======
const recommendProducts = [
  { id: 501, name: '磁吸无线充电宝', desc: '20000mAh · 快充', price: 129, emoji: '🔋', bgColor: 'linear-gradient(135deg, #667eea, #764ba2)' },
  { id: 502, name: '极简风机械键盘', desc: '三模连接 · 热插拔', price: 399, emoji: '⌨️', bgColor: 'linear-gradient(135deg, #f093fb, #f5576c)' },
  { id: 503, name: '人体工学办公椅', desc: '4D扶手 · 腰枕可调', price: 899, emoji: '🪑', bgColor: 'linear-gradient(135deg, #4facfe, #00f2fe)' },
  { id: 504, name: '智能香薰加湿器', desc: '静音 · 氛围灯', price: 199, emoji: '💨', bgColor: 'linear-gradient(135deg, #a8edea, #fed6e3)' }
]

const addRecommendToCart = (p: typeof recommendProducts[number]) => {
  addToCart({
    id: p.id,
    name: p.name,
    desc: p.desc,
    price: p.price,
    emoji: p.emoji,
    bgColor: p.bgColor
  })
}

// 返回首页
const goHome = () => router.push('/')

// 手动输入数量
const onQtyInput = (id: number, e: Event) => {
  const input = e.target as HTMLInputElement
  let val = parseInt(input.value, 10)
  if (isNaN(val) || val < 1) val = 1
  if (val > 999) val = 999
  input.value = String(val)
  updateQuantity(id, val)
}
// 失焦时校正空值
const onQtyBlur = (id: number, e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.value || parseInt(input.value, 10) < 1) {
    const item = cart.items.find(i => i.id === id)
    input.value = String(item?.quantity ?? 1)
  }
}
</script>

<template>
  <div class="cart-page">
    <!-- 返回首页 -->
    <button class="back-home" @click="goHome">← 返回首页</button>

    <!-- 页面标题 -->
    <div class="cart-header">
      <h1>🛒 购物车</h1>
      <span class="cart-count">全部商品 ({{ cart.items.length }})</span>
    </div>

    <!-- 空购物车 -->
    <template v-if="cart.items.length === 0">
      <div class="cart-empty">
        <span class="cart-empty-icon">🛒</span>
        <p>购物车空空如也，去挑点好物吧～</p>
        <button class="btn-primary big" @click="goHome">去逛逛</button>
      </div>
    </template>

    <!-- 有商品 -->
    <template v-else>
      <div class="cart-layout">
        <!-- ====== 左侧：商品列表 ====== -->
        <div class="cart-main">
          <!-- 操作栏 -->
          <div class="cart-toolbar">
            <label class="checkbox-item">
              <input
                type="checkbox"
                :checked="isAllSelected"
                @change="selectAll(!isAllSelected)"
              />
              <span>全选</span>
            </label>
            <button class="toolbar-btn" @click="handleBatchFavorites">移入收藏</button>
            <button class="toolbar-btn danger" @click="handleBatchDelete">删除</button>

            <div class="cart-toolbar-right">
              <input
                v-model="searchKeyword"
                type="text"
                class="cart-search"
                placeholder="搜索购物车内商品"
              />
            </div>
          </div>

          <!-- 商品列表 -->
          <div class="cart-list">
            <div
              v-for="item in filteredItems"
              :key="item.id"
              class="cart-item"
            >
              <!-- 复选框 -->
              <label class="item-checkbox">
                <input
                  type="checkbox"
                  :checked="item.selected"
                  @change="toggleSelected(item.id)"
                />
              </label>

              <!-- 商品图片 -->
              <div class="item-img" :style="{ background: item.bgColor }">
                <span>{{ item.emoji }}</span>
              </div>

              <!-- 商品信息 -->
              <div class="item-info">
                <h3 class="item-name">{{ item.name }}</h3>
                <p v-if="item.desc" class="item-desc">{{ item.desc }}</p>
                <!-- 促销标签 -->
                <div v-if="item.promotions && item.promotions.length" class="item-promotions">
                  <span v-for="(p, idx) in item.promotions" :key="idx" class="promo-tag">{{ p }}</span>
                </div>
              </div>

              <!-- 价格 -->
              <div class="item-price-col">
                <div class="item-price">¥{{ item.price }}</div>
                <div v-if="item.originalPrice" class="item-original-price">¥{{ item.originalPrice }}</div>
              </div>

              <!-- 数量控制 -->
              <div class="item-qty">
                <button @click="updateQuantity(item.id, item.quantity - 1)">−</button>
                <input
                  class="item-qty-num"
                  type="number"
                  min="1"
                  max="999"
                  :value="item.quantity"
                  @input="onQtyInput(item.id, $event)"
                  @blur="onQtyBlur(item.id, $event)"
                />
                <button @click="updateQuantity(item.id, item.quantity + 1)">+</button>
              </div>

              <!-- 操作按钮 -->
              <div class="item-actions">
                <button class="item-action-btn" @click="moveOneToFavorites(item.id)">移入收藏</button>
                <button class="item-action-btn danger" @click="removeFromCart(item.id)">删除</button>
              </div>
            </div>

            <!-- 搜索无结果 -->
            <div v-if="filteredItems.length === 0" class="search-empty">
              <p>没有找到匹配的商品</p>
            </div>
          </div>

          <!-- 猜你喜欢 -->
          <div class="recommend-section">
            <h3 class="recommend-title">✨ 猜你喜欢</h3>
            <div class="recommend-grid">
              <div v-for="p in recommendProducts" :key="p.id" class="recommend-card" @click="router.push(`/product/${p.id}`)">
                <div class="recommend-img" :style="{ background: p.bgColor }">
                  <span>{{ p.emoji }}</span>
                </div>
                <div class="recommend-name">{{ p.name }}</div>
                <div class="recommend-desc">{{ p.desc }}</div>
                <div class="recommend-bottom">
                  <span class="recommend-price">¥{{ p.price }}</span>
                  <button class="recommend-add" @click="addRecommendToCart(p)">+ 加入</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ====== 右侧：结算面板 ====== -->
        <aside class="cart-sidebar">
          <div class="checkout-card">
            <h3 class="checkout-title">结算明细</h3>

            <!-- 空状态 -->
            <template v-if="selectedItems.length === 0">
              <div class="checkout-empty">
                <div class="checkout-empty-icon">🛒</div>
                <p>选择商品查看实际支付价格</p>
              </div>
            </template>

            <!-- 已选商品 -->
            <template v-else>
              <div class="checkout-items">
                <div v-for="item in selectedItems" :key="item.id" class="checkout-row">
                  <span class="checkout-row-name">{{ item.name }}</span>
                  <span class="checkout-row-qty">×{{ item.quantity }}</span>
                  <span class="checkout-row-price">¥{{ (item.price * item.quantity).toFixed(2) }}</span>
                </div>
              </div>

              <div class="checkout-divider"></div>

              <div class="checkout-total-row">
                <span>共 {{ selectedCount }} 件商品，合计</span>
                <span class="checkout-total">¥{{ selectedTotal.toFixed(2) }}</span>
              </div>

              <button class="checkout-btn" @click="handleCheckout">
                去结算 ({{ selectedIds.length }})
              </button>
            </template>
          </div>

          <!-- 购物小贴士 -->
          <div class="cart-tips">
            <p>💡 小贴士</p>
            <ul>
              <li>勾选商品后可批量操作</li>
              <li>结算前请确认商品规格</li>
              <li>支持七天无理由退换</li>
            </ul>
          </div>
        </aside>
      </div>
    </template>

    <!-- ====== 批量操作确认弹窗 ====== -->
    <div v-if="batchAction" class="modal-mask" @click.self="batchAction = null">
      <div class="modal">
        <p class="modal-text">
          {{ batchAction === 'delete'
            ? `确定要删除选中的 ${selectedIds.length} 件商品吗？`
            : `确定要将选中的 ${selectedIds.length} 件商品移入收藏夹吗？` }}
        </p>
        <div class="modal-actions">
          <button class="btn-ghost" @click="batchAction = null">取消</button>
          <button
            class="btn-primary"
            :class="{ danger: batchAction === 'delete' }"
            @click="batchAction === 'delete' ? confirmBatchDelete() : confirmBatchFavorites()"
          >确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ====== 页面容器 ====== */
.cart-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

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

/* ====== 页面标题 ====== */
.cart-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.cart-header h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
}

.cart-count {
  font-size: 13px;
  color: #6b7280;
}

/* ====== 空购物车 ====== */
.cart-empty {
  padding: 80px 0;
  text-align: center;
  background-color: #ffffff;
  border-radius: 12px;
  border: 1px solid #f3f4f6;
}

.cart-empty-icon {
  display: block;
  font-size: 64px;
  margin-bottom: 16px;
}

.cart-empty p {
  margin: 0 0 24px;
  color: #9ca3af;
}

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

.btn-primary:hover {
  background-color: #4338ca;
}

.btn-primary.big {
  padding: 12px 32px;
  font-size: 15px;
}

.btn-primary.danger {
  background-color: #ef4444;
}

.btn-primary.danger:hover {
  background-color: #dc2626;
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

/* ====== 布局 ====== */
.cart-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 960px) {
  .cart-layout {
    grid-template-columns: 1fr;
  }
}

/* ====== 主区域 ====== */
.cart-main {
  background-color: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  overflow: hidden;
}

/* ====== 操作栏 ====== */
.cart-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background-color: #fafafa;
  border-bottom: 1px solid #f3f4f6;
  flex-wrap: wrap;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  user-select: none;
}

.checkbox-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.toolbar-btn {
  padding: 4px 12px;
  font-size: 12px;
  color: #6b7280;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.toolbar-btn:hover {
  color: #4f46e5;
  border-color: #c7d2fe;
}

.toolbar-btn.danger:hover {
  color: #ef4444;
  border-color: #fecaca;
}

.cart-toolbar-right {
  margin-left: auto;
}

.cart-search {
  width: 200px;
  padding: 6px 12px;
  font-size: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  outline: none;
  transition: border-color 0.15s ease;
}

.cart-search:focus {
  border-color: #818cf8;
  width: 240px;
}

/* ====== 商品列表 ====== */
.cart-list {
  display: flex;
  flex-direction: column;
}

.cart-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.15s ease;
}

.cart-item:hover {
  background-color: #fafafa;
}

.cart-item:last-child {
  border-bottom: none;
}

.item-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.item-img {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.item-promotions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.promo-tag {
  padding: 1px 8px;
  font-size: 11px;
  color: #ef4444;
  background-color: #fef2f2;
  border-radius: 4px;
  border: 1px solid #fee2e2;
}

.item-price-col {
  text-align: right;
  min-width: 70px;
}

.item-price {
  font-size: 16px;
  font-weight: 700;
  color: #ef4444;
}

.item-original-price {
  font-size: 12px;
  color: #9ca3af;
  text-decoration: line-through;
}

/* 数量控制 */
.item-qty {
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}

.item-qty button {
  width: 30px;
  height: 28px;
  font-size: 16px;
  color: #4b5563;
  background-color: #fafafa;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.item-qty button:hover {
  color: #4f46e5;
  background-color: #eef2ff;
}

.item-qty-num {
  width: 48px;
  height: 28px;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  border: none;
  border-left: 1px solid #e5e7eb;
  border-right: 1px solid #e5e7eb;
  outline: none;
  background-color: #fff;
  -moz-appearance: textfield;
  appearance: textfield;
}

/* 隐藏 number input 的上下箭头（WebKit） */
.item-qty-num::-webkit-outer-spin-button,
.item-qty-num::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.item-qty-num:focus {
  background-color: #eef2ff;
  color: #4f46e5;
}

.item-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.item-action-btn {
  padding: 2px 8px;
  font-size: 11px;
  color: #6b7280;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.15s ease;
}

.item-action-btn:hover {
  color: #4f46e5;
}

.item-action-btn.danger:hover {
  color: #ef4444;
}

.search-empty {
  padding: 40px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}

/* ====== 猜你喜欢 ====== */
.recommend-section {
  padding: 20px 16px;
  background-color: #fafafa;
}

.recommend-title {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 600;
  color: #374151;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 640px) {
  .recommend-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.recommend-card {
  padding: 10px;
  background-color: #ffffff;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
  transition: all 0.15s ease;
}

.recommend-card {
  cursor: pointer;
}

.recommend-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.recommend-img {
  width: 100%;
  padding-top: 100%;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 8px;
}

.recommend-img span {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 32px;
}

.recommend-name {
  font-size: 12px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommend-desc {
  font-size: 11px;
  color: #9ca3af;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommend-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.recommend-price {
  font-size: 14px;
  font-weight: 700;
  color: #ef4444;
}

.recommend-add {
  padding: 2px 8px;
  font-size: 11px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.recommend-add:hover {
  background-color: #4f46e5;
  color: #ffffff;
}

/* ====== 右侧结算面板 ====== */
.cart-sidebar {
  position: sticky;
  top: 80px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.checkout-card {
  padding: 18px;
  background-color: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
}

.checkout-title {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.checkout-empty {
  padding: 30px 0;
  text-align: center;
}

.checkout-empty-icon {
  font-size: 40px;
  margin-bottom: 8px;
  opacity: 0.5;
}

.checkout-empty p {
  margin: 0;
  font-size: 12px;
  color: #9ca3af;
}

.checkout-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  max-height: 180px;
  overflow-y: auto;
}

.checkout-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  font-size: 12px;
  color: #4b5563;
}

.checkout-row-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.checkout-row-qty {
  color: #9ca3af;
}

.checkout-row-price {
  font-weight: 500;
  color: #1f2937;
}

.checkout-divider {
  height: 1px;
  background-color: #f3f4f6;
  margin: 10px 0;
}

.checkout-total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 14px;
}

.checkout-total {
  font-size: 22px;
  font-weight: 700;
  color: #ef4444;
}

.checkout-btn {
  width: 100%;
  padding: 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(to right, #f97316, #ef4444);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.checkout-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.35);
}

/* 小贴士 */
.cart-tips {
  padding: 14px 16px;
  background-color: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 10px;
  font-size: 12px;
  color: #92400e;
}

.cart-tips p {
  margin: 0 0 6px;
  font-weight: 600;
}

.cart-tips ul {
  margin: 0;
  padding-left: 16px;
  line-height: 1.8;
}

/* ====== 弹窗 ====== */
.modal-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  width: 90%;
  max-width: 360px;
  padding: 24px;
  background-color: #ffffff;
  border-radius: 14px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.modal-text {
  margin: 0 0 20px;
  font-size: 14px;
  color: #374151;
  text-align: center;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
