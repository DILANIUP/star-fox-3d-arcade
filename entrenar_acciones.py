import os
from ultralytics import YOLO

ARCHIVO_ORIGINAL = "human-action-detection.ndjson"
ARCHIVO_RAPIDO   = "dataset_rapido.ndjson"
MAX_IMAGENES     = 1500  # Puedes subir este número si tienes GPU NVIDIA dedicada

if not os.path.exists(ARCHIVO_ORIGINAL):
    raise FileNotFoundError(f"No se encuentra {ARCHIVO_ORIGINAL} en esta carpeta.")

# 1. Extraer la cabecera (configuración/clases) + las primeras N imágenes para entrenamiento rápido
with open(ARCHIVO_ORIGINAL, "r", encoding="utf-8") as f_in, open(ARCHIVO_RAPIDO, "w", encoding="utf-8") as f_out:
    for i, linea in enumerate(f_in):
        if i <= MAX_IMAGENES:
            f_out.write(linea)
        else:
            break

print(f"[1/2] Subconjunto creado: {ARCHIVO_RAPIDO} ({MAX_IMAGENES} muestras)")

# 2. Entrenar modelo ligero YOLO11n (Ultralytics descarga las imágenes automáticamente)
print("[2/2] Iniciando descarga de imágenes y entrenamiento YOLO11n...")
model = YOLO("yolo11n.pt")
model.train(
    data=ARCHIVO_RAPIDO,
    epochs=15,
    imgsz=416,
    batch=16,
    project="runs_acciones",
    name="modelo_human_action"
)

print("\n[EXITO] Modelo guardado en: runs_acciones\\modelo_human_action\\weights\\best.pt")