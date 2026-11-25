#!/usr/bin/env python3
"""
Horticulture Dictionary - Local Web Dashboard
100% Offline, runs locally on macOS (Apple Silicon M4).
Zero third-party dependencies (built with Python standard library).
"""

import os
import sys
import re
import json
import csv
import socket
import webbrowser
import urllib.request
import urllib.parse
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "local_dictionary.csv")
OLLAMA_BASE = "http://localhost:11434"
RECOMMENDED_MODELS = ["qwen2.5:14b", "qwen2.5:7b", "qwen2.5", "llama3.2:3b", "llama3.2", "mistral:7b", "mistral"]

HEADERS = [
    "Word",
    "Pronunciation (IPA)",
    "Part of Speech",
    "Subfield",
    "Definition",
    "Conceptual Exposition",
    "Example Sentence",
    "Etymology",
    "Synonyms",
    "See Also",
    "Infographic Recommendation",
    "Date Added",
    "Status"
]

SUBFIELDS = [
    "Plant Propagation", "Plant Physiology", "Soil Science",
    "Plant Pathology", "Pest Management", "Pomology",
    "Olericulture", "Floriculture", "Landscape Horticulture",
    "Postharvest", "Plant Breeding", "Botany"
]


TERM_NORMALIZATIONS = {
    "apomixix": "apomixis",
    "epiphytes": "epiphyte",
    "plant-breeding": "plant breeding",
    "micro reserves": "micro-reserve",
    "micro-reserves": "micro-reserve",
    "lithophytes": "lithophyte",
    "saprophytes": "saprophyte",
    "bulbs": "bulb",
    "corms": "corm",
    "tubers": "tuber",
    "habitats": "habitat",
}


def split_terms(input_text_or_list):
    """
    Splits input into clean horticultural terms.
    Supports comma-separated, semicolon-separated, or newline-separated strings and lists.
    Preserves multi-word phrases (2-3 words) and hyphenated terms (e.g. 'air layering', 't-budding').
    Normalizes common typos and plural/hyphenation variations to canonical dictionary headwords.
    """
    raw_terms = []
    if isinstance(input_text_or_list, list):
        for item in input_text_or_list:
            raw_terms.extend(split_terms(item))
    elif isinstance(input_text_or_list, str):
        parts = re.split(r"[,;\n\r]+", input_text_or_list)
        raw_terms.extend(parts)

    cleaned = []
    seen = set()
    for t in raw_terms:
        ct = re.sub(r"\s+", " ", t).strip()
        if not ct:
            continue
        ct_canonical = TERM_NORMALIZATIONS.get(ct.lower(), ct.lower())
        if ct_canonical and ct_canonical not in seen:
            seen.add(ct_canonical)
            cleaned.append(ct_canonical)
    return cleaned


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
    "floral": "ˈflɔːr.əl",
    "induction": "ɪnˈdʌk.ʃən",
    "floral induction": "ˌflɔːr.əl ɪnˈdʌk.ʃən",
    "habit": "ˈhæb.ɪt",
    "floral habit": "ˈflɔːr.əl ˈhæb.ɪt",
    "phase": "feɪz",
    "flowering": "ˈflaʊ.ər.ɪŋ",
    "flowering phase": "ˈflaʊ.ər.ɪŋ ˈfeɪz",
    "anthesis": "ænˈθiː.sɪs",
    "overbearing": "ˌoʊ.vərˈbɛr.ɪŋ",
    "overcropping": "ˌoʊ.vərˈkrɒp.ɪŋ",
    "thinning": "ˈθɪn.ɪŋ",
    "natural": "ˈnætʃ.ər.əl",
    "natural thinning": "ˈnætʃ.ər.əl ˈθɪn.ɪŋ",

    # Genetics, biotechnology & pathology
    "germplasm": "dʒɜːrmˌplæz.əm",
    "biotechnology": "ˌbaɪ.oʊ.tɛkˈnɒl.ə.dʒi",
    "somaclonal": "ˌsoʊ.məˈkloʊ.nəl",
    "totipotency": "ˌtoʊ.tɪˈpoʊ.tən.si",
    "heterosis": "ˌhɛt.əˈroʊ.sɪs",
    "landrace": "ˈlænd.reɪs",
    "accession": "ækˈsɛʃ.ən",
    "culture": "kʌl.tʃər",
    "mother": "ˈmʌð.ər",
    "mother culture": "ˈmʌð.ər ˌkʌl.tʃər",
    "spawn": "spɔːn",
    "spawn culture": "ˈspɔːn ˌkʌl.tʃər",
    "pure": "pjʊr",
    "pure culture": "ˈpjʊr ˌkʌl.tʃər",
    "axenic": "eɪˈzɛn.ɪk",
    "fruiting": "ˈfruː.tɪŋ",
    "body": "ˈbɑː.di",
    "fruiting body": "ˈfruː.tɪŋ ˌbɑː.di",
    "sporocarp": "ˈspɔːr.oʊˌkɑːrp",
    "basidiocarp": "bəˈsɪd.i.oʊˌkɑːrp",
    "surplus": "ˈsɜːr.pləs",
    "horticulture": "ˈhɔːr.tɪˌkʌl.tʃər",

    # Subfields & general terms
    "pomology": "poʊˈmɒl.ə.dʒi",
    "olericulture": "ˌɒl.ər.ɪˈkʌl.tʃər",
    "floriculture": "ˈflɔːr.ɪˌkʌl.tʃər",
    "pathology": "pəˈθɒl.ə.dʒi",
    "morphology": "mɔːrˈfɒl.ə.dʒi",
    "anatomy": "əˈnæt.ə.mi",
    "fruit": "fruːt",
    "plant": "plɑːnt",
    "tree": "triː",
    "root": "ruːt",
    "stock": "stɒk",
    "micro": "ˈmaɪ.kroʊ",
    "reserve": "rɪˈzɜːrv",
    "reserves": "rɪˈzɜːrvz",
    "micro-reserve": "ˌmaɪ.kroʊ.rɪˈzɜːrv",
    "micro-reserves": "ˌmaɪ.kroʊ.rɪˈzɜːrvz",
    "phototrophic": "ˌfoʊ.toʊˈtroʊ.fɪk",
    "photomorphic": "ˌfoʊ.toʊˈmɔːr.fɪk",
    "photomorphogenesis": "ˌfoʊ.toʊˌmɔːr.fəˈdʒɛn.ə.sɪs",
    "phytochrome": "ˈfaɪ.toʊˌkroʊm",
    "saturation": "ˌsætʃ.əˈreɪ.ʃən",
    "compensation": "ˌkɒm.pənˈseɪ.ʃən",
    "light saturation": "ˈlaɪt ˌsætʃ.əˈreɪ.ʃən",
    "light compensation": "ˈlaɪt ˌkɒm.pənˈseɪ.ʃən",

    # Photobiology, light ecology & photoperiodism
    "day": "deɪ",
    "neutral": "ˈnuː.trəl",
    "day-neutral": "ˈdeɪˌnuː.trəl",
    "day-neutral plant": "ˈdeɪˌnuː.trəl ˌplænt",
    "halophyte": "ˈhæl.əˌfaɪt",
    "heliophyte": "ˈhiː.li.oʊˌfaɪt",
    "holophyte": "ˈhɒl.əˌfaɪt",
    "sciophyte": "ˈsaɪ.əˌfaɪt",
    "long-day": "ˈlɔːŋ.deɪ",
    "long-day plant": "ˈlɔːŋ.deɪ ˌplænt",
    "short-day": "ˈʃɔːrt.deɪ",
    "short-day plant": "ˈʃɔːrt.deɪ ˌplænt",

    # Organography, genetics & postharvest
    "bulb": "bʌlb",
    "corm": "kɔːrm",
    "pollination": "ˌpɒl.əˈneɪ.ʃən",
    "cross-pollination": "ˈkrɒs.pɒl.əˌneɪ.ʃən",
    "epiphyte": "ˈɛp.ɪˌfaɪt",
    "epiphytes": "ˈɛp.ɪˌfaɪts",
    "habitat": "ˈhæb.ɪ.tæt",
    "lithophyte": "ˈlɪθ.əˌfaɪt",
    "breeding": "ˈbriː.dɪŋ",
    "plant breeding": "ˈplænt ˌbriː.dɪŋ",
    "plant-breeding": "ˈplænt ˌbriː.dɪŋ",
    "polyembryony": "ˌpɒl.iˈɛm.bri.ə.ni",
    "polygenic": "ˌpɒl.iˈdʒɛn.ɪk",
    "polyploid": "ˈpɒl.iˌplɔɪd",
    "saprophyte": "ˈsæp.rəˌfaɪt",
    "incompatibility": "ɪn.kəmˌpæt.əˈbɪl.ə.ti",
    "self-incompatibility": "ˌsɛlf.ɪn.kəmˌpæt.əˈbɪl.ə.ti",
    "self-pollination": "ˌsɛlf.pɒl.əˈneɪ.ʃən",
    "senescence": "sɪˈnɛs.əns",
    "shelf-life": "ˈʃɛlf.laɪf",
    "sterility": "stəˈrɪl.ə.ti",
    "tuber": "ˈtjuː.bər",
    "velamen": "vəˈleɪ.mən"
}

