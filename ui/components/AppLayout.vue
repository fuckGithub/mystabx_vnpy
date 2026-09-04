<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="layout-aside layout-aside-pc-220 layout-el-aside-br-color">
      <div class="layout-logo">
        <img :src="logoSrc" class="layout-logo-img" alt="Stabx" />
      </div>
      <el-scrollbar class="flex-auto">
        <div class="layout-nav-menu-vertical">
          <el-menu :default-active="route.path" router>
            <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </el-menu>
        </div>
      </el-scrollbar>
      <div class="layout-aside-footer">
        <span class="layout-aside-footer__version">v0.1.0</span>
        <span class="layout-aside-footer__sep" aria-hidden="true">·</span>
        <span>© Cumustabilis</span>
      </div>
    </el-aside>

    <el-container class="layout-container-view h100" direction="vertical">
      <el-header class="layout-header">
        <div class="layout-navbars-breadcrumb-index">
          <div class="layout-navbars-breadcrumb">
            <span class="layout-navbars-breadcrumb-span">{{ currentTitle }}</span>
          </div>
          <div class="layout-navbars-breadcrumb-actions">
            <el-dropdown popper-class="layout-navbars-user-dropdown" @command="onUserCommand">
              <span class="header-user">
                <span class="header-user-avatar">{{ userInitial }}</span>
                <span class="header-user-name">{{ String(auth.user?.username || "") }}</span>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    <span>退出登录</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>

      <el-main class="layout-main">
        <div class="layout-padding">
          <div class="layout-padding-view">
            <router-view />
          </div>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowDown, DataLine, Setting, SwitchButton, Tickets, Wallet } from "@element-plus/icons-vue";
import { useAuthStore, useTradeStore } from "../stores";
import { connectWs, disconnectWs } from "../ws";
import logoSrc from "@/assets/brand/logo-topbar.png";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const trade = useTradeStore();

const menus = [
  { path: "/market", title: "行情", icon: DataLine },
  { path: "/trade", title: "交易", icon: Tickets },
  { path: "/account", title: "资金 / 持仓", icon: Wallet },
  { path: "/admin", title: "管理", icon: Setting, admin: true },
];

const visibleMenus = computed(() => menus.filter((item) => !item.admin || auth.isAdmin));
const currentTitle = computed(() => visibleMenus.value.find((item) => item.path === route.path)?.title || "交易台");
const userInitial = computed(() => String(auth.user?.username || "U").slice(0, 1).toUpperCase());

onMounted(async () => {
  await trade.refresh();
  connectWs();
});

function onUserCommand(command: string) {
  if (command !== "logout") return;
  disconnectWs();
  auth.logout();
  router.push("/login");
}
</script>
