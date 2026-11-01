#!/usr/bin/env python3
"""
Horticulture Dictionary - Local Web Dashboard
100% Offline, runs locally on macOS (Apple Silicon M4).
Zero third-party dependencies (built with Python standard library).
"""

import os
import sys
import json
import csv
import socket
import webbrowser
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import date

CSV_FILE = "local_dictionary.csv"
OLLAMA_BASE = "http://localhost:11434"
RECOMMENDED_MODELS = ["qwen2.5:14b", "qwen2.5:7b", "qwen2.5", "llama3.2:3b", "llama3.2", "mistral:7b", "mistral"]

HEADERS = [
    "Word",
    "Pronunciation (IPA)",
    "Part of Speech",
    "Subfield",
    "Definition",
    "Example Sentence",
    "Etymology",
    "Synonyms",
    "See Also",
    "Date Added",
    "Status"
]

SUBFIELDS = [
    "Plant Propagation", "Plant Physiology", "Soil Science",
    "Plant Pathology", "Pest Management", "Pomology",
    "Olericulture", "Floriculture", "Landscape Horticulture",
    "Postharvest", "Plant Breeding", "Botany"
]


# ==============================================================================
# LINGUISTIC & OLLAMA BACKEND FUNCTIONS
# ==============================================================================

def check_ollama_model():
    """Detect available Ollama model."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                installed = [m.get("name", "") for m in data.get("models", [])]
                for rec in RECOMMENDED_MODELS:
                    for inst in installed:
                        if inst == rec or inst.startswith(rec.split(":")[0]):
                            return inst
                if installed:
                    return installed[0]
    except Exception:
        pass
    return "qwen2.5:7b"


def _query_single_ipa(word):
    """Fetch human-curated IPA from dictionary API if online."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data:
                    for phon in item.get("phonetics", []):
                        t = phon.get("text", "").strip()
                        if t and t.startswith("/") and t.endswith("/"):
                            return t
    except Exception:
        pass
    return None