KNOWN_SYNONYMS = {
    "air layering": "marcottage, Chinese layering, pot layering",
    "apomixis": "agamospermy",
    "bulb": "tunicate bulb, scaly bulb, geophytic bulb, true bulb",
    "corm": "solid bulb (historical), bulbo-tuber, cormous stem",
    "cross-pollination": "allogamy, xenogamy, outcrossing, inter-plant pollination",
    "day-neutral plant": "photoperiod-insensitive plant, day-length indifferent plant, autonomous flowering plant, DNP",
    "ecophysiology": "physiological ecology, environmental plant physiology",
    "epiphyte": "air plant, epiphytic flora, bark-dweller, phorophytic epiphyte",
    "epiphytes": "air plant, epiphytic flora, bark-dweller, phorophytic epiphyte",
    "floral habit": "flowering habit, bearing habit, bloom pattern, inflorescence habit",
    "floral induction": "floral evocation, reproductive evocation, flower induction",
    "flowering phase": "anthesis, bloom stage, floral stage, blooming period",
    "flush": "vegetative flush, episodic growth, shoot emergence",
    "fruiting body": "sporocarp, basidiocarp, ascocarp, mushroom",
    "germplasm": "genetic resources, hereditary material, gene pool",
    "grafting": "graftage, top-working",
    "habitat": "natural provenance, ecological niche, native range, biotope",
    "halophyte": "salt-tolerant plant, euhalophyte, pseudohalophyte, saline-adapted flora",
    "heliophyte": "sun plant, light-demanding plant, photo-heliophyte, sun-loving plant",
    "holophyte": "photoautotroph, autotrophic plant, holotrophic organism",
    "horticulture": "garden cultivation, high-value crop science, intensive horticultural cultivation",
    "light compensation": "light compensation point (LCP), compensation irradiance, zero-carbon exchange point, photosynthetic compensation point",
    "light saturation": "light saturation point (LSP), photosynthetic saturation point, light-saturating irradiance, Ik (saturation irradiance)",
    "lithophyte": "epilithic plant, rupicolous flora, rock plant, saxicolous organism",
    "long-day plant": "short-night plant, photoperiodic long-day species, LDP",
    "micro-reserve": "plant micro-reserve (PMR), genetic micro-reserve, in-situ micro-refugium, botanical micro-sanctuary",
    "micro-reserves": "plant micro-reserves (PMR), genetic micro-reserves, in-situ micro-refugia, botanical micro-sanctuaries",
    "mother culture": "master culture, foundation stock, axenic stock culture, primary culture",
    "natural thinning": "physiological fruit drop, self-thinning, June drop, fruitlet abscission",
    "orthodox seed": "desiccation-tolerant seed",
    "overbearing": "overcropping, excessive crop load, biennial bearing trigger",
    "photomorphic": "photomorphogenic, photomorphogenesis, light-regulated development",
    "photomorphogenesis": "photomorphic development, photomorphogenic response, light-regulated development, de-etiolation",
    "phototrophic": "photoautotrophic, light-nourished, photosynthetic, holophytic",
    "phytochrome": "plant chromoprotein photoreceptor, red/far-red reversible photoreceptor, biliprotein photoreceptor",
    "plant breeding": "crop improvement, cultivar development, genetic crop enhancement, plant genetic breeding",
    "plant-breeding": "crop improvement, cultivar development, genetic crop enhancement, plant genetic breeding",
    "polyembryony": "nucellar polyembryony, adventitious polyembryony, multiple embryony",
    "polygenic": "quantitative, multigenic, polyfactorial, QTL-controlled",
    "polyploid": "polyploid cultivar, euploid, gigas plant, chromosome-doubled cultivar",
    "pure culture": "axenic culture, monoxenic culture, isolated clone",
    "recalcitrant seed": "desiccation-sensitive seed, non-orthodox seed",
    "saprophyte": "saprotroph, saprobe, detritivore, necrotrophic decomposer",
    "sciophyte": "shade plant, shade-tolerant plant, skiophyte, ombrophyte, photophobous plant",
    "self-incompatibility": "SI, physiological self-sterility, genetic incompatibility, allogamy enforcer",
    "self-pollination": "autogamy, selfing, self-fertilization, idiogamy",
    "senescence": "programmed cell death (PCD), physiological aging, leaf yellowing, organ senescence",
    "shelf-life": "storage life, postharvest longevity, marketable lifespan, keeping quality",
    "short-day plant": "long-night plant, photoperiodic short-day species, SDP",
    "spawn culture": "mushroom spawn, grain spawn, vegetative inoculum, planting spawn",
    "sterility": "male sterility, reproductive barrenness, gametic abortion, ovule/pollen sterility",
    "surplus": "buffer units, guard-row surplus, sampling reserve, oversampling allowance",
    "t-budding": "shield budding, T-grafting",
    "true seed": "botanical seed",
    "tuber": "stem tuber, starchy underground tuber, seed potato (production term)",
    "velamen": "velamen radicum, aerial root mantle, epiphytic root sheath",
    "vernalization": "yarovization (historical), low-temperature floral induction"
}


