# PiBot — n8n Workflows

Coleccion de workflows de n8n que conectan PiBot con servicios externos mediante webhooks.

## Workflows disponibles

| Archivo | Nombre del workflow | Descripcion |
|---|---|---|
| `gmail.json` | PiBot — Gmail | Leer, buscar y enviar correos via Gmail API |
| `youtube.json` | PiBot — YouTube | Buscar videos y obtener info de canales |
| `meta.json` | PiBot — Meta (Facebook + Instagram) | Publicar y consultar en Facebook e Instagram |
| `wordpress.json` | PiBot — WordPress | Crear y gestionar posts en WordPress |
| `holded.json` | PiBot — Holded | Consultar contactos, facturas y productos en Holded |
| `notion-tasks.json` | PiBot — Notion Tasks | Crear y consultar tareas en Notion |
| `notion-crm.json` | PiBot — Notion CRM | Gestionar contactos y deals en Notion CRM |
| `calendar.json` | PiBot — Google Calendar | Crear, listar y gestionar eventos de calendario |

## Como importar

1. Abre tu instancia de n8n
2. Ve a **Workflows > Import from File**
3. Selecciona el archivo `.json` del workflow que quieras importar
4. Configura las credenciales necesarias (OAuth2, API keys, etc.)
5. Activa el workflow

## Webhook paths

Cada workflow expone uno o mas webhooks que PiBot invoca via HTTP. Los paths estan documentados en cada JSON y siguen el patron:

```
https://<tu-n8n>/webhook/<servicio>/<accion>
```

## Credenciales necesarias

- **Gmail**: Gmail OAuth2
- **YouTube**: YouTube OAuth2
- **Meta**: Facebook Graph API token
- **WordPress**: WordPress credentials (usuario + application password)
- **Holded**: Holded API key
- **Notion**: Notion Internal Integration token
- **Google Calendar**: Google Calendar OAuth2

## Notas

- Los webhook paths NO deben modificarse ya que PiBot los referencia internamente.
- Cada workflow incluye un tag `pibot` para facilitar la organizacion en n8n.
- Los nodos de respuesta devuelven JSON estructurado que PiBot parsea automaticamente.
