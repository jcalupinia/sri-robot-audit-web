from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime
import csv, re, json, os, time
import threading

# ============================================================
# CONFIGURACIÓN GENERAL (Playwright + Docker/Render)
# ============================================================
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

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def _mes_a_texto(mes:int)->str:
    return [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ][mes-1]

def _es_clave(valor:str)->bool:
    return bool(re.fullmatch(r"\d{49}", (valor or "").strip()))

def _detectar_delimitador(sample:str)->str:
    counts = { ';': sample.count(';'), ',': sample.count(','), '\t': sample.count('\t') }
    return max(counts, key=counts.get) if any(counts.values()) else ';'

def _extraer_claves_desde_txt(txt_path: Path):
    claves = []
    sample = txt_path.read_text(encoding="utf-8", errors="ignore")[:4096]
    sep = _detectar_delimitador(sample)
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f, delimiter=sep)
        for row in reader:
            if not row: continue
            clave = next((c.strip() for c in row if _es_clave(c)), None)
            if not clave: continue
            tipo = next((c.strip() for c in row if c.lower().startswith(
                ("factura","comprobante de retención","notas de crédito","notas de débito","liquidación"))), "")
            fecha = next((c.strip() for c in row if re.fullmatch(r"\d{2}/\d{2}/\d{4}", c.strip())), "")
            claves.append({"clave": clave, "tipo": tipo, "fecha": fecha})
    return claves

def _click_texto(page, texto:str)->bool:
    for intento in range(2):
        try:
            page.get_by_role("button", name=texto, exact=False).click(timeout=3000)
            return True
        except Exception:
            pass
        try:
            page.get_by_text(texto, exact=False).click(timeout=3000)
            return True
        except Exception:
            pass
        try:
            page.locator(f"//button[contains(., '{texto}') or @title[contains(.,'{texto}')]]").first.click(timeout=3000)
            return True
        except Exception:
            time.sleep(1)
    return False

def _seleccionar(page, etiqueta:str, valor_visible:str):
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
    try:
        all_selects = page.locator("select")
        for i in range(all_selects.count()):
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
            print("[INFO] Captcha detectado, esperando resolución...")
            page.wait_for_selector("img[alt='captcha']", state="detached", timeout=60000)
    except Exception:
        pass

def _login_y_cookies(context, page, ruc, clave, cookies_path:Path):
    if cookies_path.exists():
        try:
            context.add_cookies(json.loads(cookies_path.read_text()))
            print("[OK] Sesión restaurada desde cookies.")
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
        print("[OK] Cookies guardadas.")
    except Exception:
        pass

# ============================================================
# DESCARGA ARCHIVOS
# ============================================================
def _descargar_archivo(page, destino: Path, nombre: str, tipo: str) -> bool:
    botones = {
        "XML": ["Descargar XML", "XML", "Comprobante XML"],
        "PDF": ["Descargar PDF", "RIDE", "PDF", "Comprobante PDF"]
    }
    try:
        with page.expect_download(timeout=90000) as dlinfo:
            for texto in botones[tipo]:
                if _click_texto(page, texto):
                    break
        d = dlinfo.value
        d.save_as(str(destino / f"{nombre}.{tipo.lower()}"))
        print(f"[OK] {tipo} guardado: {nombre}")
        return True
    except Exception as e:
        print(f"[WARN] {tipo} no descargado: {e}")
        return False

# ============================================================
# DESCARGA PRINCIPAL
# ============================================================
def descargar_sri(ruc, clave, anio, mes, tipo, formatos, destino, origen="Recibidos", fast_mode=True):
    destino.mkdir(parents=True, exist_ok=True)
    destino_xml = destino / "XML"
    destino_pdf = destino / "PDF"
    destino_xml.mkdir(exist_ok=True)
    destino_pdf.mkdir(exist_ok=True)

    n_xml = n_pdf = 0
    cookies_path = Path(f"cookies_{ruc}.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox","--disable-setuid-sandbox",
            "--disable-dev-shm-usage","--disable-gpu","--single-process"
        ])
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1️⃣ LOGIN
        _login_y_cookies(context, page, ruc, clave, cookies_path)

        # 2️⃣ INGRESAR MÓDULO
        url_modulo = URLS.get(origen, URLS["Recibidos"])
        page.goto(url_modulo, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        _espera_captcha(page)

        # 3️⃣ FILTROS
        try:
            _seleccionar(page, "Período emisión", str(anio))
            _seleccionar(page, "Período emisión", _mes_a_texto(mes))
            try: _seleccionar(page, "Período emisión", "Todos")
            except Exception: pass
            tipo_visible = TIPOS_MAP.get(tipo, tipo)
            _seleccionar(page, "Tipo de comprobante", tipo_visible)
        except Exception as e:
            print(f"[WARN] Filtros no aplicados: {e}")

        # 4️⃣ DESCARGAR TXT
        _click_texto(page, "Consultar")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        print("[INFO] Descargando TXT...")
        with page.expect_download(timeout=90000) as dl_info:
            if not _click_texto(page, "Descargar reporte"):
                raise RuntimeError("No se encontró el botón 'Descargar reporte'.")
        dl = dl_info.value
        txt_path = destino / (dl.suggested_filename or f"{origen}_{anio}_{mes:02d}.txt")
        dl.save_as(str(txt_path))
        print(f"[OK] TXT guardado en {txt_path}")

        # 5️⃣ PARSEAR TXT
        claves = _extraer_claves_desde_txt(txt_path)
        if not claves:
            browser.close()
            return {"estado":"sin_descargas","mensaje":"TXT sin claves","n_xml":0,"n_pdf":0}

        # 6️⃣ DESCARGAR XML/PDF (modo rápido)
        def descargar_para_clave(clave):
            nonlocal n_xml, n_pdf
            try:
                local_page = context.new_page()
                local_page.goto(url_modulo, timeout=60000)
                _espera_captcha(local_page)
                try:
                    local_page.get_by_label("Clave de acceso", exact=False).check(timeout=1500)
                except Exception:
                    local_page.get_by_text("Clave de acceso", exact=False).click()
                local_page.fill("input", clave)
                _click_texto(local_page, "Consultar")
                local_page.wait_for_load_state("networkidle")
                if "XML" in formatos:
                    if _descargar_archivo(local_page, destino_xml, clave, "XML"):
                        n_xml += 1
                if "PDF" in formatos:
                    if _descargar_archivo(local_page, destino_pdf, clave, "PDF"):
                        n_pdf += 1
                local_page.close()
            except Exception as e:
                print(f"[WARN] Error con clave {clave}: {e}")

        # MODO FAST (hilos simultáneos)
        if fast_mode:
            threads = []
            for item in claves:
                clave = item["clave"]
                t = threading.Thread(target=descargar_para_clave, args=(clave,))
                t.start()
                threads.append(t)
                if len(threads) >= 5:
                    for t in threads: t.join()
                    threads.clear()
            for t in threads: t.join()
        else:
            for item in claves:
                descargar_para_clave(item["clave"])

        browser.close()

    return {
        "estado": "ok" if (n_xml or n_pdf) else "sin_descargas",
        "n_xml": n_xml,
        "n_pdf": n_pdf,
        "txt": str(txt_path),
        "origen": origen,
        "modo": "Fast" if fast_mode else "Normal"
    }
