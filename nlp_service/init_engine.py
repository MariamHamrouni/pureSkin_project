from nlp_engine import PureSkinNLPEngine
import pandas as pd
import logging
from pathlib import Path
import sys
import traceback

# Configuration du logging détaillé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('engine_init.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_dataset(df: pd.DataFrame) -> tuple[bool, list]:
    """
    Valide la structure et la qualité du dataset
    
    Returns:
        tuple: (is_valid, list_of_issues)
    """
    issues = []
    
    # Colonnes requises
    required_columns = [
        'product_id', 'product_name', 'brand_name', 
        'ingredients', 'price_usd'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        issues.append(f"Colonnes manquantes: {missing_columns}")
    
    # Vérification des valeurs manquantes
    for col in required_columns:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                issues.append(f"Valeurs manquantes dans '{col}': {missing_count}")
    
    # Vérification des types de données
    if 'price_usd' in df.columns:
        try:
            df['price_usd'] = pd.to_numeric(df['price_usd'], errors='coerce')
            invalid_prices = df['price_usd'].isna().sum()
            if invalid_prices > 0:
                issues.append(f"Prix invalides: {invalid_prices}")
        except:
            issues.append("Erreur conversion prix")
    
    # Vérification des doublons
    duplicates = df.duplicated(subset=['product_id'], keep=False).sum()
    if duplicates > 0:
        issues.append(f"ID produits dupliqués: {duplicates}")
    
    # Vérification de la longueur des ingrédients
    if 'ingredients' in df.columns:
        df['ingredients_length'] = df['ingredients'].astype(str).str.len()
        short_ingredients = (df['ingredients_length'] < 10).sum()
        if short_ingredients > 0:
            issues.append(f"Listes d'ingrédients trop courtes: {short_ingredients}")
    
    return len(issues) == 0, issues

def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie et prépare le dataset pour l'indexation"""
    
    logger.info("🧹 Nettoyage du dataset...")
    
    # Créer une copie pour éviter les modifications inplace
    df_clean = df.copy()
    
    # 1. Standardiser les IDs produits
    if 'product_id' in df_clean.columns:
        df_clean['product_id'] = df_clean['product_id'].astype(str).str.strip()
    
    # 2. Nettoyer les noms de produits
    if 'product_name' in df_clean.columns:
        df_clean['product_name'] = df_clean['product_name'].astype(str).str.strip()
    
    # 3. Nettoyer les marques
    if 'brand_name' in df_clean.columns:
        df_clean['brand_name'] = df_clean['brand_name'].astype(str).str.strip()
    
    # 4. Nettoyer les ingrédients
    if 'ingredients' in df_clean.columns:
        # Remplacer les NaN par chaîne vide
        df_clean['ingredients'] = df_clean['ingredients'].fillna('')
        # Standardiser
        df_clean['ingredients'] = df_clean['ingredients'].astype(str).str.strip()
    
    # 5. Convertir les prix
    if 'price_usd' in df_clean.columns:
        df_clean['price_usd'] = pd.to_numeric(df_clean['price_usd'], errors='coerce')
        # Remplacer les valeurs aberrantes par la médiane
        median_price = df_clean['price_usd'].median()
        df_clean['price_usd'] = df_clean['price_usd'].fillna(median_price)
    
    # 6. Gérer les autres colonnes numériques
    numeric_columns = ['rating', 'reviews', 'loves_count']
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    logger.info(f"✅ Dataset nettoyé: {len(df_clean)} lignes")
    
    # Statistiques de nettoyage
    logger.info(f"📊 Statistiques après nettoyage:")
    logger.info(f"   - Prix moyen: ${df_clean['price_usd'].mean():.2f}")
    logger.info(f"   - Produits uniques: {df_clean['product_id'].nunique()}")
    logger.info(f"   - Marques uniques: {df_clean['brand_name'].nunique()}")
    
    return df_clean

def optimize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Optimise le dataset pour la performance"""
    
    logger.info("⚡ Optimisation du dataset...")
    
    df_opt = df.copy()
    
    # 1. Convertir les colonnes catégorielles
    categorical_cols = ['brand_name', 'primary_category', 'secondary_category']
    for col in categorical_cols:
        if col in df_opt.columns and df_opt[col].dtype == 'object':
            df_opt[col] = df_opt[col].astype('category')
    
    # 2. Sélectionner uniquement les colonnes nécessaires
    # Colonnes de base
    base_columns = [
        'product_id', 'product_name', 'brand_name', 
        'ingredients', 'price_usd'
    ]
    
    # Colonnes optionnelles utiles
    optional_columns = [
        'rating', 'reviews', 'loves_count', 'size',
        'primary_category', 'secondary_category', 'tertiary_category',
        'new', 'out_of_stock', 'highlights'
    ]
    
    # Garder les colonnes présentes
    available_cols = []
    for col in base_columns + optional_columns:
        if col in df_opt.columns:
            available_cols.append(col)
    
    df_opt = df_opt[available_cols]
    
    # 3. Échantillonner si le dataset est trop grand
    max_rows = 20000  # Limite pour la performance
    if len(df_opt) > max_rows:
        logger.warning(f"Dataset trop grand ({len(df_opt)} rows), échantillonnage à {max_rows} rows...")
        df_opt = df_opt.sample(max_rows, random_state=42).reset_index(drop=True)
    
    # 4. Optimisation mémoire
    for col in df_opt.columns:
        if df_opt[col].dtype == 'float64':
            df_opt[col] = df_opt[col].astype('float32')
        elif df_opt[col].dtype == 'int64':
            df_opt[col] = df_opt[col].astype('int32')
    
    logger.info(f"✅ Dataset optimisé: {len(df_opt)} lignes, {len(df_opt.columns)} colonnes")
    
    # Analyse mémoire
    memory_mb = df_opt.memory_usage(deep=True).sum() / 1024 / 1024
    logger.info(f"📦 Mémoire utilisée: {memory_mb:.2f} MB")
    
    return df_opt

def save_dataset_info(df: pd.DataFrame, output_dir: Path):
    """Sauvegarde les informations du dataset"""
    
    info_file = output_dir / "dataset_info.json"
    
    info = {
        "total_products": len(df),
        "unique_brands": df['brand_name'].nunique() if 'brand_name' in df.columns else 0,
        "price_stats": {
            "mean": float(df['price_usd'].mean()) if 'price_usd' in df.columns else 0,
            "median": float(df['price_usd'].median()) if 'price_usd' in df.columns else 0,
            "min": float(df['price_usd'].min()) if 'price_usd' in df.columns else 0,
            "max": float(df['price_usd'].max()) if 'price_usd' in df.columns else 0
        },
        "columns": list(df.columns),
        "categories": {}
    }
    
    # Statistiques par catégorie
    for cat_col in ['primary_category', 'secondary_category']:
        if cat_col in df.columns:
            info["categories"][cat_col] = df[cat_col].value_counts().head(20).to_dict()
    
    # Sauvegarder
    import json
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Informations dataset sauvegardées dans {info_file}")

def main():
    """Fonction principale d'initialisation du moteur"""
    
    logger.info("🚀 DÉMARRAGE DE L'INITIALISATION DU MOTEUR PURESKIN")
    logger.info("="*60)
    
    # 1. Vérifier le fichier source
    csv_path = Path("product_info_cleaned.csv")
    if not csv_path.exists():
        logger.error(f"❌ Fichier {csv_path} introuvable !")
        logger.info("💡 Assurez-vous que le fichier existe dans le répertoire courant.")
        logger.info("   Vous pouvez le générer avec data_cleaning.ipynb")
        sys.exit(1)
    
    logger.info(f"📖 Lecture du fichier {csv_path}...")
    
    try:
        # Lire le CSV avec gestion d'erreurs
        df = pd.read_csv(csv_path, low_memory=False)
        logger.info(f"✅ CSV lu avec succès: {len(df)} lignes, {len(df.columns)} colonnes")
        
        # Aperçu des colonnes
        logger.info(f"📋 Colonnes disponibles: {list(df.columns)}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lecture CSV: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # 2. Validation du dataset
    logger.info("🔍 Validation du dataset...")
    is_valid, issues = validate_dataset(df)
    
    if issues:
        logger.warning("⚠️  Problèmes détectés:")
        for issue in issues:
            logger.warning(f"   - {issue}")
        
        if not is_valid:
            logger.error("❌ Dataset invalide. Correction nécessaire.")
            # Continuer quand même avec warning
    else:
        logger.info("✅ Dataset validé avec succès")
    
    # 3. Nettoyage
    df_clean = clean_dataset(df)
    
    # 4. Optimisation
    df_opt = optimize_dataset(df_clean)
    
    # 5. Initialisation du moteur
    logger.info("🔧 Initialisation du moteur PureSkinNLPEngine...")
    try:
        engine = PureSkinNLPEngine(enable_cache=True)
        logger.info("✅ Moteur initialisé")
    except Exception as e:
        logger.error(f"❌ Erreur initialisation moteur: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # 6. Vectorisation (étape la plus longue)
    logger.info("🧠 Vectorisation des ingrédients en cours...")
    logger.info("   ⏱️  Cela peut prendre 1-5 minutes selon la taille du dataset")
    
    try:
        start_time = pd.Timestamp.now()
        engine.load_and_vectorize_data(df_opt)
        end_time = pd.Timestamp.now()
        
        duration = (end_time - start_time).total_seconds()
        logger.info(f"✅ Vectorisation terminée en {duration:.1f} secondes")
        
        # Statistiques
        if engine.products_df_indexed is not None:
            logger.info(f"📊 Produits indexés: {len(engine.products_df_indexed)}")
            logger.info(f"📐 Dimensions embeddings: {engine.product_embeddings.shape}")
            logger.info(f"🏷️  Catégories détectées: {engine.products_df_indexed['secondary_category'].value_counts().to_dict()}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vectorisation: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # 7. Test du moteur
    logger.info("🧪 Test du moteur avec une requête simple...")
    try:
        test_query = "Aqua, Niacinamide, Zinc PCA"
        results = engine.find_similar_products(test_query, top_n=3)
        
        if results:
            logger.info(f"✅ Test réussi: {len(results)} résultats trouvés")
            for i, r in enumerate(results, 1):
                logger.info(f"   {i}. {r['brand_name']} - {r['product_name']} (similarité: {r['similarity']:.3f})")
        else:
            logger.warning("⚠️  Aucun résultat trouvé pour la requête test")
            
    except Exception as e:
        logger.error(f"❌ Erreur test moteur: {e}")
    
    # 8. Sauvegarde
    output_path = "pure_skin_engine.pt"
    logger.info(f"💾 Sauvegarde du moteur vers {output_path}...")
    
    try:
        engine.save_engine(output_path)
        logger.info(f"✅ Moteur sauvegardé avec succès")
        
        # Sauvegarder les infos du dataset
        save_dataset_info(df_opt, Path("."))
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde moteur: {e}")
        logger.error(traceback.format_exc())
    
    # 9. Rapport final
    logger.info("\n" + "="*60)
    logger.info("🎉 INITIALISATION TERMINÉE AVEC SUCCÈS!")
    logger.info("="*60)
    
    logger.info("\n📁 FICHIERS GÉNÉRÉS:")
    logger.info(f"   - {output_path}: Fichier du moteur sauvegardé")
    logger.info(f"   - engine_init.log: Logs d'initialisation")
    logger.info(f"   - dataset_info.json: Informations du dataset")
    
    logger.info("\n🚀 PROCHAINES ÉTAPES:")
    logger.info("   1. Exécuter main.py pour démarrer l'API")
    logger.info("   2. Tester avec run_benchmark.py pour évaluer la performance")
    logger.info("   3. Utiliser debug_search.py pour le débogage")
    
    logger.info("\n⚙️  CONFIGURATION RECOMMANDÉE:")
    logger.info("   - CPU: 4+ cores recommandés")
    logger.info("   - RAM: 8+ GB recommandés")
    logger.info("   - Stockage: 1+ GB libre pour les embeddings")
    
    logger.info("\n🔧 POUR AMÉLIORER LES PERFORMANCES:")
    logger.info("   - Ajouter plus de produits au dataset")
    logger.info("   - Améliorer la qualité des données")
    logger.info("   - Ajuster les paramètres de pondération dans nlp_engine.py")

def check_system_resources():
    """Vérifie les ressources système disponibles"""
    import psutil
    import platform
    
    logger.info("💻 VÉRIFICATION DES RESSOURCES SYSTÈME")
    
    # Mémoire
    memory = psutil.virtual_memory()
    logger.info(f"   RAM totale: {memory.total / 1024**3:.1f} GB")
    logger.info(f"   RAM disponible: {memory.available / 1024**3:.1f} GB")
    logger.info(f"   Utilisation RAM: {memory.percent}%")
    
    # CPU
    cpu_count = psutil.cpu_count()
    logger.info(f"   Cœurs CPU: {cpu_count}")
    
    # Système
    logger.info(f"   Système: {platform.system()} {platform.release()}")
    logger.info(f"   Python: {platform.python_version()}")
    
    # Recommandations
    if memory.total < 8 * 1024**3:  # < 8GB
        logger.warning("⚠️  RAM limitée détectée (< 8GB)")
        logger.warning("   Recommandation: Limiter la taille du dataset")
    elif memory.available < 2 * 1024**3:  # < 2GB disponible
        logger.warning("⚠️  Peu de RAM disponible")
    
    if cpu_count < 4:
        logger.warning("⚠️  CPU limité détecté (< 4 cœurs)")
        logger.warning("   La vectorisation peut être lente")

if __name__ == "__main__":
    # Vérifier les ressources avant de commencer
    try:
        check_system_resources()
    except ImportError:
        logger.warning("psutil non installé, vérification système limitée")
    
    # Exécuter l'initialisation
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Initialisation interrompue par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Erreur fatale: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)