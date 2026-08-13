"""
===========================================================
OCR Agent
Projet PFE Crédit Agricole du Maroc
===========================================================

Couche fine au-dessus d'OCREngine : ce fichier ne réimplémente pas
le chargement PDF / prétraitement / appel OCR (déjà fait dans
OCREngine.pdf_to_text), il se contente de l'orchestrer au niveau
agent et de logger.
"""

import logging

from ocr.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


class OCRAgent:

    def __init__(self):
        self.ocr = OCREngine()

    def execute(self, pdf_path: str) -> str:
        """Retourne le texte OCR complet d'un PDF (toutes pages
        concaténées)."""

        logger.info("[OCRAgent] Lecture OCR : %s", pdf_path)

        text = self.ocr.pdf_to_text(pdf_path)

        logger.info(
            "[OCRAgent] OCR terminé (%d caractères).", len(text)
        )

        return text