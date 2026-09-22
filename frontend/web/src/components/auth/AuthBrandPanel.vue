<!-- vnpy AuthBrandPanel：左侧品牌栏（行情 / 交易 / 风控） -->
<template>
  <section class="brand-panel">
    <div class="brand-panel-inner">
      <header class="brand-header">
        <div class="brand-logo-row">
          <img :src="wordmarkSrc" class="brand-wordmark" alt="Stabx" />
        </div>
      </header>

      <div class="hero-copy">
        <p class="eyebrow">企业级期货交易工作台</p>
        <h1>
          让行情<span class="gradient-text">看得见</span><br />
          让交易<span class="gradient-text">更高效</span>
        </h1>
        <p class="subtitle">
          面向多账户、多合约的一体化交易中枢，帮助您把行情、资金与下单连接在同一工作台。
        </p>
        <ul class="brand-tags">
          <li v-for="tag in brandTags" :key="tag">{{ tag }}</li>
        </ul>
      </div>

      <ul class="feature-list">
        <li v-for="item in features" :key="item.title" class="feature-card">
          <span class="feature-icon" aria-hidden="true" v-html="item.icon" />
          <div class="feature-copy">
            <strong>{{ item.title }}</strong>
            <span>{{ item.desc }}</span>
          </div>
        </li>
      </ul>

      <footer class="brand-footer">
        <span>© {{ year }} Stabx</span>
        <span class="brand-footer-divider" aria-hidden="true"></span>
        <span>行情 · 交易 · 风控</span>
        <span class="brand-footer-divider" aria-hidden="true"></span>
        <RouterLink to="/disclaimer" class="brand-footer-link">免责声明</RouterLink>
        <span class="brand-footer-divider" aria-hidden="true"></span>
        <a
          class="brand-footer-link"
          href="https://www.vnpy.com"
          target="_blank"
          rel="noopener noreferrer">
          基于 vn.py
        </a>
      </footer>
    </div>

    <div class="panel-decoration" aria-hidden="true">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="grid-lines"></div>
    </div>
  </section>
</template>

<script setup lang="ts">
import logoWordmarkLight from '@/assets/brand/logo-light.png'

defineOptions({ name: 'AuthBrandPanel' })

const year = new Date().getFullYear()
const wordmarkSrc = logoWordmarkLight
const brandTags = ['实时行情', '资金持仓', '委托成交', '账户隔离']

const features = [
  {
    title: '行情与合约一屏掌握',
    desc: '合约检索、订阅与盘口刷新集中呈现，关键价格及时可见。',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 17V9"/><path d="M12 17V7"/><path d="M16 17v-5"/></svg>`,
  },
  {
    title: '下单撤单在线协同',
    desc: '限价委托、开平与撤单一站完成，减少跨终端重复确认。',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v3"/><path d="M12 18v3"/><path d="M3 12h3"/><path d="M18 12h3"/><circle cx="12" cy="12" r="4"/><path d="m8 8 2 2"/><path d="m14 14 2 2"/></svg>`,
  },
  {
    title: '资金持仓一屏洞察',
    desc: '权益、可用、持仓与成交集中呈现，为交易决策提供及时参考。',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"/><path d="M6 21V7l6-4 6 4v14"/><path d="M9 21v-6h6v6"/><path d="M9 9h.01M15 9h.01"/></svg>`,
  },
  {
    title: '账户隔离可控可溯',
    desc: '按用户分配 CTP 账户，权限分级、操作留痕，保障交易安全。',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 20 8v8l-8 5-8-5V8l8-5z"/><path d="M12 12v8"/><path d="M20 8 12 12 4 8"/></svg>`,
  },
]
</script>
