# ocr_service.py
# Version: 7.3 - Geometric Strict (Zone Top = Brand, Zone Mid = Product)

import os
import re
import shutil
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional
import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

# =========================
# 0) CONFIGURATION
# =========================
def _setup_tesseract() -> bool:
    try:
        cmd = shutil.which("tesseract")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
            return True
        if os.name == "nt":
            candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for p in candidates:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    return True
    except Exception:
        pass
    return False

_setup_tesseract()

# =========================
# 1) CHARGEMENT DB
# =========================
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "product_info_cleaned.csv")
DF = pd.DataFrame()

try:
    if os.path.exists(DB_PATH):
        DF = pd.read_csv(DB_PATH)
        DF.columns = [c.strip() for c in DF.columns]
except Exception as e:
    print(f"Erreur DB: {e}")

# Colonnes
COL_PRODUCT = next((c for c in DF.columns if c in ["product_name", "name"]), None)
COL_BRAND = next((c for c in DF.columns if c in ["brand_name", "brand"]), None)
COL_RATING = next((c for c in DF.columns if c in ["rating", "stars"]), None)
COL_PRICE = next((c for c in DF.columns if c in ["price_usd", "price"]), None)

# =========================
# 2) OUTILS
# =========================
def norm(s: str) -> str:
    if not isinstance(s, str): return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())

# Mots à ignorer absolument (Bruit)
NOISE_WORDS = {"ml", "fl", "oz", "net", "wt", "vol", "paris", "london", "new", "york", "usa", "made", "in"}

# =========================
# 3) PRE-TRAITEMENT IMAGE
# =========================
def preprocess_image(image: Image.Image) -> Image.Image:
    """Standardise l'image pour que les calculs de position soient fiables"""
    img = image.convert("RGB")
    
    # On redimensionne à une hauteur fixe (2000px) pour avoir des repères stables
    target_height = 2000
    ratio = target_height / img.height
    new_width = int(img.width * ratio)
    img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
    
    gray = img.convert("L")
    
    # Amélioration contraste
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)
    
    # Netteté
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # Si l'image est très sombre (fond noir), on inverse
    stat = ImageOps.grayscale(img).getextrema()
    # Calculer la moyenne des pixels
    np_img = np.array(gray)
    if np.mean(np_img) < 100: # Image sombre
        gray = ImageOps.invert(gray)

    return gray

# =========================
# 4) OCR GEOMETRIQUE STRICT
# =========================
def get_lines_with_geometry(image: Image.Image) -> List[Dict]:
    """Extrait le texte avec sa position Y (hauteur)"""
    processed = preprocess_image(image)
    
    # On demande des Data (coordonnées) pas juste du String
    try:
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT, config='--psm 3')
    except:
        # Fallback si tesseract plante
        return []

    lines = {}
    n_boxes = len(data['text'])
    
    for i in range(n_boxes):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        
        if not text or conf < 40: continue
        
        # On groupe par ligne (Block + Ligne)
        key = (data['block_num'][i], data['line_num'][i])
        
        if key not in lines:
            lines[key] = {
                'text_parts': [],
                'y': data['top'][i],       # Position Y (Haut -> Bas)
                'h': data['height'][i],    # Taille de la police
                'w': data['width'][i]
            }
        
        lines[key]['text_parts'].append(text)
        # On garde la hauteur max de la ligne (taille de police)
        lines[key]['h'] = max(lines[key]['h'], data['height'][i])

    # Consolidation
    final_lines = []
    img_height = processed.height # Devrait être 2000
    
    for k, v in lines.items():
        full_text = " ".join(v['text_parts']).strip()
        if len(full_text) < 3: continue
        
        # Calcul de la position relative (0.0 = Tout en haut, 1.0 = Tout en bas)
        rel_y = v['y'] / img_height
        
        final_lines.append({
            'text': full_text,
            'rel_y': rel_y,      # Position relative
            'font_size': v['h'], # Taille police
            'raw': v
        })
        
    return final_lines

