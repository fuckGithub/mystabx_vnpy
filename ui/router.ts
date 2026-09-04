import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores";
import LoginView from "../features/auth/LoginView.vue";
import MarketView from "../features/market/MarketView.vue";
import TradeView from "../features/trade/TradeView.vue";
import AccountView from "../features/account/AccountView.vue";
import AdminView from "../features/admin/AdminView.vue";
import AppLayout from "./components/AppLayout.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView },
    {
      path: "/",
      component: AppLayout,
      children: [
        { path: "", redirect: "/market" },
        { path: "market", component: MarketView },
        { path: "trade", component: TradeView },
        { path: "account", component: AccountView },
        { path: "admin", component: AdminView },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.ready) {
    await auth.hydrate();
  }
  if (to.path !== "/login" && !auth.isLogin) {
    return "/login";
  }
  if (to.path === "/login" && auth.isLogin) {
    return "/market";
  }
  if (to.path === "/admin" && !auth.isAdmin) {
    return "/market";
  }
  return true;
});

export default router;
