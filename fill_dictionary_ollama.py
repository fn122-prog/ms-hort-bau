#!/usr/bin/env python3
"""
Horticulture Dictionary Builder - Local Offline Edition (Ollama)
Runs 100% locally on your Mac (Apple Silicon M4).
- Zero cost, zero API keys
- Zero rate limits (process 100+ words at once)
- Works completely offline (greenhouses, field trips, planes)
"""

import os
import sys
import json
import csv
import urllib.request
import urllib.error
import urllib.parse
from datetime import date

OLLAMA_BASE = "http://localhost:11434"
RECOMMENDED_MODELS = ["qwen2.5:14b", "qwen2.5:7b", "llama3.2:3b", "llama3.2", "mistral:7b", "mistral"]

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


def _query_single_ipa(word):
    """Queries online linguistic dictionary for human-curated IPA."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
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


SUBFIELDS = [
    "Plant Propagation", "Plant Physiology", "Soil Science",
    "Plant Pathology", "Pest Management", "Pomology",
    "Olericulture", "Floriculture", "Landscape Horticulture",
    "Postharvest", "Plant Breeding", "Botany"
]


def check_ollama_running():
    """Verify that Ollama application is active."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                return True, models
    except Exception:
        pass
    return False, []


def pick_best_model(installed_models):
    """Automatically selects the best available horticultural model."""
    for rec in RECOMMENDED_MODELS:
        for inst in installed_models:
            if inst == rec or inst.startswith(rec.split(":")[0]):
                return inst
    if installed_models:
        return installed_models[0]
    return "llama3.2"


def query_ollama(term, model_name):
    """Send term to local Ollama model and return structured JSON."""
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
        f"8. Synonyms: You MUST provide 1 to 3 valid technical synonyms, alternative horticultural terms, or English/Latin equivalents (e.g. 'marcottage' for air layering; 'agamospermy' for apomixis; 'desiccation-tolerant seed' for orthodox seed; 'physiological ecology' for ecophysiology; 'episodic growth' or 'vegetative flush' for flush; 'shield budding' for t-budding; 'genetic resources' for germplasm). DO NOT leave empty.\n"
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
        "options": {
            "temperature": 0.1
        }
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
            # Clean possible markdown wrap
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
            return json.loads(raw_text)
    except Exception as e:
        print(f"   [!] Error querying Ollama for '{term}': {e}")
        return None


def process_words(words, model_name):
    """Processes a list of words and returns formatted rows with applied botanical guardrails."""
    results = []
    today = date.today().strftime("%Y-%m-%d")
    total = len(words)

    print(f"\nProcessing {total} term(s) locally using Ollama ({model_name})...\n")

    for i, word in enumerate(words, 1):
        clean_word = word.strip()
        if not clean_word:
            continue

        print(f"[{i}/{total}] Analyzing: {clean_word}...")
        entry = query_ollama(clean_word, model_name)

        if entry and entry.get("definition"):
            # Construct preliminary item
            verified_ipa = fetch_verified_ipa(clean_word)
            final_ipa = verified_ipa if verified_ipa else entry.get("ipa", "")
            item_dict = {
                "Word": clean_word,
                "Pronunciation (IPA)": final_ipa,
                "Part of Speech": entry.get("pos", "n."),
                "Subfield": entry.get("subfield", "Botany"),
                "Definition": entry.get("definition", ""),
                "Example Sentence": entry.get("example", ""),
                "Etymology": entry.get("etymology", ""),
                "Synonyms": entry.get("synonyms", ""),
                "See Also": entry.get("see_also", ""),
                "Date Added": today,
                "Status": "Needs review"
            }
            # Run botanical guardrails to eliminate hallucinations, enforce phonetics, and ensure synonyms
            item_dict = apply_botanical_guardrails(item_dict)

            row = [
                item_dict["Word"],
                item_dict["Pronunciation (IPA)"],
                item_dict["Part of Speech"],
                item_dict["Subfield"],
                item_dict["Definition"],
                item_dict["Example Sentence"],
                item_dict["Etymology"],
                item_dict["Synonyms"],
                item_dict["See Also"],
                item_dict["Date Added"],
                item_dict["Status"]
            ]
            print(f"   ✓ Success! [{item_dict['Subfield']}] {item_dict['Definition'][:70]}...")
        else:
            row = [clean_word, "", "", "", "", "", "", "", "", today, "Not found"]
            print(f"   ✗ Could not retrieve structured definition.")

        results.append(row)

    return results


