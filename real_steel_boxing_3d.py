import os
import random
import math
import time
from ursina import *
from ursina.shaders import lit_with_shadows_shader
from sensor_mano import conectar_esp32, enviar_comando, SensorGestual
from visor_camara_ui import VisorCamaraIntegrado

# ==========================================
# 1. INICIALIZAR URSINA E ILUMINACIÓN DE ARENA
# ==========================================
app = Ursina(title="REAL STEEL 3D // ARENA DE BOXEO ROBOT (3RA PERSONA)", borderless=False)
Entity.default_shader = lit_with_shadows_shader

Sky(color=color.rgba32(18, 24, 38, 255))
scene.fog_color = color.rgba32(22, 28, 44, 255)
scene.fog_density = 0.005

luz_principal = DirectionalLight(y=25, z=-18, shadows=False, rotation=(42, -15, 0))
luz_principal.color = color.rgba32(255, 248, 238, 255)

luz_contra = DirectionalLight(y=15, z=18, shadows=False, rotation=(145, 25, 0))
luz_contra.color = color.rgba32(110, 165, 255, 255)

amb = AmbientLight()
amb.color = color.rgba32(150, 160, 180, 255)

esp32 = conectar_esp32()
enviar_comando(esp32, 'I')

# Sensor corporal + Visor integrado en Ursina (evita que OpenCV bloquee la ventana)
sensor = SensorGestual(ancho_pant=1280, alto_pant=720, modelo_yolo="acciones_yolo.pt", modo="cuerpo")
visor_cam = VisorCamaraIntegrado()
sensor.visor_ui = visor_cam

# ==========================================
# 2. CUADRILÁTERO PROFESIONAL Y ESTADIO
# ==========================================
lona = Entity(model='cube', scale=(18, 0.5, 18), position=(0, -0.95, 7.0), color=color.rgba32(42, 62, 92, 255))
borde_lona = Entity(model='cube', scale=(19.4, 0.35, 19.4), position=(0, -1.10, 7.0), color=color.rgba32(185, 38, 38, 255))
suelo_estadio = Entity(model='plane', scale=(80, 1, 80), y=-1.3, z=12, color=color.rgba32(24, 28, 36, 255))

# Esquinas metálicas del ring
esquinas = [(-8.5, -1.5), (8.5, -1.5), (-8.5, 15.5), (8.5, 15.5)]
for ex, ez in esquinas:
    Entity(model='cube', scale=(0.35, 3.2, 0.35), position=(ex, 0.65, ez), color=color.rgba32(210, 215, 225, 255))

# Cuerdas en los 3 lados visibles (fondo, izquierda y derecha)
for alt_cuerda, col_c in [(0.35, color.rgba32(220, 45, 45, 255)), (1.05, color.white), (1.75, color.rgba32(45, 145, 255, 255))]:
    Entity(model='cube', scale=(17.0, 0.07, 0.07), position=(0, alt_cuerda, 15.5), color=col_c)
    Entity(model='cube', scale=(0.07, 0.07, 17.0), position=(-8.5, alt_cuerda, 7.0), color=col_c)
    Entity(model='cube', scale=(0.07, 0.07, 17.0), position=(8.5, alt_cuerda, 7.0), color=col_c)

# Gradas y reflectores del estadio
for gz in (20, 24, 28):
    Entity(model='cube', scale=(38, 1.5, 2.5), position=(0, (gz - 18) * 0.7, gz), color=color.rgba32(35, 42, 56, 255))
for fx in (-12, -4, 4, 12):
    Entity(model='sphere', scale=1.2, position=(fx, 9.5, 18), color=color.rgba32(255, 245, 200, 255))

# Cámara en tercera persona detrás y ligeramente sobre el hombro del robot jugador
camera.position = (0.65, 2.85, -3.6)
camera.look_at((0, 1.25, 6.0))
camera.fov = 72

