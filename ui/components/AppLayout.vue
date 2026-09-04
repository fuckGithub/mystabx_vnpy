<template>
  <el-container class="layout-container" direction="vertical">
    <el-header class="layout-header">
      <div class="layout-navbars-breadcrumb-index">
        <div class="layout-logo">
          <img :src="logoSrc" class="layout-logo-img" alt="Cumustabilis" />
        </div>
        <el-menu
          class="layout-nav-menu-horizontal"
          :default-active="route.path"
          router
          mode="horizontal"
          :ellipsis="false"
          background-color="transparent"
        >
          <el-menu-item
            v-for="item in visibleMenus"
            :key="item.path"
            :index="item.path"
            :class="{ 'is-workbench-nav': item.home }"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
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
      <div class="layout-padding" :class="{ 'layout-padding-unset': isWorkbench }">
        <div class="layout-padding-view" :class="{ 'layout-padding-unset-view': isWorkbench }">
          <router-view />
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowDown, DataLine, HomeFilled, Setting, SwitchButton, Tickets, Wallet } from "@element-plus/icons-vue";
import { useAuthStore, useMarketStore, useTradeStore } from "../stores";
import { connectWs, disconnectWs } from "../ws";
import logoSrc from "@/assets/brand/logo-light.png";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const trade = useTradeStore();
const market = useMarketStore();

const menus = [
  { path: "/workbench", title: "工作台", icon: HomeFilled, home: true },
  { path: "/market", title: "市场行情", icon: DataLine },
  { path: "/trade", title: "交易下单", icon: Tickets },
  { path: "/account", title: "资金持仓", icon: Wallet },
  { path: "/admin", title: "系统管理", icon: Setting, admin: true },
];

const visibleMenus = computed(() => menus.filter((item) => !item.admin || auth.isAdmin));
const userInitial = computed(() => String(auth.user?.username || "U").slice(0, 1).toUpperCase());
const isWorkbench = computed(() => route.path === "/workbench");

onMounted(async () => {
  await Promise.all([trade.refresh(), market.loadTicks()]);
  connectWs();
});

function onUserCommand(command: string) {
  if (command !== "logout") return;
  disconnectWs();
  auth.logout();
  router.push("/login");
}
</script>
