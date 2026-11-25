"""Rent or Buy in Geneva - application Streamlit (groupe 51).

Lancer avec :  streamlit run app.py
"""
from dataclasses import replace

import altair as alt
import pandas as pd
import streamlit as st

from model import Params, affordability, bisection, check_inputs, delta_W, simulate

st.set_page_config(page_title="Rent or Buy in Geneva", layout="wide")


def chf(x: float) -> str:
    return f"CHF {x:,.0f}".replace(",", "’")


# ---------------------------------------------------------------- saisies
st.sidebar.title("Vos données")

st.sidebar.subheader("Le logement")
P = st.sidebar.number_input("Prix d'achat (CHF)", 100_000, 10_000_000, 1_200_000, step=10_000)
L0 = st.sidebar.number_input("Loyer mensuel d'un logement équivalent (CHF)", 300, 20_000, 2_700, step=50)

st.sidebar.subheader("Le ménage")
income = st.sidebar.number_input("Revenu brut annuel du ménage (CHF)", 10_000, 5_000_000, 220_000, step=5_000)
e_pct = st.sidebar.slider("Fonds propres (% du prix)", 10, 100, 20,
                          help="Minimum légal pratique : 20 %. En dessous, l'outil refuse la simulation.")
p2_pct = st.sidebar.slider("dont 2e pilier (% du prix)", 0, 20, 0,
                           help="Au moins 10 % du prix doit venir d'ailleurs que du 2e pilier.")
tau_pct = st.sidebar.slider("Taux marginal d'imposition (%)", 0, 50, 30)
first_buyer = st.sidebar.checkbox("Primo-acquéreurs (couple marie)", value=True,
                                  help="Déduction des intérêts jusqu'a CHF 10 000 la 1re année, en baisse sur 10 ans (réforme 2029).")

st.sidebar.subheader("Le financement")
lam_pct = st.sidebar.slider("Part du prix laissée en hypothèque permanente (%)", 0, 67, 67,
                            help="Le 2e rang (au-delà de 2/3) doit être amorti en 15 ans. Plus cette part est basse, plus on rembourse.")
rm_pct = st.sidebar.slider("Taux hypothécaire (%)", 0.0, 6.0, 1.85, 0.05)

st.sidebar.subheader("Les hypothèses de marché")
g_pct = st.sidebar.slider("Hausse annuelle de la valeur du bien (%)", -3.0, 5.0, 1.0, 0.1)
gL_pct = st.sidebar.slider("Hausse annuelle des loyers (%)", -2.0, 5.0, 1.0, 0.1)
rf_pct = st.sidebar.slider("Rendement de l'épargne, taux sans risque (%)", 0.0, 5.0, 0.5, 0.05)
T = st.sidebar.slider("Horizon (années)", 1, 30, 15)

with st.sidebar.expander("Frais (avancé)"):
    fa_pct = st.number_input("Frais d'achat (% du prix)", 0.0, 10.0, 5.0, 0.5)
    s_pct = st.number_input("Frais de vente (% du prix de vente)", 0.0, 10.0, 3.0, 0.5)
    m_pct = st.number_input("Entretien et charges (% de la valeur par an)", 0.0, 5.0, 1.0, 0.1)

p = Params(P=P, e=e_pct / 100, fa=fa_pct / 100, lam=min(lam_pct / 100, 2 / 3), rm=rm_pct / 100,
           m=m_pct / 100, g=g_pct / 100, L0=L0, gL=gL_pct / 100, rf=rf_pct / 100, tau=tau_pct / 100,
           s=s_pct / 100, first_buyer=first_buyer, T=T)

# ---------------------------------------------------------------- en-tete
st.title("Rent or Buy in Geneva")
st.caption("Faut-il acheter ou louer son logement à Genève ? Comparaison du patrimoine net des deux options, "
           "cadre fiscal 2029 (sans valeur locative). Outil pédagogique, pas un conseil financier.")

errors = check_inputs(p, income, p2_pct / 100)
cost, ratio = affordability(p, income)
if errors:
    st.error("**Financement impossible avec ces données.**\n\n" + "\n".join(f"- {m}" for m in errors))
    st.info("Corrigez les valeurs dans le panneau de gauche : apport, revenu, prix ou part d'hypothèque.")
    st.stop()

# ---------------------------------------------------------------- calculs
rows = simulate(p, 30)
df = pd.DataFrame(rows)
dW_T = df.loc[df.t == T, "dW"].item()
be_year = next((r["t"] for r in rows if r["dW"] >= 0), None)