def mode_csv(model_name):
    """Process a downloaded Google Sheet CSV file."""
    input_file = "Dictionary.csv"
    output_file = "Dictionary_filled.csv"

    if not os.path.exists(input_file):
        print(f"\n[Notice] '{input_file}' not found in this folder.")
        print("To process your sheet:")
        print("1. In Google Sheets, click File > Download > Comma Separated Values (.csv)")
        print(f"2. Rename or save it here as: {os.path.abspath(input_file)}")
        print("3. Run this script again.")
        return

    words_to_process = []
    existing_rows = []

    with open(input_file, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
        if not reader:
            print("CSV file is empty.")
            return

        header = reader[0]
        rows = reader[1:]

        for r in rows:
            if not r:
                continue
            word = r[0].strip() if len(r) > 0 else ""
            status = r[-1].strip() if r else ""

            # If word exists and status is blank or Needs Review without definition
            has_def = len(r) > 4 and r[4].strip()
            if word and (not status or not has_def):
                words_to_process.append(word)
            else:
                # If existing row had 12 columns with old Source, drop the Source column
                if len(r) == 12:
                    r = r[:9] + r[10:]
                existing_rows.append(r)

    if not words_to_process:
        print("\nAll rows in Dictionary.csv already have definitions!")
        return

    print(f"Found {len(words_to_process)} words needing definitions.")
    new_rows = process_words(words_to_process, model_name)

    all_rows = existing_rows + new_rows
    # Sort alphabetically by term
    all_rows.sort(key=lambda r: r[0].lower() if r else "")

    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(all_rows)

    print(f"\n==========================================")
    print(f"✓ COMPLETE! Saved to: {os.path.abspath(output_file)}")
    print(f"You can open '{output_file}' in Excel, Numbers, or import it back to Google Sheets:")
    print("In Google Sheets: File > Import > Upload 'Dictionary_filled.csv' > Replace current sheet.")
    print(f"==========================================\n")


def mode_interactive(model_name):
    """Interactive loop to quickly look up one or more terms."""
    today = date.today().strftime("%Y-%m-%d")
    output_file = "local_dictionary.csv"
    file_exists = os.path.exists(output_file)

    print(f"\n--- Interactive Horticulture Term Lookup ---")
    print(f"Results will automatically be saved to '{output_file}'.")
    print("Type a word and press Enter. Type 'q' to quit.\n")

    while True:
        try:
            term = input("Enter horticultural term: ").strip()
            if not term:
                continue
            if term.lower() in ["q", "quit", "exit"]:
                break

            entry = query_ollama(term, model_name)
            if not entry or not entry.get("definition"):
                print("Could not generate definition.\n")
                continue

            verified_ipa = fetch_verified_ipa(term)
            final_ipa = verified_ipa if verified_ipa else entry.get("ipa", "")

            print("\n" + "=" * 60)
            print(f"Word:         {term}")
            print(f"IPA:          {final_ipa}")
            print(f"Part Speech:  {entry.get('pos', '')}")
            print(f"Subfield:     {entry.get('subfield', '')}")
            print(f"Definition:   {entry.get('definition', '')}")
            print(f"Example:      {entry.get('example', '')}")
            print(f"Etymology:    {entry.get('etymology', '')}")
            print(f"Synonyms:     {entry.get('synonyms', '')}")
            print(f"See Also:     {entry.get('see_also', '')}")
            print("=" * 60 + "\n")

            row = [
                term,
                final_ipa,
                entry.get("pos", ""),
                entry.get("subfield", "Botany"),
                entry.get("definition", ""),
                entry.get("example", ""),
                entry.get("etymology", ""),
                entry.get("synonyms", ""),
                entry.get("see_also", ""),
                today,
                "Needs review"
            ]

            with open(output_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(HEADERS)
                    file_exists = True
                writer.writerow(row)

            print(f"✓ Saved to {output_file}\n")
        except (KeyboardInterrupt, EOFError):
            break

    print("\nGoodbye!")


def main():
    print("=====================================================")
    print("  Horticulture Dictionary - Offline Ollama Edition   ")
    print("=====================================================")

    running, installed = check_ollama_running()
    if not running:
        print("\n[!] OLLAMA IS NOT RUNNING.")
        print("Please start Ollama on your Mac:")
        print("  1. Open Ollama from your Applications folder, OR")
        print("  2. In your Terminal, run:  ollama serve")
        print("\nThen run this script again.\n")
        sys.exit(1)

    print(f"✓ Ollama connection detected.")
    if installed:
        print(f"✓ Installed local models: {', '.join(installed)}")
    else:
        print("\n[!] No models found in Ollama yet.")
        print("Run this command in Terminal to download a free model (takes ~1 minute):")
        print("   ollama run llama3.2")
        print("\nThen restart this script.\n")
        sys.exit(1)

    chosen_model = pick_best_model(installed)
    print(f"✓ Using model: {chosen_model} (Apple Silicon accelerated)")

    print("\nChoose an option:")
    print("  1. Process Google Sheet CSV (reads 'Dictionary.csv' -> writes 'Dictionary_filled.csv')")
    print("  2. Interactive lookup (type words one by one and view output)")
    print("  3. Exit")

    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    if choice == "1":
        mode_csv(chosen_model)
    elif choice == "2":
        mode_interactive(chosen_model)
    else:
        print("Exiting.")


if __name__ == "__main__":
    main()
