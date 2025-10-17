from playwright.sync_api import sync_playwright
from pathlib import Path
import pandas as pd
import csv, re, json, os, time

# ====== Configuración global ======
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
os.environ["PYPPETEER_HOME"] = "/root/.cache/ms-playwright"

URLS = {
    "Recibidos": "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/recibidos/comprobantesRecibidos.jsf",
    "Emitidos":  "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/emitidos/comprobantesEmitidos.jsf",
}

TIPOS_MAP = {
    "Facturas": "Factura",
    "Retenciones": "Comprobante de Retención",
    "Notas de crédito": "Notas de Crédito",
    "Notas de débito": "Notas de Débito",
    "Liquidación de compra": "Liquidación de compra de bienes y prestación de servicios",
}

# ====== Funciones auxiliares ======
def _mes_a_texto(mes: int) -> str:
    return ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][mes-1]

def _es_clave(valor: str) -> bool:
    return bool(re.fullmatch(r"\d{49}", (valor or "").strip()))

def _detectar_delimitador(sample: str) -> str:
    counts = { ';': sample.count(';'), ',': sample.count(','), '\t': sample.count('\t') }
    return max(counts, key=counts.get) if any(counts.values()) else ';'

def _extraer_claves_desde_txt(txt_path: Path):
    claves = []
    sample = txt_path.read_text(encoding="utf-8", errors="ignore")[:4096]
    sep = _detectar_delimitador(sample)
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f, delimiter=sep)
        for row in reader:
            if not row: 
                continue
            clave = next((c.strip() for c in row if _es_clave(c)), None)
            if not clave:
                continue
            tipo = next((c.strip() for c in row if c.lower().startswith(("factura","comprobante","nota","liquidación"))), "")
            fecha = next((c.strip() for c in row if re.fullmatch(r"\d{2}/\d{2}/\d{4}", c.strip())), "")
            claves.append({"clave": clave, "tipo": tipo, "fecha": fecha})
    return claves

def _click_texto(page, texto: str) -> bool:
    for metodo in [
        lambda: page.get_by_role("button", name=texto, exact=False),
        lambda: page.get_by_text(texto, exact=False),
        lambda: page.locator(f"//button[contains(., '{texto}') or @title[contains(.,'{texto}')]]")
    ]:
        try:
            metodo().first.click(timeout=3000)
            return True
        except Exception:
            continue
    return False

def _seleccionar(page, etiqueta: str, valor_visible: str):
    try:
        sel = page.get_by_label(etiqueta, exact=False).locator("select")
        sel.select_option(label=valor_visible)
        return
    except Exception:
        pass
    try:
        page.locator(f"text={etiqueta}").locator("xpath=..").locator("select").select_option(label=valor_visible)
    except Exception:
        pass

def _espera_captcha(page):
    try:
        loc = page.locator("img[alt='captcha']")
        if loc.is_visible(timeout=1500):
            page.wait_for_selector("img[alt='captcha']", state="detached", timeout=60000)
    except Exception:
        pass

