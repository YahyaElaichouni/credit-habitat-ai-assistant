"""
===========================================================
Schemas d'extraction
Projet PFE Crédit Agricole du Maroc
===========================================================
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# =========================================================
# TRANSACTION BANCAIRE
# =========================================================

class Transaction(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    montant: Optional[float] = None
    type: Optional[str] = None


# =========================================================
# CARTE D'IDENTITE
# =========================================================

class CarteIdentiteSchema(BaseModel):

    document_type: str = "carte_identite"

    cin: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    date_naissance: Optional[str] = None
    lieu_naissance: Optional[str] = None
    sexe: Optional[str] = None
    adresse: Optional[str] = None
    date_expiration: Optional[str] = None


# =========================================================
# BULLETIN DE SALAIRE
# =========================================================

class BulletinSchema(BaseModel):

    document_type: str = "bulletin"

    nom: Optional[str] = None
    prenom: Optional[str] = None

    employeur: Optional[str] = None
    poste: Optional[str] = None

    periode: Optional[str] = None

    salaire_base: Optional[float] = None
    salaire_brut: Optional[float] = None
    salaire_net: Optional[float] = None
    salaire_net_a_payer: Optional[float] = None

    devise: Optional[str] = None


# =========================================================
# RELEVE BANCAIRE
# =========================================================

class ReleveBancaireSchema(BaseModel):

    document_type: str = "releve"

    nom: Optional[str] = None
    prenom: Optional[str] = None

    banque: Optional[str] = None
    numero_compte: Optional[str] = None
    iban: Optional[str] = None

    periode_debut: Optional[str] = None
    periode_fin: Optional[str] = None

    solde_initial: Optional[float] = None
    solde_final: Optional[float] = None

    devise: Optional[str] = None

    transactions: List[Transaction] = Field(
        default_factory=list
    )


# =========================================================
# COMPROMIS DE VENTE
# =========================================================

class CompromisSchema(BaseModel):

    document_type: str = "compromis"

    vendeur_nom: Optional[str] = None
    vendeur_prenom: Optional[str] = None

    acheteur_nom: Optional[str] = None
    acheteur_prenom: Optional[str] = None

    adresse_bien: Optional[str] = None
    type_bien: Optional[str] = None

    prix_vente: Optional[float] = None
    devise: Optional[str] = None

    date_signature: Optional[str] = None

    superficie: Optional[float] = None
    reference_cadastrale: Optional[str] = None


# =========================================================
# MAPPING DES SCHEMAS
# =========================================================

DOCUMENT_SCHEMAS = {

    "carte_identite": CarteIdentiteSchema,

    "bulletin": BulletinSchema,

    "releve": ReleveBancaireSchema,

    "compromis": CompromisSchema
}