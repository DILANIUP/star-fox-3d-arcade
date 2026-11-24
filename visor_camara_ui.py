import cv2
import numpy as np
from ursina import Entity, Texture, camera, color
from panda3d.core import Texture as P3DTexture

class VisorCamaraIntegrado:
    def __init__(self, ancho=240, alto=180, pos=(-0.71, 0.37)):
        self.ancho = ancho
        self.alto = alto

        # Crear textura dinámica de Panda3D en formato RGB
        self.p3d_tex = P3DTexture("camara_pip")
        self.p3d_tex.setup2dTexture(ancho, alto, P3DTexture.T_unsigned_byte, P3DTexture.F_rgb)
        self.ursina_tex = Texture(self.p3d_tex)

        # Marco decorativo + Pantalla de video dentro de la UI de Ursina
        self.marco = Entity(
            parent=camera.ui,
            model='quad',
            scale=(0.31, 0.24),
            position=pos,
            color=color.rgba32(0, 215, 255, 220),
            z=0.1
        )
        self.pantalla = Entity(
            parent=camera.ui,
            model='quad',
            texture=self.ursina_tex,
            scale=(0.295, 0.225),
            position=pos,
            z=0.0
        )

    def actualizar(self, frame_bgr):
        if frame_bgr is None:
            return
        # Redimensionar y voltear verticalmente para coordenadas de textura OpenGL/Panda3D
        mini = cv2.resize(frame_bgr, (self.ancho, self.alto))
        mini = cv2.flip(mini, 0)
        self.p3d_tex.setRamImage(mini.tobytes())