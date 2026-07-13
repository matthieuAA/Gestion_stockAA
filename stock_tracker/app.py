"""
Application de suivi de stock via QR Code (version Google Sheets).

Principe :
    Un QR Code collé sur un composant contient une URL avec l'identifiant du
    produit en paramètre, par exemple :
        https://mon-appli.streamlit.app/?id=COMP-001
    L'application lit cet identifiant, affiche le stock du composant et permet
    d'enregistrer une entrée, une sortie, ou de créer un nouveau composant.

Stockage :
    Les données sont dans un Google Sheet partagé (le "tableur"), avec deux
    onglets : "Stock_Actuel" et "Historique". C'est l'équivalent en ligne du
    fichier stocks.xlsx : mêmes onglets, mêmes colonnes, éditable à la main,
    mais accessible de partout et persistant.

Connexion :
    Via la librairie st-gsheets-connection, configurée par les "secrets"
    Streamlit (compte de service Google). Voir le README pour la mise en place.

Lancement local :
    streamlit run app.py
"""

from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# CONSTANTES / CONFIGURATION
# ---------------------------------------------------------------------------

ONGLET_STOCK = "Stock_Actuel"          # Onglet du stock courant
ONGLET_HISTO = "Historique"            # Onglet du journal des mouvements

# Colonnes attendues dans chaque onglet (l'ordre est important)
COLONNES_STOCK = ["ID_Composant", "Nom", "Quantite", "Emplacement"]
COLONNES_HISTO = ["Date", "ID_Composant", "Type", "Quantite", "Emplacement", "Utilisation"]

# Valeurs proposées dans les listes déroulantes
LIEUX = ["Paris", "La Rochelle", "Toulouse", "Forvia", "Airbus"]
UTILISATIONS = ["XLOCK V1.1.1", "XLOCL V1.2.2", "Bancs de tests", "Gamma Box"]

# Connexion Google Sheets (paramètres lus dans les secrets Streamlit)
conn = st.connection("gsheets", type=GSheetsConnection)


# ---------------------------------------------------------------------------
# ACCÈS AU GOOGLE SHEET
# ---------------------------------------------------------------------------

def _nettoyer(df, colonnes):
    """
    Normalise un DataFrame lu depuis Google Sheets :
    - ne garde que les colonnes attendues (dans le bon ordre) ;
    - supprime les lignes entièrement vides (Sheets renvoie souvent des
      lignes fantômes en fin de tableau).
    """
    # S'assure que toutes les colonnes attendues existent
    for col in colonnes:
        if col not in df.columns:
            df[col] = None
    df = df[colonnes]
    # Supprime les lignes où toutes les cellules sont vides
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def lire_stock():
    """Lit l'onglet Stock_Actuel. ttl=0 => lecture toujours fraîche."""
    df = conn.read(worksheet=ONGLET_STOCK, ttl=0)
    df = _nettoyer(df, COLONNES_STOCK)
    # La colonne Quantite doit être numérique (Sheets peut renvoyer du texte)
    df["Quantite"] = (
        pd.to_numeric(df["Quantite"], errors="coerce").fillna(0).astype(int)
    )
    return df


def lire_historique():
    """Lit l'onglet Historique. ttl=0 => lecture toujours fraîche."""
    df = conn.read(worksheet=ONGLET_HISTO, ttl=0)
    return _nettoyer(df, COLONNES_HISTO)


def ecrire_stock(df):
    """Réécrit l'intégralité de l'onglet Stock_Actuel."""
    conn.update(worksheet=ONGLET_STOCK, data=df)


def ecrire_historique(df):
    """Réécrit l'intégralité de l'onglet Historique."""
    conn.update(worksheet=ONGLET_HISTO, data=df)


# ---------------------------------------------------------------------------
# CRÉATION D'UN COMPOSANT
# ---------------------------------------------------------------------------

def ajouter_composant(id_composant, nom, quantite, emplacement):
    """
    Crée un nouveau composant dans l'onglet "Stock_Actuel".

    - Refuse si l'ID existe déjà (pour éviter les doublons).
    - Trace la création dans l'onglet "Historique".

    Renvoie (succès: bool, message: str).
    """
    id_composant = str(id_composant).strip()
    nom = str(nom).strip()

    if not id_composant:
        return False, "L'identifiant du composant est obligatoire."
    if not nom:
        return False, "Le nom du composant est obligatoire."

    df_stock = lire_stock()

    # Vérifie que l'ID n'existe pas déjà
    deja_present = df_stock["ID_Composant"].astype(str) == id_composant
    if deja_present.any():
        return False, f"Le composant '{id_composant}' existe déjà."

    # Ajout de la ligne dans le stock actuel
    nouveau = {
        "ID_Composant": id_composant,
        "Nom": nom,
        "Quantite": int(quantite),
        "Emplacement": emplacement,
    }
    df_stock = pd.concat([df_stock, pd.DataFrame([nouveau])], ignore_index=True)
    ecrire_stock(df_stock)

    # Trace la création dans l'historique
    df_histo = lire_historique()
    ligne_histo = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ID_Composant": id_composant,
        "Type": "Création",
        "Quantite": int(quantite),
        "Emplacement": emplacement,
        "Utilisation": "",
    }
    df_histo = pd.concat([df_histo, pd.DataFrame([ligne_histo])], ignore_index=True)
    ecrire_historique(df_histo)

    return True, f"Composant '{id_composant}' créé avec succès."


