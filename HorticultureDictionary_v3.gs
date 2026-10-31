/**
 * Horticulture Dictionary Builder v3 (Google Apps Script)
 *
 * Designed for MS in Horticulture graduate terminology reference.
 *
 * Key changes in v3:
 * - Removed interactive Audio links to ensure the entire sheet is cleanly printable.
 * - Retained IPA Pronunciation and all existing core sections.
 * - Added 100% Free Gemini API integration (Google AI Studio, no credit card required).
 * - Automatic generation of:
 *     - Rigorous academic horticultural definition
 *     - Real-world horticultural example sentences (nursery, field, orchard, lab)
 *     - Botanical etymology (Greek/Latin roots)
 *     - Standardized IPA pronunciation & Part of Speech
 *     - Horticultural Subfield classification
 *     - Technical Synonyms & "See Also" cross-references
 * - Built-in rate limiting (4s delay) to stay safely within Google AI Studio's 15 RPM free tier.
 * - Seamless fallback to Free Dictionary API & Wikipedia if Gemini key is not set.
 * - Auto-migration in setupSheet: safely detects and removes obsolete Audio column from v1/v2.
 */

const CONFIG = {
  SHEET_NAME: 'Dictionary',
  USE_AI: true,                  // Uses free Gemini API when key is set; falls back to Free Dict/Wikipedia if empty
  AI_MODEL: 'gemini-3.8-flash',  // Current model required by Google AI Studio
  MAX_PER_RUN: 20,               // Keeps each run well under Apps Script's 6-minute execution limit
  MAX_DEF_SENTENCES: 2,
  MAX_DEF_CHARS: 320
};

// 11 Purely Printable Columns (Audio and Source removed)
const HEADERS = [
  'Word',
  'Pronunciation (IPA)',
  'Part of Speech',
  'Subfield',
  'Definition',
  'Example Sentence',
  'Etymology',
  'Synonyms',
  'See Also',
  'Date Added',
  'Status'
];

const COL = {
  WORD: 0,
  IPA: 1,
  POS: 2,
  SUBFIELD: 3,
  DEF: 4,
  EX: 5,
  ETY: 6,
  SYN: 7,
  SEE: 8,
  DATE: 9,
  STATUS: 10
};

const STATUS_LIST = ['Needs review', 'Check sense', 'Verified', 'Not found', 'Duplicate'];

// Regex pattern suggesting a plant/horticulture context (used for fallback matching)
const HORT_PATTERN = new RegExp(
  '\\b(horticult|botan|plant|garden|crop|soil|seed|tree|shrub|fruit|flower|vegetable|' +
  'graft|prun|propagat|cultivat|agricultur|orchard|nursery|greenhouse|turf|lawn|leaf|' +
  'leaves|root|shoot|stem|buds?\\b|bloom|ornamental|harvest|pollinat|fertiliz|irrigat|weed|pest)',
  'i'
);

const POS_ABBR = {
  noun: 'n.',
  verb: 'v.',
  adjective: 'adj.',
  adverb: 'adv.',
  preposition: 'prep.',
  conjunction: 'conj.',
  interjection: 'interj.',
  pronoun: 'pron.'
};

const SUBFIELD_KEYWORDS = {
  'Plant Propagation': ['graft', 'scion', 'rootstock', 'cutting', 'propagat', 'layering', 'budding', 'seedling', 'tissue culture', 'rooting'],
  'Plant Physiology': ['photosynth', 'transpir', 'dormancy', 'vernaliz', 'photoperiod', 'hormone', 'auxin', 'gibberell', 'stomata', 'respiration', 'etiolat'],
  'Soil Science': ['soil', 'fertiliz', 'nutrient', 'compost', 'mulch', 'loam', 'clay', 'substrate', 'rhizosphere', 'cation'],
  'Plant Pathology': ['disease', 'pathogen', 'fungus', 'fungal', 'bacteri', 'virus', 'blight', 'wilt', 'mildew', 'canker', 'inoculat'],
  'Pest Management': ['pest', 'insect', 'mite', 'aphid', 'pesticide', 'larva', 'weed', 'herbicide', 'nematode', 'ipm'],
  'Pomology': ['fruit', 'orchard', 'apple', 'citrus', 'mango', 'berry', 'drupe', 'pome', 'stone fruit'],
  'Olericulture': ['vegetable', 'tomato', 'cucurbit', 'brassica', 'leafy', 'cole crop'],
  'Floriculture': ['flower', 'ornamental', 'bloom', 'bulb', 'cut flower', 'bedding plant'],
  'Landscape Horticulture': ['landscape', 'lawn', 'turf', 'shrub', 'arboriculture'],
  'Postharvest': ['postharvest', 'ripening', 'storage', 'ethylene', 'shelf life', 'chilling injury', 'senescence'],
  'Plant Breeding': ['breeding', 'hybrid', 'cultivar', 'genotype', 'crossing', 'pollination', 'allele', 'heterosis'],
  'Botany': ['angiosperm', 'gymnosperm', 'xylem', 'phloem', 'vascular', 'meristem', 'stoma']
};

