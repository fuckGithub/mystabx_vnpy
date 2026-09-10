<template>
  <el-config-provider size="small">
    <div class="equilibrix-dashboard quant-theme">
      <FutureTopBar :brand="topBarBrand" />
      <div class="equilibrix-dashboard-body" :class="{ 'calendar-open': calendarExpanded }">
        <main class="equilibrix-dashboard-main">
          <div class="future-cards-grid layout-containers">
            <FuturePositionsCard class="card-positions" />
            <FutureMarketQuotesCard class="card-market" />
            <FutureRiskGaugeCard class="card-risk" />
          </div>
          <FutureTradeLogBar class="future-log-section" />
        </main>
        <FutureCalendarPanel v-model:expanded="calendarExpanded" />
      </div>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useMarketStore } from "@/stores";
import { topBarBrand } from "./mockData";
import FutureTopBar from "./components/FutureTopBar.vue";
import FuturePositionsCard from "./components/FuturePositionsCard.vue";
import FutureMarketQuotesCard from "./components/FutureMarketQuotesCard.vue";
import FutureRiskGaugeCard from "./components/FutureRiskGaugeCard.vue";
import FutureTradeLogBar from "./components/FutureTradeLogBar.vue";
import FutureCalendarPanel from "./components/FutureCalendarPanel.vue";

const market = useMarketStore();
const calendarExpanded = ref(true);

onMounted(() => {
  void market.loadContracts();
});
</script>

<style src="@/styles/equilibrix-dashboard.css"></style>
