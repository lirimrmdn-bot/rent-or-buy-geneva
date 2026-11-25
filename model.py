"""Rent or Buy in Geneva - modele de base (groupe 51).

Toutes les grandeurs annuelles en CHF, taux en decimales (0.0185 = 1.85 %).
"""
from dataclasses import dataclass, replace

# Impot genevois sur les benefices et gains immobiliers (IBGI), operations privees
IBGI_TABLE = [(25, 0.00), (10, 0.10), (8, 0.15), (6, 0.20), (4, 0.30), (2, 0.40), (0, 0.50)]


def ibgi_rate(years: int) -> float:
    for threshold, rate in IBGI_TABLE:
        if years >= threshold:
            return rate
    return 0.50


@dataclass
class Params:
    P: float = 1_100_000      # prix d'achat
    e: float = 0.20           # part de fonds propres
    fa: float = 0.05          # frais d'achat (droits + notaire + registre), en % de P
    lam: float = 2 / 3        # part du prix laissee en hypotheque permanente (<= 2/3)
    n_am: int = 15            # duree d'amortissement du 2e rang
    rm: float = 0.0185        # taux hypothecaire
    m: float = 0.01           # entretien + charges PPE, en % de la valeur
    g: float = 0.015          # croissance annuelle de la valeur du bien
    L0: float = 3_000         # loyer mensuel initial
    gL: float = 0.015         # croissance annuelle du loyer
    rf: float = 0.005         # taux sans risque
    tau: float = 0.30         # taux marginal d'imposition du revenu
    s: float = 0.03           # frais de vente, en % du prix de vente
    first_buyer: bool = True  # deduction primo-acquereur (couple marie)
    ded0: float = 10_000      # plafond de la 1re annee
    T: int = 15               # horizon


def simulate(p: Params, T: int | None = None):
    """Renvoie la liste des annees avec W_B, W_R, Delta W (patrimoine en fin d'annee t)."""
    T = p.T if T is None else T
    D0 = (1 - p.e) * p.P
    A = max(D0 - p.lam * p.P, 0) / p.n_am
    rn = p.rf * (1 - p.tau)               # rendement net d'impot du placement
    D, S, B = D0, p.e * p.P + p.fa * p.P, 0.0
    rows = []
    for t in range(1, T + 1):
        V_prev = p.P * (1 + p.g) ** (t - 1)
        interest = p.rm * D
        amort = A if t <= p.n_am else 0.0
        cap = p.ded0 * (1 - (t - 1) / 10) if (p.first_buyer and t <= 10) else 0.0
        tax_saving = p.tau * min(interest, cap)
        CB = interest + amort + p.m * V_prev - tax_saving   # sortie de cash de l'acheteur
        CR = 12 * p.L0 * (1 + p.gL) ** (t - 1)              # loyer annuel
        D -= amort
        S = S * (1 + rn) + max(CB - CR, 0)   # le locataire place ce qu'il economise
        B = B * (1 + rn) + max(CR - CB, 0)   # l'acheteur place ce qu'il economise
        V = p.P * (1 + p.g) ** t
        sale = V * (1 - p.s)
        gain = max(sale - p.P * (1 + p.fa), 0)
        WB = sale - D - ibgi_rate(t) * gain + B
        rows.append(dict(t=t, V=V, D=D, interest=interest, amort=amort, maint=p.m * V_prev,
                         tax_saving=tax_saving, CB=CB, CR=CR, S=S, B=B, gain=gain,
                         ibgi=ibgi_rate(t) * gain, WB=WB, WR=S, dW=WB - S))
    return rows


def delta_W(p: Params, T: int | None = None) -> float:
    return simulate(p, T)[-1]["dW"]


def bisection(f, lo, hi, tol=1e-6, maxit=200):
    flo = f(lo)
    if flo * f(hi) > 0:
        raise ValueError("pas de changement de signe sur l'intervalle")
    for k in range(maxit):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(hi - lo) < tol:
            return mid, k
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2, maxit


def affordability(p: Params, income: float):
    """Charges théoriques selon la pratique des banques : 5 % de la dette + 1 % du prix + amortissement."""
    D0 = (1 - p.e) * p.P
    A = max(D0 - p.lam * p.P, 0) / p.n_am
    cost = 0.05 * D0 + 0.01 * p.P + A
    return cost, cost / income


def check_inputs(p: Params, income: float, pillar2: float = 0.0):
    """Renvoie la liste des regles violees (liste vide = financement possible)."""
    errors = []
    if p.P <= 0 or p.L0 <= 0 or income <= 0:
        errors.append("Le prix, le loyer et le revenu doivent être positifs.")
        return errors
    if p.e < 0.20:
        errors.append(f"Fonds propres de {p.e:.0%} : il faut au moins 20 % du prix (directives ASB).")
    if p.e - pillar2 < 0.10:
        errors.append("Au moins 10 % du prix doit venir d'autres sources que le 2e pilier (directives ASB).")
    if p.lam > 2 / 3 + 1e-9:
        errors.append("La part laissée en hypothèque ne peut pas dépasser 2/3 du prix.")
    if p.lam > 1 - p.e + 1e-9:
        errors.append("La part laissée en hypothèque ne peut pas dépasser la dette de départ.")
    _, ratio = affordability(p, income)
    if ratio > 1 / 3:
        errors.append(f"Charges théoriques = {ratio:.1%} du revenu brut : la limite des banques est 1/3.")
    return errors
