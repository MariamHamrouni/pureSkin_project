import pandas as pd
import logging
from nlp_engine import PureSkinNLPEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rebuild():
    # 1. Charger les données brutes
    print("📖 Chargement du CSV...")
    df = pd.read_csv('product_info_cleaned.csv')

    # 2. Initialiser le moteur (en mode création)
    engine = PureSkinNLPEngine(enable_cache=False)

    # 3. Lancer la vectorisation et la catégorisation automatique
    # C'est ici que detect_categories est appliqué à chaque ligne
    print("🧪 Vectorisation avec SciBERT (cela peut prendre quelques minutes)...")
    engine.load_and_vectorize_data(df)

    # 4. Sauvegarder le nouveau moteur
    print("💾 Sauvegarde du fichier pure_skin_engine.pt...")
    engine.save_engine("pure_skin_engine.pt")
    
    print("✅ Re-génération terminée !")
    
    # Petit check de debug pour CeraVe
    check = engine.products_df_indexed[engine.products_df_indexed['brand_name'].str.contains('CeraVe', case=False, na=False)]
    if not check.empty:
        print(f"🔍 Debug : CeraVe a été trouvé et classé en : {check['secondary_category'].iloc[0]}")
    else:
        print("⚠️ Attention : CeraVe n'est pas présent dans ton fichier CSV !")

if __name__ == "__main__":
    rebuild()