/* ==========================================================================
   MENU & USER INTERFACE
   ========================================================================== */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Dictionary')
    .addItem('Set up / refresh sheet', 'setupSheet')
    .addItem('Fill new words', 'processNewWords')
    .addItem('Re-run selected rows', 'reprocessSelected')
    .addSeparator()
    .addItem('Sort A-Z', 'sortSheet')
    .addItem('Lowercase selected words', 'lowercaseSelected')
    .addItem('Delete rows marked Duplicate', 'deleteDuplicateRows')
    .addSeparator()
    .addItem('Set Gemini API key (Free)', 'setApiKey')
    .addItem('Test Gemini connection', 'testGeminiConnection')
    .addItem('Schedule weekly auto-run (Sun 8 AM)', 'createWeeklyTrigger')
    .addItem('Schedule daily auto-run (Nightly 11 PM)', 'createDailyTrigger')
    .addToUi();
}

/* ==========================================================================
   SETUP & MIGRATION
   ========================================================================== */

function setupSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
  } else {
    // Migration: If upgrading, detect and remove obsolete "Audio" and "Source" columns
    const lastCol = sheet.getLastColumn();
    if (lastCol > 0) {
      const currentHeaders = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
      for (let c = currentHeaders.length - 1; c >= 0; c--) {
        const h = String(currentHeaders[c]).trim().toLowerCase();
        if (h === 'audio' || h === 'source') {
          sheet.deleteColumn(c + 1);
        }
      }
    }
  }

  // Set standard headers
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS])
    .setFontWeight('bold').setBackground('#d9ead3');
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(1);

  // Status dropdown validation
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(STATUS_LIST, true)
    .setAllowInvalid(true).build();
  sheet.getRange(2, COL.STATUS + 1, 1000, 1).setDataValidation(rule);

  formatSheet_(sheet);
  SpreadsheetApp.getUi().alert('Dictionary sheet configured with 11 printable columns and color-coded status.\nType terms in Column A and run "Dictionary > Fill new words".');
}

function formatSheet_(sheet) {
  const maxRows = sheet.getMaxRows();
  const n = Math.max(maxRows - 1, 1);

  sheet.getRange(1, 1, maxRows, HEADERS.length).setVerticalAlignment('top');
  sheet.getRange(2, 1, n, HEADERS.length).setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP);

  // Enable text wrap for reading & printing multi-sentence sections
  [COL.DEF, COL.EX, COL.ETY, COL.SYN, COL.SEE].forEach(c => {
    sheet.getRange(2, c + 1, n, 1).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
  });

  sheet.getRange(2, COL.DATE + 1, n, 1).setNumberFormat('yyyy-mm-dd');

  // Printable-friendly column widths (Total 11 columns, Source removed)
  const widths = [
    140, // Word
    130, // IPA
    80,  // Part of Speech
    150, // Subfield
    380, // Definition
    320, // Example Sentence
    220, // Etymology
    160, // Synonyms
    180, // See Also
    95,  // Date Added
    110  // Status
  ];
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));

  applyConditionalFormatting_(sheet);

  const last = sheet.getLastRow();
  if (last >= 2) sheet.autoResizeRows(2, last - 1);
}

/**
 * Color-codes the Status column:
 * - Verified: Light Green (#d9ead3)
 * - Needs review: Light Yellow (#fff2cc)
 * - Not found: Light Red (#f4cccc)
 * - Duplicate: Light Gray (#efefef)
 */
