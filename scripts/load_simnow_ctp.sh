#!/usr/bin/env bash
# Overlay SimNow official Mac CTP v6.7.13 into vnpy_ctp, then rebuild.
# Does not start the app. Never copies passwords.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPS_CTP="${ROOT}/.deps/vnpy_ctp"
VENDOR_MAC="${ROOT}/vendor/simnow-ctp/macos"
INCLUDE_DST="${DEPS_CTP}/vnpy_ctp/api/include/mac/ctp"
API_DST="${DEPS_CTP}/vnpy_ctp/api"

CANDIDATES=(
  "${STABX_SIMNOW_CTP:-}"
  "${VENDOR_MAC}"
  "/Users/x/Documents/Stabx/simnow-ctp/production/api/macos"
)

SRC=""
for cand in "${CANDIDATES[@]}"; do
  if [[ -n "${cand}" && -d "${cand}/thosttraderapi_se.framework" && -d "${cand}/thostmduserapi_se.framework" ]]; then
    SRC="${cand}"
    break
  fi
done

if [[ -z "${SRC}" ]]; then
  echo "找不到 SimNow Mac CTP framework。" >&2
  echo "请将 thostmduserapi_se.framework / thosttraderapi_se.framework 放到：" >&2
  echo "  ${VENDOR_MAC}" >&2
  echo "或设置 STABX_SIMNOW_CTP 指向含上述 framework 的目录。" >&2
  echo "下载：https://www.simnow.com.cn/static/apiDownload.action （Mac v6.7.13）" >&2
  exit 1
fi

if [[ ! -d "${DEPS_CTP}/vnpy_ctp/api" ]]; then
  echo "缺少 ${DEPS_CTP}。请先 clone vnpy_ctp（install_macos.sh 会做）。" >&2
  exit 1
fi

mkdir -p "${VENDOR_MAC}"
if [[ "${SRC}" != "${VENDOR_MAC}" ]]; then
  echo "同步 SimNow framework → vendor/simnow-ctp/macos/"
  rsync -a --delete \
    "${SRC}/thostmduserapi_se.framework/" "${VENDOR_MAC}/thostmduserapi_se.framework/"
  rsync -a --delete \
    "${SRC}/thosttraderapi_se.framework/" "${VENDOR_MAC}/thosttraderapi_se.framework/"
  SRC="${VENDOR_MAC}"
fi

echo "覆盖 vnpy_ctp Mac framework（SimNow v6.7.13）"
rm -rf "${API_DST}/thostmduserapi_se.framework" "${API_DST}/thosttraderapi_se.framework"
rsync -a "${SRC}/thostmduserapi_se.framework" "${API_DST}/"
rsync -a "${SRC}/thosttraderapi_se.framework" "${API_DST}/"

mkdir -p "${INCLUDE_DST}"
cp -f "${SRC}/thostmduserapi_se.framework/Versions/A/Headers/ThostFtdcMdApi.h" "${INCLUDE_DST}/"
cp -f "${SRC}/thostmduserapi_se.framework/Versions/A/Headers/ThostFtdcUserApiDataType.h" "${INCLUDE_DST}/"
cp -f "${SRC}/thostmduserapi_se.framework/Versions/A/Headers/ThostFtdcUserApiStruct.h" "${INCLUDE_DST}/"
cp -f "${SRC}/thosttraderapi_se.framework/Versions/A/Headers/ThostFtdcTraderApi.h" "${INCLUDE_DST}/"
# Trader headers also ship UserApi* ; keep trader copies if they differ
cp -f "${SRC}/thosttraderapi_se.framework/Versions/A/Headers/ThostFtdcUserApiDataType.h" "${INCLUDE_DST}/"
cp -f "${SRC}/thosttraderapi_se.framework/Versions/A/Headers/ThostFtdcUserApiStruct.h" "${INCLUDE_DST}/"

# 6.7.13 Create* 增加 bIsProductionMode，默认 true。显式传入生产模式以连 SimNow 看穿式前置。
TD="${DEPS_CTP}/vnpy_ctp/api/vnctp/vnctptd/vnctptd.cpp"
MD="${DEPS_CTP}/vnpy_ctp/api/vnctp/vnctpmd/vnctpmd.cpp"
python3 - "${TD}" "${MD}" <<'PY'
from pathlib import Path
import sys

td, md = Path(sys.argv[1]), Path(sys.argv[2])
replacements = (
    (td, b"CThostFtdcTraderApi::CreateFtdcTraderApi(pszFlowPath.c_str());",
         b"CThostFtdcTraderApi::CreateFtdcTraderApi(pszFlowPath.c_str(), true);"),
    (md, b"CThostFtdcMdApi::CreateFtdcMdApi(pszFlowPath.c_str());",
         b"CThostFtdcMdApi::CreateFtdcMdApi(pszFlowPath.c_str(), false, false, true);"),
)
for path, old, new in replacements:
    data = path.read_bytes()
    if new in data:
        print(f"already patched: {path.name}")
        continue
    if old not in data:
        raise SystemExit(f"Create API call not found in {path}")
    path.write_bytes(data.replace(old, new, 1))
    print(f"patched: {path.name}")

# Mac 6.7.13 内嵌采集，ReqUserLogin 不再要 systemInfo 两参
td_data = td.read_bytes()
old_login = b'\t\tint i = this->api->ReqUserLogin(&myreq, reqid, 2, "vn");'
new_login = b'\t\tint i = this->api->ReqUserLogin(&myreq, reqid);'
if old_login in td_data:
    td.write_bytes(td_data.replace(old_login, new_login, 1))
    print("patched: ReqUserLogin (Mac 6.7.13 两参)")
elif new_login in td_data:
    print("already patched: ReqUserLogin")
else:
    raise SystemExit("Mac ReqUserLogin call not found in vnctptd.cpp")
PY

echo "SimNow CTP 已覆盖到 ${DEPS_CTP}（源: ${SRC}）"
