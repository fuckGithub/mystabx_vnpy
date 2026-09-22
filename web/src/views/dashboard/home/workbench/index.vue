<template>
  <el-config-provider size="small">
    <div class="equilibrix-dashboard quant-theme home-workbench">
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
import { onMounted, ref } from 'vue'
import { topBarBrand } from './mockData'
import { useMarketStore, useTradeStore } from './stores'
import FutureTopBar from './components/FutureTopBar.vue'
import FuturePositionsCard from './components/FuturePositionsCard.vue'
import FutureMarketQuotesCard from './components/FutureMarketQuotesCard.vue'
import FutureRiskGaugeCard from './components/FutureRiskGaugeCard.vue'
import FutureTradeLogBar from './components/FutureTradeLogBar.vue'
import FutureCalendarPanel from './components/FutureCalendarPanel.vue'

const market = useMarketStore()
const trade = useTradeStore()
const calendarExpanded = ref(true)

onMounted(() => {
  void market.loadContracts()
  void market.loadTicks()
  void trade.refresh()
})
</script>

<style src="./styles/equilibrix-dashboard.css"></style>

<style scoped>
.home-workbench {
  min-height: calc(100vh - 140px);
  height: calc(100vh - 140px);
  margin: -12px;
  border-radius: 0;
}
</style>
