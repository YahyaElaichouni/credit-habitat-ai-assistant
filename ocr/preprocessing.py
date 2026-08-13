"""
===========================================================
Image Preprocessing
Projet PFE Crédit Agricole du Maroc
===========================================================
"""

import cv2
import numpy as np


class ImagePreprocessor:

    def __init__(self):
        pass

    # ======================================================
    # Niveaux de gris
    # ======================================================

    def to_grayscale(self, image):

        if len(image.shape) == 3:
            return cv2.cvtColor(
                image,
                cv2.COLOR_RGB2GRAY
            )

        return image


    # ======================================================
    # Débruitage
    # ======================================================

    def denoise(self, image):

        return cv2.fastNlMeansDenoising(
            image,
            None,
            h=12,
            templateWindowSize=7,
            searchWindowSize=21
        )


    # ======================================================
    # Amélioration du contraste
    # ======================================================

    def enhance_contrast(self, image):

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8,8)
        )

        return clahe.apply(image)


    # ======================================================
    # Binarisation
    # ======================================================

    def threshold(self, image):

        return cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]


    # ======================================================
    # Redimensionnement
    # ======================================================

    def resize(self, image, scale=2):

        return cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )


    # ======================================================
    # Pipeline complet
    # ======================================================

    def preprocess(self, image):

        image = self.to_grayscale(image)

        image = self.denoise(image)

        image = self.enhance_contrast(image)

        image = self.threshold(image)

        image = self.resize(image)

        return image