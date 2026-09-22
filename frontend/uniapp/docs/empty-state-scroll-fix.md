# 空态滚动修复记录

## 问题描述
UnoCSS 改造后，使用 `min-h-screen` 的页面即使内容为空也会显示滚动条，因为 `min-h-screen` 总是占满视口高度但内容可能不足以填充，导致浏览器渲染滚动条。

## 修复方案

### 空态容器
```html
<!-- ❌ 错误：即使没内容也会显示滚动 -->
<view class="min-h-screen flex flex-col items-center pt-[200rpx]">

<!-- ✅ 正确：h-screen 撑满但不滚动 -->
<view class="h-screen flex flex-col items-center justify-center">
```

### scroll-view 宽度溢出
```scss
// ❌ 错误：scroll-view 直接加 padding 导致内容超出视口
.merchant-scroll {
  padding: 0 24rpx;
}

// ✅ 正确：padding 放在内层 view 上
<scroll-view class="merchant-scroll">
  <view class="px-5 pb-5">
    <!-- 内容 -->
  </view>
</scroll-view>
```

### 空态非滚动
- 空态（无数据）永远不要包裹在 scroll-view 中
- 用 `static` 容器 + `h-screen` 居中显示提示文案和操作按钮
- 非空态才使用 scroll-view

## 受影响页面
| 页面 | 修复内容 |
|------|---------|
| cart/index.vue | 空态 `min-h-screen pt-[200rpx]` → `h-screen center` |
| customer-home/index.vue | 空态移出 scroll-view |
| merchant/merchant-*.vue | scroll-view padding 移到内层 view |
