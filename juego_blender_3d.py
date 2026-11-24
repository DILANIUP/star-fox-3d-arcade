import os
import glob
import math
import time
import random
from ursina import *
from ursina.shaders import lit_with_shadows_shader
from sensor_mano import SensorGestual, conectar_esp32, enviar_comando
from visor_camara_ui import VisorCamaraIntegrado

app = Ursina(
    title="COMBAT FLIGHT 3D // BLENDER STUDIO & CONTROL POSTURAL",
    borderless=False,
    fullscreen=False,
    development_mode=False
)

Entity.default_shader = lit_with_shadows_shader

window.color = color.hex("#040814")
window.fps_counter.enabled = True
window.exit_button.visible = False

# ==========================================================
# HARDWARE Y VISOR DE CAMARA INTEGRADO (DATASET + POSE)
# ==========================================================
esp32 = conectar_esp32()
sensor = SensorGestual(ancho_pant=1280, alto_pant=720, modelo_yolo="acciones_yolo.pt", modo="cuerpo")
visor_cam = VisorCamaraIntegrado()
sensor.visor_ui = visor_cam

# ==========================================================
# UTILIDADES PARA CARGAR MODELOS 3D DE BLENDER (/modelos)
# ==========================================================
def forzar_opacidad_modelo(entidad):
    """Evita que los materiales glTF/glb exportados de Blender se vean translucidos."""
    entidad.setShaderAuto()
    entidad.setTransparency(0)
    entidad.setAlphaScale(1.0)

