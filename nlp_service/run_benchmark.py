from nlp_engine import PureSkinNLPEngine
import json
import time
import numpy as np
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_test_cases(test_file: str = 'test_data.json') -> list:
    """Charge les cas de test depuis un fichier JSON"""
    test_path = Path(test_file)
    
    if not test_path.exists():
        logger.error(f"Fichier de test {test_file} introuvable")
        # Retourner des cas de test par défaut
        return [
            {
                "query_name": "Niacinamide 10% + Zinc 1%",
                "ingredients": "Aqua, Niacinamide, Pentylene Glycol, Zinc PCA, Tamarindus Indica Seed Gum, Xanthan Gum, Isoceteth-20, Ethoxydiglycol, Phenoxyethanol, Chlorphenesin",
                "expected_dupe": "The Ordinary",
                "category": "serum"
            }
        ]
    
    try:
        with open(test_path, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        logger.info(f"✅ {len(test_cases)} cas de test chargés depuis {test_file}")
        return test_cases
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Erreur de chargement: {e}")
        return []

def calculate_search_metrics(engine: PureSkinNLPEngine, test_cases: list) -> dict:
    """Calcule les métriques de performance de recherche"""
    
    metrics = {
        "latencies": [],
        "ranks": [],
        "similarities": [],
        "top_1_hits": 0,
        "top_3_hits": 0,
        "top_5_hits": 0,
        "top_10_hits": 0,
        "not_found": 0,
        "failed_searches": 0
    }
    
    if not test_cases:
        logger.warning("Aucun cas de test disponible")
        return metrics
    
    logger.info(f"\n🚀 DÉBUT DU BENCHMARK SUR {len(test_cases)} PRODUITS")
    logger.info("-" * 60)
    
    for idx, case in enumerate(test_cases, 1):
        query_name = case.get('query_name', f'Test {idx}')
        ingredients = case.get('ingredients', '')
        expected = case.get('expected_dupe', '')
        category = case.get('category', None)
        
        logger.debug(f"Traitement cas {idx}: {query_name}")
        
        if not ingredients:
            logger.warning(f"Cas {idx} ignoré: pas d'ingrédients")
            continue
        
        # Mesure de la latence
        start_time = time.perf_counter()
        
        try:
            # Recherche avec catégorie si spécifiée
            results = engine.find_similar_products(
                target_ingredients=ingredients,
                secondary=category,
                top_n=10
            )
            
            duration = (time.perf_counter() - start_time) * 1000  # ms
            metrics["latencies"].append(duration)
            
        except Exception as e:
            logger.error(f"Erreur recherche cas {idx}: {e}")
            metrics["latencies"].append(float('inf'))
            metrics["failed_searches"] += 1
            results = []
            continue
        
        # Recherche du produit attendu
        expected_clean = expected.lower()
        found_rank = 0
        found_similarity = 0.0
        
        for i, res in enumerate(results, 1):
            full_name = f"{res.get('brand_name', '')} {res.get('product_name', '')}".lower()
            
            # Recherche par nom de marque ou produit
            if expected_clean in full_name or expected_clean in res.get('brand_name', '').lower():
                found_rank = i
                found_similarity = res.get('similarity', 0.0)
                break
        
        # Enregistrement des résultats
        if found_rank > 0:
            metrics["ranks"].append(1.0 / found_rank)
            metrics["similarities"].append(found_similarity)
            
            # Mise à jour des compteurs
            if found_rank == 1: 
                metrics["top_1_hits"] += 1
            if found_rank <= 3: 
                metrics["top_3_hits"] += 1
            if found_rank <= 5: 
                metrics["top_5_hits"] += 1
            if found_rank <= 10: 
                metrics["top_10_hits"] += 1
            
            icon = "🥇" if found_rank == 1 else "🥈" if found_rank <= 3 else "🥉" if found_rank <= 5 else "✅"
            logger.info(f"{icon} '{query_name}' -> Trouvé au rang #{found_rank} (similarité: {found_similarity:.3f})")
        else:
            metrics["ranks"].append(0.0)
            metrics["not_found"] += 1
            logger.info(f"❌ '{query_name}' -> Non trouvé dans le Top 10")
    
    return metrics

def generate_report(metrics: dict, test_cases: list) -> None:
    """Génère un rapport détaillé du benchmark"""
    
    total_cases = len(test_cases)
    if total_cases == 0:
        logger.error("Aucun cas traité")
        return
    
    # Calcul des métriques
    mrr_score = np.mean(metrics["ranks"]) if metrics["ranks"] else 0
    
    acc_top1 = (metrics["top_1_hits"] / total_cases) * 100
    acc_top3 = (metrics["top_3_hits"] / total_cases) * 100
    acc_top5 = (metrics["top_5_hits"] / total_cases) * 100
    acc_top10 = (metrics["top_10_hits"] / total_cases) * 100
    
    # Latence (filtrer les valeurs infinies)
    valid_latencies = [lat for lat in metrics["latencies"] if lat != float('inf')]
    avg_latency = np.mean(valid_latencies) if valid_latencies else 0
    latency_std = np.std(valid_latencies) if valid_latencies else 0
    latency_p95 = np.percentile(valid_latencies, 95) if valid_latencies else 0
    
    # Similarité moyenne
    avg_similarity = np.mean(metrics["similarities"]) if metrics["similarities"] else 0
    
    # Rapport
    logger.info("\n" + "="*50)
    logger.info("📊 RÉSULTATS DE PERFORMANCE PURESKIN")
    logger.info("="*50)
    
    logger.info(f"📈 STATISTIQUES GÉNÉRALES")
    logger.info(f"   Cas de test : {total_cases}")
    logger.info(f"   Recherches échouées : {metrics['failed_searches']}")
    logger.info(f"   Produits non trouvés : {metrics['not_found']} ({metrics['not_found']/total_cases*100:.1f}%)")
    
    logger.info(f"\n⚡ PERFORMANCE TEMPORELLE")
    logger.info(f"   ⏱️  Latence moyenne : {avg_latency:.2f} ms")
    logger.info(f"   📊 Écart-type : {latency_std:.2f} ms")
    logger.info(f"   📈 P95 (95% des requêtes) : {latency_p95:.2f} ms")
    
    logger.info(f"\n🏆 QUALITÉ DE LA RECHERCHE")
    logger.info(f"   🎯 MRR Score : {mrr_score:.3f} / 1.000")
    logger.info(f"     - > 0.5 : Excellent")
    logger.info(f"     - 0.3-0.5 : Bon")
    logger.info(f"     - 0.1-0.3 : Moyen")
    logger.info(f"     - < 0.1 : Faible")
    
    logger.info(f"\n🎯 PRÉCISION PAR RANG")
    logger.info(f"   🥇 Top-1 Accuracy : {acc_top1:.1f}%")
    logger.info(f"   🥈 Top-3 Accuracy : {acc_top3:.1f}%")
    logger.info(f"   🥉 Top-5 Accuracy : {acc_top5:.1f}%")
    logger.info(f"   ✅ Top-10 Accuracy : {acc_top10:.1f}%")
    
    logger.info(f"\n🤝 QUALITÉ DES CORRESPONDANCES")
    logger.info(f"   Similarité moyenne : {avg_similarity:.3f}")
    logger.info(f"   - > 0.8 : Correspondance excellente")
    logger.info(f"   - 0.6-0.8 : Bonne correspondance")
    logger.info(f"   - 0.4-0.6 : Correspondance modérée")
    logger.info(f"   - < 0.4 : Correspondance faible")
    
    # Score global
    overall_score = (mrr_score + acc_top1/100 + avg_similarity) / 3
    logger.info(f"\n⭐ SCORE GLOBAL : {overall_score:.3f}/1.000")
    
    logger.info("="*50)
    
    # Sauvegarde des résultats
    save_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_cases": total_cases,
        "performance": {
            "mrr": mrr_score,
            "accuracy": {
                "top1": acc_top1,
                "top3": acc_top3,
                "top5": acc_top5,
                "top10": acc_top10
            },
            "latency_ms": {
                "mean": avg_latency,
                "std": latency_std,
                "p95": latency_p95
            },
            "similarity_mean": avg_similarity
        },
        "coverage": {
            "not_found": metrics["not_found"],
            "failed_searches": metrics["failed_searches"],
            "success_rate": 100 - ((metrics["not_found"] + metrics["failed_searches"]) / total_cases * 100)
        },
        "overall_score": overall_score
    }
    
    try:
        results_file = "benchmark_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(save_results, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Résultats sauvegardés dans {results_file}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde résultats: {e}")

