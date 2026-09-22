/**
 * 工作台本地 Pinia store。
 * main 尚无 vnpy 交易 API，默认灌入演示快照；后续接入真实通道时可替换 load* 实现。
 */
import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { demoContracts, demoFunds, demoGateways, demoOrders, demoPositions, demoTicks, demoTrades } from './demoData'

export const useMarketStore = defineStore('home-workbench-market', () => {
  const ticks = reactive<Record<string, Record<string, unknown>>>({})
  const contracts = ref<Record<string, unknown>[]>([])

  function upsertTick(tick: Record<string, unknown>) {
    const key = `${tick.exchange}.${tick.symbol}.${tick.gateway_name}`
    ticks[key] = tick
  }

  async function loadContracts(_q = '') {
    contracts.value = [...demoContracts]
    return contracts.value
  }

  async function loadTicks() {
    for (const key of Object.keys(ticks)) delete ticks[key]
    for (const tick of demoTicks) upsertTick({ ...tick })
    return demoTicks
  }

  return { ticks, contracts, upsertTick, loadContracts, loadTicks }
})

export const useTradeStore = defineStore('home-workbench-trade', () => {
  const orders = ref<Record<string, unknown>[]>([])
  const trades = ref<Record<string, unknown>[]>([])
  const positions = ref<Record<string, unknown>[]>([])
  const funds = ref<Record<string, unknown>[]>([])
  const gateways = ref<Record<string, unknown>[]>([])
  const activeGatewayName = ref('')

  function setActiveGateway(name: string) {
    if (name) activeGatewayName.value = name
  }

  function upsertFund(item: Record<string, unknown>) {
    const index = funds.value.findIndex(
      (row) => row.accountid === item.accountid && row.gateway_name === item.gateway_name
    )
    if (index >= 0) funds.value[index] = item
    else funds.value.unshift(item)
  }

  async function refresh() {
    orders.value = demoOrders.map((row) => ({ ...row }))
    trades.value = demoTrades.map((row) => ({ ...row }))
    positions.value = demoPositions.map((row) => ({ ...row }))
    funds.value = demoFunds.map((row) => ({ ...row }))
    gateways.value = demoGateways.map((row) => ({ ...row }))
    if (!activeGatewayName.value && gateways.value[0]) {
      activeGatewayName.value = String(gateways.value[0].gateway_name || '')
    }
  }

  void refresh()

  return {
    orders, trades, positions, funds, gateways, activeGatewayName,
    setActiveGateway, upsertFund, refresh,
  }
})
