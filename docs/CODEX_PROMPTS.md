# Prompts listos para Codex

## 1. Arranque
Lee AGENTS.md y README.md. Revisa todo el repositorio. Haz que `docker compose up --build -d` y el esquema inicial funcionen en un entorno limpio. Añade tests básicos y CI. No implementes nuevas funcionalidades sin verificar el arranque.

## 2. Autenticación
Lee AGENTS.md y docs/SECURITY.md. Diseña migraciones Alembic y autenticación segura con roles, sesiones, verificación de correo, restablecimiento de contraseña, CSRF y tests de permisos. Implementa por fases, sin exponer escrituras anónimas.

## 3. Foro funcional
Lee AGENTS.md. Implementa creación/edición de temas, respuestas, reportes y cola de moderación, con límites de tamaño, rate limits, validación, paginación y pruebas. Mantén todo contenido no aprobado fuera de APIs públicas y sitemap.

## 4. SEO
Lee docs/SEO.md. Audita SSR, canonical, meta, robots, sitemap completo paginado, 404, paginación y datos estructurados. Implementa tests automáticos. No generes contenido masivo artificial ni afirmes que garantizarás TOP 1.