def main():
    """Fonction principale du benchmark"""
    
    # 1. Chargement du moteur
    logger.info("⏳ Chargement du moteur...")
    try:
        engine = PureSkinNLPEngine()
        engine_path = "pure_skin_engine.pt"
        
        if Path(engine_path).exists():
            engine.load_engine(engine_path)
            logger.info(f"✅ Moteur chargé: {len(engine.products_df_indexed)} produits")
        else:
            logger.error(f"❌ Fichier {engine_path} introuvable")
            logger.info("Tentative de chargement direct depuis CSV...")
            csv_path = Path("product_info_cleaned.csv")
            if csv_path.exists():
                import pandas as pd
                df = pd.read_csv(csv_path)
                engine.load_and_vectorize_data(df)
                logger.info(f"✅ Données chargées depuis CSV: {len(df)} produits")
            else:
                logger.error("❌ Aucune donnée disponible")
                return
    except Exception as e:
        logger.error(f"❌ Erreur chargement moteur: {e}")
        return
    
    # 2. Chargement des cas de test
    test_cases = load_test_cases('test_data.json')
    
    if not test_cases:
        logger.warning("Utilisation de cas de test par défaut...")
        test_cases = [
            {
                "query_name": "Test Standard",
                "ingredients": "Aqua, Glycerin, Niacinamide, Hyaluronic Acid",
                "expected_dupe": "The Ordinary",
                "category": "serum"
            }
        ]
    
    # 3. Exécution du benchmark
    logger.info(f"🔍 Exécution du benchmark sur {len(test_cases)} cas...")
    metrics = calculate_search_metrics(engine, test_cases)
    
    # 4. Génération du rapport
    generate_report(metrics, test_cases)
    
    # 5. Message final
    logger.info("\n✨ Benchmark terminé avec succès!")
    logger.info("💡 Conseils pour améliorer les résultats:")
    logger.info("   - Augmenter la qualité des données d'entraînement")
    logger.info("   - Ajouter plus de cas de test variés")
    logger.info("   - Ajuster les paramètres de pondération dans clean_and_weight_ingredients()")
    logger.info("   - Considérer l'ajout de features supplémentaires (prix, marque, etc.)")

if __name__ == "__main__":
    main()