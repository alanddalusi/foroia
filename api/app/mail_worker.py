"""Buzón transaccional persistente: ejecutar como un trabajador separado."""
import asyncio
import os
import smtplib
import ssl
import sys
from types import SimpleNamespace
from datetime import timedelta
from email.message import EmailMessage

from sqlalchemy import delete, select

from app.core.db import get_sessionmaker
from app.models import AccountToken, MailOutbox, UserSession, utcnow


def deliver(row):
    message = EmailMessage()
    message['From'] = os.environ.get('SMTP_FROM', 'ForoIA <no-reply@localhost.test>')
    message['To'] = row.recipient
    message['Subject'] = row.subject
    message.set_content(row.body)
    with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT', '1025')), timeout=15) as smtp:
        if os.environ.get('SMTP_STARTTLS', 'false').lower() == 'true':
            smtp.starttls(context=ssl.create_default_context())
        if os.environ.get('SMTP_USER'):
            smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(message)


async def tick():
    if not os.environ.get('SMTP_HOST'):
        return
    async with get_sessionmaker()() as db:
        rows = (await db.scalars(select(MailOutbox).where(MailOutbox.sent_at.is_(None), MailOutbox.created_at > utcnow() - timedelta(days=1)).order_by(MailOutbox.id).limit(20).with_for_update(skip_locked=True))).all()
        for row in rows:
            try:
                await asyncio.to_thread(deliver, row)
            except (OSError, smtplib.SMTPException):
                # No incluir direcciones, enlaces ni respuestas SMTP en logs.
                continue
            row.sent_at, row.body = utcnow(), "[enviado]"
        await db.execute(delete(MailOutbox).where(MailOutbox.created_at < utcnow() - timedelta(days=1)))
        await db.execute(delete(AccountToken).where(AccountToken.expires_at < utcnow()))
        await db.execute(delete(UserSession).where(UserSession.expires_at < utcnow()))
        await db.commit()


async def main():
    while True:
        try:
            await tick()
        except Exception:
            print('Correo temporalmente no disponible; se reintentará.', flush=True)
        await asyncio.sleep(5)


if __name__ == '__main__':
    if '--test' in sys.argv:
        if not all(os.environ.get(k) for k in ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD')):
            raise SystemExit('Configura SMTP_HOST, SMTP_USER y SMTP_PASSWORD antes de probar.')
        if os.environ.get('SMTP_STARTTLS', 'false').lower() != 'true':
            raise SystemExit('La prueba de produccion requiere SMTP_STARTTLS=true y puerto STARTTLS.')
        try:
            deliver(SimpleNamespace(recipient='admin@foroiaaldia.com', subject='Foro IA al Día: prueba de correo',
                body='Prueba del proveedor SMTP de Foro IA al Día. Si has recibido este mensaje, confirma la recepción antes de activar las cuentas públicas. No contiene credenciales ni enlaces de acceso.'))
        except (OSError, smtplib.SMTPException):
            raise SystemExit('El proveedor no ha aceptado el envio. Revisar configuracion de forma privada.') from None
        print('Mensaje aceptado por SMTP. Falta confirmar su recepcion; esto no garantiza entrega en la bandeja de entrada.')
    else:
        asyncio.run(main())
