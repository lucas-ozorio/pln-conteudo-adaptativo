"""Estatística compartilhada pelas análises offline novas (scripts 10+).

Mesma lógica de scripts/08_cluster_bootstrap.py (bootstrap por QUESTÃO) e de scripts/05_analyze.py (Holm).
Esses scripts não importam daqui de propósito: assim os números já publicados no artigo não mudam.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def cluster_ci(valores, grupos, B: int = 5000, seed: int = 0, stat=np.mean) -> dict:
    """Estatística (média, por padrão) com IC95% por bootstrap de clusters e p bilateral (centrado em 0).

    valores: Series indexada por item; grupos: Series item -> questão (cluster).
    """
    d = pd.Series(valores).dropna()
    g = pd.Series(grupos).reindex(d.index)
    by = {k: v.values for k, v in d.groupby(g)}
    ks = np.array(list(by))
    if len(d) == 0:
        return dict(est=np.nan, lo=np.nan, hi=np.nan, p_boot=np.nan, n=0, n_questoes=0)
    rng = np.random.default_rng(seed)
    bs = np.array([stat(np.concatenate([by[k] for k in rng.choice(ks, len(ks), replace=True)])) for _ in range(B)])
    lo, hi = np.quantile(bs, [0.025, 0.975])
    p = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
    return dict(est=float(stat(d.values)), lo=float(lo), hi=float(hi), p_boot=float(p), n=len(d), n_questoes=len(ks))


def cluster_boot(df: pd.DataFrame, grupo: str, fn, B: int = 2000, seed: int = 0) -> dict:
    """IC95% por bootstrap de clusters para uma estatística arbitrária fn(DataFrame) -> número.

    Útil para correlações e coeficientes de regressão (reamostra questões inteiras).
    """
    by = {k: g for k, g in df.groupby(grupo)}
    ks = np.array(list(by))
    rng = np.random.default_rng(seed)
    est = float(fn(df))
    bs = []
    for _ in range(B):
        s = pd.concat([by[k] for k in rng.choice(ks, len(ks), replace=True)], ignore_index=True)
        v = fn(s)
        if np.isfinite(v):
            bs.append(v)
    bs = np.array(bs)
    lo, hi = np.quantile(bs, [0.025, 0.975])
    p = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
    return dict(est=est, lo=float(lo), hi=float(hi), p_boot=float(p), n=len(df), n_questoes=len(ks))


def holm(ps) -> np.ndarray:
    """p-valores ajustados por Holm (controle do erro por família)."""
    ps = np.asarray(ps, float)
    order = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Proporção com IC de Wilson (para a auditoria manual, sem estrutura de cluster)."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return (p, max(0.0, c - h), min(1.0, c + h))  # corta o ruído de ponto flutuante (ex.: -2.8e-17 quando k = 0)
