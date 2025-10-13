from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime
import csv, re, json, os, time

# ====== Playwright en Docker/Render ======
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
os.environ["PYPPETEER_HOME"] = "/root/.cache/ms-playwright"

URLS = {
    "Recibidos": "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/recibidos/comprobantesRecibidos.jsf",
    "Emitidos":  "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/emitidos/comprobantesEmitidos.jsf",
}

# Mapeo de tipos a etiquetas visibles (ajusta si tu pantalla usa otras).
TIPOS_MAP = {
    "Facturas": "Factura",
    "Retenciones": "Comprobante de Retención",
    "Notas de crédito": "Notas de Crédito",
    "Notas de débito": "Notas de Débito",
    "Liquidación de compra": "Liquidación de compra de bienes y prestación de servicios",
}

def _mes_a_texto(mes:int)->str:
    return ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][mes-1]

def _es_clave(valor:str)->bool:
    return bool(re.fullmatch(r"\d{49}", (valor or "").strip()))

def _detectar_delimitador(sample:str)->str:
    # detecta ; , o tab
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
            # Buscar columna clave (49 dígitos)
            clave = next((c.strip() for c in row if _es_clave(c)), None)
            if not clave:
                continue
            # Extras útiles si vienen en el TXT:
            tipo = next((c.strip() for c in row if c and c.strip().lower().startswith(("factura","comprobante de retención","notas de crédito","notas de débito","liquidación"))), "")
            fecha = next((c.strip() for c in row if re.fullmatch(r"\d{2}/\d{2}/\d{4}", c.strip())), "")
            claves.append({"clave": clave, "tipo": tipo, "fecha": fecha})
    return claves

def _click_texto(page, texto:str)->bool:
    try:
        page.get_by_role("button", name=texto, exact=False).click(timeout=3000); return True
    except Exception:
        pass
    try:
        page.get_by_text(texto, exact=False).click(timeout=3000); return True
    except Exception:
        pass
    try:
        page.locator(f"//button[contains(., '{texto}') or @title[contains(.,'{texto}')]]").first.click(timeout=3000); return True
    except Exception:
        return False

def _seleccionar(page, etiqueta:str, valor_visible:str):
    # Prioriza label → select; si no, busca por texto y sube al select más cercano
    try:
        sel = page.get_by_label(etiqueta, exact=False).locator("select")
        sel.select_option(label=valor_visible)
        return
    except Exception:
        pass
    try:
        page.locator(f"text={etiqueta}").locator("xpath=..").locator("select").select_option(label=valor_visible)
        return
    except Exception:
        pass
    # Último recurso: algún select en pantalla con esa opción
    try:
        all_selects = page.locator("select")
        count = all_selects.count()
        for i in range(count):
            try:
                all_selects.nth(i).select_option(label=valor_visible)
                return
            except Exception:
                continue
    except Exception:
        pass

def _espera_captcha(page):
    try:
        loc = page.locator("img[alt='captcha']")
        if loc.is_visible(timeout=1500):
            page.wait_for_selector("img[alt='captcha']", state="detached", timeout=60000)
    except Exception:
        pass

def _login_y_cookies(context, page, ruc, clave, cookies_path:Path):
    # Cookies por RUC
    if cookies_path.exists():
        try:
            context.add_cookies(json.loads(cookies_path.read_text()))
            return
        except Exception:
            pass
    # Login NAT
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
    # Guardar cookies
    try:
        cookies_path.write_text(json.dumps(context.cookies()))
    except Exception:
        pass

def _buscar_por_clave(page, clave:str):
    # Marca la opción "Clave de acceso / Nro. autorización" si existe
    try:
        page.get_by_label("Clave de acceso", exact=False).check(timeout=1500)
    except Exception:
        try:
            page.get_by_text("Clave de acceso", exact=False).click(timeout=1500)
        except Exception:
            pass
    # Completa la clave (input principal)
    try:
        page.fill("input", clave)
    except Exception:
        try:
            page.get_by_placeholder("Clave de acceso").fill(clave)
        except Exception:
            pass
    _click_texto(page, "Consultar")
    page.wait_for_load_state("networkidle")
    time.sleep(0.4)

def _descargar_xml(page, destino:Path, nombre:str)->bool:
    try:
        with page.expect_download() as dlinfo:
            # Variantes de botón/ícono
            if not (_click_texto(page, "XML") or _click_texto(page, "Descargar XML")):
                page.locator("a[title*='XML'], button[title*='XML']").first.click(timeout=2500)
        d = dlinfo.value
        d.save_as(str(destino / f"{nombre}.xml"))
        return True
    except Exception:
        return False

