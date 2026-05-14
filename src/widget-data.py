"""Outputs portfolio JSON to stdout — called by the Übersicht widget."""
import base64, importlib.util, json, os, sys
import requests

def main():
    key_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "private", "api-key.py")
    )
    spec = importlib.util.spec_from_file_location("k", key_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    token = base64.b64encode(f"{mod.api.strip()}:{mod.secret.strip()}".encode()).decode()
    h = {"Authorization": f"Basic {token}"}
    base = "https://live.trading212.com/api/v0"

    summary  = requests.get(f"{base}/equity/account/cash", headers=h, timeout=12).json()
    raw      = requests.get(f"{base}/equity/portfolio",    headers=h, timeout=12).json()
    positions = raw if isinstance(raw, list) else raw.get("items", [])

    sorted_pos = sorted(
        positions,
        key=lambda p: float(p.get("quantity", 0)) * float(p.get("currentPrice", 0)),
        reverse=True,
    )

    pos_list = []
    for p in sorted_pos[:8]:
        qty  = float(p.get("quantity", 0))
        cur  = float(p.get("currentPrice", 0))
        avg  = float(p.get("averagePrice", 0))
        val  = qty * cur
        cost = qty * avg
        pos_list.append({
            "ticker":  p.get("ticker", "").replace("_EQ", ""),
            "value":   round(val, 2),
            "ppl_pct": round(((val - cost) / cost * 100) if cost else 0, 2),
        })

    total    = float(summary.get("total",    0))
    free     = float(summary.get("free",     0))
    invested = float(summary.get("invested", 0))
    ppl      = sum(float(p.get("ppl", 0)) for p in positions)
    cost_basis = sum(
        float(p.get("quantity", 0)) * float(p.get("averagePrice", 0))
        for p in positions
    )
    ppl_pct = (ppl / cost_basis * 100) if cost_basis else 0.0

    print(json.dumps({
        "total":     round(total, 2),
        "free":      round(free, 2),
        "ppl":       round(ppl, 2),
        "ppl_pct":   round(ppl_pct, 2),
        "currency":  summary.get("currency", "GBP"),
        "positions": pos_list,
    }))

try:
    main()
except Exception as e:
    print(json.dumps({"error": str(e)}))
