<script setup lang="ts">
/**
 * CategoryView.vue - 通用分类页
 * ----------------------------------------------------------------
 * 路由：/category/:category（四个分类共用）
 *   digital   数码爆款（科技蓝）
 *   fashion   潮流穿搭（浪漫粉）
 *   homegoods 家居好物（温暖橙）
 *   newuser   新人专享（喜庆红）
 * 功能：主题横幅 / 排序筛选 / 商品网格 / 点击跳详情 / 加购
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getProductsByCategory, CATEGORY_NAMES, formatSales } from '@/stores/products'
import type { Product, ProductCategory } from '@/stores/products'
import { addToCart } from '@/stores/cart'
import { recordView } from '@/stores/history'

const props = defineProps<{ category: ProductCategory }>()

const router = useRouter()

/** 分类主题配置 */
const THEMES: Record<ProductCategory, { banner: string; icon: string; title: string; subtitle: string }> = {
  digital: {
    banner: 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)',
    icon: '📱',
    title: '数码爆款',
    subtitle: '科技好物 · 智享未来'
  },
  fashion: {
    banner: 'linear-gradient(135deg, #f472b6 0%, #fb7185 100%)',
    icon: '👗',
    title: '潮流穿搭',
    subtitle: '时尚精品 · 穿出个性'
  },
  homegoods: {
    banner: 'linear-gradient(135deg, #f59e0b 0%, #f97316 100%)',
    icon: '🏠',
    title: '家居好物',
    subtitle: '品质生活 · 温馨之家'
  },
  newuser: {
    banner: 'linear-gradient(135deg, #ef4444 0%, #f97316 100%)',
    icon: '🎁',
    title: '新人专享',
    subtitle: '专属福利 · 限时特惠'
  },
  daily: {
    banner: 'linear-gradient(135deg, #64748b 0%, #334155 100%)',
    icon: '🧺',
    title: '品质百货',
    subtitle: '精选好物 · 天天低价'
  }
}

const theme = computed(() => THEMES[props.category] ?? THEMES.digital)

/** 当前分类商品 */
const items = computed(() => getProductsByCategory(props.category))

/** 排序方式 */
const sortType = ref<'default' | 'sales' | 'priceAsc' | 'priceDesc'>('default')

const sorted = computed(() => {
  const list = [...items.value]
  switch (sortType.value) {
    case 'sales': return list.sort((a, b) => b.sales - a.sales)
    case 'priceAsc': return list.sort((a, b) => a.price - b.price)
    case 'priceDesc': return list.sort((a, b) => b.price - a.price)
    default: return list
  }
})

const sortOptions: Array<{ key: typeof sortType.value; label: string }> = [
  { key: 'default', label: '综合' },
  { key: 'sales', label: '销量' },
  { key: 'priceAsc', label: '价格↑' },
  { key: 'priceDesc', label: '价格↓' }
]

/** 点击卡片 → 记录历史并跳转详情 */
const goDetail = (p: Product) => {
  recordView({ id: p.id, name: p.name, emoji: p.emoji, bgColor: p.bgColor })
  router.push(`/product/${p.id}`)
}

/** 加购（阻止冒泡，不跳转） */
const handleAddCart = (p: Product) => {
  addToCart({
    id: p.id,
    name: p.name,
    desc: p.desc,
    price: p.price,
    emoji: p.emoji,
    bgColor: p.bgColor
  })
}

const goHome = () => router.push('/')
</script>

<template>
  <div class="cat-page">
    <!-- 返回首页 -->
    <button class="cat-back" @click="goHome">← 返回首页</button>

    <!-- 主题横幅 -->
    <div class="cat-banner" :style="{ background: theme.banner }">
      <span class="cat-banner-icon">{{ theme.icon }}</span>
      <div class="cat-banner-text">
        <h1>{{ theme.title }}</h1>
        <p>{{ theme.subtitle }}</p>
      </div>
      <span class="cat-banner-count">共 {{ items.length }} 件好物</span>
    </div>

    <!-- 排序栏 -->
    <div class="cat-toolbar">
      <button
        v-for="opt in sortOptions"
        :key="opt.key"
        class="cat-sort-btn"
        :class="{ on: sortType === opt.key }"
        @click="sortType = opt.key"
      >{{ opt.label }}</button>
      <span class="cat-toolbar-tip">💡 点击商品查看详情</span>
    </div>

    <!-- 商品网格 -->
    <div class="cat-grid">
      <div
        v-for="p in sorted"
        :key="p.id"
        class="cat-card"
        @click="goDetail(p)"
      >
        <div class="cat-card-img" :style="{ background: p.bgColor }">
          <span>{{ p.emoji }}</span>
          <span v-if="p.tag" class="cat-card-tag" :class="`tag-${p.tag}`">{{ p.tag }}</span>
        </div>
        <div class="cat-card-info">
          <h3 class="cat-card-name">{{ p.name }}</h3>
          <p class="cat-card-desc">{{ p.desc }}</p>
          <div class="cat-card-bottom">
            <div>
              <span class="cat-card-price">¥{{ p.price }}</span>
              <span v-if="p.originalPrice" class="cat-card-origin">¥{{ p.originalPrice }}</span>
            </div>
            <button class="cat-card-add" @click.stop="handleAddCart(p)">+ 购物车</button>
          </div>
          <div class="cat-card-sales">已售 {{ formatSales(p.sales) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cat-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}

.cat-back {
  margin-bottom: 14px;
  padding: 6px 14px;
  font-size: 13px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}

.cat-back:hover { background-color: #e0e7ff; }

/* 横幅 */
.cat-banner {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 28px 32px;
  border-radius: 16px;
  color: #ffffff;
  margin-bottom: 18px;
}

.cat-banner-icon { font-size: 48px; }

.cat-banner-text { flex: 1; }

.cat-banner-text h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.cat-banner-text p {
  margin: 6px 0 0;
  font-size: 13px;
  opacity: 0.9;
}

.cat-banner-count {
  font-size: 13px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 9999px;
}

/* 排序栏 */
.cat-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.cat-sort-btn {
  padding: 6px 18px;
  font-size: 13px;
  color: #6b7280;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  cursor: pointer;
}

.cat-sort-btn.on {
  color: #ffffff;
  background-color: #4f46e5;
  border-color: #4f46e5;
}

.cat-toolbar-tip {
  margin-left: auto;
  font-size: 12px;
  color: #9ca3af;
}

/* 商品网格 */
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1024px) { .cat-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 640px) { .cat-grid { grid-template-columns: repeat(2, 1fr); } }

.cat-card {
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.08);
}

.cat-card-img {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64px;
}

.cat-card-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #ffffff;
  border-radius: 9999px;
}

.tag-热销 { background: #ef4444; }
.tag-新品 { background: #10b981; }
.tag-限时 { background: #f59e0b; }
.tag-新人价 { background: #ec4899; }

.cat-card-info { padding: 12px 14px 14px; }

.cat-card-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cat-card-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #9ca3af;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cat-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.cat-card-price {
  font-size: 17px;
  font-weight: 700;
  color: #ef4444;
}

.cat-card-origin {
  margin-left: 6px;
  font-size: 11px;
  color: #c7c7c7;
  text-decoration: line-through;
}

.cat-card-add {
  padding: 5px 12px;
  font-size: 12px;
  color: #ffffff;
  background: linear-gradient(135deg, #fb923c, #f97316);
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}

.cat-card-add:hover { opacity: 0.85; }

.cat-card-sales {
  margin-top: 8px;
  font-size: 11px;
  color: #9ca3af;
}
</style>
