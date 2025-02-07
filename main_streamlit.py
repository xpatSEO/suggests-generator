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
                            extracted_keywords.append({"suggested_keyword": single_word, "main_keyword": keyword})

    # Conversion en DataFrame
    df = pd.DataFrame(extracted_keywords)

    if not df.empty:
        df = df.applymap(lambda x: None if pd.isna(x) else re.sub(r"[\"\'\[]", "", str(x)))
        df = df.replace(to_replace=r'[0-9]', value=None, regex=True)
        df = df.dropna()
        df = df[df.apply(lambda row: row['main_keyword'] in row['suggested_keyword'], axis=1)]

    return df


# --- Interface Streamlit ---
def main():
    st.image("arkee-white.png",width=150)
    st.title("Extracteur de suggestions Google")
    
    # Zone de texte pour entrer les mots-clés
    keywords_text = st.text_area("Entrez vos mots-clés (un par ligne) :")
    
    if st.button("Lancer l'extraction"):
        if keywords_text.strip():
            keywords_list = [kw.strip().lower() for kw in keywords_text.split("\n") if kw.strip()]
            
            with st.spinner("Analyse en cours..."):
                result_df = process_keywords(keywords_list)

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
