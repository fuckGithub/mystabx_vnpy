#!/usr/bin/env bash
# Overlay official SimNow CTP into vnpy_ctp, then rebuild.
# Darwin: Mac v6.7.13 .framework + Darwin-only C++ patches.
# Linux: Linux .so only — never copy Mac frameworks or apply Darwin patches.
# Does not start the app. Never copies passwords.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPS_CTP="${ROOT}/.deps/vnpy_ctp"
API_DST="${DEPS_CTP}/vnpy_ctp/api"
OS="$(uname -s)"

if [[ ! -d "${API_DST}" ]]; then
  echo "缺少 ${DEPS_CTP}。请先 clone vnpy_ctp（install_macos.sh / install_linux.sh 会做）。" >&2
  exit 1
fi

_linux_has_so() {
  local dir="$1"
  [[ -n "${dir}" && -d "${dir}" ]] || return 1
  { [[ -f "${dir}/libthostmduserapi_se.so" ]] || [[ -f "${dir}/thostmduserapi_se.so" ]]; } \
    && { [[ -f "${dir}/libthosttraderapi_se.so" ]] || [[ -f "${dir}/thosttraderapi_se.so" ]]; }
}

_copy_linux_so() {
  local src="$1" name="$2"
  if [[ -f "${src}/lib${name}" ]]; then
    cp -f "${src}/lib${name}" "${API_DST}/lib${name}"
  elif [[ -f "${src}/${name}" ]]; then
    cp -f "${src}/${name}" "${API_DST}/lib${name}"
  else
    echo "缺少 Linux CTP 动态库：${name}" >&2
    exit 1
  fi
}

load_linux_ctp() {
  local vendor_linux="${ROOT}/vendor/simnow-ctp/linux"
  local include_dst="${DEPS_CTP}/vnpy_ctp/api/include/ctp"
  local candidates=(
    "${STABX_SIMNOW_CTP:-}"
    "${vendor_linux}"
  )
  local src="" cand hdr_dir

  if [[ "${STABX_SIMNOW_CTP:-}" == *".framework"* ]]; then
    echo "STABX_SIMNOW_CTP 指向 Mac .framework，Linux 不能使用。" >&2
    echo "请改为含 libthostmduserapi_se.so / libthosttraderapi_se.so 的目录。" >&2
    exit 1
  fi

  for cand in "${candidates[@]}"; do
    if _linux_has_so "${cand}"; then
      src="${cand}"
      break
    fi
  done

  if [[ -z "${src}" ]]; then
    if [[ -f "${API_DST}/libthostmduserapi_se.so" && -f "${API_DST}/libthosttraderapi_se.so" ]]; then
      echo "未提供外部 Linux CTP，使用 vnpy_ctp 自带的 Linux .so（不要用 Mac .framework）。"
      echo "可选：把官方 Linux so 放到 ${vendor_linux} 或设置 STABX_SIMNOW_CTP。"
      return 0
    fi
    echo "找不到 Linux CTP .so。" >&2
    echo "请将 libthostmduserapi_se.so / libthosttraderapi_se.so 放到：" >&2
    echo "  ${vendor_linux}" >&2
    echo "或设置 STABX_SIMNOW_CTP 指向含上述文件的目录。" >&2
    echo "下载：https://www.simnow.com.cn/static/apiDownload.action （Linux，不要下 Mac）" >&2
    exit 1
  fi

  mkdir -p "${vendor_linux}"
  if [[ "${src}" != "${vendor_linux}" ]]; then
    echo "同步 Linux CTP .so → vendor/simnow-ctp/linux/"
    if [[ -f "${src}/libthostmduserapi_se.so" ]]; then
      cp -f "${src}/libthostmduserapi_se.so" "${vendor_linux}/libthostmduserapi_se.so"
    else
      cp -f "${src}/thostmduserapi_se.so" "${vendor_linux}/libthostmduserapi_se.so"
    fi
    if [[ -f "${src}/libthosttraderapi_se.so" ]]; then
      cp -f "${src}/libthosttraderapi_se.so" "${vendor_linux}/libthosttraderapi_se.so"
    else
      cp -f "${src}/thosttraderapi_se.so" "${vendor_linux}/libthosttraderapi_se.so"
    fi
    src="${vendor_linux}"
  fi

  echo "覆盖 vnpy_ctp Linux .so（官方 / SimNow）"
  _copy_linux_so "${src}" "thostmduserapi_se.so"
  _copy_linux_so "${src}" "thosttraderapi_se.so"

  hdr_dir=""
  for cand in "${src}" "${src}/include" "${src}/include/ctp"; do
    if [[ -f "${cand}/ThostFtdcMdApi.h" && -f "${cand}/ThostFtdcTraderApi.h" ]]; then
      hdr_dir="${cand}"
      break
    fi
  done
  if [[ -n "${hdr_dir}" ]]; then
    mkdir -p "${include_dst}"
    cp -f "${hdr_dir}/ThostFtdcMdApi.h" "${include_dst}/"
    cp -f "${hdr_dir}/ThostFtdcTraderApi.h" "${include_dst}/"
    cp -f "${hdr_dir}/ThostFtdcUserApiDataType.h" "${include_dst}/"
    cp -f "${hdr_dir}/ThostFtdcUserApiStruct.h" "${include_dst}/"
  fi

  echo "Linux CTP 已覆盖到 ${DEPS_CTP}（源: ${src}）。未应用 Darwin 补丁。"
}

