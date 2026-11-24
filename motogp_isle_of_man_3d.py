import os
import random
import math
import time
from ursina import *
from ursina.shaders import lit_with_shadows_shader
from sensor_mano import conectar_esp32, enviar_comando, SensorGestual
from visor_camara_ui import VisorCamaraIntegrado

# ==========================================
# 1. INICIALIZAR URSINA Y CLIMA ISLA DE MAN
# ==========================================
app = Ursina(title="ISLE OF MAN TT // MOTOGP CURVAS 3D", borderless=False)
Entity.default_shader = lit_with_shadows_shader

Sky(color=color.rgba32(115, 175, 225, 255))
scene.fog_color = color.rgba32(175, 205, 230, 255)
scene.fog_density = 0.0068

sol = DirectionalLight(y=35, z=-25, shadows=False, rotation=(50, -30, 0))
sol.color = color.rgba32(255, 245, 225, 255)
amb = AmbientLight()
amb.color = color.rgba32(135, 148, 160, 255)

esp32 = conectar_esp32()
enviar_comando(esp32, 'I')

sensor = SensorGestual(ancho_pant=1280, alto_pant=720, modelo_yolo="acciones_yolo.pt", modo="cuerpo")
visor_cam = VisorCamaraIntegrado()
sensor.visor_ui = visor_cam

# ==========================================
# 2. CARGAR TU MOTO GP DE FÁBRICA
# ==========================================
RUTA_MOTO_JUG = "modelos/moto_jugador.glb"
RUTAS_RIVALES = [
    "modelos/moto_rival_1.glb",
    "modelos/moto_rival_2.glb",
    "modelos/moto_rival_3.glb"
]

if os.path.exists(RUTA_MOTO_JUG):
    moto_jugador = Entity(model=RUTA_MOTO_JUG, scale=1.15, position=(0, 0, 0))
    moto_jugador.setShaderAuto()
else:
    moto_jugador = Entity(model='cube', scale=(0.6, 1.0, 2.0), position=(0, 0.5, 0), color=color.azure)

# ==========================================
# 3. FUNCIÓN MATEMÁTICA DEL TRAZADO CON CURVAS
# ==========================================
ANCHO_PISTA = 11.8
NUM_TRAMOS = 72
LARGO_TRAMO = 4.2

def obtener_centro_pista(dist_metros):
    """Genera rectas rápidas, curvas abiertas y chicanes enlazadas en X."""
    d = dist_metros * 0.016
    curva_larga = math.sin(d * 0.55) * 18.0
    chicane     = math.sin(d * 1.45) * 6.5
    return curva_larga + chicane

def obtener_curvatura(dist_metros):
    """Derivada aproximada: indica qué tan cerrada es la curva hacia la izq (-) o der (+)."""
    return (obtener_centro_pista(dist_metros + 4.0) - obtener_centro_pista(dist_metros)) / 4.0

# Pradera base infinita
pradera = Entity(model='plane', scale=(380, 1, 360), y=-0.05, z=130, color=color.rgba32(66, 120, 52, 255))

