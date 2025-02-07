import streamlit as st
import requests
from fake_useragent import UserAgent
import json
import pandas as pd
import re
import io
import time

# Fonction pour récupérer les suggestions Google
def get_suggestions(keyword, ask, hl="fr", gl="fr"):
    endpoint = f"https://suggestqueries.google.com/complete/search?output=firefox&q={ask}+*+{keyword}&hl={hl}&gl={gl}"
    ua = UserAgent()
    headers = {"user-agent": ua.chrome}

    try:
        response = requests.get(endpoint, headers=headers, timeout=5, verify=True)

        if response.status_code != 200:
            st.warning(f"⚠️ Erreur HTTP {response.status_code} pour {keyword} ({ask})")
            return []

        if not response.text.strip():
            st.warning(f"⚠️ Réponse vide pour {keyword} ({ask})")
            return []

        # Vérifier si la réponse est bien une liste JSON
        suggestions = json.loads(response.text)
        if isinstance(suggestions, list) and len(suggestions) > 1:
            return suggestions[1]  # Google retourne les suggestions en 2ème position

        return []
        
    except json.JSONDecodeError:
        st.error(f"🚨 Erreur JSON pour {keyword} ({ask}): réponse invalide")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"🚨 Erreur réseau pour {keyword} ({ask}): {e}")
        return []

# Fonction principale de traitement des mots-clés
def process_keywords(keywords_list):
    extracted_keywords = []
    interrogative_asks = ["comment", "pourquoi", "laquelle", "lequel", "ou", "quand",
                          "que", "qu'est ce", "quel", "vs", "qui", "quelle", "quoi",
                          "avec", "pour", "sans", "comme", "contre", "et"]
    transactional_asks = ["acheter", "pas cher", "comparatif", "guide d'achat", "le meilleur"]

    if not keywords_list:
        return pd.DataFrame(columns=["extracted_word", "keyword"])

    progress_bar = st.progress(0)  # Barre de progression Streamlit
    total_keywords = len(keywords_list)

    for idx, keyword in enumerate(keywords_list):
        keyword = keyword.strip()
        if not keyword:
            continue

        for ask in interrogative_asks + transactional_asks:
            suggestions = get_suggestions(keyword, ask)
            if suggestions:
                for word in suggestions:
                    matches = re.findall(r'\[(.*?)\]', str(word))
                    for match in matches:
                        split_keywords = [kw.strip() for kw in match.split(',')]
                        for single_word in split_keywords:
                            if single_word:  # Éviter d'ajouter des chaînes vides
                                extracted_keywords.append({"extracted_word": single_word, "keyword": keyword})

        # Mise à jour de la barre de progression
        progress_bar.progress((idx + 1) / total_keywords)

    return pd.DataFrame(extracted_keywords)


# Interface Streamlit
st.image("arkee-white.png", width=150)
st.title("Extraction de suggestions Google")

# Champ de texte pour saisir les requêtes
input_keywords = st.text_area("Entrez vos mots-clés (un par ligne) :")
keywords_list = [kw.strip() for kw in input_keywords.split('\n') if kw.strip()]

# Afficher un message si aucun mot-clé n'est entré
if not keywords_list:
    st.warning("Veuillez entrer au moins un mot-clé.")
else:
    if st.button("Extraire les suggestions"):
        with st.spinner("Traitement en cours..."):
            time.sleep(1) # Pause

            result_df = process_keywords(keywords_list)

            if not result_df.empty:
                result_df = result_df.applymap(lambda x: None if pd.isna(x) else re.sub(r"[\"\'\[]", "", str(x)))
                result_df = result_df.replace(to_replace=r'[0-9]', value=None, regex=True)
                result_df = result_df.dropna()
                result_df = result_df[result_df.apply(lambda row: row['keyword'] in row['extracted_word'], axis=1)]

                if not result_df.empty:
                    st.success("Extraction terminée !")
                    st.dataframe(result_df)

                    # Création du fichier CSV en mémoire pour téléchargement
                    csv_buffer = io.StringIO()
                    result_df.to_csv(csv_buffer, sep=';', encoding='utf-8', index=False)
                    csv_data = csv_buffer.getvalue()

                    st.download_button(
                        label="⬇️ Télécharger le fichier CSV",
                        data=csv_data,
                        file_name="export_suggestions_simplifie.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ Aucun mot-clé pertinent trouvé.")
            else:
                st.warning("⚠️ Aucune donnée extraite.")