def buscar_modelo_blender(palabras_clave, excluir=()):
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelos")
    if not os.path.exists(carpeta):
        return None
    archivos = sorted(glob.glob(os.path.join(carpeta, "*.*")))
    for ruta in archivos:
        nombre = os.path.basename(ruta).lower()
        ext = os.path.splitext(nombre)[1]
        if ext in (".glb", ".gltf", ".obj", ".fbx", ".bam"):
            if any(ex in nombre for ex in excluir):
                continue
            if any(k in nombre for k in palabras_clave):
                return os.path.relpath(ruta, os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
    return None

def instanciar_modelo_normalizado(parent, ruta_modelo, escala_objetivo=2.5, rotacion=(0, 0, 0), tinte=None):
    mod = Entity(parent=parent, model=ruta_modelo, rotation=rotacion)
    forzar_opacidad_modelo(mod)
    if tinte is not None:
        mod.color = tinte
    if mod.bounds:
        max_dim = max(mod.bounds.size.x, mod.bounds.size.y, mod.bounds.size.z, 0.01)
        mod.scale = escala_objetivo / max_dim
    return mod

# Buscar todos los assets de Blender disponibles para el juego espacial
RUTA_NAVE_JUGADOR = buscar_modelo_blender(
    ["nave_jugador", "arwing", "starfox", "nave", "ship", "jet", "avion", "plane"],
    excluir=("enemig", "rival", "alien", "ufo")
)
RUTA_NAVE_ENEMIGA = buscar_modelo_blender(
    ["enemig", "rival", "alien", "ufo", "tie", "caza_malo", "interceptor"]
) or RUTA_NAVE_JUGADOR

RUTA_ASTEROIDE = buscar_modelo_blender(
    ["asteroide", "asteroid", "roca", "rock", "meteor", "obstaculo"]
)
RUTA_ARO = buscar_modelo_blender(
    ["aro", "ring", "portal", "anillo", "torus", "estrella", "star"]
)

print(f"[BLENDER ASSETS] Nave Jugador: {RUTA_NAVE_JUGADOR}")
print(f"[BLENDER ASSETS] Nave Enemiga: {RUTA_NAVE_ENEMIGA}")
print(f"[BLENDER ASSETS] Asteroide:    {RUTA_ASTEROIDE}")
print(f"[BLENDER ASSETS] Aro Energia:  {RUTA_ARO}")

# ==========================================================
# ESTADO DE MISION Y TELEMETRIA
# ==========================================================
estado = {
    "puntos": 0,
    "enemigos_abatidos": 0,
    "salud": 100,
    "energia_escudo": 100.0,
    "escudo_activo": False,
    "disparando": False,
    "inclinacion": 0.0,
    "altitud_y": 1.2,
    "ultimo_disparo": 0.0,
    "terminado": False,
    "tiempo_inicio": time.time()
}

# ==========================================================
# ESCENARIO ESPACIAL / CANON FUTURISTA
# ==========================================================
luz_sol = DirectionalLight(y=16, z=-12, shadows=False, rotation=(35, -20, 0))
luz_sol.color = color.rgba32(255, 248, 235, 255)
amb = AmbientLight()
amb.color = color.rgba32(140, 165, 215, 255)

suelo_espacial = Entity(model="plane", scale=(280, 1, 420), y=-4.5, color=color.hex("#081226"))

lineas_pista = []
columnas_lateral = []
NUM_TRAMOS = 26
LARGO_TRAMO = 12.0

for i in range(NUM_TRAMOS):
    z_p = i * LARGO_TRAMO - 20
    linea = Entity(model="cube", position=(0, -4.45, z_p), scale=(0.25, 0.02, 5.5), color=color.hex("#005577"))
    lineas_pista.append(linea)

    col_izq = Entity(model="cube", position=(-12.5, -1.5, z_p), scale=(0.9, 6.5, 1.4), color=color.hex("#132240"))
    col_der = Entity(model="cube", position=(12.5, -1.5, z_p), scale=(0.9, 6.5, 1.4), color=color.hex("#132240"))
    columnas_lateral.extend([col_izq, col_der])

for _ in range(45):
    Entity(
        model="sphere",
        position=(random.uniform(-45, 45), random.uniform(-2, 24), random.uniform(20, 240)),
        scale=random.uniform(0.12, 0.32),
        color=color.white
    )

# ==========================================================
# NAVE DEL JUGADOR (100% MODELO BLENDER)
# ==========================================================
nave = Entity(position=(0, 1.2, 0))

if RUTA_NAVE_JUGADOR:
    instanciar_modelo_normalizado(nave, RUTA_NAVE_JUGADOR, escala_objetivo=2.8)
else:
    Entity(parent=nave, model="cone", rotation_x=90, scale=(0.95, 2.5, 0.55), color=color.white)
    Entity(parent=nave, model="cube", position=(0, 0.22, -0.15), scale=(0.45, 0.32, 0.95), color=color.hex("#00e5ff"))
    Entity(parent=nave, model="cube", position=(0, -0.02, -0.35), scale=(3.4, 0.1, 0.75), color=color.hex("#1d3557"))

# Propulsores traseros y Cupula de Escudo
motor_izq = Entity(parent=nave, model="cone", position=(-0.32, 0, -1.35), rotation_x=-90, scale=(0.24, 0.75, 0.24), color=color.hex("#00f5d4"))
motor_der = Entity(parent=nave, model="cone", position=(0.32, 0, -1.35), rotation_x=-90, scale=(0.24, 0.75, 0.24), color=color.hex("#00f5d4"))

escudo_esfera = Entity(
    parent=nave,
    model="sphere",
    scale=3.8,
    color=color.rgba(0, 195, 255, 85),
    enabled=False
)

# ==========================================================
# ENEMIGOS AEREOS, ASTEROIDES Y AROS DE ENERGIA (MODELOS BLENDER)
# ==========================================================
laseres = []
enemigos = []
asteroides = []
aros_energia = []

for i in range(6):
    ene = Entity(
        position=(random.uniform(-7.5, 7.5), random.uniform(-1.5, 4.2), 55 + i * 32)
    )
    if RUTA_NAVE_ENEMIGA:
        # Si reutiliza el mismo modelo de nave, la rotamos 180° hacia nosotros con tinte rojo combate
        tinte_rival = color.hex("#ff4d6d") if RUTA_NAVE_ENEMIGA == RUTA_NAVE_JUGADOR else None
        instanciar_modelo_normalizado(ene, RUTA_NAVE_ENEMIGA, escala_objetivo=2.4, rotacion=(0, 180, 0), tinte=tinte_rival)
    else:
        Entity(parent=ene, model="cube", scale=(1.5, 0.55, 1.5), color=color.hex("#ff2a55"))
        Entity(parent=ene, model="cube", scale=(2.8, 0.14, 0.55), color=color.hex("#ffbe0b"))

    enemigos.append({
        "ent": ene,
        "vel_z": random.uniform(28.0, 44.0),
        "osc_offset": random.uniform(0, 6.28)
    })

# Asteroides espaciales (Modelo Blender o roca facetada)
for i in range(5):
    ast = Entity(
        position=(random.uniform(-8.0, 8.0), random.uniform(-2.2, 4.4), 70 + i * 38)
    )
    if RUTA_ASTEROIDE:
        instanciar_modelo_normalizado(ast, RUTA_ASTEROIDE, escala_objetivo=2.1)
    else:
        Entity(parent=ast, model="sphere", scale=(1.6, 1.3, 1.5), color=color.hex("#6c757d"))
    asteroides.append({
        "ent": ast,
        "rot_vel": Vec3(random.uniform(-60, 60), random.uniform(-80, 80), random.uniform(-60, 60))
    })

# Aros de energia (Modelo Blender o aro 3D)
for i in range(4):
    aro = Entity(
        position=(random.uniform(-6.5, 6.5), random.uniform(-1.0, 3.8), 45 + i * 48)
    )
    if RUTA_ARO:
        instanciar_modelo_normalizado(aro, RUTA_ARO, escala_objetivo=2.5, tinte=color.hex("#00ff9d"))
    else:
        Entity(parent=aro, model="cylinder", rotation_x=90, scale=(2.3, 0.16, 2.3), color=color.hex("#00ff9d"))
    aros_energia.append(aro)

camera.position = (0, 3.2, -8.5)
camera.look_at((0, 1.0, 10))

# ==========================================================
# HUD DE CABINA Y TELEMETRIA
# ==========================================================
txt_titulo = Text(
    text="COMBAT FLIGHT 3D // BLENDER STUDIO + ARMAS",
    position=(-0.48, 0.46),
    scale=1.22,
    color=color.hex("#00e5ff")
)

txt_estado_gesto = Text(
    text="SISTEMAS EN LINEA",
    position=(-0.48, 0.41),
    scale=0.92,
    color=color.hex("#00ff9d")
)

txt_salud = Text(
    text="NAVE: 100%  |  ESCUDO: 100%",
    position=(0.35, 0.44),
    scale=1.05,
    color=color.hex("#ffd166")
)

barra_incl_fondo = Entity(parent=camera.ui, model="quad", position=(0, -0.35), scale=(0.46, 0.016), color=color.hex("#1c2640"))
punto_incl = Entity(parent=camera.ui, model="circle", position=(0, -0.35), scale=0.026, color=color.hex("#00e5ff"))

txt_marcador = Text(
    text="Puntos: 0  |  Enemigos Abatidos: 0",
    origin=(0, 0),
    position=(0, -0.40),
    scale=0.98,
    color=color.white
)

txt_controles = Text(
    text="INCLINAR IZQ/DER: GIRAR  |  ALZAR MANOS: DISPARAR LASER  |  ABRIR BRAZOS A LOS LADOS: ESCUDO  |  [ESC] MENU",
    origin=(0, 0),
    position=(0, -0.45),
    scale=0.72,
    color=color.light_gray
)

panel_fin = Entity(parent=camera.ui, model="quad", scale=(0.95, 0.45), color=color.rgba(10, 16, 32, 230), enabled=False)
txt_fin = Text(parent=panel_fin, text="", origin=(0, 0), position=(0, 0.05), scale=1.30, color=color.hex("#ff4d6d"))

def disparar_laser():
    ahora = time.time()
    if ahora - estado["ultimo_disparo"] < 0.22:
        return
    estado["ultimo_disparo"] = ahora

    for offset_x in (-1.35, 1.35):
        rayo = Entity(
            model="cube",
            position=(nave.x + offset_x, nave.y, nave.z + 1.5),
            scale=(0.14, 0.14, 2.4),
            color=color.hex("#00ff9d")
        )
        laseres.append(rayo)
    enviar_comando(esp32, "F")

def salir_al_menu():
    if sensor is not None:
        sensor.cerrar()
    if esp32 is not None and esp32.is_open:
        try:
            esp32.write(b"0")
            esp32.close()
        except Exception:
            pass
    application.quit()

def reiniciar_mision():
    estado["puntos"] = 0
    estado["enemigos_abatidos"] = 0
    estado["salud"] = 100
    estado["energia_escudo"] = 100.0
    estado["escudo_activo"] = False
    estado["terminado"] = False
    estado["tiempo_inicio"] = time.time()
    nave.position = (0, 1.2, 0)
    panel_fin.enabled = False
    sensor.recalibrar_postura()
    for i, e in enumerate(enemigos):
        e["ent"].position = (random.uniform(-7.5, 7.5), random.uniform(-1.5, 4.2), 55 + i * 32)
    for i, a in enumerate(asteroides):
        a["ent"].position = (random.uniform(-8.0, 8.0), random.uniform(-2.2, 4.4), 70 + i * 38)

def input(key):
    if key == "escape":
        salir_al_menu()
    elif key == "c":
        sensor.recalibrar_postura()
    elif key == "r" and estado["terminado"]:
        reiniciar_mision()

def update():
    if estado["terminado"]:
        return

    # 1. Leer gestos posturales
    datos = sensor.leer_volante()
    angulo_usuario = datos["angulo"]
    disparo_activo = datos["disparar"]           # Alzar las manos
    escudo_gesto = datos["brazos_abiertos"]      # Abrir brazos a los lados

    # Respaldo con teclado
    if held_keys["left arrow"] or held_keys["a"]:
        angulo_usuario = -36.0
    elif held_keys["right arrow"] or held_keys["d"]:
        angulo_usuario = 36.0
    if held_keys["space"] or held_keys["up arrow"]:
        disparo_activo = True
    if held_keys["e"] or held_keys["shift"]:
        escudo_gesto = True

    # 2. Control de Escudo al abrir los brazos a los lados
    if escudo_gesto and estado["energia_escudo"] > 5.0:
        estado["escudo_activo"] = True
        estado["energia_escudo"] = max(0.0, estado["energia_escudo"] - time.dt * 26.0)
    else:
        estado["escudo_activo"] = False
        estado["energia_escudo"] = min(100.0, estado["energia_escudo"] + time.dt * 14.0)

    escudo_esfera.enabled = estado["escudo_activo"]
    if estado["escudo_activo"]:
        escudo_esfera.rotation_y += time.dt * 140

    # 3. Control de Disparo al alzar las manos
    estado["disparando"] = disparo_activo
    if disparo_activo:
        disparar_laser()

    # 4. Movimiento de la Nave (Izquierda -> Izquierda, Derecha -> Derecha)
    inclinacion_obj = clamp(angulo_usuario, -48.0, 48.0)
    estado["inclinacion"] = lerp(estado["inclinacion"], inclinacion_obj, time.dt * 8.0)

    nave.rotation_z = -estado["inclinacion"]
    nave.rotation_y = estado["inclinacion"] * 0.25
    nave.x += (estado["inclinacion"] / 48.0) * 15.5 * time.dt
    nave.x = clamp(nave.x, -8.5, 8.5)

    alt_objetivo = clamp((0.68 - datos["altura"]) * 12.0 + 1.2, -2.2, 4.6) if datos["manos"] > 0 else 1.2
    nave.y = lerp(nave.y, alt_objetivo, time.dt * 4.5)
    nave.rotation_x = -(nave.y - alt_objetivo) * 12.0

    punto_incl.x = (estado["inclinacion"] / 48.0) * 0.22
    punto_incl.color = color.hex("#00ff9d") if disparo_activo else (color.hex("#00b4d8") if estado["escudo_activo"] else color.hex("#00e5ff"))

    # 5. Desplazar entorno espacial
    vel_avance = 48.0 * time.dt
    total_tramo = NUM_TRAMOS * LARGO_TRAMO
    for ent in lineas_pista + columnas_lateral:
        ent.z -= vel_avance
        if ent.z < -20:
            ent.z += total_tramo

    # 6. Actualizar rayos laser y colisiones contra enemigos y asteroides
    for rayo in laseres[:]:
        rayo.z += 115.0 * time.dt
        impacto = False
        for e in enemigos:
            ene = e["ent"]
            if abs(rayo.z - ene.z) < 2.2 and abs(rayo.x - ene.x) < 1.8 and abs(rayo.y - ene.y) < 1.5:
                estado["puntos"] += 100
                estado["enemigos_abatidos"] += 1
                ene.position = (random.uniform(-7.5, 7.5), random.uniform(-1.5, 4.2), random.uniform(135, 195))
                enviar_comando(esp32, "E")
                impacto = True
                break
        if not impacto:
            for a in asteroides:
                ast = a["ent"]
                if abs(rayo.z - ast.z) < 2.2 and abs(rayo.x - ast.x) < 1.6 and abs(rayo.y - ast.y) < 1.6:
                    estado["puntos"] += 40
                    ast.position = (random.uniform(-8.0, 8.0), random.uniform(-2.2, 4.4), random.uniform(140, 210))
                    enviar_comando(esp32, "E")
                    impacto = True
                    break
        if impacto or rayo.z > 160:
            laseres.remove(rayo)
            destroy(rayo)

    # 7. Actualizar naves enemigas de Blender
    for e in enemigos:
        ene = e["ent"]
        ene.z -= e["vel_z"] * time.dt
        ene.x += math.sin(time.time() * 2.0 + e["osc_offset"]) * 2.2 * time.dt
        ene.rotation_z = math.cos(time.time() * 2.0 + e["osc_offset"]) * 22.0

        if ene.z < -10:
            ene.position = (random.uniform(-7.5, 7.5), random.uniform(-1.5, 4.2), random.uniform(130, 190))

        if abs(ene.z - nave.z) < 1.8 and abs(ene.x - nave.x) < 1.7 and abs(ene.y - nave.y) < 1.3:
            ene.position = (random.uniform(-7.5, 7.5), random.uniform(-1.5, 4.2), random.uniform(140, 200))
            if estado["escudo_activo"]:
                estado["puntos"] += 50
                estado["enemigos_abatidos"] += 1
                enviar_comando(esp32, "S")
            else:
                estado["salud"] = max(0, estado["salud"] - 20)
                enviar_comando(esp32, "C")

    # 8. Actualizar asteroides de Blender
    for a in asteroides:
        ast = a["ent"]
        ast.z -= vel_avance * 1.15
        ast.rotation += a["rot_vel"] * time.dt
        if ast.z < -10:
            ast.position = (random.uniform(-8.0, 8.0), random.uniform(-2.2, 4.4), random.uniform(140, 210))

        if abs(ast.z - nave.z) < 1.7 and abs(ast.x - nave.x) < 1.5 and abs(ast.y - nave.y) < 1.4:
            ast.position = (random.uniform(-8.0, 8.0), random.uniform(-2.2, 4.4), random.uniform(145, 215))
            if estado["escudo_activo"]:
                estado["puntos"] += 30
                enviar_comando(esp32, "S")
            else:
                estado["salud"] = max(0, estado["salud"] - 15)
                enviar_comando(esp32, "C")

    # 9. Aros de recarga de escudo y puntos
    for aro in aros_energia:
        aro.z -= vel_avance
        aro.rotation_z += time.dt * 110
        if aro.z < -10:
            aro.position = (random.uniform(-6.5, 6.5), random.uniform(-1.0, 3.8), random.uniform(135, 195))

        if abs(aro.z - nave.z) < 1.8 and abs(aro.x - nave.x) < 1.8 and abs(aro.y - nave.y) < 1.8:
            estado["puntos"] += 50
            estado["energia_escudo"] = min(100.0, estado["energia_escudo"] + 35.0)
            aro.position = (random.uniform(-6.5, 6.5), random.uniform(-1.0, 3.8), random.uniform(140, 200))
            enviar_comando(esp32, "P")

    # 10. Actualizar camara y HUD
    camera.x = lerp(camera.x, nave.x * 0.55, time.dt * 5.0)
    camera.y = lerp(camera.y, nave.y + 2.0, time.dt * 4.0)
    camera.rotation_z = lerp(camera.rotation_z, -estado["inclinacion"] * 0.14, time.dt * 5.0)

    txt_salud.text = f"NAVE: {estado['salud']}%  |  ESCUDO: {int(estado['energia_escudo'])}%"
    txt_salud.color = color.hex("#00b4d8") if estado["escudo_activo"] else (color.hex("#ff4d6d") if estado["salud"] <= 40 else color.hex("#ffd166"))

    if estado["escudo_activo"]:
        txt_estado_gesto.text = "BRAZOS ABIERTOS -> ESCUDO DE ENERGIA ACTIVO!"
        txt_estado_gesto.color = color.hex("#00b4d8")
    elif disparo_activo:
        txt_estado_gesto.text = "MANOS ARRIBA -> DISPARANDO LASERES!"
        txt_estado_gesto.color = color.hex("#00ff9d")
    elif datos["manos"] > 0:
        if abs(estado["inclinacion"]) <= 6:
            txt_estado_gesto.text = "VUELO ESTABLE // LISTO PARA COMBATE"
        else:
            lado = "IZQUIERDA" if estado["inclinacion"] < 0 else "DERECHA"
            txt_estado_gesto.text = f"VIRANDO {lado} ({int(estado['inclinacion'])} deg)"
        txt_estado_gesto.color = color.hex("#00e5ff")
    else:
        txt_estado_gesto.text = "BUSCANDO PILOTO EN CAMARA..."
        txt_estado_gesto.color = color.hex("#ffd166")

    txt_marcador.text = f"Puntos: {estado['puntos']}  |  Enemigos Abatidos: {estado['enemigos_abatidos']}"

    if estado["salud"] <= 0:
        estado["terminado"] = True
        panel_fin.enabled = True
        txt_fin.text = (
            f"NAVE DERRIBADA - FIN DE LA MISION\n\n"
            f"Puntos: {estado['puntos']}  |  Enemigos Abatidos: {estado['enemigos_abatidos']}\n\n"
            f"Presiona [R] para reintentar  o  [ESC] para volver al Dashboard"
        )
        enviar_comando(esp32, "L")

app.run()