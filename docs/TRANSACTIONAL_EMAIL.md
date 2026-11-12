# Correo de Foro IA al Día

## Recepción y envío son servicios distintos

`admin@foroiaaldia.com` es una redirección configurada por el titular en MX Plan Redirect. No tiene buzón ni credenciales SMTP. Su recepción todavía requiere comprobación. No se ha configurado ni contratado automáticamente ningún proveedor de envío.

Comparación consultada el 22/10/2026 en páginas oficiales:

| Proveedor | Plan gratuito anunciado | Integración |
| --- | --- | --- |
| Brevo | 300 mensajes al día | SMTP, encaja con el trabajador existente |
| Resend | 3.000 mensajes al mes, máximo 100 al día | SMTP también disponible |

Recomendación para empezar: Brevo. No hay razón técnica para contratar un buzón adicional solo para enviar verificaciones. La cuenta y el dominio deben ser aprobados/autenticados por el proveedor; la gratuidad y límites se deben comprobar en su panel antes de contratar nada.

Fuentes: [Brevo Free](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan), [Resend pricing](https://resend.com/pricing), [SMTP Brevo](https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP), [claves SMTP](https://help.brevo.com/hc/en-us/articles/7959631848850-Create-and-manage-your-SMTP-keys).

## Preparación de Brevo por el propietario

1. Crear una cuenta propia y activar correo transaccional.
2. Añadir `foroiaaldia.com` y el remitente administrativo. Revisar exactamente los registros de autenticación que muestre el proveedor. No inventar valores de DKIM ni sustituir MX/SPF de OVHcloud. Si hay que modificar DNS, revisarlo y obtener autorización antes; no crear dos registros SPF en la misma etiqueta.
3. Copiar de la sección SMTP el login y generar una **clave SMTP**, no una contraseña del correo ni una clave API de otro producto.
4. Configurar privadamente `/opt/foroia/production.env` (root, 600). No enviar claves por chat ni imprimir la configuración resuelta de Compose.

```dotenv
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_FROM=Foro IA al Día <admin@foroiaaldia.com>
# Completar privadamente con los valores reales del panel:
SMTP_USER=
SMTP_PASSWORD=
REGISTRATION_ENABLED=false
ACCOUNT_EMAIL_ENABLED=false
```

El login real puede variar por cuenta. No utilizar el host como usuario. El trabajador actual soporta SMTP con STARTTLS; usar 587, no configurar 465 como si fuera STARTTLS.

## Probar antes de habilitar funciones

```sh
cd /opt/foroia
sudo docker compose --env-file production.env -f compose.production.yml up -d --force-recreate mail-worker
sudo docker compose --env-file production.env -f compose.production.yml exec -T mail-worker python -m app.mail_worker --test
```

La prueba envía solo a `admin@foroiaaldia.com`; no incluye credenciales ni enlaces de recuperación. Sin host/login/clave o STARTTLS se rechaza antes de conectar. Un mensaje aceptado por SMTP **no demuestra recepción**: comprobar destino y spam de la redirección.

Después probar el recorrido real de verificación y recuperación mediante una cuenta de prueba controlada, sin publicar contenido ficticio. Solo cuando funcione se pueden activar ambas variables y recrear API y web, que usan los mismos indicadores. Registrar las comprobaciones reales en `VALIDATION.md`.

Mientras `ACCOUNT_EMAIL_ENABLED=false`, API rechaza registro, recuperación y reenvío sin crear tokens ni mensajes; el acceso de cuentas ya existentes sigue disponible. La interfaz oculta las acciones que no funcionan y explica el estado. Cambiar solo la interfaz no habilita permisos de servidor.
