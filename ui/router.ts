import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores";
import LoginView from "../features/auth/LoginView.vue";
import DisclaimerView from "../features/auth/DisclaimerView.vue";
import WorkbenchView from "../features/workbench/index.vue";
import MarketView from "../features/market/MarketView.vue";
import TradeView from "../features/trade/TradeView.vue";
import StrategyView from "../features/strategy/StrategyView.vue";
import AccountView from "../features/account/AccountView.vue";
import AdminView from "../features/admin/AdminView.vue";
import AppLayout from "./components/AppLayout.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView },
    { path: "/disclaimer", name: "disclaimer", component: DisclaimerView, meta: { public: true } },
    {
      path: "/",
      component: AppLayout,
      children: [
        { path: "", redirect: "/workbench" },
        { path: "workbench", component: WorkbenchView },
        { path: "market", redirect: "/market/ticks" },
        { path: "market/:section", component: MarketView },
        { path: "trade", redirect: "/trade/order" },
        { path: "trade/:section", component: TradeView },
        { path: "strategy", redirect: "/strategy/cta" },
        { path: "strategy/:section", component: StrategyView },
        { path: "account", redirect: "/account/gateways" },
        { path: "account/:section", component: AccountView },
        { path: "admin", redirect: "/admin/users" },
        { path: "admin/:section", component: AdminView },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.ready) {
    await auth.hydrate();
  }
  if (!to.meta.public && to.path !== "/login" && !auth.isLogin) {
    return "/login";
  }
  if (to.path === "/login" && auth.isLogin) {
    return "/workbench";
  }
  if (to.path.startsWith("/admin") && !auth.isAdmin) {
    return "/workbench";
  }
  return true;
});

export default router;
