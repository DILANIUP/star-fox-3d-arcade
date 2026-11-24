import os
import random
import math
import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from ursina import *
from ursina.shaders import lit_with_shadows_shader
from sensor_mano import conectar_esp32, enviar_comando
from visor_camara_ui import VisorCamaraIntegrado

# ==========================================
# 1. INICIALIZAR URSINA Y ESTADIO DE FÚTBOL
# ==========================================
app = Ursina(title="GOALKEEPER 3D // PORTERO EN PRIMERA PERSONA", borderless=False)
Entity.default_shader = lit_with_shadows_shader

Sky(color=color.rgba32(25, 45, 80, 255))
scene.fog_color = color.rgba32(30, 52, 88, 255)
scene.fog_density = 0.004

luz_estadio = DirectionalLight(y=35, z=5, shadows=False, rotation=(50, 15, 0))
luz_estadio.color = color.rgba32(255, 250, 240, 255)
amb = AmbientLight()
amb.color = color.rgba32(150, 165, 180, 255)

esp32 = conectar_esp32()
enviar_comando(esp32, 'I')

# Visor integrado en Ursina + Cámara directa solo para manos libres (MediaPipe Hands)
visor_cam = VisorCamaraIntegrado()
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

base_opts = mp_python.BaseOptions(model_asset_path="hand_landmarker.task")
opts = mp_vision.HandLandmarkerOptions(
    base_options=base_opts,
    num_hands=2,
    min_hand_detection_confidence=0.45,
    min_tracking_confidence=0.45,
    running_mode=mp_vision.RunningMode.VIDEO
)
detector_manos = mp_vision.HandLandmarker.create_from_options(opts)

# ==========================================
# 2. CÉSPED, LÍNEAS DEL ÁREA, TRIBUNAS Y PORTERÍA VISIBLES
# ==========================================
for i in range(20):
    col_cesped = color.rgba32(46, 138, 54, 255) if (i % 2 == 0) else color.rgba32(38, 122, 46, 255)
    Entity(model='plane', scale=(60, 1, 3.5), position=(0, 0, i * 3.5 - 6), color=col_cesped)

# Líneas blancas del área
Entity(model='plane', scale=(11.0, 1, 0.16), position=(0, 0.01, 1.2), color=color.white)      # Línea de gol
Entity(model='plane', scale=(18.0, 1, 0.16), position=(0, 0.01, 16.5), color=color.white)     # Línea de área grande
Entity(model='plane', scale=(0.16, 1, 15.3), position=(-9.0, 0.01, 8.85), color=color.white)
Entity(model='plane', scale=(0.16, 1, 15.3), position=(9.0, 0.01, 8.85), color=color.white)
Entity(model='sphere', scale=(0.45, 0.02, 0.45), position=(0, 0.015, 12.0), color=color.white) # Punto penal

# Tribunas del estadio al fondo y reflectores
Entity(model='cube', scale=(70, 11, 4), position=(0, 5.0, 48), color=color.rgba32(35, 45, 68, 255))
for rx in (-18, -6, 6, 18):
    Entity(model='sphere', scale=1.5, position=(rx, 14.0, 46), color=color.rgba32(255, 250, 215, 255))

# Portería completamente visible dentro del encuadre (z = 1.2)
ANCHO_ARCO = 7.4   # -3.7 a +3.7
ALTO_ARCO  = 3.4   # 0.0 a 3.4
Entity(model='cube', scale=(0.20, ALTO_ARCO, 0.20), position=(-ANCHO_ARCO / 2, ALTO_ARCO / 2, 1.2), color=color.white)
Entity(model='cube', scale=(0.20, ALTO_ARCO, 0.20), position=(ANCHO_ARCO / 2, ALTO_ARCO / 2, 1.2), color=color.white)
Entity(model='cube', scale=(ANCHO_ARCO + 0.20, 0.20, 0.20), position=(0, ALTO_ARCO, 1.2), color=color.white)

# Cámara fija gran angular detrás de la línea de gol para ver los 3 palos y todo el campo
camera.position = (0, 2.0, -4.4)
camera.rotation_x = 4
camera.fov = 82

# ==========================================
# 3. GUANTES PROPORCIONADOS, DELANTERO Y BALÓN
# ==========================================
def forzar_opacidad(ent):
    ent.setShaderAuto()
    ent.setTransparency(0)
    ent.setAlphaScale(1.0)

RUTA_GUANTE    = "modelos/guante_portero.glb"
RUTA_BALON     = "modelos/balon_futbol.glb"
RUTA_DELANTERO = "modelos/delantero.glb"

