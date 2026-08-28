"""

Assistant IA — Crédit Habitat
Projet PFE Crédit Agricole du Maroc
===================================

Interface de démonstration permettant de tester :

1. Analyse documentaire
   Contrôle -> OCR -> Extraction -> Validation

2. Assistant IA
   Question -> Retrieval -> Contrôle du périmètre -> Réponse sourcée

Tous les appels passent par Orchestrator afin de conserver
un point d'entrée unique cohérent avec l'architecture du projet.
"""

import json
import logging
import uuid
from pathlib import Path

import streamlit as st

from agents.orchestrator import Orchestrator
from config.settings import settings
from database import audit
from extraction.schema import DOCUMENT_SCHEMAS

# =========================================================

# CONFIGURATION

# =========================================================

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s",
datefmt="%H:%M:%S",
)

st.set_page_config(
page_title="Crédit Habitat — Assistant IA",
page_icon="🏦",
layout="wide",
)

# =========================================================

# DESIGN

# =========================================================

st.markdown("""
<style>

    /* =====================================================
       GLOBAL
    ===================================================== */

    .stApp {
        background-color: #FFFFFF;
        color: #1E293B;
    }

    .main .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4 {
        color: #1E293B !important;
    }

    p, span, label {
        color: #475569;
    }


    /* =====================================================
       HEADER
    ===================================================== */

    .app-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding-bottom: 22px;
        margin-bottom: 25px;
        border-bottom: 1px solid #E2E8F0;
    }

    .brand-icon {
        width: 48px;
        height: 48px;
        background: #007A3D;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 700;
        color: #FFFFFF !important;
    }

    .brand-title {
        font-size: 16px;
        font-weight: 750;
        color: #006B35 !important;
        letter-spacing: .2px;
    }

    .brand-subtitle {
        font-size: 13px;
        color: #64748B !important;
        margin-top: 3px;
    }


    /* =====================================================
       SIDEBAR
    ===================================================== */

    section[data-testid="stSidebar"] {
        background-color: #F8FAF9 !important;
        border-right: 1px solid #E2E8F0;
    }

    section[data-testid="stSidebar"] * {
        color: #334155;
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #006B35 !important;
    }


    /* =====================================================
       BOUTONS
    ===================================================== */

    .stButton > button {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #D7E0DA !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        min-height: 42px;
    }

    .stButton > button:hover {
        border-color: #007A3D !important;
        color: #007A3D !important;
    }

    /* Boutons primary */
    .stButton > button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background-color: #007A3D !important;
        border-color: #007A3D !important;
        color: #FFFFFF !important;
    }

    .stButton > button[kind="primary"] *,
    button[data-testid="baseButton-primary"] * {
        color: #FFFFFF !important;
    }

    .stButton > button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background-color: #006630 !important;
        border-color: #006630 !important;
        color: #FFFFFF !important;
    }


    /* =====================================================
       CARTES ACCUEIL
    ===================================================== */

    .home-card {
        border: 1px solid #DCE5E0;
        border-radius: 14px;
        padding: 28px;
        background-color: #FFFFFF !important;
        min-height: 220px;
    }

    .home-card:hover {
        border-color: #007A3D;
    }

    .card-icon {
        font-size: 30px;
        margin-bottom: 15px;
    }

    .card-title {
        font-size: 20px;
        font-weight: 700;
        color: #1E293B !important;
        margin-bottom: 8px;
    }

    .card-description {
        font-size: 14px;
        color: #64748B !important;
        line-height: 1.6;
    }


    /* =====================================================
       STATUS
    ===================================================== */

    .status {
        display: inline-block;
        padding: 6px 11px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    .status-success {
        background-color: #E8F5EC !important;
        color: #08752F !important;
    }

    .status-warning {
        background-color: #FFF4D8 !important;
        color: #8A6200 !important;
    }

    .status-neutral {
        background-color: #F1F5F3 !important;
        color: #475569 !important;
    }


    /* =====================================================
       WORKFLOW
    ===================================================== */

    .workflow-step {
        border: 1px solid #DCE5E0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        background-color: #FFFFFF !important;
        color: #334155 !important;
        font-size: 13px;
        font-weight: 600;
    }

    .workflow-step * {
        color: #334155 !important;
    }

    .workflow-active {
        border-color: #007A3D !important;
        background-color: #F0F9F4 !important;
        color: #007A3D !important;
    }


    /* =====================================================
       METRICS
    ===================================================== */

    .metric-card {
        border: 1px solid #E1E6E3;
        border-radius: 10px;
        padding: 16px;
        background-color: #FFFFFF !important;
    }

    .metric-label {
        font-size: 12px;
        text-transform: uppercase;
        color: #64748B !important;
        font-weight: 650;
    }

    .metric-value {
        font-size: 26px;
        color: #1E293B !important;
        font-weight: 700;
        margin-top: 5px;
    }


    /* =====================================================
       INPUTS
    ===================================================== */

    .stTextInput input,
    .stTextArea textarea {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #007A3D !important;
        box-shadow: 0 0 0 1px #007A3D !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #94A3B8 !important;
    }


    /* =====================================================
       FILE UPLOADER
    ===================================================== */

    [data-testid="stFileUploader"] {
        border: 1px dashed #9FC9AF;
        border-radius: 10px;
        background-color: #FAFCFB !important;
        padding: 8px;
    }


    /* =====================================================
       EXPANDER
    ===================================================== */

    [data-testid="stExpander"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px;
        background-color: #FFFFFF !important;
    }

    [data-testid="stExpander"] * {
        color: #334155;
    }


    /* =====================================================
       DIVIDERS
    ===================================================== */

    hr {
        border-color: #E2E8F0 !important;
    }

</style>
""", unsafe_allow_html=True)

