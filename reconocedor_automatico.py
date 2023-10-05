import os
# Mostrar solo errores de TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# Deshabilitar GPU (correr en CPU)
# os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from alpr.alpr import ALPR
from argparse import ArgumentParser
import yaml
import logging
from timeit import default_timer as timer
import cv2
import mysql.connector

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main_demo(cfg, demo=True, benchmark=True, save_vid=False):
    alpr = ALPR(cfg['modelo'], cfg['db'])
    video_path = cfg['video']['fuente']
    cap = cv2.VideoCapture(video_path)
    is_img = cv2.haveImageReader(video_path)
    cv2_wait = 1

    logger.info(f'Se va analizar la fuente: {video_path}')
    frame_id = 0
    if save_vid:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) + 0.5)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) + 0.5)
        size = (width, height)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter('alpr-result.avi', fourcc, 20.0, size)
    # Cada cuantos frames hacer inferencia
    intervalo_reconocimiento = cfg['video']['frecuencia_inferencia']
    if not is_img:
        logger.info(f'El intervalo del reconocimiento para el video es de: {intervalo_reconocimiento}')

    # Establece la conexión a la base de datos MySQL en XAMPP
    db_connection = mysql.connector.connect(
        host="containers-us-west-127.railway.app",
        user="root",
        password="Ns68awzE6RkGk1oNKy8C",
        database="railway"
    )

    cursor = db_connection.cursor()

    # Crear una tabla para almacenar las placas si no existe
    cursor.execute('''CREATE TABLE IF NOT EXISTS placas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    placa VARCHAR(255)
                )''')

    # Crear un conjunto para llevar un registro de las placas impresas
    placas_impresas = set()

    while True:
        return_value, frame = cap.read()
        if return_value:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            break

        if demo:
            frame_w_pred, total_time, plate_results = alpr.mostrar_predicts(frame)
            frame_w_pred = cv2.cvtColor(frame_w_pred, cv2.COLOR_RGB2BGR)
            frame_w_pred_r = cv2.resize(frame_w_pred, dsize=(1400, 1000))

            # Imprimir resultados de las placas en la consola
            for plate_result in plate_results:
                # Verificar si la placa ya se ha registrado antes
                if plate_result not in placas_impresas:
                    print("Placa:", plate_result)
                    # Consultar si la placa está en la tabla "reportes"
                    cursor.execute("SELECT * FROM reportes WHERE Placa = %s", (plate_result,))
                    result = cursor.fetchone()
                    if result:
                        print("¡Se ha encontrado un auto robado!")
                        print("ID del auto:", result[0])
                        print("Propietario:", result[1])
                        print("Marca:", result[2])
                        print("Modelo:", result[3])
                        print("Color:", result[4])
                        # Puedes continuar imprimiendo otros campos según la estructura de tu tabla "reportes"
                    # Insertar la placa en la base de datos
                    cursor.execute("INSERT INTO placas (placa) VALUES (%s)", (plate_result,))
                    # Guardar la placa en el conjunto de placas impresas
                    placas_impresas.add(plate_result)

            if benchmark:
                display_bench = f'ms: {total_time:.4f} FPS: {1 / total_time:.0f}'
                cv2.putText(frame_w_pred_r, display_bench, (5, 45), cv2.FONT_HERSHEY_SIMPLEX,
                            1.5, (10, 140, 10), 4)

            if save_vid:
                out.write(frame_w_pred)

            cv2.namedWindow("result", cv2.WINDOW_AUTOSIZE)
            cv2.imshow("result", frame_w_pred_r)
            if cv2.waitKey(cv2_wait) & 0xFF == ord('q'):
                break
        else:
            if frame_id % intervalo_reconocimiento == 0:
                start = timer()
                plate_results = alpr.predict(frame)
                total_time = timer() - start

                # Imprimir resultados de las placas en la consola
                for plate_result in plate_results:
                    # Verificar si la placa ya se ha registrado antes
                    if plate_result not in placas_impresas:
                        print("Placa:", plate_result)
                        # Consultar si la placa está en la tabla "reportes"
                        cursor.execute("SELECT * FROM reportes WHERE Placa = %s", (plate_result,))
                        result = cursor.fetchone()
                        if result:
                            print("¡Se ha encontrado un auto robado!")
                            print("ID del auto:", result[0])
                            print("Propietario:", result[1])
                            print("Marca:", result[2])
                            print("Modelo:", result[3])
                            print("Color:", result[4])
                            # Puedes continuar imprimiendo otros campos según la estructura de tu tabla "reportes"
                        # Insertar la placa en la base de datos
                        cursor.execute("INSERT INTO placas (placa) VALUES (%s)", (plate_result,))
                        # Guardar la placa en el conjunto de placas impresas
                        placas_impresas.add(plate_result)

                if benchmark:
                    display_bench = f'ms: {total_time:.4f} FPS: {1 / total_time:.0f}'
                    print(display_bench, flush=True)

        frame_id += 1

    # Guardar los cambios en la base de datos y cerrar la conexión
    db_connection.commit()
    db_connection.close()

    cap.release()
    if save_vid:
        out.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    try:
        parser = ArgumentParser()
        parser.add_argument("--cfg", dest="cfg_file", help="Path del archivo de config, \
                            default: ./config.yaml", default='config.yaml')
        parser.add_argument("--demo", dest="demo",
                            action='store_true', help="En vez de guardar las patentes, mostrar las predicciones")
        parser.add_argument("--guardar_video", dest="save_video",
                            action='store_true', help="Guardar video en ./alpr-result.avi")
        parser.add_argument("--benchmark", dest="bench",
                            action='store_true', help="Medir la inferencia (incluye todo el pre/post processing)")
        args = parser.parse_args()
        with open(args.cfg_file, 'r') as stream:
            try:
                cfg = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                logger.exception(exc)
        main_demo(cfg, args.demo, args.bench, args.save_video)
    except Exception as e:
        logger.exception(e)