function applyConditionalFormatting_(sheet) {
  const maxRows = sheet.getMaxRows();
  const n = Math.max(maxRows - 1, 1);
  const statusRange = sheet.getRange(2, COL.STATUS + 1, n, 1);

  const rules = [
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Verified')
      .setBackground('#d9ead3')
      .setFontColor('#274e13')
      .setRanges([statusRange])
      .build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Needs review')
      .setBackground('#fff2cc')
      .setFontColor('#7f6000')
      .setRanges([statusRange])
      .build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Not found')
      .setBackground('#f4cccc')
      .setFontColor('#783f04')
      .setRanges([statusRange])
      .build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('Duplicate')
      .setBackground('#efefef')
      .setFontColor('#595959')
      .setRanges([statusRange])
      .build()
  ];
  sheet.setConditionalFormatRules(rules);
}

function setApiKey() {
  const ui = SpreadsheetApp.getUi();
  const resp = ui.prompt(
    'Gemini API Key (100% Free)',
    'Paste your Google AI Studio API key (starts with AIza...):\n' +
    'Get your key free at https://aistudio.google.com/ (no credit card needed).',
    ui.ButtonSet.OK_CANCEL
  );

  if (resp.getSelectedButton() === ui.Button.OK) {
    const raw = resp.getResponseText();
    const key = String(raw || '').trim().replace(/["']/g, '');
    if (key) {
      PropertiesService.getScriptProperties().setProperty('GEMINI_API_KEY', key);
      const testNow = ui.alert(
        'Key Saved!',
        'Your free Gemini API key was saved.\n\nWould you like to run a quick connection test now?',
        ui.ButtonSet.YES_NO
      );
      if (testNow === ui.Button.YES) {
        testGeminiConnection();
      }
    }
  }
}

/**
 * Diagnostic tool: Tests Gemini API connection and displays exact status
 */
function testGeminiConnection() {
  const ui = SpreadsheetApp.getUi();
  const rawKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const key = String(rawKey || '').trim().replace(/["']/g, '');

  if (!key) {
    ui.alert(
      'API Key Missing',
      'No Gemini API key was found in Script Properties.\n\nPlease click:\nDictionary > Set Gemini API key (Free)\nand paste your key.',
      ui.ButtonSet.OK
    );
    return;
  }

  const maskedKey = key.substring(0, 7) + '...' + key.substring(Math.max(key.length - 4, 0));
  const candidateModels = [CONFIG.AI_MODEL, 'gemini-3.8-flash', 'gemini-3.8-flash-lite', 'gemini-2.5-flash'];
  const tried = unique_(candidateModels);

  let success = false;
  let errorDetails = [];

  for (let i = 0; i < tried.length; i++) {
    const model = tried[i];
    const url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
      encodeURIComponent(model) + ':generateContent?key=' + encodeURIComponent(key);

    const payload = {
      contents: [{ parts: [{ text: 'Respond with ONLY valid JSON: {"test":"ok"}' }] }],
      generationConfig: { temperature: 0.1, responseMimeType: 'application/json' }
    };

    try {
      const res = UrlFetchApp.fetch(url, {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      const code = res.getResponseCode();
      if (code === 200) {
        success = true;
        ui.alert(
          'Gemini Connected Successfully!',
          'Key: ' + maskedKey + '\n' +
          'Working Model: ' + model + '\n\n' +
          'Gemini is functioning properly! You can now select rows and click:\n' +
          'Dictionary > Re-run selected rows',
          ui.ButtonSet.OK
        );
        break;
      } else {
        errorDetails.push('Model [' + model + '] returned HTTP ' + code + ':\n' + res.getContentText().substring(0, 180));
      }
    } catch (e) {
      errorDetails.push('Model [' + model + '] error: ' + e.message);
    }
  }

  if (!success) {
    ui.alert(
      'Gemini Connection Failed',
      'Tested Key: ' + maskedKey + '\n\n' +
      errorDetails.join('\n\n') + '\n\n' +
      'Check if your key from Google AI Studio is active and has no trailing spaces.',
      ui.ButtonSet.OK
    );
  }
}

function createWeeklyTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'processNewWords') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('processNewWords')
    .timeBased().onWeekDay(ScriptApp.WeekDay.SUNDAY).atHour(8).create();
  SpreadsheetApp.getUi().alert('Scheduled: runs every Sunday around 8:00 AM.');
}

function createDailyTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'processNewWords') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('processNewWords')
    .timeBased().everyDays(1).atHour(23).create();
  SpreadsheetApp.getUi().alert('Scheduled: runs every night around 11:00 PM.');
}

/* ==========================================================================
   MAIN PROCESSING ROUTINE
   ========================================================================== */

function getSheet_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_NAME);
}

