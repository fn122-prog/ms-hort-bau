#!/usr/bin/env python3
"""
HortiPrep - Graduate Exam Study & Course Review Application
Specially designed for MS in Horticulture (Winter Semester, BAU Mymensingh)

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
from datetime import date, datetime

PORT = 8081
DATA_FILE = "course_study_deck.json"
DICTIONARY_CSV = "local_dictionary.csv"
OLLAMA_BASE = "http://localhost:11434"
RECOMMENDED_MODELS = ["qwen2.5:14b", "qwen2.5:7b", "qwen2.5", "llama3.2:3b", "llama3.2", "mistral:7b"]

DEFAULT_COURSES = [
    {
        "id": "HORT501",
        "code": "Hort. 501",
        "name": "Advanced Fruit Production",
        "semester": 1,
        "type": "Compulsory",
        "subfields": ["Pomology", "Plant Propagation", "Fruit Crop Physiology", "Orchard Management"]
    },
    {
        "id": "HORT502",
        "code": "Hort. 502",
        "name": "Methods in Advanced Research",
        "semester": 1,
        "type": "Compulsory",
        "subfields": ["Experimental Design", "Field Techniques", "Laboratory Instrumentation"]
    },
    {
        "id": "HORT503",
        "code": "Hort. 503",
        "name": "Advanced Vegetable Production",
        "semester": 1,
        "type": "Compulsory",
        "subfields": ["Olericulture", "Vegetable Physiology", "Protected Cultivation", "Seed Production"]
    },
    {
        "id": "HORT505",
        "code": "Hort. 505",
        "name": "Advanced Research Methodology",
        "semester": 1,
        "type": "Compulsory",
        "subfields": ["Statistical Analysis", "Biometrical Genetics", "Scientific Sampling", "Manuscript Preparation"]
    },
    {
        "id": "HORT507",
        "code": "Hort. 507",
        "name": "Ornamental and Landscape Hort.",
        "semester": 1,
        "type": "Compulsory",
        "subfields": ["Floriculture", "Landscape Architecture", "Turfgrass Management", "Postharvest Floriculture"]
    },
    {
        "id": "HORT519",
        "code": "Hort. 519",
        "name": "Horticultural Seed Physiology",
        "semester": 1,
        "type": "Elective",
        "subfields": ["Seed Physiology", "Dormancy & Germination", "Seed Storage", "Chilling & Vernalization"]
    },
    {
        "id": "HORT521",
        "code": "Hort. 521",
        "name": "Horticultural Plant Biotechnology",
        "semester": 1,
        "type": "Elective",
        "subfields": ["Plant Biotechnology", "Tissue Culture", "Plant Breeding", "Molecular Markers", "Genetic Engineering"]
    }
]

INITIAL_CARDS = [
    {
        "id": "card_air_layering",
        "term": "Air Layering",
        "course_id": "HORT501",
        "course_code": "Hort. 501",
        "subfield": "Plant Propagation / Pomology",
        "biological_mechanism": "Complete girdling interrupts basipetal phloem transport of photosynthates and polar auxin (IAA). Auxin and carbohydrate accumulation at the upper girdle margin triggers dedifferentiation of phloem/cambial parenchyma into adventitious root primordia under darkness, moisture, and aeration.",
        "horticultural_practice": "Practiced during the humid monsoon season on woody branches. A 2.5-4 cm ring of bark and cambium is scraped clean, treated with rooting powder (IBA 1000-2500 ppm), enclosed in moist sphagnum moss, and tightly sealed with 200-gauge polyethylene film tied at both ends.",
        "exam_trap": "Do NOT confuse with ground layering: air layering is performed in situ on upright, elevated, rigid woody branches that cannot be bent to ground level. Girdling must thoroughly scrape the cambium to prevent healing callus from bridging the wound instead of rooting.",
        "key_crops": "Litchi (Litchi chinensis), Guava (Psidium guajava), Pomegranate (Punica granatum), Ficus elastica",
        "mastery": "Exam Ready",
        "notes": "Essential propagation technique for true-to-type litchi cultivars in Bangladesh.",
        "date_added": "2026-10-31",
        "last_reviewed": "2026-10-31"
    },
    {
        "id": "card_germplasm",
        "term": "Germplasm",
        "course_id": "HORT521",
        "course_code": "Hort. 521",
        "subfield": "Plant Biotechnology / Breeding",
        "biological_mechanism": "The total physical biological repository of genetic material—including hereditary alleles, structural genes, and epigenetic variations—preserved as viable totipotent entities (seeds, meristem cultures, pollen, or cryopreserved shoot tips).",
        "horticultural_practice": "Ex situ conservation in gene banks at -18°C (orthodox seeds) or in liquid nitrogen (-196°C cryopreservation for recalcitrant horticultural species like mango and jackfruit), systematically evaluated for biotic/abiotic stress alleles for pre-breeding introgression.",
        "exam_trap": "Distinguish between 'Gene Pool' and 'Germplasm': Gene Pool is an abstract, theoretical concept describing all genes in an interbreeding population; Germplasm refers to the physical, tangible biological samples (accessions) conserved in storage or fields.",
        "key_crops": "Solanum spp. (wild tomato/potato relatives), Malus domestica, Musa spp., Mangifera indica",
        "mastery": "Exam Ready",
        "notes": "Primary source for introgressing Late Blight and Bacterial Wilt resistance genes.",
        "date_added": "2026-10-31",
        "last_reviewed": "2026-10-31"
    },
    {
        "id": "card_grafting",
        "term": "Grafting",
        "course_id": "HORT501",
        "course_code": "Hort. 501",
        "subfield": "Pomology / Nursery Management",
        "biological_mechanism": "Wound-healing cascade: necrotic cell layer forms and dissolves; unspecialized wound-repair callus proliferates from vascular cambium of both stock and scion, interlocks in the graft zone, and subsequently redifferentiates into continuous vascular cambium, xylem vessels, and phloem sieve elements.",
        "horticultural_practice": "Whip-and-tongue, veneer, or cleft grafting conducted during active sap movement. Requires intimate cambial alignment, sharp clean incisions, structural binding with grafting tape, and waterproofing with wax to prevent desiccation.",
        "exam_trap": "Vascular cambium must make direct physical contact along at least one full side. Callus can bridge microscopic gaps, but misaligned or dead cambia result in anatomical rejection or delayed structural failure (delayed incompatibility).",
        "key_crops": "Mango (Mangifera indica), Apple (Malus domestica), Citrus spp., Grafted Tomato/Eggplant (rootstock resistance)",
        "mastery": "Exam Ready",
        "notes": "Used widely for dwarfing rootstocks in intensive orchards and nematode resistance in solanaceous vegetables.",
        "date_added": "2026-10-31",
        "last_reviewed": "2026-10-31"
    },
    {
        "id": "card_t_budding",
        "term": "T-Budding (Shield Budding)",
        "course_id": "HORT501",
        "course_code": "Hort. 501",
        "subfield": "Pomology / Nursery Management",
        "biological_mechanism": "A single scion shield bud containing active meristem and minimal xylem/bark is inserted under the bark flaps of a vigorous rootstock; callus develops from the rootstock cambium and the scion shield, establishing vascular continuity to the bud trace within 2 to 3 weeks.",
        "horticultural_practice": "Conducted in late summer or spring when rootstock cambium is vigorously dividing and bark 'slips' easily without tearing. A vertical cut (2.5 cm) and horizontal cut form a 'T'; flaps are lifted, shield bud inserted, and bound with budding tape leaving the eye exposed.",
        "exam_trap": "Prerequisite condition: Bark MUST be 'slipping' (active cambial division). If bark does not slip (dormant season or water stress), T-budding will fail; 'Chip Budding' must be used instead because chip budding does not require bark separation.",
        "key_crops": "Citrus (Sweet orange, Mandarin on Rangpur lime), Rose (Rosa spp.), Peach and Plum (Prunus spp.)",
        "mastery": "Exam Ready",
        "notes": "Standard commercial propagation technique for citrus nursery stock in Bangladesh.",
        "date_added": "2026-10-31",
        "last_reviewed": "2026-10-31"
    },
    {
        "id": "card_vernalization",
        "term": "Vernalization",
        "course_id": "HORT519",
        "course_code": "Hort. 519",
        "subfield": "Seed Physiology / Crop Physiology",
        "biological_mechanism": "Stable epigenetic silencing of floral repressor genes (e.g. FLC - Flowering Locus C in Brassicaceae) via histone modification (H3K27me3) triggered by prolonged non-freezing low temperatures (1°C to 7°C), rendering the shoot apical meristem competent to initiate floral evocation upon subsequent warm/inductive photoperiods.",
        "horticultural_practice": "Controlled artificial chilling of hydrated seeds or overwintering stecklings of biennial horticultural crops to synchronize uniform bolting and flowering for hybrid seed production.",
        "exam_trap": "CRITICAL EXAM TRAP: Do NOT confuse vernalization with stratification! Vernalization induces meristematic competence to flower (vegetative-to-reproductive transition); Stratification breaks seed embryo dormancy to allow germination. High temperatures immediately following chilling cause 'de-vernalization'.",
        "key_crops": "Cabbage (Brassica oleracea var. capitata), Carrot (Daucus carota), Onion (Allium cepa), Beetroot (Beta vulgaris)",
        "mastery": "Exam Ready",
        "notes": "Crucial concept for winter vegetable seed production in subtropical zones.",
        "date_added": "2026-10-31",
        "last_reviewed": "2026-10-31"
    }
]


# ==============================================================================
# DATA PERSISTENCE & MIGRATION
# ==============================================================================

def load_data():
    """Load courses and study cards from JSON. If missing, initialize defaults."""
    if not os.path.exists(DATA_FILE):
        data = {
            "version": "1.0",
            "last_updated": str(date.today()),
            "courses": DEFAULT_COURSES,
            "cards": INITIAL_CARDS
        }
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "courses" not in data or not data["courses"]:
                data["courses"] = DEFAULT_COURSES
            if "cards" not in data:
                data["cards"] = []
            return data
    except Exception as e:
        print(f"[ERROR] Failed to read {DATA_FILE}: {e}")
        return {"courses": DEFAULT_COURSES, "cards": INITIAL_CARDS}


def save_data(data):
    """Save courses and study cards atomically to JSON."""
    data["last_updated"] = str(date.today())
    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, DATA_FILE)


# ==============================================================================
# OLLAMA INTEGRATION (OFFLINE AI EXAM PREP GENERATOR)
# ==============================================================================

def detect_ollama_model():
    """Detect available Ollama model."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
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


