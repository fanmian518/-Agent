<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken } from '@/api/request'
import { executeAgent, type AgentResponse } from '@/api/agent'
import { isLoggedIn } from '@/stores/user'
import { refreshCart } from '@/stores/cart'
import { refreshFavorites } from '@/stores/favorites'
import { refreshOrders } from '@/stores/orders'
import { refreshAddresses } from '@/stores/addresses'

interface ChatMessage { role: 'user' | 'agent'; text: string; data?: AgentResponse }
const open = ref(false)
const router = useRouter()
const input = ref('')
const sending = ref(false)
const sessionId = ref<string>()
const addressDialog = ref<{ show: boolean; addresses: any[] }>({ show: false, addresses: [] })
const messages = ref<ChatMessage[]>([{ role: 'agent', text: '你好，我可以帮你搜索商品、操作购物车和收藏夹，并创建待支付订单。' }])
const canSend = computed(() => input.value.trim().length > 0 && !sending.value)

function summarize(data: AgentResponse) {
  if (data.address_required) return data.address_required.message
  if (data.order_result) return `订单已创建：${data.order_result.order_id || ''}，请到订单页面选择支付方式。`
  if (data.cart_result) {
    const count = data.cart_result.count ?? data.cart_result.items?.length ?? (data.cart_result.product_id ? 1 : 0)
    if (data.action === 'cart_list') return `购物车中有 ${count} 件商品。`
    if (data.action === 'cart_clear') return '购物车已清空。'
    if (data.action === 'search_and_add_to_cart') return `操作成功，已将 ${count} 件商品加入购物车。`
    if (data.action === 'search_and_remove_from_cart') return `操作成功，已从购物车移除 ${count} 件商品。`
    return `购物车操作成功，共处理 ${count} 件商品。`
  }
  if (data.favorites_result) {
    const count = data.favorites_result.count ?? data.favorites_result.items?.length ?? (data.favorites_result.product_id ? 1 : 0)
    if (data.action === 'favorites_list') return `收藏夹中有 ${count} 件商品。`
    if (data.action === 'favorites_clear') return '收藏夹已清空。'
    if (data.action === 'search_and_add_to_favorites') return `操作成功，已收藏 ${count} 件商品。`
    if (data.action === 'search_and_remove_from_favorites') return `操作成功，已取消收藏 ${count} 件商品。`
    return `收藏夹操作成功，共处理 ${count} 件商品。`
  }
  // 精确匹配失败时，后端会同时返回 error 和相似商品列表。
  // 必须优先展示错误/推荐提示，避免把推荐商品误报为“已找到”。
  if (data.error) return data.error
  if (data.products?.length) return `找到 ${data.products.length} 件商品：${data.products.slice(0, 3).map(p => p.name).join('、')}`
  return data.error || '已完成处理。'
}

/** 显示 Agent 下单时返回的已有地址选择弹窗。 */
function showAddressDialog(data: AgentResponse) {
  const addresses = Array.isArray(data.address_required?.addresses)
    ? data.address_required.addresses
    : []
  addressDialog.value = { show: addresses.length > 0, addresses }
}

/** 点击地址选项时复用 Agent 会话提交“选择第 N 个地址”。 */
async function chooseAddress(index: number) {
  if (sending.value) return
  input.value = `选择第${index}个地址`
  await send()
}

async function send() {
  if (!canSend.value) return
  if (!isLoggedIn.value) {
    // 避免旧 Token 与当前用户状态不一致时绕过登录检查。
    clearToken()
    messages.value.push({ role: 'agent', text: '请先登录后再使用购物助手。' })
    router.push({ path: '/login', query: { redirect: '/' } })
    return
  }
  const text = input.value.trim(); input.value = ''; messages.value.push({ role: 'user', text }); sending.value = true
  try {
    const data = await executeAgent(text, sessionId.value)
    sessionId.value = data.session_id || sessionId.value
    if (data.address_required) showAddressDialog(data)
    if (data.order_result) addressDialog.value.show = false
    // Agent 的数据库操作不会自动触发 Vue store 更新，执行成功后重新拉取，
    // 确保购物车、收藏夹和订单页面立即显示后端的真实结果。
    if (data.cart_result) await refreshCart().catch(() => undefined)
    if (data.favorites_result) await refreshFavorites().catch(() => undefined)
    if (data.order_result) {
      await refreshOrders().catch(() => undefined)
      // 创建订单可能同时清理了购物车，订单操作完成后也必须同步购物车。
      await refreshCart().catch(() => undefined)
      await refreshAddresses().catch(() => undefined)
    }
    messages.value.push({ role: 'agent', text: summarize(data), data })
    const orderId = data.order_result?.order_id
    if (orderId) {
      // Agent 创建待支付订单后直接打开收银台，由用户选择支付方式并确认支付。
      await router.push({ path: '/checkout', query: { orderId } })
    }
  }
  catch (error: any) { messages.value.push({ role: 'agent', text: error?.message || '请求失败，请检查后端服务。' }) }
  finally { sending.value = false }
}
</script>

