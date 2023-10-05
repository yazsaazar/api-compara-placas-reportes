from flask import Flask, render_template, stream_with_context, Response
import subprocess

app = Flask(__name__)

def generate_output():
    try:
        # Ejecutar el script Python y capturar la salida
        process = subprocess.Popen(['python', 'reconocedor_automatico.py'], stdout=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

        # Leer la salida línea por línea y enviarla al cliente
        for line in process.stdout:
            yield f"data:{line}\n\n"

        process.stdout.close()
        process.wait()

        # Si hay un error, también podrías obtener la salida de error:
        # script_output_error = result.stderr
    except Exception as e:
        yield f"data:Se produjo un error: {str(e)}\n\n"


@app.route('/')
def index2():
    # Renderizar la plantilla HTML
    return render_template('index2.html')

@app.route('/verificar')
def index():
    # Renderizar la plantilla HTML
    return render_template('index.html')

@app.route('/output')
def output():
    # Devolver la respuesta del servidor de eventos
    return Response(generate_output(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5009)