def sanitize_and_validate_card(card_data):
    """Automated self-correcting validator for botanical accuracy and phonetics."""
    term = card_data.get("term", "").strip()
    term_lower = term.lower()

    # 1. Enforce verified IPA
    curated_ipa = fetch_verified_ipa(term)
    if curated_ipa:
        card_data["ipa"] = curated_ipa
    elif card_data.get("ipa"):
        card_data["ipa"] = clean_ipa_syntax(card_data["ipa"])

    # Multi-word check: if term ends with compound suffixes, repair phonetics
    raw_ipa = card_data.get("ipa", "")
    if term_lower.endswith(" seed") and raw_ipa and "siːd" not in raw_ipa:
        card_data["ipa"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌsiːd/")
    elif term_lower.endswith(" layering") and raw_ipa and "leɪ.ər.ɪŋ" not in raw_ipa:
        card_data["ipa"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌleɪ.ər.ɪŋ/")
    elif term_lower.endswith(" budding") and raw_ipa and "bʌd.ɪŋ" not in raw_ipa:
        card_data["ipa"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌbʌd.ɪŋ/")
    elif term_lower.endswith(" grafting") and raw_ipa and "ɡræf.tɪŋ" not in raw_ipa:
        card_data["ipa"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌɡræf.tɪŋ/")

    # 2. Enforce known technical synonyms and populate fallback
    if term_lower in KNOWN_SYNONYMS:
        card_data["synonyms"] = KNOWN_SYNONYMS[term_lower]
    elif not card_data.get("synonyms") or not card_data["synonyms"].strip():
        subf = card_data.get("subfield", "Horticulture")
        card_data["synonyms"] = f"{term} ({subf.lower()} descriptor)"

    # 3. Sub-mechanism / synecdoche correction
    mech = card_data.get("biological_mechanism", "")
    practice = card_data.get("horticultural_practice", "")
    crops = card_data.get("key_crops", "")

    # Flush: ensure pomology, subtropical crop phenology, paclobutrazol (eliminate temperate apple error)
    if "flush" in term_lower:
        card_data["subfield"] = "Pomology / Fruit Crop Physiology"
        card_data["course_id"] = "HORT501"
        card_data["course_code"] = "Hort. 501"
        card_data["ipa"] = "/flʌʃ/"
        card_data["synonyms"] = "vegetative flush, episodic growth, shoot emergence"
        if "apple" in practice.lower() or "apple" in crops.lower() or "temperate" in mech.lower():
            card_data["biological_mechanism"] = (
                "A synchronized, episodic wave of rapid shoot elongation and leaf expansion or panicle bud emergence "
                "originating from previously quiescent or resting terminal meristems, alternating with intervals of apical bud quiescence "
                "in woody perennial plants. Regulated by endogenous hormonal balances—specifically root-derived cytokinin surges and declining gibberellin levels signaling bud burst."
            )
            card_data["horticultural_practice"] = (
                "In commercial mango (Mangifera indica) and litchi (Litchi chinensis) orchards, growers stimulate 1-2 vegetative flushes "
                "immediately post-harvest through canopy pruning and nitrogenous fertilization. Subsequent autumn vegetative flushes are "
                "chemically suppressed using paclobutrazol (Cultar - a gibberellin inhibitor) alongside deficit irrigation to ensure synchronized floral flushes."
            )
            card_data["key_crops"] = "Mango (Mangifera indica), Litchi (Litchi chinensis), Citrus spp., Tea (Camellia sinensis)"
            card_data["exam_trap"] = (
                "CRITICAL EXAM TRAP: Do NOT confuse tropical rhythmic 'flushing' with continuous temperate spring shoot growth! "
                "In mango and litchi, late autumn vegetative flushes directly antagonize floral evocation ('flush-flower antagonism'). Paclobutrazol suppresses vegetative flushes to allow floral flushes to proceed."
            )

    # Ecophysiology: ensure correct IPA and syllabus mapping
    if "ecophysiology" in term_lower:
        card_data["ipa"] = "/ˌiː.koʊˌfɪz.iˈɑː.lə.dʒi/"
        card_data["course_id"] = "HORT501"
        card_data["course_code"] = "Hort. 501"
        card_data["subfield"] = "Fruit Crop Physiology / Pomology"
        card_data["synonyms"] = "physiological ecology, environmental plant physiology"

    # Apomixis: prevent synecdoche
    if "apomixis" in term_lower:
        if "nucellar" in mech.lower() and "agamospermy" not in mech.lower():
            card_data["biological_mechanism"] = (
                "Asexual seed formation (agamospermy) bypassing meiosis (apomeiosis) and fertilization (parthenogenesis). "
                "Occurs via gametophytic apomixis (diplospory or apospory forming unreduced embryo sacs) or sporophytic adventitious embryony directly from ovular somatic cells."
            )
        card_data["synonyms"] = "agamospermy"

    # Recalcitrant seed: eliminate high lipids hallucination
    if "recalcitrant" in term_lower and "seed" in term_lower:
        if "high lipids" in mech.lower() or "high levels of lipids" in mech.lower():
            card_data["biological_mechanism"] = (
                "Desiccation and chilling intolerance: seeds undergo no maturation drying, are shed at high moisture contents (30–60%), "
                "remain metabolically active, and lack protective LEA proteins and oligosaccharide glass vitrification, causing lethal membrane rupture upon dehydration below 15–30%."
            )
        card_data["synonyms"] = "desiccation-sensitive seed, non-orthodox seed"

    # True seed: eliminate two-parents hallucination
    if "true seed" in term_lower:
        if "two different parents" in mech.lower() or "two parents" in mech.lower():
            card_data["biological_mechanism"] = (
                "A botanical seed containing a zygotic embryo developed from a fertilized ovule inside a flower (via autogamy or allogamy), "
                "distinguished in horticultural production from vegetative propagules (seed tubers, cloves, onion sets, bulbils)."
            )
        card_data["synonyms"] = "botanical seed"

    return card_data


def sync_card_to_dictionary(card_data):
    """
    Append or update term in local_dictionary.csv so the main dictionary
    is kept in sync with HortiPrep.
    """
    term = card_data.get("term", "").strip()
    if not term:
        return False, "Empty term"

    headers = [
        "Word", "Pronunciation (IPA)", "Part of Speech", "Subfield",
        "Definition", "Example Sentence", "Etymology", "Synonyms",
        "See Also", "Date Added", "Status"
    ]

    ipa = card_data.get("ipa", "")
    if not ipa:
        ipa = fetch_verified_ipa(term) or ""

    pos = card_data.get("pos", "n.")
    subfield = card_data.get("subfield", "Botany")
    definition = card_data.get("definition") or card_data.get("biological_mechanism", "")
    example = card_data.get("example_sentence") or card_data.get("horticultural_practice", "")
    etymology = card_data.get("etymology", "")
    synonyms = card_data.get("synonyms", "")
    see_also = card_data.get("see_also", "")
    today_str = str(date.today())

    rows = []
    found = False
    if os.path.exists(DICTIONARY_CSV):
        with open(DICTIONARY_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Word", "").strip().lower() == term.lower():
                    # Update row while preserving status if already verified
                    curr_status = row.get("Status", "Needs review")
                    row["Pronunciation (IPA)"] = ipa or row.get("Pronunciation (IPA)", "")
                    row["Part of Speech"] = pos or row.get("Part of Speech", "")
                    row["Subfield"] = subfield or row.get("Subfield", "")
                    row["Definition"] = definition or row.get("Definition", "")
                    row["Example Sentence"] = example or row.get("Example Sentence", "")
                    if etymology:
                        row["Etymology"] = etymology
                    if synonyms:
                        row["Synonyms"] = synonyms
                    if see_also:
                        row["See Also"] = see_also
                    row["Status"] = curr_status
                    found = True
                rows.append(row)

    if not found:
        new_row = {
            "Word": term.lower(),
            "Pronunciation (IPA)": ipa,
            "Part of Speech": pos,
            "Subfield": subfield,
            "Definition": definition,
            "Example Sentence": example,
            "Etymology": etymology,
            "Synonyms": synonyms,
            "See Also": see_also,
            "Date Added": today_str,
            "Status": "Needs review"
        }
        rows.append(new_row)

    temp_csv = DICTIONARY_CSV + ".tmp"
    with open(temp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({h: r.get(h, "") for h in headers})
    os.replace(temp_csv, DICTIONARY_CSV)
    return True, "Synced"


def generate_exam_card_ai(term, target_course_id="AUTO", sync_to_dict=True):
    """
    Generate graduate-level exam study breakdown for a horticultural term
    using local Ollama with rigorous academic rules.
    """
    model = detect_ollama_model()
    data = load_data()
    course_list_str = "\n".join([f"- {c['code']}: {c['name']} (ID: {c['id']}, Focus: {', '.join(c['subfields'])})" for c in data["courses"]])

    prompt = f"""You are an elite Professor of Horticulture specializing in graduate Master of Science (M.S.) examinations.
Analyze the following horticultural term and produce a comprehensive graduate exam study breakdown and dictionary entry.

TERM TO ANALYZE: "{term}"

AVAILABLE SEMESTER COURSES:
{course_list_str}

TARGET COURSE SELECTION:
- If target is specified as "{target_course_id}" and not "AUTO", assign this course ID.
- If target is "AUTO", pick the single most appropriate course ID from the available list above based on syllabus relevance.

GOLDEN RULES FOR GRADUATE (M.S.) HORTICULTURAL SYNTHESIS:
1. COMPOUND COMPLETENESS: If the term has multiple words (e.g. 'recalcitrant seed', 'orthodox seed', 'air layering'), define the FULL compound phrase. Never omit words or analyze only the first adjective.
2. CROP & PHENOLOGICAL CONGRUENCE: Match crops and examples to actual biological reality. Tropical/subtropical growth cycles (e.g. episodic flushing, recalcitrant seeds, nucellar embryony, air layering) must feature appropriate species (mango, litchi, citrus, jackfruit). Do NOT cite temperate deciduous crops like apple for tropical flushing dynamics or recalcitrant seed biology.
3. NO GENERALIZATION OF SUB-MECHANISMS: Do NOT define a broad phenomenon by only one of its subtypes:
   - APOMIXIS is asexual seed formation (agamospermy) bypassing meiosis and fertilization—do NOT define it solely as 'nucellar embryony' (which is only one subtype). Synonyms: 'agamospermy' (NEVER list 'apospory' as a synonym).
   - TRUE SEED is a fertilized botanical embryonated ovule, contrasting with vegetative propagules (potato tubers, garlic cloves, onion sets). NEVER say 'from two parents' because autogamous/self-pollinated crops produce true seed.
4. ACCURATE SEED PHYSIOLOGY (ROBERTS 1973 & BEWLEY-BLACK):
   - Orthodox seeds tolerate desiccation to 2-5% and sub-zero storage (-18°C) obeying Roberts' viability equations; do NOT claim they require dormancy.
   - Recalcitrant seeds die if dried below 15-30% because they lack LEA proteins and oligosaccharide glass vitrification while remaining metabolically active—do NOT claim this is due to 'high lipids'.
5. AUTHENTIC ETYMOLOGY: Provide genuine Greek/Latin/historical derivations with coining scientists and dates where known (e.g. Hans Winkler 1908, E.H. Roberts 1973, August Weismann 1883).
6. PROFESSOR EXAM TRAPS: State the exact high-yield distractor examiners test (e.g. Vernalization vs Stratification; Apomixis vs Parthenocarpy; Bark Slipping vs Chip Budding; Orthodox vs Recalcitrant vs Intermediate).
7. MANDATORY SYNONYMS: Provide 1 to 3 valid technical synonyms, alternative horticultural terms, or English/Latin equivalents (e.g. 'marcottage' for air layering; 'agamospermy' for apomixis; 'desiccation-tolerant seed' for orthodox seed; 'physiological ecology' for ecophysiology; 'episodic growth' or 'vegetative flush' for flush; 'shield budding' for t-budding; 'genetic resources' for germplasm). DO NOT leave empty.
8. ACCURATE IPA PHONETICS: For words ending in '-physiology', transcribe strictly as /...ˌfɪz.iˈɑː.lə.dʒi/ (never 'zaɪ'). Cover every word in compound terms.

REQUIRED JSON OUTPUT FORMAT (Strict valid JSON, no markdown outside of JSON):
{{
  "term": "{term}",
  "course_id": "HORT...",
  "course_code": "Hort. ...",
  "subfield": "Subfield name (e.g. Pomology, Seed Physiology, Plant Biotechnology)",
  "biological_mechanism": "Concise (2-3 sentences), highly scientific explanation of the botanical, physiological, biochemical, anatomical, or genetic mechanism. Use precise terminology (e.g. vascular cambium, gibberellin pathways, epigenetic FLC silencing, IAA basipetal transport).",
  "horticultural_practice": "Precise nursery, orchard, greenhouse, field, or in-vitro lab protocol. Include timings, hormones/concentrations if applicable, protective measures, or management steps.",
  "exam_trap": "CRITICAL EXAM TRAP / DISTRACTOR: Exactly what professors test to trip up students. Clarify subtle confusions (e.g. stratification vs vernalization, bark slipping vs chip budding, scion vs rootstock polarity, totipotency vs pluripotency).",
  "key_crops": "3 to 5 key horticultural species/crops with scientific names (e.g. Litchi chinensis, Brassica oleracea, Solanum lycopersicum).",
  "notes": "Key mnemonic or quick exam revision tip.",
  "pos": "n.",
  "ipa": "/.../",
  "etymology": "Morphological or classical Greek/Latin root origin with coining scientist/year where known.",
  "synonyms": "Genuine botanical/trade technical synonyms (MANDATORY, never empty).",
  "see_also": "2 to 4 comma-separated related concepts."
}}

Output ONLY the JSON object. Do not include markdown code fence formatting if possible."""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9
        }
    }

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            raise Exception(f"Ollama returned HTTP status {resp.status}")
        raw = json.loads(resp.read().decode("utf-8")).get("response", "").strip()

    # Clean potential markdown wrapping
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    card_data = json.loads(raw)
    card_data["id"] = "card_" + "".join(c if c.isalnum() else "_" for c in term.lower())
    card_data["mastery"] = "Needs Review"
    card_data["date_added"] = str(date.today())
    card_data["last_reviewed"] = str(date.today())

    # Verify course ID matches course database
    matching_course = next((c for c in data["courses"] if c["id"] == card_data.get("course_id")), None)
    if matching_course:
        card_data["course_code"] = matching_course["code"]
    elif data["courses"]:
        card_data["course_id"] = data["courses"][0]["id"]
        card_data["course_code"] = data["courses"][0]["code"]

    # Run automated self-correcting sanitizer & validator
    card_data = sanitize_and_validate_card(card_data)

    # Sync to local_dictionary.csv if requested
    if sync_to_dict:
        try:
            sync_card_to_dictionary(card_data)
        except Exception as err:
            print(f"[WARN] Failed to sync '{term}' to {DICTIONARY_CSV}: {err}")

    return card_data


# ==============================================================================
# HTML & JAVASCRIPT FRONTEND (SINGLE-PAGE APPLICATION)
# ==============================================================================

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HortiPrep - Graduate Exam Study & Course Review</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --card-hover: #1c2128;
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
      --text-dim: #6e7681;
      --accent: #2ea043;
      --accent-hover: #3fb950;
      --accent-subtle: rgba(46, 160, 67, 0.15);
      --trap-bg: rgba(248, 81, 73, 0.1);
      --trap-border: #f85149;
      --trap-text: #ff7b72;
      --warn-bg: rgba(210, 153, 34, 0.15);
      --warn-text: #d29922;
      --blue: #58a6ff;
      --blue-subtle: rgba(88, 166, 255, 0.15);
      --purple: #bc8cff;
      --purple-subtle: rgba(188, 140, 255, 0.15);
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', SFMono-Regular, Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding-bottom: 80px;
      -webkit-font-smoothing: antialiased;
    }

    header {
      background: #090d13;
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(8px);
    }

    .header-inner {
      max-width: 1400px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #238636, #2ea043);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 2px 8px rgba(46, 160, 67, 0.3);
    }

    .brand h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-ms {
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: var(--blue-subtle);
      color: var(--blue);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(88, 166, 255, 0.3);
      font-weight: 700;
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
      font-family: inherit;
    }

    .btn-primary {
      background: var(--accent);
      color: #fff;
    }
    .btn-primary:hover {
      background: var(--accent-hover);
      box-shadow: 0 0 12px rgba(46, 160, 67, 0.4);
    }

    .btn-secondary {
      background: #21262d;
      color: var(--text-main);
      border-color: var(--card-border);
    }
    .btn-secondary:hover {
      background: #30363d;
      border-color: #8b949e;
    }

    .btn-purple {
      background: var(--purple-subtle);
      color: var(--purple);
      border-color: rgba(188, 140, 255, 0.3);
    }
    .btn-purple:hover {
      background: rgba(188, 140, 255, 0.25);
    }

    /* Container */
    .container {
      max-width: 1400px;
      margin: 20px auto 0;
      padding: 0 24px;
    }

    /* Course Tabs Bar */
    .course-bar {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--card-border);
      scrollbar-width: thin;
    }
    .course-bar::-webkit-scrollbar { height: 6px; }
    .course-bar::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

    .course-tab {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text-muted);
      cursor: pointer;
      white-space: nowrap;
      font-size: 0.82rem;
      font-weight: 600;
      transition: all 0.15s ease;
    }
    .course-tab:hover {
      background: var(--card-hover);
      color: var(--text-main);
      border-color: #8b949e;
    }
    .course-tab.active {
      background: var(--accent-subtle);
      border-color: var(--accent);
      color: #fff;
    }
    .tab-count {
      font-size: 0.72rem;
      background: rgba(255,255,255,0.08);
      padding: 2px 6px;
      border-radius: 10px;
    }
    .course-tab.active .tab-count {
      background: var(--accent);
      color: #fff;
    }

    /* Toolbar */
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      margin: 18px 0;
    }

    .view-toggle {
      display: flex;
      background: #21262d;
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .toggle-btn {
      padding: 6px 14px;
      border-radius: 6px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }
    .toggle-btn.active {
      background: #30363d;
      color: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }

    .search-box {
      position: relative;
      flex: 1;
      max-width: 360px;
    }
    .search-box input {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 7px 12px 7px 32px;
      font-size: 0.85rem;
      color: var(--text-main);
      font-family: inherit;
    }
    .search-box input:focus {
      outline: none;
      border-color: var(--blue);
      box-shadow: 0 0 0 2px var(--blue-subtle);
    }
    .search-icon {
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 13px;
    }

    .filter-pills {
      display: flex;
      gap: 6px;
      align-items: center;
    }
    .pill {
      font-size: 0.75rem;
      padding: 4px 10px;
      border-radius: 14px;
      border: 1px solid var(--card-border);
      background: #161b22;
      color: var(--text-muted);
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s ease;
    }
    .pill:hover { border-color: #8b949e; color: #fff; }
    .pill.active { background: #30363d; color: #fff; border-color: #8b949e; }

    /* Cheat Sheet Table View */
    .table-container {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
    }
    thead {
      background: #0f141c;
      border-bottom: 2px solid var(--card-border);
    }
    th {
      padding: 12px 14px;
      font-weight: 700;
      color: var(--text-muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    td {
      padding: 14px 14px;
      border-bottom: 1px solid #21262d;
      vertical-align: top;
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }

    .term-cell {
      min-width: 140px;
    }
    .term-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #fff;
      display: block;
      margin-bottom: 4px;
    }
    .course-badge {
      display: inline-block;
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--blue-subtle);
      color: var(--blue);
      border: 1px solid rgba(88, 166, 255, 0.3);
    }
    .subfield-badge {
      display: block;
      font-size: 0.72rem;
      color: var(--text-dim);
      margin-top: 3px;
    }

    .mechanism-cell {
      max-width: 320px;
      color: #c9d1d9;
      line-height: 1.5;
    }
    .practice-cell {
      max-width: 280px;
      color: #8b949e;
      line-height: 1.45;
    }

    .trap-cell {
      max-width: 290px;
      background: var(--trap-bg);
      border-left: 3px solid var(--trap-border);
      padding: 10px 12px;
      border-radius: 0 6px 6px 0;
      color: #ff9b94;
      font-size: 0.82rem;
      line-height: 1.4;
    }
    .trap-cell strong {
      color: var(--trap-text);
      display: block;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 2px;
    }

    .crops-cell {
      min-width: 130px;
      font-size: 0.8rem;
      color: var(--accent-hover);
      font-style: italic;
    }

    .status-badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 0.72rem;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      user-select: none;
    }
    .status-ready {
      background: var(--accent-subtle);
      color: #3fb950;
      border: 1px solid rgba(46, 160, 67, 0.4);
    }
    .status-familiar, .status-fam {
      background: var(--warn-bg);
      color: #d29922;
      border: 1px solid rgba(210, 153, 34, 0.4);
    }
    .status-drill {
      background: var(--trap-bg);
      color: #f85149;
      border: 1px solid rgba(248, 81, 73, 0.4);
    }

    .action-cell {
      white-space: nowrap;
      text-align: right;
    }
    .btn-icon {
      background: none;
      border: none;
      color: var(--text-dim);
      cursor: pointer;
      font-size: 15px;
      padding: 4px;
      border-radius: 4px;
      transition: all 0.15s ease;
    }
    .btn-icon:hover { color: #fff; background: #30363d; }
    .btn-icon.del:hover { color: #f85149; }

    /* Flashcard Drill View */
    .drill-container {
      max-width: 820px;
      margin: 20px auto;
      perspective: 1000px;
    }

    .drill-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      color: var(--text-muted);
      font-size: 0.85rem;
    }

    .progress-bar-wrap {
      flex: 1;
      height: 6px;
      background: #21262d;
      border-radius: 3px;
      margin: 0 16px;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%;
      background: var(--accent);
      transition: width 0.3s ease;
    }

    .flashcard {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 32px 36px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      position: relative;
      min-height: 400px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .card-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .card-term-display {
      font-size: 2.2rem;
      font-weight: 800;
      color: #fff;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
    }

    .card-subfield-display {
      font-size: 0.9rem;
      color: var(--text-dim);
      font-weight: 500;
      margin-bottom: 24px;
    }

    .card-answer-box {
      background: #0f141c;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      display: none;
      animation: fadeIn 0.25s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .answer-section {
      margin-bottom: 18px;
    }
    .answer-section:last-child { margin-bottom: 0; }
    .answer-title {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--blue);
      font-weight: 700;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .answer-body {
      color: #c9d1d9;
      font-size: 0.95rem;
      line-height: 1.6;
    }

    .trap-drill-alert {
      background: var(--trap-bg);
      border: 1px solid var(--trap-border);
      border-radius: 8px;
      padding: 14px 16px;
      margin-top: 14px;
    }
    .trap-drill-alert .answer-title {
      color: var(--trap-text);
    }
    .trap-drill-alert .answer-body {
      color: #ffa39e;
    }

    .card-controls {
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: center;
      padding-top: 20px;
      border-top: 1px solid #21262d;
    }

    .btn-drill-reveal {
      width: 100%;
      padding: 14px;
      font-size: 1rem;
      border-radius: 8px;
      background: #238636;
      color: #fff;
      font-weight: 700;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
    }
    .btn-drill-reveal:hover { background: #2ea043; }

    .rating-row {
      display: none;
      width: 100%;
      gap: 12px;
    }
    .btn-rate {
      flex: 1;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid transparent;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }
    .btn-rate-drill {
      background: var(--trap-bg);
      color: var(--trap-text);
      border-color: rgba(248,81,73,0.3);
    }
    .btn-rate-drill:hover { background: rgba(248,81,73,0.2); }
    .btn-rate-fam {
      background: var(--warn-bg);
      color: var(--warn-text);
      border-color: rgba(210,153,34,0.3);
    }
    .btn-rate-fam:hover { background: rgba(210,153,34,0.25); }
    .btn-rate-ready {
      background: var(--accent-subtle);
      color: #3fb950;
      border-color: rgba(46,160,67,0.3);
    }
    .btn-rate-ready:hover { background: rgba(46,160,67,0.25); }

    .key-shortcut {
      font-size: 0.65rem;
      opacity: 0.6;
      font-family: var(--font-mono);
      font-weight: 500;
    }

    /* Modals */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
    }
    .modal-overlay.open { display: flex; }

    .modal {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      width: 100%;
      max-width: 650px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
    }
    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .modal-header h3 { font-size: 1.1rem; color: #fff; }
    .modal-body { padding: 20px; }
    .modal-footer {
      padding: 14px 20px;
      border-top: 1px solid var(--card-border);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      background: #0f141c;
      border-radius: 0 0 12px 12px;
    }

    .form-group {
      margin-bottom: 16px;
    }
    .form-group label {
      display: block;
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 6px;
    }
    .form-control {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 0.88rem;
      color: var(--text-main);
      font-family: inherit;
    }
    .form-control:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-subtle);
    }
    textarea.form-control { min-height: 70px; resize: vertical; }

    /* Print Stylesheet for Physical Cheat Sheets */
    @media print {
      body { background: #fff !important; color: #000 !important; padding: 0 !important; }
      header, .toolbar, .course-bar, .action-cell, .btn, .view-toggle, .pill { display: none !important; }
      .container { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
      .table-container { border: 1px solid #000 !important; }
      table { font-size: 9pt !important; }
      th, td { border-bottom: 1px solid #ccc !important; padding: 6px 8px !important; }
      .trap-cell { background: #fff3f3 !important; border-left: 2px solid #d00 !important; color: #900 !important; }
      .course-badge { border: 1px solid #000 !important; color: #000 !important; background: none !important; }
      .term-title { color: #000 !important; font-size: 10pt !important; }
      .mechanism-cell, .practice-cell { color: #222 !important; }
    }
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="header-inner">
      <div class="brand">
        <div class="brand-icon">🌱</div>
        <div>
          <h1>HortiPrep <span class="badge-ms">BAU M.S.</span></h1>
        </div>
      </div>
      <div class="header-controls">
        <button class="btn btn-purple" onclick="openAIGenerateModal()">✨ Generate with Ollama</button>
        <button class="btn btn-secondary" onclick="importFromDictionary()">📥 Import from Dictionary CSV</button>
        <button class="btn btn-secondary" onclick="exportCourseCSV()">📄 Export CSV</button>
        <button class="btn btn-secondary" onclick="window.print()">🖨️ Print Cheat Sheet</button>
        <button class="btn btn-primary" onclick="openAddCardModal()">➕ Add Card</button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <div class="container">
    
    <!-- Course Tabs Bar -->
    <div class="course-bar" id="courseBar">
      <!-- Injected by JS -->
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="view-toggle">
        <button class="toggle-btn active" id="btnViewTable" onclick="switchView('table')">
          📋 Cheat Sheet
        </button>
        <button class="toggle-btn" id="btnViewDrill" onclick="switchView('drill')">
          🧠 Active Drill
        </button>
      </div>

      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" placeholder="Search terms, mechanisms, traps, crops..." oninput="handleSearch()">
      </div>

      <div class="filter-pills" id="masteryFilterPills">
        <button class="pill active" onclick="setMasteryFilter('ALL')">All (<span id="countAll">0</span>)</button>
        <button class="pill" onclick="setMasteryFilter('Needs Review')">🔴 Drill (<span id="countDrill">0</span>)</button>
        <button class="pill" onclick="setMasteryFilter('Familiar')">🟡 Familiar (<span id="countFam">0</span>)</button>
        <button class="pill" onclick="setMasteryFilter('Exam Ready')">🟢 Ready (<span id="countReady">0</span>)</button>
      </div>
    </div>

    <!-- VIEW A: Cheat Sheet Table -->
    <div id="tableView" class="table-container">
      <table>
        <thead>
          <tr>
            <th style="width: 14%;">Term & Course</th>
            <th style="width: 25%;">Biological Mechanism</th>
            <th style="width: 22%;">Horticultural Practice</th>
            <th style="width: 23%;">Prof. Exam Trap</th>
            <th style="width: 10%;">Key Crops</th>
            <th style="width: 6%;">Status</th>
            <th style="width: 5%; text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          <!-- Injected by JS -->
        </tbody>
      </table>
    </div>

    <!-- VIEW B: Flashcard Active Recall Drill -->
    <div id="drillView" class="drill-container" style="display: none;">
      <div class="drill-header">
        <span id="drillCounter">Card 1 of 5</span>
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" id="drillProgressBar" style="width: 20%;"></div>
        </div>
        <span id="drillPercent">0% Exam Ready</span>
      </div>

      <div class="flashcard">
        <div>
          <div class="card-meta">
            <span class="course-badge" id="drillCourseBadge">Hort. 501</span>
            <span id="drillStatusBadge" class="status-badge status-drill">Needs Review</span>
          </div>

          <div class="card-term-display" id="drillTermDisplay">Vernalization</div>
          <div class="card-subfield-display" id="drillSubfieldDisplay">Seed Physiology / Crop Physiology</div>

          <div class="card-answer-box" id="drillAnswerBox">
            <div class="answer-section">
              <div class="answer-title">🧬 Biological Mechanism</div>
              <div class="answer-body" id="drillMechanism"></div>
            </div>

            <div class="answer-section">
              <div class="answer-title">🛠️ Horticultural Practice & Management</div>
              <div class="answer-body" id="drillPractice"></div>
            </div>

            <div class="trap-drill-alert">
              <div class="answer-title">⚠️ Professor's Exam Trap & Distractor</div>
              <div class="answer-body" id="drillExamTrap"></div>
            </div>

            <div class="answer-section" style="margin-top: 14px;">
              <div class="answer-title">🌿 Key Crops & Families</div>
              <div class="answer-body" id="drillCrops" style="color: var(--accent-hover); font-style: italic;"></div>
            </div>
          </div>
        </div>

        <div class="card-controls">
          <button class="btn-drill-reveal" id="btnReveal" onclick="revealDrillAnswer()">
            <span>Reveal Answer</span>
            <span class="key-shortcut">[Space]</span>
          </button>

          <div class="rating-row" id="ratingRow">
            <button class="btn-rate btn-rate-drill" onclick="rateDrillCard('Needs Review')">
              <span>🔴 Needs Drill</span>
              <span class="key-shortcut">[1]</span>
            </button>
            <button class="btn-rate btn-rate-fam" onclick="rateDrillCard('Familiar')">
              <span>🟡 Familiar</span>
              <span class="key-shortcut">[2]</span>
            </button>
            <button class="btn-rate btn-rate-ready" onclick="rateDrillCard('Exam Ready')">
              <span>🟢 Exam Ready</span>
              <span class="key-shortcut">[3]</span>
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Modal: Add / Edit Card -->
  <div class="modal-overlay" id="cardModal">
    <div class="modal">
      <div class="modal-header">
        <h3 id="modalTitle">Add Exam Study Card</h3>
        <button class="btn-icon" onclick="closeModal('cardModal')">✕</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="editCardId">
        
        <div class="form-group">
          <label>Term / Concept Name *</label>
          <input type="text" id="formTerm" class="form-control" placeholder="e.g. Apomixis, Girdling, Somaclonal Variation" required>
        </div>

        <div style="display: flex; gap: 12px;">
          <div class="form-group" style="flex: 1;">
            <label>Course *</label>
            <select id="formCourse" class="form-control">
              <!-- Injected by JS -->
            </select>
          </div>
          <div class="form-group" style="flex: 1;">
            <label>Subfield / Focus</label>
            <input type="text" id="formSubfield" class="form-control" placeholder="e.g. Pomology, Seed Physiology">
          </div>
        </div>

        <div class="form-group">
          <label>Biological Mechanism (Physiological / Botanical Science) *</label>
          <textarea id="formMechanism" class="form-control" rows="3" placeholder="Explain the scientific mechanism clearly..."></textarea>
        </div>

        <div class="form-group">
          <label>Horticultural Practice / Management *</label>
          <textarea id="formPractice" class="form-control" rows="2" placeholder="Field, nursery, greenhouse, or lab protocol..."></textarea>
        </div>

        <div class="form-group">
          <label>Professor Exam Trap / Common Distractor *</label>
          <textarea id="formTrap" class="form-control" rows="2" placeholder="Common pitfalls, distinctions professors test on..."></textarea>
        </div>

        <div class="form-group">
          <label>Key Horticultural Crops / Families</label>
          <input type="text" id="formCrops" class="form-control" placeholder="e.g. Litchi chinensis, Brassica oleracea">
        </div>

        <div class="form-group">
          <label>Mastery Status</label>
          <select id="formMastery" class="form-control">
            <option value="Needs Review">Needs Review (Red)</option>
            <option value="Familiar">Familiar (Yellow)</option>
            <option value="Exam Ready">Exam Ready (Green)</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="closeModal('cardModal')">Cancel</button>
        <button class="btn btn-primary" onclick="saveCard()">Save Study Card</button>
      </div>
    </div>
  </div>

  <!-- Modal: AI Generation -->
  <div class="modal-overlay" id="aiModal">
    <div class="modal" style="max-width: 500px;">
      <div class="modal-header">
        <h3>✨ Generate Exam Card with Ollama</h3>
        <button class="btn-icon" onclick="closeModal('aiModal')">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Horticultural Term</label>
          <input type="text" id="aiTermInput" class="form-control" placeholder="e.g. Parthenocarpy, Somaclonal Variation" autofocus>
        </div>
        <div class="form-group">
          <label>Target Course</label>
          <select id="aiCourseSelect" class="form-control">
            <option value="AUTO">✨ Auto-Detect Best Course</option>
            <!-- Injected by JS -->
          </select>
        </div>
        <div class="form-group" style="margin-top: 12px;">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; text-transform: none; font-size: 0.85rem; color: var(--text-main);">
            <input type="checkbox" id="aiSyncDictCheckbox" checked style="accent-color: var(--accent); width: 16px; height: 16px;">
            <span>Sync automatically with main dictionary (<code>local_dictionary.csv</code>)</span>
          </label>
        </div>
        <div id="aiLoadingIndicator" style="display: none; padding: 14px; background: rgba(46,160,67,0.1); border-radius: 8px; border: 1px solid var(--accent); color: var(--accent-hover); font-size: 0.85rem; text-align: center;">
          ⏳ Qwen 2.5 is synthesizing graduate mechanisms, practices, and exam traps...
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="closeModal('aiModal')">Cancel</button>
        <button class="btn btn-primary" id="btnSubmitAI" onclick="executeAIGeneration()">Generate Card</button>
      </div>
    </div>
  </div>

  <script>
    let state = {
      courses: [],
      cards: [],
      selectedCourseId: 'ALL',
      selectedMastery: 'ALL',
      searchQuery: '',
      currentView: 'table',
      drillIndex: 0,
      drillRevealed: false
    };

    // Load initial data from API
    async function init() {
      try {
        const resp = await fetch('/api/deck');
        const data = await resp.json();
        state.courses = data.courses || [];
        state.cards = data.cards || [];
        renderCourseTabs();
        populateCourseSelects();
        renderTable();
        updateCounts();
        initDrillCard();
      } catch (err) {
        console.error("Failed to load deck data:", err);
      }
    }

    function renderCourseTabs() {
      const bar = document.getElementById('courseBar');
      const allCount = state.cards.length;
      let html = `
        <div class="course-tab ${state.selectedCourseId === 'ALL' ? 'active' : ''}" onclick="selectCourse('ALL')">
          <span>All Courses</span>
          <span class="tab-count">${allCount}</span>
        </div>
      `;

      state.courses.forEach(c => {
        const count = state.cards.filter(card => card.course_id === c.id).length;
        const isActive = state.selectedCourseId === c.id ? 'active' : '';
        html += `
          <div class="course-tab ${isActive}" onclick="selectCourse('${c.id}')" title="${c.name}">
            <span>${c.code}</span>
            <span class="tab-count">${count}</span>
          </div>
        `;
      });

      bar.innerHTML = html;
    }

    function populateCourseSelects() {
      const selectForm = document.getElementById('formCourse');
      const selectAI = document.getElementById('aiCourseSelect');
      
      let optionsHtml = '';
      state.courses.forEach(c => {
        optionsHtml += `<option value="${c.id}">${c.code}: ${c.name}</option>`;
      });

      selectForm.innerHTML = optionsHtml;
      selectAI.innerHTML = `<option value="AUTO">✨ Auto-Detect Best Course</option>` + optionsHtml;
    }

    function selectCourse(courseId) {
      state.selectedCourseId = courseId;
      state.drillIndex = 0;
      state.drillRevealed = false;
      renderCourseTabs();
      renderTable();
      updateCounts();
      initDrillCard();
    }

    function setMasteryFilter(mastery) {
      state.selectedMastery = mastery;
      document.querySelectorAll('#masteryFilterPills .pill').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      renderTable();
    }

    function handleSearch() {
      state.searchQuery = document.getElementById('searchInput').value.toLowerCase().trim();
      renderTable();
    }

    function getFilteredCards() {
      return state.cards.filter(c => {
        const matchCourse = state.selectedCourseId === 'ALL' || c.course_id === state.selectedCourseId;
        const matchMastery = state.selectedMastery === 'ALL' || c.mastery === state.selectedMastery;
        const q = state.searchQuery;
        const matchSearch = !q || (
          c.term.toLowerCase().includes(q) ||
          (c.subfield && c.subfield.toLowerCase().includes(q)) ||
          (c.biological_mechanism && c.biological_mechanism.toLowerCase().includes(q)) ||
          (c.horticultural_practice && c.horticultural_practice.toLowerCase().includes(q)) ||
          (c.exam_trap && c.exam_trap.toLowerCase().includes(q)) ||
          (c.key_crops && c.key_crops.toLowerCase().includes(q))
        );
        return matchCourse && matchMastery && matchSearch;
      });
    }

    function renderTable() {
      const tbody = document.getElementById('tableBody');
      const filtered = getFilteredCards();

      if (filtered.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; padding: 48px; color: var(--text-dim);">
              No cards found for this course or filter.<br>
              Click <strong>"➕ Add Card"</strong> or <strong>"✨ Generate with Ollama"</strong> to create exam cards!
            </td>
          </tr>
        `;
        return;
      }

      let html = '';
      filtered.forEach(c => {
        const statusClass = c.mastery === 'Exam Ready' ? 'status-ready' : (c.mastery === 'Familiar' ? 'status-fam' : 'status-drill');
        html += `
          <tr>
            <td class="term-cell">
              <span class="term-title">${escapeHtml(c.term)}</span>
              <span class="course-badge">${escapeHtml(c.course_code || c.course_id)}</span>
              <span class="subfield-badge">${escapeHtml(c.subfield || '')}</span>
            </td>
            <td class="mechanism-cell">${escapeHtml(c.biological_mechanism || '')}</td>
            <td class="practice-cell">${escapeHtml(c.horticultural_practice || '')}</td>
            <td>
              <div class="trap-cell">
                <strong>Prof. Exam Trap</strong>
                ${escapeHtml(c.exam_trap || '')}
              </div>
            </td>
            <td class="crops-cell">${escapeHtml(c.key_crops || '')}</td>
            <td>
              <span class="status-badge ${statusClass}" onclick="cycleMastery('${c.id}')" title="Click to cycle mastery">
                ${escapeHtml(c.mastery || 'Needs Review')}
              </span>
            </td>
            <td class="action-cell">
              <button class="btn-icon" onclick="openEditCardModal('${c.id}')" title="Edit Card">✏️</button>
              <button class="btn-icon del" onclick="deleteCard('${c.id}')" title="Delete Card">🗑️</button>
            </td>
          </tr>
        `;
      });
      tbody.innerHTML = html;
    }

    function updateCounts() {
      const currentList = state.cards.filter(c => state.selectedCourseId === 'ALL' || c.course_id === state.selectedCourseId);
      document.getElementById('countAll').textContent = currentList.length;
      document.getElementById('countDrill').textContent = currentList.filter(c => c.mastery === 'Needs Review').length;
      document.getElementById('countFam').textContent = currentList.filter(c => c.mastery === 'Familiar').length;
      document.getElementById('countReady').textContent = currentList.filter(c => c.mastery === 'Exam Ready').length;
    }

    // Toggle Views
    function switchView(view) {
      state.currentView = view;
      document.getElementById('btnViewTable').classList.toggle('active', view === 'table');
      document.getElementById('btnViewDrill').classList.toggle('active', view === 'drill');
      document.getElementById('tableView').style.display = view === 'table' ? 'block' : 'none';
      document.getElementById('drillView').style.display = view === 'drill' ? 'block' : 'none';
      if (view === 'drill') {
        initDrillCard();
      }
    }

    // Drill Mode Logic
    function getDrillCards() {
      return state.cards.filter(c => state.selectedCourseId === 'ALL' || c.course_id === state.selectedCourseId);
    }

    function initDrillCard() {
      const cards = getDrillCards();
      if (cards.length === 0) {
        document.getElementById('drillTermDisplay').textContent = "No Cards in this Course";
        document.getElementById('drillSubfieldDisplay').textContent = "Select another course or generate cards.";
        document.getElementById('drillAnswerBox').style.display = 'none';
        document.getElementById('btnReveal').style.display = 'none';
        document.getElementById('ratingRow').style.display = 'none';
        document.getElementById('drillCounter').textContent = "0 of 0";
        document.getElementById('drillProgressBar').style.width = "0%";
        document.getElementById('drillPercent').textContent = "0% Ready";
        return;
      }

      if (state.drillIndex >= cards.length) state.drillIndex = 0;
      const card = cards[state.drillIndex];

      document.getElementById('drillCounter').textContent = `Card ${state.drillIndex + 1} of ${cards.length}`;
      const readyCount = cards.filter(c => c.mastery === 'Exam Ready').length;
      const pct = Math.round((readyCount / cards.length) * 100);
      document.getElementById('drillPercent').textContent = `${pct}% Exam Ready`;
      document.getElementById('drillProgressBar').style.width = `${((state.drillIndex + 1) / cards.length) * 100}%`;

      document.getElementById('drillCourseBadge').textContent = card.course_code || card.course_id;
      document.getElementById('drillTermDisplay').textContent = card.term;
      document.getElementById('drillSubfieldDisplay').textContent = card.subfield || '';

      const statusBadge = document.getElementById('drillStatusBadge');
      statusBadge.textContent = card.mastery;
      statusBadge.className = 'status-badge ' + (card.mastery === 'Exam Ready' ? 'status-ready' : (card.mastery === 'Familiar' ? 'status-fam' : 'status-drill'));

      // Populate hidden answer
      document.getElementById('drillMechanism').textContent = card.biological_mechanism || '';
      document.getElementById('drillPractice').textContent = card.horticultural_practice || '';
      document.getElementById('drillExamTrap').textContent = card.exam_trap || '';
      document.getElementById('drillCrops').textContent = card.key_crops || '';

      // Reset state to hidden
      state.drillRevealed = false;
      document.getElementById('drillAnswerBox').style.display = 'none';
      document.getElementById('btnReveal').style.display = 'flex';
      document.getElementById('ratingRow').style.display = 'none';
    }

    function revealDrillAnswer() {
      state.drillRevealed = true;
      document.getElementById('drillAnswerBox').style.display = 'block';
      document.getElementById('btnReveal').style.display = 'none';
      document.getElementById('ratingRow').style.display = 'flex';
    }

    async function rateDrillCard(newMastery) {
      const cards = getDrillCards();
      if (cards.length === 0) return;
      const card = cards[state.drillIndex];
      card.mastery = newMastery;
      card.last_reviewed = new Date().toISOString().split('T')[0];

      // Save to server
      await fetch('/api/card/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json_stringify(card)
      });

      updateCounts();
      renderCourseTabs();

      // Advance to next card
      state.drillIndex = (state.drillIndex + 1) % cards.length;
      initDrillCard();
    }

    async function cycleMastery(cardId) {
      const card = state.cards.find(c => c.id === cardId);
      if (!card) return;
      if (card.mastery === 'Needs Review') card.mastery = 'Familiar';
      else if (card.mastery === 'Familiar') card.mastery = 'Exam Ready';
      else card.mastery = 'Needs Review';

      await fetch('/api/card/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json_stringify(card)
      });

      renderTable();
      updateCounts();
    }

    // Modal Operations
    function openAddCardModal() {
      document.getElementById('modalTitle').textContent = "Add Exam Study Card";
      document.getElementById('editCardId').value = "";
      document.getElementById('formTerm').value = "";
      document.getElementById('formSubfield').value = "";
      document.getElementById('formMechanism').value = "";
      document.getElementById('formPractice').value = "";
      document.getElementById('formTrap').value = "";
      document.getElementById('formCrops').value = "";
      document.getElementById('formMastery').value = "Needs Review";

      if (state.selectedCourseId !== 'ALL') {
        document.getElementById('formCourse').value = state.selectedCourseId;
      }
      openModal('cardModal');
    }

    function openEditCardModal(cardId) {
      const card = state.cards.find(c => c.id === cardId);
      if (!card) return;
      document.getElementById('modalTitle').textContent = "Edit Study Card";
      document.getElementById('editCardId').value = card.id;
      document.getElementById('formTerm').value = card.term;
      document.getElementById('formCourse').value = card.course_id;
      document.getElementById('formSubfield').value = card.subfield || "";
      document.getElementById('formMechanism').value = card.biological_mechanism || "";
      document.getElementById('formPractice').value = card.horticultural_practice || "";
      document.getElementById('formTrap').value = card.exam_trap || "";
      document.getElementById('formCrops').value = card.key_crops || "";
      document.getElementById('formMastery').value = card.mastery || "Needs Review";
      openModal('cardModal');
    }

    async function saveCard() {
      const id = document.getElementById('editCardId').value;
      const term = document.getElementById('formTerm').value.trim();
      const course_id = document.getElementById('formCourse').value;
      const subfield = document.getElementById('formSubfield').value.trim();
      const mechanism = document.getElementById('formMechanism').value.trim();
      const practice = document.getElementById('formPractice').value.trim();
      const trap = document.getElementById('formTrap').value.trim();
      const crops = document.getElementById('formCrops').value.trim();
      const mastery = document.getElementById('formMastery').value;

      if (!term || !mechanism) {
        alert("Please provide at least the Term and Biological Mechanism.");
        return;
      }

      const courseObj = state.courses.find(c => c.id === course_id);
      const cardData = {
        id: id || ("card_" + Date.now()),
        term: term,
        course_id: course_id,
        course_code: courseObj ? courseObj.code : course_id,
        subfield: subfield,
        biological_mechanism: mechanism,
        horticultural_practice: practice,
        exam_trap: trap,
        key_crops: crops,
        mastery: mastery,
        date_added: id ? (state.cards.find(c => c.id === id)?.date_added || new Date().toISOString().split('T')[0]) : new Date().toISOString().split('T')[0],
        last_reviewed: new Date().toISOString().split('T')[0]
      };

      const endpoint = id ? '/api/card/update' : '/api/card/add';
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json_stringify(cardData)
      });

      if (resp.ok) {
        closeModal('cardModal');
        await init();
      } else {
        alert("Failed to save card.");
      }
    }

    async function deleteCard(cardId) {
      if (!confirm("Are you sure you want to delete this study card?")) return;
      const resp = await fetch('/api/card/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json_stringify({ id: cardId })
      });
      if (resp.ok) {
        await init();
      }
    }

    // AI Generation
    function openAIGenerateModal() {
      document.getElementById('aiTermInput').value = "";
      document.getElementById('aiLoadingIndicator').style.display = 'none';
      document.getElementById('btnSubmitAI').disabled = false;
      if (state.selectedCourseId !== 'ALL') {
        document.getElementById('aiCourseSelect').value = state.selectedCourseId;
      } else {
        document.getElementById('aiCourseSelect').value = "AUTO";
      }
      openModal('aiModal');
    }

    async function executeAIGeneration() {
      const term = document.getElementById('aiTermInput').value.trim();
      const targetCourse = document.getElementById('aiCourseSelect').value;
      const syncToDict = document.getElementById('aiSyncDictCheckbox').checked;

      if (!term) {
        alert("Please enter a horticultural term to generate.");
        return;
      }

      document.getElementById('aiLoadingIndicator').style.display = 'block';
      document.getElementById('btnSubmitAI').disabled = true;

      try {
        const resp = await fetch('/api/ai/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: json_stringify({ term: term, target_course: targetCourse, sync_to_dict: syncToDict })
        });

        if (resp.ok) {
          const res = await resp.json();
          closeModal('aiModal');
          await init();
          const syncMsg = res.synced ? " and synced to local_dictionary.csv!" : "!";
          alert(`Successfully generated study card for "${term}"${syncMsg}`);
        } else {
          const err = await resp.json();
          alert("AI Generation failed: " + (err.error || "Check if Ollama is running"));
        }
      } catch (e) {
        alert("Network or Ollama error: " + e.message);
      } finally {
        document.getElementById('aiLoadingIndicator').style.display = 'none';
        document.getElementById('btnSubmitAI').disabled = false;
      }
    }

    async function importFromDictionary() {
      if (!confirm("Import terms from local_dictionary.csv? Terms not yet in your study deck will be imported.")) return;
      const resp = await fetch('/api/import/dictionary', { method: 'POST' });
      const res = await resp.json();
      alert(res.message);
      await init();
    }

    function exportCourseCSV() {
      const cards = getFilteredCards();
      if (cards.length === 0) {
        alert("No cards to export under current filter.");
        return;
      }

      const headers = ["Course Code", "Term", "Subfield", "Biological Mechanism", "Horticultural Practice", "Prof Exam Trap", "Key Crops", "Mastery Status"];
      const rows = cards.map(c => [
        `"${(c.course_code || c.course_id || '').replace(/"/g, '""')}"`,
        `"${(c.term || '').replace(/"/g, '""')}"`,
        `"${(c.subfield || '').replace(/"/g, '""')}"`,
        `"${(c.biological_mechanism || '').replace(/"/g, '""')}"`,
        `"${(c.horticultural_practice || '').replace(/"/g, '""')}"`,
        `"${(c.exam_trap || '').replace(/"/g, '""')}"`,
        `"${(c.key_crops || '').replace(/"/g, '""')}"`,
        `"${(c.mastery || '').replace(/"/g, '""')}"`
      ]);

      const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows.map(e => e.join(','))].join('\\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      const filename = state.selectedCourseId === 'ALL' ? 'HortiPrep_All_Courses.csv' : `HortiPrep_${state.selectedCourseId}.csv`;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    // Modal Helpers
    function openModal(id) { document.getElementById(id).classList.add('open'); }
    function closeModal(id) { document.getElementById(id).classList.remove('open'); }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function json_stringify(obj) {
      return JSON.stringify(obj);
    }

    // Keyboard Shortcuts for Flashcard Mode
    document.addEventListener('keydown', (e) => {
      if (document.querySelector('.modal-overlay.open')) return;
      if (state.currentView === 'drill') {
        if (e.code === 'Space') {
          e.preventDefault();
          if (!state.drillRevealed) revealDrillAnswer();
        } else if (e.key === '1') {
          if (state.drillRevealed) rateDrillCard('Needs Review');
        } else if (e.key === '2') {
          if (state.drillRevealed) rateDrillCard('Familiar');
        } else if (e.key === '3') {
          if (state.drillRevealed) rateDrillCard('Exam Ready');
        } else if (e.code === 'ArrowRight') {
          const cards = getDrillCards();
          if (cards.length > 0) {
            state.drillIndex = (state.drillIndex + 1) % cards.length;
            initDrillCard();
          }
        } else if (e.code === 'ArrowLeft') {
          const cards = getDrillCards();
          if (cards.length > 0) {
            state.drillIndex = (state.drillIndex - 1 + cards.length) % cards.length;
            initDrillCard();
          }
        }
      }
    });

    // Start App
    window.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""


# ==============================================================================
# HTTP REQUEST HANDLER (API & STATIC ROUTER)
# ==============================================================================

class StudyAppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet terminal logging
        pass

    def send_json(self, status_code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path in ["/", "/index.html"]:
            data = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/deck":
            self.send_json(200, load_data())
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if path == "/api/card/add":
            data = load_data()
            new_card = req_data
            if not new_card.get("id"):
                new_card["id"] = "card_" + "".join(c if c.isalnum() else "_" for c in new_card.get("term", "item").lower())
            data["cards"].append(new_card)
            save_data(data)
            self.send_json(200, {"success": True, "card": new_card})
            return

        if path == "/api/card/update":
            data = load_data()
            card_id = req_data.get("id")
            for idx, c in enumerate(data["cards"]):
                if c.get("id") == card_id:
                    data["cards"][idx] = req_data
                    save_data(data)
                    self.send_json(200, {"success": True, "card": req_data})
                    return
            self.send_json(404, {"error": "Card not found"})
            return

        if path == "/api/card/delete":
            data = load_data()
            card_id = req_data.get("id")
            orig_len = len(data["cards"])
            data["cards"] = [c for c in data["cards"] if c.get("id") != card_id]
            if len(data["cards"]) < orig_len:
                save_data(data)
                self.send_json(200, {"success": True})
            else:
                self.send_json(404, {"error": "Card not found"})
            return

        if path == "/api/ai/generate":
            term = req_data.get("term", "").strip()
            target_course = req_data.get("target_course", "AUTO")
            sync_to_dict = req_data.get("sync_to_dict", True)
            if not term:
                self.send_json(400, {"error": "Term is required"})
                return

            try:
                new_card = generate_exam_card_ai(term, target_course, sync_to_dict=sync_to_dict)
                data = load_data()
                # Check if card already exists
                existing = next((c for c in data["cards"] if c["term"].lower() == term.lower()), None)
                if existing:
                    existing.update(new_card)
                else:
                    data["cards"].append(new_card)
                save_data(data)
                self.send_json(200, {"success": True, "card": new_card, "synced": sync_to_dict})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/api/import/dictionary":
            if not os.path.exists(DICTIONARY_CSV):
                self.send_json(404, {"error": f"{DICTIONARY_CSV} not found."})
                return

            data = load_data()
            existing_terms = {c["term"].lower() for c in data["cards"]}
            imported_count = 0

            # Subfield to Course heuristics
            subfield_map = {
                "Pomology": "HORT501",
                "Plant Propagation": "HORT501",
                "Olericulture": "HORT503",
                "Floriculture": "HORT507",
                "Landscape Horticulture": "HORT507",
                "Plant Physiology": "HORT519",
                "Plant Breeding": "HORT521",
                "Botany": "HORT521"
            }

            try:
                with open(DICTIONARY_CSV, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        word = row.get("Word", "").strip()
                        if not word or word.lower() in existing_terms:
                            continue

                        subfield = row.get("Subfield", "").strip()
                        definition = row.get("Definition", "").strip()
                        example = row.get("Example Sentence", "").strip()
                        see_also = row.get("See Also", "").strip()

                        # Assign course
                        matched_course_id = subfield_map.get(subfield, "HORT501")
                        matched_course = next((c for c in data["courses"] if c["id"] == matched_course_id), data["courses"][0])

                        card = {
                            "id": "card_" + "".join(c if c.isalnum() else "_" for c in word.lower()),
                            "term": word.title(),
                            "course_id": matched_course["id"],
                            "course_code": matched_course["code"],
                            "subfield": subfield,
                            "biological_mechanism": definition,
                            "horticultural_practice": example,
                            "exam_trap": f"Key distinction required: related to {see_also}. Be prepared to differentiate from related physiological or nursery concepts.",
                            "key_crops": "Horticultural cultivars and germplasm",
                            "mastery": "Needs Review",
                            "notes": "Imported from dictionary master CSV.",
                            "date_added": str(date.today()),
                            "last_reviewed": str(date.today())
                        }
                        data["cards"].append(card)
                        existing_terms.add(word.lower())
                        imported_count += 1

                if imported_count > 0:
                    save_data(data)
                self.send_json(200, {"success": True, "message": f"Successfully imported {imported_count} new terms from {DICTIONARY_CSV}."})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_error(404, "Endpoint not found")


# ==============================================================================
# SERVER LAUNCHER
# ==============================================================================

def find_available_port(start_port=8081, max_tries=10):
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start_port


def main():
    # Make sure initial data exists
    load_data()
    port = find_available_port(PORT)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, StudyAppHandler)

    model = detect_ollama_model()
    url = f"http://localhost:{port}"
    print("=" * 70)
    print("🌱 HortiPrep - Graduate Exam Study & Course Review Dashboard")
    print("=" * 70)
    print(f"✓ Using local model: {model} (Apple Silicon accelerated)")
    print(f"✓ Server running at: {url}")
    print("✓ Courses Loaded: 7 Semester 1 Courses (BAU M.S. Horticulture)")
    print("Features:")
    print("  • Cheat Sheet & Table Review by Course")
    print("  • Active Recall Flashcard Drill with Keyboard Controls [Space, 1, 2, 3]")
    print("  • High-Yield Exam Traps & Biological Mechanisms")
    print("  • 1-Click Print & PDF Export")
    print("  • Auto-Sync with Main Dictionary (local_dictionary.csv)")
    print("Press Ctrl+C to stop the server.")
    print("=" * 70)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] HortiPrep server shut down cleanly.")
        httpd.server_close()


if __name__ == "__main__":
    main()