function processNewWords() {
  const sheet = getSheet_();
  if (!sheet) { setupSheet(); return; }
  if (sheet.getLastRow() < 2) return;

  markDuplicates_(sheet);

  const last = sheet.getLastRow();
  const rows = sheet.getRange(2, 1, last - 1, HEADERS.length).getValues();

  // 1. Collect all pending words needing definitions
  const pending = [];
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const word = String(row[COL.WORD]).replace(/\s+/g, ' ').trim();
    if (!word || row[COL.STATUS]) continue;
    pending.push({ rowIndex: i + 2, word: word });
    if (pending.length >= CONFIG.MAX_PER_RUN) break;
  }

  if (!pending.length) return;

  // 2. Query Gemini AI in ONE single batch request for all pending words
  let aiBatchResult = null;
  if (CONFIG.USE_AI) {
    aiBatchResult = lookupAIBatch_(pending.map(p => p.word));
  }

  const aiMap = {};
  if (aiBatchResult && aiBatchResult.list && Array.isArray(aiBatchResult.list)) {
    aiBatchResult.list.forEach((item, idx) => {
      if (item && item.word) {
        aiMap[key_(item.word)] = item;
      } else if (item && pending[idx]) {
        aiMap[key_(pending[idx].word)] = item;
      }
    });
  }

  // 3. Populate rows (using AI batch result or falling back if missing)
  let processed = 0;
  for (let i = 0; i < pending.length; i++) {
    const p = pending[i];
    const k = key_(p.word);
    const aiItem = aiMap[k] || (aiBatchResult && aiBatchResult.list && aiBatchResult.list[i]);

    let r = null;
    if (aiItem && aiItem.definition && String(aiItem.definition).trim().length > 0) {
      r = {
        ipa: clean_(aiItem.ipa),
        pos: clean_(aiItem.pos),
        subfield: clean_(aiItem.subfield) || guessSubfield_(p.word + ' ' + aiItem.definition),
        def: clean_(aiItem.definition),
        ex: clean_(aiItem.example),
        ety: clean_(aiItem.etymology),
        syn: clean_(aiItem.synonyms),
        see: clean_(aiItem.see_also),
        src: 'Gemini AI (' + (aiBatchResult.model || CONFIG.AI_MODEL) + ')',
        status: 'Needs review'
      };
    } else {
      // Fallback for this single term if AI batch missed it
      r = buildEntry_(p.word);
    }

    const out = [
      p.word,
      r.ipa,
      r.pos,
      r.subfield,
      r.def,
      r.ex,
      r.ety,
      r.syn,
      r.see,
      new Date(),
      r.status
    ];

    sheet.getRange(p.rowIndex, 1, 1, HEADERS.length).setValues([out]);
    processed++;
  }

  sortSheet();
  formatSheet_(sheet);

  try {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      processed + ' entries populated (1 Batch Request).',
      'Horticulture Dictionary',
      6
    );
  } catch (e) { /* background trigger execution */ }
}

function sortSheet() {
  const sheet = getSheet_();
  const last = sheet.getLastRow();
  if (last < 3) return;
  sheet.getRange(2, 1, last - 1, HEADERS.length).sort({ column: 1, ascending: true });
}

/* ==========================================================================
   DUPLICATE DETECTION
   ========================================================================== */

function key_(w) {
  return String(w || '')
    .replace(/[\u200B-\u200D\uFEFF\u00A0]/g, ' ')
    .replace(/[\s\-]+/g, '')
    .toLowerCase();
}

function markDuplicates_(sheet) {
  const last = sheet.getLastRow();
  if (last < 2) return;
  const n = last - 1;
  const keys = sheet.getRange(2, 1, n, 1).getValues().map(r => key_(r[0]));
  const statuses = sheet.getRange(2, COL.STATUS + 1, n, 1).getValues().map(r => String(r[0]));

  const tiers = [
    s => s === 'Verified',
    s => s && s !== 'Duplicate' && s !== 'Verified',
    s => !s
  ];
  const seen = {};
  let changed = false;

  tiers.forEach(match => {
    for (let i = 0; i < n; i++) {
      const k = keys[i];
      if (!k || !match(statuses[i])) continue;
      if (seen[k]) {
        statuses[i] = 'Duplicate';
        changed = true;
      } else {
        seen[k] = true;
      }
    }
  });

  if (changed) {
    sheet.getRange(2, COL.STATUS + 1, n, 1).setValues(statuses.map(s => [s]));
  }
}

