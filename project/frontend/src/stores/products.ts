/**
 * stores/products.ts - 商品统一注册表
 * ----------------------------------------------------------------
 * 全站商品的唯一数据源，供商品详情页查询：
 *   - 按 ID 查询商品
 *   - 获取商品所属店铺信息（店铺名 / 评分）
 *   - 获取"看了又看"推荐（同分类其他商品）
 * ID 规则：数码 1xx / 穿搭 2xx / 家居 3xx / 新人 4xx / 百货 5xx
 */
export interface Product {
  id: number
  name: string
  desc?: string
  price: number
  originalPrice?: number
  emoji: string
  bgColor: string
  sales: number
  tag?: string
  category: ProductCategory
}

export type ProductCategory = 'digital' | 'fashion' | 'homegoods' | 'newuser' | 'daily'

/** 分类中文名 */
export const CATEGORY_NAMES: Record<ProductCategory, string> = {
  digital: '数码爆款',
  fashion: '潮流穿搭',
  homegoods: '家居好物',
  newuser: '新人专享',
  daily: '品质百货'
}

/** 分类所属店铺信息 */
export const SHOPS: Record<ProductCategory, { name: string; emoji: string; rating: number }> = {
  digital: { name: '极光数码旗舰店', emoji: '🛰️', rating: 4.9 },
  fashion: { name: '潮流前线服饰店', emoji: '🧵', rating: 4.8 },
  homegoods: { name: '宜家优选家居店', emoji: '🛋️', rating: 4.8 },
  newuser: { name: '新人专享福利社', emoji: '🎁', rating: 5.0 },
  daily: { name: '优品生活百货', emoji: '🧺', rating: 4.7 }
}

