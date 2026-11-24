import os
import sys
import glob
import math
import time
import subprocess
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from ursina import *
from sensor_mano import conectar_esp32, enviar_comando
from visor_camara_ui import VisorCamaraIntegrado

app = Ursina(
    title="ARCADE SUITE 3D // HAND CONTROL & BLENDER STUDIO",
    borderless=False,
    fullscreen=False,
    development_mode=False
)

window.color = color.hex("#060a16")
window.fps_counter.enabled = True
window.exit_button.visible = False

# ==========================================================
# CONTROL DE MANO FLUIDO PARA EL MENU (MEDIAPIPE HANDS)
# ==========================================================
esp32 = conectar_esp32()
visor_cam = VisorCamaraIntegrado()

class ControlManoMenu:
    def __init__(self, task_path="hand_landmarker.task"):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        base_options = mp_python.BaseOptions(model_asset_path=task_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = mp_vision.HandLandmarker.create_from_options(options)

    def leer(self):
        if not self.cap or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self.detector.detect(mp_img)

        datos = {"detectada": False, "nx": 0.5, "ny": 0.5, "cerrada": False}

        if res.hand_landmarks:
            lm = res.hand_landmarks[0]
            # Centro de la palma (muñeca + base dedo medio)
            nx = (lm[0].x + lm[9].x) / 2.0
            ny = (lm[0].y + lm[9].y) / 2.0

            # Detectar puño cerrado o pinza (puntas de los dedos cerca de la palma/pulgar)
            dist_pinza = math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y)
            dedos_doblados = sum(1 for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)] if lm[tip].y > lm[pip].y)
            cerrada = (dedos_doblados >= 3) or (dist_pinza < 0.055)

            cx, cy = int(nx * w), int(ny * h)
            col_cv = (0, 80, 255) if cerrada else (0, 255, 160)
            for pt in lm:
                cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 3, (0, 235, 255), -1)
            cv2.circle(frame, (cx, cy), 14, col_cv, 3)
            cv2.putText(frame, "SELECCIONANDO (PUNO)" if cerrada else "MANO ACTIVA", (12, h - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, col_cv, 2)

            datos = {"detectada": True, "nx": nx, "ny": ny, "cerrada": cerrada}

        cv2.putText(frame, "MENU: MUEVE MANO Y CIERRA PUNO", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 235, 255), 2)
        visor_cam.actualizar(frame)
        return datos

    def cerrar(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()

sensor_menu = ControlManoMenu()

# ==========================================================
# BUSCADOR AUTOMATICO DE MODELOS BLENDER EN /modelos
# ==========================================================
def buscar_modelo_blender(palabras_clave):
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelos")
    if not os.path.exists(carpeta):
        return None
    archivos = glob.glob(os.path.join(carpeta, "*.*"))
    for ruta in archivos:
        nombre = os.path.basename(ruta).lower()
        ext = os.path.splitext(nombre)[1]
        if ext in (".glb", ".gltf", ".obj", ".fbx", ".bam"):
            if any(k in nombre for k in palabras_clave):
                # Ursina acepta rutas relativas limpias con /
                return os.path.relpath(ruta, os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
    return None

# ==========================================================
# CATALOGO DE JUEGOS Y MODELOS 3D BLENDER
# ==========================================================
JUEGOS = [
    {
        "id": "combat_flight",
        "titulo": "COMBAT FLIGHT 3D",
        "subtitulo": "Dataset Acciones + Control Postural de Nave",
        "script": "juego_blender_3d.py",
        "color": color.hex("#00e1ff"),
        "pos_x": -5.4,
        "cmd_esp": "1",
        "keywords_modelo": ["nave", "ship", "jet", "avion", "star", "arwing", "plane"],
        "escala_modelo": 0.9
    },
    {
        "id": "motogp",
        "titulo": "ISLE OF MAN MOTOGP",
        "subtitulo": "Dataset Acciones + Inclinacion de Torso en Curvas",
        "script": "motogp_isle_of_man_3d.py",
        "color": color.hex("#ff4b2d"),
        "pos_x": -1.8,
        "cmd_esp": "2",
        "keywords_modelo": ["moto", "bike", "ducati", "yamaha", "cycle", "gp"],
        "escala_modelo": 0.9
    },
    {
        "id": "portero",
        "titulo": "GOALKEEPER 3D",
        "subtitulo": "Dataset Acciones + Reflejos de Atajada",
        "script": "portero_3d.py",
        "color": color.hex("#00ff91"),
        "pos_x": 1.8,
        "cmd_esp": "3",
        "keywords_modelo": ["balon", "ball", "porter", "goal", "guante", "glove", "soccer"],
        "escala_modelo": 0.9
    },
    {
        "id": "boxing",
        "titulo": "REAL STEEL BOXING",
        "subtitulo": "Dataset Acciones + Combate Interactivo",
        "script": "real_steel_boxing_3d.py",
        "color": color.hex("#ffc300"),
        "pos_x": 5.4,
        "cmd_esp": "4",
        "keywords_modelo": ["robot", "box", "mech", "steel", "atom", "fighter"],
        "escala_modelo": 0.9
    }
]

estado = {
    "indice": 0,
    "carga_seleccion": 0.0,
    "en_pausa": False,
    "sesiones_jugadas": 0
}

# ==========================================================
# ESCENARIO 3D Y PEDESTALES CON MODELOS BLENDER
# ==========================================================
DirectionalLight(y=10, z=-6, shadows=False)
AmbientLight(color=color.hex("#8aa4d6"))

piso = Entity(model="plane", scale=(32, 1, 24), y=-2.2, color=color.hex("#0a1024"))
for x in range(-14, 15, 2):
    Entity(model="cube", position=(x, -2.18, 2), scale=(0.03, 0.01, 20), color=color.hex("#005577"))
for z in range(-6, 13, 2):
    Entity(model="cube", position=(0, -2.18, z), scale=(28, 0.01, 0.03), color=color.hex("#005577"))

camera.position = (0, 1.8, -11.5)
camera.look_at((0, -0.3, 0))

iconos_3d = []
anillos_luz = []

for j in JUEGOS:
    px = j["pos_x"]
    col = j["color"]

    Entity(model="cylinder", position=(px, -1.75, 0), scale=(2.3, 0.45, 2.3), color=color.hex("#131c36"))
    aro = Entity(model="cylinder", position=(px, -1.5, 0), scale=(2.45, 0.08, 2.45), color=col)
    anillos_luz.append(aro)

    ruta_blender = buscar_modelo_blender(j["keywords_modelo"])
    contenedor = Entity(position=(px, 0.15, 0))

    if ruta_blender:
        print(f"[BLENDER] Cargando modelo 3D para {j['titulo']}: {ruta_blender}")
        modelo_ent = Entity(parent=contenedor, model=ruta_blender)
        # Normalizar tamaño automatico para que encaje perfecto sobre el pedestal
        if modelo_ent.bounds:
            max_dim = max(modelo_ent.bounds.size.x, modelo_ent.bounds.size.y, modelo_ent.bounds.size.z, 0.01)
            factor = 1.85 / max_dim
            modelo_ent.scale = factor
    else:
        # Fallback geometrico estilizado si no hay archivo coincidente en /modelos
        if j["id"] == "combat_flight":
            Entity(parent=contenedor, model="cone", rotation_x=90, scale=(0.75, 1.8, 0.45), color=col)
            Entity(parent=contenedor, model="cube", scale=(2.1, 0.1, 0.55), color=color.white)
        elif j["id"] == "motogp":
            Entity(parent=contenedor, model="cube", rotation_z=12, scale=(1.5, 0.65, 0.45), color=col)
            Entity(parent=contenedor, model="cylinder", position=(-0.55, -0.35, 0), rotation_x=90, scale=(0.65, 0.2, 0.65), color=color.dark_gray)
            Entity(parent=contenedor, model="cylinder", position=(0.55, -0.35, 0), rotation_x=90, scale=(0.65, 0.2, 0.65), color=color.dark_gray)
        elif j["id"] == "portero":
            Entity(parent=contenedor, model="sphere", scale=1.15, color=color.white)
            Entity(parent=contenedor, model="cube", position=(-0.85, 0, 0), scale=(0.35, 0.75, 0.35), color=col)
            Entity(parent=contenedor, model="cube", position=(0.85, 0, 0), scale=(0.35, 0.75, 0.35), color=col)
        else:
            Entity(parent=contenedor, model="cube", scale=(1.1, 1.35, 0.75), color=col)
            Entity(parent=contenedor, model="sphere", position=(0, 0.95, 0), scale=0.65, color=color.light_gray)

    iconos_3d.append(contenedor)

# ==========================================================
# CURSOR DE MANO EN PANTALLA Y HUD
# ==========================================================
cursor_mano = Entity(
    parent=camera.ui,
    model="circle",
    scale=0.032,
    color=color.hex("#00ffa0"),
    visible=False
)
cursor_anillo = Entity(
    parent=cursor_mano,
    model="circle",
    scale=1.55,
    color=color.rgba(0, 255, 160, 70)
)

txt_header = Text(
    text="ARCADE SUITE 3D // MENU POR MANOS + JUEGOS DATASET AI",
    position=(-0.48, 0.46),
    scale=1.28,
    color=color.hex("#00ebff")
)

txt_estado_hw = Text(
    text=f"Menu: HandLandmarker | Juegos: acciones_yolo.pt | ESP32: {'CONECTADO' if esp32 else 'SIMULACION'}",
    position=(-0.48, 0.42),
    scale=0.82,
    color=color.hex("#9ad1ff")
)

txt_titulo_juego = Text(text=JUEGOS[0]["titulo"], origin=(0, 0), position=(0, -0.23), scale=1.8, color=JUEGOS[0]["color"])
txt_subtitulo_juego = Text(text=JUEGOS[0]["subtitulo"], origin=(0, 0), position=(0, -0.28), scale=1.0, color=color.white)

barra_fondo = Entity(parent=camera.ui, model="quad", position=(0, -0.33), scale=(0.52, 0.022), color=color.hex("#1c2640"))
barra_progreso = Entity(parent=camera.ui, model="quad", position=(-0.26, -0.33), origin=(-0.5, 0), scale=(0.001, 0.022), color=color.hex("#00ffa0"))

txt_ayuda = Text(
    text="MUEVE TU MANO IZQ/DER PARA ELEGIR   |   CIERRA EL PUNO (O ENTER) PARA INICIAR   |   FLECHAS / 1-4",
    origin=(0, 0),
    position=(0, -0.43),
    scale=0.78,
    color=color.light_gray
)

def lanzar_juego(indice):
    global sensor_menu, esp32
    juego = JUEGOS[indice]
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), juego["script"])
    if not os.path.exists(script_path):
        txt_subtitulo_juego.text = f"[ERROR] No se encontro {juego['script']}"
        return

    estado["en_pausa"] = True
    estado["carga_seleccion"] = 0.0
    enviar_comando(esp32, juego["cmd_esp"])
    txt_subtitulo_juego.text = f"Iniciando {juego['titulo']}..."

    # Liberar camara y puerto serial antes de abrir el juego con el dataset YOLO
    if sensor_menu:
        sensor_menu.cerrar()
        sensor_menu = None
    if esp32 and esp32.is_open:
        try:
            esp32.close()
        except Exception:
            pass
        esp32 = None

    window.minimized = True
    try:
        subprocess.run([sys.executable, script_path], check=False)
    finally:
        window.minimized = False
        estado["sesiones_jugadas"] += 1
        esp32 = conectar_esp32()
        sensor_menu = ControlManoMenu()
        estado["en_pausa"] = False
        txt_subtitulo_juego.text = juego["subtitulo"]

