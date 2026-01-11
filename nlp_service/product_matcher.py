import os
import re
import shutil
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional

import pandas as pd
from PIL import Image, ImageFilter, ImageOps, ImageEnhance

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# =========================================================
# CONFIG
# =========================================================
DB_PATH = "product_info_cleaned.csv"  # mets le bon chemin si besoin

OCR_LANG = "eng+fra"
OCR_CONFIGS = [
    r"--oem 3 --psm 6",
    r"--oem 3 --psm 11",
    r"--oem 3 --psm 12",
    r"--oem 3 --psm 4",
    r"--oem 3 --psm 3",
]

INGREDIENT_MARKERS = ["INGREDIENTS", "INGRÉDIENTS", "INCI", "COMPOSITION", "CONTAINS"]
_RE_VOLUME = re.compile(r"\b\d+(\.\d+)?\s*(ML|FL\.?OZ|OZ|G|KG)\b", re.IGNORECASE)

# mots qui ne sont PAS des marques (souvent le nom de gamme / descriptif)
GENERIC_NOT_BRAND = {
    "MOISTURE", "MOISTURIZER", "MOISTURIZING", "REPLENISHING", "HYDRATING",
    "CONDITIONER", "SHAMPOO", "MASK", "CREAM", "SERUM", "LOTION", "CLEANSER",
    "ANTIAGING", "ANTI-AGING", "ANTI AGE", "REPAIR", "RESTORE", "SMOOTH",
    "VOLUME", "PROTECT", "NOURISH", "NOURISHING", "CARE", "ULTIMATE", "GLOBAL",
    "MELTING", "CLEANSE", "HAIR", "MILK", "LEAVE", "IN", "LEAVE-IN",
}

PRODUCT_HINTS = [
    "cleanser", "conditioner", "shampoo", "serum", "mask", "cream", "moisture",
    "anti aging", "anti-aging", "hydrating", "lotion", "spray", "milk", "toner",
    "leave in", "leave-in"
]


# =========================================================
# TESSERACT SETUP
# =========================================================
def setup_tesseract() -> bool:
    if not TESSERACT_AVAILABLE:
        return False

    cmd = shutil.which("tesseract")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
        return True

    if os.name == "nt":
        paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return True

    return False


# =========================================================
# DB LOAD + NORMALIZATION
# =========================================================
def norm(s: str) -> str:
    s = str(s or "").lower().strip()
    s = re.sub(r"[®™©]", "", s)
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def safe_load_db(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"DB introuvable: {path}")
    df = pd.read_csv(path)

    required = {"product_name", "brand_name", "rating"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"DB manque colonnes: {missing}. Colonnes présentes: {list(df.columns)}")

    df["product_name"] = df["product_name"].astype(str)
    df["brand_name"] = df["brand_name"].astype(str)

    df["_pn"] = df["product_name"].apply(norm)
    df["_bn"] = df["brand_name"].apply(norm)

    # optionnels
    if "price_usd" not in df.columns:
        df["price_usd"] = None
    if "primary_category" not in df.columns:
        df["primary_category"] = ""
    if "ingredients" not in df.columns:
        df["ingredients"] = ""

    return df


# charge DB une seule fois
try:
    DF = safe_load_db(DB_PATH)
    DB_READY = True
except Exception as e:
    DF = pd.DataFrame()
    DB_READY = False
    DB_LOAD_ERROR = str(e)


# =========================================================
# OCR PREPROCESS
# =========================================================
def preprocess_variants(image: Image.Image) -> List[Image.Image]:
    """
    Plusieurs variantes simples pour améliorer OCR.
    """
    variants = []
    img = image.convert("L")

    # resize stable (important)
    base_h = 1400
    if img.height < 700 or img.height > 2400:
        ratio = base_h / float(img.height)
        img = img.resize((int(img.width * ratio), base_h), Image.Resampling.LANCZOS)

    # A: sharpen + contrast
    a = img.filter(ImageFilter.UnsharpMask(radius=2, percent=190, threshold=3))
    a = ImageEnhance.Contrast(a).enhance(1.9)
    variants.append(a)

    # B: invert
    variants.append(ImageOps.invert(a))

    # C: stronger contrast
    c = ImageEnhance.Contrast(img).enhance(2.5)
    variants.append(c)

    return variants