try:
    L_star, n_it = bisection(lambda L: delta_W(replace(p, L0=L), T), 50, 50_000, tol=0.01)
except ValueError:
    L_star, n_it = None, 0

# ---------------------------------------------------------------- resultat principal
verdict = "Acheter" if dW_T >= 0 else "Louer"
st.subheader(f"Sur {T} ans : **{verdict}** est plus avantageux de {chf(abs(dW_T))}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Année d'équilibre", f"{be_year} ans" if be_year else "Jamais (sur 30 ans)",
          help="Première année où le patrimoine de l'acheteur depasse celui du locataire.")
c2.metric(f"Écart de patrimoine à {T} ans", chf(dW_T), help="Patrimoine de l'acheteur moins celui du locataire.")
c3.metric("Loyer d'équilibre (par mois)", chf(L_star) if L_star else "hors limites",
          help=f"Loyer à partir duquel acheter devient gagnant à {T} ans (bissection, {n_it} itérations).")
c4.metric("Charges théoriques / revenu", f"{ratio:.1%}", help=f"{chf(cost)} par an. Limite des banques : 33,3 %.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Patrimoine", "Scénario alternatif", "Sensibilité", "Détail année par année", "Hypothèses"])

# ---------------------------------------------------------------- onglet 1
with tab1:
    long = pd.concat([
        pd.DataFrame({"Année": df.t, "Patrimoine (CHF)": df.WB, "Option": "Acheteur"}),
        pd.DataFrame({"Année": df.t, "Patrimoine (CHF)": df.WR, "Option": "Locataire"}),
    ])
    lines = alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("Année:Q", scale=alt.Scale(domain=[1, 30])),
        y=alt.Y("Patrimoine (CHF):Q", axis=alt.Axis(format=",.0f")),
        color=alt.Color("Option:N", scale=alt.Scale(range=["#2563eb", "#9ca3af"])),
        tooltip=["Option", "Année", alt.Tooltip("Patrimoine (CHF):Q", format=",.0f")],
    )
    rule = alt.Chart(pd.DataFrame({"Année": [T]})).mark_rule(strokeDash=[4, 4], color="black").encode(x="Année:Q")
    st.altair_chart((lines + rule).properties(height=420), width="stretch")
    st.caption("Patrimoine net en fin d'année si l'on arrête à cette date (vente du bien pour l'acheteur). "
               "La ligne pointillée marque votre horizon.")
    r1 = rows[0]
    st.markdown(
        f"**Première année :** l'acheteur sort {chf(r1['CB'])} (intérêts {chf(r1['interest'])}, "
        f"amortissement {chf(r1['amort'])}, entretien {chf(r1['maint'])}, économie d'impôt -{chf(r1['tax_saving'])}), "
        f"le locataire paie {chf(r1['CR'])} de loyer. L'amortissement n'est pas une perte : il réduit la dette."
    )

# ---------------------------------------------------------------- onglet 2
with tab2:
    st.write("Changez une ou deux hypothèses pour comparer avec le scénario de base.")
    a1, a2, a3 = st.columns(3)
    g_alt = a1.slider("Hausse de la valeur du bien (%) – alternatif", -3.0, 5.0, 0.0, 0.1)
    rm_alt = a2.slider("Taux hypothécaire (%) – alternatif", 0.0, 6.0, 3.0, 0.05)
    rf_alt = a3.slider("Rendement de l'épargne (%) – alternatif", 0.0, 8.0, rf_pct, 0.05)
    p_alt = replace(p, g=g_alt / 100, rm=rm_alt / 100, rf=rf_alt / 100)
    rows_alt = simulate(p_alt, 30)
    comp = pd.concat([
        pd.DataFrame({"Année": df.t, "Écart acheteur – locataire (CHF)": df.dW, "Scénario": "Base"}),
        pd.DataFrame({"Année": [r["t"] for r in rows_alt], "Écart acheteur – locataire (CHF)": [r["dW"] for r in rows_alt],
                      "Scénario": "Alternatif"}),
    ])
    ch = alt.Chart(comp).mark_line(point=True).encode(
        x="Année:Q", y=alt.Y("Écart acheteur – locataire (CHF):Q", axis=alt.Axis(format=",.0f")),
        color=alt.Color("Scénario:N", scale=alt.Scale(range=["#2563eb", "#f59e0b"])),
        tooltip=["Scénario", "Année", alt.Tooltip("Écart acheteur – locataire (CHF):Q", format=",.0f")],
    )
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="black").encode(y="y:Q")
    st.altair_chart((ch + zero).properties(height=380), width="stretch")
    dW_alt = rows_alt[T - 1]["dW"]
    be_alt = next((r["t"] for r in rows_alt if r["dW"] >= 0), None)
    st.markdown(
        f"Au-dessus de zéro, acheter est mieux. À {T} ans : base {chf(dW_T)}, alternatif {chf(dW_alt)}. "
        f"Année d'équilibre : base {be_year or 'jamais'}, alternatif {be_alt or 'jamais'}."
    )

