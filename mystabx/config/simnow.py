"""SimNow CTP address constants. Never put account or password here."""

# Session-hours environment (use during exchange hours)
SIMNOW_SESSION = {
    "td": "182.254.243.31:30001",
    "md": "182.254.243.31:30011",
}

# 7x24 test environment (new accounts may need several trading days)
SIMNOW_24H = {
    "td": "182.254.243.31:40001",
    "md": "182.254.243.31:40011",
}

# Keys match CtpGateway.default_setting (Chinese field names).
# 柜台环境=实盘: Mac only ships the production CTP API; SimNow uses that front.
SIMNOW_CONNECT_DEFAULTS: dict[str, str] = {
    "经纪商代码": "9999",
    "交易服务器": SIMNOW_SESSION["td"],
    "行情服务器": SIMNOW_SESSION["md"],
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "柜台环境": "实盘",
}

CONNECT_FILENAME = "connect_ctp.json"
SECRET_FIELDS = ("用户名", "密码")