# Construir 72 segmentos articulados de carretera, muros de piedra, casas y árboles
tramos_pista = []
for i in range(NUM_TRAMOS):
    z_tramo = (i - 3) * LARGO_TRAMO
    padre_tramo = Entity(position=(0, 0, z_tramo))

    # Asfalto del tramo
    Entity(parent=padre_tramo, model='plane', scale=(ANCHO_PISTA, 1, LARGO_TRAMO + 0.35), y=0.0, color=color.rgba32(42, 44, 48, 255))

    # Línea central blanca discontinua
    if i % 2 == 0:
        Entity(parent=padre_tramo, model='plane', scale=(0.22, 1, LARGO_TRAMO * 0.65), y=0.015, color=color.white)

    # Bordes blancos, pianos rojo/blanco y muros de piedra tradicionales
    col_piano = color.rgba32(215, 35, 35, 255) if (i % 2 == 0) else color.white
    for lado in (-1, 1):
        Entity(parent=padre_tramo, model='plane', scale=(0.24, 1, LARGO_TRAMO + 0.35), position=(lado * ANCHO_PISTA * 0.46, 0.015, 0), color=color.white)
        Entity(parent=padre_tramo, model='cube', scale=(0.55, 0.08, LARGO_TRAMO + 0.3), position=(lado * ANCHO_PISTA * 0.52, 0.04, 0), color=col_piano)
        Entity(parent=padre_tramo, model='cube', scale=(0.75, 1.15, LARGO_TRAMO + 0.3), position=(lado * ANCHO_PISTA * 0.58, 0.55, 0), color=color.rgba32(128, 124, 116, 255))

    # Casas de piedra del pueblo TT y árboles siguiendo la curva
    if i % 3 == 0:
        lado_dec = random.choice([-1, 1])
        if random.random() < 0.55:
            x_casa = lado_dec * random.uniform(9.8, 13.5)
            tono_pared = random.choice([color.rgba32(228, 222, 208, 255), color.rgba32(175, 168, 155, 255)])
            Entity(parent=padre_tramo, model='cube', position=(x_casa, 1.8, 0), scale=(4.2, 3.6, 5.2), color=tono_pared)
            Entity(parent=padre_tramo, model='prism', position=(x_casa, 4.3, 0), scale=(4.6, 1.6, 5.4), rotation_y=90, color=color.rgba32(62, 58, 64, 255))
        else:
            x_arb = lado_dec * random.uniform(8.5, 15.0)
            Entity(parent=padre_tramo, model='cylinder', position=(x_arb, 1.2, 0), scale=(0.35, 2.4, 0.35), color=color.rgba32(82, 56, 36, 255))
            Entity(parent=padre_tramo, model='sphere', position=(x_arb, 3.4, 0), scale=(2.8, 2.6, 2.8), color=color.rgba32(44, 96, 42, 255))

    # Colinas verdes de Snaefell al fondo
    if i % 4 == 0:
        for lado_c in (-1, 1):
            Entity(
                parent=padre_tramo,
                model='sphere',
                position=(lado_c * random.uniform(32, 46), -4.0, 0),
                scale=(random.uniform(28, 40), random.uniform(14, 24), random.uniform(28, 40)),
                color=color.rgba32(58, 108, 48, 255)
            )

    tramos_pista.append(padre_tramo)

camera.position = (0, 2.45, -5.4)
camera.rotation_x = 11

# ==========================================
# 4. COMPETIDORES MOTOGP Y ESTADO DE CARRERA
# ==========================================
estado = {
    "velocidad": 175.0,
    "distancia": 0.0,
    "meta_dist": 4000.0,
    "offset_carril": 0.0,   # Posición lateral relativa al centro de la curva (-4.8 a +4.8)
    "posicion": 12,
    "t_inicio": time.time(),
    "fin": False
}

rivales = []
particulas = []

hud_top = Text(text="", position=(-0.22, 0.46), scale=1.10, color=color.rgba32(15, 25, 45, 255))
hud_vel = Text(text="", position=(0.24, -0.42), scale=1.45, color=color.rgba32(255, 215, 0, 255))
hud_ctrl = Text(
    text="RECTO: NORMAL (175 KM/H) | MANOS ARRIBA: TURBO (295 KM/H) | AGACHARSE: FRENAR | INCLINAR: CURVAS",
    origin=(0, 0),
    position=(0, -0.475),
    scale=0.68,
    color=color.white
)
aviso_curva = Text(text="", position=(-0.14, 0.35), scale=1.5, color=color.rgba32(225, 45, 25, 255))
banner  = Text(text="", origin=(0, 0), scale=2.3, enabled=False)

def chispas_3d(pos, cant=14):
    for _ in range(cant):
        p = Entity(model='cube', scale=random.uniform(0.08, 0.18), position=pos, color=color.orange)
        vel = Vec3(random.uniform(-4.5, 4.5), random.uniform(1.5, 5.5), random.uniform(-4, 2))
        particulas.append({"ent": p, "vel": vel, "vida": 0.4})

# Crear parrilla de 11 pilotos rivales que también siguen las curvas de la pista
for idx in range(11):
    ruta_r = RUTAS_RIVALES[idx % len(RUTAS_RIVALES)]
    carril_rel = random.uniform(-3.8, 3.8)
    dist_riv = 28.0 + idx * 28.0
    if os.path.exists(ruta_r):
        m_riv = Entity(model=ruta_r, scale=1.15, position=(0, 0, dist_riv))
        m_riv.setShaderAuto()
    else:
        m_riv = Entity(model='cube', scale=(0.6, 1.0, 2.0), position=(0, 0.5, dist_riv), color=color.red)

    rivales.append({
        "ent": m_riv,
        "dist": dist_riv,               # Distancia absoluta en metros sobre el circuito
        "offset_carril": carril_rel,    # Posición dentro del ancho del asfalto
        "vel_kmh": random.uniform(145.0, 215.0),
        "vx": random.choice([-1.2, 1.2])
    })

