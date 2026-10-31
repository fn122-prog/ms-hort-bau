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
    "seed": "siːd",
    "seeds": "siːdz",
    "layering": "leɪ.ər.ɪŋ",
    "budding": "bʌd.ɪŋ",
    "grafting": "ɡræf.tɪŋ",
    "cutting": "kʌt.ɪŋ",
    "cuttings": "kʌt.ɪŋz",
    "propagation": "ˌprɒp.əˈɡeɪ.ʃən",
    "culture": "kʌl.tʃər",
    "fruit": "fruːt",
    "plant": "plɑːnt",
    "tree": "triː",
    "root": "ruːt",
    "stock": "stɒk",
    "scion": "saɪ.ən",
    "orthodox": "ɔːr.θə.dɒks",
    "recalcitrant": "rɪˈkæl.sɪ.trənt",
    "true": "truː",
    "air": "ɛər",
    "apomixis": "ˌæp.əˈmɪk.sɪs",
    "vernalization": "ˌvɜːr.nə.laɪˈzeɪ.ʃən",
    "germplasm": "dʒɜːrmˌplæz.əm"
}

def clean_ipa_syntax(ipa_str):
    """Normalize and clean IPA transcription."""
    if not ipa_str:
        return ""
    t = ipa_str.strip()
    if not t.startswith("/"):
        t = "/" + t
    if not t.endswith("/"):
        t = t + "/"
    t = t.replace("ˈˈ", "ˈ").replace("ˌˌ", "ˌ").replace("ˈˌ", "ˈ").replace("ˌˈ", "ˈ")
    while "  " in t:
        t = t.replace("  ", " ")
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
        f"3. No Sub-mechanism Generalization: Do NOT define broad phenomena by only one subtype (e.g. apomixis is asexual seed formation / agamospermy—do NOT define it solely as nucellar embryony; true seed is a fertilized ovule, contrasting with vegetative propagules—never claim it requires 'two parents' since self-pollinated crops also produce true seed).\n"
        f"4. Physiological Rigor: Adhere strictly to authoritative seed physiology (Roberts 1973, Bewley & Black). Recalcitrant seeds die because they lack LEA proteins/vitrification and remain metabolically active (do NOT claim high lipids); orthodox seeds tolerate desiccation to 2-5% obeying Roberts equations.\n"
        f"5. Part of Speech: Horticultural processes/techniques ('grafting', 'air layering', 'vernalization') are nouns (n.).\n"
        f"6. Etymology: State genuine Greek/Latin/historical roots with coining scholar/date where known.\n"
        f"7. Synonyms: Provide ONLY true technical botanical synonyms (e.g. 'agamospermy' for apomixis; 'desiccation-tolerant seed' for orthodox seed; 'marcottage' for air layering). Subtypes (e.g. apospory) are NOT synonyms. If no true synonym exists, leave empty.\n"
        f"8. IPA: Provide exact, standard phonetic transcription covering EVERY word in the term.\n\n"
        f"Return ONLY a valid JSON object (no markdown, no backticks, no introductory text) with these keys:\n"
        f"- \"ipa\": Standard IPA pronunciation enclosed in slashes (e.g. \"/ˈsaɪ.ən/\")\n"
        f"- \"pos\": Abbreviated part of speech (\"n.\", \"v.\", \"adj.\")\n"
        f"- \"subfield\": One of: {', '.join(SUBFIELDS)}\n"
        f"- \"definition\": Rigorous 1-2 sentence academic definition in the botanical/horticultural sense.\n"
        f"- \"example\": Realistic sentence demonstrating practical horticultural use (orchard, greenhouse, lab, field trial).\n"
        f"- \"etymology\": True morphological derivation or naming origin.\n"
        f"- \"synonyms\": Comma-separated list of genuine technical/trade synonyms.\n"
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
    """Processes a list of words and returns formatted rows without Source column."""
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

        # Check human-curated linguistic dictionary for guaranteed IPA, fallback to model IPA
        verified_ipa = fetch_verified_ipa(clean_word)
        final_ipa = verified_ipa if verified_ipa else (entry.get("ipa", "") if entry else "")

        if entry and entry.get("definition"):
            row = [
                clean_word,
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
            print(f"   ✓ Success! [{entry.get('subfield', 'Botany')}] {entry.get('definition', '')[:70]}...")
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