# ==========================================
# 3. ROBOT GLADIADOR RIVAL Y PERSONAJE EN 3RA PERSONA
# ==========================================
RUTA_RIVAL   = "modelos/robot_rival.glb"
RUTA_JUGADOR = "modelos/robot_jugador.glb"
RUTA_PUNO    = "modelos/puno_jugador.glb"

def forzar_opacidad_modelo(entidad):
    entidad.setShaderAuto()
    entidad.setTransparency(0)
    entidad.setAlphaScale(1.0)
    entidad.double_sided = True

# --- ROBOT RIVAL ---
if os.path.exists(RUTA_RIVAL):
    rival = Entity(model=RUTA_RIVAL, scale=0.88, position=(0, -0.05, 6.2), rotation_y=180)
    forzar_opacidad_modelo(rival)
else:
    rival = Entity(model='cube', scale=(1.5, 2.8, 1.0), position=(0, 0.7, 6.2), color=color.red)

puno_rival_ataque = Entity(parent=rival, model='sphere', scale=0.65, position=(0.85, 1.5, 1.1), color=color.rgba32(255, 60, 30, 255))

# --- PERSONAJE JUGADOR EN TERCERA PERSONA ---
jugador_rig = Entity(position=(0, -0.70, 1.4))
cuerpo_jugador = Entity(parent=jugador_rig)

if os.path.exists(RUTA_JUGADOR):
    mod_jug = Entity(parent=cuerpo_jugador, model=RUTA_JUGADOR, scale=0.88, position=(0, 0.65, 0))
    forzar_opacidad_modelo(mod_jug)
else:
    # Robot boxeador "ATOM BLUE" articulado en tercera persona
    Entity(parent=cuerpo_jugador, model='cube', position=(-0.34, 0.55, 0), scale=(0.34, 1.1, 0.42), color=color.hex("#1e293b"))
    Entity(parent=cuerpo_jugador, model='cube', position=(0.34, 0.55, 0), scale=(0.34, 1.1, 0.42), color=color.hex("#1e293b"))
    # Torso blindado azul cobalto con núcleo dorsal iluminado
    Entity(parent=cuerpo_jugador, model='cube', position=(0, 1.62, 0), scale=(1.25, 1.22, 0.68), color=color.hex("#0284c7"))
    Entity(parent=cuerpo_jugador, model='sphere', position=(0, 1.68, -0.35), scale=0.38, color=color.hex("#38bdf8"))
    # Hombreras
    Entity(parent=cuerpo_jugador, model='sphere', position=(-0.82, 2.02, 0), scale=0.52, color=color.hex("#0369a1"))
    Entity(parent=cuerpo_jugador, model='sphere', position=(0.82, 2.02, 0), scale=0.52, color=color.hex("#0369a1"))
    # Cabeza con cresta neón
    Entity(parent=cuerpo_jugador, model='cube', position=(0, 2.52, 0), scale=(0.56, 0.56, 0.60), color=color.hex("#0ea5e9"))
    Entity(parent=cuerpo_jugador, model='cube', position=(0, 2.65, -0.05), scale=(0.12, 0.35, 0.55), color=color.hex("#00f5d4"))

# Brazos / Guanteletes del personaje en tercera persona
if os.path.exists(RUTA_PUNO):
    puno_izq = Entity(parent=cuerpo_jugador, model=RUTA_PUNO, scale=0.68, position=(-0.92, 1.55, 0.45), rotation=(8, 14, -8))
    puno_der = Entity(parent=cuerpo_jugador, model=RUTA_PUNO, scale=0.68, position=(0.92, 1.55, 0.45), rotation=(8, -14, 8))
    forzar_opacidad_modelo(puno_izq)
    forzar_opacidad_modelo(puno_der)
else:
    puno_izq = Entity(parent=cuerpo_jugador, model='sphere', scale=0.54, position=(-0.92, 1.55, 0.45), color=color.hex("#38bdf8"))
    puno_der = Entity(parent=cuerpo_jugador, model='sphere', scale=0.54, position=(0.92, 1.55, 0.45), color=color.hex("#38bdf8"))

