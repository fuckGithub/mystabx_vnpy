<template>
  <div class="disclaimer-page">
    <header class="disclaimer-bar">
      <img :src="wordmarkSrc" class="disclaimer-logo" alt="Stabx" />
      <RouterLink to="/login" class="disclaimer-back">返回登录</RouterLink>
    </header>

    <article class="disclaimer-article">
      <p class="disclaimer-kicker">公开说明 · 无需登录</p>
      <h1>免责声明</h1>
      <p class="disclaimer-lead">
        本文为事实说明，不构成法律意见，亦不构成对任何主体的背书或投资建议。
        完整文本与登录页一致，亦见仓库 <code>docs/07-用户服务协议与免责声明.md</code>。
      </p>

      <section>
        <h2>1. 与 vn.py / 上期技术的关系</h2>
        <p>
          本项目（Stabx Web 交易台）基于开源项目
          <a href="https://github.com/vnpy/vnpy" target="_blank" rel="noopener noreferrer">vn.py</a>
          （VeighNa）与
          <a href="https://github.com/vnpy/vnpy_ctp" target="_blank" rel="noopener noreferrer">vnpy_ctp</a>
          构建，是围绕 vnpy 的 Web UI 与 FastAPI 托管层。
        </p>
        <p>
          本仓库的存在与使用，<strong>不构成</strong>对 vn.py 官方或其作者、上海期货信息技术有限公司（上期技术）及其
          CTP 接口的背书、合作声明或官方支持。
        </p>
        <p>
          vn.py 与 vnpy_ctp 的版权与 MIT 许可原文见仓库根目录
          <code>NOTICE</code>、<code>THIRD_PARTY.md</code> 以及
          <code>licenses/vnpy-LICENSE</code>、<code>licenses/vnpy_ctp-LICENSE</code>。
          本项目不主张对 vnpy 或其组件的所有权。
        </p>
      </section>

      <section>
        <h2>2. 交易风险与投资建议</h2>
        <p>
          期货交易（含 SimNow 模拟交易）存在亏损风险，可能导致本金部分或全部损失。本软件仅提供行情查看、委托提交、资金持仓查询等技术工具，<strong>不提供投资建议、不荐品种、不预测行情、不承诺收益</strong>。
        </p>
        <p>
          软件中展示的行情、持仓、示例或任何内容，仅供操作参考，不构成买入、卖出或持有任何合约的建议。一切交易决策由使用者独立作出，盈亏自负。
        </p>
      </section>

      <section>
        <h2>3. 按现状提供</h2>
        <p>本项目按「现状（AS IS）」开源提供。在适用法律允许的范围内，作者与贡献者不对以下事项承担责任：</p>
        <ul>
          <li>使用本软件产生的盈利或亏损</li>
          <li>服务中断、连接失败、指令延迟或未成交</li>
          <li>数据延迟、错误、缺失或丢失</li>
          <li>软件缺陷、维护或第三方接口异常</li>
        </ul>
        <p>不保证软件持续可用、正确、完整或适用于特定用途。</p>
      </section>

      <section>
        <h2>4. 第三方条款</h2>
        <p>
          CTP API 由上期技术提供，与 vnpy 项目相互独立。SimNow、期货公司、交易所各自有使用条款、交易规则与风险揭示。使用本软件接入上述服务时，须自行阅读并遵守其条款；因违反第三方条款产生的后果由使用者自行承担。
        </p>
        <p>请勿将真实柜台密码、资金账号写入仓库、脚本或公开文档。</p>
      </section>

      <section>
        <h2>5. 适用范围</h2>
        <p>
          本声明适用于本仓库的软件、文档与示例。继续使用即表示你已阅读并了解上述内容。若不同意，请停止使用。
        </p>
      </section>

      <p class="disclaimer-footer-nav">
        <RouterLink to="/login" class="disclaimer-back disclaimer-back--inline">返回登录</RouterLink>
      </p>
    </article>
  </div>
</template>

<script setup lang="ts">
import wordmarkSrc from "@/assets/brand/logo-topbar.png";
</script>

<style scoped>
.disclaimer-page {
  min-height: 100dvh;
  background: #f8fafc;
  color: #0f172a;
}

.disclaimer-bar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 24px;
  background: rgba(248, 250, 252, 0.92);
  border-bottom: 1px solid #e2e8f0;
  backdrop-filter: blur(8px);
}

.disclaimer-logo {
  height: 28px;
  width: auto;
}

.disclaimer-back {
  font-size: 14px;
  font-weight: 600;
  color: #1677ff;
  text-decoration: none;
}

.disclaimer-back:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.disclaimer-article {
  max-width: 720px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

.disclaimer-kicker {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #64748b;
}

.disclaimer-article h1 {
  margin: 0 0 12px;
  font-size: 28px;
  line-height: 1.25;
}

.disclaimer-lead,
.disclaimer-article p,
.disclaimer-article li {
  font-size: 15px;
  line-height: 1.75;
  color: #334155;
}

.disclaimer-lead {
  margin: 0 0 28px;
}

.disclaimer-article section {
  margin-bottom: 28px;
}

.disclaimer-article h2 {
  margin: 0 0 10px;
  font-size: 18px;
  line-height: 1.4;
}

.disclaimer-article p {
  margin: 0 0 12px;
}

.disclaimer-article ul {
  margin: 0 0 12px;
  padding-left: 1.2em;
}

.disclaimer-article a {
  color: #1677ff;
}

.disclaimer-article code {
  font-size: 13px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #e2e8f0;
  color: #0f172a;
}

.disclaimer-footer-nav {
  margin-top: 8px;
}

.disclaimer-back--inline {
  display: inline-block;
}
</style>
