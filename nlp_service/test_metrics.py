import time
import numpy as np
from sklearn.metrics import silhouette_score, pairwise_distances
import torch
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PureSkinBenchmark:
    def __init__(self, engine):
        self.engine = engine
        self.metrics_history = []
    
    def run_search_benchmark(self, test_cases: List[Dict]) -> Dict[str, Any]:
        """
        Exécute un benchmark complet de recherche
        
        Args:
            test_cases: Liste de dictionnaires avec:
                - 'query_ing': Ingrédients de recherche
                - 'expected_product': Nom du produit attendu
                - 'category': Catégorie optionnelle
                - 'price': Prix optionnel
        """
        
        metrics = {
            "latencies": [],
            "ranks": [],
            "top_1_hits": 0,
            "top_3_hits": 0,
            "top_5_hits": 0,
            "top_10_hits": 0,
            "not_found": 0,
            "similarity_scores": [],
            "precision_at_k": {1: 0, 3: 0, 5: 0, 10: 0}
        }
        
        if not test_cases:
            logger.warning("Aucun cas de test fourni")
            return metrics
        
        logger.info(f"🚀 Début du benchmark sur {len(test_cases)} cas de test")
        logger.info("-" * 60)
        
        for idx, case in enumerate(test_cases, 1):
            query_name = case.get('query_name', f'Test {idx}')
            query_ing = case.get('ingredients', case.get('query_ing', ''))
            expected = case.get('expected_dupe', case.get('expected_product', ''))
            category = case.get('category', case.get('secondary', None))
            
            if not query_ing:
                logger.warning(f"Cas {idx}: Pas d'ingrédients spécifiés")
                continue
            
            # 1. Mesure de la latence
            start_time = time.perf_counter()
            
            try:
                results = self.engine.find_similar_products(
                    target_ingredients=query_ing,
                    secondary=category,
                    top_n=10
                )
                duration = (time.perf_counter() - start_time) * 1000  # ms
                metrics["latencies"].append(duration)
            except Exception as e:
                logger.error(f"Erreur recherche cas {idx}: {e}")
                metrics["latencies"].append(float('inf'))
                results = []
            
            # 2. Analyse du rang
            expected_clean = expected.lower()
            found_rank = 0
            found_similarity = 0.0
            
            # Recherche du produit attendu dans les résultats
            for i, res in enumerate(results, 1):
                full_name = f"{res.get('brand_name', '')} {res.get('product_name', '')}".lower()
                if expected_clean in full_name:
                    found_rank = i
                    found_similarity = res.get('similarity', 0.0)
                    break
            
            # 3. Stockage des scores
            if found_rank > 0:
                metrics["ranks"].append(1.0 / found_rank)  # Reciprocal Rank
                metrics["similarity_scores"].append(found_similarity)
                
                # Mise à jour des hits par rang
                if found_rank == 1: 
                    metrics["top_1_hits"] += 1
                if found_rank <= 3: 
                    metrics["top_3_hits"] += 1
                if found_rank <= 5: 
                    metrics["top_5_hits"] += 1
                if found_rank <= 10: 
                    metrics["top_10_hits"] += 1
                
                # Icon et log
                icon = "🥇" if found_rank == 1 else "🥈" if found_rank <= 3 else "🥉" if found_rank <= 5 else "✅"
                logger.info(f"{icon} '{query_name}' -> Trouvé au rang #{found_rank} (similarité: {found_similarity:.3f})")
            else:
                metrics["ranks"].append(0.0)
                metrics["not_found"] += 1
                logger.info(f"❌ '{query_name}' -> Non trouvé dans le Top 10")
            
            # 4. Calcul de Precision@K pour ce cas
            if results:
                relevant_found = 0
                for k in [1, 3, 5, 10]:
                    if found_rank > 0 and found_rank <= k:
                        relevant_found = 1
                    else:
                        relevant_found = 0
                    metrics["precision_at_k"][k] += relevant_found
        
        # 5. Calcul des métriques finales
        total_cases = len(test_cases)
        
        # Mean Reciprocal Rank (MRR)
        mrr_score = np.mean(metrics["ranks"]) if metrics["ranks"] else 0
        
        # Precision@K
        for k in metrics["precision_at_k"]:
            metrics["precision_at_k"][k] = (metrics["precision_at_k"][k] / total_cases) * 100
        
        # Accuracy
        acc_top1 = (metrics["top_1_hits"] / total_cases) * 100 if total_cases > 0 else 0
        acc_top3 = (metrics["top_3_hits"] / total_cases) * 100 if total_cases > 0 else 0
        acc_top5 = (metrics["top_5_hits"] / total_cases) * 100 if total_cases > 0 else 0
        acc_top10 = (metrics["top_10_hits"] / total_cases) * 100 if total_cases > 0 else 0
        
        # Latence moyenne (filtrer les inf)
        valid_latencies = [lat for lat in metrics["latencies"] if lat != float('inf')]
        avg_latency = np.mean(valid_latencies) if valid_latencies else 0
        latency_std = np.std(valid_latencies) if valid_latencies else 0
        
        # Similarité moyenne des matches
        avg_similarity = np.mean(metrics["similarity_scores"]) if metrics["similarity_scores"] else 0
        
        # 6. Rapport final
        logger.info("\n" + "="*50)
        logger.info("📊 RÉSULTATS DU BENCHMARK PURESKIN")
        logger.info("="*50)
        
        logger.info(f"📈 PERFORMANCE DE RECHERCHE")
        logger.info(f"   ⏱️  Latence Moyenne : {avg_latency:.2f} ms (±{latency_std:.2f})")
        logger.info(f"   🔍 Cas traités : {total_cases}")
        logger.info(f"   ❌ Non trouvés : {metrics['not_found']} ({metrics['not_found']/total_cases*100:.1f}%)")
        
        logger.info(f"\n🎯 QUALITÉ DES RÉSULTATS")
        logger.info(f"   🏆 MRR Score : {mrr_score:.3f} / 1.000")
        logger.info(f"     - > 0.5 : Excellent")
        logger.info(f"     - 0.3-0.5 : Bon")
        logger.info(f"     - < 0.3 : À améliorer")
        
        logger.info(f"\n📊 PRÉCISION PAR RANG")
        logger.info(f"   🥇 Top-1 Accuracy : {acc_top1:.1f}%")
        logger.info(f"   🥈 Top-3 Accuracy : {acc_top3:.1f}%")
        logger.info(f"   🥉 Top-5 Accuracy : {acc_top5:.1f}%")
        logger.info(f"   ✅ Top-10 Accuracy : {acc_top10:.1f}%")
        
        logger.info(f"\n🎯 PRECISION@K")
        for k, score in metrics["precision_at_k"].items():
            logger.info(f"   P@{k}: {score:.1f}%")
        
        logger.info(f"\n🤝 QUALITÉ DES MATCHES")
        logger.info(f"   Similarité moyenne : {avg_similarity:.3f}")
        
        logger.info("="*50)
        
        # Stocker les résultats pour l'historique
        benchmark_result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mrr": mrr_score,
            "top1_accuracy": acc_top1,
            "top5_accuracy": acc_top5,
            "avg_latency": avg_latency,
            "test_cases": total_cases,
            "not_found": metrics["not_found"]
        }
        self.metrics_history.append(benchmark_result)
        
        return {
            "summary": {
                "mrr_score": mrr_score,
                "accuracy": {
                    "top1": acc_top1,
                    "top3": acc_top3,
                    "top5": acc_top5,
                    "top10": acc_top10
                },
                "precision_at_k": metrics["precision_at_k"],
                "latency_ms": {
                    "mean": avg_latency,
                    "std": latency_std
                },
                "similarity": {
                    "mean": avg_similarity
                },
                "coverage": {
                    "total_cases": total_cases,
                    "not_found": metrics["not_found"],
                    "coverage_rate": 100 - (metrics["not_found"] / total_cases * 100) if total_cases > 0 else 0
                }
            },
            "detailed_metrics": metrics
        }
    
    def calculate_semantic_quality(self) -> Dict[str, Any]:
        """Calcule la qualité sémantique des embeddings"""
        if self.engine.product_embeddings is None:
            return {"error": "Embeddings non disponibles"}
        
        try:
            # Transformer les tensors en numpy
            embeddings = self.engine.product_embeddings.cpu().numpy()
            
            # Vérifier la présence des catégories
            if 'secondary_category' not in self.engine.products_df_indexed.columns:
                return {"error": "Colonne secondary_category non trouvée"}
            
            labels = self.engine.products_df_indexed['secondary_category'].values
            
            # Filtrer les labels invalides
            valid_mask = (labels != 'unknown') & (labels != 'nan') & (labels != '') & (~pd.isna(labels))
            
            if valid_mask.sum() < 2:
                return {"error": "Pas assez de données valides"}
            
            # Silhouette Score
            silhouette = silhouette_score(embeddings[valid_mask], labels[valid_mask])
            
            # Calculer la séparation inter/intra cluster
            unique_labels = np.unique(labels[valid_mask])
            intra_distances = []
            inter_distances = []
            
            for label in unique_labels:
                # Distances intra-cluster
                label_mask = labels[valid_mask] == label
                if np.sum(label_mask) > 1:
                    label_embeddings = embeddings[valid_mask][label_mask]
                    intra_dist = pairwise_distances(label_embeddings).mean()
                    intra_distances.append(intra_dist)
                
                # Distances inter-cluster (moyenne avec un autre cluster)
                for other_label in unique_labels:
                    if other_label != label:
                        other_mask = labels[valid_mask] == other_label
                        if np.sum(other_mask) > 0:
                            other_embeddings = embeddings[valid_mask][other_mask]
                            sample_size = min(10, len(label_embeddings), len(other_embeddings))
                            if sample_size > 0:
                                # Échantillonner pour la performance
                                idx1 = np.random.choice(len(label_embeddings), sample_size, replace=False)
                                idx2 = np.random.choice(len(other_embeddings), sample_size, replace=False)
                                inter_dist = pairwise_distances(
                                    label_embeddings[idx1], 
                                    other_embeddings[idx2]
                                ).mean()
                                inter_distances.append(inter_dist)
            
            # Ratio de séparation
            separation_ratio = np.mean(inter_distances) / np.mean(intra_distances) if intra_distances and inter_distances else 0
            
            logger.info(f"\n🧪 ANALYSE DE QUALITÉ SÉMANTIQUE")
            logger.info(f"   📊 Silhouette Score: {silhouette:.3f}")
            logger.info(f"     - > 0.7: Structure forte")
            logger.info(f"     - 0.5-0.7: Structure raisonnable")
            logger.info(f"     - 0.25-0.5: Structure faible")
            logger.info(f"     - < 0.25: Pas de structure")
            logger.info(f"   🔍 Séparation cluster: {separation_ratio:.2f}")
            logger.info(f"     - > 2.0: Bonne séparation")
            logger.info(f"     - 1.0-2.0: Séparation modérée")
            logger.info(f"     - < 1.0: Chevauchement")
            
            return {
                "silhouette_score": silhouette,
                "separation_ratio": separation_ratio,
                "clusters_count": len(unique_labels),
                "valid_samples": valid_mask.sum(),
                "intra_cluster_distance": np.mean(intra_distances) if intra_distances else 0,
                "inter_cluster_distance": np.mean(inter_distances) if inter_distances else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul qualité sémantique: {e}")
            return {"error": str(e)}
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """Génère un rapport complet de qualité"""
        semantic_quality = self.calculate_semantic_quality()
        
        # Statistiques de base
        if self.engine.products_df_indexed is not None:
            df = self.engine.products_df_indexed
            stats = {
                "total_products": len(df),
                "unique_brands": df['brand_name'].nunique(),
                "category_distribution": df['secondary_category'].value_counts().head(10).to_dict(),
                "price_stats": {
                    "mean": df['price_usd'].mean() if 'price_usd' in df.columns else 0,
                    "median": df['price_usd'].median() if 'price_usd' in df.columns else 0,
                    "std": df['price_usd'].std() if 'price_usd' in df.columns else 0
                },
                "rating_stats": {
                    "mean": df['rating'].mean() if 'rating' in df.columns else 0,
                    "median": df['rating'].median() if 'rating' in df.columns else 0
                }
            }
        else:
            stats = {}
        
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "semantic_quality": semantic_quality,
            "dataset_stats": stats,
            "benchmark_history": self.metrics_history[-5:] if len(self.metrics_history) > 5 else self.metrics_history
        }

