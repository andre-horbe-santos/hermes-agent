#!/usr/bin/env python3
"""Render a self-contained HTML dashboard from an Apollo snapshot."""
import argparse, html, json
from pathlib import Path

def esc(value): return html.escape("—" if value is None else str(value))
def rows(items, fields):
    if not items: return f'<tr><td colspan="{len(fields)}">Sem dados disponíveis</td></tr>'
    return "".join("<tr>" + "".join(f"<td>{esc(x.get(k))}</td>" for k, _ in fields) + "</tr>" for x in items)
def table(title, items, fields):
    heads = "".join(f"<th>{esc(label)}</th>" for _, label in fields)
    return f"<section><h2>{esc(title)}</h2><div class='table'><table><thead><tr>{heads}</tr></thead><tbody>{rows(items, fields)}</tbody></table></div></section>"
def render(d):
    m=d.get("metrics",{}); labels=[("Contas","accounts"),("Contatos","contacts"),("Ativos","active"),("Tarefas vencendo","tasks_due"),("Entregues","delivered"),("Respostas","replies"),("Respostas positivas","positive_replies"),("Reuniões","meetings"),("Oportunidades","opportunities")]
    cards="".join(f'<article class="card"><span>{a}</span><strong>{esc(m.get(b))}</strong></article>' for a,b in labels)
    flow=[("stage","Etapa"),("required","Necessário"),("planned","Planejado"),("actual","Realizado")]; seq=[("name","Sequência"),("active","Ativos"),("tasks_due","Tarefas"),("replies","Respostas"),("meetings","Reuniões")]; queue=[("due","Vencimento"),("owner","Responsável"),("type","Tipo"),("count","Qtd.")]
    alerts="".join(f'<li class="{esc(a.get("severity","info"))}"><b>{esc(a.get("title"))}</b> — {esc(a.get("detail"))}</li>' for a in d.get("alerts",[])) or "<li>Sem alertas registrados</li>"; notes="".join(f"<li>{esc(n)}</li>" for n in d.get("notes",[])) or "<li>Sem observações</li>"
    style="body{margin:0;font:15px/1.5 system-ui;color:#14231d;background:#f4f7f5}main{max-width:1180px;margin:auto;padding:32px 20px}header{background:linear-gradient(125deg,#10291f,#216e49);color:white;padding:28px;border-radius:18px}h1{margin:0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0}.card,section{background:white;border:1px solid #dce5df;border-radius:14px;padding:18px}.card span{display:block;color:#607068;font-size:13px}.card strong{font-size:27px}section{margin:16px 0}h2{margin:0 0 12px}.table{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px;text-align:left;border-bottom:1px solid #dce5df;white-space:nowrap}th{color:#607068;font-size:12px}li.high{color:#c53030}footer{color:#607068;font-size:12px}"
    return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{esc(d.get("campaign","Painel"))}</title><style>{style}</style></head><body><main><header><h1>{esc(d.get("campaign","Painel de Prospecção"))}</h1><p>Período: {esc(d.get("period"))}</p><p>Fonte: {esc(d.get("source"))} · Cobertura: {esc(d.get("coverage"))}</p></header><div class="cards">{cards}</div>{table("Deal Flow",d.get("deal_flow",[]),flow)}{table("Sequências",d.get("sequences",[]),seq)}{table("Fila operacional",d.get("queue",[]),queue)}<section><h2>Alertas</h2><ul>{alerts}</ul></section><section><h2>Observações</h2><ul>{notes}</ul></section><footer>Fotografia gerada em {esc(d.get("generated_at"))}. Apollo é a fonte oficial.</footer></main></body></html>'
def main():
    p=argparse.ArgumentParser(); p.add_argument("input",type=Path); p.add_argument("output",type=Path); a=p.parse_args(); d=json.loads(a.input.read_text(encoding="utf-8")); a.output.write_text(render(d),encoding="utf-8"); print(a.output)
if __name__ == "__main__": main()