def analyze_layout_strict(lines: List[Dict]) -> Dict:
    """
    Applique la règle stricte : 
    - Zone 0.0 à 0.30 : MARQUE
    - Zone 0.30 à 0.75 : PRODUIT
    """
    brand_candidates = []
    product_candidates = []
    
    # Filtrage du bruit (Volume, etc.)
    clean_lines = []
    for l in lines:
        words = set(re.findall(r'\w+', l['text'].lower()))
        if words.intersection(NOISE_WORDS): continue # C'est du bruit (50ml etc)
        clean_lines.append(l)

    # 1. Remplir les zones
    for l in clean_lines:
        text = l['text']
        y = l['rel_y']
        size = l['font_size']
        
        # ZONE MARQUE (Haut)
        if y < 0.30: 
            # Bonus si c'est en haut
            score = size * 1.5 
            brand_candidates.append({'text': text, 'score': score})
            
        # ZONE PRODUIT (Milieu)
        elif 0.30 <= y < 0.75:
            # Bonus si c'est écrit gros
            score = size * 2.0
            product_candidates.append({'text': text, 'score': score})

    # 2. Sélection MARQUE
    # On prend le candidat avec le meilleur score dans la zone haute
    brand_candidates.sort(key=lambda x: x['score'], reverse=True)
    best_brand = "Unknown"
    if brand_candidates:
        best_brand = brand_candidates[0]['text']

    # 3. Sélection PRODUIT
    # On prend les 2 lignes les plus grosses dans la zone milieu
    product_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    best_product_parts = []
    for pc in product_candidates[:2]: # Max 2 lignes pour le nom
        best_product_parts.append(pc['text'])
    
    best_product = " ".join(best_product_parts) if best_product_parts else "Unknown Product"

    # Si on a rien trouvé au milieu, on cherche juste le texte le plus gros globalement (hors marque)
    if best_product == "Unknown Product" and clean_lines:
        sorted_by_size = sorted(clean_lines, key=lambda x: x['font_size'], reverse=True)
        for l in sorted_by_size:
            if l['text'] != best_brand:
                best_product = l['text']
                break

    return {
        "brand": best_brand,
        "product": best_product
    }

# =========================
# 5) MATCHING DB
# =========================
def find_in_db_fuzzy(brand: str, product: str) -> Dict:
    if DF.empty: return {"found": False}
    
    # 1. Filtrer par marque (si trouvée)
    subset = DF
    if brand != "Unknown" and COL_BRAND:
        brand_norm = norm(brand)
        # On cherche une marque qui ressemble dans la DB
        # Astuce : on vérifie si les 4 premiers caractères matchent pour filtrer vite
        mask = DF[COL_BRAND].astype(str).apply(norm).str.contains(brand_norm[:4], regex=False)
        if mask.any():
            subset = DF[mask]

    # 2. Chercher le produit dans ce subset
    best_score = 0
    best_row = None
    product_norm = norm(product)

    for idx, row in subset.iterrows():
        db_name = norm(str(row[COL_PRODUCT]))
        # Similarité sur le nom du produit
        score = SequenceMatcher(None, product_norm, db_name).ratio()
        
        if score > best_score:
            best_score = score
            best_row = row

    threshold = 0.45 # Seuil tolérant car l'OCR peut faire des erreurs
    if best_score > threshold:
        return {
            "found": True,
            "product_name": best_row[COL_PRODUCT],
            "brand": best_row[COL_BRAND] if COL_BRAND else brand,
            "rating": best_row[COL_RATING] if COL_RATING else None,
            "price": best_row[COL_PRICE] if COL_PRICE else None,
            "match_score": round(best_score, 2)
        }
    
    return {"found": False}

# =========================
# 6) MAIN API ENTRY
# =========================
def extract_product_info_enhanced(image: Image.Image, debug_mode: bool = False) -> Dict:
    try:
        # 1. OCR avec géométrie
        lines = get_lines_with_geometry(image)
        
        if not lines:
            return {"success": False, "error": "Image illisible"}

        # 2. Analyse Zones (Haut vs Milieu)
        info = analyze_layout_strict(lines)
        
        # 3. DB Match
        match = find_in_db_fuzzy(info['brand'], info['product'])

        result = {
            "success": True,
            "ocr_type": "geometric_strict",
            "brand": match.get('brand', info['brand']),
            "product_name": match.get('product_name', info['product']),
            "rating": match.get('rating'),
            "price_usd": match.get('price'),
            "match_score": match.get('match_score', 0)
        }

        if debug_mode:
            result['debug_ocr'] = lines[:5]
            
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}