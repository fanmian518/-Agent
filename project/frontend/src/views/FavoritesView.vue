<script setup lang="ts">
/**
 * FavoritesView.vue - 独立收藏夹页面
 * ----------------------------------------------------------------
 * 功能：查看收藏 / 取消收藏 / 加入购物车 / 点击跳转详情
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useFavorites, removeFromFavorite } from '@/stores/favorites'
import { addToCart } from '@/stores/cart'

const router = useRouter()
const favorites = useFavorites()

// 取消收藏确认弹窗：存储待取消的商品 ID，null 表示不显示
const pendingRemoveId = ref<number | null>(null)

const formatTime = (ts: number) => {
  const d = new Date(ts)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const goDetail = (id: number) => router.push(`/product/${id}`)

const handleAddCart = (item: { id: number; name: string; price: number; emoji: string; bgColor: string }) => {
  addToCart(item)
}

// 点击"取消收藏"按钮 → 弹出确认弹窗
const handleRemove = (id: number) => {
  pendingRemoveId.value = id
}

// 确认取消收藏
const confirmRemove = () => {
  if (pendingRemoveId.value !== null) {
    removeFromFavorite(pendingRemoveId.value)
    pendingRemoveId.value = null
  }
}

// 取消（关闭弹窗，不操作）
const cancelRemove = () => {
  pendingRemoveId.value = null
}

const goHome = () => router.push('/')
const goCart = () => router.push('/cart')
</script>

<template>
  <div class="fav-page">
    <button class="fav-back" @click="goHome">← 返回首页</button>

    <div class="fav-header">
      <h1>❤️ 收藏夹</h1>
      <span class="fav-count">全部收藏 ({{ favorites.items.length }})</span>
    </div>

    <!-- 空状态 -->
    <div v-if="favorites.items.length === 0" class="fav-empty">
      <span class="fav-empty-icon">❤️</span>
      <p>收藏夹空空如也，去挑点好物吧～</p>
      <button class="fav-btn-primary" @click="goHome">去逛逛</button>
    </div>

    <!-- 收藏列表 -->
    <div v-else class="fav-list">
      <div v-for="item in favorites.items" :key="item.id" class="fav-item">
        <div class="fav-item-img" :style="{ background: item.bgColor }" @click="goDetail(item.id)">
          <span>{{ item.emoji }}</span>
        </div>
        <div class="fav-item-info" @click="goDetail(item.id)">
          <h3 class="fav-item-name">{{ item.name }}</h3>
          <div class="fav-item-price">¥{{ item.price }}</div>
          <div class="fav-item-time">收藏于 {{ formatTime(item.addedAt) }}</div>
        </div>
        <div class="fav-item-actions">
          <button class="fav-btn cart" @click="handleAddCart(item)">🛒 加购</button>
          <button class="fav-btn danger" @click="handleRemove(item.id)">取消收藏</button>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <div v-if="favorites.items.length > 0" class="fav-footer">
      <span class="fav-footer-tip">💡 点击商品可查看详情</span>
      <button class="fav-btn-primary" @click="goCart">去购物车 ›</button>
    </div>

    <!-- ====== 取消收藏确认弹窗 ====== -->
    <div v-if="pendingRemoveId !== null" class="modal-mask" @click.self="cancelRemove">
      <div class="modal">
        <p class="modal-text">确定要取消收藏该商品吗？</p>
        <div class="modal-actions">
          <button class="btn-ghost" @click="cancelRemove">否</button>
          <button class="btn-primary danger" @click="confirmRemove">是</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fav-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}

.fav-back {
  margin-bottom: 14px;
  padding: 6px 14px;
  font-size: 13px;
  color: #4f46e5;
  background-color: #eef2ff;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
}

.fav-back:hover { background-color: #e0e7ff; }

.fav-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.fav-header h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
}

.fav-count { font-size: 13px; color: #6b7280; }

.fav-empty {
  padding: 80px 0;
  text-align: center;
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
}

.fav-empty-icon { display: block; font-size: 60px; margin-bottom: 14px; }

.fav-empty p { margin: 0 0 22px; color: #9ca3af; }

.fav-list {
  background: #ffffff;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  overflow: hidden;
}

.fav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.fav-item:last-child { border-bottom: none; }

.fav-item-img {
  width: 76px;
  height: 76px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 38px;
  cursor: pointer;
  flex-shrink: 0;
}

.fav-item-info { flex: 1; min-width: 0; cursor: pointer; }

.fav-item-name {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-item-name:hover { color: #4f46e5; }

.fav-item-price {
  margin-top: 6px;
  font-size: 16px;
  font-weight: 700;
  color: #ef4444;
}

.fav-item-time { margin-top: 4px; font-size: 12px; color: #9ca3af; }

.fav-item-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.fav-btn {
  padding: 6px 16px;
  font-size: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.fav-btn.cart { color: #4f46e5; background-color: #eef2ff; }
.fav-btn.cart:hover { color: #fff; background-color: #4f46e5; }

.fav-btn.danger { color: #ef4444; background-color: #fee2e2; }
.fav-btn.danger:hover { color: #fff; background-color: #ef4444; }

.fav-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 18px;
  padding: 14px 16px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 10px;
}

.fav-footer-tip { font-size: 13px; color: #92400e; }

.fav-btn-primary {
  padding: 10px 24px;
  font-size: 14px;
  color: #ffffff;
  background-color: #4f46e5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.fav-btn-primary:hover { background-color: #4338ca; }

/* ====== 通用按钮样式 ====== */
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
