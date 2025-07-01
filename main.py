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
        thread_id = request.json.get("thread_id")  # Recibimos thread_id desde el frontend si existe

        print(f"Mensaje recibido: {mensaje}")
        if not mensaje:
            return jsonify({"error": "No se recibió el mensaje"}), 400

        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            print(f"Thread creado: {thread_id}")
        else:
            print(f"Usando thread existente: {thread_id}")

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=mensaje
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id="asst_eh2jnFxcgzhVif20Nnt0PmUh"
        )
        print(f"Run creado: {run.id}")

        max_wait_seconds = 30
        waited = 0

        while waited < max_wait_seconds:
            run_info = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            print(f"Estado run: {run_info.status}")

            if run_info.status == "completed":
                print("Run completado")
                break

            if run_info.status == "requires_action":
                for call in run_info.required_action.submit_tool_outputs.tool_calls:
                    print(f"Tool call detectada: {call.function.name}")
                    if call.function.name == "buscar_estudiante":
                        args = json.loads(call.function.arguments)
                        print(f"Argumentos tool call: {args}")

                        resultado = requests.post("https://project-sheets.onrender.com/api/matricula", json=args).json()
                        print(f"Respuesta API externa: {resultado}")

                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
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

        mensajes = client.beta.threads.messages.list(thread_id=thread_id)
        print(f"Mensajes recibidos: {mensajes}")

        print("Contenido completo del último mensaje del asistente:")
        print(mensajes.data[-1].content)

        try:
            respuesta = mensajes.data[-1].content[0].text.value
            print(f"Respuesta final: {respuesta}")
        except (IndexError, AttributeError) as e:
            print(f"Error extrayendo respuesta: {e}")
            return jsonify({"error": "No se pudo obtener la respuesta"}), 500

        # Devuelvo respuesta y thread_id para mantener contexto
        return jsonify({"respuesta": respuesta, "thread_id": thread_id})

    except Exception as e:
        print(f"Error en /chat: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
