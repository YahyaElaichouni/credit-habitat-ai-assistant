"""
===========================================================
OCR Engine - PaddleOCR
Projet PFE Crédit Agricole du Maroc
===========================================================

NOTE IMPORTANTE : écrit pour l'API PaddleOCR 3.x (.predict(),
résultat sous forme de dict avec les clés "rec_texts"/"rec_scores").
Si `check_paddleocr_version.py` montre un format différent chez vous,
adaptez la méthode `image_to_text()` en conséquence.
"""

import logging

from paddleocr import PaddleOCR

from ocr.pdf_loader import PDFLoader
from ocr.preprocessing import ImagePreprocessor

logger = logging.getLogger(__name__)


class OCREngine:

    def __init__(self):

        logger.info("Chargement de PaddleOCR...")

        self.reader = PaddleOCR(
            lang="fr",
            use_textline_orientation=True,
        )

        self.loader = PDFLoader()

        self.preprocessor = ImagePreprocessor()

        logger.info("PaddleOCR prêt.")

    # =====================================================
    # OCR sur une image
    # =====================================================

    def image_to_text(self, image):
        """Prétraite l'image puis lance l'OCR.

        Retourne une liste de dicts {text, confidence, bbox},
        indépendamment du format de retour interne de PaddleOCR
        (isolé ici pour que le reste du code n'en dépende pas).
        """

        processed = self.preprocessor.preprocess(image)

        raw_result = self.reader.predict(processed)

        if not raw_result:
            return []

        page_result = raw_result[0]

        texts = page_result.get("rec_texts", [])
        scores = page_result.get("rec_scores", [])
        polys = page_result.get(
            "dt_polys",
            page_result.get("rec_polys", [None] * len(texts))
        )

        lines = []
        for text, score, box in zip(texts, scores, polys):
            lines.append({
                "text": text,
                "confidence": float(score),
                "bbox": box,
            })

        return lines

    # =====================================================
    # PDF -> Texte
    # =====================================================

    def pdf_to_text(self, pdf_path):

        pages = self.loader.load(pdf_path)

        full_text = ""

        for i, image in enumerate(pages):

            logger.info("Lecture page %d", i + 1)

            lines = self.image_to_text(image)

            for line in lines:
                full_text += line["text"] + "\n"

            full_text += "\n"

        return full_text

    # =====================================================
    # PDF -> JSON
    # =====================================================

    def pdf_to_json(self, pdf_path):

        pages = self.loader.load(pdf_path)

        document = []

        for page_number, image in enumerate(pages):

            lines = self.image_to_text(image)

            for line in lines:
                document.append({
                    "page": page_number + 1,
                    "text": line["text"],
                    "confidence": line["confidence"],
                    "bbox": line["bbox"],
                })

        return document