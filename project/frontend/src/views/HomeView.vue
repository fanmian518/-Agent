<script setup lang="ts">
/**
 * HomeView.vue - 首页
 * ----------------------------------------------------------------
 * 包含：欢迎横幅 + 热销商品网格
 * 商品数据为本地 mock，后续接入真实 API
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { addToCart as cartAdd } from '@/stores/cart'
import { recordView } from '@/stores/history'

const router = useRouter()

// ====== 轮播图数据 ======
interface Banner {
  id: number
  title: string
  subtitle: string
  emoji: string
  bgGradient: string   // 背景渐变
  route: string        // 跳转路由
  cta: string          // 按钮文字
}

const banners: Banner[] = [
  {
    id: 1,
    title: '数码爆款',
    subtitle: '前沿科技好物 · 限时特惠',
    emoji: '📱',
    bgGradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    route: '/category/digital',
    cta: '立即抢购'
  },
  {
    id: 2,
    title: '潮流穿搭',
    subtitle: '穿出自我风格 · 新品上市',
    emoji: '👗',
    bgGradient: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
    route: '/category/fashion',
    cta: '去看看'
  },
  {
    id: 3,
    title: '家居好物',
    subtitle: '用心装点家 · 温馨每一天',
    emoji: '🏠',
    bgGradient: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
    route: '/category/homegoods',
    cta: '发现好物'
  },
  {
    id: 4,
    title: '新人专享',
    subtitle: '注册即领百元礼包',
    emoji: '🎁',
    bgGradient: 'linear-gradient(135deg, #ff512f 0%, #f09819 100%)',
    route: '/category/newuser',
    cta: '立即领取'
  }
]

// ====== 轮播控制 ======
const currentBanner = ref(0)
let autoTimer: number | null = null

const nextBanner = () => {
  currentBanner.value = (currentBanner.value + 1) % banners.length
}
const prevBanner = () => {
  currentBanner.value = (currentBanner.value - 1 + banners.length) % banners.length
}
const goBanner = (index: number) => {
  currentBanner.value = index
}
const startAutoPlay = () => {
  stopAutoPlay()
  autoTimer = window.setInterval(nextBanner, 4000)
}
const stopAutoPlay = () => {
  if (autoTimer) {
    clearInterval(autoTimer)
    autoTimer = null
  }
}

onMounted(startAutoPlay)
onUnmounted(stopAutoPlay)

// 点击轮播图跳转
const onBannerClick = (banner: Banner) => {
  router.push(banner.route)
}

// ====== 商品类型定义 ======
interface Product {
  id: number
  name: string          // 商品名称
  desc: string          // 商品副标题/卖点
  price: number         // 现价
  originalPrice: number // 原价（划线）
  emoji: string         // 商品图标（占位，后续替换为真实图片）
  bgColor: string       // 卡片背景色（占位）
  sales: number         // 月销量
  tag?: string          // 标签：热销 / 新品 / 限时
}

// ====== Mock 商品数据 ======
const products: Product[] = [
  {
    id: 101,
    name: '极光 Pro 5G 手机',
    desc: '6.7寸全面屏 · 12+256GB',
    price: 3999,
    originalPrice: 4999,
    emoji: '📱',
    bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    sales: 2863,
    tag: '热销'
  },
  {
    id: 103,
    name: '降噪无线蓝牙耳机',
    desc: '主动降噪 · 续航40小时',
    price: 399,
    originalPrice: 699,
    emoji: '🎧',
    bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    sales: 5120,
    tag: '限时'
  },
  {
    id: 105,
    name: '超薄智能手表',
    desc: '血氧监测 · 7天续航',
    price: 1299,
    originalPrice: 1599,
    emoji: '⌚',
    bgColor: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    sales: 1890,
    tag: '新品'
  },
  {
    id: 201,
    name: '纯棉宽松T恤',
    desc: '2026新款 · 男女同款',
    price: 89,
    originalPrice: 159,
    emoji: '👕',
    bgColor: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    sales: 8340,
  },
  {
    id: 206,
    name: '透气运动跑鞋',
    desc: '轻量减震 · 回弹缓震',
    price: 499,
    originalPrice: 799,
    emoji: '👟',
    bgColor: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    sales: 3210,
    tag: '热销'
  },
  {
    id: 301,
    name: '北欧简约台灯',
    desc: '三档调光 · 无频闪',
    price: 129,
    originalPrice: 229,
    emoji: '💡',
    bgColor: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
    sales: 1560,
  },
  {
    id: 303,
    name: '316不锈钢保温杯',
    desc: '24小时保温 · 500ml',
    price: 79,
    originalPrice: 139,
    emoji: '🥤',
    bgColor: 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)',
    sales: 6780,
    tag: '限时'
  },
  {
    id: 305,
    name: '进口零食大礼包',
    desc: '20种美味 · 送礼首选',
    price: 199,
    originalPrice: 299,
    emoji: '🍫',
    bgColor: 'linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)',
    sales: 2450,
    tag: '新品'
  }
]

// 格式化销量：超过 10000 显示 "x.x万"
const formatSales = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

// 标签颜色映射
const tagClass = (tag?: string): string => {
  switch (tag) {
    case '热销': return 'tag-hot'
    case '新品': return 'tag-new'
    case '限时': return 'tag-time'
    default: return ''
  }
}

// 跳转商品详情（记录浏览历史）
const goDetail = (product: Product) => {
  recordView({
    id: product.id,
    name: product.name,
    emoji: product.emoji,
    bgColor: product.bgColor
  })
  router.push(`/product/${product.id}`)
}

// 加入购物车
const addToCart = (product: Product) => {
  cartAdd({
    id: product.id,
    name: product.name,
    price: product.price,
    emoji: product.emoji,
    bgColor: product.bgColor
  })
  console.log('已加入购物车:', product.name)
}
</script>

<template>
  <div class="home-container">
    <!-- 顶部标题行：左标题 + 右副标题 -->
    <div class="home-hero-head">
      <h1 class="home-hero-title">欢迎来到优选商城</h1>
      <p class="home-hero-desc">首页专属福利限时领，好货低价别错过</p>
    </div>

    <!-- 轮播图：4 个分类，点击整图跳转 -->
    <section
      class="home-carousel"
      @mouseenter="stopAutoPlay"
      @mouseleave="startAutoPlay"
    >
      <!-- 幻灯片（横向滑动） -->
      <div
        class="home-carousel-track"
        :style="{ transform: `translateX(-${currentBanner * 100}%)` }"
      >
        <div
          v-for="banner in banners"
          :key="banner.id"
          class="home-carousel-slide"
          :style="{ background: banner.bgGradient }"
          @click="onBannerClick(banner)"
        >
          <div class="home-carousel-text">
            <h2>{{ banner.title }}</h2>
            <p>{{ banner.subtitle }}</p>
          </div>
          <span class="home-carousel-emoji">{{ banner.emoji }}</span>
        </div>
      </div>

      <!-- 左右箭头（hover 显示） -->
      <button class="home-carousel-arrow left" @click.stop="prevBanner">‹</button>
      <button class="home-carousel-arrow right" @click.stop="nextBanner">›</button>

      <!-- 底部指示点 -->
      <div class="home-carousel-dots">
        <span
          v-for="(banner, index) in banners"
          :key="banner.id"
          class="home-carousel-dot"
          :class="{ active: currentBanner === index }"
          @click.stop="goBanner(index)"
        ></span>
      </div>
    </section>

    <!-- 热销商品网格 -->
    <section class="home-section">
      <h2 class="home-section-title">
        🔥 热销商品
        <button
          class="home-section-more"
          @click="router.push('/products')"
          title="查看全部商品"
        >查看全部 ›</button>
      </h2>
      <div class="home-product-grid">
        <div
          v-for="product in products"
          :key="product.id"
          class="home-product-card"
          @click="goDetail(product)"
        >
          <!-- 商品图片区（占位：渐变背景 + emoji） -->
          <div
            class="home-product-img"
            :style="{ background: product.bgColor }"
          >
            <span class="home-product-emoji">{{ product.emoji }}</span>
            <!-- 标签角标 -->
            <span
              v-if="product.tag"
              class="home-product-tag"
              :class="tagClass(product.tag)"
            >{{ product.tag }}</span>
          </div>

          <!-- 商品信息 -->
          <div class="home-product-info">
            <h3 class="home-product-name">{{ product.name }}</h3>
            <p class="home-product-desc">{{ product.desc }}</p>
            <div class="home-product-bottom">
              <div class="home-product-price-wrap">
                <span class="home-product-price">¥{{ product.price }}</span>
                <span class="home-product-original">¥{{ product.originalPrice }}</span>
              </div>
              <span class="home-product-sales">已售 {{ formatSales(product.sales) }}</span>
            </div>
            <!-- 加入购物车按钮 -->
            <button
              class="home-product-cart"
              @click.stop="addToCart(product)"
            >🛒 加入购物车</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ====== 首页容器 ====== */
