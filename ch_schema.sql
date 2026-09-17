-- ClickHouse DDL aligned with docs/02. Apply once:
--   clickhouse-client --multiquery < ch_schema.sql
-- P0 does not require ClickHouse to be running for REST/WS.

CREATE DATABASE IF NOT EXISTS mystabx_vnpy;

CREATE TABLE IF NOT EXISTS mystabx_vnpy.bar_data (
    symbol        String,
    exchange      String,
    interval      String,
    datetime      DateTime64(3, 'Asia/Shanghai'),
    open_price    Float64,
    high_price    Float64,
    low_price     Float64,
    close_price   Float64,
    volume        Float64,
    turnover      Float64,
    open_interest Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(datetime)
ORDER BY (symbol, exchange, interval, datetime)
TTL datetime + INTERVAL 5 YEAR;

CREATE TABLE IF NOT EXISTS mystabx_vnpy.tick_data (
    symbol        String,
    exchange      String,
    datetime      DateTime64(3, 'Asia/Shanghai'),
    name          String,
    last_price    Float64,
    last_volume   Float64,
    volume        Float64,
    turnover      Float64,
    open_interest Float64,
    open_price    Float64, high_price Float64, low_price Float64,
    pre_close     Float64,
    limit_up      Float64, limit_down Float64,
    bid_price_1   Float64, bid_volume_1 Float64, ask_price_1 Float64, ask_volume_1 Float64,
    bid_price_2   Float64, bid_volume_2 Float64, ask_price_2 Float64, ask_volume_2 Float64,
    bid_price_3   Float64, bid_volume_3 Float64, ask_price_3 Float64, ask_volume_3 Float64,
    bid_price_4   Float64, bid_volume_4 Float64, ask_price_4 Float64, ask_volume_4 Float64,
    bid_price_5   Float64, bid_volume_5 Float64, ask_price_5 Float64, ask_volume_5 Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(datetime)
ORDER BY (symbol, exchange, datetime)
TTL datetime + INTERVAL 6 MONTH;

-- 分时 Tick：默认保留 10 个交易日（应用启动也会 CREATE IF NOT EXISTS）
CREATE TABLE IF NOT EXISTS mystabx_vnpy.market_tick (
    symbol        String,
    exchange      String,
    gateway_name  String,
    datetime      DateTime64(3, 'Asia/Shanghai'),
    trade_date    Date,
    last_price    Float64,
    last_volume   Float64,
    volume        Float64,
    turnover      Float64,
    open_interest Float64,
    bid_price_1   Float64,
    bid_volume_1  Float64,
    ask_price_1   Float64,
    ask_volume_1  Float64,
    inserted_at   DateTime64(3, 'Asia/Shanghai') DEFAULT now64(3)
) ENGINE = MergeTree()
PARTITION BY trade_date
ORDER BY (symbol, exchange, datetime)
TTL datetime + INTERVAL 10 DAY DELETE;

CREATE TABLE IF NOT EXISTS mystabx_vnpy.order_event (
    event_time  DateTime64(3, 'Asia/Shanghai'),
    order_id    String,
    gateway     String,
    symbol      String, exchange String,
    type        String, direction String, offset String,
    price       Float64, volume Float64, traded Float64,
    status      String,
    order_time  DateTime64(3, 'Asia/Shanghai'),
    user_id     Int32
) ENGINE = MergeTree()
ORDER BY (event_time, order_id)
TTL event_time + INTERVAL 3 YEAR;

CREATE TABLE IF NOT EXISTS mystabx_vnpy.trade_event (
    event_time DateTime64(3, 'Asia/Shanghai'),
    trade_id   String, order_id String,
    gateway    String,
    symbol     String, exchange String,
    direction  String, offset String,
    price      Float64, volume Float64,
    trade_time DateTime64(3, 'Asia/Shanghai'),
    user_id    Int32
) ENGINE = MergeTree()
ORDER BY (event_time, trade_id)
TTL event_time + INTERVAL 3 YEAR;

CREATE TABLE IF NOT EXISTS mystabx_vnpy.position_event (
    event_time DateTime64(3, 'Asia/Shanghai'),
    gateway    String,
    symbol     String, exchange String, direction String,
    volume     Float64, frozen Float64, price Float64,
    pnl        Float64, yd_volume Float64
) ENGINE = ReplacingMergeTree(event_time)
ORDER BY (gateway, symbol, direction);

CREATE TABLE IF NOT EXISTS mystabx_vnpy.account_event (
    event_time DateTime64(3, 'Asia/Shanghai'),
    gateway    String,
    account_id String,
    balance    Float64, frozen Float64, available Float64
) ENGINE = ReplacingMergeTree(event_time)
ORDER BY (gateway, account_id);

CREATE TABLE IF NOT EXISTS mystabx_vnpy.log_event (
    event_time DateTime64(3, 'Asia/Shanghai'),
    level      String,
    source     String,
    message    String
) ENGINE = MergeTree()
ORDER BY event_time
TTL event_time + INTERVAL 1 YEAR;

CREATE TABLE IF NOT EXISTS mystabx_vnpy.audit_log (
    event_time DateTime64(3, 'Asia/Shanghai'),
    user_id    Int32,
    gateway    String,
    action     String,
    resource   String,
    detail     String,
    ip         String,
    result     String
) ENGINE = MergeTree()
ORDER BY (event_time, user_id)
TTL event_time + INTERVAL 3 YEAR;
