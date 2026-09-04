<template>
  <el-container class="shell">
    <el-aside width="180px" class="side">
      <div class="brand">Stabx</div>
      <el-menu :default-active="route.path" router background-color="#151b22" text-color="#c9d4de" active-text-color="#67c23a">
        <el-menu-item index="/market">行情</el-menu-item>
        <el-menu-item index="/trade">交易</el-menu-item>
        <el-menu-item index="/account">资金 / 持仓</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin">管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="top">
        <div class="status">
          <span v-for="gw in trade.gateways" :key="String(gw.gateway_name)" class="pill">
            {{ gw.gateway_name }} · {{ gw.conn_status || "DISCONNECTED" }}
          </span>
          <span v-if="!trade.gateways.length" class="muted">未配置账户</span>
        </div>
        <div>
          <span class="muted">{{ String(auth.user?.username || "") }}</span>
          <el-button text type="danger" @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore, useTradeStore } from "../stores";
import { connectWs, disconnectWs } from "../ws";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const trade = useTradeStore();

onMounted(async () => {
  await trade.refresh();
  connectWs();
});

function onLogout() {
  disconnectWs();
  auth.logout();
  router.push("/login");
}
</script>

<style scoped>
.shell { height: 100%; }
.side { background: #151b22; border-right: 1px solid #243040; }
.brand { padding: 18px 16px; font-weight: 700; letter-spacing: 0.08em; }
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #151b22;
  border-bottom: 1px solid #243040;
}
.status { display: flex; gap: 8px; flex-wrap: wrap; }
.pill { font-size: 12px; background: #243040; padding: 2px 8px; border-radius: 999px; }
.muted { color: #8a97a6; margin-right: 8px; }
.main { background: #0f1419; }
</style>