.home-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 40px 16px;
}

@media (min-width: 640px) {
  .home-container {
    padding-left: 24px;
    padding-right: 24px;
  }
}

@media (min-width: 1024px) {
  .home-container {
    padding-left: 32px;
    padding-right: 32px;
  }
}

/* ====== 顶部标题行 ====== */
.home-hero-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

.home-hero-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}

.home-hero-desc {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

/* ====== 轮播图 ====== */
.home-carousel {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

/* 幻灯片轨道：横向排列，transform 控制位移 */
.home-carousel-track {
  display: flex;
  transition: transform 0.5s ease;
}

/* 单张幻灯片 */
.home-carousel-slide {
  flex: 0 0 100%;
  width: 100%;
  box-sizing: border-box;
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 72px;
  cursor: pointer;
}

.home-carousel-text h2 {
  margin: 0;
  font-size: 34px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 2px;
}

.home-carousel-text p {
  margin: 12px 0 0;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.9);
}

.home-carousel-emoji {
  font-size: 110px;
  filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.2));
  transition: transform 0.3s ease;
}

.home-carousel-slide:hover .home-carousel-emoji {
  transform: scale(1.1) rotate(-4deg);
}

/* 左右箭头：默认透明，hover 容器时显示 */
.home-carousel-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  font-size: 24px;
  line-height: 1;
  color: #ffffff;
  background-color: rgba(0, 0, 0, 0.25);
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.home-carousel-arrow.left { left: 16px; }
.home-carousel-arrow.right { right: 16px; }

