> Estado actual: solo datos sintéticos. Las variables y el adaptador bancario descritos como futuros no se leen ni activan en esta versión.

# Guía de configuración sin exponer claves

Esta guía explica cómo configurar `personal-banking-mcp` de forma que ninguna credencial acabe en el repositorio, en los logs ni en la configuración del cliente MCP en texto plano reutilizable. Está escrita para el diseño fixture-first: la mayor parte de los pasos **no necesita clave alguna**.

## 1. Modo fixtures (por defecto, sin claves)

- No definas ninguna variable de entorno bancaria. Sin ellas, el servidor debe arrancar en modo fixtures y servir solo los datos de prueba del repo.
- Comprueba antes de conectar nada real que el cliente muestra las cuentas y movimientos de ejemplo. Si no hay fixtures cargados, no hay modo real activo: es la señal correcta.
- Los fixtures nunca contienen datos reales: ni IBAN reales, ni nombres de titulares reales, ni importes reales. Si alguna vez un fixture parece real, bórralo y avisa al autor.

## 2. Cuando llegue el adaptador Enable Banking

Enable Banking funciona con una aplicación registrada en su consola, un identificador de aplicación y una pareja de claves RSA (la privada la generas tú y nunca sale de tu máquina; la pública se sube a la consola).

Reglas de oro:

1. **La clave privada vive fuera del repo.** Guárdala en una ruta fuera del directorio del proyecto, por ejemplo `~/.config/personal-banking-mcp/enable-banking.key.pem`, con permisos `chmod 600`.
2. **El repo referencia rutas y nombres, nunca contenidos.** La configuración apunta al fichero de la clave por su ruta; la clave no se copia a ningún fichero del proyecto.
3. **`.env` solo local y siempre ignorado.** Si usas un `.env` para las variables, debe estar en `.gitignore` desde el primer commit. El repo puede incluir un `.env.example` con los nombres de las variables y valores vacíos o de mentira.
4. **Nada de secretos en el JSON del cliente MCP.** La configuración del cliente (p. ej. `claude_desktop_config.json`) debe pasar variables de entorno con rutas y nombres, no el contenido de la clave. Si el cliente lo permite, mejor heredar el entorno del sistema que reescribir valores allí.
5. **Nunca en logs.** Si un error imprime la configuración, la clave debe aparecer enmascarada. Revisa los logs la primera vez que arranques el modo real.

## 3. Variables de entorno previstas

Nombres orientativos (el servidor los fijará al implementarse; el `.env.example` del repo será la referencia):

| Variable | Qué es | Secreto |
| --- | --- | --- |
| `BANKING_ADAPTER` | `fixtures` (por defecto) o `enablebanking` | No |
| `ENABLE_BANKING_APP_ID` | Identificador de la aplicación en la consola | Trátese como privado |
| `ENABLE_BANKING_KEY_PATH` | Ruta absoluta a la clave privada RSA (fuera del repo) | La ruta no; el fichero, sí |
| `ENABLE_BANKING_SANDBOX` | `true`/`false`: consola de pruebas o producción | No |

## 4. Qué hacer si una clave se escapa

1. Revócala o rota la pareja de claves en la consola de Enable Banking de inmediato.
2. Si llegó a un commit, no basta con borrarla en otro commit: hay que reescribir el historial (o tratar el repo como comprometido) antes de cualquier publicación.
3. Revisa logs y capturas hechas desde el incidente por si la clave aparece en ellos.

## 5. Lista corta de verificación

- [ ] `git status` no muestra ningún `.env`, `*.pem` ni `*.key`.
- [ ] `.gitignore` cubre `.env`, `*.pem`, `*.key` y el directorio de configuración local si estuviera dentro del repo.
- [ ] El arranque sin variables sirve fixtures y ningún dato real.
- [ ] Los logs de arranque no imprimen valores de las variables marcadas como secretas.

## Ejecutar y probar el servidor sintético

Python 3.10 o posterior. Desde la raíz del repositorio:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -v
python -O -m unittest -v
python test_server.py --demo
```

La demo inicia una sesión real de cliente/servidor MCP local por stdio e imprime datos inventados. No necesita credenciales bancarias. Para iniciar solo el servidor, ejecuta `python server.py`; espera un cliente MCP, no una orden interactiva en la terminal.

Ejemplo de configuración del cliente. Sustituye ambas rutas absolutas por la ubicación de tu copia:

```json
{
  "mcpServers": {
    "personal-banking-demo": {
      "command": "/absolute/path/personal-banking-mcp/.venv/bin/python",
      "args": ["/absolute/path/personal-banking-mcp/server.py"]
    }
  }
}
```

El ejemplo no necesita variables de entorno ni claves API. El punto de entrada del servidor funciona sin depender del directorio de trabajo del cliente.
