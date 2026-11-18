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
import re
import json
import csv
import urllib.request
import urllib.error
import urllib.parse
import time
from datetime import date

OLLAMA_BASE = "http://localhost:11434"
RECOMMENDED_MODELS = ["qwen2.5:14b", "qwen2.5:7b", "llama3.2:3b", "llama3.2", "mistral:7b", "mistral"]

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
            exp = exp.replace("tricking a branch into believing it is underground", "inducing adventitious root formation in situ")
            exp = exp.replace("trick a branch into believing it is underground", "induce adventitious root formation in situ")
            exp = exp.replace("Imagine an athlete running a marathon while carrying three passengers on their back", "When a fruit tree carries an excessive crop load beyond its photosynthetic support capacity")
            item["Conceptual Exposition"] = exp

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
    """Send term to local Ollama model with automated domain-matched few-shot exemplar and return structured JSON."""
    exemplar_word, exemplar_data = select_few_shot_exemplar(term)
    exemplar_json_str = json.dumps(exemplar_data, indent=2)

    prompt = (
        f"You are an authoritative botanical and horticultural lexicographer building a specialized, "
        f"graduate-level reference dictionary for an MS in Horticulture.\n"
        f"Provide comprehensive, academically rigorous lexical details for the term: \"{term}\".\n\n"
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
            parsed = json.loads(raw_text)
            if parsed and isinstance(parsed, dict):
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

        if i > 1:
            time.sleep(2.5)  # Thermal pacing cooldown for fanless Apple Silicon M4

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
                "Conceptual Exposition": entry.get("conceptual_exposition", ""),
                "Example Sentence": entry.get("example", ""),
                "Etymology": entry.get("etymology", ""),
                "Synonyms": entry.get("synonyms", ""),
                "See Also": entry.get("see_also", ""),
                "Infographic Recommendation": entry.get("infographic_recommendation", ""),
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
                item_dict.get("Conceptual Exposition", ""),
                item_dict["Example Sentence"],
                item_dict["Etymology"],
                item_dict["Synonyms"],
                item_dict["See Also"],
                item_dict.get("Infographic Recommendation", ""),
                item_dict["Date Added"],
                item_dict["Status"]
            ]
            print(f"   ✓ Success! [{item_dict['Subfield']}] {item_dict['Definition'][:70]}...")
        else:
            row = [clean_word, "", "", "", "", "", "", "", "", "", "", today, "Not found"]
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


