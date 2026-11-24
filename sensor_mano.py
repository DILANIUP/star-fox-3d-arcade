import cv2
import math
import time
import serial
import serial.tools.list_ports
from ultralytics import YOLO

def conectar_esp32(baudrate=115200):
    puertos = list(serial.tools.list_ports.comports())
    for p in puertos:
        if "USB" in p.description or "CH340" in p.description or "CP210" in p.description or "COM3" in p.device:
            try:
                esp = serial.Serial(p.device, baudrate, timeout=0.05)
                time.sleep(1.5)
                print(f"[OK] ESP32 conectado en {p.device}")
                return esp
            except Exception:
                pass
    print("[AVISO] ESP32 no detectado. Ejecutando en modo simulacion.")
    return None

def enviar_comando(esp32, cmd):
    if esp32 and esp32.is_open:
        try:
            esp32.write(cmd.encode('utf-8'))
        except Exception:
            pass

class SensorGestual:
    def __init__(self, ancho_pant=1280, alto_pant=720, modelo_yolo="acciones_yolo.pt", modo="cuerpo"):
        self.ancho_pant = ancho_pant
        self.alto_pant = alto_pant
        self.modo = modo
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print(f"[ULTRALYTICS] Cargando dataset ({modelo_yolo}) + Pose Medio Cuerpo...")
        self.model_acciones = YOLO(modelo_yolo)
        self.model_pose = YOLO("yolo11n-pose.pt")
        self.visor_ui = None

        self.ny_neutro = None
        self.muestras_calibracion = []

    def _procesar_hibrido(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # 1. Inferencia con tu dataset entrenado (acciones_yolo.pt)
        res_acc = self.model_acciones(frame, verbose=False, conf=0.30)
        accion_dataset = False
        defensa_dataset = False
        punch_dataset = False

        if res_acc and len(res_acc[0].boxes) > 0:
            box = sorted(res_acc[0].boxes, key=lambda b: float(b.conf[0]), reverse=True)[0]
            cls_id = int(box.cls[0])
            clase_detectada = self.model_acciones.names[cls_id].lower()
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            accion_dataset = any(k in clase_detectada for k in ("jump", "run"))
            punch_dataset = any(k in clase_detectada for k in ("punch", "kick"))
            defensa_dataset = any(k in clase_detectada for k in ("squat", "bend", "stretch"))

            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 195, 0), 2)
            cv2.putText(frame, f"DATASET: {clase_detectada.upper()} ({conf:.2f})", (x1, max(22, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 195, 0), 2)

        # 2. Inferencia de medio cuerpo (hombros, codos, muñecas y cabeza)
        res_pose = self.model_pose(frame, verbose=False, conf=0.22)
        datos = None

        if res_pose and res_pose[0].keypoints is not None and len(res_pose[0].keypoints.xy) > 0:
            kpts = res_pose[0].keypoints.xy[0].cpu().numpy()
            confs = res_pose[0].keypoints.conf[0].cpu().numpy() if res_pose[0].keypoints.conf is not None else [1.0]*17

            if len(kpts) >= 11:
                nariz = kpts[0]
                h_a, h_b = kpts[5], kpts[6]
                c_a, c_b = kpts[7], kpts[8]
                m_a, m_b = kpts[9], kpts[10]

                tiene_hombros = (confs[5] > 0.22 and confs[6] > 0.22)
                tiene_cabeza = (confs[0] > 0.22)

                if tiene_hombros or tiene_cabeza:
                    if tiene_hombros:
                        if h_a[0] <= h_b[0]:
                            h_vis_izq, h_vis_der = h_a, h_b
                        else:
                            h_vis_izq, h_vis_der = h_b, h_a

                        torso_x = (h_vis_izq[0] + h_vis_der[0]) / 2.0
                        torso_y = (h_vis_izq[1] + h_vis_der[1]) / 2.0
                        ancho_hombros = max(30.0, h_vis_der[0] - h_vis_izq[0])
                        dy = h_vis_der[1] - h_vis_izq[1]
                        angulo_hombros = math.degrees(math.atan2(dy, ancho_hombros))
                    else:
                        torso_x = nariz[0]
                        torso_y = min(h - 10, nariz[1] + 90)
                        ancho_hombros = 140.0
                        h_vis_izq = (max(10, torso_x - 70), torso_y)
                        h_vis_der = (min(w - 10, torso_x + 70), torso_y)
                        angulo_hombros = 0.0

                    torso_nx = max(0.0, min(1.0, torso_x / w))
                    torso_ny = max(0.0, min(1.0, torso_y / h))

                    if self.ny_neutro is None:
                        self.muestras_calibracion.append(torso_ny)
                        if len(self.muestras_calibracion) >= 15:
                            self.ny_neutro = sum(self.muestras_calibracion) / len(self.muestras_calibracion)
                    ny_ref = self.ny_neutro if self.ny_neutro is not None else 0.58

                    # Ordenar muñecas visualmente (Izquierda y Derecha en pantalla)
                    tiene_m_a = confs[9] > 0.24
                    tiene_m_b = confs[10] > 0.24
                    pt_ext_a = m_a if tiene_m_a else (c_a if confs[7] > 0.24 else h_vis_izq)
                    pt_ext_b = m_b if tiene_m_b else (c_b if confs[8] > 0.24 else h_vis_der)

                    if pt_ext_a[0] <= pt_ext_b[0]:
                        m_vis_izq, m_vis_der = pt_ext_a, pt_ext_b
                        conf_m_izq = confs[9] if tiene_m_a else confs[7]
                        conf_m_der = confs[10] if tiene_m_b else confs[8]
                    else:
                        m_vis_izq, m_vis_der = pt_ext_b, pt_ext_a
                        conf_m_izq = confs[10] if tiene_m_b else confs[8]
                        conf_m_der = confs[9] if tiene_m_a else confs[7]

                    # GESTO 1: MANOS JUNTAS -> DEFENSA / GUARDIA (BOXEO)
                    dist_manos = math.hypot(m_vis_izq[0] - m_vis_der[0], m_vis_izq[1] - m_vis_der[1])
                    es_manos_juntas = bool(
                        (conf_m_izq > 0.24) and (conf_m_der > 0.24) and
                        (dist_manos < ancho_hombros * 0.72)
                    )

                    # GESTO 2: MANOS ARRIBA -> GANCHO (UPPERCUT) / DISPARO / TURBO
                    ref_hombro = min(h_vis_izq[1], h_vis_der[1])
                    mano_arriba_izq = (conf_m_izq > 0.24) and (m_vis_izq[1] < ref_hombro - 18)
                    mano_arriba_der = (conf_m_der > 0.24) and (m_vis_der[1] < ref_hombro - 18)
                    es_manos_arriba = bool((mano_arriba_izq or mano_arriba_der or accion_dataset) and not es_manos_juntas)

                    # GESTO 3: GOLPES DIRECTOS IZQ / DER (JAB / CROSS)
                    # Cuando una mano se eleva a altura de pecho/hombro o se extiende sin estar arriba ni juntas
                    golpe_izq = bool(
                        not es_manos_juntas and not es_manos_arriba and
                        (conf_m_izq > 0.25) and (m_vis_izq[1] < torso_y + 25) and
                        (abs(m_vis_izq[0] - h_vis_izq[0]) > ancho_hombros * 0.35 or punch_dataset)
                    )
                    golpe_der = bool(
                        not es_manos_juntas and not es_manos_arriba and
                        (conf_m_der > 0.25) and (m_vis_der[1] < torso_y + 25) and
                        (abs(m_vis_der[0] - h_vis_der[0]) > ancho_hombros * 0.35 or punch_dataset)
                    )

                    # GESTO 4: ABRIR BRAZOS A LOS LADOS -> ESCUDO (AVION)
                    envergadura = abs(m_vis_der[0] - m_vis_izq[0])
                    es_brazos_abiertos = bool(
                        (conf_m_izq > 0.22) and (conf_m_der > 0.22) and
                        (envergadura > ancho_hombros * 1.75) and
                        not es_manos_arriba
                    )

                    # GESTO 5: AGACHARSE -> FRENO (MOTOGP) / ESQUIVA (BOXEO)
                    es_agachado = bool((torso_ny > ny_ref + 0.09) or (torso_ny > 0.72))

                    # Giro / desplazamiento lateral natural
                    giro_cuerpo = ((torso_nx - 0.5) * 95.0) + (angulo_hombros * 1.4)

                    # Dibujo en visor
                    cv2.line(frame, (int(h_vis_izq[0]), int(h_vis_izq[1])), (int(h_vis_der[0]), int(h_vis_der[1])), (0, 235, 255), 3)
                    cv2.circle(frame, (int(torso_x), int(torso_y)), 8, (0, 255, 160), -1)

                    for pt, c_pt in [(m_vis_izq, conf_m_izq), (m_vis_der, conf_m_der)]:
                        if c_pt > 0.22:
                            col_p = (0, 180, 255) if es_manos_juntas else ((0, 80, 255) if (es_manos_arriba or golpe_izq or golpe_der) else (255, 180, 0))
                            cv2.circle(frame, (int(pt[0]), int(pt[1])), 9, col_p, -1)

                    if es_manos_juntas:
                        txt_g, col_g = "MANOS JUNTAS -> DEFENSA!", (0, 180, 255)
                    elif es_manos_arriba:
                        txt_g, col_g = "MANOS ARRIBA -> GANCHO / PODER!", (0, 245, 212)
                    elif golpe_izq or golpe_der:
                        txt_g, col_g = "GOLPE DIRECTO!", (0, 90, 255)
                    elif es_agachado:
                        txt_g, col_g = "AGACHADO -> ESQUIVA / FRENO", (255, 190, 0)
                    else:
                        txt_g, col_g = "GUARDIA LISTA // MUEVETE IZQ/DER", (0, 255, 150)

                    cv2.putText(frame, txt_g, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.58, col_g, 2)

                    datos = {
                        "nx": torso_nx,
                        "ny": torso_ny,
                        "angulo_cuerpo": giro_cuerpo,
                        "accion": es_manos_arriba,
                        "manos_juntas": es_manos_juntas,
                        "golpe_izq": golpe_izq,
                        "golpe_der": golpe_der,
                        "brazos_abiertos": es_brazos_abiertos,
                        "agachado": es_agachado,
                        "defensa": bool(es_agachado or es_manos_juntas or defensa_dataset),
                        "izq_nx": max(0.0, min(1.0, m_vis_izq[0] / w)),
                        "izq_ny": max(0.0, min(1.0, m_vis_izq[1] / h)),
                        "der_nx": max(0.0, min(1.0, m_vis_der[0] / w)),
                        "der_ny": max(0.0, min(1.0, m_vis_der[1] / h)),
                    }

        if self.visor_ui is not None:
            self.visor_ui.actualizar(frame)

        return frame, datos

    def recalibrar_postura(self):
        self.ny_neutro = None
        self.muestras_calibracion.clear()

    def leer_manos_duales(self):
        frame, d = self._procesar_hibrido()
        if not d:
            return frame, []
        izq = {"lado": "izq", "nx": d["izq_nx"], "ny": d["izq_ny"], "accion": d["accion"], "defensa": d["defensa"]}
        der = {"lado": "der", "nx": d["der_nx"], "ny": d["der_ny"], "accion": d["accion"], "defensa": d["defensa"]}
        return frame, [izq, der]

    def leer(self, titulo="Ultralytics Dataset"):
        _, d = self._procesar_hibrido()
        if d:
            return {"detectada": True, "x": d["nx"] * self.ancho_pant, "y": d["ny"] * self.alto_pant, "cerrada": d["accion"], "pinza": d["accion"]}
        return {"detectada": False, "x": self.ancho_pant / 2, "y": self.alto_pant / 2, "cerrada": False, "pinza": False}

    def leer_volante(self, titulo="Ultralytics Volante"):
        _, d = self._procesar_hibrido()
        res = {
            "manos": 0,
            "angulo": 0.0,
            "altura": 0.5,
            "disparar": False,
            "escudo": False,
            "manos_juntas": False,
            "golpe_izq": False,
            "golpe_der": False,
            "brazos_abiertos": False,
            "agachado": False
        }
        if d:
            res["manos"] = 2
            res["angulo"] = max(-55.0, min(55.0, d["angulo_cuerpo"]))
            res["altura"] = d["ny"]
            res["disparar"] = d["accion"]
            res["escudo"] = d["defensa"]
            res["manos_juntas"] = d["manos_juntas"]
            res["golpe_izq"] = d["golpe_izq"]
            res["golpe_der"] = d["golpe_der"]
            res["brazos_abiertos"] = d["brazos_abiertos"]
            res["agachado"] = d["agachado"]
        return res

    def cerrar(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()