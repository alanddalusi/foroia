# ForoIA — instrucciones permanentes para Codex

Eres el ingeniero principal de ForoIA, una comunidad de IA en español. Lee PROJECT_BRIEF.md, README.md y docs/ARCHITECTURE.md antes de modificar código. PROJECT_BRIEF.md define el alcance del blog + foro y el roadmap.

## Objetivo
Construir un foro seguro, rápido, accesible, indexable y escalable. Nunca prometas un puesto en Google ni fabriques usuarios, debates, testimonios o backlinks.

## Reglas obligatorias
- Trabaja en cambios pequeños y verificables; al final indica archivos modificados, pruebas y riesgos.
- Backend Python/FastAPI asíncrono, Pydantic v2, SQLAlchemy 2; frontend Nuxt 4/Vue 3/TypeScript; PostgreSQL y Redis.
- No interpolar SQL ni ejecutar HTML del usuario; escapar texto, validar entradas y limitar tamaños. Para markdown futuro, sanitizar con lista de permitidos.
- Las escrituras requieren autenticación y autorización en servidor, rate limiting, CSRF si se usan cookies y protección anti-spam; jamás publicar directamente contenido de usuarios nuevos.
- Secretos solo en variables de entorno; nunca commitear .env, credenciales ni datos personales. Minimizar logs de PII.
- Migraciones versionadas con Alembic: no usar create_all en producción ni editar tablas a mano después de la migración inicial.
- Pruebas para permisos, visibilidad de contenido, paginación, errores, inyección, SEO y rutas públicas.
- SSR en páginas indexables; canonical absoluto, meta description única, 404 reales, sitemap con solo URLs públicas canónicas, robots coherente.
- No indexar páginas vacías, perfiles privados, búsqueda interna ni resultados de filtros sin valor.
- Accesibilidad: HTML semántico, navegación por teclado, contraste y estados de foco.
- Evitar dependencias innecesarias, N+1, consultas sin índices y caché de información privada.
- Antes de desplegar: TLS, backups y prueba de restauración, cabeceras seguras, CORS restrictivo, alertas y revisión de dependencias.

## Orden de implementación
1. Corregir y verificar arranque reproducible, dependencias fijadas y tests básicos.
2. Alembic, modelos de usuarios, roles, categorías, temas, respuestas y auditoría.
3. Registro/login, verificación de email, recuperación de contraseña y moderación.
4. CRUD de temas/respuestas con permisos y antispam.
5. SEO a escala: sitemap paginado, canonical, JSON-LD válido, robots, noindex, RSS, imágenes OG.
6. Tests CI, seguridad, rendimiento, métricas y despliegue.

Si falta información, elige defaults seguros, documenta supuestos y sigue. No añadir publicidad hasta tener consentimiento/cumplimiento y aprobación de la plataforma publicitaria.