function deleteDuplicateRows() {
  const ui = SpreadsheetApp.getUi();
  const sheet = getSheet_();
  markDuplicates_(sheet);
  const last = sheet.getLastRow();
  if (last < 2) return;
  const statuses = sheet.getRange(2, COL.STATUS + 1, last - 1, 1).getValues();
  const dupRows = [];
  statuses.forEach((r, i) => { if (r[0] === 'Duplicate') dupRows.push(i + 2); });
  if (!dupRows.length) { ui.alert('No duplicates found.'); return; }

  const ok = ui.alert('Delete ' + dupRows.length + ' duplicate row(s)?', ui.ButtonSet.YES_NO);
  if (ok !== ui.Button.YES) return;
  dupRows.reverse().forEach(r => sheet.deleteRow(r));
}

/* ==========================================================================
   ROW HELPERS
   ========================================================================== */

function reprocessSelected() {
  const ui = SpreadsheetApp.getUi();
  const sheet = getSheet_();
  const rng = SpreadsheetApp.getActiveRange();
  if (!rng || rng.getSheet().getName() !== CONFIG.SHEET_NAME) {
    ui.alert('Select the rows you want to re-run on the "' + CONFIG.SHEET_NAME + '" sheet first.');
    return;
  }
  const start = Math.max(rng.getRow(), 2);
  const end = rng.getLastRow();
  if (end < start) return;
  sheet.getRange(start, COL.IPA + 1, end - start + 1, HEADERS.length - 1).clearContent();
  processNewWords();
}

function lowercaseSelected() {
  const ui = SpreadsheetApp.getUi();
  const sheet = getSheet_();
  const rng = SpreadsheetApp.getActiveRange();
  if (!rng || rng.getSheet().getName() !== CONFIG.SHEET_NAME || rng.getColumn() !== 1) {
    ui.alert('Select cells in column A (Word) first.');
    return;
  }
  const start = Math.max(rng.getRow(), 2);
  const end = rng.getLastRow();
  if (end < start) return;
  const target = sheet.getRange(start, 1, end - start + 1, 1);
  target.setValues(target.getValues().map(r => [String(r[0]).toLowerCase()]));
  sortSheet();
}

/* ==========================================================================
   TEXT UTILITIES
   ========================================================================== */

function clean_(t) {
  return String(t || '')
    .replace(/\[\d+\]/g, '')
    .replace(/\(\s*[;,]?\s*\)/g, '')
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:])/g, '$1')
    .trim();
}

function unique_(arr) {
  return arr.filter((v, i, a) => v && a.indexOf(v) === i);
}

function shorten_(text) {
  const t = clean_(text);
  const sentences = t.match(/.+?[.!?](?=\s+[A-Z]|$)/g);
  if (!sentences) return t;
  let out = '';
  for (let i = 0; i < sentences.length && i < CONFIG.MAX_DEF_SENTENCES; i++) {
    const next = (out ? out + ' ' : '') + sentences[i].trim();
    if (out && next.length > CONFIG.MAX_DEF_CHARS) break;
    out = next;
  }
  return out;
}

function guessSubfield_(text) {
  const t = String(text || '').toLowerCase();
  let best = '', bestScore = 0;
  Object.keys(SUBFIELD_KEYWORDS).forEach(name => {
    let score = 0;
    SUBFIELD_KEYWORDS[name].forEach(k => { if (t.indexOf(k) !== -1) score++; });
    if (score > bestScore) { best = name; bestScore = score; }
  });
  return best || 'Botany';
}

/* ==========================================================================
   ENTRY BUILDER
   ========================================================================== */

