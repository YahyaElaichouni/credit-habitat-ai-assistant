"""
===========================================================
Interface de test — Pipeline 1 (extraction documentaire)
Projet PFE Crédit Agricole du Maroc
===========================================================

Interface de démonstration/développement pour tester upload ->
contrôle -> OCR -> extraction -> validation en conditions réelles.
Ne remplace pas l'interface finale du parcours client, mais permet
de vérifier concrètement chaque étape du pipeline 1.
"""

import json
import logging
import uuid
from pathlib import Path

import streamlit as st

from config.settings import settings
from database import audit
from extraction.schema import DOCUMENT_SCHEMAS
from workflows.document_workflow import workflow

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Test extraction — Crédit Habitat",
    page_icon="📄",
    layout="wide",
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# ETAT DE SESSION
# =========================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "confirmed_fields" not in st.session_state:
    # {field_name: valeur confirmée}, remis à zéro à chaque nouvelle extraction
    st.session_state.confirmed_fields = {}

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# =========================================================
# BARRE LATERALE
# =========================================================

with st.sidebar:
    st.subheader("Session")

    advisor_id = st.text_input("Identifiant conseiller", value="conseiller_test")

    st.caption(f"session_id : `{st.session_state.session_id[:8]}...`")

    st.divider()

    st.subheader("Seuils actifs")
    st.caption(f"Confiance minimale : {settings.confidence_threshold}")
    st.caption(f"Écart maximal toléré : {settings.discrepancy_threshold:.0%}")
    st.caption(f"Taille max fichier : {settings.max_file_size_mb} Mo")


# =========================================================
# FORMULAIRE D'ENTREE
# =========================================================

st.title("📄 Test du pipeline d'extraction")

col_upload, col_declared = st.columns([1, 1])

with col_upload:

    document_type = st.selectbox(
        "Type de document",
        options=list(DOCUMENT_SCHEMAS.keys()),
    )

    uploaded_file = st.file_uploader(
        "Déposer un document",
        type=[ext.lstrip(".") for ext in settings.allowed_extensions],
    )

with col_declared:

    declared_json = st.text_area(
        "Valeurs déclarées par le client (JSON, optionnel — "
        "pour tester la détection d'écart EB-108)",
        value='{\n  "salaire_net": 6000\n}',
        height=150,
    )

run_button = st.button("Lancer l'extraction", type="primary")


# =========================================================
# EXECUTION DU PIPELINE
# =========================================================

if run_button:

    if uploaded_file is None:
        st.error("Déposez un document avant de lancer l'extraction.")
        st.stop()

    try:
        declared_data = json.loads(declared_json) if declared_json.strip() else {}
    except json.JSONDecodeError as e:
        st.error(f"JSON invalide dans les valeurs déclarées : {e}")
        st.stop()

    # Sauvegarde du fichier uploadé sur disque : le pipeline attend
    # un chemin de fichier réel (OCR, contrôle de taille/type), pas
    # des bytes en mémoire.
    saved_path = UPLOAD_DIR / f"{uuid.uuid4()}_{uploaded_file.name}"
    saved_path.write_bytes(uploaded_file.getvalue())

    with st.spinner("Contrôle, OCR, extraction et validation en cours..."):
        result = workflow.invoke({
            "pdf_path": str(saved_path),
            "document_type": document_type,
            "declared_data": declared_data,
            "advisor_id": advisor_id,
            "session_id": st.session_state.session_id,
        })

    st.session_state.last_result = result
    st.session_state.last_saved_path = str(saved_path)
    st.session_state.last_document_type = document_type
    st.session_state.confirmed_fields = {}


# =========================================================
# AFFICHAGE DU RESULTAT
# =========================================================

result = st.session_state.last_result

if result is not None:

    st.divider()

    control_result = result.get("control_result", {})

    if not control_result.get("valid", False):
        st.error(f"❌ Document rejeté au contrôle : {control_result.get('reason')}")

    else:
        security = result.get("extraction_security", {})
        if security.get("suspicious"):
            st.warning(
                "⚠️ Motifs suspects détectés dans le document "
                f"(revue prioritaire recommandée) : "
                f"{', '.join(security.get('matched_patterns', []))}"
            )

        with st.expander("Texte OCR brut"):
            st.text(result.get("ocr_text", ""))

        validation_result = result.get("validation_result")

        if validation_result:

            if validation_result["needs_priority_review"]:
                st.warning("🟠 Ce document nécessite une revue prioritaire.")
            else:
                st.success("🟢 Aucun point d'attention détecté.")

            st.subheader("Champs extraits")

            for field_name, decision in validation_result["fields"].items():

                already_confirmed = field_name in st.session_state.confirmed_fields

                status = decision["status"]
                value = decision["value"]
                confidence = decision["confidence"]
                reasons = decision["reasons"]

                icon = {
                    "pre_rempli": "🟢",
                    "signale": "🟠",
                    "absent": "⚪",
                }[status]

                col_field, col_value, col_action = st.columns([1, 2, 1])

                with col_field:
                    st.markdown(f"{icon} **{field_name}**")
                    if confidence is not None:
                        st.caption(f"confiance : {confidence:.2f}")

                with col_value:
                    edited_value = st.text_input(
                        f"Valeur — {field_name}",
                        value=str(value) if value is not None else "",
                        key=f"input_{field_name}",
                        label_visibility="collapsed",
                        disabled=already_confirmed,
                        placeholder="Non extrait — à saisir manuellement",
                    )
                    for reason in reasons:
                        st.caption(f"⚠️ {reason}")

                with col_action:
                    if already_confirmed:
                        st.caption("✅ Confirmé")
                    else:
                        button_label = (
                            "Confirmer"
                            if edited_value == (str(value) if value is not None else "")
                            else "Enregistrer la correction"
                        )
                        if st.button(button_label, key=f"confirm_{field_name}"):
                            final_value = edited_value if edited_value != "" else None
                            audit.log_human_confirmation(
                                document_path=st.session_state.get(
                                    "last_saved_path", ""
                                ),
                                document_type=st.session_state.get(
                                    "last_document_type", document_type
                                ),
                                field_name=field_name,
                                confirmed_value=final_value,
                                advisor_id=advisor_id,
                                session_id=st.session_state.session_id,
                                original_value=value,
                            )
                            st.session_state.confirmed_fields[field_name] = final_value
                            st.rerun()

            st.divider()

            with st.expander("Détail moteur de règles (plausibilité)"):
                st.json(validation_result["rule_engine"])

            with st.expander("Détail écarts déclaratif / extrait"):
                st.json(validation_result["discrepancies"])