# --- EXEMPLE D'UTILISATION ---
def run_example_benchmark():
    """Exemple d'utilisation du benchmark"""
    from nlp_engine import PureSkinNLPEngine
    
    # 1. Charger le moteur
    print("⏳ Chargement du moteur...")
    engine = PureSkinNLPEngine()
    engine.load_engine("pure_skin_engine.pt")
    
    # 2. Créer le benchmark
    benchmark = PureSkinBenchmark(engine)
    
    # 3. Données de test (exemple)
    test_data = [
        {
            "query_name": "Niacinamide Serum Test",
            "ingredients": "Aqua, Niacinamide, Zinc PCA, Tamarindus Indica Seed Gum, Xanthan Gum",
            "expected_dupe": "The Ordinary",
            "category": "serum"
        },
        {
            "query_name": "Hyaluronic Acid Serum",
            "ingredients": "Aqua, Sodium Hyaluronate, Glycerin, Propanediol",
            "expected_dupe": "The Inkey List",
            "category": "serum"
        }
    ]
    
    # 4. Exécuter le benchmark
    print("\n🧪 Exécution du benchmark...")
    results = benchmark.run_search_benchmark(test_data)
    
    # 5. Analyser la qualité sémantique
    print("\n🔍 Analyse de qualité sémantique...")
    semantic_quality = benchmark.calculate_semantic_quality()
    
    # 6. Générer un rapport complet
    print("\n📄 Génération du rapport de qualité...")
    full_report = benchmark.generate_quality_report()
    
    return results, semantic_quality, full_report

if __name__ == "__main__":
    # Exemple d'exécution
    try:
        results, semantic_quality, report = run_example_benchmark()
        
        print("\n✅ Benchmark terminé avec succès")
        print(f"📊 MRR: {results['summary']['mrr_score']:.3f}")
        print(f"🎯 Top-1 Accuracy: {results['summary']['accuracy']['top1']:.1f}%")
        
    except Exception as e:
        print(f"❌ Erreur lors du benchmark: {e}")