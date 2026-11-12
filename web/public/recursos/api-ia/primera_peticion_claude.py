"""Primera petición Messages; sin --live solo muestra una demostración local.

--live requiere ANTHROPIC_API_KEY y ANTHROPIC_MODEL y genera gasto en Anthropic.
El modelo debe estar disponible en tu cuenta. No incluye reintentos automáticos.
"""
import argparse
import os
from types import SimpleNamespace


def request_text(client, model, prompt):
    message = client.messages.create(
        model=model, max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    if message.stop_reason != "end_turn":
        raise ValueError("Respuesta sin final ordinario; revisa stop_reason")
    text = "".join(block.text for block in message.content if block.type == "text")
    if not text:
        raise ValueError("La respuesta no contiene texto")
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Llamada REAL de pago")
    args = parser.parse_args()
    if args.live:
        if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("ANTHROPIC_MODEL"):
            parser.error("Configura ANTHROPIC_API_KEY y ANTHROPIC_MODEL sin compartir la clave")
        from anthropic import Anthropic
        with Anthropic(timeout=30, max_retries=0) as client:
            print(request_text(client, os.environ["ANTHROPIC_MODEL"], "Explica qué es una API en una frase."))
    else:
        # Cliente ficticio: comprueba el código local, no llama a un proveedor.
        message = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Texto de prueba.")])
        client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: message))
        print(request_text(client, "modelo-ficticio", "Pregunta de prueba"))


if __name__ == "__main__":
    main()
