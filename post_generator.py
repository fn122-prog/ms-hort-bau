#!/usr/bin/env python3
"""
Horticulture Book & LinkedIn Post Pipeline (post_generator.py)
Automates compilation of verified dictionary terms into high-engagement LinkedIn posts (<1,300 chars).
Features:
- Dual-CSV architecture (local_dictionary.csv + course_study_deck.json -> linkedin_posts.csv)
- Strict verification gate: only 'Verified by Flash' and 'Human verified' entries are eligible for posting
- Randomized selection across verified pending entries with subfield diversity
- 3-theme Bains-style narrative structure (Structural Basis -> Mechanism -> Field & Crop Context)
- CLI post creation wizard (--add-post), queue shuffling (--shuffle), and preview.txt generator
- Ultimate Humaniser Engine (Local Ollama Qwen 2.5 + Deterministic Anti-AI Filter)
- Embedded Localhost Visibility Dashboard (runs on http://localhost:8082)
"""

import os
import sys
import csv
import re
import json
import time
import random
import socket
import webbrowser
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================================================================
# CONFIGURATION & PATH RESOLUTION
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_DIR = os.path.join(BASE_DIR, "Dictionary_and_Study_Materials")
if not os.path.exists(DICT_DIR):
    DICT_DIR = BASE_DIR

SRC_CSV = os.path.join(DICT_DIR, "local_dictionary.csv")
DECK_JSON = os.path.join(DICT_DIR, "course_study_deck.json")
POST_CSV = os.path.join(DICT_DIR, "linkedin_posts.csv")
PREVIEW_FILE = os.path.join(BASE_DIR, "preview.txt")

OLLAMA_BASE = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:14b"
FALLBACK_MODEL = "qwen2.5:7b"
MAX_CHAR_LIMIT = 1300

VERIFIED_STATUSES = {
    "verified by flash",
    "human verified",
    "verified",
}

LINKEDIN_HEADERS = [
    "post_id",
    "word",
    "subfield",
    "verification_status",
    "post_type",
    "definition",
    "conceptual_exposition",
    "example_sentence",
    "infographic_recommendation",
    "generated_post",
    "posted_status",
    "posted_date",
    "humanized_status",
    "character_count"
]

POST_TYPES = {
    "term_of_the_day": "🌱 Term of the Day",
    "field_protocol": "🚜 Field Protocol & Practice",
    "exam_trap": "🧠 HortiPrep Quiz & Exam Trap",
    "book_excerpt": "📖 Behind the Book (Field Notes)",
    "custom": "✨ Custom Post"
}

ACRONYM_TOKENS = {
    "dna", "rna", "pcr", "qtl", "npq", "par", "lcp", "lsp",
    "aba", "iaa", "ga3", "flc", "bari", "brri", "bau", "rcbd"
}

ABBREVIATION_PATTERNS = [
    (r"\be\.g\.", "e__DOT__g__DOT__"),
    (r"\bi\.e\.", "i__DOT__e__DOT__"),
    (r"\betc\.", "etc__DOT__"),
    (r"\bvs\.", "vs__DOT__"),
    (r"\bvar\.", "var__DOT__"),
    (r"\bsubsp\.", "subsp__DOT__"),
    (r"\bcvs\.", "cvs__DOT__"),
    (r"\bcv\.", "cv__DOT__"),
    (r"\bspp\.", "spp__DOT__"),
    (r"\bsp\.", "sp__DOT__"),
    (r"\bapprox\.", "approx__DOT__"),
    (r"\bfig\.", "fig__DOT__"),
    (r"\bet al\.", "et al__DOT__"),
    (r"\bDr\.", "Dr__DOT__"),
    (r"\bProf\.", "Prof__DOT__"),
]

# ==============================================================================
# VERIFICATION & TEXT SANITIZATION HELPERS
# ==============================================================================

def is_verified_status(status):
    """Returns True only for entries verified by Flash or humans."""
    return str(status or "").strip().lower() in VERIFIED_STATUSES


def is_verified_post(post_row):
    """Checks whether a post row is eligible for posting."""
    if not post_row:
        return False
    status = post_row.get("verification_status", "")
    if is_verified_status(status):
        return True
    # Custom posts authored directly by the user are considered human verified
    if post_row.get("post_type") == "custom" and not status:
        return True
    return False


def format_term_title(word):
    """Formats horticultural headwords while preserving acronyms and compound hyphens."""
    raw = re.sub(r"\s+", " ", str(word or "").strip())
    if not raw:
        return ""
    tokens = []
    for space_part in raw.split(" "):
        if "-" in space_part:
            subparts = []
            for hp in space_part.split("-"):
                low = hp.lower()
                if low in ACRONYM_TOKENS:
                    subparts.append(low.upper())
                elif len(hp) == 1:
                    subparts.append(hp.upper())
                else:
                    subparts.append(hp.capitalize())
            tokens.append("-".join(subparts))
        else:
            low = space_part.lower()
            if low in ACRONYM_TOKENS:
                tokens.append(low.upper())
            else:
                tokens.append(space_part.capitalize())
    return " ".join(tokens)


def format_term_inline(word):
    """Formats term for mid-sentence prose, keeping acronyms uppercase and common nouns lowercase."""
    raw = re.sub(r"\s+", " ", str(word or "").strip())
    if not raw:
        return ""
    tokens = []
    for space_part in raw.split(" "):
        if "-" in space_part:
            subparts = []
            for hp in space_part.split("-"):
                low = hp.lower()
                if low in ACRONYM_TOKENS or len(hp) == 1:
                    subparts.append(hp.upper())
                else:
                    subparts.append(low)
            tokens.append("-".join(subparts))
        else:
            low = space_part.lower()
            tokens.append(low.upper() if low in ACRONYM_TOKENS else low)
    return " ".join(tokens)


def sanitize_for_linkedin(text):
    """Cleans markdown/LaTeX artifacts and AI buzzwords so LinkedIn posts render cleanly."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    # Convert bold/italic markdown markers to plain text
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", cleaned)
    # Convert common scientific LaTeX expressions to Unicode/plain text
    cleaned = cleaned.replace("$Q_{10}$", "Q₁₀")
    cleaned = re.sub(r"\$([^$]+)\$", lambda m: m.group(1).replace("_{", "").replace("}", ""), cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return humanize_text_deterministic(cleaned.strip())


def split_paragraphs(text):
    """Splits exposition text into clean thematic paragraphs."""
    cleaned = sanitize_for_linkedin(text)
    return [p.strip() for p in re.split(r"\n+", cleaned) if p.strip()]


def split_sentences(text):
    """Splits prose into complete sentences without breaking botanical abbreviations."""
    if not text:
        return []
    protected = sanitize_for_linkedin(text)
    for pat, token in ABBREVIATION_PATTERNS:
        protected = re.sub(pat, token, protected, flags=re.IGNORECASE)
    raw_sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])", protected)
    sentences = []
    for s in raw_sents:
        restored = s
        for pat, token in ABBREVIATION_PATTERNS:
            # Recover canonical lowercase/case from token
            literal = pat.replace(r"\b", "").replace(r"\.", ".")
            restored = restored.replace(token, literal)
        restored = restored.strip()
        if restored:
            sentences.append(restored)
    return sentences


def word_overlap_ratio(text_a, text_b):
    """Estimates semantic restatement between definition and opening sentence using word stems."""
    stop = {
        "a", "an", "the", "is", "are", "of", "in", "to", "and", "or", "for",
        "that", "which", "with", "by", "from", "on", "as", "into", "plant", "plants",
        "biological", "physiological", "condition", "wherein", "process", "mechanism"
    }
    toks_a = {w[:5] for w in re.findall(r"[a-z]+", text_a.lower()) if w not in stop and len(w) > 2}
    toks_b = {w[:5] for w in re.findall(r"[a-z]+", text_b.lower()) if w not in stop and len(w) > 2}
    if not toks_a or not toks_b:
        return 0.0
    return len(toks_a & toks_b) / min(len(toks_a), len(toks_b))


def shorten_sentence_cleanly(sentence, max_chars):
    """
    Reduces an oversized single sentence at parenthetical or full-clause boundaries
    so it stays grammatically complete without mid-list or dangling-parenthesis cuts.
    """
    s = sentence.strip()
    if len(s) <= max_chars:
        return s

    # Try removing parenthetical asides first
    no_parens = re.sub(r"\s*\([^)]{10,}\)", "", s).strip()
    no_parens = re.sub(r"\s+([,;:.])", r"\1", no_parens)
    if len(no_parens) <= max_chars and len(no_parens) >= 60:
        return no_parens if no_parens.endswith((".", "!", "?")) else no_parens + "."

    # Cut only at complete grammatical clause boundaries (never inside noun lists)
    clause_seps = [
        "; ", " — ", "—", ": ",
        ", while ", ", whereas ", ", which ", ", where ",
        ", resulting in ", ", allowing ", ", ensuring ", ", enabling ",
        ", producing ", ", causing ", ", preventing ", ", serving as ",
        ", characterized by ", ", thereby ", ", particularly ", ", notably ",
        ", because ", ", making ", ", driving ", ", triggering "
    ]
    best_candidate = None
    for sep in clause_seps:
        idx = no_parens.find(sep)
        if idx != -1:
            head = no_parens[:idx].rstrip(" ,;:")
            if 60 <= len(head) + 1 <= max_chars:
                if not re.search(r"\b(e\.g|i\.e|vs|var|cv|cvs|sp|spp|such as|including)\.?$", head, re.IGNORECASE):
                    cand = head if head.endswith((".", "!", "?")) else head + "."
                    if best_candidate is None or len(cand) > len(best_candidate):
                        best_candidate = cand
    if best_candidate:
        return best_candidate

    # Word-boundary fallback avoiding dangling prepositions or open parentheses
    cut = no_parens[:max_chars - 3].rsplit(" ", 1)[0]
    cut = re.sub(r"\s*\([^)]*$", "", cut).rstrip(" ,;:-")
    cut = re.sub(r"\s+\b(and|or|of|to|in|for|with|by|from|at|the|a|an|such|including|e\.g\.|i\.e\.)$", "", cut, flags=re.IGNORECASE).rstrip(" ,;:-")
    return cut + "..."


# ==============================================================================
# ULTIMATE HUMANISER PROMPT & AI SANITIZER
# ==============================================================================

ULTIMATE_HUMANISER_SYSTEM_PROMPT = """Act as an expert scientific editor and university horticulture author revising a LinkedIn post derived from a graduate reference book.

CRITICAL LANGUAGE REQUIREMENT:
Respond strictly and exclusively in fluent English. Never output Chinese or any other language.

