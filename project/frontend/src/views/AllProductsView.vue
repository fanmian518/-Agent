<script setup lang="ts">
/**
 * AllProductsView.vue - 全部商品「查看全部」页面
 * ----------------------------------------------------------------
 * 路由：/products
 * 入口：主界面 🔥 热销商品 右上角「查看全部 ›」
 * 功能：
 *   - 从 products store 读取全部商品（canonical 商品注册库）
 *   - 顶部：搜索框（商品名/副标题）、分类 Tab（全部/数码/穿搭/家具/新人/日用）
 *   - 排序：综合 / 销量 / 价格升序 / 价格降序 / 最新
 *   - 商品卡片网格：点击卡片跳详情，右下角按钮加入购物车
 *   - 空状态 + 返回首页
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { allProducts, getCategoryName, getProductById } from '@/stores/products'
import type { Product, ProductCategory } from '@/stores/products'
import { recordView } from '@/stores/history'
import { addToCart as cartAdd } from '@/stores/cart'

const router = useRouter()

// ====== 工具方法 ======
const formatSales = (num: number): string => {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toString()
}
const tagClass = (tag?: string): string => {
  switch (tag) {
    case '热销': return 'tag-hot'
    case '新品': return 'tag-new'
    case '限时': return 'tag-time'
    default: return ''
  }
}

// ====== 筛选与排序参数 ======
const keyword = ref('')
const activeCategory = ref<string>('all')   // all / digital / fashion / homegoods / newuser / daily
const sortKey = ref<'default' | 'sales' | 'priceAsc' | 'priceDesc' | 'newest'>('default')

const CATEGORIES: Array<{ key: string; label: string }> = [
  { key: 'all',        label: '全部' },
  { key: 'digital',    label: '📱 数码爆款' },
  { key: 'fashion',    label: '👕 潮流穿搭' },
  { key: 'homegoods',  label: '🛋️ 家具好物' },
  { key: 'newuser',    label: '🎁 新人专享' },
  { key: 'daily',      label: '🛍️ 日用百货' }
]

const SORTS: Array<{ key: typeof sortKey.value; label: string }> = [
  { key: 'default',   label: '综合排序' },
  { key: 'sales',     label: '销量优先' },
  { key: 'priceAsc',  label: '价格 ↑' },
  { key: 'priceDesc', label: '价格 ↓' },
  { key: 'newest',    label: '最新上架' }
]

// ====== 过滤后的商品列表 ======
const filteredProducts = computed<Product[]>(() => {
  let list = [...allProducts]

  // 分类过滤：按 id 百位数区分
  // 数码 1xx（100-199） 穿搭 2xx（200-299） 家具 3xx（300-399）
  // 新人 4xx（400-499） 日用 5xx（500-599）
  if (activeCategory.value !== 'all') {
    const [min, max] = ({
      digital:   [100, 199],
      fashion:   [200, 299],
      homegoods: [300, 399],
      newuser:   [400, 499],
      daily:     [500, 599]
    } as Record<string, [number, number]>)[activeCategory.value] ?? [0, 9999]
    list = list.filter(p => p.id >= min && p.id <= max)
  }

  // 关键词搜索（商品名 / 副标题）
  const kw = keyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(p =>
      p.name.toLowerCase().includes(kw) ||
      (p.desc ?? '').toLowerCase().includes(kw)
    )
  }

  // 排序
  switch (sortKey.value) {
    case 'sales':
      list.sort((a, b) => (b.sales ?? 0) - (a.sales ?? 0))
      break
    case 'priceAsc':
      list.sort((a, b) => a.price - b.price)
      break
    case 'priceDesc':
      list.sort((a, b) => b.price - a.price)
      break
    case 'newest':
      list.sort((a, b) => b.id - a.id)
      break
    default:
      // 综合：优先有 tag 的在前面，然后销量次排
      list.sort((a, b) => {
        const at = a.tag ? 1 : 0
        const bt = b.tag ? 1 : 0
        if (at !== bt) return bt - at
        return (b.sales ?? 0) - (a.sales ?? 0)
      })
  }
  return list
})

// 各分类商品数量
const categoryCount = computed<Record<string, number>>(() => {
  const m: Record<string, number> = { all: allProducts.length }
  for (const p of allProducts) {
    let k = 'all'
    if (p.id >= 100 && p.id <= 199) k = 'digital'
    else if (p.id >= 200 && p.id <= 299) k = 'fashion'
    else if (p.id >= 300 && p.id <= 399) k = 'homegoods'
    else if (p.id >= 400 && p.id <= 499) k = 'newuser'
    else if (p.id >= 500 && p.id <= 599) k = 'daily'
    if (k !== 'all') m[k] = (m[k] ?? 0) + 1
  }
  return m
})

// ====== 交互：跳转详情 / 加入购物车 ======
const goDetail = (p: Product) => {
  recordView({
    id: p.id,
    name: p.name,
    emoji: p.emoji,
    bgColor: p.bgColor
  })
  router.push(`/product/${p.id}`)
}
const addToCart = (p: Product) => {
  const full = getProductById(p.id) ?? p
  cartAdd(
    {
      id: full.id,
      name: full.name,
      price: full.price,
      emoji: full.emoji,
      bgColor: full.bgColor,
      desc: full.desc,
      originalPrice: full.originalPrice
    },
    1
  )
}
const goHome = () => router.push('/')

// 保证 getCategoryName 在模板内可用（all 不传给 getCategoryName；统一通过 activeCategory='all' 特殊处理）
const categoryName = (category: string) => {
  if (category === 'all') return '全部商品'
  return getCategoryName(category as ProductCategory)
}
</script>

<template>
  <div class="ap-page">
    <!-- 顶部面包屑 + 标题 -->
    <div class="ap-head">
      <div class="ap-crumbs">
        <a class="ap-crumb" @click="goHome">首页</a>
        <span class="ap-crumb-sep">›</span>
        <span class="ap-crumb cur">全部商品</span>
      </div>
      <h1 class="ap-title">🛍️ 全部商品</h1>
      <p class="ap-sub">共 {{ allProducts.length }} 款精选好物，点击卡片查看详情，或一键加入购物车</p>
    </div>

    <!-- 搜索 + 筛选 + 排序 工具条 -->
    <div class="ap-toolbar">
      <div class="ap-search-wrap">
        <input
          v-model="keyword"
          type="text"
          class="ap-search"
          placeholder="搜索商品名 / 副标题，如：耳机、保温"
        />
        <span class="ap-search-icon">🔍</span>
      </div>

      <div class="ap-sort-wrap">
        <span class="ap-sort-label">排序</span>
        <select v-model="sortKey" class="ap-sort">
          <option v-for="s in SORTS" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
      </div>
    </div>

    <!-- 分类 Tab -->
    <div class="ap-cats">
      <button
        v-for="c in CATEGORIES"
        :key="c.key"
        class="ap-cat-tab"
        :class="{ active: activeCategory === c.key }"
        @click="activeCategory = c.key"
      >
        {{ c.label }}
        <span
          class="ap-cat-count"
          v-if="(categoryCount[c.key] ?? 0) > 0"
        >{{ categoryCount[c.key] }}</span>
      </button>
    </div>

    <!-- 结果数量 + 当前分类名 -->
    <div class="ap-result-info">
      <span>
        当前分类：<b>{{ activeCategory === 'all' ? '全部商品' : categoryName(activeCategory) }}</b>
        ，共找到 <b>{{ filteredProducts.length }}</b> 件商品
      </span>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredProducts.length === 0" class="ap-empty">
      <span class="ap-empty-icon">🔍</span>
      <p class="ap-empty-title">暂无符合条件的商品</p>
      <p class="ap-empty-desc">试试换个关键词、切换分类或清除排序</p>
      <div class="ap-empty-btns">
        <button class="btn-ghost" @click="() => { keyword = ''; activeCategory = 'all'; sortKey = 'default' }">重置条件</button>
        <button class="btn-primary" @click="goHome">返回首页</button>
      </div>
    </div>

    <!-- 商品网格 -->
    <div v-else class="ap-grid">
      <div
        v-for="p in filteredProducts"
        :key="p.id"
        class="ap-card"
        @click="goDetail(p)"
      >
        <!-- 图 -->
        <div
          class="ap-card-img"
          :style="{ background: p.bgColor }"
        >
          <span class="ap-card-emoji">{{ p.emoji }}</span>
          <span
            v-if="p.tag"
            class="ap-card-tag"
            :class="tagClass(p.tag)"
          >{{ p.tag }}</span>
          <span
            v-if="(p.originalPrice ?? 0) > p.price"
            class="ap-card-discount"
          >省 ¥{{ ((p.originalPrice ?? 0) - p.price).toFixed(0) }}</span>
        </div>
        <!-- 信息 -->
        <div class="ap-card-info">
          <h3 class="ap-card-name" :title="p.name">{{ p.name }}</h3>
          <p class="ap-card-desc" :title="p.desc">{{ p.desc }}</p>
          <div class="ap-card-bottom">
            <div class="ap-card-price-wrap">
              <span class="ap-card-price">¥{{ p.price.toFixed(2) }}</span>
              <span v-if="(p.originalPrice ?? 0) > p.price" class="ap-card-original">
                ¥{{ (p.originalPrice ?? 0).toFixed(2) }}
              </span>
            </div>
            <span class="ap-card-sales">已售 {{ formatSales(p.sales ?? 0) }}</span>
          </div>
          <button
            class="ap-card-cart"
            @click.stop="addToCart(p)"
          >🛒 加入购物车</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ========== 复用按钮 ========== */
