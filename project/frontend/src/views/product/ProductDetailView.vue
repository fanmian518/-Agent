<script setup lang="ts">
/**
 * ProductDetailView.vue - 商品详情页
 * ----------------------------------------------------------------
 * 路由：/product/:id
 * 布局参考电商详情页：
 *   左侧：店铺信息条 + 主图 + 缩略图切换
 *   右侧：标题 / 价格区 / 配送服务 / SKU / 数量 / 操作按钮
 *   底部：用户评价 / 参数信息 / 图文详情 / 看了又看
 */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProductById, getRelatedProducts, getCategoryName, SHOPS, getProductRating, getReviewCount, formatSales } from '@/stores/products'
import type { Product } from '@/stores/products'
import { addToCart, selectAll } from '@/stores/cart'
import { isFavorite, toggleFavorite } from '@/stores/favorites'
import { recordView } from '@/stores/history'
import { createOrder } from '@/stores/orders'
import { isLoggedIn } from '@/stores/user'

const route = useRoute()
const router = useRouter()

// ====== 商品数据 ======
const product = ref<Product | null>(null)
const notFound = ref(false)

const loadProduct = (id: number) => {
  const p = getProductById(id)
  if (p) {
    product.value = p
    notFound.value = false
    // 记录浏览历史
    recordView({ id: p.id, name: p.name, emoji: p.emoji, bgColor: p.bgColor })
  } else {
    notFound.value = true
  }
}

// 监听路由参数变化（详情页之间跳转）
watch(() => route.params.id, (v) => {
  if (v) loadProduct(Number(v))
}, { immediate: true })

// ====== 派生信息 ======
const shop = computed(() => product.value ? SHOPS[product.value.category] : null)
const rating = computed(() => product.value ? getProductRating(product.value.id) : 5)
const reviewCount = computed(() => product.value ? getReviewCount(product.value.sales) : 0)

// 促销标签：无 tag 的商品显示包邮标签
const promoTags = computed(() => {
  if (!product.value) return []
  return product.value.tag ? [product.value.tag] : ['包邮']
})

// ====== 主图与缩略图（4 个渐变变体） ======
const bgVariants = [
  '',
  'linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%)',
  'linear-gradient(135deg, #fff1eb 0%, #ace0f9 100%)',
  'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)'
]
const activeBg = ref(0)
const mainBg = computed(() => {
  if (!product.value) return ''
  if (activeBg.value === 0) return product.value.bgColor
  return bgVariants[activeBg.value]
})

// ====== 底部内容标签 ======
const bottomTab = ref<'reviews' | 'params' | 'detail'>('reviews')

// ====== 数量 ======
const quantity = ref(1)
const decQty = () => { if (quantity.value > 1) quantity.value-- }
const incQty = () => { if (quantity.value < 99) quantity.value++ }

// ====== 收藏 ======
const fav = computed(() => product.value ? isFavorite(product.value.id) : false)
const handleFavorite = () => {
  if (!product.value) return
  toggleFavorite({
    id: product.value.id,
    name: product.value.name,
    price: product.value.price,
    emoji: product.value.emoji,
    bgColor: product.value.bgColor
  })
}

// ====== 加购 / 立即购买 ======
const handleAddCart = () => {
  if (!product.value) return
  addToCart({
    id: product.value.id,
    name: product.value.name,
    desc: product.value.desc,
    price: product.value.price,
    emoji: product.value.emoji,
    bgColor: product.value.bgColor
  }, quantity.value)
  alert(`已加入购物车 ×${quantity.value}`)
}