def rotate_variants(image: Image.Image) -> List[Tuple[str, Image.Image]]:
    """
    Pour texte vertical (ex: adwoa).
    """
    return [
        ("r0", image),
        ("r90", image.rotate(90, expand=True)),
        ("r270", image.rotate(270, expand=True)),
    ]


def crop_zone(image: Image.Image, y0: float, y1: float) -> Image.Image:
    w, h = image.size
    return image.crop((0, int(h * y0), w, int(h * y1)))


def clean_token(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s\-\.'’%®™©À-ÿ]", "", t)
    return t.strip()


# =========================================================
# OCR -> LINES (word boxes -> grouped lines)
# =========================================================
def ocr_words(img: Image.Image, config: str, lang: str = OCR_LANG) -> List[Dict]:
    data = pytesseract.image_to_data(
        img,
        config=config,
        lang=lang,
        output_type=pytesseract.Output.DICT
    )
    words = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = clean_token(data["text"][i])
        if not txt:
            continue
        try:
            conf = float(data["conf"][i])
        except:
            conf = -1.0
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append({"text": txt, "conf": conf, "x": x, "y": y, "w": w, "h": h})
    return words


def group_words_into_lines(words: List[Dict], y_tol: int = 14) -> List[Dict]:
    if not words:
        return []
    words = sorted(words, key=lambda d: (d["y"], d["x"]))

    groups = []
    cur = [words[0]]
    for w in words[1:]:
        if abs(w["y"] - cur[-1]["y"]) <= y_tol:
            cur.append(w)
        else:
            groups.append(cur)
            cur = [w]
    groups.append(cur)

    lines = []
    for g in groups:
        g = sorted(g, key=lambda d: d["x"])
        text = " ".join(w["text"] for w in g).strip()
        if not text:
            continue
        confs = [w["conf"] for w in g if w["conf"] >= 0]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        max_h = max(w["h"] for w in g)
        min_y = min(w["y"] for w in g)
        min_x = min(w["x"] for w in g)
        lines.append({"text": text, "avg_conf": avg_conf, "max_h": max_h, "y": min_y, "x": min_x})

    # merge lines very close in y
    lines = sorted(lines, key=lambda d: (d["y"], d["x"]))
    merged = []
    for ln in lines:
        if merged and abs(ln["y"] - merged[-1]["y"]) <= 6:
            merged[-1]["text"] = (merged[-1]["text"] + " " + ln["text"]).strip()
            merged[-1]["avg_conf"] = max(merged[-1]["avg_conf"], ln["avg_conf"])
            merged[-1]["max_h"] = max(merged[-1]["max_h"], ln["max_h"])
        else:
            merged.append(ln)

    return merged


def has_ingredient_marker(t: str) -> bool:
    U = norm(t).upper()
    return any(m in U for m in INGREDIENT_MARKERS)


def is_noise_line(t: str) -> bool:
    U = t.strip()
    if len(U) < 2:
        return True
    if _RE_VOLUME.search(U.upper()):
        return True
    if not any(c.isalpha() for c in U):
        return True
    return False


def ocr_lines_multi(img: Image.Image) -> List[Dict]:
    """
    OCR robuste: variantes + configs -> garde la meilleure extraction.
    """
    best_lines = []
    best_score = -1e18

    for v in preprocess_variants(img):
        for cfg in OCR_CONFIGS:
            words = ocr_words(v, cfg)
            lines = group_words_into_lines(words)
            if not lines:
                continue

            avg_conf = sum(l["avg_conf"] for l in lines) / max(1, len(lines))
            top_sizes = sum(sorted([l["max_h"] for l in lines], reverse=True)[:6])
            early_ing = any(has_ingredient_marker(l["text"]) and l["y"] < img.height * 0.35 for l in lines)

            score = avg_conf * 25 + top_sizes - (150 if early_ing else 0)

            if score > best_score:
                best_score = score
                best_lines = lines

    return best_lines


# =========================================================
# BUILD PRODUCT CANDIDATES FROM OCR LINES
# =========================================================
def build_candidates(lines: List[str]) -> List[str]:
    lines = [l.strip() for l in lines if l and len(l.strip()) >= 3]

    cands = []
    for i in range(len(lines)):
        cands.append(lines[i])
        if i + 1 < len(lines):
            cands.append(lines[i] + " " + lines[i + 1])
        if i + 2 < len(lines):
            cands.append(lines[i] + " " + lines[i + 1] + " " + lines[i + 2])

    # dedupe
    seen = set()
    out = []
    for c in cands:
        k = norm(c)
        if k and k not in seen and len(k) > 4:
            seen.add(k)
            out.append(c)
    return out


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def hint_bonus(text: str) -> float:
    t = norm(text)
    bonus = 0.0
    for h in PRODUCT_HINTS:
        if h in t:
            bonus += 0.04
    return min(bonus, 0.2)


def is_generic_brand_candidate(text: str) -> bool:
    U = re.sub(r"\s+", " ", norm(text).upper()).strip()
    tokens = set(U.split())
    return len(tokens & GENERIC_NOT_BRAND) > 0


# =========================================================
# FIND BRAND (optional) + BEST PRODUCT MATCH
# =========================================================
def guess_brand_from_lines(lines: List[str]) -> str:
    """
    Heuristique simple:
    - on garde une ligne courte, pas "MOISTURE", pas volume, etc.
    """
    best = "Unknown"
    best_score = -1e9

    for t in lines[:30]:
        if is_noise_line(t) or has_ingredient_marker(t):
            continue
        if is_generic_brand_candidate(t) and len(t.strip()) <= 14:
            continue

        # score: court + majuscule + pas trop long
        L = len(t.strip())
        sc = 0.0
        if 3 <= L <= 22:
            sc += 2.0
        if t.strip().isupper():
            sc += 1.5
        if any(sym in t for sym in ["®", "™", "©"]):
            sc += 1.0

        # pénalité si ressemble à type produit
        if any(k in norm(t).upper() for k in ["CONDITIONER", "CLEANser".upper(), "MOISTURE", "SHAMPOO", "SERUM"]):
            sc -= 1.5

        if sc > best_score:
            best_score = sc
            best = t

    best = re.sub(r"[®™©]", "", best).strip()
    return best if best else "Unknown"


def find_best_product(ocr_lines: List[str], brand_guess: str = "", min_score: float = 0.68) -> Dict:
    """
    Match DB:
    - candidates (1..3 lines combos)
    - filtre par brand si possible
    - score = product_sim + brand_bonus + hint_bonus
    """
    if not DB_READY:
        return {
            "found": False,
            "message": f"DB not ready: {globals().get('DB_LOAD_ERROR', 'unknown')}"
        }

    candidates = build_candidates(ocr_lines)
    brand_n = norm(brand_guess)

    df = DF
    if brand_n and len(brand_n) >= 3:
        sub = DF[DF["_bn"].str.contains(brand_n, na=False)]
        if not sub.empty:
            df = sub

    best = None

    # optimisation simple: skip very large loops when candidates empty
    if not candidates:
        return {"found": False, "message": "No OCR candidates"}

    for cand in candidates:
        cand_n = norm(cand)
        if len(cand_n) < 4:
            continue

        # petit filtre: si le cand est juste 1 mot très générique -> on ignore
        if len(cand_n.split()) == 1 and cand_n.upper() in GENERIC_NOT_BRAND:
            continue

        for _, row in df.iterrows():
            base = sim(cand_n, row["_pn"])
            if base < 0.40:
                continue

            brand_bonus = 0.0
            if brand_n:
                brand_bonus = 0.15 * sim(brand_n, row["_bn"])

            h = hint_bonus(cand)
            score = base + brand_bonus + h

            if (best is None) or (score > best["match_score"]):
                best = {
                    "found": True,
                    "match_score": score,
                    "used_candidate": cand,
                    "product_name": row["product_name"],
                    "brand_name": row["brand_name"],
                    "rating": float(row["rating"]) if pd.notnull(row["rating"]) else None,
                    "price_usd": float(row["price_usd"]) if pd.notnull(row["price_usd"]) else None,
                    "primary_category": row.get("primary_category", ""),
                }

    if not best or best["match_score"] < min_score:
        return {
            "found": False,
            "message": "Produit non trouvé avec confiance suffisante",
            "match_score": round(best["match_score"], 3) if best else 0.0
        }

    best["match_score"] = round(best["match_score"], 3)
    return best


# =========================================================
# MAIN PUBLIC FUNCTION (FastAPI uses this)
# =========================================================
def extract_product_info_enhanced(image: Image.Image, debug_mode: bool = False) -> Dict:
    """
    Retour attendu par ton main.py:
    - brand
    - product_name
    - rating
    - price_usd
    - match_score
    """
    if not TESSERACT_AVAILABLE:
        return {"success": False, "error": "pytesseract non installé", "brand": "", "product_name": "", "ingredients": ""}

    if not setup_tesseract():
        return {"success": False, "error": "Tesseract introuvable", "brand": "", "product_name": "", "ingredients": ""}

    if not DB_READY:
        return {"success": False, "error": f"DB not ready: {globals().get('DB_LOAD_ERROR','unknown')}", "brand": "", "product_name": "", "ingredients": ""}

    try:
        # zones importantes : top / mid / bottom / full
        zones = {
            "top": (0.0, 0.40),
            "mid": (0.20, 0.80),
            "bottom": (0.55, 1.0),
            "full": (0.0, 1.0),
        }

        # OCR collect lines from all crops + rotations
        collected_lines: List[str] = []
        debug_lines = []

        for rot_name, rot_img in rotate_variants(image):
            for zn, (y0, y1) in zones.items():
                crop = crop_zone(rot_img, y0, y1)
                lines = ocr_lines_multi(crop)

                # garder seulement textes
                texts = [l["text"] for l in lines if l.get("text")]
                # filtrage léger
                texts = [t for t in texts if not is_noise_line(t) and not has_ingredient_marker(t)]

                collected_lines.extend(texts)

                if debug_mode:
                    debug_lines.append((rot_name, zn, texts[:12]))

        # dedupe lines
        seen = set()
        uniq_lines = []
        for t in collected_lines:
            k = norm(t)
            if k and k not in seen:
                seen.add(k)
                uniq_lines.append(t)

        if not uniq_lines:
            return {"success": False, "error": "Aucun texte détecté", "brand": "", "product_name": "", "ingredients": ""}

        # 1) guess brand (optional)
        brand_guess = guess_brand_from_lines(uniq_lines)

        # 2) match DB to find product + rating
        match = find_best_product(uniq_lines, brand_guess=brand_guess, min_score=0.68)

        if not match.get("found"):
            # fallback: essayer sans brand
            match2 = find_best_product(uniq_lines, brand_guess="", min_score=0.70)
            match = match2 if match2.get("found") else match

        if match.get("found"):
            result = {
                "success": True,
                "brand": match.get("brand_name", brand_guess),
                "product_name": match.get("product_name", "Unknown Product"),
                "rating": match.get("rating", None),
                "price_usd": match.get("price_usd", None),
                "match_score": match.get("match_score", 0),
                "confidence": "high" if match.get("match_score", 0) >= 0.78 else "medium",
                "ocr_type": "ocr_to_db_match_v1",
                "ingredients": "",  # tu peux laisser vide si tu veux
            }
        else:
            result = {
                "success": True,
                "brand": brand_guess if brand_guess != "Unknown" else "",
                "product_name": "Unknown Product",
                "rating": None,
                "price_usd": None,
                "match_score": match.get("match_score", 0),
                "confidence": "low",
                "ocr_type": "ocr_failed_db_match",
                "ingredients": "",
                "warning": match.get("message", "No match"),
            }

        if debug_mode:
            result["debug"] = {
                "brand_guess": brand_guess,
                "uniq_lines_sample": uniq_lines[:40],
                "zones_lines_sample": debug_lines[:8],
                "db_size": int(len(DF)),
                "db_path": DB_PATH,
                "used_candidate": match.get("used_candidate", ""),
            }

        return result

    except Exception as e:
        return {"success": False, "error": f"Erreur OCR/DB: {str(e)}", "brand": "", "product_name": "", "ingredients": ""}


# =========================================================
# CLI TEST
# =========================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr_service.py <image_path>")
        sys.exit(1)

    p = sys.argv[1].strip().replace('"', "")
    img = Image.open(p)
    out = extract_product_info_enhanced(img, debug_mode=True)
    print(out)
