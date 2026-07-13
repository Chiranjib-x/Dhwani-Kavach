"""Render an eval result dict (from eval.run) into a self-contained HTML report.

Deliberately dependency-free and inline (no CDN/JS) so it opens anywhere and can
be published as an Artifact. Theme-aware light/dark.
"""
from __future__ import annotations


def _bar(pct: float, good: bool = False) -> str:
    color = "var(--ok)" if good else "var(--bad)"
    w = max(0.0, min(1.0, pct)) * 100
    return f'<div class="bar"><span style="width:{w:.1f}%;background:{color}"></span></div>'


def _config_table(res: dict) -> str:
    n = res["configs"]["neural"]; e = res["configs"]["ensemble"]
    d = n["eer"] - e["eer"]
    verdict = ("ensemble WINS" if d > 0.001 else "ensemble loses" if d < -0.001 else "tie")
    rows = ""
    for name, m in (("Neural only", n), ("Full ensemble", e)):
        rows += (f"<tr><td>{name}</td>"
                 f"<td>{m['eer']:.1%}</td><td>{m['auc']:.3f}</td><td>{m['acc']:.1%}</td>"
                 f"<td>{m['far']:.1%}</td><td>{m['frr']:.1%}</td></tr>")
    return (f"<table><thead><tr><th>Config</th><th>EER</th><th>AUC</th><th>Acc</th>"
            f"<th>FAR</th><th>FRR</th></tr></thead><tbody>{rows}</tbody></table>"
            f'<p class="delta">Multi-layer ensemble changes EER by '
            f'<b>{-d:+.1%}</b> vs the neural detector alone &mdash; {verdict}.</p>')


def render(clean: dict, phone: dict | None) -> str:
    sections = [f"<section><h2>Clean audio</h2>"
                f"<p class='meta'>real={clean['n_real']} &middot; fake={clean['n_fake']} "
                f"&middot; op-threshold={clean['t_op']:.2f} &middot; "
                f"p50 latency {clean['latency_ms_p50']:.0f} ms</p>{_config_table(clean)}</section>"]
    if phone:
        d = phone["configs"]["ensemble"]["eer"] - clean["configs"]["ensemble"]["eer"]
        sections.append(
            f"<section><h2>Through an 8&nbsp;kHz phone line</h2>"
            f"<p class='meta'>G.711 &micro;-law telephony degradation</p>{_config_table(phone)}"
            f"<p class='delta'>A phone line costs the ensemble <b>{d:+.1%}</b> EER.</p></section>")
    body = "".join(sections)
    return f"""<title>Dhwani-Kavach &mdash; Detection Eval</title>
<style>
:root{{--bg:#fff;--fg:#0f1117;--muted:#64748b;--line:#e2e8f0;--ok:#22c55e;--bad:#ff4d6d}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1117;--fg:#f1f5f9;--muted:#94a3b8;--line:#1e293b}}}}
:root[data-theme=dark]{{--bg:#0f1117;--fg:#f1f5f9;--muted:#94a3b8;--line:#1e293b}}
:root[data-theme=light]{{--bg:#fff;--fg:#0f1117;--muted:#64748b;--line:#e2e8f0}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem}}
h1{{font-size:1.5rem}}h2{{font-size:1.1rem;margin-top:2rem}}
.meta{{color:var(--muted);font-size:.85rem;margin:.2rem 0 1rem}}
table{{border-collapse:collapse;width:100%}}th,td{{text-align:right;padding:.5rem .6rem;border-bottom:1px solid var(--line)}}
th:first-child,td:first-child{{text-align:left}}th{{color:var(--muted);font-weight:600;font-size:.8rem}}
.delta{{background:color-mix(in srgb,var(--ok) 10%,transparent);padding:.6rem .8rem;border-radius:.5rem;font-size:.9rem}}
</style>
<h1>Dhwani-Kavach &mdash; Detection Eval</h1>
<p class="meta">Neural-only vs full multi-layer ensemble. Lower EER is better.</p>
{body}
"""


if __name__ == "__main__":
    # smoke: render must produce a full HTML doc from a minimal result dict.
    fake = {"eer": 0.1, "t_eer": 0.7, "auc": 0.95, "far": 0.1, "frr": 0.1, "acc": 0.9, "n_fake": 5, "n_real": 5}
    r = {"n_real": 5, "n_fake": 5, "t_op": 0.72, "latency_ms_p50": 400.0,
         "configs": {"neural": {**fake, "eer": 0.2}, "ensemble": fake}}
    html = render(r, None)
    assert "<title>" in html and "ensemble WINS" in html
    print("report self-check ok")