// 立即购买：遵循项目约束 —— 先把选中商品加入购物车，再跳转 /checkout
// 为避免把购物车里旧的未勾选商品带进结算，先取消全选 → 只加入当前商品（默认 selected=true）
const handleBuyNow = () => {
  if (!product.value) return
  if (!isLoggedIn.value) {
    alert('请先登录后再进行购买')
    router.push({
      path: '/login',
      query: { redirect: `/product/${product.value.id}` }
    })
    return
  }
  // 取消购物车其他勾选，保证本次结算只含当前数量的本商品
  selectAll(false)
  addToCart({
    id: product.value.id,
    name: product.value.name,
    desc: product.value.desc,
    price: product.value.price,
    emoji: product.value.emoji,
    bgColor: product.value.bgColor
  }, quantity.value)
  // 使用购物车里刚加入的本商品为选中项创建订单
  const pending = [{
    id: product.value.id,
    name: product.value.name,
    desc: product.value.desc,
    price: product.value.price,
    emoji: product.value.emoji,
    bgColor: product.value.bgColor,
    quantity: quantity.value,
    selected: true,
    originalPrice: product.value.originalPrice,
    promotions: product.value.tag ? [product.value.tag] : undefined
  }]
  const order = createOrder(pending)
  if (order) {
    router.push({ path: '/checkout', query: { orderId: order.id } })
  } else {
    // 兜底：createOrder 返回 null（items 为空）时回退到购物车
    router.push('/cart')
  }
}

// ====== 相关推荐 ======
const related = computed(() => product.value ? getRelatedProducts(product.value.id) : [])

// ====== 用户评价（Mock，按商品 ID 稳定生成） ======
const REVIEWERS = [
  { name: '星河**漫步', avatar: '🌟' },
  { name: '柠檬**不酸', avatar: '🍋' },
  { name: '山海**皆过', avatar: '⛰️' },
  { name: '清风**徐来', avatar: '🍃' }
]
const REVIEW_TEXTS = [
  '质量非常好，和描述完全一致，物流也很快，包装严实，满意！',
  '性价比超高，用了几天才来评价，体验很棒，值得推荐。',
  '第二次回购了，品质一如既往地稳定，客服态度也很好。',
  '外观颜值在线，做工细致，收到货超出预期，五星好评！'
]
const reviews = computed(() => {
  if (!product.value) return []
  const base = product.value.id
  return REVIEWERS.slice(0, 3 + (base % 2)).map((r, i) => ({
    ...r,
    stars: 5 - (base + i) % 2,
    text: REVIEW_TEXTS[(base + i) % REVIEW_TEXTS.length],
    time: `2026-0${1 + (base + i) % 8}-${10 + (base * 3 + i) % 18}`
  }))
})

// ====== 返回 ======
const goBack = () => router.back()
</script>