apply_darwin_patches() {
  local td="${DEPS_CTP}/vnpy_ctp/api/vnctp/vnctptd/vnctptd.cpp"
  local md="${DEPS_CTP}/vnpy_ctp/api/vnctp/vnctpmd/vnctpmd.cpp"
  python3 - "${td}" "${md}" <<'PY'
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
}

load_macos_ctp() {
  local vendor_mac="${ROOT}/vendor/simnow-ctp/macos"
  local include_dst="${DEPS_CTP}/vnpy_ctp/api/include/mac/ctp"
  local candidates=(
    "${STABX_SIMNOW_CTP:-}"
    "${vendor_mac}"
    "/Users/x/Documents/Stabx/simnow-ctp/production/api/macos"
  )
  local src="" cand

  for cand in "${candidates[@]}"; do
    if [[ -n "${cand}" && -d "${cand}/thosttraderapi_se.framework" && -d "${cand}/thostmduserapi_se.framework" ]]; then
      src="${cand}"
      break
    fi
  done

  if [[ -z "${src}" ]]; then
    echo "找不到 SimNow Mac CTP framework。" >&2
    echo "请将 thostmduserapi_se.framework / thosttraderapi_se.framework 放到：" >&2
    echo "  ${vendor_mac}" >&2
    echo "或设置 STABX_SIMNOW_CTP 指向含上述 framework 的目录。" >&2
    echo "下载：https://www.simnow.com.cn/static/apiDownload.action （Mac v6.7.13）" >&2
    exit 1
  fi

  mkdir -p "${vendor_mac}"
  if [[ "${src}" != "${vendor_mac}" ]]; then
    echo "同步 SimNow framework → vendor/simnow-ctp/macos/"
    rsync -a --delete \
      "${src}/thostmduserapi_se.framework/" "${vendor_mac}/thostmduserapi_se.framework/"
    rsync -a --delete \
      "${src}/thosttraderapi_se.framework/" "${vendor_mac}/thosttraderapi_se.framework/"
    src="${vendor_mac}"
  fi

  echo "覆盖 vnpy_ctp Mac framework（SimNow v6.7.13）"
  rm -rf "${API_DST}/thostmduserapi_se.framework" "${API_DST}/thosttraderapi_se.framework"
  rsync -a "${src}/thostmduserapi_se.framework" "${API_DST}/"
  rsync -a "${src}/thosttraderapi_se.framework" "${API_DST}/"

  mkdir -p "${include_dst}"
  cp -f "${src}/thostmduserapi_se.framework/Versions/A/Headers/ThostFtdcMdApi.h" "${include_dst}/"
  cp -f "${src}/thostmduserapi_se.framework/Versions/A/Headers/ThostFtdcUserApiDataType.h" "${include_dst}/"
  cp -f "${src}/thostmduserapi_se.framework/Versions/A/Headers/ThostFtdcUserApiStruct.h" "${include_dst}/"
  cp -f "${src}/thosttraderapi_se.framework/Versions/A/Headers/ThostFtdcTraderApi.h" "${include_dst}/"
  cp -f "${src}/thosttraderapi_se.framework/Versions/A/Headers/ThostFtdcUserApiDataType.h" "${include_dst}/"
  cp -f "${src}/thosttraderapi_se.framework/Versions/A/Headers/ThostFtdcUserApiStruct.h" "${include_dst}/"

  apply_darwin_patches
  echo "SimNow CTP 已覆盖到 ${DEPS_CTP}（源: ${src}）"
}

case "${OS}" in
  Linux)
    load_linux_ctp
    ;;
  Darwin)
    load_macos_ctp
    ;;
  *)
    echo "不支持的系统：${OS}（load_simnow_ctp.sh 仅 Linux / macOS）。" >&2
    echo "Windows 请运行：powershell -File scripts/install_windows.ps1" >&2
    echo "说明：docs/11-分平台CTP搭建.md" >&2
    exit 1
    ;;
esac
