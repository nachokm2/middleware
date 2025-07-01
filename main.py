from flask import Flask, request, jsonify
from openai import OpenAI
import json
import requests
import time

client = OpenAI()
app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    mensaje = request.json["mensaje"]
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
        assistant_id="asst_tu_id_aqui"
    )

    # Loop esperando tool call
    while True:
        run_info = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run_info.status == "completed":
            break

        if run_info.status == "requires_action":
            for call in run_info.required_action.submit_tool_outputs.tool_calls:
                if call.function.name == "buscar_estudiante":
                    args = json.loads(call.function.arguments)
                    # Llamada a tu API
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

    mensajes = client.beta.threads.messages.list(thread_id=thread.id)
    respuesta = mensajes.data[-1].content[0].text.value
    return jsonify({"respuesta": respuesta})
