"""Administración local por operador, nunca una ruta pública.

bootstrap: crea una cuenta admin verificada usando variables de entorno.
role EMAIL ROLE: cambia un rol con auditoría; no acepta contraseñas en argumentos.
"""
import asyncio
import os
import sys

from sqlalchemy import delete, select
from app.core.db import get_sessionmaker
from app.models import AuditLog, User, UserSession
from app.modules.accounts import PH, EmailPayload


async def main():
    async with get_sessionmaker()() as db:
        command = sys.argv[1] if len(sys.argv) > 1 else ''
        if command in {'editorial-seed','editorial-preview'}:
            import json
            from app.research.queue import seed_evergreen,prepare_candidate
            from app.models import EditorialCandidate,utcnow
            from app.research.writing import StopRun,generate,Draft,VOICE
            from app.research.sources import SourceError
            from app.research.evidence import catalogue
            from app.research.config import settings
            await seed_evergreen(db)
            if command=='editorial-seed':
                print('Cola editorial inicializada sin generar artículos.');return
            rows=(await db.scalars(select(EditorialCandidate).where(EditorialCandidate.engine=='evergreen',
                EditorialCandidate.state.in_(['queued','ready','deferred'])).order_by(EditorialCandidate.priority.desc()).limit(8))).all()
            budget={'remaining':4};result=[]
            for candidate in rows:
                try:
                    docs,policy=await prepare_candidate(db,candidate,utcnow(),budget)
                    reservation=[]
                    async def preview(cost):reservation.append(cost);raise StopRun('preview_no_provider_call')
                    try:await generate(settings(),Draft,VOICE,{'sources':catalogue(docs),'editorial_policy':policy},preview)
                    except StopRun as exc:
                        if str(exc)!='preview_no_provider_call':raise
                    print(json.dumps({'provider_calls':0,'candidate_id':candidate.id,'kind':candidate.kind,
                        'state':candidate.state,'official_documents':len(docs),'verified_example':bool(policy.get('example')),
                        'first_call_maximum_reserved_usd':str(reservation[0]/1_000_000),'weekly_publication_cap':5}))
                    return
                except (StopRun,SourceError) as exc:result.append({'candidate_id':candidate.id,'reason':str(exc) if isinstance(exc,StopRun) else exc.code})
            print(json.dumps({'provider_calls':0,'ready':False,'candidates':result}));return
        elif command == 'polish-titles':
            # Corrige solo la forma de los títulos publicados (mayúscula, tildes, siglas).
            # Sin --apply es una vista previa. No cambia slug, cuerpo ni updated_at.
            import json
            from sqlalchemy import update
            from app.models import Article
            from app.research.title_style import polish_title
            apply = '--apply' in sys.argv[2:]
            changes = []
            for article in (await db.scalars(select(Article).where(Article.status == 'published').order_by(Article.id))).all():
                fixed = polish_title(article.title)
                if fixed == article.title:
                    continue
                changes.append({'id': article.id, 'slug': article.slug, 'before': article.title, 'after': fixed})
                if apply:
                    await db.execute(update(Article).where(Article.id == article.id).values(title=fixed, updated_at=article.updated_at))
                    db.add(AuditLog(actor='operator', action='polish_title', entity_type='article', entity_id=article.id,
                                    details={'before': article.title, 'after': fixed}))
            print(json.dumps({'applied': apply, 'changes': changes}, ensure_ascii=False, indent=1))
            if not apply:
                return
        elif command == 'bootstrap':
            email = EmailPayload(email=os.environ['BOOTSTRAP_EMAIL']).email
            password = os.environ['BOOTSTRAP_PASSWORD']
            if len(password) < 12 or len(password) > 128:
                raise SystemExit('La contraseña debe tener entre 12 y 128 caracteres')
            if await db.scalar(select(User.id).where(User.email == email)):
                print('Cuenta existente conservada; no se han cambiado sus permisos ni contraseña.')
                return
            user = User(email=email, display_name='Administración', password_hash=await asyncio.to_thread(PH.hash, password), role='admin', verified=True)
            db.add(user)
            await db.flush()
            db.add(AuditLog(actor='operator', action='bootstrap_admin', entity_type='user', entity_id=user.id))
        elif command == 'role' and len(sys.argv) == 4:
            role = sys.argv[3]
            if role not in {'member', 'moderator', 'editor', 'admin'}:
                raise SystemExit('Rol no válido')
            user = await db.scalar(select(User).where(User.email == EmailPayload(email=sys.argv[2]).email))
            if not user:
                raise SystemExit('Cuenta no encontrada')
            user.role = role
            db.add(AuditLog(actor='operator', action='set_role', entity_type='user', entity_id=user.id, details={'role': role}))
        elif command in {'block', 'unblock'} and len(sys.argv) == 3:
            user = await db.scalar(select(User).where(User.email == EmailPayload(email=sys.argv[2]).email))
            if not user:
                raise SystemExit('Cuenta no encontrada')
            user.blocked = command == 'block'
            if user.blocked:
                await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
            db.add(AuditLog(actor='operator', action=command, entity_type='user', entity_id=user.id))
        else:
            raise SystemExit('Uso: python -m app.manage bootstrap | role EMAIL ROLE | block EMAIL | unblock EMAIL')
        await db.commit()
        print('Operación registrada correctamente.')


if __name__ == '__main__':
    asyncio.run(main())