.home-carousel:hover .home-carousel-arrow {
  opacity: 1;
}

.home-carousel-arrow:hover {
  background-color: rgba(0, 0, 0, 0.45);
}

/* 底部指示点 */
.home-carousel-dots {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 14px;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.home-carousel-dot {
  width: 8px;
  height: 8px;
  background-color: rgba(255, 255, 255, 0.5);
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.home-carousel-dot.active {
  width: 24px;
  background-color: #ffffff;
}

/* 移动端适配 */
@media (max-width: 640px) {
  .home-carousel-slide {
    flex-direction: column;
    justify-content: center;
    gap: 12px;
    min-height: 200px;
    padding: 24px;
    text-align: center;
  }

  .home-carousel-text h2 { font-size: 24px; }
  .home-carousel-emoji { font-size: 64px; }
}

/* ====== 热销商品区 ====== */
.home-section {
  margin-top: 32px;
}

.home-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

button.home-section-more {
  font-size: 14px;
  font-weight: 400;
  color: #6b7280;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  transition: color 0.15s ease, text-decoration 0.15s ease;
  font-family: inherit;
}
button.home-section-more:hover {
  color: #4f46e5;
  text-decoration: underline;
}

/* 商品网格：响应式 2/3/4 列 */
.home-product-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 640px) {
  .home-product-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1024px) {
  .home-product-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* 商品卡片 */
.home-product-card {
  background-color: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}

.home-product-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.12);
}

/* 商品图片区 */
.home-product-img {
  position: relative;
  width: 100%;
  padding-top: 100%; /* 1:1 宽高比 */
  display: flex;
  align-items: center;
  justify-content: center;
}

.home-product-emoji {
  position: absolute;
  top: 50%;
  left: 50%;
  font-size: 64px;
  transform: translate(-50%, -50%);
}

/* 标签角标 */
.home-product-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  border-radius: 9999px;
}

.tag-hot { background-color: #ef4444; }   /* 热销 - 红 */
.tag-new { background-color: #10b981; }   /* 新品 - 绿 */
.tag-time { background-color: #f59e0b; }  /* 限时 - 橙 */

/* 商品信息区 */
.home-product-info {
  padding: 12px 14px 14px;
}

.home-product-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-product-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-product-bottom {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 8px;
}

.home-product-price {
  font-size: 18px;
  font-weight: 700;
  color: #ef4444;
}

.home-product-original {
  margin-left: 6px;
  font-size: 12px;
  color: #9ca3af;
  text-decoration: line-through;
}

.home-product-sales {
  font-size: 11px;
  color: #9ca3af;
}

/* 加入购物车按钮 */
.home-product-cart {
  width: 100%;
  margin-top: 10px;
  padding: 6px 0;
  font-size: 12px;
  font-weight: 500;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.home-product-cart:hover {
  color: #ffffff;
  background-color: #4f46e5;
}
</style>