escudo_guardia = Entity(
    parent=cuerpo_jugador,
    model='cube',
    scale=(1.95, 1.45, 0.08),
    position=(0, 1.65, 0.95),
    color=color.rgba32(50, 220, 255, 85),
    enabled=False
)

# ==========================================
# 4. BARRAS DE VIDA VISUALES Y ESTADO
# ==========================================
estado = {
    "hp_jugador": 100,
    "hp_rival": 100,
    "combo": 0,
    "cuerpo_x": 0.0,
    "esquivando": False,
    "golpe_izq_anim": 0.0,
    "golpe_der_anim": 0.0,
    "gancho_anim": 0.0,
    "cd_izq": 0.0,
    "cd_der": 0.0,
    "cd_gancho": 0.0,
    "ia_estado": "mover",
    "ia_timer": time.time() + 1.5,
    "ia_vx": 2.4,
    "shake": 0.0,
    "fin": False
}

particulas = []

# Barra de vida del Rival (arriba a la derecha para no chocar con el visor de cámara)
Entity(parent=camera.ui, model='quad', scale=(0.54, 0.030), position=(0.14, 0.44), color=color.rgba32(40, 20, 25, 230))
barra_rival = Entity(parent=camera.ui, model='quad', scale=(0.52, 0.020), position=(0.14, 0.44), color=color.rgba32(235, 45, 55, 255))
hud_rival   = Text(text="", position=(-0.12, 0.475), scale=1.0, color=color.white)

# Barra de blindaje del Jugador (abajo)
Entity(parent=camera.ui, model='quad', scale=(0.62, 0.032), position=(0, -0.42), color=color.rgba32(20, 30, 45, 230))
barra_jugador = Entity(parent=camera.ui, model='quad', scale=(0.60, 0.022), position=(0, -0.42), color=color.rgba32(30, 195, 255, 255))
hud_jugador   = Text(text="", position=(-0.44, -0.455), scale=0.92, color=color.cyan)

aviso_combate = Text(text="", position=(-0.06, 0.36), scale=1.35, color=color.yellow)
banner_fin    = Text(text="", origin=(0, 0), scale=2.2, enabled=False)

def chispas_metal(pos, col=color.orange, cant=22):
    for _ in range(cant):
        p = Entity(model='cube', scale=random.uniform(0.07, 0.18), position=pos, color=col)
        vel = Vec3(random.uniform(-5.5, 5.5), random.uniform(-2, 6.5), random.uniform(-4.5, 4.5))
        particulas.append({"ent": p, "vel": vel, "vida": 0.45})

