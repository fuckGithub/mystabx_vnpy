/** 工作台演示快照（CTP 交易 API 未迁入 main 前的占位数据） */
const now = Date.now()

export const demoGateways: Record<string, unknown>[] = [
  { id: 1, gateway_name: 'CTP.SIMNOW', account_name: 'SimNow-演示', front_label: '电信1-仿真', login_status: 'CONNECTED', quote_status: 'CONNECTED', td_status: 'CONNECTED', md_status: 'CONNECTED', conn_status: 'CONNECTED', connect: { 用户名: '000001' } },
  { id: 2, gateway_name: 'CTP.LIVE', account_name: '实盘-未接入', front_label: '待配置', login_status: 'DISCONNECTED', quote_status: 'DISCONNECTED', td_status: 'DISCONNECTED', md_status: 'DISCONNECTED', conn_status: 'DISCONNECTED', connect: { 用户名: '' } },
]

export const demoFunds: Record<string, unknown>[] = [
  { gateway_name: 'CTP.SIMNOW', accountid: '000001', balance: 1256800.52, available: 986420.18, margin: 248180.34, frozen: 22200.0, close_profit: 3520.5, position_profit: 8640.25 },
]

export const demoPositions: Record<string, unknown>[] = [
  { symbol: 'rb2510', exchange: 'SHFE', direction: 'long', volume: 12, price: 3482.0, pnl: 4260.0, frozen: 0, gateway_name: 'CTP.SIMNOW' },
  { symbol: 'au2512', exchange: 'SHFE', direction: 'short', volume: 2, price: 598.4, pnl: -1820.0, frozen: 0, gateway_name: 'CTP.SIMNOW' },
  { symbol: 'IF2509', exchange: 'CFFEX', direction: 'long', volume: 1, price: 3820.2, pnl: 6200.0, frozen: 0, gateway_name: 'CTP.SIMNOW' },
  { symbol: 'm2509', exchange: 'DCE', direction: 'long', volume: 20, price: 2864.0, pnl: -1000.0, frozen: 5, gateway_name: 'CTP.SIMNOW' },
]

export const demoTicks: Record<string, unknown>[] = [
  { symbol: 'rb2510', exchange: 'SHFE', gateway_name: 'CTP.SIMNOW', name: '螺纹钢2510', last_price: 3517.0, pre_close: 3480.0, high_price: 3528.0, low_price: 3472.0, bid_price_1: 3516.0, ask_price_1: 3517.0, volume: 286420, open_interest: 1245800, datetime: new Date(now - 2000).toISOString() },
  { symbol: 'au2512', exchange: 'SHFE', gateway_name: 'CTP.SIMNOW', name: '黄金2512', last_price: 596.8, pre_close: 599.2, high_price: 601.0, low_price: 595.4, bid_price_1: 596.7, ask_price_1: 596.9, volume: 42180, open_interest: 186420, datetime: new Date(now - 3500).toISOString() },
  { symbol: 'IF2509', exchange: 'CFFEX', gateway_name: 'CTP.SIMNOW', name: '沪深300股指2509', last_price: 3841.0, pre_close: 3818.0, high_price: 3852.0, low_price: 3810.0, bid_price_1: 3840.8, ask_price_1: 3841.2, volume: 68240, open_interest: 98560, datetime: new Date(now - 1200).toISOString() },
  { symbol: 'm2509', exchange: 'DCE', gateway_name: 'CTP.SIMNOW', name: '豆粕2509', last_price: 2859.0, pre_close: 2870.0, high_price: 2882.0, low_price: 2851.0, bid_price_1: 2858.0, ask_price_1: 2859.0, volume: 312680, open_interest: 842100, datetime: new Date(now - 4800).toISOString() },
  { symbol: 'cu2510', exchange: 'SHFE', gateway_name: 'CTP.SIMNOW', name: '沪铜2510', last_price: 78620, pre_close: 78150, high_price: 78880, low_price: 77980, bid_price_1: 78610, ask_price_1: 78630, volume: 54320, open_interest: 226480, datetime: new Date(now - 6000).toISOString() },
  { symbol: 'SA509', exchange: 'CZCE', gateway_name: 'CTP.SIMNOW', name: '纯碱509', last_price: 1486.0, pre_close: 1498.0, high_price: 1506.0, low_price: 1478.0, bid_price_1: 1485.0, ask_price_1: 1486.0, volume: 198760, open_interest: 512340, datetime: new Date(now - 7200).toISOString() },
]

export const demoContracts: Record<string, unknown>[] = demoTicks.map((t) => ({ symbol: t.symbol, exchange: t.exchange, name: t.name }))

export const demoOrders: Record<string, unknown>[] = [
  { vt_orderid: 'CTP.SIMNOW.1', orderid: '1', symbol: 'rb2510', exchange: 'SHFE', direction: 'buy', offset: 'open', volume: 2, price: 3510.0, status: 'NOT_TRADED', gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 45000).toISOString() },
  { vt_orderid: 'CTP.SIMNOW.2', orderid: '2', symbol: 'm2509', exchange: 'DCE', direction: 'sell', offset: 'close', volume: 5, price: 2860.0, status: 'PART_TRADED', gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 120000).toISOString() },
  { vt_orderid: 'CTP.SIMNOW.3', orderid: '3', symbol: 'IF2509', exchange: 'CFFEX', direction: 'buy', offset: 'open', volume: 1, price: 3825.0, status: 'ALL_TRADED', gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 360000).toISOString() },
]

export const demoTrades: Record<string, unknown>[] = [
  { tradeid: 'T1001', symbol: 'IF2509', exchange: 'CFFEX', direction: 'buy', offset: 'open', volume: 1, price: 3825.0, gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 350000).toISOString() },
  { tradeid: 'T1002', symbol: 'rb2510', exchange: 'SHFE', direction: 'buy', offset: 'open', volume: 4, price: 3495.0, gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 720000).toISOString() },
  { tradeid: 'T1003', symbol: 'au2512', exchange: 'SHFE', direction: 'sell', offset: 'open', volume: 2, price: 598.4, gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 900000).toISOString() },
  { tradeid: 'T1004', symbol: 'm2509', exchange: 'DCE', direction: 'sell', offset: 'close', volume: 3, price: 2860.0, gateway_name: 'CTP.SIMNOW', datetime: new Date(now - 110000).toISOString() },
]