Strict revision guidelines:
- Preserve the EXACT 3-theme structure and section headers of the post (Conceptual/Structural Basis -> Mechanism -> Field & Crop Context).
- Keep the voice authoritative, lucid, and engaging for M.S./B.S. students, researchers, and academicians (William Bains style: natural scholarly clarity without childish metaphors or dense impenetrable jargon).
- Vary sentence length and rhythm naturally; avoid robotic transitions ('Moreover,', 'Furthermore,', 'In conclusion,') and generic AI buzzwords ('delve', 'robust', 'innovative', 'crucial', 'testament', 'tapestry', 'pivotal', 'beacon').
- Preserve ALL scientific accuracy, mechanisms, crop names, cultivars, and Bangladesh/regional field details verbatim in spirit. Never invent or hallucinate facts.
- Keep the final post strictly under 1,260 characters total, including emoji headers, question, and hashtags."""

AI_BUZZWORDS = [
    (r"\bdelve(?:s|d)?\s+into\b", "examine"),
    (r"\bdelve(?:s|d)?\b", "explore"),
    (r"\brobust\b", "resilient"),
    (r"\binnovative\b", "novel"),
    (r"\benhanced\b", "improved"),
    (r"\bcrucial\b", "essential"),
    (r"\btestament to\b", "evidence of"),
    (r"\btapestry\b", "complex fabric"),
    (r"\bpivotal\b", "key"),
    (r"\bbeacon\b", "benchmark"),
    (r"\bMoreover,\s*", "In practice, "),
    (r"\bFurthermore,\s*", "Equally important, "),
    (r"\bIn conclusion,\s*", "Ultimately, "),
    (r"\bIt is important to note that\b", "Notably,"),
    (r"\bplays a crucial role in\b", "is vital for"),
]


def humanize_text_deterministic(text):
    """
    Fast offline anti-AI sanitizer. Strips dead giveaway buzzwords and robotic connectors
    while preserving intentional paragraph line breaks.
    """
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned = line
        for pattern, replacement in AI_BUZZWORDS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
        cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines).strip()


def check_ollama_available():
    """Checks if local Ollama daemon is reachable."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                for preferred in [DEFAULT_MODEL, FALLBACK_MODEL, "qwen2.5", "llama3.2"]:
                    for m in models:
                        if m == preferred or m.startswith(preferred.split(":")[0]):
                            return True, m
                if models:
                    return True, models[0]
    except Exception:
        pass
    return False, None


def humanize_with_ollama(text, model_name=None, max_chars=MAX_CHAR_LIMIT):
    """
    Executes the Ultimate Humaniser Prompt through local Ollama instance.
    Non-destructive: operates on formatted post text without altering source CSV exposition.
    Includes strict English and character-limit guardrails with automatic fallback.
    """
    if not text:
        return "", "rules_fallback"

    is_up, detected_model = check_ollama_available()
    if not is_up:
        return humanize_text_deterministic(text), "rules_fallback"

    target_model = model_name or detected_model or DEFAULT_MODEL
    prompt = (
        f"{ULTIMATE_HUMANISER_SYSTEM_PROMPT}\n\n"
        f"LinkedIn post to polish (keep under {max_chars} characters):\n"
        f"\"\"\"\n{text}\n\"\"\"\n\n"
        f"Return ONLY the revised English LinkedIn post. Do NOT include introductory remarks, "
        f"markdown code blocks, or translation notes."
    )

    payload = {
        "model": target_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.55,
            "top_p": 0.9,
        }
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=50) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            response_text = res_json.get("response", "").strip()

            # Reject accidental bilingual/non-English drift
            chinese_chars = re.findall(r"[\u4e00-\u9fff]", response_text)
            if len(chinese_chars) > 3 or not response_text:
                return humanize_text_deterministic(text), "rules_fallback"

            if response_text.startswith("```"):
                response_text = re.sub(r"^```[a-zA-Z]*\n?", "", response_text)
                response_text = re.sub(r"\n?```$", "", response_text).strip()

            cleaned = sanitize_for_linkedin(humanize_text_deterministic(response_text))
            # Guard against runaway output or hallucinated truncation
            if len(cleaned) > max_chars or len(cleaned) < 200:
                return humanize_text_deterministic(text), "rules_fallback"
            return cleaned, "ollama_qwen"
    except Exception:
        return humanize_text_deterministic(text), "rules_fallback"


# ==============================================================================
# THEMATIC EXTRACTION & POST FORMATTERS
# ==============================================================================