# ==========================================
# 5. BUCLE PRINCIPAL DEL COMBATE (60 FPS)
# ==========================================
def update():
    dt = time.dt
    ahora = time.time()

    for pt in particulas[:]:
        pt["ent"].position += pt["vel"] * dt
        pt["vel"].y -= 15 * dt
        pt["vida"] -= dt
        if pt["vida"] <= 0:
            destroy(pt["ent"])
            particulas.remove(pt)

    # Leer movimientos corporales desde SensorGestual (actualiza automáticamente visor_cam)
    cuerpo = sensor.leer_volante()

    # Movimiento lateral del robot jugador (inclinar/desplazar cuerpo izq o der)
    cuerpo_obj_x = estado["cuerpo_x"]
    if cuerpo["manos"] > 0:
        cuerpo_obj_x = clamp((cuerpo["angulo"] / 38.0) * 3.4, -3.4, 3.4)
    if held_keys['q']:
        cuerpo_obj_x = clamp(estado["cuerpo_x"] - 4.5 * dt, -3.4, 3.4)
    elif held_keys['e']:
        cuerpo_obj_x = clamp(estado["cuerpo_x"] + 4.5 * dt, -3.4, 3.4)

    vel_lat = (cuerpo_obj_x - estado["cuerpo_x"]) * 8.5
    estado["cuerpo_x"] = lerp(estado["cuerpo_x"], cuerpo_obj_x, 8.5 * dt)
    jugador_rig.x = estado["cuerpo_x"]
    cuerpo_jugador.rotation_z = lerp(cuerpo_jugador.rotation_z, -vel_lat * 2.2, 10 * dt)

    # Agacharse para esquivar
    estado["esquivando"] = cuerpo["agachado"] and not cuerpo["manos_juntas"]
    cuerpo_jugador.scale_y = lerp(cuerpo_jugador.scale_y, 0.65 if estado["esquivando"] else 1.0, 12 * dt)

    # Cámara en tercera persona siguiendo al personaje con ligero ángulo sobre el hombro
    cam_target_x = estado["cuerpo_x"] * 0.85 + 0.55
    cam_target_y = 2.45 if estado["esquivando"] else 2.85
    if estado["shake"] > 0:
        estado["shake"] -= dt
        camera.x = cam_target_x + random.uniform(-0.14, 0.14)
        camera.y = cam_target_y + random.uniform(-0.10, 0.10)
    else:
        camera.x = lerp(camera.x, cam_target_x, 9 * dt)
        camera.y = lerp(camera.y, cam_target_y, 9 * dt)
    camera.z = -3.6
    camera.look_at(Vec3(estado["cuerpo_x"] * 0.5, 1.35, 6.2))

    if estado["fin"]:
        if held_keys['r'] or cuerpo["disparar"]:
            reiniciar_combate()
        return

    # Gestos corporales de combate
    guardia_activa = cuerpo["manos_juntas"] or held_keys['w'] or held_keys['space']
    escudo_guardia.enabled = guardia_activa

    lanzar_gancho = cuerpo["disparar"] and not guardia_activa
    lanzar_izq = (cuerpo["golpe_izq"] or held_keys['a'] or held_keys['left arrow']) and not guardia_activa and not lanzar_gancho
    lanzar_der = (cuerpo["golpe_der"] or held_keys['d'] or held_keys['right arrow']) and not guardia_activa and not lanzar_gancho

    if lanzar_gancho and (ahora - estado["cd_gancho"] >= 0.65):
        estado["gancho_anim"] = 1.0
        estado["cd_gancho"] = ahora
        evaluar_impacto_jugador(lado="gancho", dano=18)
    elif lanzar_izq and (ahora - estado["cd_izq"] >= 0.36):
        estado["golpe_izq_anim"] = 1.0
        estado["cd_izq"] = ahora
        evaluar_impacto_jugador(lado="izq", dano=8)
    elif lanzar_der and (ahora - estado["cd_der"] >= 0.44):
        estado["golpe_der_anim"] = 1.0
        estado["cd_der"] = ahora
        evaluar_impacto_jugador(lado="der", dano=12)

    # Animación de brazos y torsión del torso en tercera persona
    if guardia_activa:
        puno_izq.position = lerp(puno_izq.position, Vec3(-0.38, 1.92, 0.78), 14 * dt)
        puno_der.position = lerp(puno_der.position, Vec3(0.38, 1.92, 0.78), 14 * dt)
        cuerpo_jugador.rotation_y = lerp(cuerpo_jugador.rotation_y, 0, 12 * dt)
    elif estado["gancho_anim"] > 0:
        estado["gancho_anim"] = max(0.0, estado["gancho_anim"] - 3.6 * dt)
        avance = math.sin(estado["gancho_anim"] * math.pi) * 3.8
        elevacion = math.sin(estado["gancho_anim"] * math.pi) * 1.15
        puno_izq.position = Vec3(-0.42, 1.55 + elevacion, 0.45 + avance)
        puno_der.position = Vec3(0.42, 1.55 + elevacion, 0.45 + avance)
        cuerpo_jugador.rotation_x = math.sin(estado["gancho_anim"] * math.pi) * 14
    else:
        cuerpo_jugador.rotation_x = lerp(cuerpo_jugador.rotation_x, 0, 12 * dt)
        if estado["golpe_izq_anim"] > 0:
            estado["golpe_izq_anim"] = max(0.0, estado["golpe_izq_anim"] - 4.8 * dt)
            avance = math.sin(estado["golpe_izq_anim"] * math.pi) * 3.8
            puno_izq.position = Vec3(-0.92 + avance * 0.18, 1.55 + avance * 0.12, 0.45 + avance)
            cuerpo_jugador.rotation_y = math.sin(estado["golpe_izq_anim"] * math.pi) * 22
        else:
            puno_izq.position = lerp(puno_izq.position, Vec3(-0.92, 1.55 + math.sin(ahora * 5) * 0.05, 0.45), 12 * dt)

        if estado["golpe_der_anim"] > 0:
            estado["golpe_der_anim"] = max(0.0, estado["golpe_der_anim"] - 4.2 * dt)
            avance = math.sin(estado["golpe_der_anim"] * math.pi) * 4.0
            puno_der.position = Vec3(0.92 - avance * 0.18, 1.55 + avance * 0.14, 0.45 + avance)
            cuerpo_jugador.rotation_y = -math.sin(estado["golpe_der_anim"] * math.pi) * 24
        else:
            puno_der.position = lerp(puno_der.position, Vec3(0.92, 1.55 + math.cos(ahora * 5) * 0.05, 0.45), 12 * dt)

        if estado["golpe_izq_anim"] == 0 and estado["golpe_der_anim"] == 0:
            cuerpo_jugador.rotation_y = lerp(cuerpo_jugador.rotation_y, 0, 10 * dt)

    actualizar_ia_rival(dt, ahora, guardia_activa)

    barra_rival.scale_x   = max(0.001, (estado["hp_rival"] / 100.0) * 0.52)
    barra_jugador.scale_x = max(0.001, (estado["hp_jugador"] / 100.0) * 0.60)

    hud_rival.text   = f"RIVAL 'ATOM RED': {max(0, estado['hp_rival'])}%   |   {estado['ia_estado'].upper()}"
    hud_jugador.text = f"TU ROBOT 'ATOM BLUE': {max(0, estado['hp_jugador'])}%   |   COMBO: x{estado['combo']}   |   [Cuerpo] Mover/Golpear  [Manos Juntas] Guardia"