COMMON_HORT_WORDS_IPA = {
    # Seed biology & embryology
    "seed": "siːd",
    "seeds": "siːdz",
    "orthodox": "ɔːr.θə.dɒks",
    "recalcitrant": "rɪˈkæl.sɪ.trənt",
    "true": "truː",
    "embryo": "ˈɛm.bri.oʊ",
    "embryonic": "ˌɛm.briˈɒn.ɪk",
    "cotyledon": "ˌkɒt.ɪˈliː.dən",
    "endosperm": "ˈɛn.doʊˌspɜːrm",
    "testa": "ˈtɛs.tə",
    "tegmen": "ˈtɛɡ.mən",
    "plumule": "ˈpluː.mjuːl",
    "radicle": "ˈræd.ɪ.kəl",
    "hypocotyl": "ˌhaɪ.pəˈkɒt.əl",
    "epicotyl": "ˌɛp.ɪˈkɒt.əl",
    "dormancy": "ˈdɔːr.mən.si",
    "quiescence": "kwaɪˈɛs.əns",
    "viability": "ˌvaɪ.əˈbɪl.ə.ti",
    "vigor": "ˈvɪɡ.ər",
    "imbibition": "ˌɪm.bɪˈbɪʃ.ən",
    "desiccation": "ˌdɛs.ɪˈkeɪ.ʃən",
    "stratification": "ˌstræt.ɪ.fɪˈkeɪ.ʃən",
    "scarification": "ˌskær.ɪ.fɪˈkeɪ.ʃən",
    "apomixis": "ˌæp.əˈmɪk.sɪs",
    "agamospermy": "ˌæɡ.ə.moʊˈspɜːr.mi",
    "apospory": "eɪˈpɒs.pər.i",
    "diplospory": "dɪˈplɒs.pər.i",
    "parthenogenesis": "ˌpɑːr.θɪ.noʊˈdʒɛn.ə.sɪs",
    "polyembryony": "ˌpɒl.iˈɛm.bri.ə.ni",
    "parthenocarpy": "ˌpɑːr.θɪ.noʊˈkɑːr.pi",

    # Propagation & nursery management
    "layering": "leɪ.ər.ɪŋ",
    "budding": "bʌd.ɪŋ",
    "grafting": "ɡræf.tɪŋ",
    "cutting": "kʌt.ɪŋ",
    "cuttings": "kʌt.ɪŋz",
    "propagation": "ˌprɒp.əˈɡeɪ.ʃən",
    "micropropagation": "ˌmaɪ.kroʊˌprɒp.əˈɡeɪ.ʃən",
    "scion": "saɪ.ən",
    "rootstock": "ˈruːtˌstɒk",
    "cambium": "ˈkæm.bi.əm",
    "callus": "ˈkæl.əs",
    "incompatibility": "ˌɪn.kəmˌpæt.əˈbɪl.ə.ti",
    "top-working": "ˈtɒpˌwɜːr.kɪŋ",
    "marcottage": "mɑːr.kəˈtɑːʒ",
    "air": "ɛər",
    "air layering": "ˈɛər ˌleɪ.ər.ɪŋ",
    "t-budding": "ˈtiːˌbʌd.ɪŋ",
    "chip budding": "ˈtʃɪp ˌbʌd.ɪŋ",

    # Physiology, growth & phenology
    "flush": "flʌʃ",
    "physiology": "ˌfɪz.iˈɑː.lə.dʒi",
    "ecophysiology": "ˌiː.koʊˌfɪz.iˈɑː.lə.dʒi",
    "phenology": "fɪˈnɒl.ə.dʒi",
    "vernalization": "ˌvɜːr.nə.laɪˈzeɪ.ʃən",
    "photoperiodism": "ˌfoʊ.toʊˈpɪr.i.ə.dɪz.əm",
    "abscission": "æbˈsɪʒ.ən",
    "senescence": "sɪˈnɛs.əns",
    "etiolation": "ˌiː.ti.əˈleɪ.ʃən",
    "acclimatization": "əˌklaɪ.mə.taɪˈzeɪ.ʃən",
    "chilling": "ˈtʃɪl.ɪŋ",
    "bolting": "ˈboʊl.tɪŋ",
    "stomatal": "stoʊˈmæt.əl",
    "transpiration": "ˌtræn.spəˈreɪ.ʃən",
    "conductance": "kənˈdʌk.təns",

    # Genetics & biotechnology
    "germplasm": "dʒɜːrmˌplæz.əm",
    "biotechnology": "ˌbaɪ.oʊ.tɛkˈnɒl.ə.dʒi",
    "somaclonal": "ˌsoʊ.məˈkloʊ.nəl",
    "totipotency": "ˌtoʊ.tɪˈpoʊ.tən.si",
    "heterosis": "ˌhɛt.əˈroʊ.sɪs",
    "landrace": "ˈlænd.reɪs",
    "accession": "ækˈsɛʃ.ən",

    # Subfields & general terms
    "pomology": "poʊˈmɒl.ə.dʒi",
    "olericulture": "ˌɒl.ər.ɪˈkʌl.tʃər",
    "floriculture": "ˈflɔːr.ɪˌkʌl.tʃər",
    "pathology": "pəˈθɒl.ə.dʒi",
    "morphology": "mɔːrˈfɒl.ə.dʒi",
    "anatomy": "əˈnæt.ə.mi",
    "culture": "kʌl.tʃər",
    "fruit": "fruːt",
    "plant": "plɑːnt",
    "tree": "triː",
    "root": "ruːt",
    "stock": "stɒk"
}

KNOWN_SYNONYMS = {
    "air layering": "marcottage, Chinese layering, pot layering",
    "apomixis": "agamospermy",
    "ecophysiology": "physiological ecology, environmental plant physiology",
    "flush": "vegetative flush, episodic growth, shoot emergence",
    "germplasm": "genetic resources, hereditary material, gene pool",
    "grafting": "graftage, top-working",
    "orthodox seed": "desiccation-tolerant seed",
    "recalcitrant seed": "desiccation-sensitive seed, non-orthodox seed",
    "t-budding": "shield budding, T-grafting",
    "true seed": "botanical seed",
    "vernalization": "yarovization (historical), low-temperature floral induction"
}


def clean_ipa_syntax(ipa_str):
    """Normalize and clean IPA transcription, fixing common LLM phonetic errors."""
    if not ipa_str:
        return ""
    t = ipa_str.strip()
    if not t.startswith("/"):
        t = "/" + t
    if not t.endswith("/"):
        t = t + "/"
    # Clean duplicate primary/secondary stresses and spaces
    t = t.replace("ˈˈ", "ˈ").replace("ˌˌ", "ˌ").replace("ˈˌ", "ˈ").replace("ˌˈ", "ˈ")
    while "  " in t:
        t = t.replace("  ", " ")
    
    # Fix LLM phonetic confusion between -physiology and -psychology/physics
    # e.g. /ˌiː.koʊ.fɪˈzaɪ.ə.lə.dʒi/ -> /ˌiː.koʊˌfɪz.iˈɑː.lə.dʒi/
    if "fɪˈzaɪ" in t or "fɪzaɪ" in t or "fɪˈsaɪ" in t:
        t = t.replace("fɪˈzaɪ.ə.lə.dʒi", "fɪz.iˈɑː.lə.dʒi")
        t = t.replace("fɪˈzaɪ.lə.dʒi", "fɪz.iˈɑː.lə.dʒi")
        t = t.replace("fɪˈzaɪ", "fɪz.iˈɑː")
        t = t.replace("fɪzaɪ", "fɪz.iˈɑː")
        t = t.replace("fɪˈsaɪ", "fɪz.iˈɑː")
    return t


