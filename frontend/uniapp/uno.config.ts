import type { Preset } from 'unocss'
import { FileSystemIconLoader } from '@iconify/utils/lib/loader/node-loaders'

// https://www.npmjs.com/package/@uni-helper/unocss-preset-uni
import { presetUni } from '@uni-helper/unocss-preset-uni'
// @see https://unocss.dev/presets/legacy-compat
import { presetLegacyCompat } from '@unocss/preset-legacy-compat'
import { defineConfig, presetIcons, transformerDirectives, transformerVariantGroup } from 'unocss'

export default defineConfig({
  presets: [
    presetUni({
      attributify: false,
    }),
    presetIcons({
      scale: 1.2,
      warn: true,
      extraProperties: {
        display: 'inline-block',
        'vertical-align': 'middle',
      },
      collections: {
        'my-icons': FileSystemIconLoader('./src/static/my-icons', (svg) => {
          let svgStr = svg
          svgStr = svgStr.includes('fill="') ? svgStr : svgStr.replace(/^<svg /, '<svg fill="currentColor" ')
          svgStr = svgStr.replace(/(<svg.*?width=)"(.*?)"/, '$1"1em"').replace(/(<svg.*?height=)"(.*?)"/, '$1"1em"')
          return svgStr
        }),
      },
    }),
    presetLegacyCompat({
      commaStyleColorFunction: true,
      legacyColorSpace: true,
    }) as Preset,
  ],
  transformers: [transformerDirectives(), transformerVariantGroup()],
  shortcuts: [
    {
      center: 'flex justify-center items-center',
    },
  ],
  safelist: [
    'i-carbon-code',
    'i-carbon-home',
    'i-carbon-user',
    'i-carbon-shopping-cart',
    'i-carbon-ibm-watson-language-translator',
    'i-carbon-menu',
  ],
  rules: [
    [
      'p-safe',
      {
        padding:
          'env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)',
      },
    ],
    ['pt-safe', { 'padding-top': 'env(safe-area-inset-top)' }],
    ['pb-safe', { 'padding-bottom': 'env(safe-area-inset-bottom)' }],
  ],
  theme: {
    colors: {
      /** 用法: text-primary / bg-brand / text-text-secondary */
      primary: 'var(--wot-color-theme,#0957DE)',
      brand: '#ff6b35',
      'brand-light': '#fff5f0',
      'page-bg': '#f7f7f7',
      'card-bg': '#ffffff',
      'text-primary': '#1a1a2e',
      'text-secondary': '#666680',
      'text-tertiary': '#999aad',
      border: '#ebeef5',
      'border-light': '#f4f5f7',
      danger: '#ff4d4f',
      warning: '#ff9500',
      success: '#07c160',
      'text-disabled': '#ccc',
    },
    fontSize: {
      '3xs': ['18rpx', '26rpx'],
      '2xs': ['20rpx', '28rpx'],
      xs: ['22rpx', '30rpx'],
      sm: ['24rpx', '32rpx'],
      base: ['26rpx', '36rpx'],
      md: ['28rpx', '38rpx'],
      lg: ['30rpx', '40rpx'],
      xl: ['34rpx', '44rpx'],
      '2xl': ['40rpx', '52rpx'],
    },
    borderRadius: {
      sm: '8rpx',
      md: '16rpx',
      lg: '20rpx',
      full: '40rpx',
    },
    boxShadow: {
      sm: '0 2rpx 8rpx rgba(0,0,0,0.04)',
      md: '0 4rpx 16rpx rgba(0,0,0,0.06)',
      lg: '0 8rpx 24rpx rgba(0,0,0,0.08)',
    },
  },
})