# ---------------------------------------------------------------- onglet 3
with tab3:
    st.write(f"Comment l'écart de patrimoine à {T} ans réagit à une hausse de 1 point de pourcentage de chaque hypothèse. "
             "On compare l'approximation de Taylor (ordre 1 et 2) au recalcul complet du modèle.")
    base = delta_W(p, T)
    h, H = 1e-4, 0.01
    labels = {"g": "Hausse de la valeur du bien", "rm": "Taux hypothécaire",
              "gL": "Hausse des loyers", "rf": "Rendement de l'épargne"}
    out = []
    for name, lab in labels.items():
        x = getattr(p, name)
        up = delta_W(replace(p, **{name: x + h}), T)
        dn = delta_W(replace(p, **{name: x - h}), T)
        d1, d2 = (up - dn) / (2 * h), (up - 2 * base + dn) / h ** 2
        full = delta_W(replace(p, **{name: x + H}), T)
        t1, t2 = base + d1 * H, base + d1 * H + 0.5 * d2 * H ** 2
        out.append({"Hypothèse (+1 pp)": lab, "Dérivée × 0,01 (CHF)": d1 * H, "Taylor ordre 1": t1,
                    "Taylor ordre 2": t2, "Recalcul complet": full, "Erreur ordre 1": t1 - full})
    sens = pd.DataFrame(out)
    st.dataframe(sens.style.format({c: "{:,.0f}" for c in sens.columns if c != "Hypothèse (+1 pp)"}),
                 hide_index=True, width="stretch")
    st.caption(f"Valeur de départ : {chf(base)}. Dérivées par différences finies centrées (h = 0,01 pp).")

# ---------------------------------------------------------------- onglet 4
with tab4:
    show = df[["t", "V", "D", "interest", "amort", "maint", "tax_saving", "CB", "CR", "B", "ibgi", "WB", "WR", "dW"]].copy()
    show.columns = ["Année", "Valeur du bien", "Dette", "Intérêts", "Amortissement", "Entretien", "Économie d'impôt",
                    "Sortie acheteur", "Loyer annuel", "Épargne acheteur", "IBGI si vente", "Patrimoine acheteur",
                    "Patrimoine locataire", "Écart"]
    st.dataframe(show.style.format({c: "{:,.0f}" for c in show.columns if c != "Année"}),
                 hide_index=True, width="stretch", height=500)
    st.download_button("Télécharger en CSV", show.to_csv(index=False).encode("utf-8"), "rent_or_buy.csv", "text/csv")

# ---------------------------------------------------------------- onglet 5
with tab5:
    st.markdown("""
**Règles appliquées**
- Fonds propres : au moins 20 % du prix, dont au moins 10 % hors 2e pilier ; la dette doit redescendre à 2/3 du prix en 15 ans (directives de l'Association suisse des banquiers).
- Capacité financière : 5 % de la dette + 1 % du prix + amortissement <= 1/3 du revenu brut (pratique des banques).
- Fiscalité dès 2029 : plus de valeur locative, plus de déduction des intérêts ni de l'entretien ; déduction dégressive sur 10 ans pour les primo-acquéreurs (CHF 10 000 la 1re année pour un couple marié).
- Impôt genevois sur le gain immobilier (IBGI) : 50 % avant 2 ans, puis 40, 30, 20, 15, 10 % ; 0 % dès 25 ans.

**Ce que l'outil ne fait pas encore**
- Prix et loyer saisis à la main (la régression par commune arrive à l'étape suivante).
- Taux hypothécaire constant sur tout l'horizon ; pas d'impôt sur la fortune ; pas de réduction Casatax.
- Le locataire place son épargne au taux sans risque, net d'impôt : c'est prudent et défavorise la location.
""")