if os.path.exists(RUTA_GUANTE):
    guante_izq = Entity(model=RUTA_GUANTE, scale=0.38, position=(-1.1, 1.5, 1.35), rotation=(28, 180, -12))
    guante_der = Entity(model=RUTA_GUANTE, scale=(-0.38, 0.38, 0.38), position=(1.1, 1.5, 1.35), rotation=(28, 180, 12))
    forzar_opacidad(guante_izq)
    forzar_opacidad(guante_der)
else:
    guante_izq = Entity(model='cube', scale=(0.45, 0.55, 0.14), position=(-1.1, 1.5, 1.35), color=color.azure)
    guante_der = Entity(model='cube', scale=(0.45, 0.55, 0.14), position=(1.1, 1.5, 1.35), color=color.azure)

if os.path.exists(RUTA_DELANTERO):
    delantero = Entity(model=RUTA_DELANTERO, scale=1.25, position=(0, 0, 15.5), rotation_y=180)
    forzar_opacidad(delantero)
else:
    delantero = Entity(model='cube', scale=(0.8, 2.2, 0.6), position=(0, 1.1, 15.5), color=color.red)

if os.path.exists(RUTA_BALON):
    balon = Entity(model=RUTA_BALON, scale=0.68, position=(0, 0.35, 14.5))
    forzar_opacidad(balon)
else:
    balon = Entity(model='sphere', scale=0.60, position=(0, 0.35, 14.5), color=color.white)

# ==========================================
# 4. ESTADO DEL PARTIDO Y FÍSICA DE TIROS
# ==========================================
estado = {
    "puntos": 0,
    "atajadas": 0,
    "goles_contra": 0,
    "max_goles": 5,
    "fase": "preparando",
    "timer_fase": time.time() + 1.4,
    "vel_balon": Vec3(0, 0, 0),
    "curva_x": 0.0,
    "gravedad": 0.0,
    "tipo_tiro": "DIRECTO",
    "fin": False
}

particulas = []
ultimo_ts_ms = 0

hud_top = Text(text="", position=(-0.48, 0.46), scale=1.1, color=color.white)
aviso_tiro = Text(text="", position=(-0.48, 0.41), scale=1.15, color=color.yellow)
txt_controles = Text(
    text="MUEVE TUS DOS MANOS LIBREMENTE PARA TAPAR  |  CIERRA LOS PUÑOS PARA DESPEJAR  |  [ESC] MENU",
    origin=(0, 0),
    position=(0, -0.45),
    scale=0.76,
    color=color.light_gray
)
banner_fin = Text(text="", origin=(0, 0), scale=2.1, enabled=False)

def efecto_impacto(pos, col=color.white, cant=18):
    for _ in range(cant):
        p = Entity(model='sphere', scale=random.uniform(0.08, 0.18), position=pos, color=col)
        vel = Vec3(random.uniform(-4.5, 4.5), random.uniform(-2, 5.5), random.uniform(-3, 4.5))
        particulas.append({"ent": p, "vel": vel, "vida": 0.45})

def preparar_nuevo_tiro():
    x_origen = random.uniform(-5.5, 5.5)
    z_origen = random.uniform(13.0, 19.5)
    delantero.position = Vec3(x_origen, 0, z_origen)
    delantero.look_at(Vec3(0, 0, 1.2))
    delantero.rotation_y += 180

    balon.position = Vec3(x_origen, 0.35, z_origen - 0.85)
    balon.scale = 0.68
    estado["fase"] = "preparando"
    estado["timer_fase"] = time.time() + random.uniform(1.0, 1.5)
    aviso_tiro.text = "¡PREPARADO! EL DELANTERO VA A PATEAR..."
    aviso_tiro.color = color.yellow

def ejecutar_disparo():
    objetivo_x = random.uniform(-3.25, 3.25)
    objetivo_y = random.uniform(0.42, 2.95)
    objetivo_z = 1.2

    tipo = random.choice(["DIRECTO", "CON ROSCA", "VASELINA", "RASO POTENTE"])
    estado["tipo_tiro"] = tipo

    if tipo == "RASO POTENTE":
        objetivo_y = random.uniform(0.35, 0.85)
        tiempo_vuelo = random.uniform(0.85, 1.02)
        curva = 0.0
        grav = 0.0
    elif tipo == "VASELINA":
        objetivo_y = random.uniform(2.2, 3.05)
        tiempo_vuelo = random.uniform(1.15, 1.32)
        curva = 0.0
        grav = 10.5
    elif tipo == "CON ROSCA":
        tiempo_vuelo = random.uniform(0.95, 1.12)
        curva = random.choice([-1, 1]) * random.uniform(5.2, 7.5)
        grav = 1.8
    else:
        tiempo_vuelo = random.uniform(0.88, 1.05)
        curva = 0.0
        grav = 1.2

    dx = objetivo_x - balon.x
    dy = objetivo_y - balon.y
    dz = objetivo_z - balon.z

    vx = (dx - 0.5 * curva * (tiempo_vuelo ** 2)) / tiempo_vuelo
    vy = (dy + 0.5 * grav * (tiempo_vuelo ** 2)) / tiempo_vuelo
    vz = dz / tiempo_vuelo

    estado["vel_balon"] = Vec3(vx, vy, vz)
    estado["curva_x"] = curva
    estado["gravedad"] = grav
    estado["fase"] = "volando"
    aviso_tiro.text = f"TIRO {tipo}"
    aviso_tiro.color = color.cyan
    enviar_comando(esp32, 'S')

