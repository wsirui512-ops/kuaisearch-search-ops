"""One experiment contract shared by deck, HTML, report and validation."""
import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/experiments.json").read_text(encoding="utf-8"))
normal = NormalDist()
p0 = CONFIG["baseline"]
p1 = p0 + CONFIG["mde_pp"] / 100
pooled = (p0 + p1) / 2
N_PER_ARM = math.ceil(((normal.inv_cdf(1-CONFIG["alpha"]/2) * math.sqrt(2*pooled*(1-pooled))
                       + normal.inv_cdf(CONFIG["power"]) * math.sqrt(p0*(1-p0)+p1*(1-p1))) / (p1-p0))**2)
SAMPLE = f"每臂 {N_PER_ARM:,} 用户（主指标下限）"
ACTIONS = [(name, what, CONFIG["metric"], owner, SAMPLE) for name, what, owner in CONFIG["owner_actions"]]

if __name__ == "__main__":
    print(f"alpha={CONFIG['alpha']} power={CONFIG['power']} p0={p0} p1={p1} {SAMPLE}")