# ==========================================
# 5. BUCLE PRINCIPAL DE CARRERA (60 FPS)
# ==========================================
def update():
    dt = time.dt
    ahora = time.time()

    for pt in particulas[:]:
        pt["ent"].position += pt["vel"] * dt
        pt["vel"].y -= 14 * dt
        pt["vida"] -= dt
        if pt["vida"] <= 0:
            destroy(pt["ent"]); particulas.remove(pt)

    # Lectura de movimientos del cuerpo
    v = sensor.leer_volante()

    if estado["fin"]:
        if held_keys['r'] or v["disparar"]:
            reiniciar_carrera()
        return

    # 1. Control corporal: inclinar cuerpo (girar), manos arriba (turbo), agacharse (freno)
    if v["manos"] > 0:
        inclinacion_deseada = clamp(v["angulo"] * 1.15, -48.0, 48.0)
        turbo = v["disparar"]
        frenar = v["agachado"]
    else:
        girar = held_keys['d'] - held_keys['a']
        inclinacion_deseada = girar * 42.0
        turbo = held_keys['w'] or held_keys['space'] or held_keys['up arrow']
        frenar = held_keys['s'] or held_keys['down arrow']

    # Velocidad normal al estar recto (175 km/h), turbo al alzar manos (295 km/h), freno al agacharse (75 km/h)
    if frenar:
        vel_objetivo = 75.0
    elif turbo:
        vel_objetivo = 295.0
    else:
        vel_objetivo = 175.0

    estado["velocidad"] = lerp(estado["velocidad"], vel_objetivo, 2.8 * dt)

    # Tumbar la moto en curva
    moto_jugador.rotation_z = lerp(moto_jugador.rotation_z, inclinacion_deseada, 10 * dt)

    # Calcular curvatura actual de la pista y fuerza centrífuga
    curvatura_actual = obtener_curvatura(estado["distancia"])
    fuerza_centrifuga = curvatura_actual * (estado["velocidad"] * 0.055)

    # Movimiento lateral sobre el carril = giro del piloto - empujón centrífugo de la curva
    giro_piloto = (moto_jugador.rotation_z / 45.0) * 13.0
    estado["offset_carril"] += (giro_piloto - fuerza_centrifuga) * dt

    # Límite con los muros de piedra
    limite_pista = ANCHO_PISTA * 0.43
    if abs(estado["offset_carril"]) > limite_pista:
        estado["offset_carril"] = clamp(estado["offset_carril"], -limite_pista, limite_pista)
        estado["velocidad"] = max(110.0, estado["velocidad"] - 190.0 * dt)
        chispas_3d(moto_jugador.position + Vec3(0, 0.5, 0), 3)
        enviar_comando(esp32, 'E')

    # Avanzar distancia en el circuito
    estado["distancia"] += (estado["velocidad"] / 3.6) * dt
    centro_actual = obtener_centro_pista(estado["distancia"])

    # Posicionar la moto en la coordenada real de la carretera
    moto_jugador.x = centro_actual + estado["offset_carril"]
    moto_jugador.rotation_y = math.degrees(math.atan(curvatura_actual)) * 0.65

    # Cámara persigue la moto y anticipa la curva hacia adelante
    centro_adelante = obtener_centro_pista(estado["distancia"] + 16.0)
    camera.fov = lerp(camera.fov, 62 + (estado["velocidad"] - 150) * 0.11, 5 * dt)
    camera.x = lerp(camera.x, moto_jugador.x * 0.85 + (centro_adelante - centro_actual) * 0.25, 7 * dt)
    camera.look_at(Vec3(centro_adelante + estado["offset_carril"] * 0.5, 0.9, 18.0))

    # Alerta visual cuando se aproxima una curva cerrada
    curvatura_futura = obtener_curvatura(estado["distancia"] + 38.0)
    if curvatura_futura > 0.28:
        aviso_curva.text = ">>> CURVA DERECHA >>>"
    elif curvatura_futura < -0.28:
        aviso_curva.text = "<<< CURVA IZQUIERDA <<<"
    else:
        aviso_curva.text = ""

    # 2. Actualizar la geometría de los 72 tramos articulados de la carretera
    progreso_subtramo = (estado["distancia"] % LARGO_TRAMO)
    indice_base = int(estado["distancia"] // LARGO_TRAMO)

    for i, tramo in enumerate(tramos_pista):
        z_rel = (i - 3) * LARGO_TRAMO - progreso_subtramo
        dist_tramo = (indice_base + i - 3) * LARGO_TRAMO
        x_tramo = obtener_centro_pista(dist_tramo)
        ang_tramo = math.degrees(math.atan(obtener_curvatura(dist_tramo)))

        tramo.z = z_rel
        tramo.x = x_tramo
        tramo.rotation_y = ang_tramo

    # 3. Actualizar competidores GP siguiendo las curvas del trazado
    for r in rivales:
        ent = r["ent"]
        r["dist"] += (r["vel_kmh"] / 3.6) * dt

        r["offset_carril"] += r["vx"] * dt
        if abs(r["offset_carril"]) > 4.2:
            r["vx"] *= -1

        if r["dist"] < estado["distancia"] - 22.0:
            r["dist"] = estado["distancia"] + random.uniform(190.0, 270.0)
            r["offset_carril"] = random.uniform(-3.8, 3.8)
            r["vel_kmh"] = random.uniform(155.0, 225.0)

        z_rival = r["dist"] - estado["distancia"]
        x_centro_riv = obtener_centro_pista(r["dist"])
        curv_riv = obtener_curvatura(r["dist"])

        ent.z = z_rival
        ent.x = x_centro_riv + r["offset_carril"]
        ent.rotation_y = math.degrees(math.atan(curv_riv)) * 0.75
        ent.rotation_z = clamp(curv_riv * 55.0 + r["vx"] * 12.0, -45.0, 45.0)

        if abs(ent.z - moto_jugador.z) < 1.85 and abs(ent.x - moto_jugador.x) < 0.95:
            chispas_3d((ent.position + moto_jugador.position) * 0.5 + Vec3(0, 0.6, 0), 12)
            empujon = 1.3 if estado["offset_carril"] >= r["offset_carril"] else -1.3
            estado["offset_carril"] = clamp(estado["offset_carril"] + empujon * 0.6, -limite_pista, limite_pista)
            r["offset_carril"] -= empujon * 0.6
            estado["velocidad"] *= 0.86
            enviar_comando(esp32, 'E')

    pilotos_delante = sum(1 for r in rivales if r["dist"] > estado["distancia"])
    estado["posicion"] = 1 + pilotos_delante

    # 4. Meta a 4.0 km
    if estado["distancia"] >= estado["meta_dist"]:
        estado["fin"] = True
        tiempo_total = round(ahora - estado["t_inicio"], 1)
        banner.text = f"¡META ISLA DE MAN TT!\nPUESTO FINAL: {estado['posicion']}º / 12  |  TIEMPO: {tiempo_total}s\nAlza las manos o pulsa R para correr otra vez"
        banner.color = color.rgba32(20, 145, 45, 255) if estado["posicion"] <= 3 else color.rgba32(220, 140, 10, 255)
        banner.enabled = True
        enviar_comando(esp32, 'V' if estado["posicion"] <= 3 else 'I')

    restante_m = max(0, int(estado["meta_dist"] - estado["distancia"]))
    estado_txt = " [TURBO ON]" if turbo else (" [FRENANDO]" if frenar else " [NORMAL]")
    hud_top.text = f"POSICION: {estado['posicion']}º / 12  |  META EN: {restante_m} m  |  INCLINACION: {int(moto_jugador.rotation_z)}°"
    hud_vel.text = f"{int(estado['velocidad'])} KM/H{estado_txt}"

def reiniciar_carrera():
    for idx, r in enumerate(rivales):
        r["dist"] = 28.0 + idx * 28.0
        r["offset_carril"] = random.uniform(-3.8, 3.8)
    estado.update({"velocidad": 175.0, "distancia": 0.0, "offset_carril": 0.0, "t_inicio": time.time(), "fin": False})
    moto_jugador.position = (0, 0, 0)
    moto_jugador.rotation_z = 0
    banner.enabled = False
    sensor.recalibrar_postura()
    enviar_comando(esp32, 'I')

def input(key):
    if key == 'escape':
        if esp32 and esp32.is_open: esp32.close()
        sensor.cerrar()
        application.quit()
    elif key == 'c':
        sensor.recalibrar_postura()

app.run()