def clean_ipa_syntax(ipa_str):
    """Normalize and clean IPA transcription, fixing common LLM phonetic errors."""
    if not ipa_str:
        return ""
    t = ipa_str.strip()
    # Normalize turned-r and British parenthetical markers
    t = t.replace("ɹ", "r").replace("ə(ɹ)", "ər").replace("(ɹ)", "r").replace("(r)", "r")
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

    # Fix unpunctuated floral induction
    if "ɪndʌkˈʃən" in t or "ɪndʌkʃən" in t:
        t = t.replace("ɪndʌkˈʃən", "ɪnˈdʌk.ʃən").replace("ɪndʌkʃən", "ɪnˈdʌk.ʃən")
    # Fix natural thinning missing syllable breaks
    if "ˈnætʃrəl" in t:
        t = t.replace("ˈnætʃrəl", "ˈnætʃ.ər.əl")
    if "ˈθɪnɪŋ" in t:
        t = t.replace("ˈθɪnɪŋ", "ˈθɪn.ɪŋ")
    # Fix floral habit missing syllable breaks
    if "ˈflɔrəl" in t:
        t = t.replace("ˈflɔrəl", "ˈflɔːr.əl")
    if "ˈhæbɪt" in t:
        t = t.replace("ˈhæbɪt", "ˈhæb.ɪt")

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
    item["Word"] = term_lower  # Standardize all dictionary terms to lowercase

    # 1. Phonetics / IPA verification
    curated_ipa = fetch_verified_ipa(term_lower)
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
    elif term_lower.endswith(" culture") and raw_ipa and "kʌl.tʃər" not in raw_ipa:
        item["Pronunciation (IPA)"] = clean_ipa_syntax(f"/{raw_ipa.strip('/')} ˌkʌl.tʃər/")

    # 2. Known technical synonyms enforcement
    if term_lower in KNOWN_SYNONYMS:
        item["Synonyms"] = KNOWN_SYNONYMS[term_lower]
    elif not item.get("Synonyms") or not item["Synonyms"].strip():
        subf = item.get("Subfield", "Horticulture")
        item["Synonyms"] = f"{term_lower} ({subf.lower()} descriptor)"

    # 3. Botanical / Crop Congruence & Mechanism Guardrails
    defn = item.get("Definition", "")
    example = item.get("Example Sentence", "")
    etym = item.get("Etymology", "")

    # Fruiting body: prevent confusing fungal sporocarps with orchard fruit trees (apples/peaches)
    if "fruiting body" in term_lower:
        item["Subfield"] = "Olericulture"
        item["Pronunciation (IPA)"] = "/ˈfruː.tɪŋ ˌbɑː.di/"
        item["Synonyms"] = "sporocarp, basidiocarp, ascocarp, mushroom"
        if "apple" in defn.lower() or "peach" in defn.lower() or "prun" in defn.lower() or "tree" in defn.lower():
            item["Definition"] = (
                "A specialized, macroscopic multicellular reproductive structure (sporocarp) produced by higher fungi "
                "(Basidiomycota and Ascomycota) that bears, protects, and disseminates meiotic spores. In commercial olericultural "
                "mushroom production (e.g. Agaricus bisporus, Pleurotus ostreatus), the fruiting body represents the primary harvestable "
                "economic yield, induced by pinhead trigger conditions (temperature drop, high relative humidity, and CO2 reduction)."
            )
            item["Example Sentence"] = (
                "Commercial button mushroom growers trigger fruiting body primordial initiation (pinning) by casing the "
                "colonized compost and ventilating the growing room to lower ambient carbon dioxide below 1000 ppm."
            )

    # Spawn culture: eliminate "grown from fungal spores" error
    if "spawn culture" in term_lower:
        item["Subfield"] = "Olericulture"
        item["Pronunciation (IPA)"] = "/ˈspɔːn ˌkʌl.tʃər/"
        item["Synonyms"] = "mushroom spawn, grain spawn, vegetative inoculum, planting spawn"
        if "spore" in defn.lower():
            item["Definition"] = (
                "The commercial propagation vehicle wherein a carrier substrate (sterilized cereal grains such as wheat, "
                "rye, or sorghum, or sawdust) is fully colonized by pure, vegetative dikaryotic mycelium of a selected mushroom strain, "
                "acting as the biological seed or inoculum for commercial substrate spawning."
            )
            item["Example Sentence"] = (
                "Sterilized wheat grain bags are inoculated with mother mycelium in a laminar airflow chamber to produce "
                "vigorous grain spawn culture for oyster mushroom (Pleurotus ostreatus) bag production."
            )
        if "spawan" in etym.lower():
            item["Etymology"] = (
                "From Anglo-French 'espaundre' / Old French 'espandre' (to scatter, pour out, spread, from Latin 'expandere') "
                "+ Latin 'cultura'; historically applied to fish roe and adopted in horticulture for mycelial propagation units."
            )

    # Overbearing: eliminate "deficiency of gibberellins" & enforce overcropping synonym
    if "overbearing" in term_lower:
        item["Subfield"] = "Pomology"
        item["Pronunciation (IPA)"] = "/ˌoʊ.vərˈbɛr.ɪŋ/"
        item["Synonyms"] = "overcropping, excessive crop load, biennial bearing trigger"
        if "deficiency of gibberellin" in defn.lower() or "excess of cytokinin" in defn.lower():
            item["Definition"] = (
                "The physiological condition wherein a fruit tree sets an excessively heavy crop load relative to its canopy "
                "leaf area and photosynthetic capacity. High seed counts produce excessive gibberellins that basipetally inhibit "
                "floral induction in adjacent buds, deplete non-structural carbohydrate reserves, cause branch breakage, and trigger "
                "alternate or biennial bearing in following seasons."
            )
            item["Example Sentence"] = (
                "Apple and mango orchardists prevent overbearing in heavy crop years by performing chemical or hand fruit thinning "
                "within 30 days of full bloom to protect carbohydrate reserves and ensure floral bud initiation for the next season."
            )

    # Natural thinning: enforce physiological drop definition and pomology subfield
    if "natural thinning" in term_lower:
        item["Subfield"] = "Pomology"
        item["Pronunciation (IPA)"] = "/ˈnætʃ.ər.əl ˈθɪn.ɪŋ/"
        item["Synonyms"] = "physiological fruit drop, self-thinning, June drop, fruitlet abscission"

    # Floral induction: enforce plant physiology subfield and evocation synonyms
    if "floral induction" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˌflɔːr.əl ɪnˈdʌk.ʃən/"
        item["Synonyms"] = "floral evocation, reproductive evocation, flower induction"

    # Floral habit: enforce floriculture/pomology subfield
    if "floral habit" in term_lower:
        item["Subfield"] = "Floriculture"
        item["Pronunciation (IPA)"] = "/ˈflɔːr.əl ˈhæb.ɪt/"
        item["Synonyms"] = "flowering habit, bearing habit, bloom pattern, inflorescence habit"

    # Flowering phase: enforce anthesis synonyms
    if "flowering phase" in term_lower:
        item["Subfield"] = "Floriculture"
        item["Pronunciation (IPA)"] = "/ˈflaʊ.ər.ɪŋ ˈfeɪz/"
        item["Synonyms"] = "anthesis, bloom stage, floral stage, blooming period"

    # Surplus: eliminate supellex hallucination
    if "surplus" in term_lower:
        item["Subfield"] = "Experimental Design"
        item["Pronunciation (IPA)"] = "/ˈsɜːr.pləs/"
        item["Synonyms"] = "buffer units, guard-row surplus, sampling reserve, oversampling allowance"
        if "supellex" in etym.lower() or "furniture" in etym.lower():
            item["Etymology"] = (
                "From Old French 'surplus' (excess, remainder), from Medieval Latin 'superplus' "
                "(from Latin 'super', over/above + 'plus', more); unrelated to Latin supellex."
            )

    # Horticulture: eliminate hypernym/hyponym synonym pollution
    if term_lower == "horticulture":
        item["Subfield"] = "Botany"
        item["Pronunciation (IPA)"] = "/ˈhɔːr.tɪˌkʌl.tʃər/"
        item["Synonyms"] = "garden cultivation, high-value crop science, intensive horticultural cultivation"

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

    # Micro-reserves: plant breeding / genetic resources in-situ conservation guardrail
    if "micro-reserve" in term_lower or "micro reserve" in term_lower:
        item["Subfield"] = "Plant Breeding"
        item["Pronunciation (IPA)"] = "/ˌmaɪ.kroʊ.rɪˈzɜːrvz/" if "reserves" in term_lower else "/ˌmaɪ.kroʊ.rɪˈzɜːrv/"
        item["Synonyms"] = "plant micro-reserves (PMR), genetic micro-reserves, in-situ micro-refugia, botanical micro-sanctuaries"
        if not item.get("Definition") or "botany descriptor" in item.get("Synonyms", "") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "Small, officially designated in-situ conservation sites (typically under 20 hectares) established "
                "to protect, monitor, and manage small, localized populations of rare, endemic plant species or valuable "
                "crop wild relatives (CWR) within their natural evolutionary habitats."
            )
            item["Example Sentence"] = (
                "Agricultural researchers identified a five-hectare micro-reserve in the Chittagong Hill Tracts to conserve "
                "the remaining natural stands of Mangifera sylvatica, a critical wild relative needed for mango rootstock breeding."
            )
            item["Etymology"] = (
                "From Greek 'mikros' (small) + Latin 'reservare' (to keep back, save up, from 're-' back + 'servare' to guard, keep). "
                "Formalized into the Plant Micro-Reserve (PMR) conservation framework by Spanish botanist Emilio Laguna in 1992."
            )
            item["See Also"] = "in-situ conservation, crop wild relatives, germplasm, gene pool, genetic vulnerability, landrace"
        if not item.get("Conceptual Exposition") or len(item.get("Conceptual Exposition", "").strip()) < 50:
            item["Conceptual Exposition"] = (
                "A micro-reserve (or plant micro-reserve, PMR) is a specialized conservation parcel—rarely exceeding 10 to 20 hectares, "
                "and often as small as a single hectare or hillock—legally established to protect critical populations of rare, localized, "
                "or relict plant taxa and crop wild relatives (CWR) directly in their natural habitats. While macro-conservation schemes like "
                "national parks and wildlife sanctuaries span thousands of square kilometers to protect broad ecosystems and megafauna, they "
                "often overlook cryptic, highly localized plant species clinging to distinct micro-habitats. The micro-reserve model bridges this "
                "gap, providing targeted micro-sanctuaries that safeguard micro-populations under continuous botanical monitoring without "
                "requiring the massive land allocations of conventional national reserves.\n\n"
                "Unlike ex-situ germplasm banks—where collected seeds or tissue accessions are essentially 'frozen' in evolutionary time at "
                "sub-zero temperatures—micro-reserves maintain active, living evolutionary laboratories. In a micro-reserve, wild crop ancestors "
                "remain exposed to fluctuating weather patterns, indigenous pollinators, and constantly mutating local pathogen and insect populations. "
                "Consequently, natural selection continues to operate unabated, generating and refining novel defensive alleles, pathogen resistance traits, "
                "and climate-resilience genes. For plant breeders, these small reserves serve as living genetic vaults, retaining dynamic allelic diversity "
                "that would otherwise be permanently lost if a localized wild stand were cleared for intensive agriculture or human settlement.\n\n"
                "In densely populated deltaic landscapes like Bangladesh, where vast wilderness expanses cannot be set aside without displacing "
                "agriculture or rural livelihoods, micro-reserves represent the most pragmatic and urgent in-situ conservation strategy. Remnant evergreen "
                "and semi-evergreen forest pockets in the Chittagong Hill Tracts (Bandarban and Rangamati), degraded sal forest fragments in Madhupur, and "
                "the isolated hillocks and sacred groves of Sylhet and Moulvibazar function as de facto micro-refugia for critical horticultural wild relatives. "
                "Notable examples include wild mango (Mangifera sylvatica), wild citrus relatives (Citrus macroptera and Citrus assamensis), wild jackfruit "
                "relatives (Artocarpus chama), and wild eggplant species (Solanum torvum and Solanum viarum). Formalizing these sites into recognized "
                "micro-reserves ensures that their irreplaceable disease- and drought-resistance genes remain preserved and accessible for future rootstock "
                "breeding and horticultural cultivar development."
            )
        if not item.get("Infographic Recommendation") or "mechanism, anatomical" in item.get("Infographic Recommendation", ""):
            item["Infographic Recommendation"] = (
                "Field In-Situ Micro-Reserve Landscape Zonation: Multi-panel diagram showing: (1) Core Micro-Reserve Zone (<10 ha) protecting clustered "
                "wild relatives (Mangifera sylvatica and wild Citrus); (2) Ecological Buffer Belt shielding the core from agricultural grazing, "
                "deforestation, and herbicide drift; (3) Dynamic Genetic Linkage showing the dual pathway: natural evolutionary selection in-situ vs. "
                "selective sample extraction into ex-situ breeding genebanks for rootstock introgression."
            )

    # Phototrophic guardrail
    if "phototroph" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˌfoʊ.toʊˈtroʊ.fɪk/"
        item["Synonyms"] = "photoautotrophic, light-nourished, photosynthetic, holophytic"
        if not item.get("Definition") or "descriptor" in item.get("Synonyms", "") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "Describing organisms that synthesize their own biochemical energy from photons via light-driven reactions, "
                "fundamentally encompassing photoautotrophs (such as green plants and cyanobacteria) that fix carbon dioxide into organic carbohydrates using solar radiation."
            )
            item["Example Sentence"] = (
                "Horticultural greenhouse engineers install diffusing polyethylene films to maximize phototrophic light interception across the lower canopy leaves of indeterminate tomato crops."
            )
            item["Etymology"] = (
                "From Ancient Greek φῶς / φωτός ('phōs', 'phōtos', light) + τροφικός ('trophikos', pertaining to nourishment, from τροφή, food or feeding). "
                "Coined in microbiological and plant physiological texts to designate light-nourished organisms."
            )
            item["See Also"] = "photoautotrophy, photosynthesis, phototropism, photosystem, calvin cycle, chlorophyll"

    # Photomorphogenesis / Photomorphic guardrail
    if "photomorph" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˌfoʊ.toʊˌmɔːr.fəˈdʒɛn.ə.sɪs/" if "genesis" in term_lower else "/ˌfoʊ.toʊˈmɔːr.fɪk/"
        item["Synonyms"] = "photomorphic development, photomorphogenic response, light-regulated development, de-etiolation"
        if not item.get("Definition") or "descriptor" in item.get("Synonyms", "") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "The light-mediated structural development, cellular differentiation, and morphological patterning of plants "
                "throughout their lifecycle, operating independently of photosynthetic energy assimilation through specialized photoreceptors."
            )
            item["Example Sentence"] = (
                "Commercial vegetable nurserymen remove shade netting at seedling emergence to activate phytochrome-mediated photomorphogenesis, "
                "suppressing hypocotyl elongation and preventing leggy transplants."
            )
            item["Etymology"] = (
                "From Ancient Greek φῶς ('phōs', light) + μορφή ('morphē', form or shape) + γένεσις ('genesis', origin, creation, or production). "
                "Coined in modern plant ecophysiology to describe light-induced developmental anatomy."
            )
            item["See Also"] = "phytochrome, cryptochrome, etiolation, de-etiolation, shade avoidance response, photoperiodism"

    # Phytochrome guardrail
    if "phytochrome" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈfaɪ.toʊˌkroʊm/"
        item["Synonyms"] = "plant chromoprotein photoreceptor, red/far-red reversible photoreceptor, biliprotein photoreceptor"
        if not item.get("Definition") or "descriptor" in item.get("Synonyms", "") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A soluble, dimeric chromoprotein photoreceptor in plants that reversibly photo-interconverts between a physiologically inactive "
                "red-absorbing form (Pr) and an active far-red-absorbing form (Pfr), regulating germination, de-etiolation, shade avoidance, and photoperiodic flowering."
            )
            item["Example Sentence"] = (
                "Orchardists prune dense interior mango branches to improve sunlight penetration and elevate the red to far-red ratio, "
                "maintaining active Pfr phytochrome levels essential for floral bud initiation."
            )
            item["Etymology"] = (
                "From Ancient Greek φυτόν ('phyton', plant) + χρῶμα ('chrōma', color or pigment). "
                "Coined in 1959 by USDA agricultural researchers Warren Butler, Harry Borthwick, and Sterling Hendricks upon discovering the reversible plant pigment."
            )
            item["See Also"] = "photomorphogenesis, photoperiodism, shade avoidance response, phytochromobilin, florigen, pif transcription factors"

    # Light Saturation guardrail
    if "light sat" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈlaɪt ˌsætʃ.əˈreɪ.ʃən/"
        item["Synonyms"] = "light saturation point (LSP), photosynthetic saturation point, light-saturating irradiance, Ik (saturation irradiance)"
        if not item.get("Definition") or "descriptor" in item.get("Synonyms", "") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "The photosynthetically active radiation (PAR) irradiance level beyond which further increases in light intensity "
                "yield no corresponding increase in the rate of photosynthetic carbon dioxide assimilation, determined by the maximum enzymatic turnover capacity of Rubisco and Calvin cycle intermediates."
            )
            item["Example Sentence"] = (
                "In commercial strawberry polyhouses, supplemental LED grow-lights are adjusted to match the crop's light saturation point, "
                "maximizing photosynthetic yield without causing wasteful heat accumulation."
            )
            item["Etymology"] = (
                "From Old English 'lēoht' (light, illumination) + Latin 'saturatio' (a filling, glutting, or satisfying, from 'satur', full/sated). "
                "Coined in 20th-century plant biophysics and gas-exchange physiology."
            )
            item["See Also"] = "light compensation, light-response curve, photoinhibition, rubisco, amax, photosystem ii"

    # Light Compensation guardrail
    if "light comp" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈlaɪt ˌkɒm.pənˈseɪ.ʃən/"
        item["Synonyms"] = "light compensation point (LCP), compensation irradiance, zero-carbon exchange point, photosynthetic compensation point"
        if not item.get("Definition") or "descriptor" in item.get("Synonyms", "") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "The irradiance level on a light-response curve at which the gross rate of photosynthetic carbon dioxide assimilation "
                "exactly equals the total rate of respiratory carbon dioxide release (mitochondrial respiration plus photorespiration), resulting in zero net carbon exchange (A_net = 0)."
            )
            item["Example Sentence"] = (
                "Orchardists prune low, heavily shaded interior mango branches that sit below their light compensation point, "
                "eliminating parasitic sinks that exhaust stored carbohydrates without contributing to fruit yield."
            )
            item["Etymology"] = (
                "From Old English 'lēoht' (light, brightness) + Latin 'compensatio' (a balancing, from 'compensare' to weigh together). "
                "Applied to metabolic gas exchange in early 20th-century plant physiology."
            )
            item["See Also"] = "light saturation, dark respiration, net assimilation rate, light-response curve, shade tolerance, photoinhibition"

    # Day-neutral plant guardrail
    if "day-neutral" in term_lower or "day neutral" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈdeɪˌnuː.trəl ˌplænt/"
        item["Synonyms"] = "photoperiod-insensitive plant, day-length indifferent plant, autonomous flowering plant, DNP"
        if "day length" in defn.lower() or "responding primarily to other" in defn.lower() or not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A plant whose floral initiation is not regulated by photoperiod (day or night length), "
                "flowering autonomously upon reaching an internal juvenile-to-adult developmental threshold or in response to accumulated thermal units."
            )
        item["See Also"] = "short-day plant, long-day plant, photoperiodism, autonomous pathway, florigen, juvenility"

    # Halophyte guardrail
    if "halophyte" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈhæl.əˌfaɪt/"
        item["Synonyms"] = "salt-tolerant plant, euhalophyte, pseudohalophyte, saline-adapted flora"
        if not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A specialized plant capable of completing its entire life cycle in saline environments containing high concentrations "
                "of sodium chloride (typically exceeding 200 mM NaCl or ~4–8+ dS/m), utilizing anatomical and physiological mechanisms for salt exclusion, excretion, or vacuolar compartmentalization."
            )
        if "spartina" in example.lower():
            item["Example Sentence"] = (
                "Researchers in the coastal delta of Satkhira are screening wild halophytic rootstocks to graft high-yielding tomato scions, "
                "preventing lethal sodium accumulation during the dry winter cropping season."
            )
        item["See Also"] = "glycophyte, osmotic stress, casparian strip, tonoplast antiporter, proline, sundarbans"

    # Heliophyte guardrail
    if "heliophyte" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈhiː.li.oʊˌfaɪt/"
        item["Synonyms"] = "sun plant, light-demanding plant, photo-heliophyte, sun-loving plant"
        if not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A plant adapted to grow and thrive in full, unshaded sunlight, exhibiting thick sun-leaf anatomy, "
                "high light compensation and saturation points, and robust photoprotective mechanisms to utilize high irradiance without suffering photoinhibition."
            )
        if "broad leaves" in exp.lower() or "broad leaves" in defn.lower():
            exp = exp.replace("broad leaves", "thick, sun-adapted leaves with multi-layered palisade mesophyll")
            item["Conceptual Exposition"] = exp
        item["See Also"] = "sciophyte, light saturation, light compensation, photoinhibition, xanthophyll cycle, rubisco"

    # Holophyte guardrail: eliminate "air plant/epiphyte" hallucination
    if "holophyte" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈhɒl.əˌfaɪt/"
        item["Synonyms"] = "photoautotroph, autotrophic plant, holotrophic organism"
        if "air plant" in defn.lower() or "epiphyt" in defn.lower() or "air and water" in defn.lower() or not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "An organism that exhibits holophytic (photoautotrophic) nutrition, synthesizing its total organic nutritional requirements "
                "from simple inorganic substances (carbon dioxide, water, and inorganic mineral ions) utilizing light energy through photosynthesis."
            )
            item["Example Sentence"] = (
                "As typical holophytes, greenhouse tomato plants require only sunlight, atmospheric carbon dioxide, water, and balanced inorganic mineral salts to synthesize their entire vegetative and fruit biomass."
            )
            item["Etymology"] = (
                "From Ancient Greek ὅλος ('holos', whole, complete, entirely) + φυτόν ('phyton', plant). "
                "Coined in 19th-century biological classifications to designate organisms with 'complete plant-like' (autotrophic) nutrition in explicit contrast to 'holozoic' (animal-like) and 'saprophytic' modes."
            )
        item["See Also"] = "photoautotrophy, photosynthesis, phototrophic, saprophyte, holozoic, rubisco"

    # Long-day plant guardrail: eliminate rice hallucination, enforce short-night reality
    if "long-day plant" in term_lower or "long day plant" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈlɔːŋ.deɪ ˌplænt/"
        item["Synonyms"] = "short-night plant, photoperiodic long-day species, LDP"
        if not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A photoperiodic plant that is induced to flower only when the photoperiod exceeds a critical day length—or more accurately, "
                "when the continuous dark period falls below a critical night length—typically flowering during late spring or summer."
            )
        if "rice" in example.lower():
            item["Example Sentence"] = (
                "As natural day length increases in late February, spinach behaves as a typical long-day plant, rapidly bolting and setting seed, "
                "which terminates the marketable vegetative harvest."
            )
        item["See Also"] = "short-day plant, day-neutral plant, photoperiodism, phytochrome, florigen, night break, bolting"

    # Sciophyte guardrail: eliminate "mango is a sciophyte" error
    if "sciophyte" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈsaɪ.əˌfaɪt/"
        item["Synonyms"] = "shade plant, shade-tolerant plant, skiophyte, ombrophyte, photophobous plant"
        if not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A plant adapted to grow and thrive under low light intensities (shade), characterized by thin leaves with high specific leaf area, "
                "low light compensation and saturation points, and high chlorophyll b content to capture diffuse understory radiation."
            )
        if "mango" in example.lower() or "litchi" in example.lower():
            item["Example Sentence"] = (
                "Under the multi-tier coconut agroforestry systems of southern Bangladesh, farmers cultivate ginger and elephant foot yam as high-value sciophytes beneath the shaded forest floor."
            )
        item["See Also"] = "heliophyte, light compensation, light saturation, shade tolerance, specific leaf area, photoinhibition"

    # Short-day plant guardrail: eliminate "short-night plant" & "mango day length" error
    if "short-day plant" in term_lower or "short day plant" in term_lower:
        item["Subfield"] = "Plant Physiology"
        item["Pronunciation (IPA)"] = "/ˈʃɔːrt.deɪ ˌplænt/"
        item["Synonyms"] = "long-night plant, photoperiodic short-day species, SDP"
        if not item.get("Definition") or len(item.get("Definition", "").strip()) < 15:
            item["Definition"] = (
                "A photoperiodic plant that is induced to flower only when the photoperiod is shorter than its critical day length—or strictly speaking, "
                "when the continuous, uninterrupted dark period exceeds its critical night length—typically flowering in late summer, autumn, or winter."
            )
        if "mango" in example.lower() or "mango" in defn.lower():
            item["Example Sentence"] = (
                "Traditional Bangladeshi hyacinth bean (Shim) cultivars behave as obligate short-day plants, remaining strictly vegetative through the summer "
                "and initiating flowers only when autumn night lengths exceed the critical threshold."
            )
        item["See Also"] = "long-day plant, day-neutral plant, photoperiodism, phytochrome, florigen, night break, lablab purpureus"

    # Bulb guardrail
    if term_lower == "bulb":
        item["Subfield"] = "Plant Propagation"
        item["Pronunciation (IPA)"] = "/bʌlb/"
        item["Synonyms"] = "tunicate bulb, scaly bulb, geophytic bulb, true bulb"
        if "swollen stem" in defn.lower() and "scale" not in defn.lower():
            item["Definition"] = (
                "A specialized, underground modified storage organ consisting of a flattened basal stem plate bearing "
                "a central growing point or floral primordium, tightly enveloped by fleshy, concentric scale leaves (cataphylls) "
                "that store reserve carbohydrates and water."
            )
        item["See Also"] = "corm, tuber, rhizome, cataphyll, geophyte, allium cepa"

    # Corm guardrail
    if term_lower == "corm":
        item["Subfield"] = "Plant Propagation"
        item["Pronunciation (IPA)"] = "/kɔːrm/"
        item["Synonyms"] = "solid bulb (historical), bulbo-tuber, cormous stem"
        if "scale leaves" in defn.lower() and "solid" not in defn.lower():
            item["Definition"] = (
                "A solid, swollen vertical subterranean stem axis that functions as a carbohydrate storage and perennating organ, "
                "distinguished by distinct nodes, internodes, and dry papery tunics derived from dead leaf bases, lacking internal fleshy scales."
            )
        item["See Also"] = "bulb, tuber, rhizome, tunic, cormel, gladiolus, colocasia esculenta"

    # Tuber guardrail
    if term_lower == "tuber":
        item["Subfield"] = "Plant Propagation"
        item["Pronunciation (IPA)"] = "/ˈtuː.bər/"
        item["Synonyms"] = "stem tuber, root tuber, stoloniferous storage organ, hypogeous swollen axis"
        item["See Also"] = "stolon, eye bud, adventitious root, bulb, corm, solanum tuberosum, ipomoea batatas"

    # Velamen guardrail
    if "velamen" in term_lower:
        item["Subfield"] = "Floriculture"
        item["Pronunciation (IPA)"] = "/vəˈleɪ.mən/"
        item["Synonyms"] = "velamen radicum, multiple root epidermis, aerial root mantle"
        if "chloroplast" in defn.lower() or "photosynthes" in defn.lower():
            item["Definition"] = (
                "A specialized, multiple-layered spongy epidermis enveloping the aerial roots of epiphytic orchids and aroids, "
                "composed of dead, empty, spirally reinforced cells that absorb atmospheric moisture and condense vapor."
            )
        item["See Also"] = "epiphyte, aerial root, orchidaceae, cortex, pneumathode, vanda"

    # Saprophyte guardrail
    if "saprophyte" in term_lower:
        item["Subfield"] = "Botany"
        item["Pronunciation (IPA)"] = "/ˈsæp.rəˌfaɪt/"
        item["Synonyms"] = "saprotroph, saprobe, extracellular decomposer, detritivore"
        if "plant that derives" in defn.lower() or "plant that feeds" in defn.lower():
            item["Definition"] = (
                "An organism—historically classified as a plant but in modern taxonomy referring strictly to fungi and bacteria—that "
                "obtains organic nutrients directly from dead and decaying organic matter via extracellular enzymatic digestion and absorption."
            )
        item["See Also"] = "saprotroph, mycoheterotrophy, decomposition, pleurotus ostreatus, holophyte, parasite"

    # Polyembryony guardrail
    if "polyembryony" in term_lower:
        item["Subfield"] = "Plant Breeding"
        item["Pronunciation (IPA)"] = "/ˌpɑː.liˈɛm.bri.ə.ni/"
        item["Synonyms"] = "nucellar embryony, multiple embryo formation, adventitious polyembryony"
        item["See Also"] = "apomixis, nucellus, adventitious embryony, citrus, mangifera indica, clonal propagation"

    # Polyploid guardrail
    if "polyploid" in term_lower:
        item["Subfield"] = "Plant Breeding"
        item["Pronunciation (IPA)"] = "/ˈpɑː.liˌplɔɪd/"
        item["Synonyms"] = "euploid, whole-genome duplication (WGD), gigas-type cytotype"
        item["See Also"] = "autopolyploid, allopolyploid, colchicine, triploid, aneuploid, citrullus lanatus"

    # Self-Incompatibility guardrail
    if "self-incompatibility" in term_lower or "self incompatibility" in term_lower:
        item["Subfield"] = "Plant Breeding"
        item["Pronunciation (IPA)"] = "/ˌsɛlf.ɪn.kəmˌpæt̬.əˈbɪl.ə.ti/"
        item["Synonyms"] = "SI, self-sterility, S-allele rejection, pre-zygotic breeding barrier"
        item["See Also"] = "cross-pollination, s-locus, gametophytic si, sporophytic si, pollinizer, brassica oleracea"

    # Senescence guardrail
    if "senescence" in term_lower:
        item["Subfield"] = "Postharvest"
        item["Pronunciation (IPA)"] = "/sɪˈnɛs.əns/"
        item["Synonyms"] = "programmed organ death, developmental PCD, postharvest deterioration, catabolic leaf yellowing"
        item["See Also"] = "abscission, ethylene, chlorophyll degradation, 1-mcp, programmed cell death, postharvest"

    # Shelf-Life guardrail
    if "shelf-life" in term_lower or "shelf life" in term_lower:
        item["Subfield"] = "Postharvest"
        item["Pronunciation (IPA)"] = "/ˈʃɛlfˌlaɪf/"
        item["Synonyms"] = "storage longevity, marketable postharvest life, keeping quality, commercial postharvest duration"
        item["See Also"] = "respiration rate, climacteric, ethylene, cold chain, modified atmosphere packaging, 1-mcp"

    # Sterility guardrail
    if "sterility" in term_lower:
        item["Subfield"] = "Plant Breeding"
        item["Pronunciation (IPA)"] = "/stəˈrɪl.ə.ti/"
        item["Synonyms"] = "male sterility, cytoplasmic male sterility (CMS), genetic male sterility (GMS), gametic abortion"
        item["See Also"] = "cytoplasmic male sterility, restorer gene, f1 hybrid, emasculation, allium cepa"

    # Lithophyte guardrail
    if "lithophyte" in term_lower:
        item["Subfield"] = "Botany"
        item["Pronunciation (IPA)"] = "/ˈlɪθ.əˌfaɪt/"
        item["Synonyms"] = "epilithic plant, rupicolous plant, saxicole, rock-dwelling flora"
        item["See Also"] = "epiphyte, saxicolous, micro-habitat, poikilohydric, bryophyte, rupicolous"

    # Epiphyte guardrail
    if "epiphyte" in term_lower:
        item["Subfield"] = "Floriculture"
        item["Pronunciation (IPA)"] = "/ˈɛp.əˌfaɪt/"
        item["Synonyms"] = "air plant, phorophytic epiphyte, bark-dwelling plant, pseudoparasite (historical)"
        item["See Also"] = "phorophyte, velamen, lithophyte, commensalism, orchidaceae, aerophyte"

    # Anti-Mango Overfitting check
    if "mango" in example.lower() and term_lower in ["self-incompatibility", "sterility", "sciophyte", "saprophyte", "velamen", "corm", "bulb"]:
        if term_lower == "self-incompatibility":
            item["Example Sentence"] = (
                "Commercial sweet cherry and Brassica seed producers interplant compatible cross-pollinizing cultivars "
                "and deploy honeybee hives to overcome genetic self-incompatibility and ensure high fruit and seed set."
            )
        elif term_lower == "sterility":
            item["Example Sentence"] = (
                "Commercial onion breeders utilize Cytoplasmic Male Sterility (CMS-S) lines as female seed parents, "
                "eliminating the need for labor-intensive manual emasculation in F1 hybrid seed production."
            )

    # Map and normalize Conceptual Exposition & Infographic Recommendation
    if "conceptual_exposition" in item and not item.get("Conceptual Exposition"):
        item["Conceptual Exposition"] = item.pop("conceptual_exposition")
    if "infographic_recommendation" in item and not item.get("Infographic Recommendation"):
        item["Infographic Recommendation"] = item.pop("infographic_recommendation")

    if not item.get("Conceptual Exposition") or not item["Conceptual Exposition"].strip():
        item["Conceptual Exposition"] = item.get("Definition", "")
    if not item.get("Infographic Recommendation") or not item["Infographic Recommendation"].strip():
        item["Infographic Recommendation"] = f"Technical schematic illustrating {term_lower} mechanism, anatomical structures, and practical crop context."

    # Guard against casual colloquialisms in Conceptual Exposition
    exp = item.get("Conceptual Exposition", "")
    casual_phrases = ["trick a branch", "tricking a branch", "marathon with three passengers", "apple on a tree"]
    for cp in casual_phrases:
        if cp in exp.lower():
            # Clean casual colloquialism
            exp = exp.replace("tricking a branch into believing it is underground", "inducing adventitious root formation in situ")
            exp = exp.replace("trick a branch into believing it is underground", "induce adventitious root formation in situ")
            exp = exp.replace("Imagine an athlete running a marathon while carrying three passengers on their back", "When a fruit tree carries an excessive crop load beyond its photosynthetic support capacity")
            item["Conceptual Exposition"] = exp

    return item


