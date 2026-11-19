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

MIT propuesta en LICENSE. Titular del copyright pendiente de confirmación antes de cualquier publicación. Ver `LICENCIAS.md` para la política de licencias de dependencias.
