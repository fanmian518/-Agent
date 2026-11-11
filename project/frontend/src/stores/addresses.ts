/**
 * stores/addresses.ts - 用户地址管理
 * ----------------------------------------------------------------
 * 按当前登录用户做数据隔离，持久化到 localStorage
 * 功能：新增 / 编辑 / 删除 / 设为默认 / 取默认地址 / 取当前用户地址列表
 */
import { reactive, watch, computed } from 'vue'
import { currentUsername, isLoggedIn } from '@/stores/user'
import { apiGetAddressList, apiCreateAddress, apiDeleteAddress, apiSetDefaultAddress } from '@/api/address'

export interface Address {
  id: string             // 地址 ID
  name: string           // 收货人姓名
  phone: string          // 手机号
  region: string         // 省市区（简化：一行文本，如"江苏省 徐州市 云龙区"）
  detail: string         // 详细地址（街道、楼号、门牌）
  isDefault: boolean     // 是否为默认地址（同一用户同一时间只能一个 true）
  createdAt: number
  updatedAt: number
}

// localStorage 键：整个地址表（多用户）存在一个 key 里
const STORAGE_KEY = 'shop_addresses'

type AddressDB = Record<string, Address[]>  // username -> addresses

const loadDB = (): AddressDB => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}
const saveDB = (db: AddressDB) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(db))
}

// 生成地址 ID：毫秒时间 + 4 位随机，避免用户操作过快重复
const genId = () => `${Date.now()}${Math.floor(Math.random() * 10000).toString().padStart(4, '0')}`

/** 响应式容器：当前登录用户的地址列表；未登录 = [] */
const state = reactive<{ list: Address[] }>({ list: [] })

/** 从 DB 重新加载当前用户的地址列表 */
const reloadCurrentUser = () => {
  if (!isLoggedIn.value) {
    state.list.splice(0, state.list.length)
    return
  }
  const db = loadDB()
  const mine = db[currentUsername.value] ?? []
  // 让默认地址排在最前面，然后按更新时间倒序
  mine.sort((a, b) => {
    if (a.isDefault !== b.isDefault) return a.isDefault ? -1 : 1
    return b.updatedAt - a.updatedAt
  })
  state.list.splice(0, state.list.length, ...mine)
}

/** 优先从后端地址表刷新，失败时保留本地兼容数据。 */
export async function refreshAddresses() {
  if (!isLoggedIn.value) return
  const username = currentUsername.value
  try {
    const result = await apiGetAddressList()
    if (!isLoggedIn.value || currentUsername.value !== username) {
      state.list.splice(0, state.list.length)
      return
    }
    const rows = (result as any).addresses ?? result
    state.list.splice(0, state.list.length, ...(rows as any[]).map(row => ({
      id: String(row.id), name: row.contact_name, phone: row.phone,
      region: [row.province, row.city, row.district].filter(Boolean).join(' '),
      detail: [row.street, row.community, row.note].filter(Boolean).join(' '),
      isDefault: row.is_default, createdAt: Date.parse(row.last_used_at ?? '') || Date.now(), updatedAt: Date.parse(row.last_used_at ?? '') || Date.now()
    })))
  } catch { /* 后端不可用时继续使用本地兼容数据 */ }
}

// 首次加载 + 登录/登出切换都要重载
reloadCurrentUser()
watch([currentUsername, isLoggedIn], () => { reloadCurrentUser(); refreshAddresses() })
refreshAddresses()

/** 当前用户的默认地址 */
export const defaultAddress = computed<Address | null>(() =>
  state.list.find(a => a.isDefault) ?? state.list[0] ?? null
)

/** 当前用户的所有地址（响应式） */
export function useAddresses() {
  return state
}

/** 新增地址 */
export function addAddress(
  data: Omit<Address, 'id' | 'createdAt' | 'updatedAt' | 'isDefault'> & { isDefault?: boolean }
): { ok: boolean; msg: string } {
  if (!isLoggedIn.value) return { ok: false, msg: '请先登录' }
  const val = validate(data)
  if (!val.ok) return { ok: false, msg: val.msg }
  const regionParts = data.region.trim().split(/\s+/)
  apiCreateAddress({ contact_name: data.name.trim(), phone: data.phone.trim(), province: regionParts[0] || '', city: regionParts[1] || regionParts[0] || '', district: regionParts[2] || regionParts[1] || regionParts[0] || '', community: data.detail.trim(), note: undefined, is_default: Boolean(data.isDefault) }).then(() => refreshAddresses()).catch(() => undefined)

  const username = currentUsername.value
  const db = loadDB()
  const mine = db[username] ?? []

  const newAddr: Address = {
    id: genId(),
    name: data.name.trim(),
    phone: data.phone.trim(),
    region: data.region.trim(),
    detail: data.detail.trim(),
    isDefault: Boolean(data.isDefault) || mine.length === 0, // 第一条地址自动设默认
    createdAt: Date.now(),
    updatedAt: Date.now()
  }
  // 若用户要设默认 → 先把该用户其它地址全部取消默认
  if (newAddr.isDefault) {
    mine.forEach(a => { a.isDefault = false })
  }
  mine.unshift(newAddr)
  db[username] = mine
  saveDB(db)
  reloadCurrentUser()
  return { ok: true, msg: '地址添加成功' }
}

