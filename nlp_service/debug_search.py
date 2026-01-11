from nlp_engine import PureSkinNLPEngine
import pandas as pd
import re
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_engine_loading():
    """Teste le chargement du moteur"""
    
    print("\n" + "="*50)
    print("🔍 DEBUG - CHARGEMENT DU MOTEUR")
    print("="*50)
    
    # 1. Charger le moteur
    try:
        engine = PureSkinNLPEngine()
        engine_path = "pure_skin_engine.pt"
        
        print(f"📂 Tentative de chargement depuis {engine_path}...")
        engine.load_engine(engine_path)
        
        print(f"✅ Moteur chargé avec succès")
        print(f"📊 Total produits en base: {len(engine.products_df_indexed)}")
        
        # Afficher quelques statistiques
        if engine.products_df_indexed is not None:
            df = engine.products_df_indexed
            print(f"🏷️  Marques uniques: {df['brand_name'].nunique()}")
            print(f"📁 Catégories primaires: {df['primary_category'].value_counts().to_dict()}")
            print(f"📁 Catégories secondaires: {df['secondary_category'].value_counts().head(10).to_dict()}")
            
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return None
    
    return engine

def debug_product_search(engine, brand_pattern="Revolution", product_pattern="Niacinamide"):
    """Recherche un produit spécifique dans la base"""
    
    print(f"\n" + "="*50)
    print(f"🔎 DEBUG - RECHERCHE DE PRODUIT")
    print("="*50)
    
    if engine.products_df_indexed is None:
        print("❌ Base de données non chargée")
        return
    
    df = engine.products_df_indexed
    
    # Recherche insensible à la casse
    brand_mask = df['brand_name'].astype(str).str.contains(brand_pattern, case=False, na=False)
    product_mask = df['product_name'].astype(str).str.contains(product_pattern, case=False, na=False)
    
    matches = df[brand_mask & product_mask]
    
    if matches.empty:
        print(f"❌ Aucun produit trouvé avec marque '{brand_pattern}' et nom '{product_pattern}'")
        
        # Recherche élargie
        print("\n🔍 Recherche élargie...")
        brand_only = df[brand_mask]
        product_only = df[product_mask]
        
        if not brand_only.empty:
            print(f"📦 Produits de la marque '{brand_pattern}':")
            for _, row in brand_only.head(5).iterrows():
                print(f"   - '{row['product_name']}' (Cat: {row.get('secondary_category', 'N/A')})")
        
        if not product_only.empty:
            print(f"\n📦 Produits contenant '{product_pattern}':")
            for _, row in product_only.head(5).iterrows():
                print(f"   - {row['brand_name']}: '{row['product_name']}' (Cat: {row.get('secondary_category', 'N/A')})")
        
        # Suggestions de marques similaires
        print(f"\n💡 Suggestions de marques:")
        all_brands = df['brand_name'].astype(str).unique()
        similar_brands = [b for b in all_brands if brand_pattern.lower() in b.lower()]
        if similar_brands:
            for brand in similar_brands[:5]:
                print(f"   - {brand}")
    else:
        print(f"✅ {len(matches)} produit(s) trouvé(s):")
        for idx, (_, row) in enumerate(matches.iterrows(), 1):
            print(f"\n{idx}. {row['brand_name']} - {row['product_name']}")
            print(f"   Catégorie: {row.get('primary_category', 'N/A')} > {row.get('secondary_category', 'N/A')}")
            print(f"   Prix: ${row.get('price_usd', 'N/A')}")
            print(f"   Rating: {row.get('rating', 'N/A')} ({row.get('reviews', 0)} avis)")
            
            # Afficher un aperçu des ingrédients
            ingredients = str(row.get('ingredients', ''))
            if len(ingredients) > 100:
                ingredients = ingredients[:100] + "..."
            print(f"   Ingrédients: {ingredients}")

