import { productNameFromCode } from "../workbench/liveMap";

export type ContractRow = Record<string, unknown>;

export const EXCHANGE_LABELS: Record<string, string> = {
  CFFEX: "中金所",
  SHFE: "上期所",
  INE: "能源中心",
  DCE: "大商所",
  CZCE: "郑商所",
  GFEX: "广期所",
};

export const INDEX_PRODUCTS = new Set(["IF", "IH", "IC", "IM", "T", "TF", "TS", "TL"]);

export type BoardTab = "all" | "main" | "index" | "product";

export type ContractGroup = {
  key: string;
  title: string;
  hint?: string;
  rows: ContractRow[];
};

export function productCode(symbol: unknown): string {
  const m = String(symbol || "").trim().match(/^([A-Za-z]+)/);
  return (m?.[1] || String(symbol || "")).toUpperCase();
}

export function productName(row: ContractRow): string {
  const raw = String(row.name || "").replace(/\d+/g, "").trim();
  const code = productCode(row.symbol);
  if (raw && raw.toUpperCase() !== code && raw.toUpperCase() !== String(row.symbol || "").toUpperCase()) {
    return raw;
  }
  return productNameFromCode(String(row.symbol || "")) || code;
}

export function exchangeLabel(exchange: unknown): string {
  const key = String(exchange || "").toUpperCase();
  return EXCHANGE_LABELS[key] || key || "其他";
}

export function contractKey(row: ContractRow | null | undefined): string {
  if (!row) return "";
  return `${String(row.exchange || "").toUpperCase()}.${String(row.symbol || "").toUpperCase()}`;
}

export function isIndexContract(row: ContractRow): boolean {
  if (INDEX_PRODUCTS.has(productCode(row.symbol))) return true;
  return String(row.name || "").includes("指数");
}

function monthRank(symbol: unknown): number {
  const m = String(symbol || "").match(/(\d{3,4})$/);
  return m ? Number(m[1]) : Number.MAX_SAFE_INTEGER;
}

export function pickMainContracts(rows: ContractRow[], ticks: Record<string, Record<string, unknown>>): ContractRow[] {
  const byProduct = new Map<string, ContractRow[]>();
  for (const row of rows) {
    const key = `${String(row.exchange || "").toUpperCase()}:${productCode(row.symbol)}`;
    const list = byProduct.get(key) || [];
    list.push(row);
    byProduct.set(key, list);
  }

  const tickList = Object.values(ticks);
  const picked: ContractRow[] = [];
  for (const list of byProduct.values()) {
    const scored = list.map((row) => {
      const tick = tickList.find(
        (t) =>
          String(t.symbol).toUpperCase() === String(row.symbol).toUpperCase() &&
          String(t.exchange).toUpperCase() === String(row.exchange).toUpperCase(),
      );
      const oi = Number(tick?.open_interest);
      const vol = Number(tick?.volume);
      return {
        row,
        oi: Number.isFinite(oi) ? oi : -1,
        vol: Number.isFinite(vol) ? vol : -1,
        month: monthRank(row.symbol),
      };
    });
    scored.sort((a, b) => b.oi - a.oi || b.vol - a.vol || a.month - b.month);
    if (scored[0]) picked.push(scored[0].row);
  }
  return picked;
}

const EXCHANGE_ORDER = ["CFFEX", "SHFE", "INE", "DCE", "CZCE", "GFEX"];

function exchangeRank(exchange: unknown): number {
  const i = EXCHANGE_ORDER.indexOf(String(exchange || "").toUpperCase());
  return i < 0 ? 99 : i;
}

export function compareContractRows(
  a: ContractRow,
  b: ContractRow,
  subscribed: ReadonlySet<string> = new Set(),
): number {
  const sa = subscribed.has(contractKey(a)) ? 0 : 1;
  const sb = subscribed.has(contractKey(b)) ? 0 : 1;
  if (sa !== sb) return sa - sb;
  const ex = exchangeRank(a.exchange) - exchangeRank(b.exchange);
  if (ex) return ex;
  const pa = productCode(a.symbol).localeCompare(productCode(b.symbol));
  if (pa) return pa;
  return String(a.symbol || "").localeCompare(String(b.symbol || ""), "en");
}

export function groupContracts(
  rows: ContractRow[],
  tab: BoardTab,
  ticks: Record<string, Record<string, unknown>>,
  subscribed: ReadonlySet<string> = new Set(),
): ContractGroup[] {
  if (tab === "main") {
    return [{
      key: "main",
      title: "主力合约",
      rows: [...pickMainContracts(rows, ticks)].sort((a, b) => compareContractRows(a, b, subscribed)),
    }];
  }
  if (tab === "index") {
    return [{
      key: "index",
      title: "股指 / 国债",
      rows: rows.filter(isIndexContract).sort((a, b) => compareContractRows(a, b, subscribed)),
    }];
  }

  const subscribedRows = rows.filter((row) => subscribed.has(contractKey(row))).sort((a, b) =>
    compareContractRows(a, b),
  );
  const rest = rows.filter((row) => !subscribed.has(contractKey(row)));
  const buckets = new Map<string, ContractGroup>();
  for (const row of rest) {
    const ex = String(row.exchange || "").toUpperCase();
    const product = productCode(row.symbol);
    const key = tab === "all" ? `ex:${ex}` : `ex:${ex}:${product}`;
    const title = tab === "all" ? exchangeLabel(ex) : `${exchangeLabel(ex)} · ${productName(row)}`;
    const group = buckets.get(key) || { key, title, hint: product, rows: [] };
    group.rows.push(row);
    buckets.set(key, group);
  }

  const groups = [...buckets.values()].sort((a, b) => {
    const ea = String(a.rows[0]?.exchange || "").toUpperCase();
    const eb = String(b.rows[0]?.exchange || "").toUpperCase();
    const ia = exchangeRank(ea);
    const ib = exchangeRank(eb);
    if (ia !== ib) return ia - ib;
    return a.title.localeCompare(b.title, "zh-CN");
  });
  for (const group of groups) {
    group.rows.sort((a, b) => compareContractRows(a, b));
  }
  if (subscribedRows.length) {
    groups.unshift({ key: "subscribed", title: "已订阅", rows: subscribedRows });
  }
  return groups;
}

/** Stable, distinct accent colors for subscribed contract list bars. */
const CONTRACT_BAR_PALETTE = [
  "#1677ff",
  "#13c2c2",
  "#52c41a",
  "#fa8c16",
  "#eb2f96",
  "#722ed1",
  "#2f54eb",
  "#a0d911",
  "#fa541c",
  "#8978ff",
  "#08979c",
  "#d4b106",
  "#c41d7f",
  "#1d39c4",
  "#d4380d",
];

function hashContractKey(key: string): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i += 1) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Deterministic per vt_symbol / contract key; unique among the given set. */
export function contractBarColors(keys: string[]): Record<string, string> {
  const unique = [...new Set(keys.map((k) => String(k || "").trim()).filter(Boolean))].sort();
  const used = new Set<number>();
  const out: Record<string, string> = {};
  const n = CONTRACT_BAR_PALETTE.length;
  for (const key of unique) {
    let idx = hashContractKey(key) % n;
    for (let step = 0; step < n && used.has(idx); step += 1) {
      idx = (idx + 1) % n;
    }
    used.add(idx);
    out[key] = CONTRACT_BAR_PALETTE[idx];
  }
  return out;
}