.btn-primary {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  background: #4f46e5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-primary:hover { background: #4338ca; }
.btn-ghost {
  padding: 9px 18px;
  font-size: 14px;
  color: #6b7280;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-ghost:hover { color: #4f46e5; border-color: #c7d2fe; }

/* ========== 容器 ========== */
.ap-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 16px 60px;
}

/* 头部 */
.ap-head { margin-bottom: 14px; }
.ap-crumbs {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #9ca3af;
  margin-bottom: 10px;
}
.ap-crumb {
  color: #6b7280;
  cursor: pointer;
  transition: color 0.15s ease;
}
.ap-crumb:hover { color: #4f46e5; }
.ap-crumb.cur { color: #111827; cursor: default; }
.ap-crumb-sep { color: #d1d5db; }

.ap-title {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.5px;
}
.ap-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

/* 工具条 */
.ap-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.ap-search-wrap {
  position: relative;
  flex: 1;
  min-width: 240px;
  max-width: 520px;
}
.ap-search {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 38px 10px 14px;
  font-size: 14px;
  color: #111827;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  outline: none;
  transition: all 0.15s ease;
}
.ap-search:focus { border-color: #818cf8; box-shadow: 0 0 0 3px #e0e7ff; }
.ap-search-icon {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  color: #9ca3af;
  pointer-events: none;
}

.ap-sort-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ap-sort-label { font-size: 13px; color: #6b7280; }
.ap-sort {
  padding: 8px 12px;
  font-size: 13px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s ease;
}
.ap-sort:focus { border-color: #818cf8; }

/* 分类 Tab */
.ap-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px;
  margin-bottom: 12px;
  background: #f9fafb;
  border-radius: 10px;
}
.ap-cat-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  font-size: 13px;
  color: #6b7280;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}
.ap-cat-tab:hover { color: #4f46e5; }
.ap-cat-tab.active {
  background: #fff;
  color: #4f46e5;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.ap-cat-count {
  display: inline-block;
  min-width: 18px;
  padding: 0 6px;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  color: #fff;
  background: #6366f1;
  border-radius: 9999px;
}
.ap-cat-tab.active .ap-cat-count { background: #ef4444; }

/* 结果信息条 */
.ap-result-info {
  padding: 8px 14px;
  margin-bottom: 14px;
  font-size: 12px;
  color: #4b5563;
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border-radius: 8px;
}
.ap-result-info b { color: #1f2937; font-weight: 600; }

/* 空状态 */
.ap-empty {
  padding: 80px 24px;
  text-align: center;
  background: #fff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
}
.ap-empty-icon { display: block; font-size: 60px; margin-bottom: 10px; opacity: 0.8; }
.ap-empty-title { margin: 0 0 6px; font-size: 18px; font-weight: 600; color: #1f2937; }
.ap-empty-desc { margin: 0 0 22px; font-size: 13px; color: #9ca3af; }
.ap-empty-btns { display: flex; gap: 12px; justify-content: center; }

/* 商品卡片网格 */
.ap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
@media (max-width: 540px) {
  .ap-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
}

.ap-card {
  background: #fff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.18s ease;
}
.ap-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 10px 26px rgba(79, 70, 229, 0.12);
  transform: translateY(-2px);
}

.ap-card-img {
  position: relative;
  aspect-ratio: 1 / 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.ap-card-emoji {
  font-size: 58px;
  transition: transform 0.18s ease;
  transform: scale(1);
  filter: drop-shadow(0 6px 12px rgba(0,0,0,0.15));
}
.ap-card:hover .ap-card-emoji { transform: scale(1.1); }

.ap-card-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  border-radius: 9999px;
  letter-spacing: 0.5px;
}
.tag-hot  { background: #ef4444; }
.tag-new  { background: #10b981; }
.tag-time { background: #f59e0b; }

.ap-card-discount {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border-radius: 9999px;
}

.ap-card-info { padding: 10px 12px 12px; }
.ap-card-name {
  margin: 0 0 3px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 39px;
}
.ap-card-desc {
  margin: 0 0 8px;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ap-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.ap-card-price-wrap { display: flex; align-items: baseline; gap: 6px; }
.ap-card-price {
  font-size: 18px;
  font-weight: 800;
  color: #ef4444;
  line-height: 1;
}
.ap-card-original {
  font-size: 12px;
  color: #9ca3af;
  text-decoration: line-through;
}
.ap-card-sales { font-size: 11px; color: #9ca3af; }

.ap-card-cart {
  width: 100%;
  padding: 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: #4f46e5;
  background: #eef2ff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ap-card-cart:hover { background: #4f46e5; color: #fff; }
</style>
