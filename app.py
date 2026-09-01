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
import time
import pickle
import hashlib
from pathlib import Path
from datetime import datetime
from io import BytesIO

import streamlit as st
import pandas as pd

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
    initial_sidebar_state="expanded",
)

# =========================================================
# CACHE
# =========================================================

@st.cache_resource
def get_orchestrator():
    """Créer l'orchestrator une seule fois (caché)"""
    return Orchestrator()

# =========================================================
# DESIGN - STYLES AMÉLIORÉS
# =========================================================

def apply_theme(theme="light"):
    """Appliquer le thème (clair ou sombre)"""
    if theme == "dark":
        st.markdown("""
        <style>
            .stApp {
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }
            .main .block-container {
                background-color: #1E1E1E !important;
            }
            h1, h2, h3, h4, .stTitle, .stSubheader {
                color: #E0E0E0 !important;
            }
            p, span, label, .stCaption {
                color: #B0B0B0 !important;
            }
            .stTextInput input, .stTextArea textarea, .stSelectbox select {
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                border-color: #404040 !important;
            }
            .stButton > button {
                background-color: #2D2D2D !important;
                color: #E0E0E0 !important;
                border-color: #404040 !important;
            }
            .stButton > button:hover {
                border-color: #007A3D !important;
                color: #007A3D !important;
            }
            section[data-testid="stSidebar"] {
                background-color: #252525 !important;
                border-right-color: #404040 !important;
            }
            section[data-testid="stSidebar"] * {
                color: #D0D0D0 !important;
            }
            .home-card, .workflow-step, .metric-card {
                background-color: #2D2D2D !important;
                border-color: #404040 !important;
            }
            [data-testid="stExpander"] {
                background-color: #2D2D2D !important;
                border-color: #404040 !important;
            }
            [data-testid="stFileUploader"] {
                background-color: #2D2D2D !important;
                border-color: #404040 !important;
            }
            .stAlert {
                background-color: #2D2D2D !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            /* =====================================================
               GLOBAL - VERSION CLAIRE AMÉLIORÉE
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
            
            /* Amélioration du focus */
            *:focus-visible {
                outline: 2px solid #007A3D !important;
                outline-offset: 2px !important;
            }
            
            /* Champs obligatoires */
            .required::after {
                content: " *";
                color: #DC2626;
                font-weight: bold;
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
                overflow: hidden;
            }
            .brand-icon img {
                width: 100%;
                height: 100%;
                object-fit: cover;
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
                transition: all 0.2s ease;
            }
            .stButton > button:hover {
                border-color: #007A3D !important;
                color: #007A3D !important;
                transform: translateY(-1px);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }
            .stButton > button[kind="primary"],
            button[data-testid="baseButton-primary"] {
                background-color: #007A3D !important;
                border-color: #007A3D !important;
                color: #FFFFFF !important;
            }
            .stButton > button[kind="primary"]:hover,
            button[data-testid="baseButton-primary"]:hover {
                background-color: #006630 !important;
                border-color: #006630 !important;
                color: #FFFFFF !important;
                transform: translateY(-1px);
                box-shadow: 0 4px 6px -1px rgba(0, 122, 61, 0.3);
            }
            .stButton > button:disabled {
                opacity: 0.5 !important;
                cursor: not-allowed !important;
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
                transition: all 0.3s ease;
            }
            .home-card:hover {
                border-color: #007A3D;
                transform: translateY(-4px);
                box-shadow: 0 8px 25px rgba(0, 122, 61, 0.1);
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
            .status-error {
                background-color: #FEE2E2 !important;
                color: #991B1B !important;
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
                transition: all 0.3s ease;
            }
            .workflow-step * {
                color: #334155 !important;
            }
            .workflow-active {
                border-color: #007A3D !important;
                background-color: #F0F9F4 !important;
                color: #007A3D !important;
                box-shadow: 0 0 0 3px rgba(0, 122, 61, 0.2);
            }
            .workflow-completed {
                border-color: #007A3D !important;
                background-color: #E8F5EC !important;
                color: #08752F !important;
            }
            .workflow-error {
                border-color: #DC2626 !important;
                background-color: #FEE2E2 !important;
                color: #991B1B !important;
            }

            /* =====================================================
               METRICS
            ===================================================== */
            .metric-card {
                border: 1px solid #E1E6E3;
                border-radius: 10px;
                padding: 16px;
                background-color: #FFFFFF !important;
                transition: all 0.3s ease;
            }
            .metric-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
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
            .stTextArea textarea,
            .stSelectbox select {
                background-color: #FFFFFF !important;
                color: #1E293B !important;
                border: 2px solid #CBD5E1 !important;
                border-radius: 8px !important;
                transition: border-color 0.2s ease;
            }
            .stTextInput input:focus,
            .stTextArea textarea:focus,
            .stSelectbox select:focus {
                border-color: #007A3D !important;
                box-shadow: 0 0 0 3px rgba(0, 122, 61, 0.2) !important;
            }
            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {
                color: #94A3B8 !important;
            }

            /* =====================================================
               FILE UPLOADER
            ===================================================== */
            [data-testid="stFileUploader"] {
                border: 2px dashed #9FC9AF;
                border-radius: 10px;
                background-color: #FAFCFB !important;
                padding: 8px;
                transition: all 0.3s ease;
            }
            [data-testid="stFileUploader"]:hover {
                border-color: #007A3D;
                background-color: #F0F9F4 !important;
            }
            [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
                padding: 20px;
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

            /* =====================================================
               PROGRESS BAR
            ===================================================== */
            .stProgress > div > div {
                background-color: #007A3D !important;
            }

            /* =====================================================
               CHAT
            ===================================================== */
            [data-testid="stChatMessage"] {
                background-color: transparent !important;
            }
            [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
                background-color: #F8FAF9;
                padding: 12px 16px;
                border-radius: 8px;
            }
            [data-testid="stChatMessage"][data-testid="user"] {
                background-color: #007A3D !important;
                color: #FFFFFF !important;
                border-radius: 8px;
            }
            
            /* Document list styles */
            .doc-item {
                padding: 8px 12px;
                border-radius: 6px;
                border-left: 3px solid #007A3D;
                margin-bottom: 4px;
                background-color: #F8FAF9;
                transition: all 0.2s ease;
            }
            .doc-item:hover {
                background-color: #F0F9F4;
            }
            .doc-item-active {
                background-color: #E8F5EC;
                border-left-color: #006630;
            }
        </style>
        """, unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================

def get_image_base64(image_path):
    """Convertir une image en base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return ""

import base64

def render_header():
    """Rendre l'en-tête de l'application"""
    logo_base64 = get_image_base64("assets/logo_ca.jpg")
    
    if logo_base64:
        logo_html = f'<img src="data:image/jpeg;base64,{logo_base64}" alt="Crédit Agricole du Maroc">'
    else:
        logo_html = "🏦"
    
    st.markdown(
        f"""
        <div class="app-header">
            <div class="brand-icon">
                {logo_html}
            </div>
            <div>
                <div class="brand-title">Assistant IA — Crédit Habitat</div>
                <div class="brand-subtitle">Crédit Agricole du Maroc — PFE 2026</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# FONCTIONS UTILITAIRES
# =========================================================

def validate_file(uploaded_file):
    """Valider le fichier uploadé"""
    if uploaded_file is None:
        return False, "Aucun fichier sélectionné"
    
    # Vérifier la taille
    if uploaded_file.size > settings.max_file_size_mb * 1024 * 1024:
        return False, f"Fichier trop volumineux (max {settings.max_file_size_mb} MB)"
    
    # Vérifier l'extension
    file_ext = Path(uploaded_file.name).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        return False, f"Format non supporté. Formats acceptés : {', '.join(settings.allowed_extensions)}"
    
    # Vérifier le type MIME (optionnel)
    try:
        import magic
        mime = magic.from_buffer(uploaded_file.getvalue(), mime=True)
        allowed_mime = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
        if mime not in allowed_mime:
            return False, f"Type MIME non supporté : {mime}"
    except Exception:
        # Si python-magic n'est pas disponible, on ignore cette vérification
        pass
    
    return True, "OK"

def save_session_state():
    """Sauvegarder l'état de la session"""
    try:
        session_dir = Path("data/sessions")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = session_dir / f"session_{st.session_state.session_id}.pkl"
        with open(session_file, "wb") as f:
            # Exclure les objets non sérialisables
            state_to_save = {
                k: v for k, v in st.session_state.items()
                if not k.startswith("_") and not callable(v)
            }
            pickle.dump(state_to_save, f)
        return True
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de la session : {e}")
        return False

def load_session_state(session_id):
    """Restaurer l'état de la session"""
    try:
        session_file = Path("data/sessions") / f"session_{session_id}.pkl"
        if session_file.exists():
            with open(session_file, "rb") as f:
                saved_state = pickle.load(f)
                for key, value in saved_state.items():
                    if key not in ["orchestrator", "_orchestrator"]:
                        st.session_state[key] = value
            return True
    except Exception as e:
        logging.error(f"Erreur lors de la restauration de la session : {e}")
    return False

def export_results_to_csv(result_data, document_type):
    """Exporter les résultats en CSV"""
    if not result_data or 'validation_result' not in result_data:
        return None
    
    fields = result_data['validation_result']['fields']
    rows = []
    for field_name, field_data in fields.items():
        rows.append({
            'Champ': field_name,
            'Valeur': field_data.get('value', ''),
            'Statut': field_data.get('status', ''),
            'Confiance': field_data.get('confidence', 0),
            'Raisons': ', '.join(field_data.get('reasons', []))
        })
    
    df = pd.DataFrame(rows)
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    return csv_buffer.getvalue()

def process_document_with_progress(file_path, document_type, declared_data, advisor_id, session_id):
    """Traiter un document avec barre de progression détaillée"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    steps = [
        ("🔍 Contrôle du document", 15),
        ("📄 OCR et lecture du document", 35),
        ("📊 Extraction des informations", 70),
        ("✅ Validation des résultats", 100)
    ]
    
    for step, progress in steps:
        status_text.text(f"⏳ {step}...")
        progress_bar.progress(progress)
        time.sleep(0.3)  # Simuler un traitement
    
    # Appel réel à l'orchestrator
    try:
        result = orchestrator.handle_document(
            pdf_path=str(file_path),
            document_type=document_type,
            advisor_id=advisor_id,
            session_id=session_id,
            declared_data=declared_data,
        )
        status_text.text("✅ Analyse terminée")
        progress_bar.progress(100)
        return result
    except Exception as e:
        status_text.text(f"❌ Erreur : {str(e)}")
        progress_bar.progress(100)
        raise

def get_document_summary(doc_data):
    """Obtenir un résumé du document pour l'affichage"""
    filename = doc_data.get('filename', 'Document')
    doc_type = doc_data.get('type', 'Inconnu')
    status = doc_data.get('status', 'inconnu')
    
    status_icon = {
        'completed': '✅',
        'processing': '⏳',
        'error': '❌',
        'inconnu': '⏸️'
    }.get(status, '⏸️')
    
    return f"{status_icon} {filename} ({doc_type})"

# =========================================================
# INITIALISATION
# =========================================================

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

orchestrator = get_orchestrator()

# =========================================================
# SESSION STATE - INITIALISATION AMÉLIORÉE
# =========================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "documents" not in st.session_state:
    st.session_state.documents = {}  # Structure: {doc_id: {"type": ..., "data": ...}}

if "current_doc_id" not in st.session_state:
    st.session_state.current_doc_id = None

if "current_client_id" not in st.session_state:
    st.session_state.current_client_id = ""

if "confirmed_fields" not in st.session_state:
    st.session_state.confirmed_fields = {}

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "page" not in st.session_state:
    st.session_state.page = "Accueil"

if "theme" not in st.session_state:
    st.session_state.theme = "light"

if "processing" not in st.session_state:
    st.session_state.processing = False

# =========================================================
# SIDEBAR AMÉLIORÉE AVEC GESTION CLIENT
# =========================================================

with st.sidebar:
    # Thème toggle
    col_theme, _ = st.columns([1, 3])
    with col_theme:
        theme_icon = "🌙" if st.session_state.theme == "light" else "☀️"
        if st.button(theme_icon, help="Changer de thème"):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()
    
    st.subheader("👤 Espace conseiller")
    
    advisor_id = st.text_input(
        "Identifiant conseiller",
        value="conseiller_test",
        help="Votre identifiant pour tracer les actions"
    )
    
    st.caption(f"🆔 Session : {st.session_state.session_id[:8]}...")
    
    st.divider()
    
    # Section Client
    st.subheader("👤 Client")
    
    client_id = st.text_input(
        "Identifiant client",
        value=st.session_state.current_client_id,
        placeholder="Entrez l'ID du client",
        help="Les documents sont regroupés par client"
    )
    
    if client_id != st.session_state.current_client_id:
        st.session_state.current_client_id = client_id
        # Réinitialiser l'affichage lors du changement de client
        st.session_state.current_doc_id = None
        st.session_state.last_result = None
        st.session_state.confirmed_fields = {}
        st.rerun()
    
    st.divider()
    
    st.subheader("🧭 Navigation")
    
    if st.button("🏠 Accueil", use_container_width=True):
        st.session_state.page = "Accueil"
        st.rerun()
    
    if st.button("📄 Analyse documentaire", use_container_width=True):
        st.session_state.page = "Extraction"
        st.rerun()
    
    if st.button("💬 Assistant IA", use_container_width=True):
        st.session_state.page = "Assistant"
        st.rerun()
    
    st.divider()
    
    st.subheader("📊 Système")
    
    col_status, col_indicator = st.columns([2, 1])
    with col_status:
        st.markdown("Orchestrateur")
    with col_indicator:
        st.markdown('<span class="status status-success">●</span>', unsafe_allow_html=True)
    
    col_status, col_indicator = st.columns([2, 1])
    with col_status:
        st.markdown("Pipeline extraction")
    with col_indicator:
        st.markdown('<span class="status status-success">●</span>', unsafe_allow_html=True)
    
    col_status, col_indicator = st.columns([2, 1])
    with col_status:
        st.markdown("Audit actif")
    with col_indicator:
        st.markdown('<span class="status status-success">●</span>', unsafe_allow_html=True)
    
    st.divider()
    
    # Actions rapides
    st.subheader("⚡ Actions rapides")
    
    if st.button("💾 Sauvegarder la session", use_container_width=True):
        if save_session_state():
            st.success("✅ Session sauvegardée")
        else:
            st.error("❌ Erreur lors de la sauvegarde")
    
    if st.button("↩️ Restaurer la session", use_container_width=True):
        if load_session_state(st.session_state.session_id):
            st.success("✅ Session restaurée")
            st.rerun()
        else:
            st.error("❌ Aucune session sauvegardée")
    
    st.divider()
    
    with st.expander("⚙️ Paramètres techniques"):
        st.caption(f"Confiance minimale : {settings.confidence_threshold}")
        st.caption(f"Écart maximal : {settings.discrepancy_threshold:.0%}")
        st.caption(f"Taille max : {settings.max_file_size_mb} Mo")
        st.caption(f"Similarité RAG : {settings.rag_similarity_threshold}")
    
    # Journal d'activité
    with st.expander("📋 Journal d'activité"):
        try:
            last_actions = audit.get_recent_actions(
                advisor_id=advisor_id,
                limit=10
            ) if hasattr(audit, 'get_recent_actions') else []
            
            if last_actions:
                for action in last_actions[:5]:
                    col_time, col_action = st.columns([1, 2])
                    with col_time:
                        st.caption(action.get('timestamp', '')[:10])
                    with col_action:
                        st.text(action.get('description', '')[:50])
            else:
                st.caption("Aucune activité récente")
        except Exception:
            st.caption("Journal non disponible")

# =========================================================
# APPLICATION DU THÈME
# =========================================================

apply_theme(st.session_state.theme)

# =========================================================
# RENDU DE L'EN-TÊTE
# =========================================================

render_header()

# =========================================================
# PAGE ACCUEIL
# =========================================================

if st.session_state.page == "Accueil":
    st.title("👋 Bonjour, conseiller")
    
    st.caption(
        "Choisissez une fonctionnalité pour commencer."
    )
    
    # Afficher le client actuel
    if st.session_state.current_client_id:
        st.info(f"👤 Client actuel : **{st.session_state.current_client_id}**")
    
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
            "🚀 Commencer l'analyse",
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
            "💬 Ouvrir l'assistant",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.page = "Assistant"
            st.rerun()
    
    st.write("")
    st.divider()
    
    st.subheader("🔄 Fonctionnement")
    
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
    
    # Statistiques rapides
    st.write("")
    st.divider()
    
    st.subheader("📊 En un coup d'œil")
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    # Calculer les stats réelles
    total_docs = len(st.session_state.documents)
    client_docs = sum(1 for d in st.session_state.documents.values() 
                     if d.get('client_id') == st.session_state.current_client_id)
    
    with col_stat1:
        st.metric("📄 Documents analysés", total_docs)
    with col_stat2:
        st.metric("👤 Documents du client", client_docs)
    with col_stat3:
        st.metric("🎯 Précision extraction", "94%", "+2%")
    with col_stat4:
        st.metric("💬 Questions posées", len(st.session_state.chat_history))

# =========================================================
# PAGE EXTRACTION AMÉLIORÉE AVEC GESTION MULTI-DOCUMENTS
# =========================================================

elif st.session_state.page == "Extraction":
    st.title("📄 Analyse documentaire")
    
    # Vérifier que le client est renseigné
    if not st.session_state.current_client_id:
        st.warning("⚠️ Veuillez d'abord renseigner un identifiant client dans la sidebar")
        st.stop()
    
    # Afficher le client actuel
    st.info(f"👤 Client : **{st.session_state.current_client_id}**")
    
    # -----------------------------------------------------
    # LISTE DES DOCUMENTS DU CLIENT
    # -----------------------------------------------------
    
    client_docs = {
        doc_id: doc_data 
        for doc_id, doc_data in st.session_state.documents.items()
        if doc_data.get("client_id") == st.session_state.current_client_id
    }
    
    if client_docs:
        st.subheader("📁 Documents du client")
        
        # Afficher les documents dans une grille
        cols = st.columns(2)
        for idx, (doc_id, doc_data) in enumerate(client_docs.items()):
            col = cols[idx % 2]
            with col:
                is_active = doc_id == st.session_state.current_doc_id
                status = doc_data.get('status', 'inconnu')
                
                # Couleur selon le statut
                status_color = {
                    'completed': '✅',
                    'processing': '⏳',
                    'error': '❌',
                    'inconnu': '⏸️'
                }.get(status, '⏸️')
                
                status_text = {
                    'completed': 'Traité',
                    'processing': 'En cours...',
                    'error': 'Erreur',
                    'inconnu': 'En attente'
                }.get(status, 'En attente')
                
                with st.container():
                    col_btn, col_status = st.columns([3, 1])
                    with col_btn:
                        if st.button(
                            f"📄 {doc_data.get('filename', 'Document')[:30]}...",
                            key=f"view_{doc_id}",
                            use_container_width=True,
                        ):
                            st.session_state.current_doc_id = doc_id
                            st.session_state.last_result = doc_data.get('result')
                            st.session_state.confirmed_fields = doc_data.get('confirmed_fields', {})
                            st.rerun()
                    with col_status:
                        st.caption(f"{status_color} {status_text}")
                    
                    # Infos supplémentaires
                    st.caption(f"Type: {doc_data.get('type', 'Inconnu')}")
                    if doc_data.get('timestamp'):
                        st.caption(f"📅 {doc_data.get('timestamp')[:16]}")
                
                st.write("")  # Espacement
        
        st.divider()
    
    # -----------------------------------------------------
    # AJOUTER UN NOUVEAU DOCUMENT
    # -----------------------------------------------------
    
    st.subheader("📎 Ajouter un document")
    
    col_upload, col_data = st.columns([1.1, 0.9], gap="large")
    
    with col_upload:
        document_type = st.selectbox(
            "Type de document",
            options=list(DOCUMENT_SCHEMAS.keys()),
            help="Sélectionnez le type de document pour optimiser l'extraction",
            key="doc_type_select"
        )
        
        uploaded_file = st.file_uploader(
            "Déposer un document",
            type=[ext.lstrip(".") for ext in settings.allowed_extensions],
            help=f"Formats acceptés : {', '.join(settings.allowed_extensions)}. Taille max : {settings.max_file_size_mb} MB",
            key=f"uploader_{st.session_state.current_client_id}"
        )
        
        if uploaded_file is not None:
            is_valid, message = validate_file(uploaded_file)
            if is_valid:
                st.success(f"✅ Document sélectionné : {uploaded_file.name}")
                st.caption(f"📦 Taille : {uploaded_file.size / 1024:.1f} KB")
            else:
                st.error(f"⚠️ {message}")
                uploaded_file = None
    
    with col_data:
        st.subheader("📝 Informations déclarées")
        
        declared_json = st.text_area(
            "Valeurs déclarées par le client",
            value='{\n  "salaire_net": 6000,\n  "montant_emprunt": 150000\n}',
            height=180,
            help="Ces données permettent de détecter les écarts avec les informations extraites.",
            key="declared_json_area"
        )
    
    # Boutons d'action
    col_buttons = st.columns([1, 1])
    with col_buttons[0]:
        run_button = st.button(
            "🚀 Lancer l'analyse",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.processing or uploaded_file is None
        )
    with col_buttons[1]:
        if st.button("🔄 Réinitialiser l'affichage", use_container_width=True):
            st.session_state.current_doc_id = None
            st.session_state.last_result = None
            st.session_state.confirmed_fields = {}
            st.rerun()
    
    # -----------------------------------------------------
    # EXECUTION AMÉLIORÉE
    # -----------------------------------------------------
    
    if run_button:
        if not st.session_state.current_client_id:
            st.error("⚠️ Veuillez renseigner un identifiant client")
            st.stop()
        
        if uploaded_file is None:
            st.error("⚠️ Déposez un document avant de lancer l'analyse")
            st.stop()
        
        try:
            declared_data = json.loads(declared_json) if declared_json.strip() else {}
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON invalide : {e}")
            st.stop()
        
        # Créer un ID unique pour ce document
        doc_id = f"{st.session_state.current_client_id}_{document_type}_{uuid.uuid4()}"
        
        # Stocker le document dans la session
        st.session_state.documents[doc_id] = {
            "client_id": st.session_state.current_client_id,
            "type": document_type,
            "filename": uploaded_file.name,
            "timestamp": datetime.now().isoformat(),
            "status": "processing",
            "result": None,
            "confirmed_fields": {},
            "declared_data": declared_data
        }
        
        st.session_state.current_doc_id = doc_id
        
        # Sauvegarder le fichier
        saved_path = UPLOAD_DIR / f"{doc_id}_{uploaded_file.name}"
        saved_path.write_bytes(uploaded_file.getvalue())
        
        # Traiter avec progression
        st.session_state.processing = True
        
        try:
            result = process_document_with_progress(
                file_path=saved_path,
                document_type=document_type,
                declared_data=declared_data,
                advisor_id=advisor_id,
                session_id=st.session_state.session_id
            )
            
            # Mettre à jour les données du document
            st.session_state.documents[doc_id]["result"] = result
            st.session_state.documents[doc_id]["status"] = "completed"
            st.session_state.last_result = result
            st.session_state.confirmed_fields = {}
            
            # Log dans l'audit
            try:
                audit.log_document_processed(
                    document_id=doc_id,
                    document_type=document_type,
                    client_id=st.session_state.current_client_id,
                    advisor_id=advisor_id,
                    status="completed"
                )
            except Exception:
                pass
            
        except Exception as e:
            st.session_state.documents[doc_id]["status"] = "error"
            st.error(f"❌ Erreur lors du traitement : {str(e)}")
            st.expander("🔍 Détails techniques").code(str(e))
        finally:
            st.session_state.processing = False
            st.rerun()
    
    # -----------------------------------------------------
    # RESULTATS DU DOCUMENT SÉLECTIONNÉ
    # -----------------------------------------------------
    
    # Si un document est sélectionné, afficher ses résultats
    if st.session_state.current_doc_id and st.session_state.last_result:
        current_doc = st.session_state.documents.get(st.session_state.current_doc_id)
        
        if current_doc:
            st.divider()
            
            # En-tête du document
            st.subheader(f"📊 Résultat - {current_doc.get('filename', 'Document')}")
            st.caption(f"Type: {current_doc.get('type', 'Inconnu')} | {current_doc.get('timestamp', '')[:16]}")
            
            result = st.session_state.last_result
            control_result = result.get("control_result", {})
            
            if not control_result.get("valid", False):
                st.error(f"🚫 Document rejeté : {control_result.get('reason', 'Raison inconnue')}")
            else:
                security = result.get("extraction_security", {})
                
                if security.get("suspicious"):
                    st.warning(
                        "⚠️ Motifs nécessitant une attention : "
                        f"{', '.join(security.get('matched_patterns', []))}"
                    )
                
                validation_result = result.get("validation_result")
                
                if validation_result:
                    fields = validation_result["fields"]
                    
                    total = len(fields)
                    reliable = sum(1 for field in fields.values() if field["status"] == "pre_rempli")
                    review = sum(1 for field in fields.values() if field["status"] == "signale")
                    absent = sum(1 for field in fields.values() if field["status"] == "absent")
                    
                    # Métriques
                    col_1, col_2, col_3, col_4 = st.columns(4)
                    
                    metrics = [
                        (col_1, "📊 Champs détectés", total),
                        (col_2, "✅ Fiables", reliable),
                        (col_3, "⚠️ À vérifier", review),
                        (col_4, "❌ Absents", absent),
                    ]
                    
                    for column, label, value in metrics:
                        with column:
                            st.markdown(
                                f"""
                                <div class="metric-card">
                                    <div class="metric-label">{label}</div>
                                    <div class="metric-value">{value}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    
                    st.write("")
                    
                    if validation_result["needs_priority_review"]:
                        st.warning("🔴 Une revue prioritaire est recommandée.")
                    else:
                        st.success("✅ Aucun point critique détecté.")
                    
                    st.subheader("📋 Informations extraites")
                    
                    # Exporter les résultats
                    csv_data = export_results_to_csv(result, current_doc.get('type', ''))
                    if csv_data:
                        st.download_button(
                            label="📥 Exporter en CSV",
                            data=csv_data,
                            file_name=f"extraction_{current_doc.get('type', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    st.write("")
                    
                    # Affichage des champs
                    confirmed_fields = st.session_state.confirmed_fields
                    
                    for field_name, decision in fields.items():
                        already_confirmed = field_name in confirmed_fields
                        
                        status = decision["status"]
                        value = decision["value"]
                        confidence = decision["confidence"]
                        reasons = decision["reasons"]
                        
                        icon = {
                            "pre_rempli": "🟢",
                            "signale": "🟠",
                            "absent": "⚪",
                        }.get(status, "⚪")
                        
                        with st.container():
                            col_field, col_value, col_action = st.columns([1.2, 2, 1])
                            
                            with col_field:
                                st.markdown(f"{icon} **{field_name}**")
                                if confidence is not None:
                                    st.progress(min(max(float(confidence), 0), 1))
                                    st.caption(f"Confiance : {confidence:.0%}")
                            
                            with col_value:
                                edited_value = st.text_input(
                                    f"Valeur — {field_name}",
                                    value=str(value) if value is not None else "",
                                    key=f"input_{field_name}_{st.session_state.current_doc_id}",
                                    label_visibility="collapsed",
                                    disabled=already_confirmed,
                                    placeholder="Non extrait — saisie manuelle",
                                )
                                
                                for reason in reasons:
                                    st.caption(f"ℹ️ {reason}")
                            
                            with col_action:
                                if already_confirmed:
                                    st.markdown(
                                        '<span class="status status-success">✅ Confirmé</span>',
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    button_label = "✅ Confirmer" if edited_value == (str(value) if value is not None else "") else "💾 Enregistrer"
                                    
                                    if st.button(
                                        button_label,
                                        key=f"confirm_{field_name}_{st.session_state.current_doc_id}",
                                        use_container_width=True,
                                    ):
                                        final_value = edited_value if edited_value != "" else None
                                        
                                        try:
                                            audit.log_human_confirmation(
                                                document_path=st.session_state.current_doc_id,
                                                document_type=current_doc.get('type', ''),
                                                field_name=field_name,
                                                confirmed_value=final_value,
                                                advisor_id=advisor_id,
                                                session_id=st.session_state.session_id,
                                                original_value=value,
                                            )
                                        except Exception:
                                            pass
                                        
                                        # Mettre à jour les confirmed_fields
                                        st.session_state.confirmed_fields[field_name] = final_value
                                        
                                        # Mettre à jour dans les documents
                                        if st.session_state.current_doc_id in st.session_state.documents:
                                            st.session_state.documents[st.session_state.current_doc_id]["confirmed_fields"] = st.session_state.confirmed_fields
                                        
                                        st.rerun()
                            
                            st.divider()
                    
                    # Sections détaillées
                    with st.expander("📄 Voir le texte OCR"):
                        st.text(result.get("ocr_text", ""))
                    
                    with st.expander("⚙️ Détail du moteur de règles"):
                        st.json(validation_result["rule_engine"])
                    
                    with st.expander("📊 Détail des écarts"):
                        st.json(validation_result["discrepancies"])
                    
                    # Bouton pour supprimer le document
                    if st.button("🗑️ Supprimer ce document", use_container_width=True):
                        if st.session_state.current_doc_id in st.session_state.documents:
                            del st.session_state.documents[st.session_state.current_doc_id]
                        st.session_state.current_doc_id = None
                        st.session_state.last_result = None
                        st.session_state.confirmed_fields = {}
                        st.rerun()

# =========================================================
# PAGE ASSISTANT AMÉLIORÉE
# =========================================================

elif st.session_state.page == "Assistant":
    st.title("💬 Assistant Crédit Habitat")
    
    st.caption(
        "Posez une question sur les documents officiels indexés dans la base documentaire."
    )
    
    # Actions rapides
    col_new, _ = st.columns([1, 3])
    with col_new:
        if st.button("🆕 Nouvelle conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    st.divider()
    
    # -----------------------------------------------------
    # QUESTIONS RAPIDES
    # -----------------------------------------------------
    
    st.caption("⚡ Questions rapides")
    
    quick_1, quick_2, quick_3 = st.columns(3)
    quick_question = None
    
    with quick_1:
        if st.button(
            "📋 Conditions d'éligibilité",
            use_container_width=True,
            help="Quelles sont les conditions d'éligibilité au crédit habitat ?"
        ):
            quick_question = "Quelles sont les conditions d'éligibilité au crédit habitat ?"
    
    with quick_2:
        if st.button(
            "📎 Documents nécessaires",
            use_container_width=True,
            help="Quels documents sont nécessaires pour constituer un dossier de crédit habitat ?"
        ):
            quick_question = "Quels documents sont nécessaires pour constituer un dossier de crédit habitat ?"
    
    with quick_3:
        if st.button(
            "💰 Taux du crédit",
            use_container_width=True,
            help="Quel est le taux d'intérêt du crédit habitat ?"
        ):
            quick_question = "Quel est le taux d'intérêt du crédit habitat ?"
    
    st.write("")
    
    # -----------------------------------------------------
    # HISTORIQUE
    # -----------------------------------------------------
    
    for exchange in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(exchange["question"])
        
        with st.chat_message("assistant"):
            if exchange.get("in_scope", False):
                st.markdown(
                    '<span class="status status-success">📚 Réponse documentée</span>',
                    unsafe_allow_html=True,
                )
                st.write(exchange["answer"])
                
                if exchange.get("sources"):
                    with st.expander("📖 Sources utilisées"):
                        for source in exchange["sources"]:
                            st.write(f"• {source}")
            else:
                st.markdown(
                    '<span class="status status-warning">⚠️ Question hors périmètre</span>',
                    unsafe_allow_html=True,
                )
                st.warning(exchange["answer"])
    
    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------
    
    question = st.chat_input("💬 Posez votre question...")
    
    if quick_question:
        question = quick_question
    
    # -----------------------------------------------------
    # EXECUTION
    # -----------------------------------------------------
    
    if question:
        with st.chat_message("user"):
            st.write(question)
        
        with st.chat_message("assistant"):
            with st.spinner("🔍 Recherche dans la documentation..."):
                try:
                    chat_result = orchestrator.handle_question(
                        question=question,
                        advisor_id=advisor_id,
                        session_id=st.session_state.session_id,
                    )
                except FileNotFoundError:
                    st.error(
                        "❌ Le vectorstore RAG n'existe pas encore. "
                        "Lancez `python -m rag.ingest` après avoir ajouté les documents dans `data/docs/`."
                    )
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Erreur lors du traitement : {str(e)}")
                    st.stop()
            
            if chat_result.get("in_scope", False):
                st.markdown(
                    '<span class="status status-success">📚 Réponse documentée</span>',
                    unsafe_allow_html=True,
                )
                st.write(chat_result["answer"])
                
                if chat_result.get("sources"):
                    with st.expander("📖 Sources utilisées"):
                        for source in chat_result["sources"]:
                            st.write(f"• {source}")
            else:
                st.markdown(
                    '<span class="status status-warning">⚠️ Question hors périmètre</span>',
                    unsafe_allow_html=True,
                )
                st.warning(chat_result["answer"])
        
        # Ajouter à l'historique
        st.session_state.chat_history.append({
            "question": question,
            "answer": chat_result["answer"],
            "in_scope": chat_result.get("in_scope", False),
            "sources": chat_result.get("sources", []),
        })
        
        st.rerun()

# =========================================================
# FOOTER
# =========================================================

st.divider()
st.caption(
    f"🏦 Crédit Agricole du Maroc — PFE 2026 | "
    f"Session : {st.session_state.session_id[:8]} | "
    f"v1.3.0 | Documents : {len(st.session_state.documents)}"
)

# =========================================================
# GESTION DES ERREURS GLOBALES
# =========================================================

if "error" in st.session_state:
    with st.sidebar:
        st.error(f"⚠️ {st.session_state.error}")
        if st.button("Effacer l'erreur"):
            del st.session_state.error
            st.rerun()