function buildEntry_(word) {
  // Query Gemini AI first if enabled & key exists
  const ai = CONFIG.USE_AI ? lookupAI_(word) : null;
  const hasAi = Boolean(ai && ai.definition && ai.definition.trim());

  // Query Free Dictionary API for supplementary phonetics or fallback
  const dict = lookupDictionary_(word);

  // Fall back to Wikipedia only if AI and dictionary didn't provide botanical meaning
  const needWiki = !hasAi && !(dict && dict.horticultural);
  const wiki = needWiki ? lookupWikipedia_(word) : null;

  let def = '', ex = '', pos = '', ipa = '', ety = '', syn = '', see = '';
  let status = 'Not found';
  const sources = [];

  if (hasAi) {
    def = ai.definition;
    ex = ai.example || '';
    pos = ai.pos || (dict && dict.pos) || '';
    ipa = ai.ipa || (dict && dict.ipa) || '';
    ety = ai.etymology || (dict && dict.ety) || '';
    syn = ai.synonyms || (dict && dict.syn) || '';
    see = ai.see_also || '';
    sources.push('Gemini AI (' + (ai.usedModel || CONFIG.AI_MODEL) + ')');
    status = 'Needs review';
  } else if (dict && dict.horticultural) {
    def = dict.def;
    ex = dict.ex;
    pos = dict.pos;
    ipa = dict.ipa;
    ety = dict.ety;
    syn = dict.syn;
    sources.push('Free Dictionary API');
    status = 'Needs review';
  } else if (wiki) {
    def = shorten_(wiki.def);
    ipa = (dict && dict.ipa) || '';
    pos = (dict && dict.pos) || '';
    ety = (dict && dict.ety) || '';
    sources.push('Wikipedia: ' + wiki.title + ' ' + wiki.url);
    status = 'Needs review';
  } else if (dict && dict.def) {
    def = dict.def;
    ex = dict.ex;
    pos = dict.pos;
    ipa = dict.ipa;
    ety = dict.ety;
    syn = dict.syn;
    sources.push('Free Dictionary API (general English sense)');
    status = 'Check sense';
  }

  // Fallback IPA from Free Dictionary API if missing
  if (!ipa && dict && dict.ipa) {
    ipa = dict.ipa;
  }

  const subfield = (ai && ai.subfield) || guessSubfield_(word + ' ' + def);

  return {
    ipa: clean_(ipa),
    pos: clean_(pos),
    subfield: clean_(subfield),
    def: clean_(def),
    ex: clean_(ex),
    ety: clean_(ety),
    syn: clean_(syn),
    see: clean_(see),
    src: unique_(sources).join('; '),
    status: def ? status : 'Not found'
  };
}

/* ==========================================================================
   LOOKUPS: GEMINI AI, FREE DICTIONARY API, WIKIPEDIA
   ========================================================================== */

function getJson_(url, options) {
  try {
    const res = UrlFetchApp.fetch(url, Object.assign({ muteHttpExceptions: true }, options || {}));
    if (res.getResponseCode() !== 200) return null;
    return JSON.parse(res.getContentText());
  } catch (e) {
    return null;
  }
}

/**
 * 1-Request Batching: Processes an entire list of terms in ONE single API call
 * Solves rate limits completely (1 call for up to 20 words).
 */
