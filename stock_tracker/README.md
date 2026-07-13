# 📦 Suivi de stock par QR Code

Application web (Streamlit) de suivi de stock, pensée pour être ouverte en
scannant un QR Code collé sur un composant. Le QR Code contient une URL avec
l'identifiant du composant :

```
https://mon-appli.streamlit.app/?id=COMP-001
```

Les données sont stockées dans un **Google Sheet** partagé (onglets
`Stock_Actuel` et `Historique`) : accessible de partout, persistant, et
consultable à la main comme un tableur classique.

---

## 1. Installation locale (pour tester)

```bash
cd stock_tracker
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

Pour lancer en local, il faut d'abord configurer l'accès Google (étapes 2 et 3),
puis :

```bash
streamlit run app.py
```

---

## 2. Préparer le Google Sheet

1. Créez un nouveau Google Sheet (nom libre, ex. « Stock »).
2. Créez **deux onglets** nommés **exactement** :
   - `Stock_Actuel` avec, en ligne 1 : `ID_Composant | Nom | Quantite | Emplacement`
   - `Historique` avec, en ligne 1 : `Date | ID_Composant | Type | Quantite | Emplacement | Utilisation`
3. Notez l'URL du document (elle servira dans les secrets).

---

## 3. Créer un compte de service Google (accès automatisé)

L'application se connecte au Sheet via un « compte de service » (un robot Google).

1. Allez sur <https://console.cloud.google.com/> et créez un projet (ou réutilisez-en un).
2. Activez ces deux API : **Google Sheets API** et **Google Drive API**
   (menu « API et services » > « Bibliothèque »).
3. Menu « API et services » > « Identifiants » > « Créer des identifiants » >
   **Compte de service**. Donnez-lui un nom, validez.
4. Ouvrez le compte de service créé > onglet **Clés** > « Ajouter une clé » >
   « Créer une clé » > **JSON**. Un fichier `.json` se télécharge : gardez-le.
5. Ouvrez ce JSON, copiez la valeur de `client_email`
   (ex. `robot@projet.iam.gserviceaccount.com`).
6. Dans votre Google Sheet, cliquez **Partager** et partagez le document avec
   cette adresse e-mail en **Éditeur**. ⚠️ Étape indispensable, sinon l'appli
   ne pourra rien écrire.

---

## 4. Renseigner les secrets

Copiez le modèle et remplissez-le avec les valeurs du fichier JSON :

```bash
# dans le dossier .streamlit/
copy secrets.toml.example secrets.toml      # Windows
# cp secrets.toml.example secrets.toml       # Linux / macOS
```

Éditez `.streamlit/secrets.toml` : collez l'URL du Sheet et recopiez les champs
depuis le JSON (`private_key`, `client_email`, etc.).

> 🔒 `secrets.toml` contient une clé privée : il est déjà ignoré par Git
> (`.gitignore`). Ne le commitez jamais, ne le partagez pas.

Vous pouvez maintenant tester en local avec `streamlit run app.py`.

---

## 5. Déployer en ligne (Streamlit Community Cloud — gratuit)

Objectif : obtenir une **URL fixe** pour les QR Codes, sans PC à laisser allumé.

1. Poussez ce dossier `stock_tracker` sur un dépôt **GitHub**
   (le `.gitignore` protège déjà `secrets.toml`).
2. Allez sur <https://share.streamlit.io/> et connectez-vous avec GitHub.
3. « New app » > choisissez le dépôt, la branche, et `app.py` comme fichier.
4. Avant de déployer : ouvrez **Advanced settings > Secrets** et **collez le
   contenu** de votre `secrets.toml` (les secrets ne sont PAS sur GitHub, il
   faut les redonner ici).
5. Déployez. Vous obtenez une URL du type
   `https://<votre-appli>.streamlit.app`.

Cette URL est **permanente** : c'est elle qui ira dans les QR Codes.

```
https://<votre-appli>.streamlit.app/?id=COMP-001
```

---

## 6. Utilisation

- **Scanner un QR Code** ouvre la page du composant : nom, stock actuel, et le
  formulaire d'entrée / sortie.
- **Sortie de stock** : un champ « Utilisation » apparaît
  (XLOCK V1.1.1, XLOCL V1.2.2, Bancs de tests, Gamma Box).
- **Composant inconnu** (ID pas encore dans le Sheet) : un formulaire de
  création s'affiche, avec l'ID déjà pré-rempli.
- **Ajouter un composant** est aussi toujours possible via le panneau
  « ➕ Ajouter un nouveau composant » en bas de page.
- **Lieux disponibles** : Paris, La Rochelle, Toulouse, Forvia, Airbus.

---

## Remarque technique (à connaître)

L'application réécrit l'onglet concerné à chaque mouvement. Si deux personnes
valident **exactement au même instant** depuis deux sites différents, un
mouvement pourrait être écrasé. C'est rare à l'échelle d'un atelier, mais si le
volume de scans simultanés devient important, il faudra passer sur une vraie
base de données (ex. Supabase). À rediscuter le moment venu.
