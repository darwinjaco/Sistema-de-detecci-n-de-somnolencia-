# LIBRERIAS 
from scipy.spatial import distance
from imutils import face_utils
import imutils
import dlib
import cv2
import socket
import time
import numpy as np

# MAC address of the ESP32 Bluetooth device
esp32_mac_address = '3C:8A:1F:0B:F4:C2'  # Reemplazar con la MAC real

# Configuración de detección de somnolencia
thresh = 0.12
frame_check = 10
periodo_gracia = 1.2  # segundos para que el usuario reaccione

# ---- FUNCIÓN BLUETOOTH ----
def connect_to_esp32(mac_address):
    try:
        print("Conectando a ESP32 por Bluetooth...")
        port = 1
        esp32_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        esp32_sock.connect((mac_address, port))
        print("¡Conexión Bluetooth establecida con ESP32!")
        return esp32_sock
    except Exception as e:
        print("Error en conexión Bluetooth:", e)
        return None

detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

url = 'http://192.168.100.167:81/stream'
cap = cv2.VideoCapture(0)

def enviar_nivel(sock, nivel):
    """Envía el nivel de somnolencia por Bluetooth y lo imprime"""
    if sock is None:
        print("(Simulación) ENVIAR: somnolencia_{}".format(nivel))
        return
    
    try:
        if nivel == 1:
            sock.send(b'1')
            print("ENVIADO: somnolencia_1 - Buzzer al 50%")
        elif nivel == 2:
            sock.send(b'2')
            print("ENVIADO: somnolencia_2 - Buzzer 50% + Motor 50%")
        elif nivel == 3:
            sock.send(b'3')
            print("ENVIADO: somnolencia_3 - Buzzer 100% + Motor 100% + LED")
    except Exception as e:
        print("Error al enviar por Bluetooth:", e)

def main():
    # Conectar Bluetooth
    esp32_sock = connect_to_esp32(esp32_mac_address)
    
    # Variables de estado del sistema
    nivel_actual = 0
    estado_anterior = 0  # 0 = despierto, 1 = somnoliento
    tiempo_inicio_somnolencia = 0
    tiempo_ultimo_cambio = 0
    contador_episodios = 0
    nivel_alcanzado = 0  # Máximo nivel alcanzado
    
    if not cap.isOpened():
        print("No se pudo abrir la cámara desde Python. Verifica la URL o la conexión.")
        if esp32_sock:
            esp32_sock.close()
        return
    else:
        print("Stream de ESP32-CAM abierto correctamente desde Python.")

    flag = 0
    while True:
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print("Error: No se pudo recibir el frame. Reintentando...")
            time.sleep(0.1)
            continue
            
        if frame.shape[0] == 0 or frame.shape[1] == 0:
            print("Advertencia: Frame vacío recibido. Reintentando...")
            time.sleep(0.1)
            continue

        frame = imutils.resize(frame, width=450)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        subjects = detect(gray, 0)
        
        # Verificar si hay somnolencia en el frame actual
        somnolencia_actual = False
        
        for subject in subjects:
            shape = predict(gray, subject)
            shape = face_utils.shape_to_np(shape)
            leftEye = shape[lStart:lEnd]
            rightEye = shape[rStart:rEnd]
            leftEAR = eye_aspect_ratio(leftEye)
            rightEAR = eye_aspect_ratio(rightEye)
            ear = (leftEAR + rightEAR) / 2.0
            
            leftEyeHull = cv2.convexHull(leftEye)
            rightEyeHull = cv2.convexHull(rightEye)
            cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
            cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
            
            if ear < thresh:
                flag += 1
                print(f"EAR: {ear:.3f} - Frames consecutivos: {flag}/{frame_check}")
                if flag >= frame_check:
                    somnolencia_actual = True
            else:
                flag = 0
        
        # Lógica de manejo de estados
        tiempo_actual = time.time()
        
        # Transición: despierto -> somnoliento
        if somnolencia_actual and not estado_anterior:
            print("\n--- NUEVO EPISODIO DE SOMNOLENCIA DETECTADO ---")
            estado_anterior = 1
            tiempo_inicio_somnolencia = tiempo_actual
            tiempo_ultimo_cambio = tiempo_actual
            
            # Solo incrementar el contador si no hemos alcanzado nivel 3
            if nivel_alcanzado < 3:
                contador_episodios += 1
                nivel_actual = min(contador_episodios, 3)
                nivel_alcanzado = max(nivel_alcanzado, nivel_actual)
                print(f"Episodio #{contador_episodios} - Nivel asignado: {nivel_actual}")
                enviar_nivel(esp32_sock, nivel_actual)
            else:
                # Si ya estamos en nivel 3, enviamos nivel 3 nuevamente
                nivel_actual = 3
                print("Episodio adicional en nivel 3 - Reenviando alerta máxima")
                enviar_nivel(esp32_sock, 3)
        
        # Estado: sigue somnoliento
        elif somnolencia_actual and estado_anterior:
            tiempo_transcurrido = tiempo_actual - tiempo_inicio_somnolencia
            print(f"Somnolencia continua: {tiempo_transcurrido:.1f}s/{periodo_gracia}s")
            
            # Verificar si ha pasado el periodo de gracia sin despertarse
            if tiempo_transcurrido >= periodo_gracia:
                # Si aún no está en nivel 3, saltar directamente
                if nivel_actual < 3:
                    print(f"¡PERIODO DE GRACIA EXCEDIDO! Saltando a nivel 3")
                    nivel_actual = 3
                    nivel_alcanzado = 3
                    enviar_nivel(esp32_sock, 3)
        
        # Transición: somnoliento -> despierto
        elif not somnolencia_actual and estado_anterior:
            print("\n--- FIN DE EPISODIO DE SOMNOLENCIA ---")
            estado_anterior = 0
            tiempo_ultimo_cambio = tiempo_actual
            
            # Si estamos en nivel 3, mantenerlo para siempre
            if nivel_alcanzado < 3:
                # Reiniciar solo el estado actual, no el contador
                nivel_actual = 0
                print("Usuario despertado. Esperando siguiente episodio...")
            else:
                print("Usuario despertado (nivel 3 permanente activado)")
        
        # Mostrar información en el frame
        estado_texto = "SOMNOLIENTO" if estado_anterior else "DESPIERTO"
        nivel_texto = f"Nivel: {nivel_alcanzado} | Episodios: {contador_episodios}"
        color_estado = (0, 0, 255) if estado_anterior else (0, 255, 0)
        
        cv2.putText(frame, estado_texto, (10, 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_estado, 2)
        cv2.putText(frame, nivel_texto, (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Mostrar alerta si está en estado de somnolencia
        if estado_anterior:
            tiempo_transcurrido = tiempo_actual - tiempo_inicio_somnolencia
            tiempo_texto = f"Tiempo: {tiempo_transcurrido:.1f}s"
            cv2.putText(frame, tiempo_texto, (10, 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            if nivel_actual == 3:
                cv2.putText(frame, "ALERTA MAXIMA!", (10, 110), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow("Deteccion de Somnolencia", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    # Limpieza final
    cv2.destroyAllWindows()
    cap.release()
    if esp32_sock:
        esp32_sock.close()
        print("Conexión Bluetooth cerrada")

def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

if __name__ == "__main__":
    main()
