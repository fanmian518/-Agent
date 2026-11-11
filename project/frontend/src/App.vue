<script setup lang="ts">
/**
 * App.vue - 应用根组件
 * ----------------------------------------------------------------
 * 全局布局：顶部固定导航 + 主内容区（路由出口） + 底部备案信息
 * 使用 flex 纵向布局确保 footer 始终贴底
 * 样式：传统 CSS（scoped）
 */
import { RouterView } from 'vue-router'
import HeaderNav from './components/HeaderNav.vue'
import AgentChat from './components/AgentChat.vue'
import { onMounted, watch } from 'vue'
import { loadProducts } from './stores/products'
import { refreshCart } from './stores/cart'
import { refreshFavorites } from './stores/favorites'
import { refreshOrders } from './stores/orders'
import { refreshCoupons } from './stores/coupons'
import { refreshReviews } from './stores/reviews'
import { refreshFollowedShops } from './stores/shops'
import { refreshHistory } from './stores/history'
import { isLoggedIn } from './stores/user'
import { clearToken } from './api/request'

/** 登录成功后同步所有属于当前用户的数据，确保进入页面时显示数据库真实状态。 */
const refreshUserScopedData = async () => {
  await Promise.all([
    refreshCart().catch(() => undefined),
    refreshFavorites().catch(() => undefined),
    refreshOrders().catch(() => undefined),
    refreshCoupons().catch(() => undefined),
    refreshReviews().catch(() => undefined),
    refreshFollowedShops().catch(() => undefined),
    refreshHistory().catch(() => undefined)
  ])
}

// 登录发生在 App 挂载之后时，补做一次用户数据同步。
watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) void refreshUserScopedData()
})

onMounted(async () => {
  // Token 和用户状态必须成对存在；清理旧 Token，避免未登录时读取其他用户数据。
  if (!isLoggedIn.value) clearToken()
  await loadProducts().catch(() => undefined)
  await refreshUserScopedData()
})
</script>

<template>
  <!-- 根容器：纵向 flex 布局，min-h-screen 保证至少占满视口高度 -->
  <div class="app-root">
    <!-- 顶部导航栏（sticky 吸顶） -->
    <HeaderNav />
    <AgentChat />

    <!-- 主内容区：flex-1 撑满剩余空间，内部渲染路由视图 -->
    <main class="app-main">
      <!-- 路由出口：v-slot 获取当前路由组件 -->
      <RouterView v-slot="{ Component }">
        <!--
          路由切换过渡动画：不使用 mode="out-in"
          - out-in 会先让旧组件完全离场（0.2s）后再入场新组件（0.2s）
            中间出现 0.4s 的主内容区空白，用户体验像"白屏/空白"
          - 去掉 mode 后，旧组件淡出 + 新组件淡入 同时进行（重叠过渡）
            配合 .fade-leave-active 的 position:absolute 脱离文档流，
            两者不会互相推挤，过渡平滑无空白闪烁
        -->
        <transition name="fade">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>

    <!-- 底部备案信息 -->
    <footer class="app-footer">
      <p>© 2026 优选商城</p>
    </footer>
  </div>
</template>

<style scoped>
/* ====== 应用根容器 ====== */
.app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f9fafb;
  color: #1f2937;
}

/* ====== 主内容区 ======
   position:relative 作为 .fade-leave-active 绝对定位的容器参照，
   保证路由过渡时离场组件的宽高与容器一致，不会错位
*/
.app-main {
  position: relative;
  flex: 1;
  width: 100%;
}

/* ====== 底部备案信息 ====== */
.app-footer {
  padding: 24px 0;
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  background-color: #ffffff;
  border-top: 1px solid #f3f4f6;
}

/* ====== 路由切换淡入淡出动画 ====== */

/*
  入场/离场过程中的过渡效果
  - .fade-leave-active 绝对定位脱离文档流：
    因为不使用 mode="out-in"，新老组件会同时存在于 DOM，
    把离场组件抽离出普通流后，入场组件直接占据正常位置，
    两者重叠过渡而不是把布局撑开/互相推挤
*/
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-leave-active {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  pointer-events: none; /* 过渡中拦截点击，避免用户误操作离场组件 */
}

/* 入场起点 / 离场终点：透明 */
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
