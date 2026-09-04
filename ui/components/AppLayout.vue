<template>
  <el-container class="layout-container" direction="vertical">
    <el-header class="layout-header">
      <div class="layout-navbars-breadcrumb-index is-topbar-light-fg">
        <div class="layout-logo">
          <img :src="logoSrc" class="layout-logo-img" alt="Cumustabilis" />
        </div>
        <el-menu
          class="layout-nav-menu-horizontal"
          :default-active="activeTopPath"
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
            <span class="nav-item-title">{{ item.title }}</span>
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

    <el-container class="layout-body">
      <el-aside v-if="showSidebar" class="layout-aside" width="208px">
        <el-menu
          class="layout-aside-menu"
          :key="currentModule || 'none'"
          :default-active="activeSidebarPath"
          router
        >
          <el-menu-item v-for="item in sidebarItems" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main class="layout-main">
        <div class="layout-padding" :class="{ 'layout-padding-unset': isWorkbench }">
          <div class="layout-padding-view" :class="{ 'layout-padding-unset-view': isWorkbench }">
            <router-view />
          </div>
        </div>
      </el-main>
    </el-container>

    <el-footer class="layout-footer" height="28px">
      <span>© {{ year }} Stabx</span>
      <span class="layout-footer-divider" aria-hidden="true"></span>
      <a
        class="layout-footer-link"
        href="https://www.vnpy.com"
        target="_blank"
        rel="noopener noreferrer"
      >基于 vn.py</a>
    </el-footer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowDown, SwitchButton } from "@element-plus/icons-vue";
import { useAuthStore, useMarketStore, useTradeStore } from "../stores";
import { moduleKeyFromPath, sidebars, topActivePath, topMenus } from "../nav";
import { connectWs, disconnectWs } from "../ws";
import logoSrc from "@/assets/brand/logo-light.png";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const year = new Date().getFullYear();
const trade = useTradeStore();
const market = useMarketStore();

const visibleMenus = computed(() => topMenus.filter((item) => !item.admin || auth.isAdmin));
const userInitial = computed(() => String(auth.user?.username || "U").slice(0, 1).toUpperCase());
const isWorkbench = computed(() => route.path === "/workbench" || route.path.startsWith("/workbench/"));
const currentModule = computed(() => moduleKeyFromPath(route.path));
const showSidebar = computed(() => Boolean(currentModule.value));
const sidebarItems = computed(() => sidebars[currentModule.value] ?? []);
const activeTopPath = computed(() => topActivePath(route.path));
const activeSidebarPath = computed(() => {
  const items = sidebarItems.value;
  if (items.some((item) => item.path === route.path)) return route.path;
  return items[0]?.path ?? route.path;
});

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
