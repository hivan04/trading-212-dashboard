import { css } from "uebersicht";

export const command =
  "/Users/ivanhung/Documents/GitHub/trading-212-dashboard/venv/bin/python " +
  "/Users/ivanhung/Documents/GitHub/trading-212-dashboard/src/widget-data.py";

export const refreshFrequency = 300000; // 5 minutes

export const className = `
  top: 24px;
  right: 24px;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
`;

const SYM = { GBP: "£", USD: "$", EUR: "€" };

function fmt(v, sym) {
  const a = Math.abs(v);
  const s = v < 0 ? "-" : "";
  if (a >= 1e6) return `${s}${sym}${(a / 1e6).toFixed(2)}M`;
  if (a >= 1e3) return `${s}${sym}${(a / 1e3).toFixed(1)}K`;
  return `${s}${sym}${a.toFixed(2)}`;
}

export const render = ({ output, error }) => {
  if (error) return <div style={s.card}><p style={s.muted}>Error: {String(error)}</p></div>;

  let d = {};
  try { d = JSON.parse(output || "{}"); } catch (_) {}
  if (d.error) return <div style={s.card}><p style={s.muted}>{d.error}</p></div>;

  const sym     = SYM[d.currency] || "£";
  const pplPos  = (d.ppl || 0) >= 0;
  const pplClr  = pplPos ? "#34d399" : "#f87171";
  const now     = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div style={s.card}>
      {/* Header */}
      <div style={s.header}>
        <span style={s.title}>Portfolio</span>
        <span style={s.muted}>{now}</span>
      </div>

      <div style={s.divider} />

      {/* KPIs */}
      <div style={s.kpiRow}>
        <div style={s.kpi}>
          <div style={s.label}>Total Value</div>
          <div style={s.value}>{fmt(d.total || 0, sym)}</div>
        </div>
        <div style={s.kpi}>
          <div style={s.label}>Free Cash</div>
          <div style={s.value}>{fmt(d.free || 0, sym)}</div>
        </div>
      </div>

      <div style={{ ...s.kpi, marginBottom: 16 }}>
        <div style={s.label}>Total P&L</div>
        <div style={{ ...s.value, color: pplClr }}>
          {fmt(d.ppl || 0, sym)}{" "}
          <span style={{ fontSize: 12 }}>({(d.ppl_pct || 0) >= 0 ? "+" : ""}{(d.ppl_pct || 0).toFixed(2)}%)</span>
        </div>
      </div>

      {/* Holdings */}
      <div style={s.label}>TOP HOLDINGS</div>
      <div style={s.divider} />

      {(d.positions || []).map((p, i) => {
        const pos = p.ppl_pct >= 0;
        return (
          <div key={i} style={s.row}>
            <span style={s.ticker}>{p.ticker}</span>
            <span style={s.rowVal}>{fmt(p.value, sym)}</span>
            <span style={{ ...s.rowPct, color: pos ? "#34d399" : "#f87171" }}>
              {pos ? "+" : ""}{p.ppl_pct.toFixed(1)}%
            </span>
          </div>
        );
      })}
    </div>
  );
};

const s = {
  card: {
    width: 280,
    background: "rgba(10, 15, 28, 0.78)",
    backdropFilter: "blur(24px) saturate(180%)",
    WebkitBackdropFilter: "blur(24px) saturate(180%)",
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.08)",
    padding: "16px 18px",
    color: "#f9fafb",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  title: { fontSize: 15, fontWeight: 700, letterSpacing: "-0.3px" },
  divider: { height: 1, background: "rgba(255,255,255,0.08)", marginBottom: 12 },
  kpiRow: { display: "flex", gap: 10, marginBottom: 10 },
  kpi:   { flex: 1 },
  label: { fontSize: 9, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 },
  value: { fontSize: 15, fontWeight: 700 },
  muted: { fontSize: 11, color: "#6b7280" },
  row: {
    display: "flex",
    alignItems: "center",
    padding: "4px 0",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
  },
  ticker: { flex: 1, fontSize: 11, color: "#e5e7eb" },
  rowVal: { fontSize: 11, color: "#e5e7eb", marginRight: 8 },
  rowPct: { fontSize: 10, fontWeight: 600, minWidth: 48, textAlign: "right" },
};
