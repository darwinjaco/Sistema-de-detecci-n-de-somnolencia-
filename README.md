# Sistema Portatil de Deteccion de Somnolencia en Conductores

![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%204-red)
![Platform](https://img.shields.io/badge/platform-ESP32-blue)
![Language](https://img.shields.io/badge/language-Python%20%7C%20C%2B%2B-green)
![Protocol](https://img.shields.io/badge/protocol-Bluetooth-lightblue)
![Status](https://img.shields.io/badge/status-Presentado%20ESPOL%202025-yellow)

Sistema embebido que detecta somnolencia en conductores en tiempo real usando vision por computadora. Presentado en la Feria de Electronica ESPOL 2025 junto a Jeremy Rafael Delgado, bajo la guia de Ing. Sandra Coello e Ing. Ronald Solis.

---

## Arquitectura del sistema

```
Raspberry Pi 4
  └── Python (OpenCV + dlib)
        ├── Captura de camara en tiempo real
        ├── Deteccion facial (68 landmarks)
        ├── Calculo EAR (Eye Aspect Ratio)
        └── Bluetooth Serial  -->  ESP32
                                      ├── Fase 1: Alerta leve
                                      ├── Fase 2: Motor vibracion 50% + Telegram
                                      └── Fase 3: Motor vibracion 100% + Telegram
```

---

## Stack tecnologico

| Capa | Tecnologia |
|---|---|
| Vision por computadora | Python, OpenCV, dlib |
| Deteccion facial | shape_predictor_68_face_landmarks |
| Microcontrolador | ESP32 (Arduino framework) |
| Comunicacion | Bluetooth Serial (RFCOMM) |
| Alertas remotas | Telegram Bot API |
| Actuador haptico | Motor de vibracion PWM |
| Configuracion WiFi | Web server AP embebido en ESP32 |

---

## Estructura del repositorio

```
Sistema-Deteccion-Somnolencia/
├── raspberry/
│   ├── drowsiness_detection.py      # Logica principal de deteccion
│   └── credentials.example.py      # Plantilla de credenciales
├── firmware/
│   ├── src/
│   │   ├── main.cpp                 # Firmware ESP32
│   │   └── credentials.example.h   # Plantilla de credenciales
│   └── .gitignore
├── .gitignore
└── README.md
```

---

## Como usar

### Requisitos - Raspberry Pi
- Python 3.8+
- `pip install scipy imutils dlib opencv-python numpy`
- Archivo `shape_predictor_68_face_landmarks.dat` (descargar desde [dlib.net](http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2))

### Requisitos - ESP32
- PlatformIO o Arduino IDE
- Librerias: BluetoothSerial, HTTPClient, WebServer, EEPROM

### Pasos

1. Clonar el repo
   ```bash
   git clone https://github.com/darwinjaco/Sistema-Deteccion-Somnolencia.git
   ```

2. Configurar credenciales Python
   ```bash
   cd raspberry
   cp credentials.example.py credentials.py
   # Editar credentials.py con la MAC de tu ESP32
   ```

3. Configurar credenciales ESP32
   ```bash
   cd firmware/src
   cp credentials.example.h credentials.h
   # Editar credentials.h con tu token de Telegram y contrasena AP
   ```

4. Flashear la ESP32
   ```bash
   cd firmware
   pio run --target upload
   ```

5. Ejecutar la deteccion
   ```bash
   cd raspberry
   python drowsiness_detection.py
   ```

---

## Logica de deteccion

El sistema usa el metodo EAR (Eye Aspect Ratio) para detectar cierre ocular prolongado:

- EAR menor a 0.12 por 10 frames consecutivos activa el estado de somnolencia
- Fase 1: primer episodio — alerta silenciosa
- Fase 2: segundo episodio o somnolencia continua — vibracion 50% + Telegram
- Fase 3: tercer episodio o periodo de gracia excedido — vibracion 100% + Telegram critico

---

## Presentacion

Este proyecto fue presentado en la Feria de Electronica ESPOL 2025 con un simulador de conduccion en el que el sistema identifico signos de fatiga y emitio alertas preventivas en tiempo real ante la comunidad politecnica.

---

## Licencia

MIT - Darwin Jacome, Jeremy Delgado