/** 全站商品注册表（启动时由后端数据库同步） */
let PRODUCTS: Product[] = [
  // ====== 数码爆款 ======
  { id: 101, name: '极光 Pro 5G 手机', desc: '6.7寸全面屏 · 12+256GB', price: 3999, originalPrice: 4999, emoji: '📱', bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', sales: 2863, tag: '热销', category: 'digital' },
  { id: 102, name: '旗舰折叠屏手机', desc: '8.0寸折叠屏 · 16+512GB', price: 8999, originalPrice: 9999, emoji: '📲', bgColor: 'linear-gradient(135deg, #5ee7df 0%, #b490ca 100%)', sales: 1230, tag: '新品', category: 'digital' },
  { id: 103, name: '降噪无线蓝牙耳机', desc: '主动降噪 · 续航40小时', price: 399, originalPrice: 699, emoji: '🎧', bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', sales: 5120, tag: '限时', category: 'digital' },
  { id: 104, name: '立体声蓝牙音箱', desc: '360°环绕 · IPX7防水', price: 299, originalPrice: 499, emoji: '🔊', bgColor: 'linear-gradient(135deg, #ff6a00 0%, #ee0979 100%)', sales: 3450, category: 'digital' },
  { id: 105, name: '超薄智能手表', desc: '血氧监测 · 7天续航', price: 1299, originalPrice: 1599, emoji: '⌚', bgColor: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', sales: 1890, tag: '新品', category: 'digital' },
  { id: 106, name: '智能运动手环', desc: '心率监测 · 14天续航', price: 199, originalPrice: 299, emoji: '⌚', bgColor: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', sales: 6780, tag: '热销', category: 'digital' },
  { id: 107, name: '65W氮化镓充电器', desc: '双口快充 · 折叠插脚', price: 99, originalPrice: 159, emoji: '🔌', bgColor: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', sales: 4320, category: 'digital' },
  { id: 108, name: '高速移动固态硬盘', desc: '1TB容量 · USB4传输', price: 599, originalPrice: 799, emoji: '💾', bgColor: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)', sales: 980, tag: '新品', category: 'digital' },

  // ====== 潮流穿搭 ======
  { id: 201, name: '纯棉宽松T恤', desc: '2026新款 · 男女同款', price: 89, originalPrice: 159, emoji: '👕', bgColor: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', sales: 8340, tag: '热销', category: 'fashion' },
  { id: 202, name: '法式碎花连衣裙', desc: '显瘦版型 · 春夏新款', price: 269, originalPrice: 399, emoji: '👗', bgColor: 'linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)', sales: 4210, tag: '新品', category: 'fashion' },
  { id: 203, name: '针织开衫外套', desc: '柔软亲肤 · 多色可选', price: 199, originalPrice: 299, emoji: '🧥', bgColor: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', sales: 1890, category: 'fashion' },
  { id: 204, name: '高腰直筒牛仔裤', desc: '修身显腿长 · 舒适弹力', price: 159, originalPrice: 259, emoji: '👖', bgColor: 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)', sales: 5670, tag: '限时', category: 'fashion' },
  { id: 205, name: '休闲运动短裤', desc: '速干面料 · 松紧腰头', price: 69, originalPrice: 119, emoji: '🩳', bgColor: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)', sales: 3450, category: 'fashion' },
  { id: 206, name: '透气运动跑鞋', desc: '轻量减震 · 回弹缓震', price: 499, originalPrice: 799, emoji: '👟', bgColor: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)', sales: 3210, tag: '热销', category: 'fashion' },
  { id: 207, name: '复古帆布鞋', desc: '经典款式 · 百搭舒适', price: 129, originalPrice: 199, emoji: '👟', bgColor: 'linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%)', sales: 6780, category: 'fashion' },
  { id: 208, name: '真皮时尚单肩包', desc: '简约百搭 · 大容量', price: 359, originalPrice: 599, emoji: '👜', bgColor: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)', sales: 2340, tag: '新品', category: 'fashion' },
  { id: 209, name: '潮流墨镜', desc: 'UV400防晒 · 多款可选', price: 99, originalPrice: 199, emoji: '🕶️', bgColor: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)', sales: 4520, tag: '限时', category: 'fashion' },
  { id: 210, name: '编织时尚帽子', desc: '四季百搭 · 显脸小', price: 49, originalPrice: 89, emoji: '🧢', bgColor: 'linear-gradient(135deg, #ff6a00 0%, #ee0979 100%)', sales: 2890, category: 'fashion' },

  // ====== 家居好物 ======
  { id: 301, name: '北欧简约台灯', desc: '三档调光 · 无频闪', price: 129, originalPrice: 229, emoji: '💡', bgColor: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)', sales: 1560, category: 'homegoods' },
  { id: 302, name: '智能感应夜灯', desc: '人体感应 · 柔光护眼', price: 59, originalPrice: 99, emoji: '🪔', bgColor: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)', sales: 4320, tag: '热销', category: 'homegoods' },
  { id: 303, name: '316不锈钢保温杯', desc: '24小时保温 · 500ml', price: 79, originalPrice: 139, emoji: '🥤', bgColor: 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)', sales: 6780, tag: '限时', category: 'homegoods' },
  { id: 304, name: '陶瓷餐具套装', desc: '6件套 · 食品级釉下彩', price: 159, originalPrice: 259, emoji: '🍽️', bgColor: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)', sales: 2340, category: 'homegoods' },
  { id: 305, name: '进口零食大礼包', desc: '20种美味 · 送礼首选', price: 199, originalPrice: 299, emoji: '🍫', bgColor: 'linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)', sales: 2450, tag: '新品', category: 'homegoods' },
  { id: 306, name: '多层收纳置物架', desc: '稳固承重 · 免安装', price: 139, originalPrice: 219, emoji: '🗄️', bgColor: 'linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%)', sales: 3120, category: 'homegoods' },
  { id: 307, name: '衣物收纳袋', desc: '大容量 · 防尘防潮', price: 39, originalPrice: 69, emoji: '🧺', bgColor: 'linear-gradient(135deg, #ff6a00 0%, #ee0979 100%)', sales: 5670, tag: '热销', category: 'homegoods' },
  { id: 308, name: '北欧风装饰画', desc: '高清喷绘 · 实木画框', price: 89, originalPrice: 159, emoji: '🖼️', bgColor: 'linear-gradient(135deg, #5ee7df 0%, #b490ca 100%)', sales: 1890, category: 'homegoods' },
  { id: 309, name: '香薰精油蜡烛', desc: '助眠舒缓 · 持久留香', price: 69, originalPrice: 129, emoji: '🕯️', bgColor: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)', sales: 4230, tag: '新品', category: 'homegoods' },
  { id: 310, name: '仿真绿植盆栽', desc: '免养护 · 四季常青', price: 49, originalPrice: 99, emoji: '🪴', bgColor: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', sales: 6780, tag: '限时', category: 'homegoods' },

  // ====== 新人专享 ======
  { id: 401, name: '新人专享 · 蓝牙耳机', desc: '新人特惠 · 限量抢购', price: 99, originalPrice: 299, emoji: '🎧', bgColor: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', sales: 12340, tag: '新人价', category: 'newuser' },
  { id: 402, name: '新人专享 · 智能手环', desc: '新人特惠 · 心率监测', price: 79, originalPrice: 199, emoji: '⌚', bgColor: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', sales: 9870, tag: '新人价', category: 'newuser' },
  { id: 403, name: '新人专享 · 保温杯', desc: '新人特惠 · 316不锈钢', price: 29, originalPrice: 99, emoji: '🥤', bgColor: 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)', sales: 15620, tag: '新人价', category: 'newuser' },
  { id: 404, name: '新人专享 · T恤', desc: '新人特惠 · 纯棉舒适', price: 39, originalPrice: 129, emoji: '👕', bgColor: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', sales: 8920, tag: '新人价', category: 'newuser' },

  // ====== 品质百货（购物车推荐位） ======
  { id: 501, name: '磁吸无线充电宝', desc: '20000mAh · 快充', price: 129, emoji: '🔋', bgColor: 'linear-gradient(135deg, #667eea, #764ba2)', sales: 2650, category: 'daily' },
  { id: 502, name: '极简风机械键盘', desc: '三模连接 · 热插拔', price: 399, emoji: '⌨️', bgColor: 'linear-gradient(135deg, #f093fb, #f5576c)', sales: 1870, category: 'daily' },
  { id: 503, name: '人体工学办公椅', desc: '4D扶手 · 腰枕可调', price: 899, emoji: '🪑', bgColor: 'linear-gradient(135deg, #4facfe, #00f2fe)', sales: 960, category: 'daily' },
  { id: 504, name: '智能香薰加湿器', desc: '静音 · 氛围灯', price: 199, emoji: '💨', bgColor: 'linear-gradient(135deg, #a8edea, #fed6e3)', sales: 3240, category: 'daily' }
]

/** 按 ID 查询商品 */
export function getProductById(id: number): Product | undefined {
  return PRODUCTS.find(p => p.id === id)
}

/** 按分类获取商品列表 */
export function getProductsByCategory(cat: ProductCategory): Product[] {
  return PRODUCTS.filter(p => p.category === cat)
}

/** 查询分类中文名 */
export function getCategoryName(cat: ProductCategory): string {
  return CATEGORY_NAMES[cat]
}

/** "看了又看"推荐：同分类其他商品，不足 4 个时用热门商品补齐 */
export function getRelatedProducts(id: number, limit = 4): Product[] {
  const cur = getProductById(id)
  if (!cur) return []
  const sameCat = PRODUCTS.filter(p => p.category === cur.category && p.id !== id)
  const fill = PRODUCTS.filter(p => p.category !== cur.category && p.id !== id)
    .sort((a, b) => b.sales - a.sales)
  return [...sameCat, ...fill].slice(0, limit)
}

/** 由 ID 稳定生成评分（同一商品每次一致） */
export function getProductRating(id: number): number {
  return 4.6 + (id % 4) * 0.1
}

/** 由销量估算评价数 */
export function getReviewCount(sales: number): number {
  return Math.floor(sales * 0.42)
}

/** 全部商品（直接引用 PRODUCTS 原数组，View-All 页面入口使用） */
export const allProducts: Product[] = PRODUCTS

/** 从后端商品表加载并替换本地注册表。 */
export async function loadProducts(): Promise<void> {
  const { apiGetProductList } = await import('@/api/product')
  const response = await apiGetProductList()
  const rows = (response as unknown as { products?: any[] }).products ?? response
  PRODUCTS = (rows as any[]).map((item, index) => ({
    id: item.id,
    name: item.name,
    desc: item.category,
    price: Number(item.price),
    originalPrice: Number(item.price),
    emoji: item.category === '手机' ? '📱' : item.category === '耳机' ? '🎧' : '🛍️',
    bgColor: '#f3f4f6',
    sales: 0,
    tag: item.tags?.[0],
    category: item.category === '手机' || item.category === '耳机' || item.category.includes('电脑') ? 'digital' : item.category.includes('鞋') ? 'fashion' : 'homegoods'
  }))
  allProducts.splice(0, allProducts.length, ...PRODUCTS)
}

/** 格式化销量：超过 10000 显示 "x.x万" */
export function formatSales(num: number): string {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toString()
}
