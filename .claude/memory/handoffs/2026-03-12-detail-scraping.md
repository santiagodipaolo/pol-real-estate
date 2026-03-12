# Handoff — Detail Scraping para enriquecer listings (2026-03-12)

## Qué se hizo

Implementación completa del pipeline de scraping de detalle para enriquecer los ~1250 listings existentes con datos de fichas individuales. **Todo el código está escrito, falta deploy y verificación.**

### Archivos creados/modificados

| Archivo | Estado | Cambio |
|---------|--------|--------|
| `backend/app/models/listing.py` | DONE | +5 columnas: floor, orientation, condition, description, detail_scraped_at |
| `backend/alembic/versions/003_add_detail_fields.py` | DONE | Migración para las nuevas columnas |
| `backend/app/scrapers/detail.py` | NUEVO | DetailData dataclass + parse_amenities (13 categorías), parse_floor, parse_condition, parse_orientation |
| `backend/app/scrapers/zonaprop.py` | DONE | +scrape_detail(url): __NEXT_DATA__ → DOM fallback. +_detail_from_next_data, +_detail_from_dom |
| `backend/app/scrapers/argenprop.py` | DONE | +scrape_detail(url): DOM puro, busca coords en data-attrs/iframe/scripts |
| `backend/app/scrapers/pipeline.py` | DONE | +enrich_listings(batch_size, source): query priorizada, 1 browser por source, delay 5-10s |
| `backend/app/api/v1/admin.py` | DONE | +POST /admin/enrich, +enrich param en /pipeline, query retrain incluye nuevas cols |
| `backend/app/valuation/features.py` | DONE | 13→21 features (+floor, has_pool, has_gym, has_security, has_balcony, is_front, condition_encoded, amenity_count) |
| `backend/app/valuation/model.py` | DONE | predict() acepta floor, orientation, condition, amenities (backward-compatible) |

### Branch
`feat/detail-scraping` — cambios sin commitear

## Qué falta hacer

### P0 — Verificación inmediata
1. **Commitear** los cambios en la branch actual
2. **Correr migración local**: `alembic upgrade head` (agrega 5 columnas a listings)
3. **Probar enrich local**: `POST /admin/enrich?batch_size=5` con backend corriendo
4. **Verificar en DB** que los listings tienen floor, amenities, condition, description populados
5. **Deploy a Railway**: push + verificar que migración corre
6. **Probar enrich en prod**: `POST /admin/enrich?batch_size=5`
7. **Retrain y comparar MAE**: `POST /admin/retrain` — comparar MAE antes (28-30%) vs después

### P1 — Mejoras post-verificación
- **Scraping masivo**: correr enrich con batch_size=50-100 varias veces hasta cubrir todos los listings
- **Cron job**: configurar Railway cron para enrich periódico (ej: cada 6h, batch_size=30)
- **Validar DOM selectors**: los selectores de Zonaprop y Argenprop para detalle son best-guess — validar contra páginas reales y ajustar
- **Coordenadas**: muchos listings no tienen lat/lng del listado, el detalle debería llenarlos → mejor barrio matching → mejor modelo

### P2 — Iteraciones futuras
- Score de oportunidad usando las nuevas features
- "Analizá esta URL": scrape on-demand de una URL individual
- Feature importance analysis: ver cuáles de las 8 nuevas features aportan más al modelo
- Agregar más amenities (parrilla, jardín, quincho, etc.)

## Notas técnicas
- Los parsers fueron testeados inline: parse_floor("Piso 5")→5, parse_floor("Planta baja")→0, parse_condition("A estrenar")→"Nuevo", parse_orientation("Norte")→"N"
- 13 categorías de amenities: pool, gym, security, balcony, laundry, rooftop, sum, solarium, parking, storage, elevator, ac, heating
- enrich_listings prioriza: sin coordenadas > precio alto > más nuevos
- Delay 5-10s entre requests para evitar bloqueo
- _mark_detail_scraped marca listings aunque falle extracción (evita retry loops)
