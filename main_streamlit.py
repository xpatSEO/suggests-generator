import streamlit as st
import requests
from fake_useragent import UserAgent
import json
import pandas as pd
import re
import time  # Ajout pour simuler un délai

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

# --- Interface Streamlit ---
def main():
    st.image("arkee-white.png", width=150)
    st.title("Extracteur de suggestions Google")

    # Zone de texte pour entrer les mots-clés
    keywords_text = st.text_area("Entrez vos mots-clés (un par ligne) :")

    # Liste des asks
    interrogative_asks = ["comment", "pourquoi", "laquelle", "lequel", "ou", "quand",
                          "que", "qu'est ce", "quel", "vs", "qui", "quelle", "quoi",
                          "avec", "pour", "sans", "comme", "contre", "et"]
    
    transactional_asks = ["acheter", "pas cher", "comparatif", "guide d'achat", "le meilleur"]

    # Expander pour les options avancées (remplace le popover)
    with st.expander("⚙️ Options avancées"):
        st.subheader("Sélectionnez les asks à inclure")

        selected_interrogative_asks = [
            ask for ask in interrogative_asks if st.checkbox(ask, value=True)
        ]
        
        selected_transactional_asks = [
            ask for ask in transactional_asks if st.checkbox(ask, value=True)
        ]

        # Zone pour ajouter des asks personnalisés
        st.subheader("Asks personnalisés")
        additional_asks_text = st.text_area("Ajoutez des asks personnalisés (un par ligne) :", "")

    if st.button("Lancer l'extraction"):
        if keywords_text.strip():
            keywords_list = [kw.strip().lower() for kw in keywords_text.split("\n") if kw.strip()]
            
            with st.spinner("Préparation..."):
                time.sleep(1)  # Petit délai avant le début du traitement

            # Filtrage des asks sélectionnés
            additional_asks_list = [ask.strip().lower() for ask in additional_asks_text.split("\n") if ask.strip()]
            selected_asks = selected_interrogative_asks + selected_transactional_asks + additional_asks_list

            result_df = process_keywords(keywords_list, selected_asks)

            if not result_df.empty:
                st.success("✅ Analyse terminée avec succès !")
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

# --- Fonction principale de traitement ---
def process_keywords(keywords_list, selected_asks):
    extracted_keywords = []

    total_iterations = len(keywords_list) * len(selected_asks)  # Nombre total d'itérations
    progress_bar = st.progress(0)  # Initialisation de la barre de progression
    progress_text = st.empty()  # Zone pour afficher le pourcentage
    iteration = 0

    # Boucle sur les mots-clés
    for keyword in keywords_list:
        for ask in selected_asks:
            suggestions = get_suggestions(keyword, ask)
            for word in suggestions:
                if word:
                    matches = re.findall(r'\[(.*?)\]', str(word))
                    for match in matches:
                        split_keywords = [kw.strip() for kw in match.split(',')]
                        for single_word in split_keywords:
                            extracted_keywords.append({"suggested_keyword": single_word, "main_keyword": keyword})
            
            # Mise à jour de la barre de progression
            iteration += 1
            progress_bar.progress(iteration / total_iterations)  # Mise à jour de la barre
            progress_text.text(f"Traitement en cours... {int((iteration / total_iterations) * 100)}%")  

            time.sleep(0.1)  # Simule un délai pour mieux voir la progression

    # Suppression des nombres de 1 ou 2 chiffres seuls mais conservation des années
    df = pd.DataFrame(extracted_keywords)
    if not df.empty:
        df = df.applymap(lambda x: None if pd.isna(x) else re.sub(r"[\"\'\[]", "", str(x)))
        df = df.replace(to_replace=r'^\d{1,2}$', value=None, regex=True)  # Supprime uniquement les nombres courts
        df = df.dropna()
        df = df[df.apply(lambda row: row['main_keyword'] in row['suggested_keyword'], axis=1)]

    # Suppression de la barre une fois terminé
    progress_bar.empty()
    progress_text.empty()

    return df

if __name__ == "__main__":
    main()
