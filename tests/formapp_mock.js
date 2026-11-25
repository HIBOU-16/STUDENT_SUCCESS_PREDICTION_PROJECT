// Simulation minimale de Google Apps Script (FormApp, SpreadsheetApp, Logger) pour tester
// forms/creer_formulaire_google.gs hors de Google. Usage : node tests/formapp_mock.js <fichier.gs>
// Affiche en JSON la liste des éléments créés.
const fs = require("fs");
const vm = require("vm");

const items = [];
const settings = {};
const logs = [];
let pageCount = 0;

function item(kind) {
  const it = { kind, title: null, required: false, choices: null, validation: null, help: null };
  const api = {
    _it: it,
    setTitle(t) { it.title = t; return api; },
    setHelpText(t) { it.help = t; return api; },
    setRequired(r) { it.required = r; return api; },
    setChoiceValues(v) { it.choices = v.map((value) => ({ value, nav: null })); return api; },
    createChoice(value, nav) {
      const target = nav && nav._it ? { page: nav._it.title } : nav;
      return { value, nav: target };
    },
    setChoices(list) { it.choices = list; return api; },
    setValidation(v) { it.validation = v; return api; },
    setBounds(a, b) { it.bounds = [a, b]; return api; },
    setLabels(a, b) { it.labels = [a, b]; return api; },
  };
  if (kind === "page") pageCount += 1;
  items.push(it);
  return api;
}

const form = {
  setDescription(d) { settings.description = d; return form; },
  setCollectEmail(v) { settings.collectEmail = v; return form; },
  setProgressBar(v) { settings.progressBar = v; return form; },
  setAllowResponseEdits(v) { settings.allowEdits = v; return form; },
  setConfirmationMessage(m) { settings.confirmation = m; return form; },
  addMultipleChoiceItem: () => item("choice"),
  addCheckboxItem: () => item("checkbox"),
  addTextItem: () => item("text"),
  addScaleItem: () => item("scale"),
  addParagraphTextItem: () => item("paragraph"),
  addPageBreakItem: () => item("page"),
  setDestination(type, id) { settings.destination = { type, id }; return form; },
  getPublishedUrl: () => "https://docs.google.com/forms/FAKE/viewform",
  getEditUrl: () => "https://docs.google.com/forms/FAKE/edit",
};

function validationBuilder() {
  const v = {};
  const b = {
    setHelpText(t) { v.help = t; return b; },
    requireNumberBetween(a, c) { v.min = a; v.max = c; return b; },
    build() { return v; },
  };
  return b;
}

const sandbox = {
  FormApp: {
    create(title) { settings.title = title; return form; },
    createTextValidation: validationBuilder,
    PageNavigationType: { CONTINUE: "CONTINUE", SUBMIT: "SUBMIT" },
    DestinationType: { SPREADSHEET: "SPREADSHEET" },
  },
  SpreadsheetApp: { create(name) { settings.sheet = name; return { getId: () => "SHEET_ID", getUrl: () => "https://docs.google.com/spreadsheets/FAKE" }; } },
  Logger: { log: (m) => logs.push(m) },
};

vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), sandbox);
sandbox.creerFormulaire();
console.log(JSON.stringify({ settings, items, pageCount, logs }));