def evaluar_impacto_jugador(lado, dano):
    if abs(rival.x - estado["cuerpo_x"]) < 2.2 and rival.z < 7.2:
        if estado["ia_estado"] == "guardia" and lado != "gancho":
            estado["hp_rival"] = max(0, estado["hp_rival"] - max(2, dano // 4))
            chispas_metal(rival.position + Vec3(0, 1.5, -0.6), color.cyan, 12)
            aviso_combate.text = "BLOQUEADO POR EL RIVAL"
            enviar_comando(esp32, 'S')
        else:
            bonus = min(6, estado["combo"])
            estado["hp_rival"] = max(0, estado["hp_rival"] - (dano + bonus))
            estado["combo"] += 1
            rival.z = min(7.4, rival.z + 0.45)
            rival.rotation_x = -14 if lado in ("der", "gancho") else -9
            estado["shake"] = 0.14
            chispas_metal(rival.position + Vec3(0, 1.6, -0.5), color.orange, 24)
            aviso_combate.text = f"IMPACTO DIRECTO -{dano + bonus} HP"
            enviar_comando(esp32, 'E')

            if estado["hp_rival"] <= 0:
                terminar_combate(victoria=True)
    else:
        estado["combo"] = 0
        aviso_combate.text = "AL AIRE"

def actualizar_ia_rival(dt, ahora, jugador_bloqueando):
    rival.rotation_x = lerp(rival.rotation_x, 0, 8 * dt)
    puno_rival_ataque.z = lerp(puno_rival_ataque.z, 1.1, 8 * dt)

    if estado["ia_estado"] == "mover":
        aviso_combate.text = ""
        rival.z = lerp(rival.z, 5.8, 3.0 * dt)
        rival.x += estado["ia_vx"] * dt
        if abs(rival.x) > 2.2:
            estado["ia_vx"] *= -1

        if ahora >= estado["ia_timer"]:
            if random.random() < 0.72:
                estado["ia_estado"] = "preparar_golpe"
                estado["ia_timer"] = ahora + 0.80
                rival.x = lerp(rival.x, estado["cuerpo_x"], 0.7)
            else:
                estado["ia_estado"] = "guardia"
                estado["ia_timer"] = ahora + 1.2

    elif estado["ia_estado"] == "guardia":
        aviso_combate.text = "RIVAL EN GUARDIA"
        rival.scale_x = 0.78
        if ahora >= estado["ia_timer"]:
            rival.scale_x = 0.88
            estado["ia_estado"] = "mover"
            estado["ia_timer"] = ahora + random.uniform(1.0, 1.8)

    elif estado["ia_estado"] == "preparar_golpe":
        aviso_combate.text = "¡ATAQUE INMINENTE! JUNTA MANOS O MUEVETE"
        rival.rotation_y = 180 + math.sin(ahora * 25) * 12
        puno_rival_ataque.scale = 0.95
        if ahora >= estado["ia_timer"]:
            estado["ia_estado"] = "golpear"
            estado["ia_timer"] = ahora + 0.35
            rival.z = 4.6
            puno_rival_ataque.z = 3.2
            puno_rival_ataque.scale = 0.65
            rival.rotation_y = 180

            if abs(rival.x - estado["cuerpo_x"]) < 1.85:
                if estado["esquivando"]:
                    chispas_metal(Vec3(estado["cuerpo_x"], 1.35, 1.8), color.lime, 18)
                    aviso_combate.text = "¡ESQUIVA PERFECTA!"
                    enviar_comando(esp32, 'S')
                elif jugador_bloqueando:
                    chispas_metal(Vec3(estado["cuerpo_x"], 1.35, 1.8), color.cyan, 24)
                    aviso_combate.text = "¡BLOQUEO PERFECTO!"
                    enviar_comando(esp32, 'S')
                else:
                    estado["hp_jugador"] = max(0, estado["hp_jugador"] - 14)
                    estado["combo"] = 0
                    estado["shake"] = 0.24
                    chispas_metal(Vec3(estado["cuerpo_x"], 1.4, 1.4), color.red, 26)
                    aviso_combate.text = "¡TE GOLPEARON! -14% BLINDAJE"
                    enviar_comando(esp32, 'D')
                    if estado["hp_jugador"] <= 0:
                        terminar_combate(victoria=False)
            else:
                aviso_combate.text = "¡ESQUIVADO LATERALMENTE!"

    elif estado["ia_estado"] == "golpear":
        if ahora >= estado["ia_timer"]:
            estado["ia_estado"] = "mover"
            estado["ia_timer"] = ahora + random.uniform(1.1, 1.9)

def terminar_combate(victoria):
    estado["fin"] = True
    if victoria:
        rival.rotation_x = -85
        rival.y = -0.55
        banner_fin.text = "¡K.O. TÉCNICO! ERES EL CAMPEÓN DE ACERO\nAlza las manos o pulsa R para la revancha"
        banner_fin.color = color.rgba32(40, 230, 90, 255)
        enviar_comando(esp32, 'V')
    else:
        banner_fin.text = "¡SISTEMAS DESTRUIDOS! HAS CAÍDO EN EL RING\nAlza las manos o pulsa R para reintentar"
        banner_fin.color = color.rgba32(240, 50, 50, 255)
        enviar_comando(esp32, 'D')
    banner_fin.enabled = True

def reiniciar_combate():
    rival.position = (0, -0.05, 6.2)
    rival.rotation = (0, 180, 0)
    rival.scale = 0.88
    estado.update({
        "hp_jugador": 100, "hp_rival": 100, "combo": 0, "cuerpo_x": 0.0,
        "ia_estado": "mover", "ia_timer": time.time() + 1.5, "fin": False
    })
    banner_fin.enabled = False
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