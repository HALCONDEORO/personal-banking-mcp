# personal-banking-mcp

MCP local y de **solo lectura** para banca personal, con enfoque *fixture-first*: funciona desde el primer momento contra datos de prueba (fixtures) en tu propia máquina, sin tocar ningún banco real. El adaptador para [Enable Banking](https://enablebanking.com/) (agregación PSD2) está **planificado**, no implementado.

> Sin afiliación con ningún banco. Proyecto privado y personal.

## Principios

- **Solo lectura.** El servidor no puede iniciar pagos, transferencias ni cambios. No existe código de escritura contra ninguna fuente bancaria.
- **Fixture-first.** Los datos sintéticos están incluidos en server.py. Puedes desarrollar, probar y leer la documentación sin credenciales de nada.
- **Local.** El servidor corre en tu máquina y habla con tu cliente MCP (p. ej. Claude Desktop) por stdio. Este servidor solo sirve datos sintéticos; no existe un adaptador bancario activable.
- **Claves fuera del repo.** Cuando llegue el adaptador real, las credenciales viven en variables de entorno o en un `.env` ignorado por git. Nunca en el código, nunca en el README, nunca en los fixtures. Ver `CONFIGURACION.md`.

## Estado

| Pieza | Estado |
| --- | --- |
| Documentación | En preparación |
| Servidor MCP con fixtures | Implementado y probado localmente |
| Adaptador Enable Banking (PSD2, solo lectura AIS) | Planificado |

## Uso con datos sintéticos

1. Clonar el repo y seguir `CONFIGURACION.md`.
2. Crear un entorno Python, instalar requirements.txt y ejecutar python server.py. No necesita claves.
3. Conectar el cliente MCP al comando indicado en `CONFIGURACION.md`.
4. El adaptador Enable Banking sigue planificado; no se puede activar en esta versión.

## Licencia

Código bajo MIT en LICENSE. Copyright: Marco Antonio Tevar Asensio. Ver `LICENCIAS.md` para la política de licencias de dependencias.

## Herramientas y límites actuales

- `list_accounts`: dos cuentas ficticias, sin identificadores bancarios reales.
- `get_balance(account)`: saldo sintético como cadena decimal y moneda.
- `get_transactions(account, start, end, limit=20, offset=0)`: fechas ISO inclusivas, hasta 366 días, entre 1 y 100 filas y paginación por offset acotada; distingue movimientos pendientes y contabilizados.

Las respuestas incluyen `source: synthetic-fixtures`, `live: false` y una fecha `as_of` fija. No son información bancaria actual. No hay conexión con Revolut ni otro banco, servidor HTTP ni adaptador real activable. No es un producto oficial de Revolut o Enable Banking ni un servicio de asesoramiento financiero.

Ejecutarlo localmente no significa que tu cliente AI esté desconectado: el cliente MCP que elijas puede enviar los datos devueltos a su servicio de AI. Las descripciones de movimientos son datos no fiables, nunca instrucciones.

## Acceso futuro al proveedor y condiciones

El modo restringido de producción de Enable Banking permite el uso personal no comercial de las cuentas propias vinculadas, sujeto a sus condiciones. Para cuentas empresariales, clientes o un servicio comercial o multiusuario alojado hay que consultar el uso previsto con Enable Banking y obtener un acuerdo separado cuando corresponda. MIT licencia este código, no el acceso al proveedor, los datos bancarios, las marcas ni permisos regulatorios. Siguen vigentes las restricciones sobre compartir acceso al servicio y usos competitivos. No se garantiza la aceptación del proveedor.

La configuración del consentimiento usa autorización y creación de sesiones por separado de las lecturas de información de cuentas. Este prototipo no expone herramientas de configuración, pagos ni cambios de cuentas. Un adaptador futuro debe fallar de forma cerrada si caduca el consentimiento.

Referencias oficiales comprobadas el 19 de noviembre de 2026:

- [Condiciones de Enable Banking](https://enablebanking.com/terms/)
- [Cuentas propias vinculadas y producción restringida](https://enablebanking.com/docs/api/linked-accounts/)
- [Referencia de API](https://enablebanking.com/docs/api/reference/)
- [SDK Python MCP](https://github.com/modelcontextprotocol/python-sdk), dependencia MIT cuyo aviso se conserva en THIRD_PARTY_NOTICES.md.

Referencias de diseño, sin copiar código fuente en esta versión: [BankMCP](https://github.com/noskillish/bankmcp/), [EU Open Banking MCP](https://github.com/cver-me/EU-Open-Banking-MCP), [Enable Banking MCP en Rust](https://github.com/Algiras/enable-banking-mcp). No son dependencias. El inventario dependency-licenses.json no sustituye los textos de licencia ni las obligaciones de distribución.