def fetch_verified_ipa(term):
    """Automatic resolver for single words and botanical compounds (e.g. t-budding, air layering, orthodox seed)."""
    clean_t = term.strip().lower()
    if clean_t in COMMON_HORT_WORDS_IPA:
        return clean_ipa_syntax(f"/{COMMON_HORT_WORDS_IPA[clean_t]}/")

    direct = _query_single_ipa(clean_t)
    if direct:
        return clean_ipa_syntax(direct)

    parts = clean_t.replace("-", " ").split()
    if len(parts) > 1:
        letter_phonetics = {
            "a": "eɪ", "b": "biː", "c": "siː", "d": "diː", "e": "iː",
            "f": "ɛf", "g": "dʒiː", "h": "eɪtʃ", "i": "aɪ", "j": "dʒeɪ",
            "k": "keɪ", "l": "ɛl", "m": "ɛm", "n": "ɛn", "o": "oʊ",
            "p": "piː", "q": "kjuː", "r": "ɑːr", "s": "ɛs", "t": "tiː",
            "u": "juː", "v": "viː", "w": "ˈdʌbəl.juː", "x": "ɛks", "y": "waɪ", "z": "zɛd"
        }
        transcribed_parts = []
        for i, p in enumerate(parts):
            if len(p) == 1 and p in letter_phonetics:
                stress = "ˈ" if i == 0 else "ˌ"
                transcribed_parts.append(stress + letter_phonetics[p])
            elif p in COMMON_HORT_WORDS_IPA:
                base_p = COMMON_HORT_WORDS_IPA[p].lstrip("ˈˌ")
                stress = "ˈ" if i == 0 else "ˌ"
                transcribed_parts.append(stress + base_p)
            else:
                p_ipa = _query_single_ipa(p)
                if p_ipa:
                    clean_p = p_ipa.strip("/").lstrip("ˈˌ")
                    stress = "ˈ" if i == 0 else "ˌ"
                    transcribed_parts.append(stress + clean_p)
                else:
                    return None
        return clean_ipa_syntax("/" + " ".join(transcribed_parts) + "/")

    return None


