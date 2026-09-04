# 04 WebSocket 消息协议

## 1. 通用 envelope

所有消息统一一个外层信封：

```json
{
  "type": "tick",
  "ts": 1710000000123,
  "data": { }
}
```

`type` 枚举：`auth_ok | tick | bar | order | trade | position | account | contract | gateway | log | quote | strategy | error | pong`。

## 2. 客户端 → 服务端

```json
// 鉴权（连接后首条）
{ "type": "auth", "data": { "token": "<JWT>" } }

// 订阅（服务端仍按用户可见账户二次过滤）
{ "type": "subscribe", "data": { "topics": ["tick:SHFE.rb2410", "order"] } }

// 退订
{ "type": "unsubscribe", "data": { "topics": ["tick:SHFE.rb2410"] } }

// 心跳
{ "type": "ping", "data": {} }
```

## 3. 服务端 → 客户端（字段对齐 vnpy 4.x）

```json
// 行情 tick
{ "type": "tick", "data": {
  "symbol": "rb2410", "exchange": "SHFE",
  "datetime": "2025-01-01T09:30:00.500+08:00",
  "name": "螺纹2410",
  "last_price": 3950.0, "last_volume": 2,
  "volume": 12345.0, "turnover": 48700000.0, "open_interest": 100000.0,
  "open_price": 3940.0, "high_price": 3960.0, "low_price": 3930.0, "pre_close": 3945.0,
  "limit_up": 4250.0, "limit_down": 3650.0,
  "bid_price_1": 3949.0, "bid_volume_1": 20, "ask_price_1": 3951.0, "ask_volume_1": 15,
  "bid_price_2": 3948.0, "bid_volume_2": 10, "ask_price_2": 3952.0, "ask_volume_2": 8,
  "gateway_name": "CTP.1"
}}

// 委托
{ "type": "order", "data": {
  "symbol": "rb2410", "exchange": "SHFE",
  "orderid": "ORD-1001", "type": "LIMIT",
  "direction": "LONG", "offset": "OPEN",
  "price": 3950.0, "volume": 2, "traded": 1,
  "status": "PART_TRADED", "datetime": "2025-01-01T09:30:01.100+08:00",
  "reference": "web:1", "gateway_name": "CTP.1"
}}

// 成交
{ "type": "trade", "data": {
  "symbol": "rb2410", "exchange": "SHFE",
  "orderid": "ORD-1001", "tradeid": "TRD-9",
  "direction": "LONG", "offset": "OPEN",
  "price": 3949.0, "volume": 1,
  "datetime": "2025-01-01T09:30:01.200+08:00", "gateway_name": "CTP.1"
}}

// 持仓
{ "type": "position", "data": {
  "symbol": "rb2410", "exchange": "SHFE", "direction": "LONG",
  "volume": 3, "frozen": 0, "price": 3947.0, "pnl": 600.0, "yd_volume": 0,
  "gateway_name": "CTP.1"
}}

// 资金
{ "type": "account", "data": {
  "accountid": "123456", "balance": 1000000.0, "frozen": 8000.0, "available": 992000.0,
  "gateway_name": "CTP.1"
}}

// 合约
{ "type": "contract", "data": {
  "symbol": "rb2410", "exchange": "SHFE", "name": "螺纹2410",
  "product": "螺纹钢", "size": 10, "pricetick": 1.0, "min_volume": 1,
  "gateway_name": "CTP.1"
}}

// 网关状态
{ "type": "gateway", "data": { "gateway_name": "CTP.1", "status": "CONNECTED" } }

// 日志
{ "type": "log", "data": { "level": "error", "msg": "连接失败", "time": "...", "gateway_name": "CTP.1" } }

// 策略（CTA）
{ "type": "strategy", "data": {
  "strategy_name": "1.DoubleMa", "status": "running",
  "vt_symbol": "rb2410.SHFE", "gateway_name": "CTP.1"
}}

// 错误
{ "type": "error", "data": { "code": "PERMISSION_DENIED", "message": "无权限订阅该账户" } }

// 心跳回包
{ "type": "pong", "data": {} }
```

## 4. 序列化约定

| vnpy 类型 | 前端表示 |
|---|---|
| `datetime` | ISO 8601 字符串（含时区，毫秒） |
| `Direction/Offset/OrderType/Status` 枚举 | 大写字符串（`LONG`/`OPEN`/`LIMIT`/`PART_TRADED`） |
| 浮点价格/数量 | 数字（前端负责格式化） |
| 空字段 | `null` |

## 5. 连接生命周期

1. 建立 WS 连接 → 客户端立即发 `auth`。
2. 服务端校验 JWT → 回 `auth_ok`（含用户可见账户列表）或 `error` 并断开。
3. 客户端按需 `subscribe`；服务端按"用户可见账户"过滤后推送。
4. 客户端定时 `ping`，服务端回 `pong`；超时/异常断开 → 客户端指数退避重连。
5. 重连成功后重新 `auth` + `subscribe`，并拉取一次快照（资金/持仓/活动委托）补全状态。
