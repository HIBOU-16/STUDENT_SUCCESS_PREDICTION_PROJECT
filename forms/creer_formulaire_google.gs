/**
 * Crée le formulaire « Évaluation du modèle d'alerte précoce du décrochage - cas tunisien ».
 * Généré automatiquement par forms/build_google_form.py - ne pas modifier à la main.
 * Mode d'emploi : https://script.google.com > Nouveau projet > coller ce code > Exécuter « creerFormulaire ».
 */
function creerFormulaire() {
  var form = FormApp.create("Évaluation du modèle d'alerte précoce du décrochage - cas tunisien");
  form.setDescription("Ce questionnaire fait partie d'un projet académique (ISI / UVT, mini-projet « Alerte précoce du décrochage universitaire », binôme Mariam & Iheb). Il sert à vérifier si un modèle de prédiction, entraîné sur des étudiants portugais, fonctionne aussi pour des étudiants tunisiens.\n\n• Le questionnaire est ANONYME : aucun nom, email, numéro d'inscription ni CIN n'est demandé.\n• Il concerne votre PREMIÈRE ANNÉE dans une formation universitaire (licence ou équivalent).\n• Si vous ne vous souvenez pas d'un chiffre exact, donnez une estimation.\n• Durée : environ 8 minutes. La participation est volontaire ; vous pouvez arrêter à tout moment.\n• Les réponses sont utilisées uniquement dans le cadre pédagogique de ce projet.\n\nLes étudiants qui ont quitté leur formation sont particulièrement importants pour cette étude : n'hésitez pas à transmettre le lien.");
  form.setCollectEmail(false);          // anonymat : aucun email collecté
  form.setProgressBar(true);
  form.setAllowResponseEdits(false);
  form.setConfirmationMessage("Merci pour votre participation ! Vos réponses anonymes aideront à évaluer l'outil d'alerte précoce.");

  var pages = {};

  var q_consentement = form.addMultipleChoiceItem().setTitle("J'ai lu les informations ci-dessus et j'accepte de participer").setChoiceValues(["Oui, j'accepte", "Non, je ne souhaite pas participer"]).setRequired(true);

  pages["profil"] = form.addPageBreakItem().setTitle("1. Votre profil à l'entrée en 1re année").setHelpText("Répondez pour le moment où vous êtes entré(e) en 1re année de cette formation.");
  var q_repondant = form.addMultipleChoiceItem().setTitle("Qui remplit ce questionnaire ?").setChoiceValues(["Je réponds pour moi-même (étudiant ou ancien étudiant)", "Je suis un membre du personnel et je saisis un dossier anonymisé"]).setRequired(true);
  var q_annee_entree = form.addTextItem().setTitle("Année d'entrée en 1re année").setHelpText("Exemple : 2022").setRequired(true);
  q_annee_entree.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 2000 et 2030").requireNumberBetween(2000, 2030).build());
  var q_filiere = form.addMultipleChoiceItem().setTitle("Domaine de la formation").setChoiceValues(["Informatique / génie logiciel / réseaux", "Gestion / économie", "Gestion (cours du soir)", "Marketing / publicité", "Journalisme / communication", "Design / multimédia", "Design graphique / communication visuelle", "Tourisme", "Sciences infirmières / santé", "Agronomie", "Service social", "Sciences de l'éducation / enseignement", "Vétérinaire / soins animaliers", "Autre domaine"]).setRequired(true);
  var q_genre = form.addMultipleChoiceItem().setTitle("Sexe").setChoiceValues(["Homme", "Femme"]).setRequired(true);
  var q_age_entree = form.addTextItem().setTitle("Âge à l'entrée en 1re année (en années)").setRequired(true);
  q_age_entree.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 15 et 70").requireNumberBetween(15, 70).build());
  var q_etat_civil = form.addMultipleChoiceItem().setTitle("État civil à l'entrée").setChoiceValues(["Célibataire", "Marié(e)", "Divorcé(e)", "Veuf / veuve"]).setRequired(true);
  var q_nationalite = form.addMultipleChoiceItem().setTitle("Nationalité").setChoiceValues(["Tunisienne", "Autre nationalité"]).setRequired(true);
  var q_diplome_avant = form.addMultipleChoiceItem().setTitle("Diplôme le plus élevé obtenu AVANT cette inscription").setChoiceValues(["Baccalauréat", "Licence ou diplôme universitaire de 1er cycle", "Master", "BTS / diplôme technique supérieur", "Formation professionnelle ou technologique", "Baccalauréat non obtenu (accès spécial)"]).setRequired(true);
  var q_section_bac = form.addMultipleChoiceItem().setTitle("Section du baccalauréat").setChoiceValues(["Mathématiques", "Sciences expérimentales", "Sciences techniques", "Sciences de l'informatique", "Économie et gestion", "Lettres", "Sport", "Autre / pas de bac"]).setRequired(false);
  var q_moyenne_bac = form.addTextItem().setTitle("Moyenne générale au baccalauréat (sur 20)").setHelpText("Utilisez un point pour les décimales, par exemple 13.45").setRequired(true);
  q_moyenne_bac.setValidation(FormApp.createTextValidation().setHelpText("Nombre décimal entre 0 et 20").requireNumberBetween(0, 20).build());
  var q_mode_admission = form.addMultipleChoiceItem().setTitle("Comment avez-vous été admis(e) dans cette formation ?").setChoiceValues(["Orientation universitaire - 1er tour", "Orientation universitaire - 2e tour", "Orientation universitaire - 3e tour / orientation finale", "Réorientation (changement de filière)", "Transfert depuis un autre établissement", "Titulaire d'un autre diplôme supérieur", "Formation continue / candidat de plus de 23 ans", "Étudiant étranger (admission internationale)"]).setRequired(true);
  var q_rang_choix = form.addTextItem().setTitle("Rang de cette formation dans votre fiche de vœux (1 = premier choix)").setHelpText("Si vous ne savez pas, mettez votre meilleure estimation.").setRequired(true);
  q_rang_choix.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 1 et 30").requireNumberBetween(1, 30).build());
  var q_regime = form.addMultipleChoiceItem().setTitle("Régime des cours").setChoiceValues(["Cours du jour", "Cours du soir", "À distance / hybride"]).setRequired(true);
  var q_niveau_mere = form.addMultipleChoiceItem().setTitle("Niveau d'études de la mère").setChoiceValues(["Non scolarisé(e) / ne sait pas lire", "Primaire", "Collège (enseignement de base jusqu'à la 9e)", "Secondaire sans baccalauréat", "Baccalauréat", "Licence (bac+3)", "Master / ingénieur (bac+5)", "Doctorat", "Je ne sais pas"]).setRequired(true);
  var q_niveau_pere = form.addMultipleChoiceItem().setTitle("Niveau d'études du père").setChoiceValues(["Non scolarisé(e) / ne sait pas lire", "Primaire", "Collège (enseignement de base jusqu'à la 9e)", "Secondaire sans baccalauréat", "Baccalauréat", "Licence (bac+3)", "Master / ingénieur (bac+5)", "Doctorat", "Je ne sais pas"]).setRequired(true);
  var q_profession_mere = form.addMultipleChoiceItem().setTitle("Profession de la mère").setChoiceValues(["Étudiant(e)", "Cadre supérieur / directeur / élu", "Profession intellectuelle ou scientifique (ingénieur, médecin, enseignant…)", "Technicien / profession intermédiaire", "Employé(e) administratif / de bureau", "Commerce, services, sécurité", "Agriculteur / pêcheur", "Ouvrier qualifié / artisan / bâtiment", "Conducteur / opérateur de machines", "Ouvrier non qualifié", "Forces armées", "Sans emploi / au foyer / retraité(e)", "Décédé(e) / je ne sais pas"]).setRequired(true);
  var q_profession_pere = form.addMultipleChoiceItem().setTitle("Profession du père").setChoiceValues(["Étudiant(e)", "Cadre supérieur / directeur / élu", "Profession intellectuelle ou scientifique (ingénieur, médecin, enseignant…)", "Technicien / profession intermédiaire", "Employé(e) administratif / de bureau", "Commerce, services, sécurité", "Agriculteur / pêcheur", "Ouvrier qualifié / artisan / bâtiment", "Conducteur / opérateur de machines", "Ouvrier non qualifié", "Forces armées", "Sans emploi / au foyer / retraité(e)", "Décédé(e) / je ne sais pas"]).setRequired(true);
  var q_loge_hors_famille = form.addMultipleChoiceItem().setTitle("Pendant la 1re année, logiez-vous hors du domicile familial (foyer, location) ?").setChoiceValues(["Oui", "Non"]).setRequired(true);
  var q_besoins_specifiques = form.addMultipleChoiceItem().setTitle("Aviez-vous des besoins éducatifs particuliers (handicap, trouble…) ?").setChoiceValues(["Oui", "Non"]).setRequired(true);
  var q_boursier = form.addMultipleChoiceItem().setTitle("Étiez-vous boursier / boursière en 1re année ?").setChoiceValues(["Oui", "Non"]).setRequired(true);
  var q_frais_a_jour = form.addMultipleChoiceItem().setTitle("Vos frais d'inscription de 1re année ont-ils été payés à temps ?").setChoiceValues(["Oui", "Non"]).setRequired(true);
  var q_dette = form.addMultipleChoiceItem().setTitle("Aviez-vous une dette envers l'établissement en 1re année (frais, foyer, bibliothèque…) ?").setChoiceValues(["Oui", "Non"]).setRequired(true);
  var q_distance_km = form.addTextItem().setTitle("Distance entre votre domicile et l'établissement (en km)").setRequired(false);
  q_distance_km.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 1000").requireNumberBetween(0, 1000).build());
  var q_transport = form.addMultipleChoiceItem().setTitle("Moyen de transport principal").setChoiceValues(["À pied", "Transport en commun (bus, métro, train, louage)", "Voiture / moto", "Logé(e) sur place / foyer", "Cours à distance"]).setRequired(false);
  var q_temps_trajet = form.addTextItem().setTitle("Temps de trajet aller (en minutes)").setRequired(false);
  q_temps_trajet.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 400").requireNumberBetween(0, 400).build());
  var q_emploi = form.addMultipleChoiceItem().setTitle("Aviez-vous un emploi pendant la 1re année ?").setChoiceValues(["Non", "Oui, à temps partiel", "Oui, à temps plein"]).setRequired(false);

  pages["s1"] = form.addPageBreakItem().setTitle("2. Votre 1er semestre de 1re année").setHelpText("Un « module » = une matière évaluée séparément. Donnez une estimation si vous n'êtes pas sûr(e).");
  var q_s1_inscrits = form.addTextItem().setTitle("S1 - Nombre de modules auxquels vous étiez inscrit(e)").setRequired(true);
  q_s1_inscrits.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s1_credites = form.addTextItem().setTitle("S1 - Nombre de modules validés par équivalence ou dispense (sans les passer)").setHelpText("En général 0.").setRequired(true);
  q_s1_credites.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s1_evaluations = form.addTextItem().setTitle("S1 - Nombre d'examens finaux passés (session principale + rattrapage)").setRequired(true);
  q_s1_evaluations.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 60").requireNumberBetween(0, 60).build());
  var q_s1_valides = form.addTextItem().setTitle("S1 - Nombre de modules validés").setRequired(true);
  q_s1_valides.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s1_moyenne = form.addTextItem().setTitle("S1 - Moyenne générale du semestre (sur 20)").setHelpText("Utilisez un point pour les décimales, par exemple 11.25").setRequired(true);
  q_s1_moyenne.setValidation(FormApp.createTextValidation().setHelpText("Nombre décimal entre 0 et 20").requireNumberBetween(0, 20).build());
  var q_s1_sans_eval = form.addTextItem().setTitle("S1 - Nombre de modules pour lesquels vous n'avez passé AUCUN examen").setRequired(true);
  q_s1_sans_eval.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s1_absences = form.addMultipleChoiceItem().setTitle("S1 - Combien de séances avez-vous manquées environ ?").setChoiceValues(["Aucune", "1 à 3", "4 à 10", "Plus de 10"]).setRequired(false);
  var q_s1_plateforme = form.addMultipleChoiceItem().setTitle("S1 - À quelle fréquence utilisiez-vous la plateforme en ligne (Moodle, Classroom…) ?").setChoiceValues(["Jamais", "Moins d'une fois par semaine", "1 à 3 fois par semaine", "Presque tous les jours"]).setRequired(false);
  var q_s1_participation = form.addScaleItem().setTitle("S1 - Votre participation aux activités (TD, TP, projets)").setBounds(1, 5).setLabels("Très faible", "Très forte").setRequired(false);
  var q_s1_travail_perso = form.addTextItem().setTitle("S1 - Heures de travail personnel par semaine (environ)").setRequired(false);
  q_s1_travail_perso.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 80").requireNumberBetween(0, 80).build());
  var q_s2_fait = form.addMultipleChoiceItem().setTitle("Avez-vous suivi le 2e semestre de la 1re année ?").setRequired(true);

  pages["s2"] = form.addPageBreakItem().setTitle("3. Votre 2e semestre de 1re année").setHelpText("Mêmes questions que pour le 1er semestre.");
  var q_s2_inscrits = form.addTextItem().setTitle("S2 - Nombre de modules auxquels vous étiez inscrit(e)").setRequired(true);
  q_s2_inscrits.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s2_credites = form.addTextItem().setTitle("S2 - Nombre de modules validés par équivalence ou dispense (sans les passer)").setRequired(true);
  q_s2_credites.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s2_evaluations = form.addTextItem().setTitle("S2 - Nombre d'examens finaux passés (session principale + rattrapage)").setRequired(true);
  q_s2_evaluations.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 60").requireNumberBetween(0, 60).build());
  var q_s2_valides = form.addTextItem().setTitle("S2 - Nombre de modules validés").setRequired(true);
  q_s2_valides.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());
  var q_s2_moyenne = form.addTextItem().setTitle("S2 - Moyenne générale du semestre (sur 20)").setRequired(true);
  q_s2_moyenne.setValidation(FormApp.createTextValidation().setHelpText("Nombre décimal entre 0 et 20").requireNumberBetween(0, 20).build());
  var q_s2_sans_eval = form.addTextItem().setTitle("S2 - Nombre de modules pour lesquels vous n'avez passé AUCUN examen").setRequired(true);
  q_s2_sans_eval.setValidation(FormApp.createTextValidation().setHelpText("Nombre entier entre 0 et 30").requireNumberBetween(0, 30).build());

  pages["situation"] = form.addPageBreakItem().setTitle("4. Votre situation aujourd'hui").setHelpText("C'est la question la plus importante : elle permet de vérifier si le modèle avait raison.");
  var q_statut = form.addMultipleChoiceItem().setTitle("Quelle est votre situation aujourd'hui dans CETTE formation ?").setChoiceValues(["J'ai obtenu le diplôme de cette formation", "Je suis encore inscrit(e) et j'ai dépassé la durée normale (redoublement)", "Je suis encore inscrit(e), dans la durée normale", "J'ai quitté cette formation sans le diplôme (abandon, réorientation, autre établissement)"]).setRequired(true);
  var q_annee_depart = form.addMultipleChoiceItem().setTitle("Si vous avez quitté la formation : pendant quelle année d'études ?").setChoiceValues(["1re année", "2e année", "3e année ou plus"]).setRequired(false);
  var q_raisons_depart = form.addCheckboxItem().setTitle("Si vous avez quitté la formation : pour quelles raisons ?").setChoiceValues(["Difficultés financières", "Résultats insuffisants", "Formation non choisie / mauvaise orientation", "Transport ou distance", "Santé", "Travail", "Perte de motivation", "Raisons familiales"]).setRequired(false);
  var q_satisfaction = form.addScaleItem().setTitle("Votre satisfaction vis-à-vis de la formation").setBounds(1, 5).setLabels("Pas du tout satisfait(e)", "Très satisfait(e)").setRequired(false);

  pages["avis"] = form.addPageBreakItem().setTitle("5. Votre avis sur un outil d'alerte précoce");
  var q_utilite = form.addScaleItem().setTitle("Un outil qui aide l'université à repérer tôt les étudiants en difficulté serait-il utile ?").setBounds(1, 5).setLabels("Pas du tout utile", "Très utile").setRequired(false);
  var q_aide_souhaitee = form.addCheckboxItem().setTitle("Quelle aide auriez-vous souhaité recevoir en cas de difficulté ?").setChoiceValues(["Tutorat / soutien pédagogique", "Entretien avec un enseignant", "Aide financière", "Soutien psychologique", "Aide à la réorientation", "Aucune"]).setRequired(false);
  var q_accord_donnees = form.addMultipleChoiceItem().setTitle("Seriez-vous d'accord pour que des données anonymes servent à ce type d'outil ?").setChoiceValues(["Oui", "Oui, seulement avec mon accord explicite", "Non"]).setRequired(false);
  var q_commentaire = form.addParagraphTextItem().setTitle("Commentaire libre (facultatif)").setRequired(false);

  // Navigation conditionnelle
  q_consentement.setChoices([q_consentement.createChoice("Oui, j'accepte", FormApp.PageNavigationType.CONTINUE), q_consentement.createChoice("Non, je ne souhaite pas participer", FormApp.PageNavigationType.SUBMIT)]);
  q_s2_fait.setChoices([q_s2_fait.createChoice("Oui", pages["s2"]), q_s2_fait.createChoice("Non", pages["situation"])]);
  // Fin du S2 : continuer vers la page « situation » (comportement par défaut).

  // Feuille Google Sheets qui reçoit les réponses
  var ss = SpreadsheetApp.create("Réponses - Évaluation du modèle d'alerte précoce du décrochage - cas tunisien");
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  Logger.log('Lien à ENVOYER aux répondants : ' + form.getPublishedUrl());
  Logger.log('Lien pour MODIFIER le formulaire : ' + form.getEditUrl());
  Logger.log('Feuille des réponses : ' + ss.getUrl());
}
