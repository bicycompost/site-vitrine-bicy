# Site vitrine Bicy — www.bicycompost.fr

Copie autonome (HTML / CSS / JS) du site anciennement hébergé sur Webflow.
Aucune base de données, aucun serveur applicatif : de simples fichiers à déposer chez OVH.

## Organisation

| Dossier | Contenu |
|---|---|
| `site/` | **Le site en ligne** : c'est ce dossier qui est envoyé sur OVH (dans `www/`). |
| `site/*.html` | Une page = un fichier (`site/blog/xxx.html` = www.bicycompost.fr/blog/xxx). |
| `site/assets/medias/` | Images, PDF, polices, CSS et JS rapatriés de Webflow. |
| `site/.htaccess` | Adresses sans `.html`, HTTPS + www forcés, page 404, cache. |
| `outils/apercu.py` | Aperçu local : `python3 outils/apercu.py` puis http://localhost:8000 |
| `outils/optimiser_images.py` | Allège les images (WebP) et les polices (WOFF2) : à relancer après ajout de nouvelles images. |
| `outils/construire_site.py` | Script qui a converti la copie Webflow (utile seulement pour refaire une copie). |

## Mettre à jour le site

1. Demander la modification à Claude (ou modifier le fichier HTML concerné).
2. La modification arrive sur la branche `main`.
3. GitHub envoie automatiquement `site/` sur OVH (workflow `.github/workflows/deploiement-ovh.yml`).

Prérequis une seule fois : créer les secrets `OVH_FTP_SERVER`, `OVH_FTP_USER`,
`OVH_FTP_PASSWORD` dans GitHub (Settings → Secrets and variables → Actions).

## Points à traiter avant la bascule

- **Formulaires** (newsletter du pied de page, contact, « Estimer mon besoin ») :
  ils envoient encore leurs données à Webflow et ne fonctionneront plus une fois
  Webflow coupé. À rebrancher sur un service de formulaires (Tally, Formspree…) ou un petit script PHP OVH.
- **Mentions légales** : la rubrique hébergeur cite encore Webflow → mettre OVH.
- **DNS** : chez Ionos, faire pointer `www` et le domaine nu vers l'hébergement OVH.
- Liens déjà cassés sur le site Webflow d'origine (conservés tels quels) : /contact, /offres,
  /bicyarche, /que-peut-on-composter, /le-blog-du-compostage, etc.
