/**
 * router/index.ts - Vue Router 路由配置（SPA 前端路由）
 * ----------------------------------------------------------------
 * 路由表 + 全局导航守卫
 *  meta 字段说明：
 *    meta.requiresAuth  true → 用户必须登录；否则重定向到 /login?redirect=原路径
 *    meta.noAuth        true → 登录状态下访问（登录/注册）自动踢到 /profile（用户中心）
 * 滚动行为：普通跳转 smooth 滚回页面顶部；浏览器前进/后退还原用户滚动位置
 *           （修复从商品详情滚动到底部再回首页看到"空白"的问题）
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { isLoggedIn } from '@/stores/user'

/**
 * 路由表
 *  全部按需动态 import，保证首屏只加载 HomeView 的 bundle。
 *  新增页面时请保持路由的"语义化名字 + 注释入口"惯例。
 */
const routes: RouteRecordRaw[] = [
  // 首页
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue')
  },
  // 购物车（HeaderNav 购物车图标、ProfileView 购物车 Tab 复用同一个组件入口）
  {
    path: '/cart',
    name: 'cart',
    component: () => import('@/views/CartView.vue'),
    meta: { requiresAuth: true }
  },
  // 收藏夹（HeaderNav ❤️ 图标；ProfileView 也有 Tab 但用的是内嵌面板，不是路由）
  {
    path: '/favorites',
    name: 'favorites',
    component: () => import('@/views/FavoritesView.vue'),
    meta: { requiresAuth: true }
  },
  // 全部商品「查看全部」—— 入口：首页 🔥 热销商品 右上 "查看全部 ›"
  {
    path: '/products',
    name: 'allProducts',
    component: () => import('@/views/AllProductsView.vue')
  },
  // 收银台 / 付款跳转页：/checkout?orderId=订单号
  //  调用方：CartView "去结算"、ProductDetailView "立即购买" → createOrder → 携带 orderId 跳转
  {
    path: '/checkout',
    name: 'checkout',
    component: () => import('@/views/CheckoutView.vue'),
    meta: { requiresAuth: true }  // 未登录不允许进入付款
  },
  // 商品详情页（首页卡片 / 分类页 / 全部商品页 / 浏览历史 Tab 都会跳转进来）
  {
    path: '/product/:id',
    name: 'product',
    component: () => import('@/views/product/ProductDetailView.vue')
  },
  // 四个分类页共用 CategoryView.vue 一个组件（props: true 把 :category 作为组件 props 传入）
  //  /category/digital | /category/fashion | /category/homegoods | /category/newuser
  {
    path: '/category/:category',
    name: 'category',
    component: () => import('@/views/category/CategoryView.vue'),
    props: true
  },
  // 登录页（HeaderNav 未登录头像；路由守卫 requiresAuth 重定向）
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { noAuth: true }  // 已登录用户访问登录页 → 自动跳 /profile
  },
  // 注册页（登录页底部 "没有账号？立即注册" 链接进来）
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { noAuth: true }
  },
  // 用户中心（路由守卫鉴权；HeaderNav 登录头像；支持 ?tab=xxx 直接切到指定 Tab）
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  /**
   * 滚动行为控制：
   *  - 浏览器前进/后退（savedPosition 存在）：还原用户上次滚动位置
   *  - 普通路由跳转（点击 Logo / 跳转按钮 / router.push）：滚到页面顶部
   *  避免从商品详情页（滚动到底部看评价）回到首页时，
   *  停留在 y>0 的位置导致首页内容区看起来"空白"
   */
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0, behavior: 'smooth' }
  }
})

// ====== 路由守卫 ======
router.beforeEach((to) => {
  // 需要登录但未登录 → 跳转登录页
  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  // 已登录访问登录/注册页 → 跳转用户中心
  if (to.meta.noAuth && isLoggedIn.value) {
    return { path: '/profile' }
  }
})

export default router
