"""Consumidor de texto Responses. Por defecto solo usa eventos ficticios locales.

Una llamada real requiere --live, OPENAI_API_KEY y OPENAI_MODEL; tiene coste.
No implementa herramientas, audio ni moderación. El texto parcial es provisional.
"""
import argparse
import os
from types import SimpleNamespace


def consume_text(events, write, max_chars=20_000):
    parts, size, completed = [], 0, False
    for event in events:
        if event.type == "response.output_text.delta":
            delta = event.delta
            if not isinstance(delta, str):
                raise ValueError("Delta de texto no válido")
            size += len(delta)
            if size > max_chars:
                raise ValueError("Texto mayor que el límite local")
            parts.append(delta)
            write(delta)
        elif event.type in {"error", "response.failed", "response.incomplete"}:
            raise ValueError("La respuesta no terminó correctamente")
        elif event.type == "response.completed":
            completed = True
            break
    if not completed:
        raise ValueError("La conexión terminó sin response.completed")
    return "".join(parts)


def stream_text(client, model, prompt, write):
    stream = client.responses.create(
        model=model, input=prompt, stream=True, max_output_tokens=1000,
    )
    try:
        return consume_text(stream, write)
    finally:
        stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Llamada REAL de pago")
    args = parser.parse_args()
    write = lambda text: print(text, end="", flush=True)
    if args.live:
        if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
            parser.error("Configura OPENAI_API_KEY y OPENAI_MODEL sin compartir la clave")
        from openai import OpenAI
        with OpenAI(timeout=30, max_retries=0) as client:
            stream_text(client, os.environ["OPENAI_MODEL"], "Explica qué es una API en una frase.", write)
    else:
        # Demostración de control de flujo; NO es una respuesta obtenida de una IA.
        events = [SimpleNamespace(type="response.output_text.delta", delta="Texto "),
                  SimpleNamespace(type="response.output_text.delta", delta="de prueba."),
                  SimpleNamespace(type="response.completed")]
        consume_text(events, write)
    print()


if __name__ == "__main__":
    main()
