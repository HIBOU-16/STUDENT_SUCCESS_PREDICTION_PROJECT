# Formulaire d'évaluation : cas tunisien

Ce formulaire sert à vérifier si le modèle, entraîné sur des étudiants portugais, fonctionne pour des étudiants tunisiens. Il recueille les mêmes informations que celles utilisées par le modèle, plus la **situation réelle** de chaque répondant (diplômé, encore inscrit après la durée normale, ou abandon). L'application compare ensuite la prédiction du modèle à cette situation réelle.

## 1. Créer le Google Form (5 minutes, une seule fois)

1. Connectez-vous au compte Google qui doit posséder le formulaire, puis ouvrez https://script.google.com.
2. Cliquez sur **Nouveau projet**.
3. Effacez le code affiché, puis collez **tout** le contenu de `creer_formulaire_google.gs`.
4. Enregistrez (icône disquette), vérifiez que la fonction `creerFormulaire` est sélectionnée en haut, puis cliquez sur **Exécuter**.
5. Google demande une autorisation : **Examiner les autorisations**, choisissez votre compte, puis **Paramètres avancés › Accéder au projet (non sécurisé)** › **Autoriser**. Ce message apparaît parce que le script est le vôtre et n'a pas été vérifié par Google ; il ne fait que créer un formulaire et une feuille dans votre Drive.
6. Ouvrez le **Journal d'exécution** en bas. Il affiche trois liens :
   - le **lien à envoyer** aux répondants ;
   - le **lien pour modifier** le formulaire ;
   - la **feuille Google Sheets** des réponses.

Le formulaire et la feuille sont aussi visibles dans votre Google Drive.

## 2. Avant de diffuser

- Faites relire l'aperçu `APERCU_FORMULAIRE_TUNISIE.pdf` par votre encadrante.
- Remplissez le formulaire vous-mêmes une fois, puis supprimez cette réponse de test dans la feuille.
- **Ne modifiez pas le texte des questions ni des choix dans Google Forms.** Le programme reconnaît les réponses grâce à ces textes. Pour changer une question, modifiez `src/tunisia_form.py`, lancez `python forms/build_google_form.py`, puis recréez le formulaire.

## 3. Diffuser

- Cibles : étudiants de 2e et 3e année, diplômés récents, et surtout **les étudiants qui ont quitté leur formation**, souvent difficiles à joindre (groupes de promotion, réseaux sociaux, bouche-à-oreille).
- Un membre de la scolarité peut aussi saisir des dossiers **anonymisés** : choisir « Je suis un membre du personnel… ».
- Objectif : **au moins 100 réponses, dont 30 abandons**. En dessous de 30 réponses avec une situation connue, ou de 10 abandons, l'application n'affiche pas de conclusion.

## 4. Analyser les réponses

1. Dans la feuille des réponses : **Fichier › Télécharger › Valeurs séparées par des virgules (.csv)**.
2. Dans l'application, page **Évaluation Tunisie**, importez ce fichier.
   Équivalent en ligne de commande : `python -m src.tunisia --csv chemin/vers/le_fichier.csv`
3. L'application affiche, pour chaque moment de prédiction (A, B, C) : le nombre de réponses exploitables, le macro-F1 et le taux de décrocheurs détectés avec leurs **intervalles de confiance à 95 %**, la comparaison avec le Portugal, la matrice de confusion, la comparaison des profils et une **conclusion proposée**.

Les réponses converties sont enregistrées dans `data/tunisia/reponses_converties.csv`. Elles pourront servir à ré-entraîner le modèle. Ce dossier est exclu de Git, car il contient les réponses réelles.

## Approximations à citer dans le rapport

| Réponse tunisienne | Variable du modèle | Approximation |
|---|---|---|
| Moyenne du bac /20 | `admission_grade`, `previous_qualification_grade` (/200) | multipliée par 10 |
| Domaine de formation | `course` | cursus portugais le plus proche ; « Autre » = catégorie rare |
| Tours d'orientation, réorientation, transfert | `application_mode` | modes portugais équivalents |
| Rang du vœu | `application_order` | plafonné à 9 |
| Nationalité tunisienne / autre | `nationality`, `international` | « nationale » = code 1 ; autre = code rare et international = 1 |
| À distance / hybride | `daytime_evening_attendance` | traité comme « cours du soir » (0) |
| Chômage, inflation, PIB | `unemployment_rate`, `inflation_rate`, `gdp` | médiane portugaise (valeur neutre) : le modèle n'a vu que 10 années portugaises |
| Moyenne du semestre si aucun module validé | `cu_*_grade` | 0, comme dans le dataset UCI |

Les questions sur l'absentéisme, la plateforme en ligne, le transport, l'emploi et la satisfaction ne sont **pas** utilisées par le modèle actuel, car le dataset portugais ne les contient pas. L'énoncé les mentionne : elles sont recueillies pour un futur modèle tunisien.