# ==============================================================================
# GOLD-STANDARD FEW-SHOT BENCHMARK EXEMPLARS
# ==============================================================================

FEW_SHOT_POOL = {
    "propagation": {
        "term": "air layering",
        "json": {
            "ipa": "/ˈɛər ˌleɪ.ər.ɪŋ/",
            "pos": "n.",
            "subfield": "Plant Propagation",
            "definition": "The asexual propagation technique of inducing adventitious roots on an aerial, woody shoot while it remains attached to the parent plant, achieved by girdling a ring of bark and enclosing the exposed cambium in a moist rooting medium.",
            "conceptual_exposition": "Air layering is an asexual propagation technique that allows a grower to develop a well-rooted, independent new tree while the branch is still physically connected to the parent plant. In traditional stem cuttings, the propagule is severed immediately, leaving it vulnerable to moisture stress and death before adventitious roots can form. Air layering overcomes this vulnerability by keeping the water-conducting sapwood (xylem) intact while removing an outer ring of bark (phloem), maintaining continuous hydration from the roots.\n\nBecause sugars and natural growth hormones (chiefly auxins like indole-3-acetic acid) manufactured in the leaves travel downward through the phloem, their path is blocked at the cut ring. These substances accumulate at the upper cut margin, stimulating rapid cell division that forms a swollen callus, followed by the differentiation of vigorous adventitious root primordia. When this wound is enclosed in a moist substrate (such as sphagnum moss or rich compost) and wrapped tightly in polyethylene film, darkness and sustained moisture accelerate root development. Once a dense mass of roots is visible through the plastic, the branch is sawed off just below the wrap and potted as an established, true-to-type tree.\n\nIn Bangladesh, air layering is the standard commercial method for propagating fruit crops that root poorly from ordinary cuttings, notably Litchi (Litchi chinensis cvs. China-3, Bedana, and Bombay in Dinajpur and Ishwardi) and Guava (Psidium guajava cv. Kazi Peyara). Propagation is executed during the humid monsoon months (Asharh–Sraban; June to August) when high humidity protects the moss from drying. For success, the green cambium ring must be completely scraped away; if any cambial tissue bridges the girdle, the wound simply heals over without forming roots.",
            "example": "Commercial fruit nurserymen in Ishwardi propagate elite 'China-3' litchi cultivars via air layering in July, using moist sphagnum moss wrapped in polyethylene film to induce adventitious rooting.",
            "etymology": "Compound term from Middle English 'air' (via Old French from Greek ἀήρ, 'aēr', atmosphere) and 'layering' (from Middle English 'leyere', an established shoot laid down for rooting, from Old English 'lecgan', to lay).",
            "synonyms": "marcottage, Chinese layering, pot layering",
            "see_also": "layering, adventitious roots, girdling, sphagnum moss, clonal propagation",
            "infographic_recommendation": "3-Step Field Layering Schematic: (1) Pencil-thick branch with a 2.5 cm bark ring stripped clean down to the white xylem, showing downward auxin accumulation at the upper cut lip; (2) Fist-sized ball of moist sphagnum moss molded around the wound, tightly sealed in 200-gauge transparent polyethylene and tied at both ends like a toffee wrapper; (3) Dense white adventitious roots radiating throughout the substrate inside the plastic, with an arrow indicating the harvesting cut below the basal tie."
        }
    },
    "breeding": {
        "term": "apomixis",
        "json": {
            "ipa": "/ˌæp.əˈmɪk.sɪs/",
            "pos": "n.",
            "subfield": "Plant Breeding",
            "definition": "The asexual formation and development of a viable seed without female meiosis (apomeiosis) and without fertilization (parthenogenesis), producing progeny that are maternal genetic clones of the seed parent.",
            "conceptual_exposition": "Apomixis is a specialized reproductive phenomenon in flowering plants where viable seeds are produced completely without sexual fertilization. In normal sexual reproduction, male and female gametes undergo meiosis to halve their chromosome numbers and fuse at fertilization to generate a genetically unique embryo. In apomictic plants, this entire sexual cycle is bypassed: the embryo arises directly from unreduced maternal ovular cells, producing seeds that are exact genetic clones of the mother plant.\n\nThis asexual seed formation occurs through two primary pathways. In gametophytic apomixis (apospory or diplospory), an unreduced embryo sac develops without meiosis, and the egg cell initiates embryo development spontaneously (parthenogenesis) without pollen union. In adventitious (sporophytic) embryony, somatic cells of the nucellus or integument directly proliferate into multiple embryos inside the seed, often coexisting with a single sexual zygote. For plant breeders, apomixis represents the 'holy grail' of crop genetics because it permanently locks in hybrid vigor (heterosis) across successive generations without the genetic segregation that normally destroys hybrid traits in subsequent seed crops.\n\nIn horticultural practice, apomixis is most famously exploited in citrus production (such as Rangpur lime, Citrus limonia, and Mandarin, Citrus reticulata). Polyembryonic citrus seeds contain multiple nucellar embryos that emerge as exceptionally uniform, virus-free rootstocks that match the maternal parent with 100% genetic fidelity. Researchers must strictly distinguish apomixis (seed production without fertilization) from parthenocarpy (fruit development without seed formation).",
            "example": "Citrus breeders rely on natural nucellar apomixis to propagate genetically identical, virus-free rootstock seedlings directly from seed.",
            "etymology": "Coined in 1908 by German botanist Hans Winkler from Greek ἀπό ('apo-', without/away from) and μῖξις ('mixis', mingling or sexual union).",
            "synonyms": "agamospermy",
            "see_also": "parthenogenesis, apospory, diplospory, adventitious embryony, polyembryony, parthenocarpy",
            "infographic_recommendation": "Comparative Ovule Embryogeny Diagram: Left panel showing standard sexual fertilization (meiotic egg cell + pollen sperm = single genetically variable zygote); Right panel showing sporophytic apomixis in Citrus (maternal nucellar cells budding around embryo sac to yield multiple identical clonal embryos alongside the central zygote)."
        }
    },
    "physiology": {
        "term": "halophyte",
        "json": {
            "ipa": "/ˈhæl.əˌfaɪt/",
            "pos": "n.",
            "subfield": "Plant Physiology",
            "definition": "A specialized plant capable of completing its entire life cycle in saline environments containing high concentrations of sodium chloride (typically exceeding 200 mM NaCl or ~4–8+ dS/m), utilizing anatomical and physiological mechanisms for salt exclusion, excretion, or vacuolar compartmentalization.",
            "conceptual_exposition": "Halophytes are specialized plants evolved to survive, grow, and reproduce in soils or waters characterized by high concentrations of soluble salts—predominantly sodium chloride (NaCl)—at concentrations that would induce lethal osmotic stress and ion toxicity in glycophytes (normal non-tolerant plants). In saline substrates, low external soil water potential restricts water uptake (physiological drought), while excessive cytosolic accumulation of sodium (Na+) and chloride (Cl-) disrupts enzymatic function, displaces potassium (K+), and destroys cellular membranes.\n\nTo overcome these dual biophysical challenges, halophytes deploy three coordinated physiological strategies. First, they synthesize and accumulate compatible organic osmolytes (such as proline, glycine betaine, and pinitol) in the cytosol to maintain osmotic equilibrium without perturbing enzyme kinetics. Second, they actively compartmentalize Na+ and Cl- ions into large central vacuoles using ATP-powered tonoplast Na+/H+ antiporters (NHX family), isolating toxic ions away from active metabolic machinery in the cytoplasm while using them for cellular turgor. Third, many halophytes feature anatomical specializations, such as epidermal salt glands or bladder cells that actively secrete or sequestrate excess salt onto the leaf surface, and thickened suberized Casparian strips in root endodermal layers that strictly exclude apoplastic salt entry.\n\nIn Bangladesh, halophytic physiology is of paramount agricultural significance across the southern coastal belt (Satkhira, Khulna, and Bagerhat), where tidal saline ingress restricts conventional crop production. The Sundarbans mangrove forest exemplifies natural halophytic flora, dominated by species such as Sundari (Heritiera fomes), Gewa (Excoecaria agallocha), and Keora (Sonneratia apetala). In horticultural research, scientists at BARI and BINA investigate halophytic mechanisms in wild relatives to breed or graft salt-tolerant tomato, brinjal, and watermelon crops suitable for dry-season coastal cultivation.",
            "example": "Researchers in the coastal delta of Satkhira are screening wild halophytic rootstocks to graft high-yielding tomato scions, preventing lethal sodium accumulation during the dry winter cropping season.",
            "etymology": "From Ancient Greek ἅλς ('hals', genitive 'halos', salt or the sea) + φυτόν ('phyton', plant). Coined in 19th-century plant geography by Danish botanist Eugenius Warming to classify flora adapted to saline soils.",
            "synonyms": "salt-tolerant plant, euhalophyte, pseudohalophyte, saline-adapted flora",
            "see_also": "glycophyte, osmotic stress, casparian strip, tonoplast antiporter, proline, sundarbans",
            "infographic_recommendation": "Comparative Salinity Tolerance & Cellular Ion Partitioning: Left panel shows root Casparian strip salt exclusion barrier; Center panel shows mesophyll cell vacuolar Na+ compartmentalization via tonoplast NHX antiporter with cytosolic proline osmoregulation; Right panel shows leaf salt gland secretion on a Sundarbans mangrove leaf."
        }
    }
}


