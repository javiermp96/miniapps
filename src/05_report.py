"""Agente 05: cierra el círculo. Lee scan_log.csv (demanda analizada) y sales_funnel.csv
(resultados de venta) para sugerir ajustes con datos reales, en vez de a ojo.

Uso: python src/05_report.py
"""
import csv
from collections import Counter, defaultdict
from statistics import mean

from common import OUTPUT_DIR

SCAN_LOG = OUTPUT_DIR / "scan_log.csv"
FUNNEL_LOG = OUTPUT_DIR / "sales_funnel.csv"


def read_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def report_demand(rows):
    print("\n" + "=" * 60)
    print("DEMANDA (output/scan_log.csv)")
    print("=" * 60)
    if not rows:
        print("Sin ejecuciones registradas todavía.")
        return
    scores = [float(r["top_score"]) for r in rows if r.get("top_score")]
    viable = sum(1 for r in rows if r.get("viable") == "True")
    print(f"Ejecuciones: {len(rows)}  |  Con oportunidad viable: {viable} "
         f"({viable / len(rows) * 100:.0f}%)")
    if scores:
        print(f"Puntuación máxima media por ejecución: {mean(scores):.1f}")
        print(f"Puntuación máxima, últimas 5 ejecuciones: "
             f"{[round(s,1) for s in scores[-5:]]}")
    if len(scores) >= 10:
        first_half = mean(scores[:len(scores)//2])
        second_half = mean(scores[len(scores)//2:])
        if second_half > first_half + 0.5:
            print(f"Tendencia: SUBIENDO ({first_half:.1f} -> {second_half:.1f}). Probablemente "
                 f"solo falte paciencia/volumen, no un cambio de criterio.")
        elif second_half < first_half - 0.5:
            print(f"Tendencia: BAJANDO ({first_half:.1f} -> {second_half:.1f}). Las fuentes "
                 f"configuradas podrían estarse agotando (revisa SOURCES/REDDIT_SUBREDDITS).")
        else:
            print(f"Tendencia: ESTABLE (~{first_half:.1f}). El criterio parece calibrado; "
                 f"el ritmo de hallazgos depende del volumen de fuentes.")


def report_sales(rows):
    print("\n" + "=" * 60)
    print("VENTAS (output/sales_funnel.csv)")
    print("=" * 60)
    if not rows:
        print("Sin envíos registrados todavía. Usa --log-outcome en el paso 4 para registrar.")
        return

    by_status = Counter(r["status"] for r in rows)
    by_channel = Counter(r["channel"] for r in rows)
    print(f"Envíos totales: {len(rows)}")
    print(f"Por estado: {dict(by_status)}")
    print(f"Por canal:  {dict(by_channel)}")

    resolved = [r for r in rows if r["status"] != "sent"]
    if len(resolved) < 3:
        print(f"\nSolo {len(resolved)} envío(s) con resultado conocido todavía — "
             f"demasiado pocos para sacar conclusiones fiables. Sigue registrando "
             f"resultados con --log-outcome.")
        return

    # Conversión por canal (sobre los que ya tienen un resultado distinto de 'sent')
    print("\n--- Conversión por canal ---")
    by_channel_resolved = defaultdict(list)
    for r in resolved:
        by_channel_resolved[r["channel"]].append(r["status"])
    for channel, statuses in by_channel_resolved.items():
        positive = sum(1 for s in statuses if s in ("replied_positive", "sold"))
        print(f"  {channel}: {positive}/{len(statuses)} positivos "
             f"({positive / len(statuses) * 100:.0f}%)")

    if "dm" in by_channel_resolved and "public_reply" in by_channel_resolved:
        dm_rate = sum(1 for s in by_channel_resolved["dm"] if s in ("replied_positive", "sold")) \
            / len(by_channel_resolved["dm"])
        pub_rate = sum(1 for s in by_channel_resolved["public_reply"] if s in ("replied_positive", "sold")) \
            / len(by_channel_resolved["public_reply"])
        if pub_rate > dm_rate:
            print(f"\n  -> La respuesta pública convierte mejor ({pub_rate*100:.0f}% vs "
                 f"{dm_rate*100:.0f}%). Prioriza ese canal en los próximos envíos.")
        elif dm_rate > pub_rate:
            print(f"\n  -> El DM convierte mejor en tus datos ({dm_rate*100:.0f}% vs "
                 f"{pub_rate*100:.0f}%), contra lo esperado. Con pocos envíos puede ser ruido; "
                 f"sigue registrando antes de decidir del todo.")

    sold = by_status.get("sold", 0)
    if len(resolved) >= 5 and sold == 0:
        print("\n  -> 5+ resultados conocidos y 0 ventas: normal en frío a este volumen. "
             "Si casi todo fue 'dm', prueba 'public_reply' antes de concluir que el "
             "producto falla. Si ya probaste ambos canales sin éxito, el problema puede "
             "estar en el PRECIO o en la validación de demanda (revisa 'demand_risk' de "
             "cada oportunidad antes de ofrecerla).")


def main():
    scan_rows = read_csv(SCAN_LOG)
    funnel_rows = read_csv(FUNNEL_LOG)
    report_demand(scan_rows)
    report_sales(funnel_rows)
    print()


if __name__ == "__main__":
    main()
