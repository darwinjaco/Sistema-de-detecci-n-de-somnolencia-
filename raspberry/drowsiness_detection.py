"""
Sistema de Deteccion de Somnolencia
Raspberry Pi 4 + Python

Detecta somnolencia en tiempo real usando vision por computadora (EAR - Eye Aspect Ratio).
Comunica el nivel de alerta a una ESP32 via Bluetooth Serial.

Dependencias:
    pip install scipy imutils dlib opencv-python numpy

Requiere:
    - shape_predictor_68_face_landmarks.dat (descargar desde dlib.net)
    - ESP32 con Bluetooth activo y MAC configurada en credentials.py
"""

from scipy.spatial import distance
from imutils import face_utils
import imutils
import dlib
import cv2
import socket
import time

from credentials import ESP32_MAC_ADDRESS  # ver credentials.example.py

# ========== CONFIGURACION ==========
EAR_THRESHOLD   = 0.12   # Umbral de cierre ocular
FRAME_CHECK     = 10     # Frames consecutivos para confirmar somnolencia
GRACE_PERIOD    = 1.2    # Segundos antes de escalar nivel

# ========== DETECTOR FACIAL ==========
detector  = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

(L_START, L_END) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(R_START, R_END) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

# ========== EAR ==========
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

# ========== BLUETOOTH ==========
def connect_bluetooth(mac_address):
    try:
        print("[BT] Conectando a ESP32...")
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.connect((mac_address, 1))
        print("[BT] Conexion establecida.")
        return sock
    except Exception as e:
        print(f"[BT] Error: {e}. Continuando en modo simulacion.")
        return None

def send_alert(sock, level):
    """Envia nivel de somnolencia (1, 2 o 3) a la ESP32."""
    if sock is None:
        print(f"[SIMULACION] Nivel: {level}")
        return
    try:
        sock.send(str(level).encode())
        print(f"[BT] Enviado: nivel_{level}")
    except Exception as e:
        print(f"[BT] Error al enviar: {e}")

# ========== MAIN ==========
def main():
    sock = connect_bluetooth(ESP32_MAC_ADDRESS)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] No se pudo abrir la camara.")
        return

    # Estado del sistema
    flag                     = 0
    level                    = 0
    max_level                = 0
    episode_count            = 0
    is_drowsy                = False
    drowsiness_start         = 0

    print("[SISTEMA] Deteccion iniciada. Presiona 'q' para salir.\n")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.1)
            continue

        frame = imutils.resize(frame, width=450)
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray, 0)

        drowsy_this_frame = False

        for face in faces:
            shape     = predictor(gray, face)
            shape     = face_utils.shape_to_np(shape)
            left_eye  = shape[L_START:L_END]
            right_eye = shape[R_START:R_END]
            ear       = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0

            cv2.drawContours(frame, [cv2.convexHull(left_eye)],  -1, (0, 255, 0), 1)
            cv2.drawContours(frame, [cv2.convexHull(right_eye)], -1, (0, 255, 0), 1)

            if ear < EAR_THRESHOLD:
                flag += 1
                if flag >= FRAME_CHECK:
                    drowsy_this_frame = True
            else:
                flag = 0

        now = time.time()

        # Transicion: despierto -> somnoliento
        if drowsy_this_frame and not is_drowsy:
            is_drowsy       = True
            drowsiness_start = now
            episode_count   += 1

            if max_level < 3:
                level     = min(episode_count, 3)
                max_level = max(max_level, level)
            else:
                level = 3

            print(f"\n[ALERTA] Episodio #{episode_count} - Nivel {level}")
            send_alert(sock, level)

        # Somnolencia continua - escalar si excede periodo de gracia
        elif drowsy_this_frame and is_drowsy:
            elapsed = now - drowsiness_start
            if elapsed >= GRACE_PERIOD and level < 3:
                print(f"[ALERTA] Periodo de gracia excedido - Escalando a nivel 3")
                level     = 3
                max_level = 3
                send_alert(sock, 3)

        # Transicion: somnoliento -> despierto
        elif not drowsy_this_frame and is_drowsy:
            is_drowsy = False
            if max_level < 3:
                level = 0
            print("[OK] Usuario despierto.")

        # HUD
        color = (0, 0, 255) if is_drowsy else (0, 255, 0)
        cv2.putText(frame, "SOMNOLIENTO" if is_drowsy else "DESPIERTO",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Nivel: {max_level} | Episodios: {episode_count}",
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if is_drowsy:
            elapsed = now - drowsiness_start
            cv2.putText(frame, f"Tiempo: {elapsed:.1f}s",
                        (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow("Deteccion de Somnolencia", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    if sock:
        sock.close()
        print("[BT] Conexion cerrada.")

if __name__ == "__main__":
    main()
