import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUTPUT = ROOT / "output"
sys.path.insert(0, str(SRC))
from common import record_attempt  # noqa: E402

STEPS = {
    1: ("01_demand_scout.py", "Buscar demanda"),
    2: ("02_developer_qa.py", "Desarrollar y pasar QA automática"),
    3: ("03_demo_recorder.py", "Grabar demo"),
    4: ("04_sales_stripe.py", "Crear pago y propuesta"),
    5: ("05_report.py", "Informe de progreso (demanda + ventas)"),
}
NO_OPPORTUNITY = 2  # código de salida del paso 1 cuando no hay nada nuevo/viable


def run_step(n: int, extra=()) -> int:
    script, label = STEPS[n]
    print(f"\n>>> PASO {n}: {label} ({script}) <<<\n")
    return subprocess.run([sys.executable, str(SRC / script), *extra], cwd=ROOT).returncode


def load_opportunity() -> dict:
    f = OUTPUT / "opportunity.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def ask(prompt: str) -> bool:
    return input(prompt).strip().lower() in ("s", "si", "sí", "y", "yes")


def human_qa_gate(opp: dict, skip: bool) -> bool:
    """La QA automática del paso 2 solo comprueba que la app carga sin errores,
    NUNCA que hace bien su trabajo. Un conversor de CSV puede pasar esa QA y
    generar datos incorrectos. Probarla tú mismo con datos reales antes de
    venderla es tu responsabilidad: este gate es obligatorio por defecto."""
    app_name = opp.get("app_name", "")
    app_folder = OUTPUT / app_name
    target = app_folder / ("popup.html" if opp.get("solution_type") == "chrome_extension" else "index.html")
    print("\n--- REVISIÓN HUMANA: PRUEBA LA HERRAMIENTA TÚ MISMO ---")
    print(f"App:      {app_name}  ({opp.get('solution_type')})")
    print(f"Problema: {opp.get('pain_summary')}")
    print(f"Abre:     {target}")
    print("Pruébala con datos REALES parecidos al caso de uso, no datos de prueba.")
    print("Verifica sobre todo que el RESULTADO es correcto, no solo que la interfaz no falla.")
    if skip:
        print("[--skip-human-qa] Gate omitido manualmente. Asumes la responsabilidad.")
        return True
    return ask("\n¿Has probado la herramienta y el resultado es correcto? [s/N]: ")


def sales_gate(opp: dict, skip: bool) -> bool:
    p = opp.get("pricing", {})
    print("\n--- REVISIÓN HUMANA: ANTES DE CREAR EL COBRO Y LA PROPUESTA ---")
    print(f"Post origen: {opp.get('selected_post', {}).get('url')}")
    print(f"Riesgo de demanda detectado por el análisis: {opp.get('demand_risk', 'No evaluado')}")
    print(f"Precio sugerido (fórmula automática, revísalo): {p.get('calculated_amount')} {p.get('currency')} ({p.get('model')})")
    print("Recuerda:")
    print(" - Un post de Reddit no es demanda validada: comprueba que el problema sigue sin resolver")
    print("   y que no hay ya una alternativa gratuita obvia.")
    print(" - El precio es una sugerencia; ajústalo a lo que el mercado pagaría de verdad.")
    print(" - NO se envía ningún DM automáticamente. El texto queda en un .txt para que lo revises")
    print("   y lo mandes tú, o mejor: respóndelo públicamente en el hilo si la comunidad lo permite.")
    if skip:
        print("[--skip-sales-gate] Gate omitido manualmente.")
        return True
    return ask("\n¿Crear el enlace de pago y la propuesta de todos modos? [s/N]: ")


def main():
    ap = argparse.ArgumentParser(description="Pipeline de micro-apps (uso manual y supervisado)")
    ap.add_argument("--from-step", type=int, choices=STEPS, default=1, help="Reanudar desde este paso")
    ap.add_argument("--only", type=int, choices=STEPS, help="Ejecutar solo un paso")
    ap.add_argument("--skip-human-qa", action="store_true",
                    help="Omite la revisión manual de que la app funciona bien (NO recomendado)")
    ap.add_argument("--skip-sales-gate", action="store_true",
                    help="Omite la confirmación antes de crear el cobro (NO recomendado)")
    ap.add_argument("--live", action="store_true", help="Permitir clave live de Stripe")
    ap.add_argument("--debug", action="store_true",
                    help="En el paso 1, muestra el top 5 de candidatas con puntuación y motivo")
    args = ap.parse_args()

    steps = [args.only] if args.only else [n for n in STEPS if n >= args.from_step]
    for n in steps:
        if n == 2:
            rc = run_step(2)
            opp = load_opportunity()
            url = opp.get("selected_post", {}).get("url")
            if rc != 0:
                if url:
                    record_attempt(url, success=False)  # reintentable hasta MAX_ATTEMPTS_PER_POST
                print("\n[!] Detenido por error en el paso 2 (QA automática).")
                sys.exit(rc)
            if not human_qa_gate(opp, args.skip_human_qa):
                print("[-] Cancelado tras la revisión manual. El post queda disponible para reintentar.")
                return
            if url:
                record_attempt(url, success=True)
            continue

        if n == 4:
            opp = load_opportunity()
            if not sales_gate(opp, args.skip_sales_gate):
                print("Cancelado antes del paso 4.")
                return

        extra = ()
        if n == 4 and args.live:
            extra = ("--live",)
        elif n == 1 and args.debug:
            extra = ("--debug",)
        rc = run_step(n, extra)
        if n == 1 and rc == NO_OPPORTUNITY:
            print("\n[-] Sin oportunidades nuevas/viables ahora. Prueba más tarde.")
            return
        if rc != 0:
            print(f"\n[!] Detenido por error en el paso {n}")
            sys.exit(rc)

    print("\n[✓] CICLO COMPLETO FINALIZADO.")
    print("Recuerda: el mensaje de venta NO se envía solo. Revísalo en output/ antes de mandarlo.")


if __name__ == "__main__":
    main()
