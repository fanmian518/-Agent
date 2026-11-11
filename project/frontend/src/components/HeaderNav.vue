<script setup lang="ts">
/**
 * HeaderNav.vue - 顶部全局导航栏
 * ----------------------------------------------------------------
 * 布局：左侧 Logo │ 中间搜索框 │ 右侧购物车图标 + 用户头像
 * 功能：搜索、跳转购物车、跳转登录/用户中心、显示登录状态
 * 样式：传统 CSS（scoped），sticky 吸顶 + 毛玻璃背景
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { isLoggedIn, currentUsername } from '@/stores/user'
import { useCart } from '@/stores/cart'
import { useFavorites } from '@/stores/favorites'

const router = useRouter()

/* ============ 响应式状态 ============ */

// 搜索关键字（双向绑定到输入框）
const searchKeyword = ref('')

// 购物车数量（接入 store）
const cart = useCart()
const cartCount = computed(() => cart.items.reduce((sum, i) => sum + i.quantity, 0))

// 收藏夹数量（接入 store）
const favorites = useFavorites()
const favCount = computed(() => favorites.items.length)

/* ============ 事件处理 ============ */

// 跳转搜索结果页（预留）
const handleSearch = () => {
  if (!searchKeyword.value.trim()) return
  // TODO: router.push({ path: '/search', query: { keyword: searchKeyword.value } })
  console.log('search:', searchKeyword.value)
}

// 跳转购物车页面
const handleCartClick = () => {
  router.push('/cart')
}

// 跳转收藏夹页面
const handleFavClick = () => {
  router.push('/favorites')
}

// 点击用户头像：已登录 → 用户中心；未登录 → 登录页
const handleUserClick = () => {
  if (isLoggedIn.value) {
    router.push('/profile')
  } else {
    router.push('/login')
  }
}
</script>