function lookupAIBatch_(words) {
  const rawKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const key = String(rawKey || '').trim().replace(/["']/g, '');
  if (!key || !words || !words.length) return null;

  const prompt =
    'You are an authoritative botanical and horticultural lexicographer building a specialized, graduate-level reference dictionary for an MS in Horticulture.\n' +
    'Provide comprehensive, academically rigorous lexical details for each of the following horticultural terms:\n' +
    JSON.stringify(words) + '\n\n' +
    'Return ONLY a valid JSON array of objects (one per term in the exact same order). Each object MUST have these exact keys:\n' +
    '- "word": The term from the input list.\n' +
    '- "ipa": Standard International Phonetic Alphabet (IPA) pronunciation enclosed in slashes (e.g. "/ˈsaɪ.ən/").\n' +
    '- "pos": Abbreviated part of speech (e.g. "n.", "v.", "adj.").' +
    '- "subfield": The single most relevant horticultural subfield chosen from: ' +
    '["Plant Propagation", "Plant Physiology", "Soil Science", "Plant Pathology", "Pest Management", "Pomology", "Olericulture", "Floriculture", "Landscape Horticulture", "Postharvest", "Plant Breeding", "Botany"].\n' +
    '- "definition": A rigorous, academic definition (1 to 2 sentences) written specifically in the botanical/horticultural sense. Avoid circular wording.\n' +
    '- "example": One natural, authentic sentence demonstrating how this term is used in a real horticultural scenario (nursery, greenhouse, orchard, field research, breeding trial, or postharvest lab).\n' +
    '- "etymology": Concise linguistic origin (Latin/Greek root words and etymological derivation).\n' +
    '- "synonyms": Comma-separated list of recognized technical or trade synonyms (or empty string if none).\n' +
    '- "see_also": 2 to 4 comma-separated related botanical/horticultural terms, contrasting terms, or physiological concepts.\n\n' +
    'Ensure all terms in the array are processed.';

  const models = unique_([CONFIG.AI_MODEL, 'gemini-3.8-flash', 'gemini-3.8-flash-lite', 'gemini-2.5-flash']);

  for (let m = 0; m < models.length; m++) {
    const currentModel = models[m];
    const url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
      encodeURIComponent(currentModel) + ':generateContent?key=' + encodeURIComponent(key);

    const payload = {
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.1,
        responseMimeType: 'application/json'
      }
    };

    try {
      const res = UrlFetchApp.fetch(url, {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      const statusCode = res.getResponseCode();
      if (statusCode === 200) {
        const data = JSON.parse(res.getContentText());
        if (!data.candidates || !data.candidates.length) continue;
        const candidate = data.candidates[0];
        if (!candidate.content || !candidate.content.parts || !candidate.content.parts.length) continue;

        const rawJson = candidate.content.parts[0].text;
        const parsed = JSON.parse(rawJson);
        const list = Array.isArray(parsed) ? parsed : (parsed.terms || parsed.words || parsed.entries || []);
        return { list: list, model: currentModel };
      }

      Logger.log('Batch AI model ' + currentModel + ' returned HTTP ' + statusCode);
      if (statusCode === 429) {
        try {
          SpreadsheetApp.getActiveSpreadsheet().toast('Gemini Rate Limit (429). Pausing 10s...', 'API Warning', 8);
        } catch (e) {}
        Utilities.sleep(10000);
      }
    } catch (e) {
      Logger.log('Network error in lookupAIBatch_ for ' + currentModel + ': ' + e.message);
    }
  }

  return null;
}

/**
 * 100% Free Gemini API lookup via Google AI Studio (Single Word Fallback)
 * Free tier allows 15 requests per minute with no billing account required.
 * Automatically tries fallback models if the primary model returns 404.
 */
function lookupAI_(word) {
  const rawKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const key = String(rawKey || '').trim().replace(/["']/g, '');
  if (!key) return null;

  // Rate limiting for Gemini free tier (15 RPM = ~4 seconds between requests)
  Utilities.sleep(4000);

  const prompt =
    'You are an authoritative botanical and horticultural lexicographer building a specialized, graduate-level reference dictionary for an MS in Horticulture.\n' +
    'Provide comprehensive, academically rigorous lexical details for the horticultural or botanical term: "' + word + '".\n\n' +
    'Return ONLY a valid JSON object with the following exact keys:\n' +
    '- "ipa": Standard International Phonetic Alphabet (IPA) pronunciation enclosed in slashes (e.g. "/ˈsaɪ.ən/").\n' +
    '- "pos": Abbreviated part of speech (e.g. "n.", "v.", "adj.").' +
    '- "subfield": The single most relevant horticultural subfield chosen from: ' +
    '["Plant Propagation", "Plant Physiology", "Soil Science", "Plant Pathology", "Pest Management", "Pomology", "Olericulture", "Floriculture", "Landscape Horticulture", "Postharvest", "Plant Breeding", "Botany"].\n' +
    '- "definition": A rigorous, academic definition (1 to 2 sentences) written specifically in the botanical/horticultural sense. Avoid circular wording.\n' +
    '- "example": One natural, authentic sentence demonstrating how this term is used in a real horticultural scenario (nursery, greenhouse, orchard, field research, breeding trial, or postharvest lab).\n' +
    '- "etymology": Concise linguistic origin (Latin/Greek root words and etymological derivation).\n' +
    '- "synonyms": Comma-separated list of recognized technical or trade synonyms (or empty string if none).\n' +
    '- "see_also": 2 to 4 comma-separated related botanical/horticultural terms, contrasting terms, or physiological concepts.\n\n' +
    'If the term has no recognized botanical or horticultural meaning, return {}.';

  // Primary model and automatic fallbacks if one returns 404
  const models = unique_([CONFIG.AI_MODEL, 'gemini-3.8-flash', 'gemini-3.8-flash-lite', 'gemini-2.5-flash']);

  for (let m = 0; m < models.length; m++) {
    const currentModel = models[m];
    const url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
      encodeURIComponent(currentModel) + ':generateContent?key=' + encodeURIComponent(key);

    const payload = {
      contents: [
        {
          parts: [{ text: prompt }]
        }
      ],
      generationConfig: {
        temperature: 0.1,
        responseMimeType: 'application/json'
      }
    };

    try {
      const res = UrlFetchApp.fetch(url, {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      const statusCode = res.getResponseCode();
      if (statusCode === 200) {
        const data = JSON.parse(res.getContentText());
        if (!data.candidates || !data.candidates.length) return null;
        const candidate = data.candidates[0];
        if (!candidate.content || !candidate.content.parts || !candidate.content.parts.length) return null;

        const rawJson = candidate.content.parts[0].text;
        const parsed = JSON.parse(rawJson);
        parsed.usedModel = currentModel;
        return parsed;
      }

      // If 404, try next model; if 400 (bad key), alert user
      Logger.log('Gemini model ' + currentModel + ' returned HTTP ' + statusCode + ': ' + res.getContentText());
      if (statusCode === 400 || statusCode === 403) {
        try {
          SpreadsheetApp.getActiveSpreadsheet().toast('Gemini API Key rejected (HTTP ' + statusCode + '). Check your key.', 'API Error', 8);
        } catch (e) {}
        return null;
      }
    } catch (e) {
      Logger.log('Network error connecting to Gemini (' + currentModel + '): ' + e.message);
    }
  }

  return null;
}

/**
 * Fallback: General English dictionary for pronunciation, POS, and definitions
 */
function lookupDictionary_(word) {
  const lower = word.toLowerCase().trim();
  const tries = unique_([lower, lower.replace(/\s+/g, '')]);
  let data = null;
  for (let i = 0; i < tries.length; i++) {
    data = getJson_('https://api.dictionaryapi.dev/api/v2/entries/en/' + encodeURIComponent(tries[i]));
    if (data && data.length) break;
  }
  if (!data || !data.length) return null;

  const out = { ipa: '', pos: '', def: '', ex: '', ety: '', syn: '', horticultural: false };
  const cands = [];

  data.forEach(e => {
    if (!out.ety && e.origin) out.ety = e.origin;
    (e.phonetics || []).forEach(p => {
      if (!out.ipa && p.text) out.ipa = p.text;
    });
    (e.meanings || []).forEach(m => {
      (m.definitions || []).forEach(d => {
        cands.push({
          pos: m.partOfSpeech || '',
          def: d.definition || '',
          ex: d.example || '',
          syn: (d.synonyms || []).concat(m.synonyms || [])
        });
      });
    });
  });

  if (!cands.length) return out;

  const hort = cands.find(c => HORT_PATTERN.test(c.def));
  const chosen = hort || cands[0];
  out.horticultural = !!hort;
  out.def = clean_(chosen.def);
  out.ex = clean_(chosen.ex);
  out.pos = POS_ABBR[chosen.pos] || chosen.pos;
  out.syn = unique_(chosen.syn).slice(0, 5).join(', ');
  return out;
}

function wikiSummary_(title) {
  const data = getJson_('https://en.wikipedia.org/api/rest_v1/page/summary/' +
    encodeURIComponent(String(title).replace(/ /g, '_')));
  if (!data || data.type !== 'standard' || !data.extract) return null;
  if (!HORT_PATTERN.test(data.extract)) return null;
  return {
    title: data.title,
    def: data.extract,
    url: data.content_urls && data.content_urls.desktop ? data.content_urls.desktop.page : ''
  };
}

/**
 * Fallback: Technical botanical terms missing from standard general dictionaries
 */
function lookupWikipedia_(word) {
  const w = word.trim().replace(/\s+/g, ' ');
  const lower = w.toLowerCase();
  const cap = s => s.charAt(0).toUpperCase() + s.slice(1);

  const variants = unique_([
    w,
    cap(lower),
    cap(lower.replace(/\s+/g, '')),
    cap(lower.replace(/[\s]+/g, '-')),
    cap(lower.replace(/-/g, ' '))
  ]);

  for (let i = 0; i < variants.length; i++) {
    const hit = wikiSummary_(variants[i]);
    if (hit) return hit;
  }

  const s = getJson_('https://en.wikipedia.org/w/rest.php/v1/search/title?limit=3&q=' + encodeURIComponent(w));
  if (s && s.pages) {
    for (let j = 0; j < s.pages.length; j++) {
      const hit = wikiSummary_(s.pages[j].title);
      if (hit) return hit;
    }
  }
  return null;
}
