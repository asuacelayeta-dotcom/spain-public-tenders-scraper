# 🏛️ Spain Public Tenders — PLACSP Live Feed (Pay-per-result)
## 🇪🇸 Licitaciones Públicas España — Datos en Tiempo Real

**The smartest gateway for international and Spanish companies to Spain's public procurement market.**

---

## 🌍 Who uses this

Built for companies, funds and teams across **Europe, USA, China, Japan and Spain** that need to monitor Spanish public contracts without spending hours on government websites.

* 🇺🇸 **US firms** entering Spain's infrastructure and tech markets
* 🇨🇳 **Chinese investors** tracking energy and construction contracts
* 🇯🇵 **Japanese companies** monitoring technology and transport tenders
* 🇪🇺 **European firms** competing for NextGenerationEU-funded projects
* 🇪🇸 **Spanish companies** — consultancies, contractors, B2G sales teams

---

## 🚀 How to use it — 5 steps

```
PASO 1 ── Accede al scraper
          apify.com → Spain Public Tenders Scraper → Try for free

    ↓

PASO 2 ── Rellena el formulario de Input
          Opción A → Palabra clave: solar, limpieza, ciberseguridad...
          Opción B → Tipo de contrato: Obras, Servicios, Suministros
          Opción C → CPV: 45 Construcción, 72 TI, 90 Limpieza...

    ↓

PASO 3 ── Pulsa Start
          El scraper tarda 30-60 segundos

    ↓

PASO 4 ── Ve a la pestaña Output
          Verás una tabla con: objeto, órgano, fecha límite y URL

    ↓

PASO 5 ── Haz clic en la URL de la licitación
          Abre el expediente completo: pliego, presupuesto, solvencia
```

---

## 🎯 Targeted Sectors / Sectores Estratégicos

* **IA y GovTech** — transformación digital, plataformas, smart city
* **Hidrógeno y energía renovable** — solar, eólica, NextGenerationEU
* **Defensa y armamento** — sistemas militares, seguridad nacional
* **Obras e infraestructura** — carreteras, ferroviario, puertos
* **Sanidad** — equipamiento médico, hospitales, laboratorios
* **Ciberseguridad** — SOC, firewall, pentesting
* **Tecnología** — software, cloud, digitalización
* **Consultoría e ingeniería** — arquitectura, dirección de obra
* **Transporte** — flotas, movilidad, mantenimiento vial
* **Medio ambiente** — residuos, agua, limpieza urbana
* **Educación y formación** — universidades, FP, e-learning
* **Facility Management** — mantenimiento integral de edificios

---

## 🤖 Smart Search Dictionary

This Actor uses a built-in sector dictionary. When you type a keyword like **"infraestructura"**, the system automatically searches for related terms: *obra civil, vial, carretera, ferroviario, puerto* — without any extra configuration.

**You write one word. The system finds everything relevant.**

---

## 📦 What you get / Qué recibes

Every result includes:

| Campo | Descripción |
|---|---|
| `objeto_contrato` | Título y descripción del contrato |
| `organo_contratacion` | Organismo público que licita |
| `url_licitacion` | Enlace directo al expediente completo |
| `estado_texto` | Siempre "Publicado" — solo contratos activos |
| `fecha_fin_presentacion_iso` | Plazo límite en formato ISO |

---

## ▶️ Example Input / Ejemplo de entrada

```json
{
  "estado": "Publicado",
  "keyword": "infraestructura",
  "tipo_contrato": "Obras",
  "cpv": "45000000"
}
```

---

## 📤 Example Output / Ejemplo de salida

```json
{
  "objeto_contrato": "Obras de mejora de infraestructura viaria en el municipio",
  "organo_contratacion": "Diputación Provincial de Sevilla",
  "url_licitacion": "https://contrataciondelestado.es/wps/poc?uri=deeplink:detalle_licitacion&idEvl=...",
  "estado_texto": "Publicado",
  "fecha_fin_presentacion_iso": "2026-06-15T23:59:00"
}
```

---

## ❓ FAQ

**¿Los datos son oficiales?**
Sí. Directamente de PLACSP — la plataforma oficial del Ministerio de Hacienda.

**¿Con qué frecuencia se actualiza?**
Diariamente. Cada ejecución trae los datos más recientes.

**¿Puedo integrar los resultados en mi CRM o herramienta BI?**
Sí. Output JSON estándar compatible con Zapier, Make, Excel y cualquier API.

**¿Qué pasa si no hay resultados para mi keyword?**
El sistema amplía automáticamente la búsqueda con el diccionario de sector. Si aún así no hay resultados, prueba con una keyword más amplia.

**Is the data official?**
Yes. Directly from PLACSP — Spain's official Ministry of Finance contracting platform.

**Can I integrate results into my CRM or BI tool?**
Yes. Clean JSON output compatible with Zapier, Make, Excel and any API.

---

## 🇪🇸 En Español

Extractor inteligente de licitaciones públicas de España conectado directamente a PLACSP. Más de 15.000 organismos contratantes. Solo contratos vigentes. Diccionario de búsqueda por sector integrado. Sin suscripción. Pagas solo por las licitaciones que recibes.

---

## 🚀 Start now / Empieza ahora

Click **Try for free**, type your sector keyword and receive today's active Spanish public tenders in seconds.