<template>
  <!-- 商品不存在 -->
  <div v-if="notFound" class="pd-notfound">
    <span class="pd-notfound-icon">🔍</span>
    <p>商品不存在或已下架</p>
    <button class="pd-btn-primary" @click="router.push('/')">回首页逛逛</button>
  </div>

  <div v-else-if="product" class="pd-page">
    <!-- 面包屑 -->
    <div class="pd-crumb">
      <button class="pd-back" @click="goBack">← 返回</button>
      <span class="pd-crumb-sep">/</span>
      <span>{{ getCategoryName(product.category) }}</span>
      <span class="pd-crumb-sep">/</span>
      <span class="pd-crumb-cur">{{ product.name }}</span>
    </div>

    <!-- ====== 主体：左图右信息 ====== -->
    <div class="pd-main">
      <!-- 左侧：店铺条 + 图片区 -->
      <div class="pd-left">
        <!-- 店铺信息条 -->
        <div class="pd-shop-bar">
          <span class="pd-shop-avatar">{{ shop?.emoji }}</span>
          <div class="pd-shop-info">
            <div class="pd-shop-name">
              {{ shop?.name }}
              <span class="pd-shop-arrow">›</span>
            </div>
            <div class="pd-shop-meta">
              <span class="pd-stars">{{ '★'.repeat(5) }}</span>
              <span class="pd-shop-rating">{{ shop?.rating }}</span>
              <span class="pd-shop-divider">|</span>
              <span>{{ formatSales(product.sales) }} 人已买</span>
            </div>
          </div>
          <button class="pd-shop-btn">💬 客服</button>
          <button class="pd-shop-btn">🏪 进店</button>
        </div>

        <!-- 主图 -->
        <div class="pd-img-main" :style="{ background: mainBg }">
          <span class="pd-img-emoji">{{ product.emoji }}</span>
          <span v-if="product.tag" class="pd-img-tag">{{ product.tag }}</span>
        </div>

        <!-- 缩略图切换 -->
        <div class="pd-thumbs">
          <div
            v-for="(bg, i) in bgVariants"
            :key="i"
            class="pd-thumb"
            :class="{ active: activeBg === i }"
            :style="{ background: i === 0 ? product.bgColor : bg }"
            @click="activeBg = i"
          >
            <span>{{ product.emoji }}</span>
          </div>
        </div>

        <!-- 图集/参数 切换 -->
        <div class="pd-gallery-tabs">
          <button :class="{ on: bottomTab !== 'params' }" @click="bottomTab = 'reviews'">图集</button>
          <button :class="{ on: bottomTab === 'params' }" @click="bottomTab = 'params'">参数</button>
        </div>
      </div>

      <!-- 右侧：商品信息 -->
      <div class="pd-right">
        <!-- 标题 -->
        <h1 class="pd-title">{{ product.name }}</h1>
        <p v-if="product.desc" class="pd-subtitle">{{ product.desc }}</p>

        <!-- 销量/评价 -->
        <div class="pd-sold-row">
          <span class="pd-sold-num">已售 {{ formatSales(product.sales) }}</span>
          <span class="pd-shop-divider">|</span>
          <span>{{ reviewCount }} 条评价</span>
          <span class="pd-shop-divider">|</span>
          <span>好评率 {{ Math.min(99, Math.floor(rating * 20)) }}%</span>
        </div>

        <!-- 价格区 -->
        <div class="pd-price-block">
          <div class="pd-price-left">
            <span class="pd-price-symbol">¥</span>
            <span class="pd-price-num">{{ product.price }}</span>
            <span v-if="product.originalPrice" class="pd-price-origin">¥{{ product.originalPrice }}</span>
          </div>
          <div class="pd-price-right">
            <span v-for="t in promoTags" :key="t" class="pd-promo-tag">{{ t }}</span>
          </div>
        </div>

        <!-- 配送信息 -->
        <div class="pd-ship-row">
          <span class="pd-ship-icon">🚚</span>
          <span>48小时内发货</span>
          <span class="pd-shop-divider">|</span>
          <span>快递：免运费</span>
          <span class="pd-shop-divider">|</span>
          <span>送至 江苏徐州</span>
        </div>

        <!-- 服务保障 -->
        <div class="pd-service-row">
          <span class="pd-service-item">🛡️ 假一赔四</span>
          <span class="pd-service-item">⚡ 极速退款</span>
          <span class="pd-service-item">↩️ 7天无理由退换</span>
          <span class="pd-service-item">💳 信用卡支付</span>
        </div>

        <!-- 分类 SKU -->
        <div class="pd-sku-row">
          <span class="pd-sku-label">分类</span>
          <span class="pd-sku-chip active">{{ getCategoryName(product.category) }}</span>
        </div>

        <!-- 数量 -->
        <div class="pd-sku-row">
          <span class="pd-sku-label">数量</span>
          <div class="pd-qty">
            <button @click="decQty">−</button>
            <input
              type="number"
              min="1"
              max="99"
              :value="quantity"
              @change="quantity = Math.max(1, Math.min(99, Number(($event.target as HTMLInputElement).value) || 1))"
            />
            <button @click="incQty">+</button>
          </div>
          <span class="pd-stock">有货（限购 99 件）</span>
        </div>

        <!-- 操作按钮 -->
        <div class="pd-actions">
          <button class="pd-btn-cart" @click="handleAddCart">🛒 加入购物车</button>
          <button class="pd-btn-buy" @click="handleBuyNow">立即购买</button>
          <button class="pd-btn-fav" :class="{ on: fav }" @click="handleFavorite">
            {{ fav ? '★' : '☆' }}
            <span>{{ fav ? '已收藏' : '收藏' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ====== 底部内容区 ====== -->
    <div class="pd-bottom">
      <!-- 标签栏 -->
      <div class="pd-bottom-tabs">
        <button :class="{ on: bottomTab === 'reviews' }" @click="bottomTab = 'reviews'">用户评价</button>
        <button :class="{ on: bottomTab === 'params' }" @click="bottomTab = 'params'">参数信息</button>
        <button :class="{ on: bottomTab === 'detail' }" @click="bottomTab = 'detail'">图文详情</button>
      </div>

      <!-- 用户评价 -->
      <div v-if="bottomTab === 'reviews'" class="pd-panel">
        <div v-for="(r, i) in reviews" :key="i" class="pd-review">
          <div class="pd-review-head">
            <span class="pd-review-avatar">{{ r.avatar }}</span>
            <span class="pd-review-name">{{ r.name }}</span>
            <span class="pd-review-stars">{{ '★'.repeat(r.stars) }}{{ '☆'.repeat(5 - r.stars) }}</span>
            <span class="pd-review-time">{{ r.time }}</span>
          </div>
          <p class="pd-review-text">{{ r.text }}</p>
        </div>
      </div>

      <!-- 参数信息 -->
      <div v-else-if="bottomTab === 'params'" class="pd-panel">
        <table class="pd-param-table">
          <tr><th>商品名称</th><td>{{ product.name }}</td></tr>
          <tr><th>商品编号</th><td>NO.{{ product.id }}</td></tr>
          <tr><th>商品规格</th><td>{{ product.desc || '标准版' }}</td></tr>
          <tr><th>所属分类</th><td>{{ getCategoryName(product.category) }}</td></tr>
          <tr><th>所属店铺</th><td>{{ shop?.name }}</td></tr>
          <tr><th>月销量</th><td>{{ formatSales(product.sales) }}</td></tr>
          <tr><th>售后服务</th><td>7天无理由退换 · 极速退款 · 假一赔四</td></tr>
        </table>
      </div>

      <!-- 图文详情 -->
      <div v-else class="pd-panel pd-detail-panel">
        <div class="pd-detail-img" :style="{ background: product.bgColor }">
          <span>{{ product.emoji }}</span>
        </div>
        <h3>{{ product.name }}</h3>
        <p class="pd-detail-desc">{{ product.desc || '精选好物，品质保障' }}</p>
        <ul class="pd-detail-points">
          <li>✅ 正品保障，官方渠道直供</li>
          <li>✅ 严选材质，做工精细</li>
          <li>✅ 48小时内极速发货</li>
          <li>✅ 全程物流跟踪，签收无忧</li>
        </ul>
      </div>
    </div>

    <!-- ====== 看了又看 ====== -->
    <div class="pd-related">
      <h2 class="pd-related-title">👀 看了又看</h2>
      <div class="pd-related-grid">
        <div
          v-for="p in related"
          :key="p.id"
          class="pd-related-card"
          @click="router.push(`/product/${p.id}`)"
        >
          <div class="pd-related-img" :style="{ background: p.bgColor }">
            <span>{{ p.emoji }}</span>
          </div>
          <div class="pd-related-name">{{ p.name }}</div>
          <div class="pd-related-price">¥{{ p.price }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ====== 页面容器 ====== */
.pd-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}

/* ====== 面包屑 ====== */
.pd-crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #6b7280;
}

.pd-back {
  padding: 4px 12px;
  font-size: 12px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}

.pd-back:hover { background-color: #e0e7ff; }

.pd-crumb-sep { color: #d1d5db; }
.pd-crumb-cur { color: #1f2937; font-weight: 500; }

/* ====== 主体两栏 ====== */
.pd-main {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  padding: 20px;
}

@media (max-width: 768px) {
  .pd-main { flex-direction: column; }
}

/* ====== 左侧 ====== */
.pd-left {
  width: 42%;
  min-width: 320px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .pd-left { width: 100%; min-width: 0; }
}

/* 店铺信息条 */
.pd-shop-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.pd-shop-avatar {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background-color: #f3f4f6;
  border-radius: 10px;
  flex-shrink: 0;
}

.pd-shop-info { flex: 1; min-width: 0; }

.pd-shop-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.pd-shop-arrow { color: #9ca3af; }

.pd-shop-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}

.pd-stars { color: #f59e0b; font-size: 11px; letter-spacing: 1px; }
.pd-shop-rating { color: #ef4444; font-weight: 600; }
.pd-shop-divider { color: #e5e7eb; }

.pd-shop-btn {
  padding: 6px 12px;
  font-size: 12px;
  color: #4b5563;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  cursor: pointer;
  white-space: nowrap;
}

.pd-shop-btn:hover { color: #4f46e5; border-color: #c7d2fe; }

/* 主图 */
.pd-img-main {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.pd-img-emoji {
  font-size: 140px;
  filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.18));
  transition: transform 0.3s ease;
}

.pd-img-main:hover .pd-img-emoji { transform: scale(1.08); }

.pd-img-tag {
  position: absolute;
  top: 14px;
  left: 14px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #f43f5e, #ef4444);
  border-radius: 9999px;
}

/* 缩略图 */
.pd-thumbs {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.pd-thumb {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.15s ease;
}

.pd-thumb.active {
  border-color: #4f46e5;
  transform: translateY(-2px);
}

/* 图集/参数切换 */
.pd-gallery-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
}

.pd-gallery-tabs button {
  padding: 6px 24px;
  font-size: 13px;
  color: #6b7280;
  background-color: #f3f4f6;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}

.pd-gallery-tabs button.on {
  color: #ffffff;
  background-color: #4f46e5;
}

/* ====== 右侧 ====== */
.pd-right { flex: 1; min-width: 0; }

.pd-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.4;
}

.pd-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: #6b7280;
}

.pd-sold-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #9ca3af;
}

.pd-sold-num { color: #ef4444; font-weight: 600; }

/* 价格区 */
.pd-price-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  padding: 14px 18px;
  background: linear-gradient(135deg, #ff4d4f 0%, #ff7a45 100%);
  border-radius: 12px;
  color: #ffffff;
}

.pd-price-left { display: flex; align-items: baseline; gap: 4px; }

.pd-price-symbol { font-size: 18px; font-weight: 600; }

.pd-price-num {
  font-size: 34px;
  font-weight: 800;
  line-height: 1;
}

.pd-price-origin {
  margin-left: 8px;
  font-size: 14px;
  opacity: 0.75;
  text-decoration: line-through;
}

.pd-price-right { display: flex; gap: 6px; }

.pd-promo-tag {
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 9999px;
}

/* 配送 / 服务 */
.pd-ship-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  font-size: 13px;
  color: #4b5563;
}

.pd-service-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 12px;
  color: #6b7280;
}

/* SKU */
.pd-sku-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.pd-sku-label {
  font-size: 13px;
  color: #9ca3af;
  flex-shrink: 0;
}

.pd-sku-chip {
  padding: 6px 16px;
  font-size: 13px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 8px;
}

/* 数量 */
.pd-qty {
  display: flex;
  align-items: center;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.pd-qty button {
  width: 32px;
  height: 32px;
  font-size: 16px;
  color: #4b5563;
  background-color: #f9fafb;
  border: none;
  cursor: pointer;
}

.pd-qty button:hover { background-color: #eef2ff; color: #4f46e5; }

.pd-qty input {
  width: 48px;
  height: 32px;
  text-align: center;
  font-size: 14px;
  border: none;
  border-left: 1px solid #e5e7eb;
  border-right: 1px solid #e5e7eb;
  outline: none;
  -moz-appearance: textfield;
}

.pd-qty input::-webkit-outer-spin-button,
.pd-qty input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.pd-stock { font-size: 12px; color: #9ca3af; }

/* 操作按钮 */
.pd-actions {
  display: flex;
  align-items: stretch;
  gap: 12px;
  margin-top: 22px;
}

.pd-btn-cart,
.pd-btn-buy {
  flex: 1;
  padding: 13px 0;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pd-btn-cart {
  background: linear-gradient(135deg, #fb923c, #f97316);
}

.pd-btn-cart:hover { opacity: 0.9; transform: translateY(-1px); }

.pd-btn-buy {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.pd-btn-buy:hover { opacity: 0.9; transform: translateY(-1px); }

.pd-btn-fav {
  width: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 18px;
  color: #6b7280;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
}

.pd-btn-fav span { font-size: 11px; }

.pd-btn-fav.on {
  color: #f59e0b;
  border-color: #fcd34d;
  background-color: #fffbeb;
}

/* ====== 底部内容区 ====== */
.pd-bottom {
  margin-top: 20px;
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  overflow: hidden;
}

.pd-bottom-tabs {
  display: flex;
  border-bottom: 1px solid #f3f4f6;
}

.pd-bottom-tabs button {
  padding: 14px 28px;
  font-size: 14px;
  color: #6b7280;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
}

.pd-bottom-tabs button.on {
  color: #ef4444;
  font-weight: 600;
  border-bottom-color: #ef4444;
}

.pd-panel { padding: 20px; }

/* 用户评价 */
.pd-review {
  padding: 14px 0;
  border-bottom: 1px solid #f9fafb;
}

.pd-review:last-child { border-bottom: none; }

.pd-review-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.pd-review-avatar { font-size: 20px; }
.pd-review-name { color: #374151; font-weight: 500; }

.pd-review-stars { color: #f59e0b; }

.pd-review-time { margin-left: auto; color: #9ca3af; font-size: 12px; }

.pd-review-text {
  margin: 8px 0 0;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}

/* 参数表 */
.pd-param-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.pd-param-table th {
  width: 140px;
  padding: 12px 16px;
  text-align: left;
  color: #6b7280;
  font-weight: 400;
  background-color: #f9fafb;
}

.pd-param-table td {
  padding: 12px 16px;
  color: #1f2937;
}

.pd-param-table tr {
  border-bottom: 1px solid #f3f4f6;
}

/* 图文详情 */
.pd-detail-panel { text-align: center; }

.pd-detail-img {
  width: 240px;
  height: 240px;
  margin: 0 auto;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 100px;
}

.pd-detail-panel h3 { margin: 18px 0 6px; color: #1f2937; }

.pd-detail-desc { margin: 0; color: #6b7280; font-size: 14px; }

.pd-detail-points {
  list-style: none;
  padding: 0;
  margin: 18px auto 0;
  max-width: 360px;
  text-align: left;
}

.pd-detail-points li {
  padding: 8px 0;
  font-size: 13px;
  color: #4b5563;
  border-bottom: 1px dashed #f3f4f6;
}

/* ====== 看了又看 ====== */
.pd-related { margin-top: 20px; }

.pd-related-title {
  margin: 0 0 14px;
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
}

.pd-related-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

@media (max-width: 768px) {
  .pd-related-grid { grid-template-columns: repeat(2, 1fr); }
}

.pd-related-card {
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pd-related-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}

.pd-related-img {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
}

.pd-related-name {
  margin-top: 8px;
  font-size: 13px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pd-related-price {
  margin-top: 4px;
  font-size: 15px;
  font-weight: 700;
  color: #ef4444;
}

/* ====== 未找到 ====== */
.pd-notfound {
  padding: 100px 0;
  text-align: center;
}

.pd-notfound-icon { font-size: 64px; }

.pd-notfound p { color: #9ca3af; margin: 16px 0 24px; }

/* ====== 通用按钮 ====== */
.pd-btn-primary {
  padding: 10px 28px;
  font-size: 14px;
  color: #ffffff;
  background-color: #4f46e5;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}
</style>
