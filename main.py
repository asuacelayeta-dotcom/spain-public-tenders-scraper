"""
Spain Public Tenders Scraper PLACSP
=====================================
Motor de decisión con diccionario de búsqueda por sector.
Jerarquía: keyword > tipo_contrato > cpv (excepcional)
Límites fijos: max_results=200, max_pages=3

Author: Juan Alberto Asua Celayeta
License: MIT
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional
from lxml import etree
import httpx
from apify import Actor

log = logging.getLogger(__name__)

BASE_FEED_URL = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3.atom"
)
MAX_RESULTS     = 200
MAX_PAGES       = 3
PRESUPUESTO_MIN = 15000.0
VALID_CODE      = "PUB"
VALID_LABEL     = "Publicado"
VALID_ESTADOS   = ["Publicado", "Activo"]
VALID_TIPOS     = [
    "Obras", "Servicios", "Suministros", "Administrativo especial",
    "Privado", "Gestión de Servicios Públicos", "Concesión de Servicios",
    "Concesión de Obras Públicas", "Concesión de Obras",
    "Colaboración entre el sector público y sector privado", "Patrimonial"
]

PALABRAS_EXCLUIR = [
    "adjudicada", "desierta", "modificación", "prórroga",
    "modificacion", "prorroga", "anulada", "contrato menor", "contratos menores"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PLACSP-Scraper/8.0)"}

NS: dict[str, str] = {
    "atom":          "http://www.w3.org/2005/Atom",
    "cbc":           "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac":           "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
}

CONTRACT_TYPE_MAP: dict[str, list[str]] = {
    "Obras":                                                 ["1"],
    "Servicios":                                             ["2"],
    "Suministros":                                           ["3"],
    "Administrativo especial":                               ["6"],
    "Privado":                                               ["31"],
    "Gestión de Servicios Públicos":                         ["8"],
    "Concesión de Servicios":                                ["21"],
    "Concesión de Obras Públicas":                           ["7"],
    "Concesión de Obras":                                    ["7"],
    "Colaboración entre el sector público y sector privado": ["22"],
    "Patrimonial":                                           ["40"],
}

# ──────────────────────────────────────────────────────────────
# Diccionario de búsqueda por sector (máximo cuantía)
# Máx: 3 semillas, 5 variantes, 3 CPVs, 3 negativas
# ──────────────────────────────────────────────────────────────
DICCIONARIO: dict[str, dict] = {
    # TOP 1
    "obras": {
        "semilla": ["obra", "obras", "construcción"],
        "variantes": ["obra civil", "urbanización", "carretera", "rehabilitación", "pavimentación"],
        "cpv_prefijos": ["4523", "4521", "4511"],
        "negativas": ["mantenimiento", "redacción", "asistencia técnica"]
    },
    "infraestructura": {
        "semilla": ["infraestructura", "obra", "obras"],
        "variantes": ["obra civil", "vial", "carretera", "ferroviario", "puerto"],
        "cpv_prefijos": ["4523", "4521", "6311"],
        "negativas": ["mantenimiento", "redacción", "consultoría"]
    },
    # TOP 2
    "inteligencia artificial": {
        "semilla": ["inteligencia artificial", "IA", "machine learning"],
        "variantes": ["transformación digital", "automatización", "algoritmo", "datos", "GovTech"],
        "cpv_prefijos": ["7226", "4800", "7320"],
        "negativas": ["mantenimiento", "formación básica", "soporte"]
    },
    "govtech": {
        "semilla": ["govtech", "digitalización", "tecnología"],
        "variantes": ["administración digital", "plataforma digital", "e-gobierno", "smart city", "datos abiertos"],
        "cpv_prefijos": ["7226", "4800", "7200"],
        "negativas": ["mantenimiento", "impresión", "papelería"]
    },
    "tecnología": {
        "semilla": ["tecnología", "sistemas", "software"],
        "variantes": ["transformación digital", "plataforma", "aplicación", "digitalización", "cloud"],
        "cpv_prefijos": ["4800", "7200", "3200"],
        "negativas": ["mantenimiento", "soporte básico", "impresión"]
    },
    # TOP 3
    "defensa": {
        "semilla": ["defensa", "armamento", "militar"],
        "variantes": ["sistema de armas", "vehículo militar", "munición", "equipamiento militar", "ejército"],
        "cpv_prefijos": ["3500", "7500", "3510"],
        "negativas": ["mantenimiento", "formación", "consultoría"]
    },
    "armamento": {
        "semilla": ["armamento", "armas", "munición"],
        "variantes": ["sistema de armas", "vehículo blindado", "artillería", "misil", "defensa"],
        "cpv_prefijos": ["3510", "3500", "3560"],
        "negativas": ["mantenimiento", "limpieza", "formación"]
    },
    "seguridad": {
        "semilla": ["seguridad", "vigilancia", "protección"],
        "variantes": ["guardia de seguridad", "control de acceso", "videovigilancia", "alarma", "custodia"],
        "cpv_prefijos": ["7971", "3500", "3523"],
        "negativas": ["salud laboral", "prevención de riesgos", "formación"]
    },
    # TOP 4
    "hidrógeno": {
        "semilla": ["hidrógeno", "energía verde", "renovable"],
        "variantes": ["hidrógeno verde", "electrolizador", "pila de combustible", "NextGenerationEU", "descarbonización"],
        "cpv_prefijos": ["0933", "0900", "4521"],
        "negativas": ["gas natural", "combustible fósil", "mantenimiento"]
    },
    "energía": {
        "semilla": ["energía", "renovable", "solar"],
        "variantes": ["fotovoltaico", "eólico", "paneles solares", "aerogenerador", "batería"],
        "cpv_prefijos": ["0933", "3140", "0900"],
        "negativas": ["gas natural", "petróleo", "mantenimiento"]
    },
    "solar": {
        "semilla": ["solar", "fotovoltaico", "paneles"],
        "variantes": ["panel solar", "instalación solar", "energía solar", "placa solar", "autoconsumo"],
        "cpv_prefijos": ["0933", "3140", "4521"],
        "negativas": ["mantenimiento", "limpieza", "estudio"]
    },
    # TOP 5
    "sanidad": {
        "semilla": ["sanidad", "hospital", "salud"],
        "variantes": ["equipamiento médico", "dispositivo médico", "clínica", "centro de salud", "ambulancia"],
        "cpv_prefijos": ["3300", "8500", "3310"],
        "negativas": ["formación", "consultoría", "limpieza"]
    },
    "hospital": {
        "semilla": ["hospital", "clínica", "sanitario"],
        "variantes": ["equipamiento hospitalario", "quirófano", "UCI", "radiología", "laboratorio clínico"],
        "cpv_prefijos": ["3300", "3310", "3312"],
        "negativas": ["mantenimiento", "limpieza", "catering"]
    },
    # Resto de sectores
    "ciberseguridad": {
        "semilla": ["ciberseguridad", "seguridad informática", "hacking"],
        "variantes": ["firewall", "SOC", "SIEM", "pentesting", "seguridad cloud"],
        "cpv_prefijos": ["7226", "4800", "3523"],
        "negativas": ["mantenimiento", "formación básica", "antivirus básico"]
    },
    "educación": {
        "semilla": ["educación", "formación", "enseñanza"],
        "variantes": ["formación profesional", "universidad", "colegio", "e-learning", "capacitación"],
        "cpv_prefijos": ["8000", "7200", "3000"],
        "negativas": ["mantenimiento", "limpieza", "catering"]
    },
    "facility": {
        "semilla": ["facility", "mantenimiento", "edificio"],
        "variantes": ["mantenimiento integral", "gestión de instalaciones", "limpieza edificios", "climatización", "ascensores"],
        "cpv_prefijos": ["5000", "9000", "4521"],
        "negativas": ["obra nueva", "construcción", "demolición"]
    },
    "transporte": {
        "semilla": ["transporte", "flota", "vehículo"],
        "variantes": ["transporte público", "autobús", "tren", "flota municipal", "movilidad"],
        "cpv_prefijos": ["6000", "3400", "6311"],
        "negativas": ["mantenimiento", "reparación", "estudio"]
    },
    "medio ambiente": {
        "semilla": ["medio ambiente", "residuos", "agua"],
        "variantes": ["gestión de residuos", "depuradora", "reciclaje", "limpieza viaria", "parque natural"],
        "cpv_prefijos": ["9000", "4100", "7700"],
        "negativas": ["consultoría", "estudio", "redacción"]
    },
    "limpieza": {
        "semilla": ["limpieza", "higiene", "desinfección"],
        "variantes": ["limpieza viaria", "recogida de basuras", "limpieza de edificios", "gestión de residuos", "saneamiento"],
        "cpv_prefijos": ["9000", "3900", "9010"],
        "negativas": ["productos de limpieza", "suministro", "estudio"]
    },
    "consultoría": {
        "semilla": ["consultoría", "ingeniería", "arquitectura"],
        "variantes": ["dirección de obra", "proyecto técnico", "asistencia técnica", "redacción de proyecto", "estudio"],
        "cpv_prefijos": ["7100", "7300", "7900"],
        "negativas": ["obra", "construcción", "suministro"]
    },
}


# ──────────────────────────────────────────────────────────────
# Normalización y validación
# ──────────────────────────────────────────────────────────────
def normalizar(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    v = str(valor).strip()
    if v in ["", "Selecciona", "Seleccione", "Todos", "Cualquiera", "null", "None", "--"]:
        return None
    return v


def normalizar_cpv(cpv: Any) -> Optional[str]:
    cpv = normalizar(cpv)
    if not cpv:
        return None
    cpv = "".join(ch for ch in cpv if ch.isdigit())
    if len(cpv) < 4:
        return None
    return cpv[:5]


def validar_input(estado, keyword, tipo_contrato, cpv):
    estado        = normalizar(estado) or "Publicado"
    keyword       = normalizar(keyword)
    tipo_contrato = normalizar(tipo_contrato)
    cpv           = normalizar_cpv(cpv)

    if estado not in VALID_ESTADOS:
        return {"error": True, "mensaje": "Estado no válido. Usa Publicado o Activo."}

    if tipo_contrato and tipo_contrato not in VALID_TIPOS:
        return {"error": True, "mensaje": f"Tipo de contrato no válido."}

    if not keyword and not tipo_contrato and not cpv:
        return {
            "error": True,
            "mensaje": "Si no escribes una palabra clave, debes seleccionar Tipo de contrato o Código CPV."
        }

    return {
        "error":         False,
        "estado":        estado,
        "keyword":       keyword,
        "tipo_contrato": tipo_contrato,
        "cpv":           cpv,
    }


def buscar_en_diccionario(keyword: str) -> Optional[dict]:
    """Busca la keyword en el diccionario. Devuelve entrada si hay coincidencia."""
    kw = keyword.lower().strip()
    for clave, datos in DICCIONARIO.items():
        if kw == clave or kw in datos.get("semilla", []):
            return datos
    # Búsqueda parcial
    for clave, datos in DICCIONARIO.items():
        if clave in kw or kw in clave:
            return datos
    return None


# ──────────────────────────────────────────────────────────────
# XML helpers
# ──────────────────────────────────────────────────────────────
def _clean(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return re.sub(r'\s+', ' ', text).strip() or None


def first_text(node: etree._Element, xpaths: list[str], ns: dict[str, str]) -> Optional[str]:
    for xp in xpaths:
        try:
            vals = node.xpath(xp, namespaces=ns)
            if vals:
                v = vals[0]
                text = v if isinstance(v, str) else (getattr(v, 'text', '') or '')
                cleaned = _clean(text)
                if cleaned:
                    return cleaned
        except Exception:
            continue
    return None


def fetch_xml(url: str, client: httpx.Client, retries: int = 3) -> Optional[bytes]:
    for attempt in range(retries):
        try:
            r = client.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.content
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                log.error(f"Error descargando {url}: {e}")
    return None


def parse_xml(content: bytes) -> Optional[etree._Element]:
    try:
        return etree.fromstring(content)
    except Exception as e:
        log.error(f"Error parseando XML: {e}")
        return None


def extract_next_link(root: etree._Element, ns: dict[str, str]) -> Optional[str]:
    links = root.xpath("//atom:link[@rel='next']/@href", namespaces=ns)
    return links[0] if links else None


def parse_entry(entry: etree._Element, ns: dict[str, str]) -> Optional[dict[str, Any]]:
    _id  = first_text(entry, ["./atom:id/text()"], ns)
    _upd = first_text(entry, ["./atom:updated/text()"], ns)
    try:
        _updated_dt: Optional[datetime] = None
        if _upd:
            try:
                _updated_dt = datetime.fromisoformat(_upd)
            except Exception:
                pass

        estado_codigo = first_text(entry, [".//cbc-place-ext:ContractFolderStatusCode/text()"], ns)
        if estado_codigo != VALID_CODE:
            return None

        _tipo_codigo = first_text(entry, [".//cac:ProcurementProject/cbc:TypeCode/text()"], ns)
        _cpv_codigo  = first_text(entry, [".//cac:RequiredCommodityClassification/cbc:ItemClassificationCode/text()"], ns)

        _presupuesto: float = 0.0
        _pres_str = first_text(entry, [".//cac:BudgetAmount/cbc:TaxExclusiveAmount/text()"], ns)
        if _pres_str:
            try:
                _presupuesto = float(_pres_str)
            except Exception:
                pass

        organo = first_text(entry, [
            ".//cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name/text()",
            ".//cac-place-ext:LocatedContractingParty//cac:PartyName/cbc:Name/text()",
            ".//cac-place-ext:LocatedContractingParty//cbc:Name/text()",
        ], ns)

        objeto = first_text(entry, [
            ".//cac:ProcurementProject/cbc:Name/text()",
            "./atom:title/text()",
            ".//cbc:Name/text()",
        ], ns)

        url_licitacion = first_text(entry, [
            "./atom:link[@rel='alternate']/@href",
            "./atom:link/@href",
        ], ns)

        end_date = first_text(entry, [".//cac:TenderSubmissionDeadlinePeriod/cbc:EndDate/text()"], ns)
        end_time = first_text(entry, [".//cac:TenderSubmissionDeadlinePeriod/cbc:EndTime/text()"], ns)

        if end_date and end_time:
            fecha_iso = f"{end_date}T{end_time}"
        elif end_date:
            fecha_iso = end_date
        else:
            fecha_iso = None

        return {
            "_id":          _id,
            "_updated_dt":  _updated_dt,
            "_tipo_codigo": _tipo_codigo,
            "_cpv_codigo":  _cpv_codigo,
            "_presupuesto": _presupuesto,
            "objeto_contrato":            objeto,
            "organo_contratacion":        organo,
            "url_licitacion":             url_licitacion,
            "estado_texto":               VALID_LABEL,
            "fecha_fin_presentacion_iso": fecha_iso,
        }
    except Exception as e:
        log.warning(f"Error parseando entry {_id}: {e}")
        return None


def deduplicate_entries(records: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for r in records:
        eid = r.get("_id") or ""
        upd = r.get("_updated_dt")
        existing = seen.get(eid)
        if not existing:
            seen[eid] = r
        else:
            existing_upd = existing.get("_updated_dt")
            if upd and existing_upd and upd > existing_upd:
                seen[eid] = r
            elif upd and not existing_upd:
                seen[eid] = r
    return list(seen.values())


def apply_exclusions(records: list[dict]) -> list[dict]:
    return [
        r for r in records
        if not any(excl in (r.get("objeto_contrato") or "").lower() for excl in PALABRAS_EXCLUIR)
    ]


def apply_budget_filter(records: list[dict]) -> list[dict]:
    return [
        r for r in records
        if r.get("_presupuesto", 0.0) == 0.0 or r.get("_presupuesto", 0.0) >= PRESUPUESTO_MIN
    ]


def filter_by_terms(records: list[dict], terms: list[str]) -> list[dict]:
    """Filtra por lista de términos (OR entre ellos)."""
    resultado = []
    for r in records:
        texto = (
            f"{r.get('objeto_contrato') or ''} "
            f"{r.get('organo_contratacion') or ''}"
        ).lower()
        if any(t.lower() in texto for t in terms):
            resultado.append(r)
    return resultado


def filter_by_contract_type(records: list[dict], tipo: str) -> list[dict]:
    allowed = CONTRACT_TYPE_MAP.get(tipo, [])
    return [r for r in records if r.get("_tipo_codigo") in allowed]


def filter_by_cpv(records: list[dict], cpv: str) -> list[dict]:
    prefix = cpv[:5].rstrip("0") or cpv[:4]
    return [r for r in records if (r.get("_cpv_codigo") or "").startswith(prefix)]


def apply_negativas(records: list[dict], negativas: list[str]) -> list[dict]:
    return [
        r for r in records
        if not any(n in (r.get("objeto_contrato") or "").lower() for n in negativas)
    ]


def clean_output(record: dict) -> dict:
    return {k: v for k, v in record.items() if not k.startswith("_")}


def motor_decision(records, keyword, tipo_contrato, cpv):
    base = apply_exclusions(records)
    base = apply_budget_filter(base)

    filtro_primario     = ""
    filtros_secundarios = []
    diccionario_usado   = {"activo": False}
    resultado           = base

    if keyword:
        # Buscar en diccionario
        dic_entry = buscar_en_diccionario(keyword)
        terminos_busqueda = [keyword]

        if dic_entry:
            # Añadir semillas y variantes del diccionario
            terminos_busqueda = list(set(
                [keyword] + dic_entry.get("semilla", []) + dic_entry.get("variantes", [])
            ))
            diccionario_usado = {
                "activo": True,
                "termino_base": keyword,
                "variantes_aplicadas": dic_entry.get("variantes", []),
                "cpv_sugeridos": dic_entry.get("cpv_prefijos", []),
                "negativas_aplicadas": dic_entry.get("negativas", [])
            }

        resultado = filter_by_terms(base, terminos_busqueda)

        # Aplicar negativas del diccionario
        if dic_entry and dic_entry.get("negativas"):
            resultado = apply_negativas(resultado, dic_entry["negativas"])

        filtro_primario = f"keyword='{keyword}'"

        if tipo_contrato:
            resultado = filter_by_contract_type(resultado, tipo_contrato)
            filtros_secundarios.append(f"tipo_contrato='{tipo_contrato}'")
        if cpv:
            resultado = filter_by_cpv(resultado, cpv)
            filtros_secundarios.append(f"cpv_prefix='{cpv}'")

    elif tipo_contrato:
        resultado = filter_by_contract_type(base, tipo_contrato)
        filtro_primario = f"tipo_contrato='{tipo_contrato}'"
        if cpv:
            resultado = filter_by_cpv(resultado, cpv)
            filtros_secundarios.append(f"cpv_prefix='{cpv}'")

    elif cpv:
        resultado = filter_by_cpv(base, cpv)
        filtro_primario = f"cpv_prefix='{cpv}' (excepcional)"

    return resultado[:MAX_RESULTS], filtro_primario, filtros_secundarios, diccionario_usado


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
async def main() -> None:
    async with Actor:
        input_data = await Actor.get_input() or {}

        # Pay-per-event: cobra el evento de arranque
        try:
            await Actor.charge(event_name="apify-actor-start")
        except Exception as e:
            Actor.log.warning(f"No se pudo cobrar actor-start: {e}")

        estado        = input_data.get("estado", "Publicado")
        keyword       = input_data.get("keyword")
        tipo_contrato = input_data.get("tipo_contrato")
        cpv           = input_data.get("cpv")

        validacion = validar_input(estado, keyword, tipo_contrato, cpv)

        if validacion["error"]:
            Actor.log.error(f"❌ {validacion['mensaje']}")
            await Actor.push_data({"valid": False, "mensaje": validacion["mensaje"]})
            return

        keyword       = validacion["keyword"]
        tipo_contrato = validacion["tipo_contrato"]
        cpv           = validacion["cpv"]

        Actor.log.info("=" * 60)
        Actor.log.info("Spain Public Tenders Scraper PLACSP")
        Actor.log.info(f"Keyword:          {keyword or '(vacío)'}")
        Actor.log.info(f"Tipo de contrato: {tipo_contrato or '(todos)'}")
        Actor.log.info(f"CPV:              {cpv or '(todos)'}")
        Actor.log.info(f"Max results:      {MAX_RESULTS} (fijo)")
        Actor.log.info(f"Max páginas:      {MAX_PAGES} (fijo)")
        Actor.log.info("=" * 60)

        all_records: list[dict] = []
        visited: set[str] = set()
        next_url: Optional[str] = BASE_FEED_URL
        page_count = 0

        with httpx.Client() as client:
            page_count = 0
            next_url: Optional[str] = BASE_FEED_URL
            visited: set[str] = set()

            while next_url and page_count < MAX_PAGES:
                if next_url in visited:
                    break
                visited.add(next_url)
                page_count += 1
                Actor.log.info(f"Descargando página {page_count}/{MAX_PAGES}")

                content = fetch_xml(next_url, client)
                if not content:
                    break

                root = parse_xml(content)
                if root is None:
                    break

                entries = root.xpath("//atom:entry", namespaces=NS)
                n_entries = len(entries)
                Actor.log.info(f"  → {n_entries} entries encontradas")

                # Procesar entries
                for entry in entries:
                    record = parse_entry(entry, NS)
                    if record:
                        all_records.append(record)

                # Corte si no hay entries
                if n_entries == 0:
                    Actor.log.info("  → Sin entries. Fin del feed.")
                    break

                next_url = extract_next_link(root, NS)
                if not next_url:
                    Actor.log.info("  → Sin más páginas en el feed.")
                    break

        Actor.log.info(f"Total PUB: {len(all_records)}")
        unique = deduplicate_entries(all_records)
        Actor.log.info(f"Tras deduplicación: {len(unique)}")

        resultados, filtro_primario, filtros_secundarios, dic_usado = motor_decision(
            unique, keyword or "", tipo_contrato or "", cpv or ""
        )

        Actor.log.info(f"Filtro primario:     {filtro_primario}")
        Actor.log.info(f"Filtros secundarios: {filtros_secundarios}")
        if dic_usado.get("activo"):
            Actor.log.info(f"Diccionario activo:  {dic_usado['termino_base']} → {dic_usado['variantes_aplicadas']}")
        Actor.log.info(f"Resultados:          {len(resultados)}")

        for record in resultados:
            await Actor.push_data(clean_output(record))
            # Pay-per-event: cobra un evento por cada resultado entregado
            try:
                await Actor.charge(event_name="apify-default-dataset-item")
            except Exception as e:
                Actor.log.warning(f"No se pudo cobrar result: {e}")

        Actor.log.info(f"FINALIZADO. {len(resultados)} licitaciones exportadas.")
        Actor.log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
