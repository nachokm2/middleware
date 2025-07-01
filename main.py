from flask import Flask, request, jsonify
from openai import OpenAI
import json
import requests
import time
import os

app = Flask(__name__)

# Inicializa el cliente OpenAI con la API key desde variable de entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/chat", methods=["POST"])
def chat():
    mensaje = request.json.get("mensaje")
    if not mensaje:
        return jsonify({"error": "No se recibió el mensaje"}), 400

    thread = client.beta.threads.create()

    # Crear mensaje del usuario
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=mensaje
    )

    # Ejecutar asistente
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id="asst_eh2jnFxcgzhVif20Nnt0PmUh"
    )

    max_wait_seconds = 30
    waited = 0

    # Loop esperando tool call o finalización
    while waited < max_wait_seconds:
        run_info = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run_info.status == "completed":
            break

        if run_info.status == "requires_action":
            for call in run_info.required_action.submit_tool_outputs.tool_calls:
                if call.function.name == "buscar_estudiante":
                    args = json.loads(call.function.arguments)
                    # Llamada a tu API externa
                    resultado = requests.post("https://project-sheets.onrender.com/api/matricula", json=args).json()

                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=[
                            {
                                "tool_call_id": call.id,
                                "output": json.dumps(resultado)
                            }
                        ]
                    )
        time.sleep(1)
        waited += 1

    else:
        return jsonify({"error": "Tiempo de espera agotado"}), 504

    mensajes = client.beta.threads.messages.list(thread_id=thread.id)

    # Asumiendo que la respuesta está en el último mensaje y tiene el formato esperado
    try:
        respuesta = mensajes.data[-1].content[0].text.value
    except (IndexError, AttributeError):
        return jsonify({"error": "No se pudo obtener la respuesta"}), 500

    return jsonify({"respuesta": respuesta})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render asigna el puerto como variable de entorno
    app.run(host="0.0.0.0", port=port)
