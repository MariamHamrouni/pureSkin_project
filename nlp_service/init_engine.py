from nlp_engine import PureSkinNLPEngine
import pandas as pd

# 1. Charger le moteur (sans charger de fichier .pt pour l'instant)
engine = PureSkinNLPEngine()

# 2. Charger ton fichier de données (Vérifie bien le nom du fichier CSV !)
csv_path = "product_info_cleaned.csv"
print(f"📖 Lecture du fichier {csv_path}...")
df = pd.read_csv(csv_path)

# 3. Transformer le texte en vecteurs (Indexation)
# C'est ici que le modèle MPNet travaille le plus
print("🧠 Vectorisation des ingrédients en cours (cela peut prendre 1-2 minutes)...")
engine.load_and_vectorize_data(df)

# 4. Sauvegarder le résultat pour les futurs tests
engine.save_engine("pure_skin_engine.pt")
print("✅ Succès ! Le fichier 'pure_skin_engine.pt' a été créé.")