def load_study_deck_map():
    """Loads optional enriched study cards keyed by lowercase term."""
    if not os.path.exists(DECK_JSON):
        return {}
    try:
        with open(DECK_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        cards = data.get("cards", []) if isinstance(data, dict) else []
        return {
            str(c.get("term", "")).strip().lower(): c
            for c in cards
            if isinstance(c, dict) and c.get("term")
        }
    except Exception:
        return {}


def build_hashtags(subfield, extra_tag=None):
    """Generates clean 4-5 academic/horticulture hashtags without duplication."""
    clean_subfield = subfield.strip() if subfield else "Plant Science"
    subfield_tag = "#" + re.sub(r"[^a-zA-Z]", "", clean_subfield)
    tags = ["#Horticulture", "#PlantScience", "#Botany"]
    if extra_tag and extra_tag not in tags:
        tags.append(extra_tag)
    if subfield_tag not in tags and len(subfield_tag) > 1:
        tags.append(subfield_tag)
    if len(tags) < 5 and "#Agriculture" not in tags:
        tags.append("#Agriculture")
    return " ".join(tags[:5])


def build_academic_cta(word, subfield, post_type):
    """Returns a grammatically natural, academic CTA tailored to subfield and post type."""
    term = format_term_inline(word)
    sf = (subfield or "").strip().lower()

    if post_type == "exam_trap":
        return (
            f"Exam & viva check: how would you concisely contrast {term} "
            f"with its closest botanical lookalike for a graduate cohort?"
        )
    if post_type == "field_protocol":
        return (
            f"For nursery managers and field researchers: what seasonal or crop-specific "
            f"adjustments matter most when applying {term}?"
        )
    if post_type == "book_excerpt":
        return (
            f"From our upcoming horticulture reference work: what part of {term} "
            f"do students find hardest to connect between textbook theory and the field?"
        )

    if any(k in sf for k in ["breeding", "seed", "biotechnology"]):
        return (
            f"For breeders and seed scientists: where do you see {term} creating the "
            f"biggest practical impact in cultivar development or seed quality?"
        )
    if any(k in sf for k in ["propagation", "pomology", "olericulture", "floriculture", "landscape", "postharvest"]):
        return (
            f"For growers, students, and researchers: what field conditions make or break "
            f"outcomes involving {term} in your crops?"
        )
    return (
        f"For plant scientists and students: how does understanding {term} "
        f"shape your approach to crop management or experimental interpretation?"
    )


def extract_bains_themes(defn, expo, example=""):
    """
    Splits the Bains-style conceptual exposition into its 3 canonical academic themes:
      1. Structural / Conceptual Basis (Paragraph 1 — skipping redundant opening restatement)
      2. Physiological / Molecular Mechanism (Paragraph 2 — merging short topic openers)
      3. Field & Agro-Ecological Context (Paragraph 3 — prioritizing concrete regional/crop sentences)
    """
    def_sents = split_sentences(defn)
    core_def = def_sents[0] if def_sents else sanitize_for_linkedin(defn)

    paras = split_paragraphs(expo)
    p1_sents = split_sentences(paras[0]) if len(paras) >= 1 else []
    p2_sents = split_sentences(paras[1]) if len(paras) >= 2 else []
    p3_sents = split_sentences(paras[2]) if len(paras) >= 3 else []

    # Avoid restating the core definition verbatim at the start of Theme 1
    if len(p1_sents) >= 2 and word_overlap_ratio(core_def, p1_sents[0]) >= 0.38:
        p1_sents = p1_sents[1:]

    # If P2 starts with a brief transitional topic sentence, pair it with the concrete mechanism
    if len(p2_sents) >= 2 and len(p2_sents[0]) < 135:
        p2_sents = [f"{p2_sents[0]} {p2_sents[1]}"] + p2_sents[2:]

    # Prioritize concrete regional/crop sentence in P3 over generic introductory framing
    if len(p3_sents) >= 2:
        concrete_markers = (
            "bangladesh", "bari", "brri", "bau", "rajshahi", "dinajpur", "jashore",
            "jessore", "gazipur", "faridpur", "sylhet", "sundarbans", "satkhira",
            "mymensingh", "munshiganj", "chapainawabganj"
        )
        if not any(m in p3_sents[0].lower() for m in concrete_markers):
            for idx, s in enumerate(p3_sents[1:], start=1):
                if any(m in s.lower() for m in concrete_markers):
                    p3_sents = p3_sents[idx:]
                    break

    if not p3_sents and example:
        p3_sents = split_sentences(example)

    return {
        "core_def": core_def,
        "p1_sents": p1_sents,
        "p2_sents": p2_sents,
        "p3_sents": p3_sents,
    }


def assemble_thematic_post(hook, core_def, sections, cta_q, hashtags, max_chars=MAX_CHAR_LIMIT):
    """
    Fits hook + core definition + 3 thematic sections + CTA + hashtags cleanly
    within max_chars while guaranteeing every non-empty theme is represented
    with complete, readable sentences.
    sections: list of (label, sentence_list)
    """
    active = [(lbl, sents) for lbl, sents in sections if sents]

    def render(selected_texts, def_text):
        parts = [hook]
        if def_text:
            parts.append(def_text)
        for lbl, txt in selected_texts:
            if txt:
                parts.append(f"{lbl}\n{txt}")
        parts.append(f"💬 Your Turn:\n{cta_q}")
        parts.append(hashtags)
        return "\n\n".join(parts).strip()

    allocations = [
        [2] * len(active),
        [1, 2, 2][:len(active)],
        [1, 1, 2][:len(active)],
        [1, 2, 1][:len(active)],
        [1] * len(active),
    ]

    for counts in allocations:
        selected = []
        for (lbl, sents), cnt in zip(active, counts):
            selected.append((lbl, " ".join(sents[:cnt]).strip()))
        candidate = render(selected, core_def)
        if len(candidate) <= max_chars:
            return candidate

    def _strip_parens(txt):
        res = re.sub(r"\s*\([^)]{10,}\)", "", txt).strip()
        return re.sub(r"\s+([,;:.])", r"\1", res)

    def_short = core_def
    fitted = [(lbl, sents[0]) for lbl, sents in active]

    # Step 1: Strip long parentheticals cleanly before touching sentence structure
    if len(render(fitted, def_short)) > max_chars:
        if len(def_short) > 180:
            def_short = _strip_parens(def_short)
        for idx in sorted(range(len(fitted)), key=lambda i: len(fitted[i][1]), reverse=True):
            if len(render(fitted, def_short)) <= max_chars:
                break
            lbl, txt = fitted[idx]
            fitted[idx] = (lbl, _strip_parens(txt))

    # Step 2: Incrementally trim only the longest section until within max_chars
    post = render(fitted, def_short)
    while len(post) > max_chars:
        overflow = len(post) - max_chars
        longest_idx = max(range(len(fitted)), key=lambda i: len(fitted[i][1]))
        lbl, txt = fitted[longest_idx]
        if len(txt) <= 80:
            if len(def_short) > 120:
                def_short = shorten_sentence_cleanly(def_short, max(110, len(def_short) - overflow))
                post = render(fitted, def_short)
                continue
            break
        target_len = max(80, len(txt) - max(overflow, 25))
        new_txt = shorten_sentence_cleanly(txt, target_len)
        if len(new_txt) >= len(txt):
            new_txt = shorten_sentence_cleanly(txt, len(txt) - 25)
        fitted[longest_idx] = (lbl, new_txt)
        post = render(fitted, def_short)

    return post


def format_term_of_the_day(word, subfield, defn, expo, example="", humanize=False):
    """
    Formats an engaging, academic LinkedIn post strictly under 1,300 characters
    preserving all 3 Bains thematic beats:
      1. Hook + Core Definition
      2. 🔬 Structural & Conceptual Basis (P1)
      3. ⚙️ Physiological Mechanism (P2)
      4. 🌾 Field & Crop Context (P3)
      5. 💬 Academic CTA + Hashtags
    """
    title = format_term_title(word)
    clean_subfield = subfield.strip() if subfield else "Plant Science"
    themes = extract_bains_themes(defn, expo, example)

    hook = f"🌱 Horticulture Concept: {title}"
    sections = [
        ("🔬 Structural & Conceptual Basis:", themes["p1_sents"]),
        ("⚙️ Physiological Mechanism:", themes["p2_sents"]),
        ("🌾 Field & Crop Context:", themes["p3_sents"]),
    ]
    cta_q = build_academic_cta(word, clean_subfield, "term_of_the_day")
    hashtags = build_hashtags(clean_subfield)

    post = assemble_thematic_post(hook, themes["core_def"], sections, cta_q, hashtags)
    if humanize:
        post, _ = humanize_with_ollama(post)
    return post


def format_field_protocol(word, subfield, defn, expo, example="", deck_card=None, humanize=False):
    """
    Formats a practitioner & student-friendly Field Protocol post maintaining
    the Bains thematic flow (Core Context -> Biological Rationale -> Field Execution).
    """
    title = format_term_title(word)
    clean_subfield = subfield.strip() if subfield else "Plant Science"
    themes = extract_bains_themes(defn, expo, example)

    practice_sents = []
    if deck_card and deck_card.get("horticultural_practice"):
        practice_sents = split_sentences(deck_card["horticultural_practice"])

    field_sents = themes["p3_sents"] or practice_sents
    rationale_sents = themes["p2_sents"] or themes["p1_sents"]
    context_sents = practice_sents if (themes["p3_sents"] and practice_sents) else themes["p1_sents"]

    hook = f"🚜 Field & Lab Protocol: {title}"
    sections = [
        ("📋 Practical Context:", context_sents),
        ("⚙️ Biological Rationale:", rationale_sents),
        ("🌾 Field Execution:", field_sents),
    ]
    cta_q = build_academic_cta(word, clean_subfield, "field_protocol")
    hashtags = build_hashtags(clean_subfield, "#FieldProtocol")

    post = assemble_thematic_post(hook, themes["core_def"], sections, cta_q, hashtags)
    if humanize:
        post, _ = humanize_with_ollama(post)
    return post


def format_exam_trap(word, subfield, defn, expo, example="", deck_card=None, humanize=False):
    """
    Formats a student & academician Concept Check / Exam Trap post preserving
    conceptual distinction, mechanism, and crop-level application.
    """
    title = format_term_title(word)
    clean_subfield = subfield.strip() if subfield else "Plant Science"
    themes = extract_bains_themes(defn, expo, example)

    trap_sents = []
    if deck_card:
        raw_trap = str(deck_card.get("exam_trap", "")).strip()
        if raw_trap and not raw_trap.startswith("Key distinction required:"):
            raw_trap = re.sub(r"^(CRITICAL EXAM TRAP|Exam Trap):\s*", "", raw_trap, flags=re.IGNORECASE)
            trap_sents = split_sentences(raw_trap)

    if not trap_sents:
        trap_sents = themes["p1_sents"]

    hook = f"🧠 HortiPrep Concept Check: {title}"
    sections = [
        ("❓ Key Distinction:", trap_sents),
        ("🔬 Biological Mechanism:", themes["p2_sents"]),
        ("🌾 Applied Crop Context:", themes["p3_sents"]),
    ]
    cta_q = build_academic_cta(word, clean_subfield, "exam_trap")
    hashtags = build_hashtags(clean_subfield, "#HortiPrep")

    post = assemble_thematic_post(hook, themes["core_def"], sections, cta_q, hashtags)
    if humanize:
        post, _ = humanize_with_ollama(post)
    return post


def format_book_excerpt(word, subfield, defn, expo, example="", humanize=False):
    """
    Formats a 'From the Horticulture Manuscript' post preserving the full
    3-beat Bains narrative arc for academic readers and students.
    """
    title = format_term_title(word)
    clean_subfield = subfield.strip() if subfield else "Plant Science"
    themes = extract_bains_themes(defn, expo, example)

    hook = f"📖 From the Horticulture Book: {title}"
    sections = [
        ("🌿 Conceptual Frame:", themes["p1_sents"]),
        ("🔬 Underlying Mechanism:", themes["p2_sents"]),
        ("🌾 Agro-Ecological Reality:", themes["p3_sents"]),
    ]
    cta_q = build_academic_cta(word, clean_subfield, "book_excerpt")
    hashtags = build_hashtags(clean_subfield, "#HorticultureBook")

    post = assemble_thematic_post(hook, themes["core_def"], sections, cta_q, hashtags)
    if humanize:
        post, _ = humanize_with_ollama(post)
    return post


def format_post_by_type(row, humanize=False, deck_map=None):
    """Dispatches row formatting based on its post_type attribute."""
    ptype = row.get("post_type", "term_of_the_day")
    word = row.get("word", "")
    subfield = row.get("subfield", "")
    defn = row.get("definition", "")
    expo = row.get("conceptual_exposition", "")
    example = row.get("example_sentence", "")

    if deck_map is None:
        deck_map = load_study_deck_map()
    deck_card = deck_map.get(word.strip().lower())

    if ptype == "field_protocol":
        return format_field_protocol(word, subfield, defn, expo, example, deck_card=deck_card, humanize=humanize)
    elif ptype == "exam_trap":
        return format_exam_trap(word, subfield, defn, expo, example, deck_card=deck_card, humanize=humanize)
    elif ptype == "book_excerpt":
        return format_book_excerpt(word, subfield, defn, expo, example, humanize=humanize)
    elif ptype == "custom":
        existing = sanitize_for_linkedin(row.get("generated_post", ""))
        if existing:
            return humanize_with_ollama(existing)[0] if humanize else humanize_text_deterministic(existing)
        return format_term_of_the_day(word, subfield, defn, expo, example, humanize=humanize)
    else:
        return format_term_of_the_day(word, subfield, defn, expo, example, humanize=humanize)


# ==============================================================================
# CSV ENGINE, VERIFICATION SYNC & RANDOMIZATION
# ==============================================================================

def load_posts_csv():
    """Reads linkedin_posts.csv and returns list of dictionaries."""
    if not os.path.exists(POST_CSV):
        return []
    posts = []
    with open(POST_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row or not any(row.values()):
                continue
            posts.append(row)
    return posts


def save_posts_csv(posts):
    """Writes list of dictionaries back to linkedin_posts.csv with normalized newlines."""
    with open(POST_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LINKEDIN_HEADERS, lineterminator="\n")
        writer.writeheader()
        for p in posts:
            row = {h: p.get(h, "") for h in LINKEDIN_HEADERS}
            writer.writerow(row)


def init_or_sync_posts_csv(force_rebuild=False, reformat_unedited=False):
    """
    Initializes linkedin_posts.csv from local_dictionary.csv or synchronizes verified entries.
    - Strictly enforces the verification gate: only 'Verified by Flash' and 'Human verified'
      (plus already-posted rows or human-authored custom posts) are kept in the queue.
    - Unverified 'Needs review' pending entries are excluded until verified.
    - Preserves posted_status, posted_date, and manual edits for existing rows.
    """
    if not os.path.exists(SRC_CSV):
        print(f"[Warning] Source dictionary not found at {SRC_CSV}")
        return load_posts_csv()

    dict_rows = []
    with open(SRC_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r and any(r.values()) and r.get("Word"):
                dict_rows.append(r)

    dict_map = {r.get("Word", "").strip().lower(): r for r in dict_rows}
    deck_map = load_study_deck_map()
    existing_posts = [] if force_rebuild else load_posts_csv()
    existing_map = {p.get("word", "").strip().lower(): p for p in existing_posts}

    synced_posts = []
    seen_words = set()
    next_id = 1

    # Retain eligible existing posts and refresh dictionary metadata
    for p in existing_posts:
        w_lower = p.get("word", "").strip().lower()
        dr = dict_map.get(w_lower)
        status = p.get("posted_status", "pending").strip().lower()

        if dr is not None:
            dict_status = dr.get("Status", "").strip()
            p["verification_status"] = dict_status
            p["infographic_recommendation"] = dr.get("Infographic Recommendation", "").strip()

            # Exclude unverified entries unless already posted
            if not is_verified_status(dict_status) and status != "posted":
                continue

            # Refresh source text for unedited pending rows if dictionary updated
            new_def = dr.get("Definition", "")
            new_expo = dr.get("Conceptual Exposition", "")
            new_ex = dr.get("Example Sentence", "")
            new_subf = dr.get("Subfield", "Plant Science")
            source_changed = (
                p.get("definition", "") != new_def
                or p.get("conceptual_exposition", "") != new_expo
                or p.get("subfield", "") != new_subf
            )
            p["definition"] = new_def
            p["conceptual_exposition"] = new_expo
            p["example_sentence"] = new_ex
            p["subfield"] = new_subf

            if status != "posted" and (
                reformat_unedited
                or (source_changed and p.get("humanized_status", "original") == "original")
                or not p.get("generated_post", "").strip()
            ):
                if p.get("humanized_status", "original") == "original":
                    post_body = format_post_by_type(p, humanize=False, deck_map=deck_map)
                    p["generated_post"] = post_body
                    p["character_count"] = str(len(post_body))
        else:
            # Custom or standalone entries authored directly in the pipeline
            if not p.get("verification_status"):
                p["verification_status"] = "Human verified"
            if not is_verified_post(p) and status != "posted":
                continue

        # Clean stale posted_date if status is not posted
        if status != "posted":
            p["posted_date"] = ""

        p["character_count"] = str(len(p.get("generated_post", "")))
        synced_posts.append(p)
        seen_words.add(w_lower)
        try:
            curr_id = int(p.get("post_id", 0))
            if curr_id >= next_id:
                next_id = curr_id + 1
        except ValueError:
            pass

    # Collect newly verified dictionary entries not yet in linkedin_posts.csv
    new_verified_rows = []
    for dr in dict_rows:
        w = dr.get("Word", "").strip()
        w_lower = w.lower()
        dict_status = dr.get("Status", "").strip()
        if w_lower in seen_words or not is_verified_status(dict_status):
            continue
        new_verified_rows.append(dr)

    # Randomize newly added verified terms so the queue never defaults to A-Z order
    random.shuffle(new_verified_rows)

    for dr in new_verified_rows:
        w = dr.get("Word", "").strip()
        w_lower = w.lower()
        defn = dr.get("Definition", "")
        expo = dr.get("Conceptual Exposition", "")
        ex = dr.get("Example Sentence", "")
        subf = dr.get("Subfield", "Plant Science")
        dict_status = dr.get("Status", "").strip()
        info_rec = dr.get("Infographic Recommendation", "").strip()

        new_post = {
            "post_id": str(next_id),
            "word": w,
            "subfield": subf,
            "verification_status": dict_status,
            "post_type": "term_of_the_day",
            "definition": defn,
            "conceptual_exposition": expo,
            "example_sentence": ex,
            "infographic_recommendation": info_rec,
            "posted_status": "pending",
            "posted_date": "",
            "humanized_status": "original",
        }
        post_body = format_post_by_type(new_post, humanize=False, deck_map=deck_map)
        new_post["generated_post"] = post_body
        new_post["character_count"] = str(len(post_body))

        synced_posts.append(new_post)
        seen_words.add(w_lower)
        next_id += 1

    # Re-sequence IDs cleanly if rebuilding from scratch
    if force_rebuild:
        for idx, p in enumerate(synced_posts, start=1):
            p["post_id"] = str(idx)

    save_posts_csv(synced_posts)
    return synced_posts


def shuffle_pending_queue():
    """Randomizes the order of pending verified posts in linkedin_posts.csv."""
    posts = load_posts_csv()
    posted_or_skipped = [p for p in posts if p.get("posted_status", "").strip().lower() != "pending"]
    pending = [p for p in posts if p.get("posted_status", "").strip().lower() == "pending"]
    random.shuffle(pending)
    combined = posted_or_skipped + pending
    save_posts_csv(combined)
    return combined


# ==============================================================================
# PIPELINE GENERATION LOGIC (RANDOMIZED & VERIFIED)
# ==============================================================================

def _get_last_posted_subfield(posts):
    """Finds the subfield of the most recently posted item to promote topical variety."""
    posted = [p for p in posts if p.get("posted_status", "").strip().lower() == "posted"]
    if not posted:
        return None
    posted.sort(key=lambda p: (p.get("posted_date", ""), int(p.get("post_id", 0) or 0)))
    return posted[-1].get("subfield", "").strip().lower()


def get_next_pending_post(posts=None):
    """
    Randomly selects an eligible pending post (strictly Verified by Flash or Human verified),
    preferring a different subfield from the most recent post when alternatives exist.
    """
    if posts is None:
        posts = load_posts_csv()
        if not posts:
            posts = init_or_sync_posts_csv()

    eligible = [
        p for p in posts
        if p.get("posted_status", "").strip().lower() == "pending" and is_verified_post(p)
    ]
    if not eligible:
        return None

    last_subf = _get_last_posted_subfield(posts)
    if last_subf:
        diverse = [p for p in eligible if p.get("subfield", "").strip().lower() != last_subf]
        if diverse:
            return random.choice(diverse)

    return random.choice(eligible)


def generate_and_preview_next(auto_humanize=False, mark_as_posted=False, post_type_override=None, target_query=None):
    """
    Selects a randomized verified pending row (or specific requested verified term),
    preserves manual drafts unless regenerating, writes preview.txt, and prints preview.
    """
    posts = load_posts_csv()
    if not posts:
        posts = init_or_sync_posts_csv()

    target_post = None
    if target_query:
        q = str(target_query).strip().lower()
        for p in posts:
            if p.get("post_id", "").strip().lower() == q or p.get("word", "").strip().lower() == q:
                target_post = p
                break
        if target_post is None:
            print(f"\n[Error] No verified entry matching '{target_query}' found in queue.\n")
            return None
        if not is_verified_post(target_post):
            print(f"\n[Blocked] '{target_post.get('word')}' is '{target_post.get('verification_status')}', not Verified by Flash or Human verified.\n")
            return None
    else:
        target_post = get_next_pending_post(posts)

    if target_post is None:
        print("\n🎉 No eligible verified pending posts remaining in the queue!")
        print("Verify more entries in local_dictionary.csv and run --sync, or add one with --add-post.\n")
        return None

    target_idx = posts.index(target_post)
    word = target_post.get("word", "")
    title = format_term_title(word)

    if post_type_override and post_type_override in POST_TYPES:
        target_post["post_type"] = post_type_override

    print(f"\n============================================================")
    print(f"  📝 Randomized Verified Post: \"{title}\" (ID #{target_post.get('post_id')})")
    print(f"  ✅ Verification: {target_post.get('verification_status')} | Subfield: {target_post.get('subfield')}")
    print(f"============================================================")

    is_manual_draft = target_post.get("humanized_status") == "manual_edit" and target_post.get("generated_post", "").strip()
    if auto_humanize:
        print(f"Polishing thematic LinkedIn post via Ollama ({DEFAULT_MODEL})...")
        base_text = target_post.get("generated_post", "").strip() if is_manual_draft else format_post_by_type(target_post, humanize=False)
        post_text, engine = humanize_with_ollama(base_text)
        target_post["humanized_status"] = engine
    elif is_manual_draft and not post_type_override:
        post_text = target_post["generated_post"]
    else:
        post_text = format_post_by_type(target_post, humanize=False)

    target_post["generated_post"] = post_text
    char_count = len(post_text)
    target_post["character_count"] = str(char_count)

    info_rec = target_post.get("infographic_recommendation", "").strip()
    info_block = f"\nVISUAL / CAROUSEL IDEA:\n{info_rec}\n" if info_rec else ""

    preview_content = f"""============================================================
LINKEDIN POST PREVIEW: {title}
Post ID: #{target_post.get('post_id')} | Subfield: {target_post.get('subfield')} | Type: {target_post.get('post_type')}
Verification: {target_post.get('verification_status')} | Style Status: {target_post.get('humanized_status')}
Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Character Count: {char_count} / {MAX_CHAR_LIMIT} chars (Optimal engagement)
============================================================

{post_text}
{info_block}
============================================================
INSTRUCTIONS TO PUBLISH:
1. Copy the text block above.
2. Paste directly into your LinkedIn post composer.
3. Review line breaks on mobile view.
4. Mark as posted: python3 post_generator.py --mark-posted {target_post.get('post_id')}
============================================================
"""
    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(preview_content)

    if mark_as_posted:
        target_post["posted_status"] = "posted"
        target_post["posted_date"] = date.today().strftime("%Y-%m-%d")
        print(f"✓ Marked post #{target_post.get('post_id')} as POSTED on {target_post['posted_date']}.")

    posts[target_idx] = target_post
    save_posts_csv(posts)

    print("\n" + preview_content)
    print(f"✓ Post preview saved to: {PREVIEW_FILE}")
    print(f"✓ Character Count: {char_count} / {MAX_CHAR_LIMIT} characters ({'✅ Under Limit' if char_count <= MAX_CHAR_LIMIT else '⚠️ Over Limit'})\n")

    return target_post


def mark_post_status(post_id_or_word, new_status="posted"):
    """Updates the status of a specific post by ID or word, enforcing verification when posting."""
    posts = load_posts_csv()
    target = str(post_id_or_word).strip().lower()
    updated = False

    for p in posts:
        if p.get("post_id", "").strip().lower() == target or p.get("word", "").strip().lower() == target:
            if new_status == "posted" and not is_verified_post(p):
                print(f"[Blocked] Post #{p.get('post_id')} ('{p.get('word')}') is '{p.get('verification_status')}' and cannot be marked posted.")
                return False
            p["posted_status"] = new_status
            if new_status == "posted":
                p["posted_date"] = date.today().strftime("%Y-%m-%d")
            else:
                p["posted_date"] = ""
            updated = True
            print(f"✓ Post #{p.get('post_id')} ('{p.get('word')}') marked as '{new_status}'.")
            break

    if updated:
        save_posts_csv(posts)
    else:
        print(f"[Error] Post matching '{post_id_or_word}' was not found in {POST_CSV}.")
    return updated


def add_post_cli(args):
    """
    CLI handler for --add-post.
    Supports both interactive prompts and direct flags (--title, --type, --subfield, --def, --body, --humanize, --mark-posted).
    """
    def _get_flag(flag_names):
        for i, tok in enumerate(args):
            if tok in flag_names and i + 1 < len(args) and not args[i + 1].startswith("--"):
                return args[i + 1]
        return None

    title_arg = _get_flag(["--title", "--word", "-t"])
    ptype_arg = _get_flag(["--type"])
    subfield_arg = _get_flag(["--subfield", "-s"])
    def_arg = _get_flag(["--def", "--definition"])
    body_arg = _get_flag(["--body", "--expo", "--text"])
    auto_humanize = "--humanize" in args
    mark_posted = "--mark-posted" in args

    posts = load_posts_csv()
    next_id = 1
    for p in posts:
        try:
            cid = int(p.get("post_id", 0))
            if cid >= next_id:
                next_id = cid + 1
        except ValueError:
            pass

    if not title_arg and not body_arg:
        print("\n============================================================")
        print("  ➕ Add New LinkedIn Post (Marked: Human verified)")
        print("============================================================")
        print("Post Types:")
        type_keys = list(POST_TYPES.keys())
        for idx, k in enumerate(type_keys, 1):
            print(f"  {idx}. {k:<16} ({POST_TYPES[k]})")

        raw_type = input("\nSelect post type [1-5 or name, default=book_excerpt]: ").strip()
        if raw_type.isdigit() and 1 <= int(raw_type) <= len(type_keys):
            ptype_arg = type_keys[int(raw_type) - 1]
        elif raw_type in POST_TYPES:
            ptype_arg = raw_type
        else:
            ptype_arg = "book_excerpt"

        title_arg = input("Term / Subject Title: ").strip()
        if not title_arg:
            print("Cancelled: title is required.")
            return None

        subfield_arg = input("Subfield (default: Horticulture): ").strip() or "Horticulture"

        if ptype_arg == "custom":
            print("Paste/type your custom LinkedIn post text (enter a single '.' on a new line to finish):")
            lines = []
            while True:
                line = input()
                if line.strip() == ".":
                    break
                lines.append(line)
            body_arg = "\n".join(lines).strip()
            def_arg = ""
        else:
            def_arg = input("Core Definition / Takeaway (1 sentence): ").strip()
            print("Enter 1-3 thematic paragraphs (Structural Basis / Mechanism / Field Context).")
            print("Type '.' on its own line when finished:")
            lines = []
            while True:
                line = input()
                if line.strip() == ".":
                    break
                lines.append(line)
            body_arg = "\n".join(lines).strip()

        if not auto_humanize:
            ans = input("Polish with local Ollama humanizer? [y/N]: ").strip().lower()
            auto_humanize = ans in ("y", "yes")
    else:
        ptype_arg = ptype_arg if ptype_arg in POST_TYPES else ("custom" if body_arg and not def_arg else "book_excerpt")
        subfield_arg = subfield_arg or "Horticulture"
        title_arg = title_arg or "Horticulture Insight"

    new_row = {
        "post_id": str(next_id),
        "word": title_arg,
        "subfield": subfield_arg,
        "verification_status": "Human verified",
        "post_type": ptype_arg,
        "definition": def_arg or "",
        "conceptual_exposition": "" if ptype_arg == "custom" else (body_arg or ""),
        "example_sentence": "",
        "infographic_recommendation": "",
        "generated_post": (body_arg or "") if ptype_arg == "custom" else "",
        "posted_status": "posted" if mark_posted else "pending",
        "posted_date": date.today().strftime("%Y-%m-%d") if mark_posted else "",
        "humanized_status": "original",
    }

    formatted = format_post_by_type(new_row, humanize=False)
    if auto_humanize:
        formatted, engine = humanize_with_ollama(formatted)
        new_row["humanized_status"] = engine

    new_row["generated_post"] = formatted
    new_row["character_count"] = str(len(formatted))

    posts.append(new_row)
    save_posts_csv(posts)

    preview_content = f"""============================================================
LINKEDIN POST PREVIEW: {format_term_title(title_arg)}
Post ID: #{new_row['post_id']} | Subfield: {subfield_arg} | Type: {ptype_arg}
Verification: Human verified | Character Count: {len(formatted)} / {MAX_CHAR_LIMIT} chars
============================================================

{formatted}
"""
    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(preview_content)

    print("\n" + preview_content)
    print(f"✓ Saved post #{new_row['post_id']} to {POST_CSV} and previewed in {PREVIEW_FILE}.\n")
    return new_row


# ==============================================================================
# EMBEDDED LOCALHOST VISIBILITY DASHBOARD
# Zero external network dependencies, pure Python standard library.
# ==============================================================================

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LinkedIn Post Pipeline & Book Workspace</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg: #f8fafc;
      --surface: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --primary: #0a66c2;
      --primary-hover: #084e96;
      --primary-light: #e0f2fe;
      --green: #15803d;
      --green-light: #dcfce7;
      --yellow: #b45309;
      --yellow-light: #fef3c7;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
    }

    header {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 16px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      position: sticky;
      top: 0;
      z-index: 50;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon {
      font-size: 26px; width: 44px; height: 44px;
      background: #e0f2fe; border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
    }
    .brand-title { font-size: 18px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
    .brand-sub { font-size: 12px; color: var(--text-muted); }

    .stats-bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

    .stat-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 6px 12px; border-radius: 9999px;
      font-size: 12px; font-weight: 600;
    }
    .badge-pending { background: var(--yellow-light); color: var(--yellow); border: 1px solid #fde68a; }
    .badge-posted { background: var(--green-light); color: var(--green); border: 1px solid #bbf7d0; }
    .badge-total { background: #f1f5f9; color: #475569; border: 1px solid var(--border); }

    .btn {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 8px 14px; border-radius: 7px; font-size: 13px;
      font-weight: 600; cursor: pointer; border: none;
      transition: all 0.15s ease; text-decoration: none;
    }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-green { background: #16a34a; color: #fff; }
    .btn-green:hover { background: #15803d; }
    .btn-outline { background: var(--surface); border: 1px solid var(--border); color: #334155; }
    .btn-outline:hover { background: #f8fafc; border-color: #cbd5e1; }
    .btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 5px; }

    .control-bar {
      padding: 16px 28px;
      display: flex; justify-content: space-between;
      gap: 16px; flex-wrap: wrap; align-items: center;
    }

    .filters-group { display: flex; gap: 10px; align-items: center; flex: 1; flex-wrap: wrap; }
    .search-input {
      padding: 8px 14px; border: 1px solid var(--border);
      border-radius: 6px; font-size: 13px; width: 260px;
      outline: none; background: var(--surface);
    }
    .search-input:focus { border-color: var(--primary); }
    .select-filter {
      padding: 8px 12px; border: 1px solid var(--border);
      border-radius: 6px; font-size: 13px; background: var(--surface); outline: none;
    }

    .table-container {
      margin: 0 28px; background: var(--surface);
      border: 1px solid var(--border); border-radius: 8px;
      overflow-x: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }

    th {
      background: #f8fafc; padding: 12px 14px; font-weight: 600; color: #475569;
      font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
      border-bottom: 1px solid var(--border); white-space: nowrap;
    }

    td {
      padding: 12px 14px; border-bottom: 1px solid var(--border);
      vertical-align: middle; color: #1e293b;
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #fafafa; }

    .cell-id { font-family: var(--mono); color: #94a3b8; width: 45px; }
    .cell-term { font-weight: 700; color: #0f172a; white-space: nowrap; font-size: 14px; }
    .cell-subfield { color: #0284c7; font-weight: 500; font-size: 12px; }

    .verify-badge {
      display: inline-block; padding: 3px 8px; border-radius: 9999px;
      font-size: 11px; font-weight: 600; white-space: nowrap;
    }
    .verify-human { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .verify-flash { background: #e0f2fe; color: #075985; border: 1px solid #bae6fd; }
    .verify-other { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

    .type-select {
      padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;
      border: 1px solid var(--border); background: #f8fafc; color: #1e293b; cursor: pointer;
    }

    .status-select {
      padding: 4px 8px; border-radius: 9999px; font-size: 12px; font-weight: 600;
      border: 1px solid transparent; outline: none; cursor: pointer;
    }
    .status-pending { background: var(--yellow-light); color: var(--yellow); border-color: #fde68a; }
    .status-posted { background: var(--green-light); color: var(--green); border-color: #bbf7d0; }
    .status-skipped { background: #f1f5f9; color: #64748b; border-color: var(--border); }

    .char-badge {
      font-family: var(--mono); font-size: 11px; padding: 3px 7px;
      border-radius: 4px; font-weight: 600; white-space: nowrap;
    }
    .char-good { background: #dcfce7; color: #15803d; }
    .char-warn { background: #fef3c7; color: #b45309; }
    .char-over { background: #fee2e2; color: #b91c1c; }

    .actions-cell { display: flex; gap: 6px; align-items: center; white-space: nowrap; }

    .modal-overlay {
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.6); display: none;
      align-items: center; justify-content: center; z-index: 100;
      backdrop-filter: blur(2px);
    }
    .modal-card {
      background: var(--surface); border-radius: 12px; max-width: 720px; width: 92%;
      max-height: 90vh; display: flex; flex-direction: column;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); overflow: hidden;
    }
    .modal-header {
      padding: 16px 24px; border-bottom: 1px solid var(--border);
      display: flex; justify-content: space-between; align-items: center; background: #fafafa;
    }
    .modal-title { font-size: 16px; font-weight: 700; color: #0f172a; }
    .modal-body { padding: 20px 24px; overflow-y: auto; flex: 1; }
    .modal-footer {
      padding: 14px 24px; border-top: 1px solid var(--border);
      display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; background: #fafafa;
    }

    .modal-toolbar {
      display: flex; justify-content: space-between; align-items: center;
      gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
    }

    .linkedin-feed-card {
      border: 1px solid var(--border); border-radius: 8px; background: #fff;
      padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-size: 14px; line-height: 1.55;
    }
    .linkedin-user { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
    .linkedin-avatar {
      width: 42px; height: 42px; border-radius: 50%; background: #0a66c2; color: white;
      display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px;
    }
    .linkedin-meta { font-size: 13px; }
    .linkedin-name { font-weight: 700; color: #0f172a; }
    .linkedin-headline { font-size: 11px; color: var(--text-muted); }
    .linkedin-post-text {
      width: 100%; white-space: pre-wrap; font-family: inherit; color: #1e293b;
      margin-bottom: 10px; background: #fdfdfd; padding: 12px; border: 1px solid #e2e8f0;
      border-radius: 6px; outline: none; font-size: 13.5px; line-height: 1.55; resize: vertical;
    }
    .linkedin-post-text:focus { border-color: var(--primary); background: #fff; }

    .infographic-box {
      margin-top: 14px; padding: 12px 14px; border-radius: 8px;
      background: #f0f9ff; border: 1px solid #bae6fd; font-size: 12.5px; color: #0c4a6e;
    }
    .infographic-title { font-weight: 700; margin-bottom: 4px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; }

    .gauge-bar-wrapper { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
    .gauge-track { height: 6px; background: #e2e8f0; border-radius: 9999px; overflow: hidden; }
    .gauge-fill { height: 100%; background: var(--green); transition: width 0.2s; }
    .gauge-label {
      font-size: 12px; display: flex; justify-content: space-between;
      color: var(--text-muted); font-family: var(--mono);
    }

    .form-group { margin-bottom: 14px; }
    .form-label { display: block; font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 5px; }
    .form-input, .form-textarea, .form-select {
      width: 100%; padding: 8px 12px; border: 1px solid var(--border);
      border-radius: 6px; font-size: 13px; outline: none; background: #fff;
    }
    .form-textarea { resize: vertical; min-height: 90px; }
    .form-input:focus, .form-textarea:focus { border-color: var(--primary); }

    .toast {
      position: fixed; bottom: 24px; right: 24px; background: #0f172a; color: #fff;
      padding: 10px 18px; border-radius: 6px; font-size: 13px; font-weight: 500;
      opacity: 0; transform: translateY(10px); transition: all 0.2s; z-index: 200;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .toast.show { opacity: 1; transform: translateY(0); }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">🌱</div>
      <div>
        <div class="brand-title">Horticulture Book & LinkedIn Post Hub</div>
        <div class="brand-sub">Verified Entries Only • Randomized Thematic Pipeline</div>
      </div>
    </div>
    <div class="stats-bar">
      <span class="stat-badge badge-pending" id="badge-pending">0 Pending Verified</span>
      <span class="stat-badge badge-posted" id="badge-posted">0 Posted</span>
      <span class="stat-badge badge-total" id="badge-total">0 Total</span>
      <button class="btn btn-primary" onclick="generateNextPost()">⚡ Random Next Post</button>
      <button class="btn btn-outline" onclick="shuffleQueue()">🎲 Shuffle Queue</button>
      <button class="btn btn-outline" onclick="openNewPostModal()">➕ Add Post</button>
      <button class="btn btn-outline" onclick="syncWithDict()">🔄 Sync Verified</button>
      <a class="btn btn-outline" href="/api/export" download>📥 Export CSV</a>
    </div>
  </header>

  <div class="control-bar">
    <div class="filters-group">
      <input type="text" id="search-box" class="search-input" placeholder="Search terms, concepts, subfields..." oninput="renderTable()">
      <select id="status-filter" class="select-filter" onchange="renderTable()">
        <option value="">All Statuses</option>
        <option value="pending">Pending Only</option>
        <option value="posted">Posted Only</option>
        <option value="skipped">Skipped Only</option>
      </select>
      <select id="verify-filter" class="select-filter" onchange="renderTable()">
        <option value="">All Verified Sources</option>
        <option value="Verified by Flash">Verified by Flash</option>
        <option value="Human verified">Human Verified</option>
      </select>
      <select id="type-filter" class="select-filter" onchange="renderTable()">
        <option value="">All Post Types</option>
        <option value="term_of_the_day">🌱 Concept Breakdown</option>
        <option value="book_excerpt">📖 From the Book</option>
        <option value="field_protocol">🚜 Field Protocol</option>
        <option value="exam_trap">🧠 Concept Check / Trap</option>
        <option value="custom">✨ Custom Post</option>
      </select>
    </div>
    <div style="font-size: 13px; color: var(--text-muted);">
      3-Theme Bains Flow • Limit <strong style="color: #0f172a;">1,300 chars</strong>
    </div>
  </div>

  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Term / Title</th>
          <th>Subfield</th>
          <th>Verification</th>
          <th>Post Type</th>
          <th>Length</th>
          <th>Status</th>
          <th>Style</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="posts-tbody"></tbody>
    </table>
  </div>

  <!-- PREVIEW & EDIT MODAL -->
  <div id="preview-modal" class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title" id="modal-post-title">LinkedIn Post Preview</div>
        <button class="btn btn-outline btn-sm" onclick="closeModal('preview-modal')">✕</button>
      </div>
      <div class="modal-body">
        <div class="modal-toolbar">
          <div style="display:flex; gap:8px; align-items:center;">
            <span id="modal-verify-badge" class="verify-badge verify-flash">Verified</span>
            <select id="modal-type-select" class="type-select" onchange="reformatModalType()">
              <option value="term_of_the_day">🌱 Concept Breakdown</option>
              <option value="book_excerpt">📖 From the Book</option>
              <option value="field_protocol">🚜 Field Protocol</option>
              <option value="exam_trap">🧠 Concept Check / Trap</option>
              <option value="custom">✨ Custom</option>
            </select>
          </div>
          <button class="btn btn-outline btn-sm" onclick="reformatModalType()">🔄 Re-render Template</button>
        </div>

        <div class="linkedin-feed-card">
          <div class="linkedin-user">
            <div class="linkedin-avatar">🌱</div>
            <div class="linkedin-meta">
              <div class="linkedin-name">Author / Researcher • Horticulture Reference</div>
              <div class="linkedin-headline">Plant Science • Graduate Studies in Horticulture • Bangladesh</div>
            </div>
          </div>
          <textarea id="modal-post-editor" class="linkedin-post-text" rows="15" oninput="updateModalCharCount()"></textarea>
          <div class="gauge-bar-wrapper">
            <div class="gauge-label">
              <span id="modal-gauge-count">0 / 1,300 chars</span>
              <span id="modal-gauge-status">Optimal</span>
            </div>
            <div class="gauge-track">
              <div id="modal-gauge-fill" class="gauge-fill" style="width: 0%;"></div>
            </div>
          </div>
        </div>

        <div id="modal-infographic-box" class="infographic-box" style="display:none;">
          <div class="infographic-title">📊 Companion Figure / Carousel Blueprint</div>
          <div id="modal-infographic-text"></div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" id="btn-modal-humanize" onclick="humanizeCurrentModalPost()">✍️ Humanize (Ollama)</button>
        <button class="btn btn-green" onclick="copyModalPost()">📋 Copy</button>
        <button class="btn btn-outline" onclick="saveModalDraft()">💾 Save Draft</button>
        <button class="btn btn-primary" onclick="saveModalPostEdits()">✅ Save & Mark Posted</button>
      </div>
    </div>
  </div>

  <!-- NEW CUSTOM POST MODAL -->
  <div id="new-post-modal" class="modal-overlay">
    <div class="modal-card" style="max-width: 580px;">
      <div class="modal-header">
        <div class="modal-title">Add Post (Human Verified)</div>
        <button class="btn btn-outline btn-sm" onclick="closeModal('new-post-modal')">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Post Type</label>
          <select id="new-post-type" class="form-select">
            <option value="book_excerpt">📖 From the Horticulture Book</option>
            <option value="term_of_the_day">🌱 Horticulture Concept Breakdown</option>
            <option value="field_protocol">🚜 Field & Lab Protocol</option>
            <option value="exam_trap">🧠 HortiPrep Concept Check</option>
            <option value="custom">✨ Custom Freeform Post</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Term / Subject Title</label>
          <input type="text" id="new-post-word" class="form-input" placeholder="e.g. Micro-Grafting or Monsoon Pruning">
        </div>
        <div class="form-group">
          <label class="form-label">Subfield</label>
          <input type="text" id="new-post-subfield" class="form-input" placeholder="e.g. Pomology or Plant Breeding">
        </div>
        <div class="form-group">
          <label class="form-label">Core Definition / Takeaway</label>
          <textarea id="new-post-def" class="form-textarea" placeholder="Core scientific definition or opening takeaway..."></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Thematic Paragraphs (Structural Basis / Mechanism / Field Context)</label>
          <textarea id="new-post-expo" class="form-textarea" placeholder="Separate the 3 thematic paragraphs with blank lines (or paste full text for Custom Freeform)..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeModal('new-post-modal')">Cancel</button>
        <button class="btn btn-primary" onclick="submitNewCustomPost()">Add to Verified Queue</button>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">Action completed</div>

  <script>
    let posts = [];
    let activeModalIdx = null;

    function isVerifiedStatus(status) {
      const s = String(status || '').trim().toLowerCase();
      return s === 'verified by flash' || s === 'human verified' || s === 'verified';
    }

    function verifyBadgeInfo(status) {
      const s = String(status || '').trim();
      const low = s.toLowerCase();
      if (low === 'human verified') return { cls: 'verify-human', label: '🧑 Human verified' };
      if (low === 'verified by flash' || low === 'verified') return { cls: 'verify-flash', label: '⚡ Verified by Flash' };
      return { cls: 'verify-other', label: s || 'Needs review' };
    }

    async function loadPosts() {
      try {
        const res = await fetch('/api/posts');
        posts = await res.json();
        renderTable();
        updateStats();
      } catch (e) {
        showToast('Error loading posts from server');
      }
    }

    function updateStats() {
      const pending = posts.filter(p => p.posted_status === 'pending' && isVerifiedStatus(p.verification_status)).length;
      const posted = posts.filter(p => p.posted_status === 'posted').length;
      document.getElementById('badge-pending').textContent = `${pending} Pending Verified`;
      document.getElementById('badge-posted').textContent = `${posted} Posted`;
      document.getElementById('badge-total').textContent = `${posts.length} Total`;
    }

    function renderTable() {
      const tbody = document.getElementById('posts-tbody');
      tbody.innerHTML = '';

      const query = document.getElementById('search-box').value.toLowerCase().trim();
      const statusFilter = document.getElementById('status-filter').value;
      const verifyFilter = document.getElementById('verify-filter').value;
      const typeFilter = document.getElementById('type-filter').value;

      posts.forEach((p, idx) => {
        if (statusFilter && p.posted_status !== statusFilter) return;
        if (verifyFilter && p.verification_status !== verifyFilter) return;
        if (typeFilter && p.post_type !== typeFilter) return;
        if (query) {
          const match = [p.word, p.subfield, p.definition, p.generated_post]
            .some(v => String(v || '').toLowerCase().includes(query));
          if (!match) return;
        }

        const tr = document.createElement('tr');
        const charCount = parseInt(p.character_count || (p.generated_post ? p.generated_post.length : 0) || 0, 10);

        let charClass = 'char-good';
        if (charCount > 1300) charClass = 'char-over';
        else if (charCount > 1180) charClass = 'char-warn';

        const vb = verifyBadgeInfo(p.verification_status);
        const safeStatus = ['pending', 'posted', 'skipped'].includes(p.posted_status) ? p.posted_status : 'pending';
        const pt = p.post_type || 'term_of_the_day';

        tr.innerHTML = `
          <td class="cell-id">#${escapeHtml(p.post_id)}</td>
          <td class="cell-term">${escapeHtml(p.word || '')}</td>
          <td class="cell-subfield">${escapeHtml(p.subfield || 'Horticulture')}</td>
          <td><span class="verify-badge ${vb.cls}">${escapeHtml(vb.label)}</span></td>
          <td>
            <select class="type-select" onchange="changeRowType(${idx}, this.value)">
              <option value="term_of_the_day" ${pt === 'term_of_the_day' ? 'selected' : ''}>🌱 Concept</option>
              <option value="book_excerpt" ${pt === 'book_excerpt' ? 'selected' : ''}>📖 Book Note</option>
              <option value="field_protocol" ${pt === 'field_protocol' ? 'selected' : ''}>🚜 Protocol</option>
              <option value="exam_trap" ${pt === 'exam_trap' ? 'selected' : ''}>🧠 Exam Trap</option>
              <option value="custom" ${pt === 'custom' ? 'selected' : ''}>✨ Custom</option>
            </select>
          </td>
          <td><span class="char-badge ${charClass}">${charCount} chars</span></td>
          <td>
            <select class="status-select status-${safeStatus}" onchange="updateRowStatus(${idx}, this.value)">
              <option value="pending" ${safeStatus === 'pending' ? 'selected' : ''}>Pending</option>
              <option value="posted" ${safeStatus === 'posted' ? 'selected' : ''}>Posted</option>
              <option value="skipped" ${safeStatus === 'skipped' ? 'selected' : ''}>Skipped</option>
            </select>
          </td>
          <td>
            <span style="font-size: 11px; color: #64748b; font-family: var(--mono);">${escapeHtml(p.humanized_status || 'original')}</span>
          </td>
          <td>
            <div class="actions-cell">
              <button class="btn btn-outline btn-sm" onclick="openPreviewModal(${idx})">👁️ Preview</button>
              <button class="btn btn-outline btn-sm" onclick="humanizePostRow(${idx})" title="Polish with Ollama">✍️ Humanize</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function changeRowType(idx, newType) {
      try {
        const res = await fetch('/api/post/reformat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ post_id: posts[idx].post_id, post_type: newType })
        });
        const updated = await res.json();
        if (updated && updated.post_id) {
          posts[idx] = updated;
          renderTable();
          showToast(`Reformatted "${updated.word}" as ${newType}`);
        }
      } catch (e) {
        showToast('Error updating post type');
      }
    }

    async function updateRowStatus(idx, newStatus) {
      if (newStatus === 'posted' && !isVerifiedStatus(posts[idx].verification_status)) {
        showToast('Only Verified by Flash or Human verified posts can be posted');
        renderTable();
        return;
      }
      posts[idx].posted_status = newStatus;
      posts[idx].posted_date = (newStatus === 'posted') ? new Date().toISOString().split('T')[0] : '';
      await savePostToServer(posts[idx]);
      updateStats();
      renderTable();
      showToast(`Status updated to ${newStatus}`);
    }

    function openPreviewModal(idx) {
      activeModalIdx = idx;
      const p = posts[idx];
      document.getElementById('modal-post-title').textContent = `LinkedIn Post Preview: ${p.word || 'Entry'}`;
      document.getElementById('modal-post-editor').value = p.generated_post || '';
      document.getElementById('modal-type-select').value = p.post_type || 'term_of_the_day';

      const vb = verifyBadgeInfo(p.verification_status);
      const badgeEl = document.getElementById('modal-verify-badge');
      badgeEl.className = `verify-badge ${vb.cls}`;
      badgeEl.textContent = vb.label;

      const infoBox = document.getElementById('modal-infographic-box');
      if (p.infographic_recommendation && p.infographic_recommendation.trim()) {
        document.getElementById('modal-infographic-text').textContent = p.infographic_recommendation.trim();
        infoBox.style.display = 'block';
      } else {
        infoBox.style.display = 'none';
      }

      updateModalCharCount();
      document.getElementById('preview-modal').style.display = 'flex';
    }

    async function reformatModalType() {
      if (activeModalIdx === null) return;
      const newType = document.getElementById('modal-type-select').value;
      try {
        const res = await fetch('/api/post/reformat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ post_id: posts[activeModalIdx].post_id, post_type: newType })
        });
        const updated = await res.json();
        if (updated && updated.post_id) {
          posts[activeModalIdx] = updated;
          document.getElementById('modal-post-editor').value = updated.generated_post;
          updateModalCharCount();
          renderTable();
          showToast(`Re-rendered template (${newType})`);
        }
      } catch (e) {
        showToast('Error re-rendering template');
      }
    }

    function updateModalCharCount() {
      const text = document.getElementById('modal-post-editor').value;
      const len = text.length;
      const countEl = document.getElementById('modal-gauge-count');
      const statusEl = document.getElementById('modal-gauge-status');
      const fillEl = document.getElementById('modal-gauge-fill');

      countEl.textContent = `${len} / 1,300 chars`;
      const pct = Math.min(100, Math.round((len / 1300) * 100));
      fillEl.style.width = `${pct}%`;

      if (len <= 1180) {
        fillEl.style.background = '#15803d';
        statusEl.textContent = 'Optimal Length';
        statusEl.style.color = '#15803d';
      } else if (len <= 1300) {
        fillEl.style.background = '#b45309';
        statusEl.textContent = 'Near Limit';
        statusEl.style.color = '#b45309';
      } else {
        fillEl.style.background = '#b91c1c';
        statusEl.textContent = 'Exceeds 1,300 Chars!';
        statusEl.style.color = '#b91c1c';
      }
    }

    async function humanizeCurrentModalPost() {
      if (activeModalIdx === null) return;
      const btn = document.getElementById('btn-modal-humanize');
      btn.disabled = true;
      btn.textContent = '⏳ Humanizing...';
      try {
        const res = await fetch('/api/post/humanize', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ post_id: posts[activeModalIdx].post_id })
        });
        const updated = await res.json();
        posts[activeModalIdx] = updated;
        document.getElementById('modal-post-editor').value = updated.generated_post;
        updateModalCharCount();
        renderTable();
        showToast(`Polished (${updated.humanized_status})`);
      } catch (e) {
        showToast('Error querying local Ollama engine');
      } finally {
        btn.disabled = false;
        btn.textContent = '✍️ Humanize (Ollama)';
      }
    }

    async function humanizePostRow(idx) {
      showToast('Polishing via local Ollama...');
      try {
        const res = await fetch('/api/post/humanize', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ post_id: posts[idx].post_id })
        });
        const updated = await res.json();
        posts[idx] = updated;
        renderTable();
        showToast(`✓ Polished: ${updated.word} (${updated.humanized_status})`);
      } catch (e) {
        showToast('Error during humanization');
      }
    }

    async function saveModalDraft() {
      if (activeModalIdx === null) return;
      const edited = document.getElementById('modal-post-editor').value.trim();
      posts[activeModalIdx].generated_post = edited;
      posts[activeModalIdx].character_count = String(edited.length);
      posts[activeModalIdx].humanized_status = 'manual_edit';

      await savePostToServer(posts[activeModalIdx]);
      renderTable();
      updateStats();
      showToast('💾 Draft saved (status unchanged)');
    }

    async function saveModalPostEdits() {
      if (activeModalIdx === null) return;
      if (!isVerifiedStatus(posts[activeModalIdx].verification_status)) {
        showToast('Blocked: unverified entry cannot be marked posted');
        return;
      }
      const edited = document.getElementById('modal-post-editor').value.trim();
      posts[activeModalIdx].generated_post = edited;
      posts[activeModalIdx].character_count = String(edited.length);
      posts[activeModalIdx].posted_status = 'posted';
      posts[activeModalIdx].posted_date = new Date().toISOString().split('T')[0];

      await savePostToServer(posts[activeModalIdx]);
      closeModal('preview-modal');
      renderTable();
      updateStats();
      showToast('✅ Saved & marked as POSTED!');
    }

    function copyModalPost() {
      const text = document.getElementById('modal-post-editor').value;
      navigator.clipboard.writeText(text).then(() => {
        showToast('📋 Copied formatted LinkedIn post to clipboard!');
      }).catch(() => {
        showToast('Failed to copy to clipboard');
      });
    }

    async function generateNextPost() {
      try {
        const res = await fetch('/api/post/next', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
          await loadPosts();
          const targetIdx = posts.findIndex(p => p.post_id === data.post.post_id);
          if (targetIdx !== -1) openPreviewModal(targetIdx);
          showToast(`🎲 Picked random verified post: ${data.post.word}`);
        } else {
          showToast(data.message || 'No eligible verified pending posts left!');
        }
      } catch (e) {
        showToast('Error generating next post');
      }
    }

    async function shuffleQueue() {
      try {
        const res = await fetch('/api/post/shuffle', { method: 'POST' });
        const data = await res.json();
        await loadPosts();
        showToast(`🎲 Shuffled ${data.pending} pending verified posts`);
      } catch (e) {
        showToast('Error shuffling queue');
      }
    }

    async function syncWithDict() {
      showToast('Syncing verified entries from local_dictionary.csv...');
      try {
        const res = await fetch('/api/sync', { method: 'POST' });
        const data = await res.json();
        await loadPosts();
        showToast(`✓ Synced ${data.total} verified posts`);
      } catch (e) {
        showToast('Error syncing dictionary');
      }
    }

    function openNewPostModal() {
      document.getElementById('new-post-modal').style.display = 'flex';
    }

    async function submitNewCustomPost() {
      const post_type = document.getElementById('new-post-type').value;
      const word = document.getElementById('new-post-word').value.trim();
      const subfield = document.getElementById('new-post-subfield').value.trim();
      const defn = document.getElementById('new-post-def').value.trim();
      const expo = document.getElementById('new-post-expo').value.trim();

      if (!word) {
        showToast('Please enter a term or title');
        return;
      }

      try {
        await fetch('/api/post/add', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ post_type, word, subfield, definition: defn, conceptual_exposition: expo })
        });
        closeModal('new-post-modal');
        document.getElementById('new-post-word').value = '';
        document.getElementById('new-post-subfield').value = '';
        document.getElementById('new-post-def').value = '';
        document.getElementById('new-post-expo').value = '';
        await loadPosts();
        showToast(`Added Human verified post "${word}"!`);
      } catch (e) {
        showToast('Error saving new post');
      }
    }

    function closeModal(id) {
      document.getElementById(id).style.display = 'none';
      activeModalIdx = null;
    }

    async function savePostToServer(post) {
      try {
        const res = await fetch('/api/post/update', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(post)
        });
        if (!res.ok) {
          const err = await res.json();
          showToast(err.error || 'Error saving post');
        }
      } catch (e) {
        showToast('Network error saving post');
      }
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2800);
    }

    function escapeHtml(s) {
      return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    loadPosts();
  </script>
</body>
</html>"""


# ==============================================================================
# HTTP HANDLER FOR LOCALHOST DASHBOARD
# ==============================================================================

class PostDashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet HTTP logs

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))

        elif path == "/api/posts":
            posts = load_posts_csv()
            if not posts:
                posts = init_or_sync_posts_csv()
            self._send_json(200, posts)

        elif path == "/api/export":
            if os.path.exists(POST_CSV):
                with open(POST_CSV, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="linkedin_posts.csv"')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "CSV not found")
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body) if body else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        if path == "/api/post/update":
            post_id = str(payload.get("post_id", "")).strip()
            posts = load_posts_csv()
            for p in posts:
                if p.get("post_id") == post_id:
                    new_status = str(payload.get("posted_status", p.get("posted_status", "pending"))).strip().lower()
                    if new_status == "posted" and not is_verified_post(p):
                        self._send_json(400, {"error": "Unverified entries cannot be marked posted"})
                        return
                    for k, v in payload.items():
                        if k in LINKEDIN_HEADERS:
                            p[k] = v
                    if new_status != "posted":
                        p["posted_date"] = ""
                    p["character_count"] = str(len(p.get("generated_post", "")))
                    break
            save_posts_csv(posts)
            self._send_json(200, {"status": "ok"})

        elif path == "/api/post/reformat":
            post_id = str(payload.get("post_id", "")).strip()
            new_type = str(payload.get("post_type", "term_of_the_day")).strip()
            posts = load_posts_csv()
            target_post = None
            for p in posts:
                if p.get("post_id") == post_id:
                    if new_type in POST_TYPES:
                        p["post_type"] = new_type
                    p["generated_post"] = format_post_by_type(p, humanize=False)
                    p["character_count"] = str(len(p["generated_post"]))
                    p["humanized_status"] = "original"
                    target_post = p
                    break
            save_posts_csv(posts)
            self._send_json(200, target_post or {})

        elif path == "/api/post/next":
            res = generate_and_preview_next(auto_humanize=False, mark_as_posted=False)
            if res:
                self._send_json(200, {"status": "ok", "post": res})
            else:
                self._send_json(200, {"status": "exhausted", "message": "No eligible verified pending posts left!"})

        elif path == "/api/post/shuffle":
            shuffled = shuffle_pending_queue()
            pending = sum(1 for p in shuffled if p.get("posted_status", "").strip().lower() == "pending")
            self._send_json(200, {"status": "ok", "pending": pending})

        elif path == "/api/post/humanize":
            post_id = str(payload.get("post_id", "")).strip()
            posts = load_posts_csv()
            target_post = None
            for p in posts:
                if p.get("post_id") == post_id:
                    target_post = p
                    break

            if target_post:
                # Non-destructive: polish formatted LinkedIn post while keeping dictionary exposition intact
                base_post = (
                    target_post.get("generated_post", "").strip()
                    if target_post.get("humanized_status") == "manual_edit"
                    else format_post_by_type(target_post, humanize=False)
                )
                polished, engine = humanize_with_ollama(base_post)
                target_post["generated_post"] = polished
                target_post["character_count"] = str(len(polished))
                target_post["humanized_status"] = engine
                save_posts_csv(posts)

            self._send_json(200, target_post or {})

        elif path == "/api/post/add":
            posts = load_posts_csv()
            next_id = 1
            for p in posts:
                try:
                    cid = int(p.get("post_id", 0))
                    if cid >= next_id:
                        next_id = cid + 1
                except ValueError:
                    pass

            w = payload.get("word", "").strip()
            subf = payload.get("subfield", "Plant Science").strip() or "Plant Science"
            ptype = payload.get("post_type", "custom")
            if ptype not in POST_TYPES:
                ptype = "custom"
            defn = payload.get("definition", "").strip()
            expo = payload.get("conceptual_exposition", "").strip()

            new_row = {
                "post_id": str(next_id),
                "word": w,
                "subfield": subf,
                "verification_status": "Human verified",
                "post_type": ptype,
                "definition": defn,
                "conceptual_exposition": "" if ptype == "custom" else expo,
                "example_sentence": "",
                "infographic_recommendation": "",
                "generated_post": expo if ptype == "custom" else "",
                "posted_status": "pending",
                "posted_date": "",
                "humanized_status": "original",
            }
            new_row["generated_post"] = format_post_by_type(new_row, humanize=False)
            new_row["character_count"] = str(len(new_row["generated_post"]))

            posts.append(new_row)
            save_posts_csv(posts)
            self._send_json(200, {"status": "ok", "post": new_row})

        elif path == "/api/sync":
            synced = init_or_sync_posts_csv()
            self._send_json(200, {"status": "ok", "total": len(synced)})
        else:
            self.send_error(404)


def find_available_port(start_port=8082, max_tries=10):
    """Finds available TCP port starting from 8082."""
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", p)) != 0:
                return p
    return start_port


def start_server(port=8082):
    """Starts the embedded local host dashboard on localhost."""
    actual_port = find_available_port(port)
    server = HTTPServer(("localhost", actual_port), PostDashboardHandler)
    url = f"http://localhost:{actual_port}"

    print(f"\n============================================================")
    print(f"  🌱 LinkedIn Post & Book Compilation Dashboard")
    print(f"============================================================")
    print(f"✓ Connected to CSV:  {POST_CSV}")
    print(f"✓ Server running at: {url}")
    print(f"============================================================")
    print(f"Opening dashboard in your web browser...")
    print(f"Press Ctrl + C in this Terminal window to stop the server.\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped. All updates saved.")
    finally:
        server.server_close()


# ==============================================================================
# CLI COMMAND ROUTER
# ==============================================================================

def print_help():
    print("""
Horticulture LinkedIn Post Generator & Tracking Engine
Usage:
  python3 post_generator.py                     # Pick a random verified pending post -> preview.txt
  python3 post_generator.py --next              # Same as default; accepts --humanize, --type <TYPE>, --mark-posted
  python3 post_generator.py --add-post          # Interactive wizard (or flags --title, --type, --subfield, --def, --body)
  python3 post_generator.py --shuffle           # Randomize pending verified post order in CSV
  python3 post_generator.py --mark-posted <ID>  # Mark a verified post as 'posted' by ID or Term
  python3 post_generator.py --mark-pending <ID> # Reset a post back to 'pending' and clear posted_date
  python3 post_generator.py --humanize <ID>     # Polish formatted post via Ollama without altering dictionary text
  python3 post_generator.py --sync              # Sync verified entries ('Verified by Flash' / 'Human verified')
  python3 post_generator.py --rebuild           # Cleanly rebuild & randomize queue from verified dictionary entries
  python3 post_generator.py --serve             # Start localhost visibility dashboard (port 8082)
  python3 post_generator.py <term_or_id>        # Preview a specific verified term (supports --type, --humanize)
  python3 post_generator.py --help              # Show this help guide
""")


def _extract_flag_value(args, flag_names):
    for i, tok in enumerate(args):
        if tok in flag_names and i + 1 < len(args) and not args[i + 1].startswith("--"):
            return args[i + 1]
    return None


def main():
    args = sys.argv[1:]

    if args and args[0] in ["--help", "-h", "help"]:
        print_help()
        return

    # Always synchronize verified pool unless doing a full explicit --rebuild
    if "--rebuild" not in args:
        init_or_sync_posts_csv()

    if not args or args[0] in ["--next", "next"]:
        auto_humanize = "--humanize" in args
        mark_posted = "--mark-posted" in args
        ptype = _extract_flag_value(args, ["--type"])
        generate_and_preview_next(auto_humanize=auto_humanize, mark_as_posted=mark_posted, post_type_override=ptype)

    elif args[0] in ["--add-post", "add-post", "--add", "add"]:
        add_post_cli(args[1:])

    elif args[0] in ["--serve", "serve", "web", "--web"]:
        start_server(port=8082)

    elif args[0] in ["--shuffle", "shuffle"]:
        posts = shuffle_pending_queue()
        pending = sum(1 for p in posts if p.get("posted_status") == "pending" and is_verified_post(p))
        print(f"🎲 Shuffled {pending} verified pending posts in {POST_CSV}.")

    elif args[0] in ["--rebuild", "rebuild"]:
        posts = init_or_sync_posts_csv(force_rebuild=True, reformat_unedited=True)
        pending = sum(1 for p in posts if p.get("posted_status") == "pending" and is_verified_post(p))
        print(f"✓ Rebuilt randomized verified queue: {len(posts)} total ({pending} pending verified).")

    elif args[0] in ["--sync", "sync"]:
        reformat = "--reformat" in args
        posts = init_or_sync_posts_csv(reformat_unedited=reformat)
        pending = sum(1 for p in posts if p.get("posted_status") == "pending" and is_verified_post(p))
        print(f"✓ Synchronized {len(posts)} verified posts ({pending} pending verified).")

    elif args[0] in ["--mark-posted", "mark-posted", "--post"]:
        if len(args) > 1 and not args[1].startswith("--"):
            mark_post_status(args[1], "posted")
        else:
            print("Specify a post ID or term to mark as posted. e.g. python3 post_generator.py --mark-posted 1")

    elif args[0] in ["--mark-pending", "mark-pending"]:
        if len(args) > 1 and not args[1].startswith("--"):
            mark_post_status(args[1], "pending")
        else:
            print("Specify a post ID or term to reset to pending.")

    elif args[0] in ["--humanize", "humanize"]:
        if len(args) > 1 and not args[1].startswith("--"):
            target = args[1]
            posts = load_posts_csv()
            found = False
            for p in posts:
                if p.get("post_id") == target or p.get("word", "").lower() == target.lower():
                    if not is_verified_post(p):
                        print(f"[Blocked] '{p.get('word')}' is '{p.get('verification_status')}' and ineligible.")
                        return
                    print(f"Polishing '{p.get('word')}' with Ollama...")
                    base_post = (
                        p.get("generated_post", "").strip()
                        if p.get("humanized_status") == "manual_edit"
                        else format_post_by_type(p, humanize=False)
                    )
                    polished, engine = humanize_with_ollama(base_post)
                    p["generated_post"] = polished
                    p["character_count"] = str(len(polished))
                    p["humanized_status"] = engine
                    found = True
                    save_posts_csv(posts)
                    print(f"✓ Updated post #{p.get('post_id')} ({engine}). Length: {p['character_count']} chars.")
                    break
            if not found:
                print(f"Post '{target}' not found.")
        else:
            print("Specify a post ID or term to humanize. e.g. python3 post_generator.py --humanize 1")

    else:
        ptype = _extract_flag_value(args, ["--type"])
        auto_humanize = "--humanize" in args
        mark_posted = "--mark-posted" in args
        term_tokens = []
        skip_next = False
        for tok in args:
            if skip_next:
                skip_next = False
                continue
            if tok == "--type":
                skip_next = True
                continue
            if tok.startswith("--"):
                continue
            term_tokens.append(tok)
        term_target = " ".join(term_tokens).strip()
        if term_target:
            generate_and_preview_next(
                auto_humanize=auto_humanize,
                mark_as_posted=mark_posted,
                post_type_override=ptype,
                target_query=term_target,
            )
        else:
            print(f"Unknown command: {' '.join(args)}")
            print_help()


if __name__ == "__main__":
    main()
