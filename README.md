# Métro de Paris — en direct

Une carte du métro parisien (14 lignes + 3bis/7bis) qui affiche :
- **l'état du trafic en temps réel** par ligne (normal / perturbé / interrompu) ;
- **les prochains passages en temps réel** à chaque station, quand vous cliquez dessus ;
- des trains **animés** qui circulent sur les voies — ceci est une **simulation**
  basée sur les fréquences officielles : la RATP ne publie pas la position GPS
  réelle des rames (le métro est souterrain), donc personne ne peut afficher
  "le vrai point bleu qui bouge". Le reste (trafic, prochains passages) est en
  revanche bien réel.

Tout tourne **en local sur votre ordinateur**, avec votre propre clé API
gratuite. Rien n'est envoyé ailleurs que vers l'API officielle d'Île-de-France
Mobilités.

## Installation (une fois)

**1. Récupérez une clé API gratuite**
Allez sur https://prim.iledefrance-mobilites.fr/fr/mon-jeton-api, créez un
compte (email + mot de passe), puis générez un jeton dans "Mes jetons API".
C'est gratuit et donne droit à 1 000 000 requêtes/jour sur les horaires et
20 000/jour sur le trafic — largement suffisant pour un usage personnel.

**2. Installez les dépendances Python** (Python 3.9 ou plus récent)
```bash
cd paris-metro-live
pip install -r requirements.txt
```

**3. Configurez votre clé**
```bash
cp .env.example .env
```
Puis ouvrez `.env` et collez votre clé après `PRIM_API_KEY=`.

**4. Construisez les données du réseau** (une seule fois, ~1-2 minutes)
```bash
python3 build_network.py
```
Ce script télécharge les données publiques (coordonnées des stations,
identifiants techniques) directement depuis le portail open data
d'Île-de-France Mobilités — **aucune clé API n'est nécessaire pour cette
étape**, ce sont des données ouvertes. Il affiche à la fin un rapport des
stations qu'il n'a pas réussi à rapprocher automatiquement (s'il y en a) :
regardez `data/topology.py` si une station de la carte finale semble mal
placée ou absente.

## Lancer la carte

```bash
python3 server.py
```
Puis ouvrez **http://127.0.0.1:8000** dans votre navigateur.

## Comment ça marche

- `data/topology.py` : l'ordre des stations de chaque ligne et les couleurs
  officielles, compilés à la main (texte lisible, modifiable facilement).
- `build_network.py` : croise cette topologie avec les données ouvertes
  officielles pour récupérer les vraies coordonnées GPS et les identifiants
  techniques de chaque station, et écrit `data/network.json`.
- `server.py` : petit serveur Flask qui sert la carte et relaie les deux API
  temps réel (état du trafic, prochains passages) en y ajoutant votre clé —
  qui ne quitte donc jamais votre machine côté navigateur.
- `static/` : la carte elle-même (HTML/CSS/JS, une seule page, pas de
  dépendance externe).

## Déploiement en ligne (accessible depuis n'importe où)

Vous pouvez aussi héberger ce projet gratuitement sur [Render](https://render.com)
au lieu de le faire tourner en local — pratique si vous voulez y accéder depuis
votre téléphone ou un autre ordinateur.

1. Créez un compte GitHub (gratuit) si vous n'en avez pas, puis un nouveau
   dépôt, et uploadez-y le contenu de ce dossier **sauf `.env`** (ne mettez
   jamais votre clé API dans un dépôt) et `data/network.json` (inutile, il
   sera reconstruit automatiquement).
2. Créez un compte sur [render.com](https://render.com), "New +" → "Web
   Service", connectez le dépôt GitHub.
3. Renseignez :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python3 server.py`
4. Dans l'onglet "Environment", ajoutez la variable `PRIM_API_KEY` avec votre
   clé.
5. Déployez. Au premier démarrage, le serveur construit automatiquement
   `data/network.json` (1-2 minutes), puis la carte est accessible à l'URL
   fournie par Render.

À savoir : le plan gratuit de Render met le service en veille après 15 minutes
sans visite, avec ~30-60 secondes de réveil au prochain accès — sans impact
une fois la page chargée.

## Limites connues

- **Positions des trains = simulation.** Basées sur une fréquence supposée
  par ligne, pas sur la position réelle des rames (donnée non publiée).
- **Ordre des stations compilé à la main.** Pour les embranchements (lignes 7
  et 13 notamment) et les extensions récentes, une petite erreur est possible.
  Si vous en repérez une, corrigez le nom dans `data/topology.py` et relancez
  `build_network.py`.
- Le serveur Flask utilisé (`debug=True`) est fait pour un usage local, pas
  pour être exposé sur internet.

## Idées d'amélioration

- Ajouter les RER et tramways (la structure du code s'y prête : il suffirait
  d'étendre `data/topology.py` et de filtrer `transportmode` autrement dans
  `build_network.py`).
- Caler la vitesse simulée des trains sur les vrais horaires GTFS plutôt que
  sur une fréquence moyenne.
- Un mode "zoom sur une ligne" en cliquant sur la légende.