def save_or_update_terms_to_csv(new_rows, csv_path):
    """
    Saves or updates rows in local_dictionary.csv with all 13 columns,
    preserving headers, keeping alphabetical sort, and writing atomically.
    """
    existing_rows = []
    if os.path.exists(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            existing_rows = list(reader)

    if existing_rows:
        header = existing_rows[0]
        data_rows = existing_rows[1:]
    else:
        header = HEADERS
        data_rows = []

    # Map by lowercase word for updating existing rows without duplicate entries
    row_map = {r[0].strip().lower(): r for r in data_rows if r and len(r) > 0}
    for nr in new_rows:
        if nr and len(nr) >= 1:
            row_map[nr[0].strip().lower()] = nr

    combined = list(row_map.values())
    combined.sort(key=lambda r: r[0].lower() if r and len(r) > 0 else "")

    temp_file = csv_path + ".tmp"
    with open(temp_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(combined)
    os.replace(temp_file, csv_path)


def batch_process_and_save(terms, model_name, output_file=None):
    """
    Processes a list of terms, applies multi-layer botanical guardrails,
    enforces 13-column format, and updates local_dictionary.csv.
    """
    if not output_file:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(base_dir, "local_dictionary.csv")

    today = date.today().strftime("%Y-%m-%d")
    total = len(terms)
    print(f"\n=======================================================")
    print(f"  Batch Processing {total} Horticultural Term(s) via Ollama")
    print(f"  Model: {model_name} | Target: {os.path.basename(output_file)}")
    print(f"=======================================================\n")

    saved_rows = []
    for i, term in enumerate(terms, 1):
        print(f"[{i}/{total}] Analyzing: '{term}'...")
        entry = query_ollama(term, model_name)
        if not entry or not entry.get("definition"):
            print(f"   [!] Could not generate structured definition for '{term}'.\n")
            continue

        verified_ipa = fetch_verified_ipa(term)
        final_ipa = verified_ipa if verified_ipa else entry.get("ipa", "")

        item_dict = {
            "Word": term,
            "Pronunciation (IPA)": final_ipa,
            "Part of Speech": entry.get("pos", "n."),
            "Subfield": entry.get("subfield", "Botany"),
            "Definition": entry.get("definition", ""),
            "Conceptual Exposition": entry.get("conceptual_exposition", ""),
            "Example Sentence": entry.get("example", ""),
            "Etymology": entry.get("etymology", ""),
            "Synonyms": entry.get("synonyms", ""),
            "See Also": entry.get("see_also", ""),
            "Infographic Recommendation": entry.get("infographic_recommendation", ""),
            "Date Added": today,
            "Status": "Needs review"
        }
        item_dict = apply_botanical_guardrails(item_dict)

        row = [
            item_dict["Word"],
            item_dict["Pronunciation (IPA)"],
            item_dict["Part of Speech"],
            item_dict["Subfield"],
            item_dict["Definition"],
            item_dict.get("Conceptual Exposition", ""),
            item_dict["Example Sentence"],
            item_dict["Etymology"],
            item_dict["Synonyms"],
            item_dict["See Also"],
            item_dict.get("Infographic Recommendation", ""),
            item_dict["Date Added"],
            item_dict["Status"]
        ]
        saved_rows.append(row)

        print(f"   ✓ Subfield:   {item_dict['Subfield']}")
        print(f"   ✓ IPA:        {item_dict['Pronunciation (IPA)']}")
        print(f"   ✓ Definition: {item_dict['Definition'][:75]}...")
        if item_dict.get("Synonyms"):
            print(f"   ✓ Synonyms:   {item_dict['Synonyms']}")
        print()

    if saved_rows:
        save_or_update_terms_to_csv(saved_rows, output_file)
        print(f"=======================================================")
        print(f"✓ Saved {len(saved_rows)} of {total} term(s) to: {output_file}")
        print(f"=======================================================\n")
    else:
        print("No new terms were saved.\n")


def mode_interactive(model_name):
    """Interactive loop to quickly look up single or multiple comma-separated terms."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(base_dir, "local_dictionary.csv")

    print(f"\n--- Interactive Horticulture Term Lookup ---")
    print(f"Results will automatically be saved to '{output_file}'.")
    print("Supports single terms or multiple terms separated by commas.")
    print("Example: 'air layering, t-budding, rootstock-scion interaction'")
    print("Type 'q' to return to menu.\n")

    while True:
        try:
            raw_input_str = input("Enter term(s): ").strip()
            if not raw_input_str:
                continue
            if raw_input_str.lower() in ["q", "quit", "exit"]:
                break

            terms = split_terms(raw_input_str)
            if not terms:
                continue

            batch_process_and_save(terms, model_name, output_file)

        except (KeyboardInterrupt, EOFError):
            break

    print("\nReturning to main menu.")


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

    # Direct terminal command-line batch mode:
    # e.g.: python3 fill_dictionary_ollama.py "air layering, t-budding, rootstock-scion interaction"
    # or:   python3 fill_dictionary_ollama.py "air layering" "t-budding" "micro-reserves"
    if len(sys.argv) > 1:
        raw_args = " ".join(sys.argv[1:])
        terms = split_terms(raw_args)
        if terms:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(base_dir, "local_dictionary.csv")
            batch_process_and_save(terms, chosen_model, output_file)
            return

    print("\nChoose an option:")
    print("  1. Process Google Sheet CSV (reads 'Dictionary.csv' -> writes 'Dictionary_filled.csv')")
    print("  2. Interactive lookup (type single or comma-separated terms)")
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