def _descargar_pdf(page, destino:Path, nombre:str)->bool:
    try:
        with page.expect_download() as dlinfo:
            if not (_click_texto(page, "RIDE") or _click_texto(page, "PDF") or _click_texto(page, "Descargar PDF")):
                page.locator("a[title*='PDF'], a[title*='RIDE'], button[title*='PDF']").first.click(timeout=2500)
        d = dlinfo.value
        d.save_as(str(destino / f"{nombre}.pdf"))
        return True
    except Exception:
        return False

def descargar_sri(ruc: str, clave: str, anio: int, mes: int, tipo: str, formatos: list, destino: Path, origen:str="Recibidos"):
    """
    Flujo: (Recibidos/Emitidos) -> TXT semilla -> descargar XML (+PDF si aplica).
    Retorna dict con contadores y ruta del TXT.
    """
    destino.mkdir(parents=True, exist_ok=True)
    destino_xml = destino / "XML"; destino_pdf = destino / "PDF"
    destino_xml.mkdir(exist_ok=True); destino_pdf.mkdir(exist_ok=True)

    n_xml = n_pdf = 0
    cookies_path = Path(f"cookies_{ruc}.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu","--single-process"]
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1) Login/cookies
        _login_y_cookies(context, page, ruc, clave, cookies_path)

        # 2) Ir al módulo según Origen
        url_modulo = URLS.get(origen, URLS["Recibidos"])
        page.goto(url_modulo, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        _espera_captcha(page)

        # 3) Filtros (Año, Mes, Tipo)
        try:
            _seleccionar(page, "Período emisión", str(anio))                 # Año
            _seleccionar(page, "Período emisión", _mes_a_texto(mes))         # Mes
            # Un tercer combo puede ser 'Todos' (día):
            try: _seleccionar(page, "Período emisión", "Todos")
            except Exception: pass

            tipo_visible = TIPOS_MAP.get(tipo, tipo)
            _seleccionar(page, "Tipo de comprobante", tipo_visible)
        except Exception as e:
            print(f"[WARN] Filtros no aplicados automáticamente: {e}")

        # 4) Consultar
        _click_texto(page, "Consultar")
        page.wait_for_load_state("networkidle")
        time.sleep(0.8)

        # 5) Descargar TXT (Descargar reporte)
        with page.expect_download() as dl_info:
            ok = _click_texto(page, "Descargar reporte")
            if not ok:
                raise RuntimeError("No se encontró el botón 'Descargar reporte'.")
        dl = dl_info.value
        sugerido = dl.suggested_filename or f"{origen}_{anio}_{mes:02d}.txt"
        txt_path = destino / sugerido
        dl.save_as(str(txt_path))
        print(f"[OK] TXT guardado en {txt_path}")

        # 6) Parsear TXT
        claves = _extraer_claves_desde_txt(txt_path)
        if not claves:
            browser.close()
            return {"estado":"sin_descargas","mensaje":"TXT sin claves","n_xml":0,"n_pdf":0}

        # 7) Descargar por clave (XML y/o PDF)
        for i, item in enumerate(claves, start=1):
            clave_acc = item["clave"]
            nombre_base = clave_acc  # puedes anteponer tipo/fecha si quieres
            try:
                # Re-abrir página del módulo (asegura estado limpio)
                page.goto(url_modulo, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                _espera_captcha(page)

                # Buscar por clave
                _buscar_por_clave(page, clave_acc)

                # Descargar XML
                if "XML" in formatos:
                    if _descargar_xml(page, destino_xml, nombre_base):
                        n_xml += 1

                # Descargar PDF (RIDE)
                if "PDF" in formatos:
                    if _descargar_pdf(page, destino_pdf, nombre_base):
                        n_pdf += 1

                # Anti-bloqueo leve
                time.sleep(0.2)
                if i % 20 == 0:
                    time.sleep(2)
            except Exception as e:
                print(f"[WARN] Falló descarga para {clave_acc}: {e}")
                continue

        browser.close()

    return {
        "estado": "ok" if (n_xml or n_pdf) else "sin_descargas",
        "n_xml": n_xml,
        "n_pdf": n_pdf,
        "txt": str(txt_path),
        "origen": origen
    }