def leer_guantes_camara():
    global ultimo_ts_ms
    ret, frame = cap.read()
    manos_detectadas = []
    if ret:
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        ts_ms = int(time.time() * 1000)
        if ts_ms <= ultimo_ts_ms:
            ts_ms = ultimo_ts_ms + 1
        ultimo_ts_ms = ts_ms

        det = detector_manos.detect_for_video(mp_img, ts_ms)

        if det.hand_landmarks:
            for lm in det.hand_landmarks:
                nx, ny = lm[9].x, lm[9].y
                cerrada = (lm[8].y > lm[6].y and lm[12].y > lm[10].y and lm[16].y > lm[14].y)
                cx, cy = int(nx * w), int(ny * h)
                for pt in lm:
                    cv2.circle(frame, (int(pt.x * w), int(pt.y * h)), 2, (0, 235, 255), -1)
                cv2.circle(frame, (cx, cy), 16, (0, 80, 255) if cerrada else (0, 255, 140), -1)
                manos_detectadas.append({"nx": nx, "ny": ny, "cerrada": cerrada})

        cv2.putText(frame, "GUANTES LIBRES (MANOS)", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 150), 2)
        visor_cam.actualizar(frame)

    return manos_detectadas

# ==========================================
# 5. BUCLE PRINCIPAL 3D (60 FPS)
# ==========================================
def update():
    dt = time.dt
    ahora = time.time()

    for pt in particulas[:]:
        pt["ent"].position += pt["vel"] * dt
        pt["vel"].y -= 14 * dt
        pt["vida"] -= dt
        if pt["vida"] <= 0:
            destroy(pt["ent"])
            particulas.remove(pt)

    manos = leer_guantes_camara()

    izq_cerrada = False
    der_cerrada = False

    if len(manos) >= 2:
        manos.sort(key=lambda m: m["nx"])
        m_izq, m_der = manos[0], manos[1]
        tx_i = (m_izq["nx"] - 0.5) * 8.4
        ty_i = (1.0 - m_izq["ny"]) * 3.6
        tx_d = (m_der["nx"] - 0.5) * 8.4
        ty_d = (1.0 - m_der["ny"]) * 3.6

        guante_izq.x = lerp(guante_izq.x, clamp(tx_i, -3.7, 3.7), 18 * dt)
        guante_izq.y = lerp(guante_izq.y, clamp(ty_i, 0.35, 3.35), 18 * dt)
        guante_der.x = lerp(guante_der.x, clamp(tx_d, -3.7, 3.7), 18 * dt)
        guante_der.y = lerp(guante_der.y, clamp(ty_d, 0.35, 3.35), 18 * dt)

        izq_cerrada = m_izq["cerrada"]
        der_cerrada = m_der["cerrada"]
    elif len(manos) == 1:
        m = manos[0]
        tx = (m["nx"] - 0.5) * 8.4
        ty = (1.0 - m["ny"]) * 3.6
        guante_izq.x = lerp(guante_izq.x, clamp(tx - 0.42, -3.7, 3.7), 18 * dt)
        guante_izq.y = lerp(guante_izq.y, clamp(ty, 0.35, 3.35), 18 * dt)
        guante_der.x = lerp(guante_der.x, clamp(tx + 0.42, -3.7, 3.7), 18 * dt)
        guante_der.y = lerp(guante_der.y, clamp(ty, 0.35, 3.35), 18 * dt)
        izq_cerrada = der_cerrada = m["cerrada"]
    else:
        mx = mouse.x * 7.6
        my = 1.7 + mouse.y * 3.4
        guante_izq.x = lerp(guante_izq.x, clamp(mx - 0.45, -3.7, 3.7), 18 * dt)
        guante_izq.y = lerp(guante_izq.y, clamp(my, 0.35, 3.35), 18 * dt)
        guante_der.x = lerp(guante_der.x, clamp(mx + 0.45, -3.7, 3.7), 18 * dt)
        guante_der.y = lerp(guante_der.y, clamp(my, 0.35, 3.35), 18 * dt)
        izq_cerrada = der_cerrada = mouse.left

    guante_izq.rotation_x = lerp(guante_izq.rotation_x, 55 if izq_cerrada else 28, 14 * dt)
    guante_der.rotation_x = lerp(guante_der.rotation_x, 55 if der_cerrada else 28, 14 * dt)

    if estado["fin"]:
        if held_keys['r'] or (izq_cerrada and der_cerrada):
            reiniciar_partido()
        return

    if estado["fase"] == "preparando":
        if ahora >= estado["timer_fase"]:
            ejecutar_disparo()

    elif estado["fase"] == "volando":
        estado["vel_balon"].x += estado["curva_x"] * dt
        estado["vel_balon"].y -= estado["gravedad"] * dt
        balon.position += estado["vel_balon"] * dt

        balon.rotation_z += estado["curva_x"] * 45 * dt
        balon.rotation_x -= 420 * dt

        if balon.y < 0.34:
            balon.y = 0.34
            estado["vel_balon"].y = abs(estado["vel_balon"].y) * 0.65

        # Detectar parada con guante izquierdo o derecho en la línea de gol (z = 1.2)
        if 0.4 <= balon.z <= 2.3:
            dist_izq = math.hypot(balon.x - guante_izq.x, balon.y - guante_izq.y)
            dist_der = math.hypot(balon.x - guante_der.x, balon.y - guante_der.y)

            toca_izq = dist_izq < 0.85
            toca_der = dist_der < 0.85

            if toca_izq or toca_der:
                puno_usado = (toca_izq and izq_cerrada) or (toca_der and der_cerrada)
                estado["atajadas"] += 1

                if puno_usado:
                    estado["puntos"] += 120
                    estado["fase"] = "despejado"
                    estado["timer_fase"] = ahora + 1.1
                    desvio_x = -5.5 if balon.x < 0 else 5.5
                    estado["vel_balon"] = Vec3(desvio_x, 6.0, 15.0)
                    efecto_impacto(balon.position, color.white, 20)
                    aviso_tiro.text = "¡GRAN DESPEJE DE PUÑOS! +120"
                    aviso_tiro.color = color.cyan
                    enviar_comando(esp32, 'E')
                else:
                    estado["puntos"] += 200
                    estado["fase"] = "atrapado"
                    estado["timer_fase"] = ahora + 1.1
                    balon.position = Vec3((guante_izq.x + guante_der.x) * 0.5, (guante_izq.y + guante_der.y) * 0.5, 1.55)
                    efecto_impacto(balon.position, color.lime, 22)
                    aviso_tiro.text = "¡BALÓN ATRAPADO! +200"
                    aviso_tiro.color = color.lime
                    enviar_comando(esp32, 'V')
                return

        if balon.z < 0.3:
            if abs(balon.x) <= (ANCHO_ARCO / 2) and 0 <= balon.y <= ALTO_ARCO:
                estado["goles_contra"] += 1
                efecto_impacto(balon.position, color.red, 25)
                aviso_tiro.text = "¡GOL EN CONTRA!"
                aviso_tiro.color = color.red
                enviar_comando(esp32, 'D')
            else:
                aviso_tiro.text = "¡FUERA! TIRO DESVIADO"
                aviso_tiro.color = color.white

            if estado["goles_contra"] >= estado["max_goles"]:
                estado["fin"] = True
                banner_fin.text = f"FIN DE LA TANDA DE PENALES\nATAJADAS: {estado['atajadas']}  |  PUNTOS: {estado['puntos']}\nCierra ambos puños o pulsa R para jugar"
                banner_fin.color = color.yellow
                banner_fin.enabled = True
            else:
                estado["fase"] = "espera_post"
                estado["timer_fase"] = ahora + 1.1

    elif estado["fase"] == "despejado":
        balon.position += estado["vel_balon"] * dt
        estado["vel_balon"].y -= 12 * dt
        if ahora >= estado["timer_fase"]:
            preparar_nuevo_tiro()

    elif estado["fase"] == "atrapado":
        balon.position = Vec3((guante_izq.x + guante_der.x) * 0.5, (guante_izq.y + guante_der.y) * 0.5, 1.55)
        if ahora >= estado["timer_fase"]:
            preparar_nuevo_tiro()

    elif estado["fase"] == "espera_post":
        if ahora >= estado["timer_fase"]:
            preparar_nuevo_tiro()

    hud_top.text = f"PUNTOS: {estado['puntos']}  |  ATAJADAS: {estado['atajadas']}  |  GOLES EN CONTRA: {estado['goles_contra']} / {estado['max_goles']}"

def reiniciar_partido():
    estado.update({"puntos": 0, "atajadas": 0, "goles_contra": 0, "fin": False})
    banner_fin.enabled = False
    preparar_nuevo_tiro()
    enviar_comando(esp32, 'I')

def input(key):
    if key == 'escape':
        if esp32 and esp32.is_open:
            esp32.close()
        if cap and cap.isOpened():
            cap.release()
        application.quit()
    elif key == 'r' and estado["fin"]:
        reiniciar_partido()

preparar_nuevo_tiro()
app.run()