<template>
  <!-- 顶部导航容器：sticky 吸顶 + 毛玻璃背景 + 底部细线分隔 -->
  <header class="nav-header">
    <!-- 内容容器：限宽 1280px，居中，高 64px -->
    <div class="nav-inner">
      <!-- ====== 左侧 Logo ====== -->
      <a href="/" class="nav-logo" @click.prevent="router.push('/')">
        <!-- 购物袋 SVG 图标 -->
        <svg
          class="nav-logo-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="9" cy="21" r="1" />
          <circle cx="20" cy="21" r="1" />
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
        </svg>
        <span>优选商城</span>
      </a>

      <!-- ====== 中间搜索框 ====== -->
      <div class="nav-search-wrap">
        <!-- 相对定位容器，用于绝对定位搜索图标和按钮 -->
        <div class="nav-search-box">
          <!-- 搜索输入框：回车触发搜索 -->
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索商品、品牌、分类"
            class="nav-search-input"
            @keyup.enter="handleSearch"
          />
          <!-- 搜索图标（绝对定位在输入框左侧） -->
          <svg
            class="nav-search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <!-- 搜索按钮（绝对定位在输入框右侧） -->
          <button
            type="button"
            class="nav-search-btn"
            @click="handleSearch"
          >
            搜索
          </button>
        </div>
      </div>

      <!-- ====== 右侧操作区 ====== -->
      <div class="nav-actions">
        <!-- 收藏夹图标按钮（带数量红点） -->
        <button
          type="button"
          class="nav-fav-btn"
          aria-label="收藏夹"
          @click="handleFavClick"
        >
          <!-- 心形 SVG 图标 -->
          <svg
            class="nav-fav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
          <!-- 数量红点 -->
          <span v-if="favCount > 0" class="nav-fav-badge">
            {{ favCount > 99 ? '99+' : favCount }}
          </span>
        </button>

        <!-- 购物车图标按钮（带数量红点） -->
        <button
          type="button"
          class="nav-cart-btn"
          aria-label="购物车"
          @click="handleCartClick"
        >
          <!-- 购物车 SVG 图标 -->
          <svg
            class="nav-cart-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
          <!-- 数量红点：>0 显示，>99 显示 99+ -->
          <span
            v-if="cartCount > 0"
            class="nav-cart-badge"
          >
            {{ cartCount > 99 ? '99+' : cartCount }}
          </span>
        </button>

        <!-- 用户头像按钮 -->
        <button
          type="button"
          class="nav-user-btn"
          :class="{ logged: isLoggedIn }"
          :aria-label="isLoggedIn ? currentUsername : '登录'"
          @click="handleUserClick"
        >
          <!-- 头像图片（已登录显示真实头像，未登录显示占位） -->
          <img
            :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${isLoggedIn ? currentUsername : 'Guest'}`"
            :alt="isLoggedIn ? currentUsername : '登录'"
            class="nav-avatar"
          />
          <!-- 已登录显示用户名 -->
          <span v-if="isLoggedIn" class="nav-username">{{ currentUsername }}</span>
          <span v-else class="nav-login-tip">登录</span>
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
/* ====== 顶部导航栏 ====== */

/* 导航容器：sticky 吸顶 + 毛玻璃背景 */
.nav-header {
  position: sticky;
  top: 0;
  z-index: 50;
  width: 100%;
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid #f3f4f6;
}

/* 内容容器：限宽 1280px，居中，高 64px */
.nav-inner {
  max-width: 1280px;
  height: 64px;
  margin: 0 auto;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

@media (min-width: 640px) {
  .nav-inner {
    padding: 0 24px;
  }
}

@media (min-width: 1024px) {
  .nav-inner {
    padding: 0 32px;
  }
}

/* ====== Logo ====== */
.nav-logo {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #4f46e5;
  text-decoration: none;
}

.nav-logo-icon {
  width: 28px;
  height: 28px;
}

/* ====== 搜索框区域 ====== */
.nav-search-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
}

.nav-search-box {
  position: relative;
  width: 100%;
  max-width: 576px;
}

/* 搜索输入框 */
.nav-search-input {
  width: 100%;
  padding: 8px 80px 8px 40px;
  font-size: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  background-color: #f9fafb;
  outline: none;
  transition: all 0.15s ease;
}

.nav-search-input:focus {
  border-color: #818cf8;
  background-color: #ffffff;
  box-shadow: 0 0 0 2px rgba(165, 180, 252, 0.5);
}

/* 搜索图标（绝对定位在输入框左侧） */
.nav-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  width: 16px;
  height: 16px;
  color: #9ca3af;
  transform: translateY(-50%);
}

/* 搜索按钮（绝对定位在输入框右侧） */
.nav-search-btn {
  position: absolute;
  right: 4px;
  top: 50%;
  padding: 4px 16px;
  font-size: 12px;
  font-weight: 500;
  color: #ffffff;
  background-color: #4f46e5;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: background-color 0.15s ease;
  transform: translateY(-50%);
}

.nav-search-btn:hover {
  background-color: #4338ca;
}

/* ====== 右侧操作区 ====== */
.nav-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 收藏夹按钮 */
.nav-fav-btn {
  position: relative;
  padding: 8px;
  color: #4b5563;
  background: none;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-fav-btn:hover {
  color: #ec4899;
  background-color: #fdf2f8;
}

.nav-fav-icon {
  width: 22px;
  height: 22px;
}

/* 收藏夹数量红点 */
.nav-fav-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  background-color: #ec4899;
  border-radius: 9999px;
}

/* 购物车按钮 */
.nav-cart-btn {
  position: relative;
  padding: 8px;
  color: #4b5563;
  background: none;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-cart-btn:hover {
  color: #4f46e5;
  background-color: #f3f4f6;
}

.nav-cart-icon {
  width: 24px;
  height: 24px;
}

/* 购物车数量红点 */
.nav-cart-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  background-color: #ef4444;
  border-radius: 9999px;
}

/* 用户头像按钮 */
.nav-user-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px 2px 2px;
  background: none;
  border: 2px solid transparent;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-user-btn:hover {
  border-color: #c7d2fe;
  background-color: #f9fafb;
}

.nav-user-btn.logged {
  padding-right: 12px;
}

.nav-avatar {
  width: 32px;
  height: 32px;
  background-color: #f3f4f6;
  border-radius: 9999px;
}

.nav-username {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-login-tip {
  font-size: 13px;
  font-weight: 500;
  color: #4f46e5;
}
</style>