def debug_vector_search(engine, query_ingredients, category="serum"):
    """Teste la recherche vectorielle"""
    
    print(f"\n" + "="*50)
    print(f"🧪 DEBUG - RECHERCHE VECTORIELLE")
    print("="*50)
    
    if engine.product_embeddings is None:
        print("❌ Embeddings non disponibles")
        return
    
    print(f"🔍 Requête: {query_ingredients[:100]}...")
    print(f"📁 Catégorie filtrée: {category}")
    
    # Recherche
    try:
        results = engine.find_similar_products(
            target_ingredients=query_ingredients,
            secondary=category,
            top_n=10
        )
        
        if not results:
            print("❌ Aucun résultat trouvé")
            # Essayer sans filtre de catégorie
            print("\n🔍 Essai sans filtre de catégorie...")
            results = engine.find_similar_products(
                target_ingredients=query_ingredients,
                secondary=None,
                top_n=10
            )
        
        if results:
            print(f"✅ {len(results)} résultat(s) trouvé(s):")
            for i, r in enumerate(results, 1):
                print(f"\n{i}. [{r['similarity']:.3f}] {r['brand_name']} - {r['product_name']}")
                print(f"   💰 Prix: ${r['price']:.2f}")
                print(f"   ⭐ Rating: {r.get('rating', 'N/A')}")
                print(f"   📁 Catégorie: {r.get('secondary_category', 'N/A')}")
                
                # Identifier si c'est un bon match
                if r['similarity'] > 0.8:
                    match_quality = "EXCELLENT"
                elif r['similarity'] > 0.6:
                    match_quality = "BON"
                elif r['similarity'] > 0.4:
                    match_quality = "MODÉRÉ"
                else:
                    match_quality = "FAIBLE"
                print(f"   🎯 Qualité match: {match_quality}")
        else:
            print("❌ Aucun résultat même sans filtre")
            
    except Exception as e:
        print(f"❌ Erreur lors de la recherche: {e}")

def debug_embeddings_analysis(engine):
    """Analyse les embeddings"""
    
    print(f"\n" + "="*50)
    print(f"🔬 DEBUG - ANALYSE DES EMBEDDINGS")
    print("="*50)
    
    if engine.product_embeddings is None:
        print("❌ Embeddings non disponibles")
        return
    
    print(f"📐 Dimensions embeddings: {engine.product_embeddings.shape}")
    print(f"   - Produits: {engine.product_embeddings.shape[0]}")
    print(f"   - Dimensions: {engine.product_embeddings.shape[1]}")
    
    # Aperçu des premiers embeddings
    print(f"\n👀 Aperçu embeddings (3 premiers produits):")
    for i in range(min(3, len(engine.products_df_indexed))):
        product_name = engine.products_df_indexed.iloc[i]['product_name']
        embedding = engine.product_embeddings[i]
        print(f"   {i+1}. {product_name[:50]}...")
        print(f"      Embedding: [{embedding[0]:.4f}, {embedding[1]:.4f}, ..., {embedding[-1]:.4f}]")

def main():
    """Fonction principale de debug"""
    
    print("🛠️  DÉMARRAGE DU DEBUG PURESKIN ENGINE")
    print("="*50)
    
    # 1. Test de chargement
    engine = debug_engine_loading()
    if engine is None:
        return
    
    # 2. Recherche d'un produit spécifique
    debug_product_search(engine, "Revolution", "Niacinamide")
    
    # 3. Recherche vectorielle
    query = "Aqua, Niacinamide, Pentylene Glycol, Zinc PCA, Dimethyl Isosorbide"
    debug_vector_search(engine, query, "serum")
    
    # 4. Analyse des embeddings
    debug_embeddings_analysis(engine)
    
    # 5. Test de performance
    print(f"\n" + "="*50)
    print(f"⚡ DEBUG - TEST DE PERFORMANCE")
    print("="*50)
    
    import time
    test_queries = [
        "Aqua, Niacinamide, Zinc PCA",
        "Glycerin, Hyaluronic Acid, Sodium Hyaluronate",
        "Water, Salicylic Acid, Witch Hazel"
    ]
    
    for i, query in enumerate(test_queries, 1):
        start = time.perf_counter()
        results = engine.find_similar_products(query, top_n=5)
        duration = (time.perf_counter() - start) * 1000
        
        print(f"Query {i} ({len(query)} chars): {duration:.2f} ms, {len(results)} résultats")
    
    print(f"\n✨ Debug terminé avec succès!")
    print("💡 Prochaines étapes:")
    print("   - Vérifier la qualité des données dans product_info_cleaned.csv")
    print("   - Ajouter plus de produits à la base")
    print("   - Ajuster les paramètres de similarité")
    print("   - Tester avec différents types de requêtes")

if __name__ == "__main__":
    main()