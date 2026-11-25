# Rent or Buy in Geneva — groupe 51

Outil interactif qui compare, pour un ménage genevois, le patrimoine net s'il achète son logement ou s'il continue à louer, dans le cadre fiscal de 2029 (sans valeur locative).

## Lancer l'application

Il faut Python 3.10 ou plus récent.

1. Ouvrir un terminal dans ce dossier.
2. Installer les bibliothèques (une seule fois) :

   ```
   pip install -r requirements.txt
   ```

3. Lancer l'application :

   ```
   streamlit run app.py
   ```

4. Le navigateur s'ouvre sur http://localhost:8501. Sinon, ouvrir cette adresse à la main.

## Utiliser l'outil

- Le panneau de gauche contient toutes les données : prix, loyer, revenu, fonds propres, taux, hypothèses de marché et horizon.
- Si le financement ne respecte pas les règles des banques (fonds propres < 20 %, moins de 10 % hors 2e pilier, charges > 1/3 du revenu), l'outil affiche la règle violée et ne calcule pas.
- Les onglets montrent : l'évolution des deux patrimoines, un scénario alternatif, l'analyse de sensibilité (Taylor contre recalcul complet), le détail année par année (téléchargeable en CSV) et les hypothèses.

## Fichiers

| Fichier | Contenu |
| --- | --- |
| `app.py` | L'interface Streamlit |
| `model.py` | Le modèle : récurrences, bissection, règles de financement |
| `example.py` | Recalcule l'exemple du document (étape 1) et les vérifications |
| `requirements.txt` | Les bibliothèques nécessaires |

## Prochaines étapes

- Remplacer le prix et le loyer saisis à la main par la régression par commune (étape 2, données).
- Remplacer le taux sans risque provisoire (0,5 %) par la donnée de la BNS.
