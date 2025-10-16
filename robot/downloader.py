from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime
import csv, re, json, os, time

# ============================================================
# CONFIGURACIÓN GENERAL (Playwright + Docker/Render)
# ============================================================
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
os.environ["PYPPETEER_HOME"] = "/root/.cache/ms-playwright"

RECIBIDOS_URL = "https://srienlinea.sri.gob.ec/comprobantes-electronicos-internet/pages/consultas/recibidos/comprobantesRecibidos.jsf"
BUSQUEDA_CLAVE_URL = RECIBIDOS_URL

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
    return bool(re.fullmatch(r"\d{49}", valor or ""))

def _extraer_claves_desde_txt(txt_path: Path):
    claves = []
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        sample = f.read(4096)
        sep = ";" if sample.count(";")>=sample.count(",") and sample.count(";")>=sample.count("\t") else ("," if sample.count(",")>=sample.count("\t") else "\t")
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f, delimiter=sep)
        for row in reader:
            if not row: continue
            candidato = next((c.strip() for c in row if _es_clave(c.strip())), None)
            if candidato:
                tipo = next((c.strip() for c in row if c.strip().lower().startswith(("factura","comprobante de retención","notas","liquidación"))), "")
                fecha = next((c.strip() for c in row if re.fullmatch(r"\d{2}/\d{2}/\d{4}", c.strip())), "")
                claves.append({"clave": candidato, "tipo": tipo or "", "fecha": fecha or ""})
    return claves

def _click_descargar(page, texto_btn:str):
    for intento in range(2):
        try:
            page.get_by_role("button", name=texto_btn, exact=False).click(timeout=4000)
            return True
        except Exception:
            try:
                page.get_by_text(texto_btn, exact=False).click(timeout=4000)
                return True
            except Exception:
                time.sleep(1)
    return False

def _espera_captcha(page):
    try:
        if page.locator("img[alt='captcha']").is_visible(timeout=2000):
            print("[INFO] Captcha detectado, esperando resolución manual...")
            page.wait_for_selector("img[alt='captcha']", state="detached", timeout=90000)
    except Exception:
        pass

def _login_y_cookies(context, page, ruc, clave, cookies_path: Path):
    if cookies_path.exists():
        try:
            context.add_cookies(json.loads(cookies_path.read_text()))
            print("[OK] Sesión previa restaurada desde cookies.")
            return
        except Exception:
            print("[WARN] Cookies inválidas, iniciando nuevo login.")

    print("[INFO] Iniciando sesión en SRI...")
    page.goto("https://srienlinea.sri.gob.ec/sri-en-linea/inicio/NAT", timeout=90000)
    page.wait_for_load_state("domcontentloaded")

    # Llenar credenciales (tolerante a cambios en UI)
    try:
        if page.locator("input[name='usuario']").count() > 0:
            page.fill("input[name='usuario']", ruc)
            page.fill("input[name='password']", clave)
        elif page.get_by_placeholder("Ruc/Cédula/Pasaporte").count() > 0:
            page.get_by_placeholder("Ruc/Cédula/Pasaporte").fill(ruc)
            page.get_by_placeholder("Contraseña").fill(clave)
        else:
            inputs = page.locator("input[type='text'], input[type='password']").all()
            if len(inputs) >= 2:
                inputs[0].fill(ruc)
                inputs[1].fill(clave)
    except Exception as e:
        print(f"[ERROR] No se pudieron llenar los campos: {e}")

    _espera_captcha(page)
    _click_descargar(page, "Ingresar")
    page.wait_for_load_state("networkidle", timeout=90000)

    try:
        cookies_path.write_text(json.dumps(context.cookies()))
        print("[OK] Cookies guardadas para futuras sesiones.")
    except Exception:
        pass

# ============================================================
# FUNCIÓN PRINCIPAL DE DESCARGA
# ============================================================

def descargar_sri(ruc: str, clave: str, anio: int, mes: int, tipo: str, formatos: list, destino: Path, origen:str="Recibidos"):
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
            args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu","--single-process"]
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1️⃣ LOGIN
        _login_y_cookies(context, page, ruc, clave, cookies_path)

        # 2️⃣ INGRESAR A MÓDULO
        page.goto(RECIBIDOS_URL, timeout=90000)
        page.wait_for_load_state("domcontentloaded")
        _espera_captcha(page)

        # 3️⃣ FILTROS
        try:
            tipo_visible = TIPOS_MAP.get(tipo, tipo)
            page.select_option("select", label=tipo_visible)
        except Exception:
            print("[WARN] No se pudieron aplicar filtros automáticamente.")

        # 4️⃣ CONSULTAR
        _click_descargar(page, "Consultar")
        page.wait_for_load_state("networkidle", timeout=90000)
        time.sleep(2)

        # 5️⃣ DESCARGAR TXT (robusto y extendido)
        print("[INFO] Intentando descargar el archivo TXT del SRI...")
        for intento in range(3):
            try:
                with page.expect_download(timeout=90000) as dl_info:
                    if not _click_descargar(page, "Descargar reporte"):
                        print("[WARN] Botón 'Descargar reporte' no visible, reintentando...")
                        time.sleep(3)
                        continue
                dl = dl_info.value
                txt_path = destino / (dl.suggested_filename or f"{origen.upper()}_{anio}_{mes:02d}.txt")
                dl.save_as(str(txt_path))
                print(f"[OK] TXT guardado correctamente en {txt_path}")
                break
            except Exception as e:
                print(f"[WARN] Fallo al intentar descargar TXT (intento {intento+1}/3): {e}")
                time.sleep(5)
        else:
            raise TimeoutError("❌ No se pudo descargar el archivo TXT después de 3 intentos.")

        # 6️⃣ PARSEAR TXT
        claves = _extraer_claves_desde_txt(txt_path)
        if not claves:
            return {"estado": "sin_descargas", "mensaje": "TXT sin claves", "n_xml": 0, "n_pdf": 0}

        # 7️⃣ DESCARGAR XML Y PDF
        for i, item in enumerate(claves, start=1):
            clave_acc = item["clave"]
            try:
                page.goto(BUSQUEDA_CLAVE_URL, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                _espera_captcha(page)

                try:
                    page.get_by_label("Clave de acceso", exact=False).check(timeout=3000)
                except Exception:
                    page.get_by_text("Clave de acceso", exact=False).click()

                page.fill("input", clave_acc)
                _click_descargar(page, "Consultar")
                page.wait_for_load_state("networkidle")

                # XML
                if "XML" in formatos:
                    with page.expect_download(timeout=90000) as dlinfo:
                        _click_descargar(page, "XML") or _click_descargar(page, "Descargar XML")
                    d = dlinfo.value
                    d.save_as(str(destino_xml / f"{clave_acc}.xml"))
                    n_xml += 1

                # PDF
                if "PDF" in formatos:
                    with page.expect_download(timeout=90000) as dlinfo:
                        _click_descargar(page, "RIDE") or _click_descargar(page, "PDF")
                    d = dlinfo.value
                    d.save_as(str(destino_pdf / f"{clave_acc}.pdf"))
                    n_pdf += 1

            except Exception as e:
                print(f"[WARN] Falló descarga para clave {clave_acc}: {e}")
                continue

        browser.close()

    return {
        "estado": "ok" if (n_xml or n_pdf) else "sin_descargas",
        "n_xml": n_xml,
        "n_pdf": n_pdf,
        "txt": str(txt_path),
    }