# =========================================================

# HEADER

# =========================================================

st.markdown("""

<div class="app-header">
    <div class="brand-icon">CA</div>
    <div>
        <div class="brand-title">CRÉDIT AGRICOLE DU MAROC</div>
        <div class="brand-subtitle">
            Assistant IA — Crédit Habitat
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================

# INITIALISATION

# =========================================================

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

orchestrator = Orchestrator()

# =========================================================

# SESSION STATE

# =========================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "confirmed_fields" not in st.session_state:
    st.session_state.confirmed_fields = {}

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "page" not in st.session_state:
    st.session_state.page = "Accueil"

# =========================================================

# SIDEBAR

# =========================================================

with st.sidebar:

    st.subheader("Espace conseiller")

    advisor_id = st.text_input(
        "Identifiant conseiller",
        value="conseiller_test",
    )

    st.caption(
        f"Session : {st.session_state.session_id[:8]}..."
    )

    st.divider()

    st.subheader("Navigation")

    if st.button(
        "⌂ Accueil",
        use_container_width=True,
    ):
        st.session_state.page = "Accueil"
        st.rerun()

    if st.button(
        "Analyse documentaire",
        use_container_width=True,
    ):
        st.session_state.page = "Extraction"
        st.rerun()

    if st.button(
        "Assistant IA",
        use_container_width=True,
    ):
        st.session_state.page = "Assistant"
        st.rerun()

    st.divider()

    st.subheader("Système")

    st.markdown(
        '<span class="status status-success">'
        '● Orchestrateur disponible'
        '</span>',
        unsafe_allow_html=True,
    )

    st.write("")

    st.markdown(
        '<span class="status status-success">'
        '● Pipeline extraction'
        '</span>',
        unsafe_allow_html=True,
    )

    st.write("")

    st.markdown(
        '<span class="status status-success">'
        '● Audit actif'
        '</span>',
        unsafe_allow_html=True,
    )

    st.divider()

    with st.expander("Paramètres techniques"):

        st.caption(
            f"Confiance minimale : "
            f"{settings.confidence_threshold}"
        )

        st.caption(
            f"Écart maximal : "
            f"{settings.discrepancy_threshold:.0%}"
        )

        st.caption(
            f"Taille max : "
            f"{settings.max_file_size_mb} Mo"
        )

        st.caption(
            f"Similarité RAG : "
            f"{settings.rag_similarity_threshold}"
        )

# =========================================================

# PAGE ACCUEIL

# =========================================================

if st.session_state.page == "Accueil":

    st.title("Bonjour, conseiller")

    st.caption(
        "Choisissez une fonctionnalité pour commencer."
    )

    st.write("")

    col_extract, col_chat = st.columns(2, gap="large")

    with col_extract:

        st.markdown("""
        <div class="home-card">
            <div class="card-icon">📄</div>
            <div class="card-title">
                Analyse documentaire
            </div>
            <div class="card-description">
                Analysez un document automatiquement grâce
                au contrôle, à l'OCR, à l'extraction des
                données et à la validation.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "Commencer l'analyse",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.page = "Extraction"
            st.rerun()

    with col_chat:

        st.markdown("""
        <div class="home-card">
            <div class="card-icon">💬</div>
            <div class="card-title">
                Assistant Crédit Habitat
            </div>
            <div class="card-description">
                Interrogez la documentation officielle et
                obtenez des réponses contextualisées et
                sourcées.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "Ouvrir l'assistant",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.page = "Assistant"
            st.rerun()

    st.write("")
    st.divider()

    st.subheader("Fonctionnement")

    step_1, step_2, step_3, step_4 = st.columns(4)

    with step_1:
        st.markdown("""
        <div class="workflow-step">
            01<br>Contrôle
        </div>
        """, unsafe_allow_html=True)

    with step_2:
        st.markdown("""
        <div class="workflow-step">
            02<br>OCR
        </div>
        """, unsafe_allow_html=True)

    with step_3:
        st.markdown("""
        <div class="workflow-step">
            03<br>Extraction
        </div>
        """, unsafe_allow_html=True)

    with step_4:
        st.markdown("""
        <div class="workflow-step">
            04<br>Validation
        </div>
        """, unsafe_allow_html=True)

# =========================================================

# PAGE EXTRACTION

# =========================================================

elif st.session_state.page == "Extraction":

    st.title("Analyse documentaire")

    st.caption(
        "Déposez un document pour lancer son analyse."
    )

    step_1, step_2, step_3, step_4 = st.columns(4)

    for column, number, label in [
        (step_1, "01", "Contrôle"),
        (step_2, "02", "OCR"),
        (step_3, "03", "Extraction"),
        (step_4, "04", "Validation"),
    ]:

        with column:

            st.markdown(
                f"""
                <div class="workflow-step">
                    {number}<br>{label}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    st.divider()

    col_upload, col_data = st.columns(
        [1.1, 0.9],
        gap="large",
    )

    with col_upload:

        st.subheader("Document")

        document_type = st.selectbox(
            "Type de document",
            options=list(DOCUMENT_SCHEMAS.keys()),
        )

        uploaded_file = st.file_uploader(
            "Déposer un document",
            type=[
                ext.lstrip(".")
                for ext in settings.allowed_extensions
            ],
        )

        if uploaded_file is not None:

            st.success(
                f"Document sélectionné : "
                f"{uploaded_file.name}"
            )

    with col_data:

        st.subheader("Informations déclarées")

        declared_json = st.text_area(
            "Valeurs déclarées par le client",
            value='{\n  "salaire_net": 6000\n}',
            height=180,
            help=(
                "Ces données permettent de détecter les "
                "écarts avec les informations extraites."
            ),
        )

    run_button = st.button(
        "Lancer l'analyse",
        type="primary",
        use_container_width=True,
    )


    # -----------------------------------------------------
    # EXECUTION
    # -----------------------------------------------------

    if run_button:

        if uploaded_file is None:

            st.error(
                "Déposez un document avant de lancer l'analyse."
            )

            st.stop()

        try:

            declared_data = (
                json.loads(declared_json)
                if declared_json.strip()
                else {}
            )

        except json.JSONDecodeError as e:

            st.error(
                f"JSON invalide : {e}"
            )

            st.stop()

        saved_path = (
            UPLOAD_DIR
            / f"{uuid.uuid4()}_{uploaded_file.name}"
        )

        saved_path.write_bytes(
            uploaded_file.getvalue()
        )

        progress = st.progress(0)
        status = st.empty()

        status.write("1/4 — Contrôle du document")
        progress.progress(15)

        status.write("2/4 — OCR et lecture du document")
        progress.progress(35)

        with st.spinner(
            "Analyse en cours..."
        ):

            result = orchestrator.handle_document(
                pdf_path=str(saved_path),
                document_type=document_type,
                advisor_id=advisor_id,
                session_id=st.session_state.session_id,
                declared_data=declared_data,
            )

        status.write("3/4 — Extraction des informations")
        progress.progress(75)

        status.write("4/4 — Validation des résultats")
        progress.progress(100)

        status.success("Analyse terminée.")

        st.session_state.last_result = result
        st.session_state.last_saved_path = str(saved_path)
        st.session_state.last_document_type = document_type
        st.session_state.confirmed_fields = {}


    # -----------------------------------------------------
    # RESULTATS
    # -----------------------------------------------------

    result = st.session_state.last_result

    if result is not None:

        st.divider()

        st.subheader("Résultat de l'analyse")

        control_result = result.get(
            "control_result",
            {},
        )

        if not control_result.get("valid", False):

            st.error(
                "Document rejeté : "
                f"{control_result.get('reason')}"
            )

        else:

            security = result.get(
                "extraction_security",
                {},
            )

            if security.get("suspicious"):

                st.warning(
                    "Motifs nécessitant une attention : "
                    f"{', '.join(security.get('matched_patterns', []))}"
                )

            validation_result = result.get(
                "validation_result"
            )

            if validation_result:

                fields = validation_result["fields"]

                total = len(fields)

                reliable = sum(
                    1
                    for field in fields.values()
                    if field["status"] == "pre_rempli"
                )

                review = sum(
                    1
                    for field in fields.values()
                    if field["status"] == "signale"
                )

                absent = sum(
                    1
                    for field in fields.values()
                    if field["status"] == "absent"
                )

                col_1, col_2, col_3, col_4 = st.columns(4)

                metrics = [
                    (col_1, "Champs détectés", total),
                    (col_2, "Fiables", reliable),
                    (col_3, "À vérifier", review),
                    (col_4, "Absents", absent),
                ]

                for column, label, value in metrics:

                    with column:

                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <div class="metric-label">
                                    {label}
                                </div>
                                <div class="metric-value">
                                    {value}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                st.write("")

                if validation_result[
                    "needs_priority_review"
                ]:

                    st.warning(
                        "Une revue prioritaire est recommandée."
                    )

                else:

                    st.success(
                        "Aucun point critique détecté."
                    )

                st.subheader("Informations extraites")

                for field_name, decision in fields.items():

                    already_confirmed = (
                        field_name
                        in st.session_state.confirmed_fields
                    )

                    status = decision["status"]
                    value = decision["value"]
                    confidence = decision["confidence"]
                    reasons = decision["reasons"]

                    icon = {
                        "pre_rempli": "🟢",
                        "signale": "🟠",
                        "absent": "⚪",
                    }[status]

                    col_field, col_value, col_action = (
                        st.columns([1.2, 2, 1])
                    )

                    with col_field:

                        st.markdown(
                            f"{icon} **{field_name}**"
                        )

                        if confidence is not None:

                            st.progress(
                                min(max(float(confidence), 0), 1),
                            )

                            st.caption(
                                f"Confiance : "
                                f"{confidence:.0%}"
                            )

                    with col_value:

                        edited_value = st.text_input(
                            f"Valeur — {field_name}",
                            value=(
                                str(value)
                                if value is not None
                                else ""
                            ),
                            key=f"input_{field_name}",
                            label_visibility="collapsed",
                            disabled=already_confirmed,
                            placeholder=(
                                "Non extrait — "
                                "saisie manuelle"
                            ),
                        )

                        for reason in reasons:

                            st.caption(
                                f"⚠️ {reason}"
                            )

                    with col_action:

                        if already_confirmed:

                            st.markdown(
                                '<span class="status status-success">'
                                '✓ Confirmé'
                                '</span>',
                                unsafe_allow_html=True,
                            )

                        else:

                            button_label = (
                                "Confirmer"
                                if edited_value == (
                                    str(value)
                                    if value is not None
                                    else ""
                                )
                                else
                                "Enregistrer"
                            )

                            if st.button(
                                button_label,
                                key=f"confirm_{field_name}",
                                use_container_width=True,
                            ):

                                final_value = (
                                    edited_value
                                    if edited_value != ""
                                    else None
                                )

                                audit.log_human_confirmation(
                                    document_path=(
                                        st.session_state.get(
                                            "last_saved_path",
                                            "",
                                        )
                                    ),
                                    document_type=(
                                        st.session_state.get(
                                            "last_document_type",
                                            document_type,
                                        )
                                    ),
                                    field_name=field_name,
                                    confirmed_value=final_value,
                                    advisor_id=advisor_id,
                                    session_id=(
                                        st.session_state.session_id
                                    ),
                                    original_value=value,
                                )

                                st.session_state.confirmed_fields[
                                    field_name
                                ] = final_value

                                st.rerun()

                st.divider()

                with st.expander("Voir le texte OCR"):

                    st.text(
                        result.get("ocr_text", "")
                    )

                with st.expander(
                    "Détail du moteur de règles"
                ):

                    st.json(
                        validation_result[
                            "rule_engine"
                        ]
                    )

                with st.expander(
                    "Détail des écarts"
                ):

                    st.json(
                        validation_result[
                            "discrepancies"
                        ]
                    )

# =========================================================

# PAGE ASSISTANT

# =========================================================

elif st.session_state.page == "Assistant":

    st.title("Assistant Crédit Habitat")

    st.caption(
        "Posez une question sur les documents officiels "
        "indexés dans la base documentaire."
    )

    if st.button("Nouvelle conversation"):

        st.session_state.chat_history = []
        st.rerun()

    st.divider()


    # -----------------------------------------------------
    # QUESTIONS RAPIDES
    # -----------------------------------------------------

    st.caption("Questions rapides")

    quick_1, quick_2, quick_3 = st.columns(3)

    quick_question = None

    with quick_1:

        if st.button(
            "Conditions d'éligibilité",
            use_container_width=True,
        ):

            quick_question = (
                "Quelles sont les conditions d'éligibilité "
                "au crédit habitat ?"
            )

    with quick_2:

        if st.button(
            "Documents nécessaires",
            use_container_width=True,
        ):

            quick_question = (
                "Quels documents sont nécessaires pour "
                "constituer un dossier de crédit habitat ?"
            )

    with quick_3:

        if st.button(
            "Taux du crédit",
            use_container_width=True,
        ):

            quick_question = (
                "Quel est le taux d'intérêt du crédit habitat ?"
            )


    # -----------------------------------------------------
    # HISTORIQUE
    # -----------------------------------------------------

    for exchange in st.session_state.chat_history:

        with st.chat_message("user"):

            st.write(exchange["question"])

        with st.chat_message("assistant"):

            if exchange["in_scope"]:

                st.markdown(
                    '<span class="status status-success">'
                    'Réponse documentée'
                    '</span>',
                    unsafe_allow_html=True,
                )

                st.write(exchange["answer"])

                if exchange["sources"]:

                    with st.expander("Sources utilisées"):

                        for source in exchange["sources"]:

                            st.write(f"• {source}")

            else:

                st.markdown(
                    '<span class="status status-warning">'
                    'Question hors périmètre'
                    '</span>',
                    unsafe_allow_html=True,
                )

                st.warning(exchange["answer"])


    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------

    question = st.chat_input(
        "Posez votre question..."
    )

    if quick_question:

        question = quick_question


    # -----------------------------------------------------
    # EXECUTION
    # -----------------------------------------------------

    if question:

        with st.chat_message("user"):

            st.write(question)

        with st.chat_message("assistant"):

            with st.spinner(
                "Recherche dans la documentation..."
            ):

                try:

                    chat_result = (
                        orchestrator.handle_question(
                            question=question,
                            advisor_id=advisor_id,
                            session_id=(
                                st.session_state.session_id
                            ),
                        )
                    )

                except FileNotFoundError:

                    st.error(
                        "Le vectorstore RAG n'existe pas encore. "
                        "Lancez `python -m rag.ingest` après avoir "
                        "ajouté les documents dans `data/docs/`."
                    )

                    st.stop()

            if chat_result["in_scope"]:

                st.markdown(
                    '<span class="status status-success">'
                    'Réponse documentée'
                    '</span>',
                    unsafe_allow_html=True,
                )

                st.write(
                    chat_result["answer"]
                )

                if chat_result["sources"]:

                    with st.expander(
                        "Sources utilisées"
                    ):

                        for source in chat_result["sources"]:

                            st.write(
                                f"• {source}"
                            )

            else:

                st.markdown(
                    '<span class="status status-warning">'
                    'Question hors périmètre'
                    '</span>',
                    unsafe_allow_html=True,
                )

                st.warning(
                    chat_result["answer"]
                )

        st.session_state.chat_history.append(
            {
                "question": question,
                "answer": chat_result["answer"],
                "in_scope": chat_result["in_scope"],
                "sources": chat_result["sources"],
            }
        )
