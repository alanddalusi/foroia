# Checklist de seguridad previa a producción

- [ ] Login seguro, verificación email, MFA para administradores, recuperación con tokens de un solo uso.
- [ ] Autorización backend y protección contra IDOR; roles mínimos.
- [ ] Rate limits por IP y usuario con Redis; protección bot y colas de moderación.
- [ ] Cookies Secure/HttpOnly/SameSite y CSRF en acciones con cookies.
- [ ] HTTPS, proxy de confianza y TrustedHost configurables; CORS mínimo.
- [ ] Cabeceras CSP, HSTS, X-Content-Type-Options y Referrer-Policy tras pruebas.
- [ ] Escape HTML, sanitización de markdown, protección de enlaces y archivos adjuntos.
- [ ] Variables de entorno seguras; rotación de secretos y escaneo de dependencias.
- [ ] Backups cifrados, restauración probada, métricas, alertas y auditoría.
- [ ] Aviso legal, privacidad, cookies/consentimiento y mecanismo de denuncias.

**Estado:** prototipo local, NO preparado para exposición pública.
