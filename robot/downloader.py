from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime
import csv, re, json, os, time
from robot.historial import registrar_descarga  # ✅ nuevo módulo

# ============================================================
# CONFIGURACIÓN GLOBAL PARA DOCKER/RENDER
# ============================================================
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
os.environ["PYPPETEER_HOME"] = "/root/.cache/ms-playwright"

# URLs base
RECIBIDOS_URL = "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/recibidos/comprobantesRecibidos.jsf"
EMITIDOS_URL = "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/menu.jsf"
BUSQUEDA_CLAVE_URL = RECIBIDOS_URL  # en la mayoría de casos es el mismo

TIPOS_MAP = {
    "Facturas": "Factura",
    "Retenciones": "Comprobante de Retención",
    "Notas de crédito": "Notas de Crédito",
    "Notas de débito": "Notas de Débito",
    "Liquidación de compra": "Liquidación de compra de bienes y prestación de servicios",
    "Factura": "Factura",
    "Nota de Crédito": "Nota de Crédito",
    "Nota de Débito": "Nota de Débito",
    "Guía de Remisión": "Guía de Remisión",
    "Comprobante de Retención": "Comprobante de Retención",
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _mes_a_texto(mes: int) -> str:
    return [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ][mes - 1]


def _es_clave(valor: str) -> bool:
    return bool(re.fullmatch(r"\d{49}", valor or ""))


def _extraer_claves_desde_txt(txt_path: Path):
    claves = []
    if not txt_path.exists():
        return claves
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        sample = f.read(4096)
        sep = ";" if sample.count(";") >= sample.count(",") else ","
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f, delimiter=sep)
        for row in reader:
            if not row:
                continue
            candidato = next((c.strip() for c in row if _es_clave(c.strip())), None)
            if candidato:
                tipo = next((c.strip() for c in row if "factura" in c.lower()), "Factura")
                claves.append({"clave": candidato, "tipo": tipo})
    return claves


def _click_descargar(page, texto_btn: str):
    try:
        page.get_by_role("button", name=texto_btn, exact=False).click(timeout=4000)
        return True
    except Exception:
        try:
            page.get_by_text(texto_btn, exact=False).click(timeout=4000)
            return True
        except Exception:
            return False


def _seleccionar(page, etiqueta: str, valor_visible: str):
    try:
        page.select_option("select", label=valor_visible)
    except Exception:
        try:
            lab = page.get_by_label(etiqueta, exact=False)
            sel = lab.locator("select")
            sel.select_option(label=valor_visible)
        except Exception:
            pass


def _espera_captcha(page):
    try:
        if page.locator("img[alt='captcha']").is_visible(timeout=2000):
            page.wait_for_selector("img[alt='captcha']", state="detached", timeout=60000)
    except Exception:
        pass


def _login_y_cookies(context, page, ruc, clave, cookies_path: Path):
    if cookies_path.exists():
        try:
            context.add_cookies(json.loads(cookies_path.read_text()))
            return
        except Exception:
            pass

    page.goto("https://srienlinea.sri.gob.ec/sri-en-linea/inicio/NAT", timeout=60000)
    page.wait_for_load_state("domcontentloaded")

    try:
        page.fill("input[placeholder*='Ruc'], input[name*='usuario']", ruc)
        page.fill("input[type='password'], input[name*='password']", clave)
    except Exception as e:
        print(f"[WARN] No se encontraron campos de login: {e}")

    _espera_captcha(page)
    _click_descargar(page, "Ingresar")
    page.wait_for_load_state("networkidle")

    try:
        cookies_path.write_text(json.dumps(context.cookies()))
    except Exception:
        pass


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def descargar_sri(ruc: str, clave: str, anio: int, mes: int, tipo: str, formatos: list, destino: Path, origen: str = "Recibidos"):
    destino.mkdir(parents=True, exist_ok=True)
    destino_xml = destino / "XML"
    destino_pdf = destino / "PDF"
    destino_xml.mkdir(exist_ok=True)
    destino_pdf.mkdir(exist_ok=True)

    n_xml = n_pdf = 0
    cookies_path = Path(f"cookies_{ruc}.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-dev-shm-usage", "--disable-gpu",
                "--single-process"
            ]
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        _login_y_cookies(context, page, ruc, clave, cookies_path)

        # Seleccionar módulo según tipo
        if origen.lower().startswith("emit"):
            page.goto(EMITIDOS_URL, timeout=60000)
        else:
            page.goto(RECIBIDOS_URL, timeout=60000)

        page.wait_for_load_state("domcontentloaded")
        _espera_captcha(page)

        # Aplicar filtros
        try:
            _seleccionar(page, "Período emisión", str(anio))
            _seleccionar(page, "Período emisión", _mes_a_texto(mes))
            tipo_visible = TIPOS_MAP.get(tipo, tipo)
            _seleccionar(page, "Tipo de comprobante", tipo_visible)
        except Exception as e:
            print(f"[WARN] No se pudieron aplicar filtros: {e}")

        _click_descargar(page, "Consultar")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Descargar TXT
        try:
            with page.expect_download() as dl_info:
                _click_descargar(page, "Descargar reporte")
            dl = dl_info.value
            txt_path = destino / (dl.suggested_filename or f"{origen}_{anio}_{mes:02d}.txt")
            dl.save_as(str(txt_path))
        except Exception as e:
            print(f"[ERROR] No se pudo descargar el TXT: {e}")
            return {"estado": "error", "mensaje": str(e), "n_xml": 0, "n_pdf": 0}

        claves = _extraer_claves_desde_txt(txt_path)
        if not claves:
            return {"estado": "sin_descargas", "mensaje": "TXT sin claves", "n_xml": 0, "n_pdf": 0}

        for i, item in enumerate(claves, start=1):
            clave_acc = item["clave"]
            try:
                page.goto(BUSQUEDA_CLAVE_URL, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                _espera_captcha(page)
                page.fill("input", clave_acc)
                _click_descargar(page, "Consultar")
                page.wait_for_load_state("networkidle")
                time.sleep(0.5)

                if "XML" in formatos:
                    with page.expect_download() as dlinfo:
                        _click_descargar(page, "XML") or _click_descargar(page, "Descargar XML")
                    d = dlinfo.value
                    d.save_as(str(destino_xml / f"{clave_acc}.xml"))
                    n_xml += 1

                if "PDF" in formatos:
                    with page.expect_download() as dlinfo:
                        _click_descargar(page, "RIDE") or _click_descargar(page, "PDF")
                    d = dlinfo.value
                    d.save_as(str(destino_pdf / f"{clave_acc}.pdf"))
                    n_pdf += 1

                if i % 20 == 0:
                    time.sleep(3)
            except Exception as e:
                print(f"[WARN] Falló descarga para {clave_acc}: {e}")
                continue

        browser.close()

    resultado = {
        "estado": "ok" if (n_xml or n_pdf) else "sin_descargas",
        "n_xml": n_xml,
        "n_pdf": n_pdf,
        "txt": str(destino / f"{origen}_{anio}_{mes:02d}.txt"),
    }

    # ✅ Guardar registro
    registrar_descarga(ruc, origen, anio, mes, tipo, resultado)
    return resultado