<template>
  <button class="agent-launcher" title="打开购物助手" @click="open = !open">⌕ <span>购物助手</span></button>
  <aside v-if="open" class="agent-panel">
    <header><strong>购物助手</strong><button title="关闭" @click="open = false">×</button></header>
    <div class="agent-messages">
      <div v-for="(message, index) in messages" :key="index" class="agent-message" :class="message.role">{{ message.text }}</div>
      <div v-if="sending" class="agent-message agent">正在处理…</div>
    </div>
    <form class="agent-compose" @submit.prevent="send"><input v-model="input" placeholder="例如：把5000元以下的手机加入购物车" /><button :disabled="!canSend">发送</button></form>
    <div v-if="addressDialog.show" class="address-dialog-mask">
      <section class="address-dialog" role="dialog" aria-modal="true" aria-label="选择收货地址">
        <header class="address-dialog-head">
          <strong>选择收货地址</strong>
          <button type="button" title="关闭" @click="addressDialog.show = false">×</button>
        </header>
        <p class="address-dialog-tip">请选择地址，或在聊天框中说“选择第几个地址”。</p>
        <button
          v-for="(address, index) in addressDialog.addresses"
          :key="address.id"
          type="button"
          class="address-option"
          :disabled="sending"
          @click="chooseAddress(index + 1)"
        >
          <span class="address-option-index">{{ index + 1 }}</span>
          <span class="address-option-body">
            <span class="address-option-name">{{ address.contact_name }} {{ address.phone }}</span>
            <span class="address-option-detail">
              {{ [address.province, address.city, address.district, address.street, address.community, address.note].filter(Boolean).join(' ') }}
            </span>
            <span v-if="address.is_default" class="address-default">默认地址</span>
          </span>
        </button>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.agent-launcher{position:fixed;right:24px;bottom:24px;z-index:50;border:0;border-radius:999px;background:#4f46e5;color:#fff;padding:12px 18px;box-shadow:0 8px 24px #312e8155;cursor:pointer}.agent-panel{position:fixed;right:24px;bottom:78px;width:360px;height:500px;z-index:50;background:#fff;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 16px 40px #11182733;display:flex;flex-direction:column;overflow:hidden}.agent-panel header{display:flex;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #eee}.agent-panel header button{border:0;background:transparent;font-size:22px;cursor:pointer}.agent-messages{flex:1;overflow:auto;padding:14px;background:#f8fafc}.agent-message{max-width:85%;padding:9px 11px;border-radius:10px;margin-bottom:10px;line-height:1.5;font-size:14px;white-space:pre-wrap}.agent-message.user{margin-left:auto;background:#4f46e5;color:#fff}.agent-message.agent{background:#fff;border:1px solid #e5e7eb;color:#1f2937}.agent-compose{display:flex;gap:8px;padding:12px;border-top:1px solid #eee}.agent-compose input{min-width:0;flex:1;border:1px solid #d1d5db;border-radius:6px;padding:9px}.agent-compose button{border:0;border-radius:6px;padding:0 14px;background:#4f46e5;color:#fff}.agent-compose button:disabled{opacity:.5}.address-dialog-mask{position:absolute;inset:0 0 66px;z-index:2;background:#0005;display:flex;align-items:center;justify-content:center;padding:14px}.address-dialog{width:100%;max-height:90%;overflow:auto;background:#fff;border-radius:10px;box-shadow:0 10px 30px #11182755;padding-bottom:8px}.address-dialog-head{display:flex;justify-content:space-between;align-items:center;padding:13px 15px;border-bottom:1px solid #e5e7eb}.address-dialog-head button{border:0;background:transparent;font-size:22px;cursor:pointer}.address-dialog-tip{margin:10px 14px;color:#6b7280;font-size:12px;line-height:1.5}.address-option{width:calc(100% - 20px);margin:5px 10px;display:flex;gap:10px;text-align:left;border:1px solid #e5e7eb;background:#fff;border-radius:8px;padding:10px;cursor:pointer}.address-option:hover{border-color:#4f46e5;background:#f5f3ff}.address-option:disabled{opacity:.6;cursor:wait}.address-option-index{flex:none;width:22px;height:22px;border-radius:50%;background:#4f46e5;color:#fff;text-align:center;line-height:22px;font-size:12px}.address-option-body{min-width:0;display:flex;flex-direction:column;gap:3px}.address-option-name{font-weight:600;color:#111827}.address-option-detail{color:#4b5563;font-size:12px;line-height:1.4;word-break:break-all}.address-default{align-self:flex-start;color:#4f46e5;font-size:11px}@media(max-width:600px){.agent-panel{right:12px;left:12px;bottom:72px;width:auto}.agent-launcher{right:12px;bottom:14px}}
</style>