def input(key):
    if estado["en_pausa"]:
        return
    if key in ("right arrow", "d"):
        estado["indice"] = (estado["indice"] + 1) % len(JUEGOS)
    elif key in ("left arrow", "a"):
        estado["indice"] = (estado["indice"] - 1) % len(JUEGOS)
    elif key in ("1", "2", "3", "4"):
        estado["indice"] = int(key) - 1
        lanzar_juego(estado["indice"])
    elif key in ("enter", "space"):
        lanzar_juego(estado["indice"])
    elif key == "escape":
        if sensor_menu:
            sensor_menu.cerrar()
        application.quit()

def update():
    if estado["en_pausa"] or not sensor_menu:
        return

    mano = sensor_menu.leer()
    if mano and mano["detectada"]:
        cursor_mano.visible = True
        # Convertir coordenadas normalizadas (0..1) a pantalla UI de Ursina
        cursor_mano.x = (mano["nx"] - 0.5) * window.aspect_ratio
        cursor_mano.y = 0.5 - mano["ny"]
        cursor_mano.color = color.hex("#ff4b2d") if mano["cerrada"] else color.hex("#00ffa0")

        # Seleccion directa por zona horizontal de la mano (4 columnas claras)
        norm_x = clamp((mano["nx"] - 0.12) / 0.76, 0.0, 0.999)
        nuevo_idx = int(norm_x * len(JUEGOS))
        if nuevo_idx != estado["indice"]:
            estado["indice"] = nuevo_idx
            estado["carga_seleccion"] = 0.0
            enviar_comando(esp32, "M")

        # Cerrar el puno o hacer pinza llena la barra rapido (0.8 segundos)
        if mano["cerrada"]:
            estado["carga_seleccion"] += time.dt * 1.25
            if estado["carga_seleccion"] >= 1.0:
                lanzar_juego(estado["indice"])
                return
        else:
            estado["carga_seleccion"] = max(0.0, estado["carga_seleccion"] - time.dt * 1.0)
    else:
        cursor_mano.visible = False
        estado["carga_seleccion"] = max(0.0, estado["carga_seleccion"] - time.dt * 0.8)

    sel = estado["indice"]
    juego_actual = JUEGOS[sel]
    txt_titulo_juego.text = juego_actual["titulo"]
    txt_titulo_juego.color = juego_actual["color"]
    txt_subtitulo_juego.text = juego_actual["subtitulo"]
    barra_progreso.scale_x = max(0.001, estado["carga_seleccion"] * 0.52)
    barra_progreso.color = juego_actual["color"]

    for i, icono in enumerate(iconos_3d):
        icono.rotation_y += time.dt * (80 if i == sel else 25)
        target_y = 0.45 + math.sin(time.time() * 3.2) * 0.12 if i == sel else 0.1
        target_scale = 1.25 if i == sel else 0.9
        icono.y = lerp(icono.y, target_y, time.dt * 6)
        icono.scale = lerp(icono.scale, Vec3(target_scale, target_scale, target_scale), time.dt * 6)
        anillos_luz[i].scale = (2.7, 0.12, 2.7) if i == sel else (2.35, 0.06, 2.35)

    camera.x = lerp(camera.x, juego_actual["pos_x"] * 0.45, time.dt * 5.0)

app.run()