/** 编辑地址 */
export function updateAddress(
  id: string,
  data: Partial<Omit<Address, 'id' | 'createdAt' | 'updatedAt'>>
): { ok: boolean; msg: string } {
  if (!isLoggedIn.value) return { ok: false, msg: '请先登录' }
  const username = currentUsername.value
  const db = loadDB()
  const mine = db[username] ?? []
  const idx = mine.findIndex(a => a.id === id)
  if (idx < 0) return { ok: false, msg: '地址不存在' }

  const merged = { ...mine[idx], ...data }
  // 若本次更新涉及关键字段，则校验
  if (data.name !== undefined || data.phone !== undefined ||
      data.region !== undefined || data.detail !== undefined) {
    const val = validate(merged)
    if (!val.ok) return { ok: false, msg: val.msg }
  }

  // 若改默认 → 把其它的全部取消默认
  if (data.isDefault === true) {
    mine.forEach(a => { a.isDefault = false })
  }
  mine[idx] = {
    ...merged,
    id: mine[idx].id,
    createdAt: mine[idx].createdAt,
    updatedAt: Date.now()
  } as Address
  db[username] = mine
  saveDB(db)
  reloadCurrentUser()
  return { ok: true, msg: '地址更新成功' }
}

/** 删除地址 */
export function deleteAddress(id: string): { ok: boolean; msg: string } {
  if (!isLoggedIn.value) return { ok: false, msg: '请先登录' }
  const username = currentUsername.value
  const db = loadDB()
  const mine = db[username] ?? []
  const target = mine.find(a => a.id === id)
  if (!target) return { ok: false, msg: '地址不存在' }
  apiDeleteAddress(id).then(() => refreshAddresses()).catch(() => undefined)
  const wasDefault = target.isDefault
  const next = mine.filter(a => a.id !== id)
  // 若删的是默认地址，且列表里还有地址，把剩余第一个自动升为默认
  if (wasDefault && next.length > 0) {
    next[0].isDefault = true
    next[0].updatedAt = Date.now()
  }
  db[username] = next
  saveDB(db)
  reloadCurrentUser()
  return { ok: true, msg: '地址已删除' }
}

/** 设为默认地址 */
export function setDefaultAddress(id: string): { ok: boolean; msg: string } {
  if (!isLoggedIn.value) return { ok: false, msg: '请先登录' }
  const username = currentUsername.value
  const db = loadDB()
  const mine = db[username] ?? []
  if (!mine.some(a => a.id === id)) return { ok: false, msg: '地址不存在' }
  apiSetDefaultAddress(id).then(() => refreshAddresses()).catch(() => undefined)
  mine.forEach(a => {
    a.isDefault = a.id === id
    if (a.isDefault) a.updatedAt = Date.now()
  })
  db[username] = mine
  saveDB(db)
  reloadCurrentUser()
  return { ok: true, msg: '已设为默认地址' }
}

/** 表单校验（前后端同规则的前端前置） */
function validate(
  d: Pick<Address, 'name' | 'phone' | 'region' | 'detail'>
): { ok: boolean; msg: string } {
  if (!d.name?.trim()) return { ok: false, msg: '收货人不能为空' }
  if (d.name.trim().length > 20) return { ok: false, msg: '收货人姓名过长' }
  if (!/^1[3-9]\d{9}$/.test((d.phone ?? '').trim())) {
    return { ok: false, msg: '手机号格式错误（11 位大陆手机号）' }
  }
  if (!d.region?.trim()) return { ok: false, msg: '请填写省/市/区' }
  if (!d.detail?.trim()) return { ok: false, msg: '请填写详细地址' }
  if (d.detail.trim().length > 120) return { ok: false, msg: '详细地址过长（最多 120 字）' }
  return { ok: true, msg: '' }
}