def formulaire_creation(id_pre_rempli=""):
    """
    Affiche un formulaire de création de composant.

    `id_pre_rempli` pré-remplit l'identifiant (ex : ID scanné mais inconnu).
    """
    with st.form("form_creation", clear_on_submit=True):
        new_id = st.text_input("Identifiant du composant", value=id_pre_rempli)
        new_nom = st.text_input("Nom du composant")
        new_qte = st.number_input("Quantité initiale", min_value=0, step=1, value=0)
        new_lieu = st.selectbox("Lieu", options=LIEUX, key="creation_lieu")
        creer = st.form_submit_button("Créer le composant")

    if creer:
        succes, message = ajouter_composant(new_id, new_nom, new_qte, new_lieu)
        if succes:
            st.success(f"✅ {message}")
        else:
            st.error(f"❌ {message}")


# ---------------------------------------------------------------------------
# ENREGISTREMENT D'UN MOUVEMENT
# ---------------------------------------------------------------------------

def enregistrer_mouvement(id_composant, type_mvt, quantite, emplacement, utilisation):
    """
    Enregistre un mouvement de stock.

    - Ajoute une ligne dans l'onglet "Historique".
    - Met à jour la quantité dans l'onglet "Stock_Actuel"
      (ajout si "Entrée", soustraction si "Sortie").

    Renvoie (succès: bool, message: str, nouvelle_quantite: int|None).
    """
    df_stock = lire_stock()

    # Recherche de la ligne du composant
    masque = df_stock["ID_Composant"].astype(str) == str(id_composant)
    if not masque.any():
        return False, f"Composant '{id_composant}' introuvable.", None

    index_ligne = df_stock[masque].index[0]
    quantite_actuelle = int(df_stock.at[index_ligne, "Quantite"])

    # Calcul de la nouvelle quantité
    if type_mvt == "Entrée de stock":
        nouvelle_quantite = quantite_actuelle + quantite
    else:  # "Sortie de stock"
        nouvelle_quantite = quantite_actuelle - quantite
        if nouvelle_quantite < 0:
            return (
                False,
                f"Stock insuffisant : {quantite_actuelle} en stock, "
                f"sortie de {quantite} demandée.",
                None,
            )

    # Mise à jour du stock actuel
    df_stock.at[index_ligne, "Quantite"] = nouvelle_quantite
    ecrire_stock(df_stock)

    # Ajout de la ligne dans l'historique
    df_histo = lire_historique()
    nouvelle_ligne = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ID_Composant": id_composant,
        "Type": type_mvt,
        "Quantite": quantite,
        "Emplacement": emplacement,
        "Utilisation": utilisation if type_mvt == "Sortie de stock" else "",
    }
    df_histo = pd.concat([df_histo, pd.DataFrame([nouvelle_ligne])], ignore_index=True)
    ecrire_historique(df_histo)

    return True, "Mouvement enregistré avec succès.", nouvelle_quantite


# ---------------------------------------------------------------------------
# INTERFACE STREAMLIT
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Suivi de stock", page_icon="📦")
    st.title("📦 Suivi de stock")

    # --- 1. Récupération de l'ID depuis l'URL -----------------------------
    id_composant = st.query_params.get("id", None)

    if not id_composant:
        st.error("Veuillez scanner un QR Code valide.")
        # On laisse tout de même la possibilité d'ajouter un composant
        st.divider()
        with st.expander("➕ Ajouter un nouveau composant"):
            formulaire_creation()
        st.stop()

    # --- 2. Recherche du composant dans le stock actuel -------------------
    df_stock = lire_stock()
    masque = df_stock["ID_Composant"].astype(str) == str(id_composant)

    if not masque.any():
        st.warning(
            f"Le composant **{id_composant}** n'existe pas encore dans le stock."
        )
        st.info("Renseignez ses informations ci-dessous pour le créer.")
        formulaire_creation(id_pre_rempli=str(id_composant))
        st.stop()

    # Informations du composant trouvé
    ligne = df_stock[masque].iloc[0]
    nom = ligne["Nom"]
    stock_actuel = int(ligne["Quantite"])

    st.subheader(f"{nom}  ·  `{id_composant}`")
    st.metric(label="Stock actuel", value=stock_actuel)
    st.divider()

    # --- 3. Formulaire de mouvement ---------------------------------------
    # Le choix "Entrée / Sortie" est HORS du formulaire pour que le champ
    # conditionnel "Utilisation" apparaisse en temps réel.
    type_mvt = st.radio(
        "Type de mouvement",
        options=["Entrée de stock", "Sortie de stock"],
        horizontal=True,
    )

    with st.form("form_mouvement"):
        quantite = st.number_input("Quantité", min_value=1, step=1, value=1)
        emplacement = st.selectbox("Lieu", options=LIEUX)

        # Champ conditionnel : uniquement pour une sortie de stock
        utilisation = ""
        if type_mvt == "Sortie de stock":
            utilisation = st.selectbox("Utilisation", options=UTILISATIONS)

        valider = st.form_submit_button("Valider le mouvement")

    # --- 4. Traitement de la validation -----------------------------------
    if valider:
        succes, message, nouvelle_quantite = enregistrer_mouvement(
            id_composant=id_composant,
            type_mvt=type_mvt,
            quantite=int(quantite),
            emplacement=emplacement,
            utilisation=utilisation,
        )
        if succes:
            st.success(f"✅ {message}  Nouveau stock : {nouvelle_quantite}.")
            st.balloons()
        else:
            st.error(f"❌ {message}")

    # --- 5. Ajout d'un composant : TOUJOURS disponible --------------------
    st.divider()
    with st.expander("➕ Ajouter un nouveau composant"):
        formulaire_creation()


if __name__ == "__main__":
    main()