def _login(context, page, ruc, clave, cookies_path: Path):
    if cookies_path.exists():
        try:
            context.add_cookies(json.loads(cookies_path.read_text()))
            return
        except Exception:
            pass
    page.goto("https://srienlinea.sri.gob.ec/sri-en-linea/inicio/NAT", timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    try:
        page.fill("input[name='usuario']", ruc)
        page.fill("input[name='password']", clave)
    except Exception:
        page.get_by_placeholder("Ruc/Cédula/Pasaporte").fill(ruc)
        page.get_by_placeholder("Contraseña").fill(clave)
    _espera_captcha(page)
    _click_texto(page, "Ingresar")
    page.wait_for_load_state("networkidle")
    try:
        cookies_path.write_text(json.dumps(context.cookies()))
    except Exception:
        pass

# ============================================================
# 🔹 DESCARGA DE COMPROBANTES RECIBIDOS (TXT + XML + PDF)
# ============================================================
def _flujo_recibidos(page, destino: Path, anio: int, mes: int, tipo: str, formatos: list):
    _seleccionar(page, "Período emisión", str(anio))
    _seleccionar(page, "Período emisión", _mes_a_texto(mes))
    try: _seleccionar(page, "Período emisión", "Todos")
    except Exception: pass
    tipo_visible = TIPOS_MAP.get(tipo, tipo)
    _seleccionar(page, "Tipo de comprobante", tipo_visible)
    _click_texto(page, "Consultar")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    with page.expect_download() as dl_info:
        if not _click_texto(page, "Descargar reporte"):
            raise RuntimeError("No se encontró el botón 'Descargar reporte'.")
    dl = dl_info.value
    txt_path = destino / (dl.suggested_filename or f"RECIBIDOS_{anio}_{mes:02d}.txt")
    dl.save_as(str(txt_path))
    claves = _extraer_claves_desde_txt(txt_path)

    destino_xml = destino / "XML"; destino_pdf = destino / "PDF"
    destino_xml.mkdir(exist_ok=True); destino_pdf.mkdir(exist_ok=True)
    n_xml = n_pdf = 0

    for i, item in enumerate(claves, start=1):
        clave = item["clave"]
        try:
            page.goto(URLS["Recibidos"], timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            _espera_captcha(page)
            page.get_by_text("Clave de acceso", exact=False).click()
            page.fill("input", clave)
            _click_texto(page, "Consultar")
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            if "XML" in formatos:
                with page.expect_download() as dlinfo:
                    _click_texto(page, "XML") or _click_texto(page, "Descargar XML")
                d = dlinfo.value
                d.save_as(str(destino_xml / f"{clave}.xml"))
                n_xml += 1
            if "PDF" in formatos:
                with page.expect_download() as dlinfo:
                    _click_texto(page, "RIDE") or _click_texto(page, "PDF")
                d = dlinfo.value
                d.save_as(str(destino_pdf / f"{clave}.pdf"))
                n_pdf += 1
        except Exception as e:
            print(f"[WARN] No se pudo descargar {clave}: {e}")
            continue

    return {"estado": "ok", "n_xml": n_xml, "n_pdf": n_pdf, "txt": str(txt_path)}

# ============================================================
# 🔹 LECTURA DE TABLA PARA COMPROBANTES EMITIDOS (sin TXT)
# ============================================================
def _flujo_emitidos(page, destino: Path, anio: int, mes: int, tipo: str):
    _seleccionar(page, "Período emisión", str(anio))
    _seleccionar(page, "Período emisión", _mes_a_texto(mes))
    tipo_visible = TIPOS_MAP.get(tipo, tipo)
    _seleccionar(page, "Tipo de comprobante", tipo_visible)
    _click_texto(page, "Consultar")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    html = page.content()
    rows = re.findall(
        r"<tr[^>]*>\s*(.*?)\s*</tr>",
        html,
        flags=re.DOTALL
    )

    data = []
    for r in rows:
        cols = re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.DOTALL)
        if len(cols) < 6:
            continue
        data.append({
            "Fecha Emisión": re.sub("<.*?>", "", cols[0]).strip(),
            "Tipo": re.sub("<.*?>", "", cols[1]).strip(),
            "Número": re.sub("<.*?>", "", cols[2]).strip(),
            "RUC Receptor": re.sub("<.*?>", "", cols[3]).strip(),
            "Razón Social": re.sub("<.*?>", "", cols[4]).strip(),
            "Total": re.sub("<.*?>", "", cols[5]).strip(),
            "Estado": re.sub("<.*?>", "", cols[6]).strip() if len(cols) > 6 else "",
        })

    if not data:
        return {"estado": "sin_resultados", "mensaje": "No se encontraron filas en la tabla"}

    df = pd.DataFrame(data)
    excel_path = destino / f"emitidos_reporte_{anio}_{mes:02d}.xlsx"
    df.to_excel(excel_path, index=False)
    return {"estado": "ok", "n_registros": len(df), "reporte": str(excel_path)}

# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================
def descargar_sri(ruc: str, clave: str, anio: int, mes: int, tipo: str, formatos: list, destino: Path, origen: str = "Recibidos"):
    destino.mkdir(parents=True, exist_ok=True)
    cookies_path = Path(f"cookies_{ruc}.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        _login(context, page, ruc, clave, cookies_path)
        page.goto(URLS.get(origen, URLS["Recibidos"]), timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        _espera_captcha(page)

        if origen == "Emitidos":
            resultado = _flujo_emitidos(page, destino, anio, mes, tipo)
        else:
            resultado = _flujo_recibidos(page, destino, anio, mes, tipo, formatos)

        browser.close()
        return resultado
