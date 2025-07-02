from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import json
import requests
import time
import os

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/chat", methods=["POST"])
def chat():
    try:
        mensaje = request.json.get("mensaje")
        print(f"Mensaje recibido: {mensaje}")
        if not mensaje:
            return jsonify({"error": "No se recibió el mensaje"}), 400

        thread = client.beta.threads.create()
        print(f"Thread creado: {thread.id}")

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=mensaje
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id="asst_eh2jnFxcgzhVif20Nnt0PmUh"
        )
        print(f"Run creado: {run.id}")

        max_wait_seconds = 30
        waited = 0

        while waited < max_wait_seconds:
            run_info = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(f"Estado run: {run_info.status}")

            if run_info.status == "completed":
                print("Run completado")
                break

            if run_info.status == "requires_action":
                for call in run_info.required_action.submit_tool_outputs.tool_calls:
                    print(f"Tool call detectada: {call.function.name}")
                    args = json.loads(call.function.arguments)
                    print(f"Argumentos tool call: {args}")

                    if call.function.name == "buscar_estudiante":
                        resultado = requests.post("https://project-sheets.onrender.com/api/matricula", json=args).json()

                    elif call.function.name == "buscar_programa":
                        resultado = requests.post("https://project-sheets.onrender.com/api/oferta", json=args).json()

                    else:
                        resultado = {"error": f"Función no reconocida: {call.function.name}"}

                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=[{
                            "tool_call_id": call.id,
                            "output": json.dumps(resultado)
                        }]
                    )

            time.sleep(1)
            waited += 1
        else:
            return jsonify({"error": "Tiempo de espera agotado"}), 504

        mensajes = client.beta.threads.messages.list(thread_id=thread.id)
        print(f"Mensajes recibidos: {mensajes}")

        # Buscar el último mensaje del asistente
        respuesta = None
        for mensaje in reversed(mensajes.data):
            if mensaje.role == "assistant":
                if mensaje.content and hasattr(mensaje.content[0], "text"):
                    respuesta = mensaje.content[0].text.value
                    break

        if not respuesta:
            return jsonify({"error": "No se pudo obtener una respuesta del asistente"}), 500

        print(f"Respuesta final: {respuesta}")
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        print(f"Error en /chat: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
