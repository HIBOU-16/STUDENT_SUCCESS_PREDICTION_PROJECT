"""Génère forms/creer_formulaire_google.gs à partir de src/tunisia_form.py.

    python forms/build_google_form.py

Le fichier .gs se colle dans https://script.google.com : la fonction creerFormulaire() crée le Google Form,
la feuille Google Sheets qui reçoit les réponses, et affiche les deux liens.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tunisia_form import INTRO, SECTIONS, choices_of  # noqa: E402

OUT = Path(__file__).with_name("creer_formulaire_google.gs")
TITLE = "Évaluation du modèle d'alerte précoce du décrochage - cas tunisien"


def js(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def number_validation(q) -> str:
    kind = "décimal" if q.get("decimal") else "entier"
    help_text = f"Nombre {kind} entre {q['min']} et {q['max']}"
    return (f"FormApp.createTextValidation().setHelpText({js(help_text)})"
            f".requireNumberBetween({q['min']}, {q['max']}).build()")


def item_code(q) -> list[str]:
    title, req = js(q["title"]), "true" if q.get("required") else "false"
    help_line = f".setHelpText({js(q['help'])})" if q.get("help") else ""
    var = f"q_{q['id']}"
    t = q["type"]
    if t == "choice":
        return [f"  var {var} = form.addMultipleChoiceItem().setTitle({title}){help_line}"
                f".setChoiceValues({js(list(choices_of(q)))}).setRequired({req});"]
    if t == "checkbox":
        return [f"  var {var} = form.addCheckboxItem().setTitle({title}){help_line}"
                f".setChoiceValues({js(list(choices_of(q)))}).setRequired({req});"]
    if t == "number":
        return [f"  var {var} = form.addTextItem().setTitle({title}){help_line}.setRequired({req});",
                f"  {var}.setValidation({number_validation(q)});"]
    if t == "scale":
        return [f"  var {var} = form.addScaleItem().setTitle({title}){help_line}.setBounds(1, 5)"
                f".setLabels({js(q['low'])}, {js(q['high'])}).setRequired({req});"]
    if t == "paragraph":
        return [f"  var {var} = form.addParagraphTextItem().setTitle({title}){help_line}.setRequired({req});"]
    if t == "branch":  # les choix (avec saut de page) sont posés à la fin, quand toutes les pages existent
        return [f"  var {var} = form.addMultipleChoiceItem().setTitle({title}){help_line}.setRequired({req});"]
    raise ValueError(t)


def build() -> str:
    lines = [
        "/**",
        " * Crée le formulaire « " + TITLE + " ».",
        " * Généré automatiquement par forms/build_google_form.py - ne pas modifier à la main.",
        " * Mode d'emploi : https://script.google.com > Nouveau projet > coller ce code > Exécuter « creerFormulaire ».",
        " */",
        "function creerFormulaire() {",
        f"  var form = FormApp.create({js(TITLE)});",
        f"  form.setDescription({js(INTRO)});",
        "  form.setCollectEmail(false);          // anonymat : aucun email collecté",
        "  form.setProgressBar(true);",
        "  form.setAllowResponseEdits(false);",
        "  form.setConfirmationMessage(" + js("Merci pour votre participation ! Vos réponses anonymes aideront à "
                                              "évaluer l'outil d'alerte précoce.") + ");",
        "",
        "  var pages = {};",
    ]
    for sec in SECTIONS:
        lines.append("")
        if sec["title"]:
            help_line = f".setHelpText({js(sec['help'])})" if sec.get("help") else ""
            lines.append(f"  pages[{js(sec['id'])}] = form.addPageBreakItem().setTitle({js(sec['title'])}){help_line};")
        for q in sec["questions"]:
            lines += item_code(q)

    lines += ["", "  // Navigation conditionnelle"]
    consent = SECTIONS[0]["questions"][0]
    yes, no = list(choices_of(consent))
    lines.append(f"  q_consentement.setChoices([q_consentement.createChoice({js(yes)}, FormApp.PageNavigationType.CONTINUE),"
                 f" q_consentement.createChoice({js(no)}, FormApp.PageNavigationType.SUBMIT)]);")
    for sec in SECTIONS:
        for q in sec["questions"]:
            if q["type"] == "branch":
                ch = ", ".join(f"q_{q['id']}.createChoice({js(lab)}, pages[{js(target)}])"
                               for lab, target in q["choices"].items())
                lines.append(f"  q_{q['id']}.setChoices([{ch}]);")
    lines += [
        "  // Fin du S2 : continuer vers la page « situation » (comportement par défaut).",
        "",
        "  // Feuille Google Sheets qui reçoit les réponses",
        f"  var ss = SpreadsheetApp.create({js('Réponses - ' + TITLE)});",
        "  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());",
        "",
        "  Logger.log('Lien à ENVOYER aux répondants : ' + form.getPublishedUrl());",
        "  Logger.log('Lien pour MODIFIER le formulaire : ' + form.getEditUrl());",
        "  Logger.log('Feuille des réponses : ' + ss.getUrl());",
        "}",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    n = sum(len(s["questions"]) for s in SECTIONS)
    print(f"{OUT.name} généré : {n} questions, {sum(1 for s in SECTIONS if s['title'])} pages")