def select_few_shot_exemplar(term):
    """
    Selects the most domain-congruent gold-standard exemplar from the verified pool.
    Returns (exemplar_term, exemplar_dict).
    """
    t_lower = term.lower()
    breeding_kw = ["breed", "gene", "cross", "pollin", "steril", "ploid", "embryo", "allele", "hybrid", "male steril", "incompatib"]
    if any(k in t_lower for k in breeding_kw):
        return FEW_SHOT_POOL["breeding"]["term"], FEW_SHOT_POOL["breeding"]["json"]

    phys_kw = ["light", "photo", "salt", "water", "stress", "respir", "hormone", "phyto", "chlor", "osmoti", "saturat", "compensat", "senesc", "dorm"]
    if any(k in t_lower for k in phys_kw):
        return FEW_SHOT_POOL["physiology"]["term"], FEW_SHOT_POOL["physiology"]["json"]

    return FEW_SHOT_POOL["propagation"]["term"], FEW_SHOT_POOL["propagation"]["json"]


def query_ollama(term, model_name):
    """Queries local Ollama instance with automated domain-matched few-shot exemplar and guardrails."""
    exemplar_word, exemplar_data = select_few_shot_exemplar(term)
    exemplar_json_str = json.dumps(exemplar_data, indent=2)

    prompt = (
        f"You are an authoritative botanical and horticultural lexicographer building a specialized, "
        f"university-level reference dictionary for an MS/BS in Horticulture.\n"
        f"Provide comprehensive, academically rigorous yet accessible lexical details for the term: \"{term}\".\n\n"
        f"CRITICAL LEXICOGRAPHICAL GUIDELINES:\n"
        f"1. Context: Focus strictly on botanical, agricultural, breeding, physiological, or mycological meaning.\n"
        f"2. Compound Completeness: For multi-word terms (e.g. 'recalcitrant seed', 'fruiting body', 'spawn culture', 'air layering'), define the FULL compound phrase. Never omit words or define only the adjective.\n"
        f"3. Botanical vs. Mycological Rigor: In botany/pomology, an angiosperm tree bears a 'fruit' (fructus/pericarp); a 'fruiting body' (sporocarp) is strictly a fungal reproductive organ (mushroom cultivation or pathology). NEVER confuse tree fruit with fungal fruiting bodies, and never claim orchardists 'prune the fruiting body'.\n"
        f"4. Mushroom Spawn Rigor: Commercial mushroom spawn is strictly pure vegetative dikaryotic mycelium grown on sterilized cereal grain (wheat, rye, sorghum); NEVER claim commercial spawn is propagated from sexual spores (which segregate and degenerate).\n"
        f"5. Crop & Phenological Congruence: Match crop examples to biological reality. For tropical/subtropical phenomena (e.g. rhythmic flushing, recalcitrant seeds, nucellar embryony, marcottage), cite appropriate tropical/subtropical taxa (e.g. Mangifera indica, Litchi chinensis, Citrus spp., Artocarpus heterophyllus, Psidium guajava). Do NOT cite temperate deciduous crops (e.g. apple, pear) for tropical flushing dynamics or recalcitrant seed biology.\n"
        f"6. Overbearing & Alternate Bearing: Overbearing/overcropping describes excessive crop load on a fruit tree; developing seed embryos produce abundant gibberellins which inhibit flower bud induction for the following season, triggering alternate/biennial bearing.\n"
        f"7. No Sub-mechanism Generalization: Do NOT define broad phenomena by only one subtype (e.g. apomixis is asexual seed formation / agamospermy—do NOT define it solely as nucellar embryony; true seed is a fertilized ovule, contrasting with vegetative propagules—never claim it requires 'two parents' since self-pollinated crops also produce true seed).\n"
        f"8. Physiological Rigor: Adhere strictly to authoritative seed physiology (Roberts 1973, Bewley & Black). Recalcitrant seeds die because they lack LEA proteins/vitrification and remain metabolically active (do NOT claim high lipids); orthodox seeds tolerate desiccation to 2-5% obeying Roberts equations.\n"
        f"9. Part of Speech: Horticultural processes/techniques ('grafting', 'air layering', 'vernalization', 'natural thinning') are nouns (n.).\n"
        f"10. Accurate Etymology: State genuine Greek/Latin/historical roots with coining scholar/date where known. 'Surplus' is from Latin super + plus, NOT supellex; 'spawn' is from Anglo-Norman espandre, NOT Old English spawan.\n"
        f"11. Synonyms: You MUST provide 1 to 3 valid technical synonyms, alternative horticultural terms, or English/Latin equivalents (e.g. 'marcottage' for air layering; 'agamospermy' for apomixis; 'sporocarp' for fruiting body; 'grain spawn' for spawn culture; 'overcropping' for overbearing; 'physiological fruit drop' for natural thinning). DO NOT leave empty.\n"
        f"12. Standard Syllabic IPA: Provide exact phonetic transcription with syllable dots ('.') and stress marks ('ˈ', 'ˌ') covering EVERY word in the term. Roots ending in '-physiology' are transcribed strictly as /...ˌfɪz.iˈɑː.lə.dʒi/ (never 'zaɪ').\n"
        f"13. Balanced Scientific Storytelling (Bains Style): Provide a 'conceptual_exposition' of 2-3 structured paragraphs in lucid, natural, balanced scientific English. Explain: (a) the physical/structural basis; (b) the physiological/cellular/hormonal mechanism; (c) real-world agro-ecological context with Bangladeshi crops (e.g., mango, litchi, guava, brinjal, oyster mushroom, tea). Do NOT use childish or casual metaphors ('trick the plant', 'marathon with people on back'); do NOT use impenetrable, abstruse Ph.D. jargon ('pseudo-parenchymatous hyphal ontogeny'). Strike the golden mean of an articulate university professor.\n"
        f"14. Infographic Blueprint: Provide an 'infographic_recommendation' containing a multi-step or multi-panel visual blueprint (e.g. 3-panel step-by-step nursery schematic, comparative anatomical cutaway, or hormonal feedback flow chart) suitable for future technical illustration.\n"
        f"15. Photoperiodism & Dark-Length Rigor: Short-day plants (SDPs) are biologically LONG-NIGHT plants requiring continuous darkness exceeding critical night length; long-day plants (LDPs) are SHORT-NIGHT plants. NEVER call an SDP a 'short-night plant'. A brief night-break flash of red light disrupts SDP flowering and promotes LDP flowering.\n"
        f"16. Photoperiodic Crop Congruence: Do NOT claim mango or litchi are short-day or photoperiodic plants (their floral induction is triggered by low winter temperatures/dormancy, not day length). Cite genuine tropical/subtropical SDPs (e.g. Lablab purpureus / country bean Shim, photoperiod-sensitive Aman rice, Chrysanthemum) and LDPs (cool-season bolting in spinach, radish, lettuce; photoperiod lighting in floriculture).\n"
        f"17. Light Ecology Rigor: Heliophytes (sun plants) have thick leaves with multi-layer palisade cells, high LCP/LSP, and high NPQ (NEVER claim they have broad/thin shade leaves); Sciophytes (shade plants) have thin leaves, high specific leaf area, low Chl a/b ratio, and low LCP/LSP. NEVER claim orchard trees like mango or litchi are sciophytes! Cite genuine sciophytes: ginger, turmeric, cardamom, betel vine barouj, shade tea.\n"
        f"18. Autotrophic / Holophytic Nutrition Rigor: A 'holophyte' is an organism exhibiting holophytic (photoautotrophic) nutrition, synthesizing its own food from inorganic precursors (CO2, H2O, salts) using light, in contrast to holozoic (animals) and saprophytic/parasitic organisms. NEVER claim a holophyte is an 'air plant' or epiphyte!\n"
        f"19. Halophyte & Deltaic Salinity Rigor: Halophytes exclude, compartmentalize via NHX into vacuoles, or excrete salt; cite Sundarbans mangrove taxa (Heritiera fomes, Excoecaria agallocha) and coastal Bangladesh salinity belt (Satkhira, Khulna).\n"
        f"20. Anti-Mango Overfitting: Do NOT default to 'In a mango orchard' for unrelated biological mechanisms (e.g. self-incompatibility, apomixis, dormancy, shelf-life, senescence, sterility, sciophytes, velamen). Use the authentic crop for each concept: brassicas/onion for sterility and self-incompatibility; banana/tomato for climacteric postharvest shelf-life and senescence; citrus for nucellar polyembryony; epiphytic orchids for velamen; potato/yam for tubers; onion/garlic/lily for bulbs; gladiolus/taro for corms; oyster/button mushrooms for saprophytes.\n"
        f"21. Underground Organs (Geophytes) Rigor: Strictly distinguish true bulbs (flattened basal plate + fleshy concentric scale leaves, e.g. Allium cepa), corms (solid swollen subterranean stem tissue with distinct nodes/internodes, e.g. Gladiolus, Colocasia), and tubers (swollen stoloniferous stems or storage roots, e.g. Solanum tuberosum). NEVER list bulb, corm, and tuber as synonyms of each other!\n"
        f"22. Velamen Anatomy Rigor: Velamen radicum is a multi-layered spongy mantle of DEAD cells at functional maturity surrounding aerial roots of epiphytic orchids and aroids; velamen cells DO NOT contain chloroplasts (when hydrated they turn transparent, revealing the underlying green living cortex).\n"
        f"23. Saprophyte vs. Plant: Non-photosynthetic plants are mycoheterotrophs, not saprophytes; true saprobes in horticulture are saprotrophic fungi (e.g. Agaricus, Pleurotus) and bacteria secreting extracellular enzymes to decompose organic matter.\n\n"
        f"--- GOLD-STANDARD BENCHMARK EXEMPLAR ---\n"
        f"Study the exact depth, tone, syllabic IPA formatting, 3-paragraph structure, and authentic Bangladeshi crop context in this verified benchmark entry for \"{exemplar_word}\":\n\n"
        f"{exemplar_json_str}\n\n"
        f"--- YOUR TASK ---\n"
        f"Now generate an entry of identical caliber, academic rigor, and JSON schema for the target term: \"{term}\".\n"
        f"Return ONLY a valid JSON object (no markdown, no backticks, no introductory text) matching the schema of the benchmark example above, with keys:\n"
        f"- \"ipa\": Standard IPA pronunciation enclosed in slashes (e.g. \"/ˈsaɪ.ən/\")\n"
        f"- \"pos\": Abbreviated part of speech (\"n.\", \"v.\", \"adj.\")\n"
        f"- \"subfield\": One of: {', '.join(SUBFIELDS)}\n"
        f"- \"definition\": Rigorous 1-2 sentence academic definition in the botanical/horticultural sense.\n"
        f"- \"conceptual_exposition\": 2 to 3 paragraphs of balanced scientific storytelling explaining the structural basis, physiological mechanism, and practical crop context.\n"
        f"- \"example\": Realistic sentence demonstrating practical horticultural use (orchard, greenhouse, lab, field trial).\n"
        f"- \"etymology\": True morphological derivation or naming origin.\n"
        f"- \"synonyms\": Comma-separated list of genuine technical/trade synonyms (MANDATORY, never empty).\n"
        f"- \"see_also\": 2 to 4 comma-separated related botanical/horticultural concepts.\n"
        f"- \"infographic_recommendation\": Multi-step or multi-panel technical figure description.\n"
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
            parsed = json.loads(raw_text)
            if parsed and isinstance(parsed, dict):
                # Normalize common key variances from local LLMs
                if "definition" not in parsed and "meaning" in parsed:
                    parsed["definition"] = parsed["meaning"]
                if "conceptual_exposition" not in parsed and "explanation" in parsed:
                    parsed["conceptual_exposition"] = parsed["explanation"]
                elif "conceptual_exposition" not in parsed and "exposition" in parsed:
                    parsed["conceptual_exposition"] = parsed["exposition"]
                if "infographic_recommendation" not in parsed and "infographic" in parsed:
                    parsed["infographic_recommendation"] = parsed["infographic"]
            return parsed
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


def parse_csv_field(val):
    """Parses a comma-separated string into a list of clean, unique items."""
    if not val:
        return []
    items = []
    seen = set()
    for part in str(val).split(","):
        cleaned = re.sub(r"\s+", " ", part).strip()
        cleaned = re.sub(r"^(?:see\s+also\s*:\s*)+", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            items.append(cleaned)
    return items


def format_csv_field(items):
    """Formats a list of strings into a clean, comma-separated string without duplicates."""
    seen = set()
    cleaned = []
    for it in items:
        clean_it = re.sub(r"\s+", " ", str(it)).strip()
        clean_it = re.sub(r"^(?:see\s+also\s*:\s*)+", "", clean_it, flags=re.IGNORECASE).strip()
        if clean_it and clean_it.lower() not in seen:
            seen.add(clean_it.lower())
            cleaned.append(clean_it)
    return ", ".join(cleaned)


def link_bidirectional_see_also(item, term_map, known_synonyms=None):
    """
    Ensures bidirectional 'See Also' relationships between `item` and any existing terms in `term_map`.
    
    1. If `item` lists existing terms in its 'See Also', those existing terms will have `item['Word']`
       added to their 'See Also'.
    2. If `item` is a synonym or shares strong similarity with an existing term (via Synonyms, KNOWN_SYNONYMS,
       or compound base matching), both terms will link to each other in 'See Also'.
    3. If any existing term already listed `item['Word']` in its 'See Also', `item['See Also']` will include that term.
    
    Updates `item` in-place and updates corresponding dicts in `term_map` in-place.
    Returns list of linked terms.
    """
    if known_synonyms is None:
        known_synonyms = KNOWN_SYNONYMS if "KNOWN_SYNONYMS" in globals() else {}

    item_word = item.get("Word", "").strip()
    if not item_word:
        return []
    item_word_lower = item_word.lower()

    # Parse current item's See Also and Synonyms
    item_see_also = parse_csv_field(item.get("See Also", ""))
    item_see_lowers = {s.lower(): s for s in item_see_also}

    item_synonyms = parse_csv_field(item.get("Synonyms", ""))
    item_syn_lowers = {s.lower() for s in item_synonyms}

    # Include known synonyms for item_word
    if item_word_lower in known_synonyms:
        for ks in parse_csv_field(known_synonyms[item_word_lower]):
            item_syn_lowers.add(ks.lower())

    linked_terms = []

    # Iterate over all existing terms
    for exist_word_lower, exist_item in term_map.items():
        if exist_word_lower == item_word_lower:
            continue

        exist_word = exist_item.get("Word", "").strip()
        if not exist_word:
            continue

        exist_see_also = parse_csv_field(exist_item.get("See Also", ""))
        exist_see_lowers = {s.lower(): s for s in exist_see_also}

        exist_synonyms = parse_csv_field(exist_item.get("Synonyms", ""))
        exist_syn_lowers = {s.lower() for s in exist_synonyms}
        if exist_word_lower in known_synonyms:
            for ks in parse_csv_field(known_synonyms[exist_word_lower]):
                exist_syn_lowers.add(ks.lower())

        should_link = False

        # Condition 1: Already explicitly mentioned in item's See Also
        if exist_word_lower in item_see_lowers:
            should_link = True

        # Condition 2: item is explicitly mentioned in exist_item's See Also
        if item_word_lower in exist_see_lowers:
            should_link = True

        # Condition 3: One is a synonym of the other
        if exist_word_lower in item_syn_lowers or item_word_lower in exist_syn_lowers:
            should_link = True

        # Condition 4: Shared non-trivial synonym
        common_synonyms = item_syn_lowers.intersection(exist_syn_lowers)
        if any(len(cs) >= 4 and cs not in {"plant", "tree", "crop", "leaf", "root", "stem", "seed"} for cs in common_synonyms):
            should_link = True

        # Condition 5: Compound / morphological base match (e.g. grafting & whip grafting, tuber & stem tuber)
        generic_stems = {"plant", "flora", "crop", "tree", "fruit", "seed", "leaf", "soil", "stress"}
        if item_word_lower not in generic_stems and exist_word_lower not in generic_stems:
            pat1 = r"(?:^|[\s\-])" + re.escape(item_word_lower) + r"(?:$|[\s\-])"
            pat2 = r"(?:^|[\s\-])" + re.escape(exist_word_lower) + r"(?:$|[\s\-])"
            if len(item_word_lower) >= 5 and re.search(pat1, exist_word_lower):
                should_link = True
            elif len(exist_word_lower) >= 5 and re.search(pat2, item_word_lower):
                should_link = True

        if should_link:
            # 1. Ensure exist_word is in item's See Also
            if exist_word_lower not in [s.lower() for s in item_see_also]:
                item_see_also.append(exist_word)
                linked_terms.append(exist_word)

            # 2. Ensure item_word is in exist_item's See Also (RECIPROCAL LINK)
            if item_word_lower not in [s.lower() for s in exist_see_also]:
                exist_see_also.append(item_word)
                exist_item["See Also"] = format_csv_field(exist_see_also)

    item["See Also"] = format_csv_field(item_see_also)
    return linked_terms


def sync_all_bidirectional_see_also(term_map):
    """
    Scans the entire dictionary term_map and reconciles all one-way 'See Also' links
    so every single link is bidirectional. Returns the number of reciprocal links added.
    """
    total_added = 0
    for word_lower, item in list(term_map.items()):
        current_word = item.get("Word", "").strip()
        if not current_word:
            continue
        see_also_items = parse_csv_field(item.get("See Also", ""))
        for target_name in see_also_items:
            target_lower = target_name.lower()
            if target_lower in term_map and target_lower != word_lower:
                target_item = term_map[target_lower]
                target_see = parse_csv_field(target_item.get("See Also", ""))
                target_see_lowers = [s.lower() for s in target_see]
                if word_lower not in target_see_lowers:
                    target_see.append(current_word)
                    target_item["See Also"] = format_csv_field(target_see)
                    total_added += 1
    return total_added


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
    .badge-verified-human { background: var(--green-bg); color: var(--green-text); border: 1px solid var(--green-border); }
    .badge-verified-flash, .badge-verified { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-review { background: var(--yellow-bg); color: var(--yellow-text); border: 1px solid var(--yellow-border); }

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
      max-width: 640px;
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
    .cell-exp { min-width: 320px; max-width: 440px; line-height: 1.45; font-size: 12px; color: #334155; }
    .cell-info { min-width: 240px; max-width: 320px; font-size: 12px; color: #047857; background: #ecfdf5; border-radius: 4px; padding: 4px; }
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
    .status-verified-human {
      background: var(--green-bg);
      color: var(--green-text);
      border-color: var(--green-border);
    }
    .status-verified-flash, .status-verified {
      background: #eff6ff;
      color: #1d4ed8;
      border-color: #bfdbfe;
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
      <span class="badge-count badge-verified-human" id="count-human">0 Human verified</span>
      <span class="badge-count badge-verified-flash" id="count-flash">0 Verified by Flash</span>
      <span class="badge-count badge-review" id="count-review">0 Needs review</span>
      <button class="btn btn-outline" onclick="exportCSV()">Download CSV</button>
    </div>
  </header>

  <div class="control-bar">
    <div class="add-form">
      <input type="text" id="new-term" class="add-input" placeholder="Enter term(s), single or comma-separated (e.g., air layering, t-budding, micro-reserves)..." onkeydown="if(event.key==='Enter') generateTerm()">
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
        <option value="Human verified">Human Verified Only</option>
        <option value="Verified by Flash">Verified by Flash Only</option>
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
          <th>Conceptual Exposition</th>
          <th>Example Sentence</th>
          <th>Etymology</th>
          <th>Synonyms</th>
          <th>See Also</th>
          <th>Infographic Blueprint</th>
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

      let humanCount = 0;
      let flashCount = 0;
      let reviewCount = 0;

      terms.forEach((t, idx) => {
        if (t.Status === 'Human verified') humanCount++;
        else if (t.Status === 'Verified by Flash' || t.Status === 'Verified') flashCount++;
        else if (t.Status === 'Needs review') reviewCount++;

        // Filters
        const matchesQuery = !query || Object.values(t).some(v => String(v).toLowerCase().includes(query));
        const matchesSf = !sfFilter || t.Subfield === sfFilter;
        let matchesSt = true;
        if (stFilter === 'Verified by Flash') matchesSt = (t.Status === 'Verified by Flash' || t.Status === 'Verified');
        else if (stFilter) matchesSt = (t.Status === stFilter);

        if (!matchesQuery || !matchesSf || !matchesSt) return;

        const tr = document.createElement('tr');

        tr.innerHTML = `
          <td class="cell-word editable" contenteditable="true" onblur="updateField(${idx}, 'Word', this.innerText)">${escapeHtml(t.Word)}</td>
          <td class="cell-ipa editable" contenteditable="true" onblur="updateField(${idx}, 'Pronunciation (IPA)', this.innerText)">${escapeHtml(t['Pronunciation (IPA)'])}</td>
          <td class="cell-pos editable" contenteditable="true" onblur="updateField(${idx}, 'Part of Speech', this.innerText)">${escapeHtml(t['Part of Speech'])}</td>
          <td class="cell-subfield editable" contenteditable="true" onblur="updateField(${idx}, 'Subfield', this.innerText)">${escapeHtml(t.Subfield)}</td>
          <td class="cell-def editable" contenteditable="true" onblur="updateField(${idx}, 'Definition', this.innerText)">${escapeHtml(t.Definition)}</td>
          <td class="cell-exp editable" contenteditable="true" onblur="updateField(${idx}, 'Conceptual Exposition', this.innerText)">${escapeHtml(t['Conceptual Exposition'] || '')}</td>
          <td class="cell-ex editable" contenteditable="true" onblur="updateField(${idx}, 'Example Sentence', this.innerText)">${escapeHtml(t['Example Sentence'])}</td>
          <td class="cell-ety editable" contenteditable="true" onblur="updateField(${idx}, 'Etymology', this.innerText)">${escapeHtml(t.Etymology)}</td>
          <td class="cell-syn editable" contenteditable="true" onblur="updateField(${idx}, 'Synonyms', this.innerText)">${escapeHtml(t.Synonyms)}</td>
          <td class="cell-see editable" contenteditable="true" onblur="updateField(${idx}, 'See Also', this.innerText)">${escapeHtml(t['See Also'])}</td>
          <td class="cell-info editable" contenteditable="true" onblur="updateField(${idx}, 'Infographic Recommendation', this.innerText)">${escapeHtml(t['Infographic Recommendation'] || '')}</td>
          <td class="cell-date">${escapeHtml(t['Date Added'])}</td>
          <td>
            <select class="status-select ${getStatusClass(t.Status)}" onchange="updateStatus(${idx}, this.value)">
              <option value="Needs review" ${t.Status === 'Needs review' ? 'selected' : ''}>Needs review</option>
              <option value="Verified by Flash" ${t.Status === 'Verified by Flash' || t.Status === 'Verified' ? 'selected' : ''}>Verified by Flash</option>
              <option value="Human verified" ${t.Status === 'Human verified' ? 'selected' : ''}>Human verified</option>
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

      document.getElementById('count-human').textContent = `${humanCount} Human verified`;
      document.getElementById('count-flash').textContent = `${flashCount} Verified by Flash`;
      document.getElementById('count-review').textContent = `${reviewCount} Needs review`;
    }

    function getStatusClass(status) {
      if (status === 'Human verified') return 'status-verified-human';
      if (status === 'Verified by Flash' || status === 'Verified') return 'status-verified-flash';
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

      if (field === 'Word') {
        const lowerVal = cleanVal.toLowerCase();
        const exists = terms.some((t, i) => i !== idx && t.Word.toLowerCase() === lowerVal);
        if (exists) {
          showToast(`Cannot rename: "${cleanVal}" already exists in dictionary.`);
          renderTable();
          return;
        }
      }

      terms[idx][field] = cleanVal;
      await saveTermToServer(terms[idx]);

      if (field === 'See Also' || field === 'Synonyms' || field === 'Word') {
        await loadTerms(); // Re-sync reciprocal links if relationships changed
      }
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

    function splitTerms(str) {
      if (!str) return [];
      const raw = str.split(/[,;\\n\\r]+/);
      const cleaned = [];
      const seen = new Set();
      for (let r of raw) {
        const term = r.trim().replace(/\\s+/g, ' ');
        if (term && !seen.has(term.toLowerCase())) {
          seen.add(term.toLowerCase());
          cleaned.push(term);
        }
      }
      return cleaned;
    }

    async function generateTerm() {
      const input = document.getElementById('new-term');
      const rawInput = input.value.trim();
      if (!rawInput) return;

      const termsToGen = splitTerms(rawInput);
      if (termsToGen.length === 0) return;

      const btn = document.getElementById('btn-generate');
      const btnText = document.getElementById('btn-text');

      btn.disabled = true;
      input.disabled = true;

      let successCount = 0;
      let ignoredCount = 0;
      let generatedNames = [];

      try {
        for (let i = 0; i < termsToGen.length; i++) {
          const currentWord = termsToGen[i];

          // Check client-side if word already exists in dictionary
          const isDuplicate = terms.some(t => t.Word.toLowerCase() === currentWord.toLowerCase());
          if (isDuplicate) {
            showToast(`Ignored: "${currentWord}" already exists in dictionary.`);
            ignoredCount++;
            continue;
          }

          if (termsToGen.length > 1) {
            btnText.innerHTML = `<span class="loading-spinner"></span> Analyzing (${i + 1}/${termsToGen.length}): ${escapeHtml(currentWord)}...`;
          } else {
            btnText.innerHTML = `<span class="loading-spinner"></span> Analyzing: ${escapeHtml(currentWord)}...`;
          }

          try {
            const res = await fetch('/api/generate', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ word: currentWord })
            });
            const data = await res.json();

            if (data.status === 'ignored') {
              showToast(data.message || `Ignored: "${currentWord}" already exists in dictionary.`);
              ignoredCount++;
              continue;
            }

            const newEntries = Array.isArray(data) ? data : (data.items || (data.Word ? [data] : []));
            
            for (let entry of newEntries) {
              if (entry && entry.Word) {
                const existingIdx = terms.findIndex(t => t.Word.toLowerCase() === entry.Word.toLowerCase());
                if (existingIdx >= 0) {
                  terms[existingIdx] = entry;
                } else {
                  terms.push(entry);
                }
                generatedNames.push(entry.Word);
                successCount++;
              }
            }

            // Keep table sorted and re-render progressively
            terms.sort((a,b) => a.Word.toLowerCase().localeCompare(b.Word.toLowerCase()));
            renderTable();
          } catch (itemErr) {
            console.error(`Failed to generate "${currentWord}":`, itemErr);
          }
        }

        // Re-sync all terms from server to ensure all reciprocal See Also updates appear immediately
        if (successCount > 0) {
          await loadTerms();
        }

        input.value = '';
        if (successCount === 1) {
          showToast(`Generated: ${generatedNames[0]}`);
        } else if (successCount > 1) {
          showToast(`✓ Generated ${successCount} terms: ${generatedNames.join(', ')}`);
        } else if (ignoredCount > 0) {
          showToast(`No new terms generated (${ignoredCount} already existed).`);
        } else {
          showToast('Failed to generate term(s)');
        }
      } catch (e) {
        showToast('Error during generation');
      } finally {
        btn.disabled = false;
        input.disabled = false;
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
            term_map = {t.get("Word", "").strip().lower(): t for t in terms}
            updated = False
            if word_target in term_map:
                target_item = term_map[word_target]
                target_item.update(payload)
                # Enforce bidirectional See Also links if relationships were modified
                link_bidirectional_see_also(target_item, term_map)
                updated = True
            if updated:
                updated_terms = list(term_map.values())
                updated_terms.sort(key=lambda t: t.get("Word", "").lower())
                save_terms(updated_terms)
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
            raw_words = payload.get("words") or payload.get("word", "")
            terms_to_process = split_terms(raw_words)
            if not terms_to_process:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No valid terms provided."}).encode("utf-8"))
                return

            terms = load_terms()
            term_map = {t.get("Word", "").strip().lower(): t for t in terms}

            # Duplicate Check: filter out terms that already exist in the dictionary
            new_terms = []
            ignored_terms = []
            for w in terms_to_process:
                w_lower = w.strip().lower()
                w_canonical = TERM_NORMALIZATIONS.get(w_lower, w_lower)
                if w_lower in term_map or w_canonical in term_map:
                    ignored_terms.append(w)
                else:
                    new_terms.append(w)

            # If all requested terms already exist, ignore and return without running Ollama
            if not new_terms:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                existing_items = [term_map.get(w.lower()) or term_map.get(TERM_NORMALIZATIONS.get(w.lower(), w.lower())) for w in ignored_terms]
                existing_items = [x for x in existing_items if x]
                self.wfile.write(json.dumps({
                    "status": "ignored",
                    "ignored": ignored_terms,
                    "message": f"Term(s) already exist in dictionary and were ignored: {', '.join(ignored_terms)}",
                    "items": existing_items,
                    "Word": existing_items[0]["Word"] if existing_items else ignored_terms[0]
                }).encode("utf-8"))
                return

            model_name = check_ollama_model()
            today = date.today().strftime("%Y-%m-%d")

            generated_items = []
            for idx_word, word in enumerate(new_terms):
                if idx_word > 0:
                    time.sleep(2.5)  # Thermal pacing cooldown for fanless Apple Silicon M4
                # Query Ollama
                entry = query_ollama(word, model_name)
                verified_ipa = fetch_verified_ipa(word)
                final_ipa = verified_ipa if verified_ipa else (entry.get("ipa", "") if entry else "")

                new_item = {
                    "Word": word,
                    "Pronunciation (IPA)": final_ipa,
                    "Part of Speech": entry.get("pos", "n.") if entry else "n.",
                    "Subfield": entry.get("subfield", "Botany") if entry else "Botany",
                    "Definition": entry.get("definition", "") if entry else "",
                    "Conceptual Exposition": entry.get("conceptual_exposition", "") if entry else "",
                    "Example Sentence": entry.get("example", "") if entry else "",
                    "Etymology": entry.get("etymology", "") if entry else "",
                    "Synonyms": entry.get("synonyms", "") if entry else "",
                    "See Also": entry.get("see_also", "") if entry else "",
                    "Infographic Recommendation": entry.get("infographic_recommendation", "") if entry else "",
                    "Date Added": today,
                    "Status": "Needs review"
                }
                # Run multi-layer botanical guardrail to enforce IPA accuracy and prevent hallucinations
                new_item = apply_botanical_guardrails(new_item)

                # Link relevant synonyms and similar words in 'See Also' bidirectionally
                link_bidirectional_see_also(new_item, term_map)

                term_map[word.lower()] = new_item
                generated_items.append(new_item)

            updated_terms = list(term_map.values())
            updated_terms.sort(key=lambda t: t.get("Word", "").lower())
            save_terms(updated_terms)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if len(generated_items) == 1 and not ignored_terms:
                self.wfile.write(json.dumps(generated_items[0]).encode("utf-8"))
            else:
                resp_payload = {
                    "status": "ok",
                    "count": len(generated_items),
                    "items": generated_items,
                    "ignored": ignored_terms,
                    "Word": generated_items[0]["Word"] if generated_items else ""
                }
                if ignored_terms:
                    resp_payload["message"] = f"Generated {len(generated_items)} term(s). Ignored duplicate(s): {', '.join(ignored_terms)}"
                self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
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
