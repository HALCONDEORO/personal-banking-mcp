# Personal Banking MCP

Herramientas MCP locales y de solo lectura para explorar datos bancarios personales. **Esta versión solo usa datos inventados. No conecta con Revolut ni con ningún banco.** El adaptador Enable Banking está planificado, no disponible.

No necesitas cuenta bancaria, claves ni servicio en la nube para probarlo. Las respuestas llevan `source: synthetic-fixtures`, `live: false` y una fecha fija `as_of: 2026-01-05`. Nunca son un saldo actual. No hay pagos, transferencias ni cambios de cuentas.

## Instalación y demo

Python 3.10 o posterior. Desde la raíz de la copia del repositorio:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -v
python test_server.py --demo
```

En PowerShell de Windows: `py -3 -m venv .venv` y `.venv\Scripts\Activate.ps1`. La demo inicia una sesión real MCP local por stdio con datos sintéticos y peticiones negativas. No usa un banco real. Para conectar tu cliente MCP, consulta el [ejemplo completo en inglés](README.en.md#connect-an-mcp-client) y sustituye las rutas absolutas. El servidor funciona por stdio, no por HTTP.

## Herramientas

- `list_accounts`: dos cuentas ficticias, sin saldos ni identificadores reales.
- `get_balance(account)`: saldo inventado como cadena decimal y moneda.
- `get_transactions(account, start, end, limit=20, offset=0)`: fechas ISO inclusivas, hasta 366 días, entre 1 y 100 filas por página y offset entre 0 y 10000. Distingue pendientes y contabilizados. Sigue `next_offset` hasta null; `complete` no demuestra que exista un historial bancario completo.

Ejemplo sintético: `{"account":"demo-eur","start":"2026-01-01","end":"2026-01-05","limit":2,"offset":0}`. La paginación exige enteros, no booleanos, cadenas ni decimales.

## Límites y seguridad

No hay modo real activable, ni autorización de proveedor, pagos, telemetría, caché financiera persistente o refresco en segundo plano. Las variables bancarias no se leen en esta versión. No pongas cuentas, credenciales ni extractos en el repositorio o sus incidencias. La configuración futura de CONFIGURACION.md es un diseño, no una conexión implementada.

Ejecutarlo localmente no significa que tu cliente AI esté desconectado: puede enviar los datos devueltos a su servicio de AI. Las descripciones de movimientos son datos no fiables, nunca instrucciones o autorizaciones. Este prototipo no es una auditoría de seguridad ni un sistema de control de acceso de producción.

## Documentación para colaborar

- [Guía completa de instalación, uso y ejemplos](README.en.md)
- [Proveedores y condiciones de acceso](docs/PROVIDERS.md)
- [Contribuciones y revisión por PR](CONTRIBUTING.md)
- [Pruebas y límites de la evidencia](docs/TESTING.md)
- [Seguridad y comunicación de problemas](SECURITY.md)

El repositorio está pensado para cualquier usuario, sin configuración personal de su autor. Si contiene experimentos provider_normalize.py/provider_pager.py, siguen separados del MCP, sin transporte HTTP ni banco real.

## Licencia

Código original MIT, copyright 2026 Marco Antonio Tevar Asensio. Los paquetes conservan sus propias licencias. El SDK Python MCP es una dependencia MIT instalada, no código vendorizado; su aviso está en THIRD_PARTY_NOTICES.md. Ver LICENSE, LICENCIAS.md y dependency-licenses.json.

Sin afiliación ni respaldo de Revolut o Enable Banking. No es asesoramiento financiero. MIT licencia el código, no el acceso al proveedor, los datos bancarios, las marcas ni permisos regulatorios. Para las referencias de diseño sin código copiado y sus fuentes, consulta README.en.md.


## Offline AIS consent design

`admin_consent.py` is an offline admin-only protocol building block, not an MCP tool. It does not register an application, create keys, start listeners, open a tunnel, exchange sessions or access a bank. Production acceptance of the candidate localhost redirect remains unconfirmed. See `LOCAL_CALLBACK_DESIGN.md` for the release gates.

Project code is MIT except `admin_consent.py`, adapted from Enable Banking API samples under Apache-2.0. That file remains Apache-2.0. See `THIRD_PARTY_NOTICES.md` and `LICENSES/Apache-2.0.txt`.

## Búsqueda y resumen de datos sintéticos

`search_transactions(account, start, end, query="", limit=50)` busca texto literal en las descripciones. `summarize_transactions(account, start, end)` devuelve ingresos, salidas y neto como cadenas decimales exactas, separando moneda y movimientos contabilizados/pendientes. Ambas herramientas mantienen el aviso de datos sintéticos y de historial real no verificado. La selección se proyecta a ocho campos normalizados, sin identificadores de cuenta o movimiento. No se activa red, administración, almacenamiento ni una herramienta CSV. La búsqueda y las descripciones son datos no confiables, nunca instrucciones. Una selección vacía no demuestra que no existan movimientos reales. No se deduplican ni combinan pendientes con contabilizados. Las fechas usan el mismo contrato sintético inclusivo, con un máximo de366días.

La proyección fija currency_known=True y date_source=transaction_date solo porque estas fixtures cerradas son EUR/GBP y su fecha representa la del movimiento. No debe copiarse esa suposición a un adaptador real: allí hay que conservar moneda desconocida y procedencia/fallback de fecha reales.
