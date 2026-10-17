# Superguide : PartnerHub Data Platform

Ce guide explique tout, pas à pas, pour refaire le projet sur n'importe quel ordinateur.
Lis chaque étape **dans l'ordre**. Copie les commandes **exactement**.

---

## 0. L'histoire du projet (à raconter en entretien)

Imagine une entreprise qui vend un logiciel de gestion des **partenaires commerciaux** (comme EULER).
Elle a 3 clients : **Acme**, **Globex** et **Initech**.

Chaque client utilise un CRM différent, et chacun **dit la même chose avec des mots différents** :

| Ce que ça veut dire | Acme (HubSpot) | Globex (Salesforce) | Initech (Pipedrive) |
|---|---|---|---|
| Affaire gagnée | `closedwon` | `Closed Won` | `won` |
| Revendeur | `Reseller` | `VAR` | `reseller` |
| Côte d'Ivoire | `Ivory Coast` | `Côte d'Ivoire` | `CIV` |
| Monnaie | dollar | euro | franc CFA |

**Ton travail** : tout ramener à **un seul langage commun**, sans perdre une seule ligne, sans laisser fuir de données personnelles, et en le **prouvant** avec des tests.

C'est exactement ton histoire de Global Pharma (« SUS » et « SUSP »), mais en mieux outillé.

---

## 1. Ce qu'il faut installer (une seule fois)

1. **Docker Desktop** : https://www.docker.com/products/docker-desktop
   - Télécharge-le, installe-le, puis redémarre l'ordinateur.
   - Ouvre Docker Desktop et attends que la baleine en bas à gauche soit **verte** (« Engine running »).
2. **Git** : https://git-scm.com/downloads (clique sur « Next » partout).
3. **VS Code** (pour lire le code) : https://code.visualstudio.com

Pour vérifier, ouvre un terminal (touche Windows, tape `PowerShell`, Entrée), puis tape :

```bash
docker --version
```

Tu dois voir un numéro de version. Fais pareil avec `git --version`.

---

## 2. Récupérer le projet

Dans le terminal :

```bash
cd $HOME\Downloads
```

```bash
git clone https://github.com/Isac9/partnerhub-data-platform.git
```

```bash
cd partnerhub-data-platform
```

Tu es maintenant **dans le dossier du projet**. Toutes les commandes suivantes se tapent **ici**.

---

## 3. Démarrer les services

```bash
docker compose up -d postgres crm-api docs
```

La première fois, ça prend quelques minutes, car Docker télécharge les images.

Ce qui démarre :

| Service | Rôle | Adresse |
|---|---|---|
| `postgres` | La base de données (l'entrepôt) | `localhost:5435` |
| `crm-api` | Une fausse API HubSpot pour Acme | http://localhost:8010/docs |
| `docs` | Le catalogue de données | http://localhost:8082 |

---

## 4. Lancer le pipeline

```bash
docker compose run --rm pipeline
```

La première fois, Docker construit l'image Python, ce qui prend environ 5 minutes. Ensuite, le pipeline tourne en moins d'une minute.

Tu vas voir défiler ces étapes. Voici ce que chacune fait :

| Étape | Ce qui se passe | En une phrase pour l'entretien |
|---|---|---|
| 0 | Création des fausses données | « J'ai simulé 3 clients avec 3 CRM. » |
| 1 | Lecture de l'API (page par page), du CSV et du JSON | « Ingestion de 3 formats, avec pagination par curseur. » |
| 2 | Les e-mails sont remplacés par un code (hachage HMAC), les noms supprimés | « Les données personnelles n'entrent jamais en clair dans l'entrepôt. » |
| 3 | Chaque valeur est comparée aux tables de correspondance | « Une valeur inconnue arrête le pipeline au lieu de disparaître. » |
| 4 | Chargement dans `raw`, avec les totaux de la source | « Je garde les totaux de la source pour rapprocher. » |
| 5 | dbt : transformations et 28 tests | « Le modèle commun est testé, rapprochement compris. » |
| 6 | Recherche de tout e-mail dans toute la base | « Je prouve qu'aucune donnée personnelle n'a fui. » |
| 7 | Export en Parquet, analyse avec DuckDB | « Je regarde la distribution avant de croire une moyenne. » |
| 8 | Analyse de survie (Kaplan-Meier) | « Je tiens compte des affaires encore ouvertes. » |
| 9 | Génération du catalogue | « Tout est documenté, avec le lignage. » |

À la fin, tu dois lire : **`PIPELINE OK`**.

---

## 5. Regarder le résultat

### Le catalogue de données
Ouvre http://localhost:8082 dans ton navigateur.
- À gauche, clique sur **partnerhub**, puis **marts**, puis **fct_deals** : tu vois les colonnes et leur description.
- En bas à droite, le bouton bleu rond ouvre **le lignage** (le graphique du parcours des données).

### La base de données
```bash
docker compose exec postgres psql -U partnerhub -d partnerhub
```
Tu es dans PostgreSQL. Tape :
```sql
select tenant_id, status, count(*) from marts.fct_deals group by 1, 2 order by 1, 2;
```
Pour sortir, tape `\q`, puis Entrée.

---

## 6. Les 3 démonstrations à savoir faire

### Démo 1 : une nouvelle orthographe arrive (ton histoire « SUS / SUSP »)
On fait comme si Globex se mettait à écrire `Closed-Won` au lieu de `Closed Won` :
```bash
docker compose run --rm pipeline python -m partnerhub.generate --inject-anomaly
```
```bash
docker compose run --rm pipeline
```
Résultat : le pipeline **s'arrête**, et dit exactement quoi corriger :
```
globex  globex_opportunities.StageName  Closed-Won  55
PIPELINE FAILED: 1 unknown value(s): add them to dbt/seeds/*_mapping.csv
```

**Pour corriger**, ouvre `dbt/seeds/stage_mapping.csv` dans VS Code, ajoute cette ligne à la fin, puis enregistre :
```
globex,Closed-Won,won
```
Relance :
```bash
docker compose run --rm pipeline
```
Cette fois : `PIPELINE OK`.

Pour revenir aux données normales :
```bash
docker compose run --rm pipeline python -m partnerhub.generate
```

### Démo 2 : chaque client ne voit que ses données
On se connecte comme un analyste :
```bash
docker compose exec postgres psql -U analyst -d partnerhub -c "select count(*) from marts.fct_deals"
```
Résultat : **0**. Sans client choisi, l'analyste ne voit rien.
```bash
docker compose exec postgres psql -U analyst -d partnerhub -c "set app.tenant_id='acme'; select tenant_id, count(*) from marts.fct_deals group by 1"
```
Résultat : **seulement acme**. C'est la *Row-Level Security* de PostgreSQL.

### Démo 3 : les tests automatiques
```bash
docker compose run --rm pipeline pytest -q
```
Résultat : `14 passed`. Sur GitHub, ces tests et tout le pipeline sont relancés **à chaque envoi de code** : c'est le badge vert « CI » en haut du README (voir la section 10).

---

## 7. Les résultats à connaître par cœur

- **Montant des affaires gagnées** : la moyenne (environ 13 000 $) est **1,6 fois** la médiane (environ 8 000 $). Les 10 % plus grosses affaires font **37 %** du chiffre d'affaires.
  → *« Une moyenne seule aurait trompé. Il faut regarder la distribution. »*
- **Durée pour conclure une affaire** (partenaires technologiques) : 94 jours si on ne regarde que les affaires fermées, **106 jours** avec Kaplan-Meier.
  → *« Ignorer les affaires encore ouvertes sous-estime le cycle de vente : c'est un biais de sélection. »*

---

## 8. Arrêter proprement

```bash
docker compose down
```
Pour tout effacer, y compris la base :
```bash
docker compose down -v
```

---

## 9. Problèmes fréquents

| Message | Solution |
|---|---|
| `failed to connect to the docker API` | Docker Desktop n'est pas lancé : ouvre-le et attends la baleine verte. |
| `port is already allocated` | Un autre projet utilise le port : arrête-le avec `docker compose down` dans son dossier. |
| `no configuration file provided` | Tu n'es pas dans le bon dossier : tape `cd $HOME\Downloads\partnerhub-data-platform`. |
| `CRM API unreachable` | Tape `docker compose up -d crm-api`, puis relance le pipeline. |

---

## 10. Utiliser GitHub (sauvegarder et montrer ton travail)

GitHub, c'est un **cahier en ligne** pour ton code. Chaque fois que tu « commites », tu prends une **photo** du projet. Quand tu « pousses », tu envoies ces photos sur Internet, où le recruteur peut les voir.

### 10.1 Les mots à connaître

| Mot | Ce que ça veut dire |
|---|---|
| **dépôt** (*repository*) | Le dossier du projet, suivi par Git |
| **commit** | Une photo du projet à un instant donné, avec un message |
| **push** | Envoyer tes commits sur GitHub |
| **pull** | Récupérer sur ton PC ce qui a changé sur GitHub |
| **clone** | Copier un dépôt GitHub sur ton PC (la première fois) |
| **CI** (*GitHub Actions*) | Un robot qui relance les tests à chaque push |

### 10.2 Une seule fois par ordinateur : dire qui tu es

```bash
git config --global user.name "Isac9"
```
```bash
git config --global user.email "52701548+Isac9@users.noreply.github.com"
```
Cette adresse « noreply » cache ton vrai e-mail aux visiteurs de GitHub.

Ensuite, installe **GitHub CLI** (https://cli.github.com), puis connecte-toi :
```bash
gh auth login
```
Réponds : `GitHub.com`, puis `HTTPS`, puis `Login with a web browser`. Un code s'affiche : colle-le dans la page qui s'ouvre.

### 10.3 Chaque fois que tu modifies le projet (le cycle normal)

1. Modifie un fichier dans VS Code et enregistre (Ctrl + S).
2. Regarde ce qui a changé :
```bash
git status
```
Les fichiers modifiés apparaissent en rouge.

3. Prépare tous les changements pour la photo :
```bash
git add -A
```
4. Prends la photo, avec un message **en anglais** qui dit ce que tu as fait :
```bash
git commit -m "Add mapping for Closed-Won spelling"
```
5. Envoie sur GitHub :
```bash
git push
```

6. Va sur https://github.com/Isac9/partnerhub-data-platform, puis clique sur l'onglet **Actions** :
   - un rond jaune = les tests tournent ;
   - une coche verte ✅ = tout est bon ;
   - une croix rouge ❌ = clique dessus, puis sur l'étape en rouge, pour lire l'erreur.

### 10.4 Si tu travailles sur deux ordinateurs

Avant de commencer, récupère toujours la dernière version :
```bash
git pull
```

### 10.5 Créer un nouveau dépôt sur GitHub (pour un futur projet)

Dans le dossier du nouveau projet :
```bash
git init -b main
```
```bash
git add -A
```
```bash
git commit -m "First version"
```
```bash
gh repo create Isac9/nom-du-projet --public --source . --push
```

### 10.6 Règles d'or

- **Jamais de mot de passe ni de clé** dans le code. Le fichier `.gitignore` liste ce que Git doit ignorer (`.env`, `data/`…).
- **Un commit = une idée.** Commite souvent, avec des messages clairs.
- **Le README est ta vitrine** : c'est la première chose que le recruteur lit.
- **Garde le badge CI vert** : il prouve que ton code est testé.

### 10.7 Erreurs fréquentes

| Message | Solution |
|---|---|
| `Please tell me who you are` | Refais l'étape 10.2. |
| `rejected ... fetch first` | Quelqu'un (ou toi, sur un autre PC) a poussé avant toi : tape `git pull`, puis `git push`. |
| `nothing to commit` | Tu n'as rien modifié, ou tu as oublié d'enregistrer le fichier. |
| `Authentication failed` | Tape `gh auth login`. |

---

## 11. Phrases d'entretien (en anglais)

- *"I built a multi-tenant pipeline that maps three CRMs into one canonical model. Unknown values stop the run instead of being silently dropped."*
- *"Personal data is pseudonymized with a keyed hash before it reaches the warehouse, and a final scan proves no email leaked."*
- *"Every run reconciles row counts and amounts with the source, tenant by tenant."*
- *"For time-to-close I used Kaplan-Meier, because open deals are censored. The naive median was biased low by about 11 days."*