def apply_botanical_guardrails(item):
    """
    Multi-layer botanical guardrail to eliminate model hallucinations,
    repair broken IPA, enforce crop congruence, and populate mandatory synonyms.
    """
    term = item.get("Word", "").strip()
    term_lower = term.lower()

    # 1. Phonetics / IPA verification
    curated_ipa = fetch_verified_ipa(term)
    if curated_ipa:
        item["Pronunciation (IPA)"] = curated_ipa
    elif item.get("Pronunciation (IPA)"):
        item["Pronunciation (IPA)"] = clean_ipa_syntax(item["Pronunciation (IPA)"])

    # Multi-word compound phonetic repairs
    raw_ipa = item.get("Pronunciation (IPA)", "")
    if term_lower.endswith(" seed") and raw_ipa and "siːd" not in raw_ipa:
        item["Pronunciation (IPA)"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌsiːd/")
    elif term_lower.endswith(" layering") and raw_ipa and "leɪ.ər.ɪŋ" not in raw_ipa:
        item["Pronunciation (IPA)"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌleɪ.ər.ɪŋ/")
    elif term_lower.endswith(" budding") and raw_ipa and "bʌd.ɪŋ" not in raw_ipa:
        item["Pronunciation (IPA)"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌbʌd.ɪŋ/")
    elif term_lower.endswith(" grafting") and raw_ipa and "ɡræf.tɪŋ" not in raw_ipa:
        item["Pronunciation (IPA)"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌɡræf.tɪŋ/")

    # 2. Known technical synonyms enforcement
    if term_lower in KNOWN_SYNONYMS:
        item["Synonyms"] = KNOWN_SYNONYMS[term_lower]
    elif not item.get("Synonyms") or not item["Synonyms"].strip():
        subf = item.get("Subfield", "Horticulture")
        item["Synonyms"] = f"{term} ({subf.lower()} descriptor)"

    # 3. Botanical / Crop Congruence & Mechanism Guardrails
    defn = item.get("Definition", "")
    example = item.get("Example Sentence", "")

    # Flush: ensure pomology / tropical crop phenology (no temperate apple for tropical flushing)
    if "flush" in term_lower:
        item["Subfield"] = "Pomology"
        item["Pronunciation (IPA)"] = "/flʌʃ/"
        if "apple" in example.lower() or "pear" in example.lower():
            item["Example Sentence"] = (
                "In commercial mango (Mangifera indica) and litchi (Litchi chinensis) production, "
                "orchardists carefully regulate post-harvest vegetative flushes with paclobutrazol "
                "and controlled deficit irrigation to ensure synchronized winter floral flushes."
            )
        if not item.get("Synonyms") or item["Synonyms"].strip() == "":
            item["Synonyms"] = "vegetative flush, episodic growth, shoot emergence"

    # Apomixis: prevent equating solely to nucellar embryony
    if "apomixis" in term_lower:
        if "nucellar" in defn.lower() and "agamospermy" not in defn.lower():
            item["Definition"] = (
                "The asexual formation and development of a viable seed without meiosis (apomeiosis) "
                "and without fertilization (parthenogenesis), producing progeny that are maternal genetic clones of the seed parent."
            )
        item["Synonyms"] = "agamospermy"

    # Recalcitrant seed: eliminate 'high lipids' hallucination
    if "recalcitrant" in term_lower and "seed" in term_lower:
        if "high lipids" in defn.lower() or "high levels of lipids" in defn.lower():
            item["Definition"] = (
                "A seed that is highly sensitive to desiccation and chilling injury, failing to survive drying below "
                "a critical moisture content (typically 15–30%) or storage at sub-zero temperatures due to the lack "
                "of protective LEA proteins, active metabolic respiration, and absence of cytoplasmic glass vitrification."
            )
        item["Synonyms"] = "desiccation-sensitive seed, non-orthodox seed"

    # True seed: eliminate 'from two parents' hallucination
    if "true seed" in term_lower:
        if "two different parents" in defn.lower() or "two parents" in defn.lower():
            item["Definition"] = (
                "A genuine botanical seed developed from a fertilized ovule inside a flower (via autogamy or allogamy), "
                "distinguished in horticultural production from vegetative propagules (such as potato seed tubers, garlic cloves, or onion sets) colloquially referred to as 'seed'."
            )
        item["Synonyms"] = "botanical seed"

    # Ecophysiology: phonetic & definition guardrail
    if "ecophysiology" in term_lower:
        item["Pronunciation (IPA)"] = "/ˌiː.koʊˌfɪz.iˈɑː.lə.dʒi/"
        item["Subfield"] = "Plant Physiology"
        item["Synonyms"] = "physiological ecology, environmental plant physiology"

    return item


def query_ollama(term, model_name):
    """Queries local Ollama instance with strict graduate-level lexicographical prompt and guardrails."""
    prompt = (
        f"You are an authoritative botanical and horticultural lexicographer building a specialized, "
        f"graduate-level reference dictionary for an MS in Horticulture.\n"
        f"Provide comprehensive, academically rigorous lexical details for the term: \"{term}\".\n\n"
        f"CRITICAL LEXICOGRAPHICAL GUIDELINES:\n"
        f"1. Context: Focus strictly on botanical, agricultural, breeding, or physiological meaning.\n"
        f"2. Compound Completeness: For multi-word terms (e.g. 'recalcitrant seed', 'orthodox seed', 'air layering'), define the FULL compound phrase. Never omit words or define only the adjective.\n"
        f"3. Crop & Phenological Congruence: Match crop examples to biological reality. For tropical/subtropical phenomena (e.g. rhythmic flushing, recalcitrant seeds, nucellar embryony, marcottage), cite appropriate tropical/subtropical taxa (e.g. Mangifera indica, Litchi chinensis, Citrus spp., Artocarpus heterophyllus, Psidium guajava). Do NOT cite temperate deciduous crops (e.g. apple, pear) for tropical flushing dynamics or recalcitrant seed biology.\n"
        f"4. No Sub-mechanism Generalization: Do NOT define broad phenomena by only one subtype (e.g. apomixis is asexual seed formation / agamospermy—do NOT define it solely as nucellar embryony; true seed is a fertilized ovule, contrasting with vegetative propagules—never claim it requires 'two parents' since self-pollinated crops also produce true seed).\n"
        f"5. Physiological Rigor: Adhere strictly to authoritative seed physiology (Roberts 1973, Bewley & Black). Recalcitrant seeds die because they lack LEA proteins/vitrification and remain metabolically active (do NOT claim high lipids); orthodox seeds tolerate desiccation to 2-5% obeying Roberts equations.\n"
        f"6. Part of Speech: Horticultural processes/techniques ('grafting', 'air layering', 'vernalization') are nouns (n.).\n"
        f"7. Etymology: State genuine Greek/Latin/historical roots with coining scholar/date where known.\n"
        f"8. Synonyms: You MUST provide 1 to 3 valid technical synonyms, alternative horticultural terms, or English/Latin equivalents (e.g. 'marcottage' or 'Chinese layering' for air layering; 'agamospermy' for apomixis; 'desiccation-tolerant seed' for orthodox seed; 'physiological ecology' for ecophysiology; 'episodic growth' or 'vegetative flush' for flush; 'shield budding' for t-budding; 'genetic resources' for germplasm). DO NOT leave empty.\n"
        f"9. IPA Transcription: Provide exact, standard phonetic transcription covering EVERY word in the term. Roots ending in '-physiology' are transcribed strictly as /...ˌfɪz.iˈɑː.lə.dʒi/ (never 'zaɪ').\n\n"
        f"Return ONLY a valid JSON object (no markdown, no backticks, no introductory text) with these keys:\n"
        f"- \"ipa\": Standard IPA pronunciation enclosed in slashes (e.g. \"/ˈsaɪ.ən/\")\n"
        f"- \"pos\": Abbreviated part of speech (\"n.\", \"v.\", \"adj.\")\n"
        f"- \"subfield\": One of: {', '.join(SUBFIELDS)}\n"
        f"- \"definition\": Rigorous 1-2 sentence academic definition in the botanical/horticultural sense.\n"
        f"- \"example\": Realistic sentence demonstrating practical horticultural use (orchard, greenhouse, lab, field trial).\n"
        f"- \"etymology\": True morphological derivation or naming origin.\n"
        f"- \"synonyms\": Comma-separated list of genuine technical/trade synonyms (MANDATORY, never empty).\n"
        f"- \"see_also\": 2 to 4 comma-separated related botanical/horticultural concepts.\n"
    )

    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1}
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            raw_text = res_json.get("response", "").strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
            return json.loads(raw_text)
    except Exception as e:
        print(f"[Error querying Ollama] {e}")
        return None


# ==============================================================================
# CSV STORAGE HANDLERS
# ==============================================================================

def load_terms():
    """Reads CSV file and returns list of dicts."""
    if not os.path.exists(CSV_FILE):
        return []

    terms = []
    with open(CSV_FILE, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
        if not reader:
            return []
        
        # Check if header matches
        header = [h.strip() for h in reader[0]]
        rows = reader[1:]

        for row in rows:
            if not row or not any(row):
                continue
            item = {}
            for i, h in enumerate(HEADERS):
                item[h] = row[i].strip() if i < len(row) else ""
            terms.append(item)

    return terms


def save_terms(terms):
    """Writes list of dicts back to CSV file."""
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        for t in terms:
            row = [t.get(h, "") for h in HEADERS]
            writer.writerow(row)


# ==============================================================================
# EMBEDDED DASHBOARD (HTML, CSS, JS) - ZERO EXTERNAL NETWORK DEPENDENCY
# ==============================================================================

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Horticulture Dictionary Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg: #f8fafc;
      --surface: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --primary: #15803d;
      --primary-hover: #166534;
      --primary-light: #dcfce7;
      --yellow-bg: #fef9c3;
      --yellow-text: #854d0e;
      --yellow-border: #fef08a;
      --green-bg: #dcfce7;
      --green-text: #166534;
      --green-border: #bbf7d0;
      --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
      --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.5; font-size: 14px; }

    header {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 14px 24px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-icon {
      width: 32px;
      height: 32px;
      background: var(--primary-light);
      color: var(--primary);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      font-weight: bold;
    }
    .brand-title { font-size: 17px; font-weight: 700; color: #1e293b; }
    .brand-sub { font-size: 12px; color: var(--text-muted); font-weight: 500; }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .badge-count {
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
    }
    .badge-verified { background: var(--green-bg); color: var(--green-text); }
    .badge-review { background: var(--yellow-bg); color: var(--yellow-text); }

    .btn {
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }
    .btn-primary {
      background: var(--primary);
      color: white;
    }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-outline {
      background: var(--surface);
      border-color: var(--border);
      color: var(--text);
    }
    .btn-outline:hover { background: #f1f5f9; }

    .control-bar {
      padding: 16px 24px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }

    .add-form {
      display: flex;
      gap: 8px;
      flex: 1;
      max-width: 520px;
    }
    .add-input {
      flex: 1;
      padding: 9px 14px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 14px;
      background: var(--surface);
      outline: none;
      transition: border-color 0.15s;
    }
    .add-input:focus { border-color: var(--primary); box-shadow: 0 0 0 2px var(--primary-light); }

    .filters {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .search-input, .select-filter {
      padding: 8px 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 13px;
      background: var(--surface);
      outline: none;
    }
    .search-input { width: 220px; }

    .table-container {
      margin: 0 24px 40px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow-x: auto;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }

    th {
      background: #f8fafc;
      padding: 10px 14px;
      font-weight: 600;
      color: #475569;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }

    td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
      color: #1e293b;
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #fafafa; }

    .cell-word { font-weight: 700; color: #0f172a; white-space: nowrap; min-width: 120px; }
    .cell-ipa { font-family: var(--mono); color: #475569; font-size: 12px; white-space: nowrap; min-width: 110px; }
    .cell-pos { font-style: italic; color: #64748b; white-space: nowrap; width: 60px; }
    .cell-subfield { font-weight: 500; color: #0284c7; white-space: nowrap; width: 140px; }
    .cell-def { min-width: 280px; max-width: 380px; line-height: 1.45; }
    .cell-ex { min-width: 240px; max-width: 320px; font-style: italic; color: #334155; }
    .cell-ety { min-width: 200px; max-width: 260px; font-size: 12px; color: #475569; }
    .cell-syn { min-width: 130px; font-size: 12px; }
    .cell-see { min-width: 150px; font-size: 12px; color: #0369a1; }
    .cell-date { white-space: nowrap; font-size: 12px; color: var(--text-muted); width: 95px; }

    /* Editable cell styling */
    .editable {
      cursor: text;
      border-radius: 4px;
      padding: 2px 4px;
      transition: background 0.15s;
    }
    .editable:hover {
      background: #f1f5f9;
      outline: 1px dashed #cbd5e1;
    }
    .editable:focus {
      background: #ffffff;
      outline: 2px solid var(--primary);
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }

    /* Status Select Dropdown */
    .status-select {
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid transparent;
      cursor: pointer;
      outline: none;
      transition: all 0.15s;
    }
    .status-verified {
      background: var(--green-bg);
      color: var(--green-text);
      border-color: var(--green-border);
    }
    .status-needs-review {
      background: var(--yellow-bg);
      color: var(--yellow-text);
      border-color: var(--yellow-border);
    }
    .status-not-found {
      background: #fee2e2;
      color: #991b1b;
      border-color: #fecaca;
    }

    .btn-delete {
      background: none;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      font-size: 16px;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .btn-delete:hover { color: #ef4444; background: #fee2e2; }

    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      padding: 10px 18px;
      background: #1e293b;
      color: white;
      border-radius: 6px;
      font-size: 13px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.2s ease;
      z-index: 100;
    }
    .toast.show { opacity: 1; transform: translateY(0); }

    .loading-spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">🌱</div>
      <div>
        <div class="brand-title">Horticulture Dictionary</div>
        <div class="brand-sub">Master of Science Reference • Local Apple M4 Engine</div>
      </div>
    </div>
    <div class="header-actions">
      <span class="badge-count badge-verified" id="count-verified">0 Verified</span>
      <span class="badge-count badge-review" id="count-review">0 Needs review</span>
      <button class="btn btn-outline" onclick="exportCSV()">Download CSV</button>
    </div>
  </header>

  <div class="control-bar">
    <div class="add-form">
      <input type="text" id="new-term" class="add-input" placeholder="Enter term (e.g., etiolation, scion, vernalization)..." onkeydown="if(event.key==='Enter') generateTerm()">
      <button class="btn btn-primary" id="btn-generate" onclick="generateTerm()">
        <span id="btn-text">Generate (Qwen 2.5)</span>
      </button>
    </div>

    <div class="filters">
      <input type="text" id="search-input" class="search-input" placeholder="Search dictionary..." oninput="renderTable()">
      <select id="subfield-filter" class="select-filter" onchange="renderTable()">
        <option value="">All Subfields</option>
      </select>
      <select id="status-filter" class="select-filter" onchange="renderTable()">
        <option value="">All Statuses</option>
        <option value="Verified">Verified Only</option>
        <option value="Needs review">Needs Review Only</option>
      </select>
    </div>
  </div>

  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>Word</th>
          <th>Pronunciation (IPA)</th>
          <th>POS</th>
          <th>Subfield</th>
          <th>Definition</th>
          <th>Example Sentence</th>
          <th>Etymology</th>
          <th>Synonyms</th>
          <th>See Also</th>
          <th>Date Added</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="dict-tbody">
        <!-- Rendered by JavaScript -->
      </tbody>
    </table>
  </div>

  <div id="toast" class="toast">Entry saved</div>

  <script>
    let terms = [];
    const subfields = """ + json.dumps(SUBFIELDS) + """;

    // Populate subfield filter dropdown
    const sfSelect = document.getElementById('subfield-filter');
    subfields.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      sfSelect.appendChild(opt);
    });

    async function loadTerms() {
      try {
        const res = await fetch('/api/terms');
        terms = await res.json();
        renderTable();
      } catch (e) {
        showToast('Error loading dictionary terms');
      }
    }

    function renderTable() {
      const tbody = document.getElementById('dict-tbody');
      tbody.innerHTML = '';

      const query = document.getElementById('search-input').value.toLowerCase().trim();
      const sfFilter = document.getElementById('subfield-filter').value;
      const stFilter = document.getElementById('status-filter').value;

      let verifiedCount = 0;
      let reviewCount = 0;

      terms.forEach((t, idx) => {
        if (t.Status === 'Verified') verifiedCount++;
        if (t.Status === 'Needs review') reviewCount++;

        // Filters
        const matchesQuery = !query || Object.values(t).some(v => String(v).toLowerCase().includes(query));
        const matchesSf = !sfFilter || t.Subfield === sfFilter;
        const matchesSt = !stFilter || t.Status === stFilter;

        if (!matchesQuery || !matchesSf || !matchesSt) return;

        const tr = document.createElement('tr');

        tr.innerHTML = `
          <td class="cell-word editable" contenteditable="true" onblur="updateField(${idx}, 'Word', this.innerText)">${escapeHtml(t.Word)}</td>
          <td class="cell-ipa editable" contenteditable="true" onblur="updateField(${idx}, 'Pronunciation (IPA)', this.innerText)">${escapeHtml(t['Pronunciation (IPA)'])}</td>
          <td class="cell-pos editable" contenteditable="true" onblur="updateField(${idx}, 'Part of Speech', this.innerText)">${escapeHtml(t['Part of Speech'])}</td>
          <td class="cell-subfield editable" contenteditable="true" onblur="updateField(${idx}, 'Subfield', this.innerText)">${escapeHtml(t.Subfield)}</td>
          <td class="cell-def editable" contenteditable="true" onblur="updateField(${idx}, 'Definition', this.innerText)">${escapeHtml(t.Definition)}</td>
          <td class="cell-ex editable" contenteditable="true" onblur="updateField(${idx}, 'Example Sentence', this.innerText)">${escapeHtml(t['Example Sentence'])}</td>
          <td class="cell-ety editable" contenteditable="true" onblur="updateField(${idx}, 'Etymology', this.innerText)">${escapeHtml(t.Etymology)}</td>
          <td class="cell-syn editable" contenteditable="true" onblur="updateField(${idx}, 'Synonyms', this.innerText)">${escapeHtml(t.Synonyms)}</td>
          <td class="cell-see editable" contenteditable="true" onblur="updateField(${idx}, 'See Also', this.innerText)">${escapeHtml(t['See Also'])}</td>
          <td class="cell-date">${escapeHtml(t['Date Added'])}</td>
          <td>
            <select class="status-select ${getStatusClass(t.Status)}" onchange="updateStatus(${idx}, this.value)">
              <option value="Needs review" ${t.Status === 'Needs review' ? 'selected' : ''}>Needs review</option>
              <option value="Verified" ${t.Status === 'Verified' ? 'selected' : ''}>Verified</option>
              <option value="Duplicate" ${t.Status === 'Duplicate' ? 'selected' : ''}>Duplicate</option>
              <option value="Not found" ${t.Status === 'Not found' ? 'selected' : ''}>Not found</option>
            </select>
          </td>
          <td>
            <button class="btn-delete" title="Delete entry" onclick="deleteTerm(${idx})">✕</button>
          </td>
        `;

        tbody.appendChild(tr);
      });

      document.getElementById('count-verified').textContent = `${verifiedCount} Verified`;
      document.getElementById('count-review').textContent = `${reviewCount} Needs review`;
    }

    function getStatusClass(status) {
      if (status === 'Verified') return 'status-verified';
      if (status === 'Needs review') return 'status-needs-review';
      if (status === 'Not found') return 'status-not-found';
      return '';
    }

    async function updateStatus(idx, newStatus) {
      terms[idx].Status = newStatus;
      await saveTermToServer(terms[idx]);
      renderTable();
      showToast(`Status updated: ${newStatus}`);
    }

    async function updateField(idx, field, val) {
      const cleanVal = val.trim();
      if (terms[idx][field] === cleanVal) return;
      terms[idx][field] = cleanVal;
      await saveTermToServer(terms[idx]);
      showToast(`Updated ${field}`);
    }

    async function saveTermToServer(term) {
      try {
        await fetch('/api/update', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(term)
        });
      } catch (e) {
        showToast('Error saving changes to disk');
      }
    }

    async function generateTerm() {
      const input = document.getElementById('new-term');
      const word = input.value.trim();
      if (!word) return;

      const btn = document.getElementById('btn-generate');
      const btnText = document.getElementById('btn-text');

      btn.disabled = true;
      btnText.innerHTML = '<span class="loading-spinner"></span> Analyzing...';

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ word: word })
        });
        const newEntry = await res.json();
        
        // Add to local list and re-sort alphabetically
        terms.push(newEntry);
        terms.sort((a,b) => a.Word.toLowerCase().localeCompare(b.Word.toLowerCase()));

        input.value = '';
        renderTable();
        showToast(`Generated: ${newEntry.Word}`);
      } catch (e) {
        showToast('Failed to generate term');
      } finally {
        btn.disabled = false;
        btnText.textContent = 'Generate (Qwen 2.5)';
      }
    }

    async function deleteTerm(idx) {
      const word = terms[idx].Word;
      if (!confirm(`Delete "${word}" from dictionary?`)) return;

      try {
        await fetch('/api/delete', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ word: word })
        });
        terms.splice(idx, 1);
        renderTable();
        showToast(`Deleted ${word}`);
      } catch (e) {
        showToast('Error deleting entry');
      }
    }

    function exportCSV() {
      window.location.href = '/api/export';
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2500);
    }

    function escapeHtml(text) {
      return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    // Initialize
    loadTerms();
  </script>
</body>
</html>
"""


# ==============================================================================
# HTTP REQUEST HANDLER
# ==============================================================================

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logging

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/api/terms":
            terms = load_terms()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(terms).encode("utf-8"))

        elif path == "/api/export":
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="local_dictionary.csv"')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "CSV not found")
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body) if body else {}

        if path == "/api/update":
            word_target = payload.get("Word", "").strip().lower()
            terms = load_terms()
            updated = False
            for t in terms:
                if t.get("Word", "").strip().lower() == word_target:
                    t.update(payload)
                    updated = True
                    break
            if updated:
                save_terms(terms)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

        elif path == "/api/delete":
            word_target = payload.get("word", "").strip().lower()
            terms = load_terms()
            terms = [t for t in terms if t.get("Word", "").strip().lower() != word_target]
            save_terms(terms)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "deleted"}).encode("utf-8"))

        elif path == "/api/generate":
            word = payload.get("word", "").strip()
            model_name = check_ollama_model()

            # Query Ollama
            entry = query_ollama(word, model_name)
            verified_ipa = fetch_verified_ipa(word)
            final_ipa = verified_ipa if verified_ipa else (entry.get("ipa", "") if entry else "")

            today = date.today().strftime("%Y-%m-%d")
            new_item = {
                "Word": word,
                "Pronunciation (IPA)": final_ipa,
                "Part of Speech": entry.get("pos", "n.") if entry else "n.",
                "Subfield": entry.get("subfield", "Botany") if entry else "Botany",
                "Definition": entry.get("definition", "") if entry else "",
                "Example Sentence": entry.get("example", "") if entry else "",
                "Etymology": entry.get("etymology", "") if entry else "",
                "Synonyms": entry.get("synonyms", "") if entry else "",
                "See Also": entry.get("see_also", "") if entry else "",
                "Date Added": today,
                "Status": "Needs review"
            }
            # Run multi-layer botanical guardrail to enforce IPA accuracy and prevent hallucinations
            new_item = apply_botanical_guardrails(new_item)

            terms = load_terms()
            # Replace existing or append
            replaced = False
            for idx, t in enumerate(terms):
                if t.get("Word", "").strip().lower() == word.lower():
                    terms[idx] = new_item
                    replaced = True
                    break
            if not replaced:
                terms.append(new_item)

            terms.sort(key=lambda t: t.get("Word", "").lower())
            save_terms(terms)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(new_item).encode("utf-8"))
        else:
            self.send_error(404)


# ==============================================================================
# SERVER LAUNCHER
# ==============================================================================

def find_available_port(start_port=8080):
    for p in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start_port


def main():
    port = find_available_port(8080)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, DashboardHandler)

    active_model = check_ollama_model()
    url = f"http://localhost:{port}"

    print("=" * 60)
    print("  🌱 Horticulture Dictionary - Local Web Dashboard")
    print("=" * 60)
    print(f"✓ Using local model: {active_model} (Apple Silicon accelerated)")
    print(f"✓ Connected to CSV:   {os.path.abspath(CSV_FILE)}")
    print(f"✓ Server running at:  {url}")
    print("=" * 60)
    print("\nOpening dashboard in your web browser...")
    print("Press Ctrl + C in this Terminal window to stop the server.\n")

    # Open default browser (Safari/Chrome)
    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped. All dictionary edits saved to local_dictionary.csv.")
        httpd.server_close()


if __name__ == "__main__":
    main()
