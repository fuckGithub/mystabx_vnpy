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
  const name = String(row.name || "").replace(/\d+/g, "").trim();
  return name || productCode(row.symbol);
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

export function groupContracts(
  rows: ContractRow[],
  tab: BoardTab,
  ticks: Record<string, Record<string, unknown>>,
): ContractGroup[] {
  if (tab === "main") {
    return [{ key: "main", title: "主力合约", rows: pickMainContracts(rows, ticks) }];
  }
  if (tab === "index") {
    return [{ key: "index", title: "股指 / 国债", rows: rows.filter(isIndexContract) }];
  }

  const source = tab === "product" ? rows : rows;
  const buckets = new Map<string, ContractGroup>();
  for (const row of source) {
    const ex = String(row.exchange || "").toUpperCase();
    const product = productCode(row.symbol);
    const key = tab === "all" ? `ex:${ex}` : `ex:${ex}:${product}`;
    const title = tab === "all" ? exchangeLabel(ex) : `${exchangeLabel(ex)} · ${productName(row)}`;
    const group = buckets.get(key) || { key, title, hint: product, rows: [] };
    group.rows.push(row);
    buckets.set(key, group);
  }

  const order = ["CFFEX", "SHFE", "INE", "DCE", "CZCE", "GFEX"];
  return [...buckets.values()].sort((a, b) => {
    const ea = String(a.rows[0]?.exchange || "").toUpperCase();
    const eb = String(b.rows[0]?.exchange || "").toUpperCase();
    const ia = order.indexOf(ea);
    const ib = order.indexOf(eb);
    if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    return a.title.localeCompare(b.title, "zh-CN");
  });
}
