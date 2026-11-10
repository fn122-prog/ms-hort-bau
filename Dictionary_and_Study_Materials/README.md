# 🌱 HortiPrep & Lexicon: M.S. Horticultural Dictionary & Exam Review System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Zero--Dependency-brightgreen.svg)]()
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success.svg)]()
[![Hardware](https://img.shields.io/badge/Hardware-Apple%20Silicon%20M4%20Accelerated-orange.svg)]()
[![AI Engine](https://img.shields.io/badge/Local%20LLM-Qwen%202.5%2014B-purple.svg)](https://ollama.com/library/qwen2.5)
[![Academic Program](https://img.shields.io/badge/Program-M.S.%20in%20Horticulture-darkgreen.svg)]()

A specialized, publication-grade lexical and active-recall exam review system designed for Master of Science (M.S.) candidates in Horticulture. The platform bridges rigorous botanical lexicography with high-yield graduate exam preparation, powered by offline local language models (`qwen2.5:14b`) and automated linguistic validation pipelines.

---

## 🏛️ Academic Scope & Course Syllabus Alignment

Engineered specifically around the graduate curriculum of the **Department of Horticulture, Bangladesh Agricultural University (BAU), Mymensingh** (Winter Semester):

| Course Code | Course Name | Focus Areas | Key Verified Concepts |
| :--- | :--- | :--- | :--- |
| **`Hort. 501`** | **Advanced Fruit Production** | Pomology, Propagation, Orchard Architecture | *Air Layering, Grafting, T-Budding (Shield Budding)* |
| **`Hort. 502`** | **Methods in Advanced Research** | Field Instrumentation, Laboratory Protocols | *Biometrical sampling, trial layouts* |
| **`Hort. 503`** | **Advanced Vegetable Production** | Olericulture, Protected Cultivation, Bolting | *True Seed (TPS), Biennial bolting control* |
| **`Hort. 505`** | **Advanced Research Methodology** | Experimental Design, Statistical Biometry | *RCBD, Factorial split-plot ANOVA* |
| **`Hort. 507`** | **Ornamental & Landscape Hort.** | Floriculture, Turfgrass, Landscape Design | *Marcottage, Clonal nursery propagation* |
| **`Hort. 519`** | **Horticultural Seed Physiology** | Dormancy, Chilling, Seed Viability | *Vernalization, Orthodox Seed, Recalcitrant Seed, Apomixis* |
| **`Hort. 521`** | **Horticultural Plant Biotechnology** | In-Vitro Culture, Breeding, Cryopreservation | *Germplasm Conservation, Nucellar Embryony* |

---

## 🚀 Key Features

### 1. Master Lexicographical Dashboard (`app.py` &bull; `http://localhost:8080`)
* **Standard 11-Column Layout**: Word, Pronunciation (IPA), Part of Speech, Subfield, Definition, Example Sentence, Etymology, Synonyms, Cross-References, Date Added, and Verification Status.
* **Inline Sheet Editing**: Real-time two-way synchronization with `local_dictionary.csv`.
* **Zero Dependencies**: Built entirely using Python standard libraries (`http.server`, `urllib`, `csv`, `json`). No `pip install` or heavyweight frameworks required.

### 2. HortiPrep Graduate Exam Review (`study_app.py` &bull; `http://localhost:8081`)
* **Dynamic Course Filtering**: Instant zero-lag in-memory switching between all 7 courses.
* **High-Yield Exam Dimensions**:
  * **Biological Mechanism**: Deep physiological, anatomical, and genetic foundations (e.g. *histone methylation of FLC, LEA protein synthesis, cambial callus bridging*).
  * **Horticultural Practice / Protocol**: Exact field, nursery, or lab protocols (e.g. *IBA hormone concentrations, bark slipping prerequisites, cryopreservation of embryonic axes*).
  * **Professor's Exam Trap & Distractor**: Highlighted warning alerts outlining subtleties professors test on graduate exams (*Vernalization vs. Stratification; Apomixis vs. Parthenocarpy; Bark Slipping vs. Chip Budding*).
  * **Target Crops**: Botanical species and families (*Litchi chinensis, Mangifera indica, Solanum tuberosum*).
* **Two Interactive Modes**:
  * 📋 **Course Cheat Sheet Table**: Sort, search, and 1-click export to CSV or print-ready PDF cheat sheets.
  * 🧠 **Active Recall Flashcard Drill**: Spaced repetition testing with instant keyboard shortcuts (<kbd>Space</kbd> to flip, <kbd>1</kbd>/<kbd>2</kbd>/<kbd>3</kbd> to grade, <kbd>←</kbd>/<kbd>→</kbd> to navigate).

### 3. Offline AI Synthesis & Automated Safeguards (`qwen2.5:14b`)
* Runs 100% locally on Apple Silicon Metal GPU acceleration via [Ollama](https://ollama.com).
* **Automated 3-Tier Safeguards**:
  * **Curated Offline Phonetics**: Built-in phonetic tables and linguistic compounding algorithms that eliminate phonetic hallucinations and double-stress glitches (`/ˈˈ.../`).
  * **In-Context Botanical Constraints**: Enforces Roberts (1973) seed viability rules, autogamous plant breeding principles, and eliminates subtype synecdoche.
  * **Self-Correcting Post-Processor**: Validates every generated card in Python before writing to disk.

---

## 💻 Portability & Multi-Device Usage

> [!NOTE]
> **Can this project be used on other computers without an AI model?**  
> **YES!** All study, review, search, filtering, flashcard drills, and cheat sheet printing work **100% offline on ANY computer with Python installed** (Windows, macOS, or Linux). You do **NOT** need Ollama or a GPU to review your terms.  
> The AI model (`qwen2.5:14b`) is only invoked when you choose to auto-generate *brand-new* cards.

---

## 🛠️ Quickstart

### Prerequisites
* Python 3.9+ (pre-installed on macOS/Linux)
* *(Optional, for AI generation)* [Ollama](https://ollama.com) running `qwen2.5:14b`:
  ```bash
  ollama pull qwen2.5:14b
  ```

### Installation & Launch

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/horticulture-lexicon-prep.git
   cd horticulture-lexicon-prep
   ```

2. **Launch the HortiPrep Exam Review Dashboard**:
   ```bash
   python3 study_app.py
   ```
   *Opens `http://localhost:8081` in your default browser.*

3. **Launch the Master Dictionary Dashboard**:
   ```bash
   python3 app.py
   ```
   *Opens `http://localhost:8080` in your default browser.*

4. **CLI Batch Generator**:
   ```bash
   python3 fill_dictionary_ollama.py
   ```

---

## 📂 Project Structure

```text
├── app.py                      # Standalone Dictionary Web Dashboard (Port 8080)
├── study_app.py                # HortiPrep Course Review & Flashcard Drill (Port 8081)
├── fill_dictionary_ollama.py   # Offline CLI batch generator with Qwen 2.5 14B
├── local_dictionary.csv        # Master CSV dataset (11 publication-grade columns)
├── course_study_deck.json      # Structured JSON database mapped by semester course
├── HorticultureDictionary_v3.gs # Google Apps Script backup with 1-request batching
├── .gitignore                  # Git ignore rules (caches, temp files, OS artifacts)
├── LICENSE                     # MIT License
└── README.md                   # Project documentation & portfolio summary
```

---

## 🎓 Author & Attribution

**FNFahim**  
*B.Sc. in Agriculture (Honours)*  
*M.Sc. in Horticulture Candidate*  
Department of Horticulture, Bangladesh Agricultural University (BAU), Mymensingh.  

*Designed and developed as an open-source, offline-first tool for graduate agricultural researchers and plant science students.*
