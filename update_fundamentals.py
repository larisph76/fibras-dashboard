"""
update_fundamentals.py
Corre cada trimestre via GitHub Actions.
Usa Claude para buscar y actualizar NAV, distribución, FFO, AFFO y LTV
de cada FIBRA desde sus reportes públicos en BMV/BIVA.
"""

import os, re, json, requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
INDEX_FILE = "index.html"

FIBRAS = [
    "FUNO11", "DANHOS13", "FSHOP13", "FMTY14", "FIBRAPL14",
    "FIBRAMQ12", "TERRA13", "FINN13", "STORAGE", "FIBRAHD",
    "PLUSFIB", "HITES", "VESTA", "CREAL",
]

PROMPT = """Eres un analista financiero especializado en FIBRAs mexicanas (BMV/BIVA).

Tu tarea: proporcionar los datos fundamentales MÁS RECIENTES disponibles públicamente para las siguientes FIBRAs mexicanas, basándote en sus últimos reportes trimestrales (disponibles en BMV, BIVA o sus páginas de relación con inversionistas).

FIBRAs: {tickers}

Para cada FIBRA devuelve un JSON con EXACTAMENTE estas claves:
- ticker: string (ej. "FUNO11")
- nav: number — NAV por CBFI en MXN (Patrimonio neto / CBFIs en circulación)
- dist: number — Distribución anual por CBFI en MXN (suma de los últimos 4 trimestres)
- ffo: number — FFO anualizado por CBFI en MXN
- affo: number — AFFO anualizado por CBFI en MXN
- ltv: number — Loan-to-Value como decimal (ej. 0.42 para 42%)
- sector: string — sector de la FIBRA

Responde ÚNICAMENTE con un array JSON válido, sin texto adicional, sin markdown, sin backticks.
Si no tienes datos recientes de alguna FIBRA, usa los valores más cercanos que conozcas y marca ltv con el valor que tengas.
Ejemplo de formato:
[{{"ticker":"FUNO11","nav":18.50,"dist":1.25,"ffo":1.80,"affo":1.60,"ltv":0.42,"sector":"Diversificado"}}]
"""

def get_updated_data():
    tickers_str = ", ".join(FIBRAS)
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": PROMPT.format(tickers=tickers_str)}],
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "interleaved-thinking-2025-05-14",
        "Content-Type": "application/json",
    }
    resp = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    result = resp.json()

    # Extract text from content blocks
    text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")

    # Parse JSON
    text = text.strip()
    # Remove markdown fences if present
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)

def update_index_html(fibras_data):
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Build new FIBRAS JS array
    lines = ["const FIBRAS = ["]
    for d in fibras_data:
        lines.append(
            f'  {{ ticker:"{d["ticker"]}", nav:{d["nav"]}, dist:{d["dist"]}, '
            f'ffo:{d["ffo"]}, affo:{d["affo"]}, ltv:{d["ltv"]}, sector:"{d["sector"]}" }},'
        )
    lines.append("];")
    new_block = "\n".join(lines)

    # Replace existing FIBRAS array
    pattern = r"const FIBRAS = \[[\s\S]*?\];"
    updated_html = re.sub(pattern, new_block, html)

    # Update fundamental date comment
    from datetime import date
    date_str = date.today().strftime("%d/%m/%Y")
    # Insert/update comment near the FIBRAS array
    updated_html = updated_html.replace(
        "// ── Datos fundamentales (actualizados automáticamente cada trimestre) ──────",
        f"// ── Datos fundamentales — última actualización automática: {date_str} ──────"
    )

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(updated_html)
    print(f"✅ index.html actualizado con datos al {date_str}")

if __name__ == "__main__":
    print("🔍 Buscando datos fundamentales más recientes de FIBRAs...")
    fibras_data = get_updated_data()
    print(f"✅ Datos obtenidos para {len(fibras_data)} FIBRAs")
    for d in fibras_data:
        print(f"   {d['ticker']}: NAV={d['nav']}, dist={d['dist']}, LTV={d['ltv']:.0%}")
    update_index_html(fibras_data)
