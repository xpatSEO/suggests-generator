import streamlit as st
import requests
from fake_useragent import UserAgent
import json
import pandas as pd
import re

# --- Fonction pour récupérer les suggestions Google ---
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

        return json.loads(response.text)

    except json.JSONDecodeError:
        st.error(f"🚨 Erreur JSON pour {keyword} ({ask}): réponse invalide")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"🚨 Erreur réseau pour {keyword} ({ask}): {e}")
        return []


# --- Fonction principale de traitement ---
def process_keywords(keywords_list):
    extracted_keywords = []

    # Listes de requêtes
    interrogative_asks = ["comment", "pourquoi", "laquelle", "lequel", "ou", "quand",
                          "que", "qu'est ce", "quel", "vs", "qui", "quelle", "quoi",
                          "avec", "pour", "sans", "comme", "contre", "et"]
    
    transactional_asks = ["acheter", "pas cher", "comparatif", "guide d'achat", "le meilleur"]

    # Boucle sur les mots-clés
    for keyword in keywords_list:
        # Suggestions interrogatives
        for ask in interrogative_asks:
            suggestions = get_suggestions(keyword, ask)
            for word in suggestions:
                if word:
                    matches = re.findall(r'\[(.*?)\]', str(word))
                    for match in matches:
                        split_keywords = [kw.strip() for kw in match.split(',')]
                        for single_word in split_keywords:
                            extracted_keywords.append({"suggested_keyword": single_word, "main_keyword": keyword})

        # Suggestions transactionnelles
        for ask in transactional_asks:
            suggestions = get_suggestions(keyword, ask)
            for word in suggestions:
                if word:
                    matches = re.findall(r'\[(.*?)\]', str(word))
                    for match in matches:
                        split_keywords = [kw.strip() for kw in match.split(',')]
                        for single_word in split_keywords:
                            extracted_keywords.append({"extracted_word": single_word, "keyword": keyword})

        # Mise à jour de la barre de progression
        progress_bar.progress((idx + 1) / total_keywords)

    return pd.DataFrame(extracted_keywords)


# Interface Streamlit
st.title("Extraction de suggestions Google")
st.image("logo_arkée.png")

# Upload du fichier CSV
uploaded_file = st.file_uploader("📂 Importer un fichier CSV contenant des mots-clés :", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, header=None, names=['keyword'])
    keywords_list = df['keyword'].tolist()

    if st.button("🚀 Lancer l'extraction des suggestions"):
        with st.spinner("⏳ Traitement en cours..."):
            time.sleep(1)  # Pause pour simuler un chargement
            result_df = process_keywords(keywords_list)
            result_df = result_df.applymap(lambda x: None if pd.isna(x) else re.sub(r"[\"\'\[]", "", str(x)))
            result_df = result_df.replace(to_replace=r'[0-9]', value=None, regex=True)
            result_df = result_df.dropna()
            result_df = result_df[result_df.apply(lambda row: row['keyword'] in row['extracted_word'], axis=1)]

            if not result_df.empty:
                st.success("Analyse terminée avec succès !")
                st.balloons()
                st.dataframe(result_df)

                # Génération du fichier CSV téléchargeable
                csv = result_df.to_csv(sep=';', encoding='utf-8', index=False).encode('utf-8')
                st.download_button(
                    label="📥 Télécharger le fichier CSV",
                    data=csv,
                    file_name="export_suggests.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ Aucun mot-clé extrait.")

        else:
            st.warning("⚠️ Veuillez entrer au moins un mot-clé.")

if __name__ == "__main__":
    main()
