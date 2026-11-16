# Resultados iniciais

## E0 — Diagnóstico vs nota-ouro (PT-ASAG)
| n | QWK | Spearman | MAE | acc_exata | acc_binaria(>=2) | concept_P(proxy) | concept_R(proxy) |
|---|---|---|---|---|---|---|---|
| 595 | 0.487 | 0.580 | 0.703 | 0.429 | 0.677 | 0.375 | 0.967 |

Referência de teto: no PT-ASAG original, a concordância entre avaliadores humanos foi r=0,581 (Pearson) nas respostas duplamente avaliadas (Galhardi et al., 2018).
As colunas `concept_*(proxy)` comparam o diagnóstico com presença lexical da palavra-chave: proxy fraco, não é anotação de conceito.

Matriz de confusão:
```
        pred=0  pred=1  pred=2  pred=3
ouro=0      85      63       2       0
ouro=1      16     107      27       0
ouro=2       7      89      52       2
ouro=3       2      65      67      11
```

## E1 — Qualidade do material (juiz LLM, 1–5; IC95% bootstrap por item)
| condicao | n | palavras | coerencia | correcao_conceitual | fidelidade_gabarito | foco_na_lacuna | utilidade_pedagogica | adequacao_nivel | afirmacoes_incorretas | q_alinhamento | q_clareza | q_relevancia | q_resp_correta | q_bloom_match |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0_gabarito | 180 | 83.933 | 3.66 [3.48; 3.84] | 4.21 [4.01; 4.40] | 3.72 [3.49; 3.94] | 1.33 [1.18; 1.48] | 1.76 [1.62; 1.91] | 4.04 [3.90; 4.18] | 0.18 [0.11; 0.26] | — | — | — | — | — |
| S_estatico | 180 | 158.933 | 4.82 [4.74; 4.89] | 4.91 [4.82; 4.98] | 4.60 [4.47; 4.72] | 3.79 [3.59; 4.00] | 4.22 [4.06; 4.39] | 4.85 [4.79; 4.91] | 0.04 [0.01; 0.08] | 4.67 [4.61; 4.73] | 4.84 [4.79; 4.87] | 4.19 [4.11; 4.28] | 1.00 [1.00; 1.00] | 0.98 [0.96; 0.99] |
| A0_direto | 180 | 120.489 | 4.79 [4.71; 4.87] | 4.93 [4.87; 4.98] | 4.73 [4.63; 4.81] | 4.57 [4.42; 4.71] | 4.62 [4.47; 4.74] | 4.87 [4.80; 4.92] | 0.02 [0.00; 0.04] | 4.73 [4.68; 4.77] | 4.88 [4.85; 4.91] | 4.31 [4.23; 4.38] | 1.00 [0.99; 1.00] | 0.97 [0.95; 0.99] |
| A1_pipeline | 180 | 158.528 | 4.92 [4.88; 4.96] | 4.95 [4.91; 4.99] | 4.74 [4.66; 4.82] | 4.59 [4.45; 4.72] | 4.74 [4.63; 4.83] | 4.97 [4.93; 4.99] | 0.01 [0.00; 0.02] | 4.80 [4.76; 4.84] | 4.82 [4.77; 4.86] | 4.43 [4.35; 4.51] | 1.00 [1.00; 1.00] | 0.97 [0.95; 0.99] |
| A2_pipeline_verif | 180 | 144.550 | 4.93 [4.89; 4.96] | 4.98 [4.96; 5.00] | 4.79 [4.72; 4.86] | 4.67 [4.54; 4.78] | 4.79 [4.69; 4.87] | 4.97 [4.94; 4.99] | 0.01 [0.00; 0.02] | 4.80 [4.75; 4.85] | 4.84 [4.79; 4.87] | 4.46 [4.38; 4.54] | 1.00 [0.99; 1.00] | 0.98 [0.96; 0.99] |

### Contrastes pareados (diferença média, IC95%, Wilcoxon, efeito r rank-biserial, p ajustado por Holm)
| contraste | dimensao | n | diff | lo | hi | r_rb | p | p_holm |
|---|---|---|---|---|---|---|---|---|
| A1_pipeline − S_estatico | coerencia | 180 | 0.106 | 0.022 | 0.194 | 0.444 | 0.017 | 0.543 |
| A1_pipeline − S_estatico | correcao_conceitual | 180 | 0.044 | -0.044 | 0.144 | 0.282 | 0.424 | 1.000 |
| A1_pipeline − S_estatico | fidelidade_gabarito | 180 | 0.144 | 0.006 | 0.278 | 0.273 | 0.045 | 1.000 |
| A1_pipeline − S_estatico | foco_na_lacuna | 180 | 0.800 | 0.555 | 1.028 | 0.642 | 0.000 | 0.000 |
| A1_pipeline − S_estatico | utilidade_pedagogica | 180 | 0.517 | 0.328 | 0.694 | 0.610 | 0.000 | 0.000 |
| A1_pipeline − S_estatico | adequacao_nivel | 180 | 0.117 | 0.050 | 0.189 | 0.677 | 0.002 | 0.064 |
| A1_pipeline − S_estatico | afirmacoes_incorretas | 180 | -0.033 | -0.078 | 0.006 | -0.800 | 0.188 | 1.000 |
| A1_pipeline − S_estatico | q_alinhamento | 180 | 0.131 | 0.065 | 0.193 | 0.408 | 0.001 | 0.021 |
| A1_pipeline − S_estatico | q_clareza | 180 | -0.015 | -0.070 | 0.043 | -0.077 | 0.561 | 1.000 |
| A1_pipeline − S_estatico | q_relevancia | 180 | 0.239 | 0.161 | 0.311 | 0.524 | 0.000 | 0.000 |
| A1_pipeline − S_estatico | q_resp_correta | 180 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| A1_pipeline − S_estatico | q_bloom_match | 180 | -0.007 | -0.028 | 0.013 | -0.120 | 0.564 | 1.000 |
| A1_pipeline − A0_direto | coerencia | 180 | 0.128 | 0.044 | 0.222 | 0.534 | 0.005 | 0.171 |
| A1_pipeline − A0_direto | correcao_conceitual | 180 | 0.017 | -0.050 | 0.094 | 0.136 | 0.715 | 1.000 |
| A1_pipeline − A0_direto | fidelidade_gabarito | 180 | 0.017 | -0.083 | 0.117 | 0.090 | 0.577 | 1.000 |
| A1_pipeline − A0_direto | foco_na_lacuna | 180 | 0.022 | -0.150 | 0.189 | 0.045 | 0.779 | 1.000 |
| A1_pipeline − A0_direto | utilidade_pedagogica | 180 | 0.122 | -0.028 | 0.278 | 0.248 | 0.128 | 1.000 |
| A1_pipeline − A0_direto | adequacao_nivel | 180 | 0.100 | 0.039 | 0.172 | 0.684 | 0.006 | 0.226 |
| A1_pipeline − A0_direto | afirmacoes_incorretas | 180 | -0.011 | -0.044 | 0.011 | -0.500 | 0.750 | 1.000 |
| A1_pipeline − A0_direto | q_alinhamento | 180 | 0.074 | 0.020 | 0.130 | 0.294 | 0.014 | 0.464 |
| A1_pipeline − A0_direto | q_clareza | 180 | -0.057 | -0.111 | -0.004 | -0.265 | 0.045 | 1.000 |
| A1_pipeline − A0_direto | q_relevancia | 180 | 0.120 | 0.043 | 0.191 | 0.271 | 0.007 | 0.239 |
| A1_pipeline − A0_direto | q_resp_correta | 180 | 0.002 | 0.000 | 0.006 | 1.000 | 1.000 | 1.000 |
| A1_pipeline − A0_direto | q_bloom_match | 180 | -0.002 | -0.024 | 0.020 | -0.043 | 0.849 | 1.000 |
| A2_pipeline_verif − A1_pipeline | coerencia | 180 | 0.006 | -0.039 | 0.050 | 0.067 | 0.808 | 1.000 |
| A2_pipeline_verif − A1_pipeline | correcao_conceitual | 180 | 0.033 | 0.006 | 0.072 | 1.000 | 0.125 | 1.000 |
| A2_pipeline_verif − A1_pipeline | fidelidade_gabarito | 180 | 0.050 | -0.022 | 0.133 | 0.233 | 0.253 | 1.000 |
| A2_pipeline_verif − A1_pipeline | foco_na_lacuna | 180 | 0.078 | -0.033 | 0.200 | 0.228 | 0.254 | 1.000 |
| A2_pipeline_verif − A1_pipeline | utilidade_pedagogica | 180 | 0.050 | -0.056 | 0.161 | 0.228 | 0.312 | 1.000 |
| A2_pipeline_verif − A1_pipeline | adequacao_nivel | 180 | 0.000 | -0.033 | 0.039 | 0.000 | 1.000 | 1.000 |
| A2_pipeline_verif − A1_pipeline | afirmacoes_incorretas | 180 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| A2_pipeline_verif − A1_pipeline | q_alinhamento | 180 | 0.004 | -0.041 | 0.046 | 0.005 | 0.978 | 1.000 |
| A2_pipeline_verif − A1_pipeline | q_clareza | 180 | 0.015 | -0.031 | 0.061 | 0.112 | 0.530 | 1.000 |
| A2_pipeline_verif − A1_pipeline | q_relevancia | 180 | 0.031 | -0.022 | 0.087 | 0.155 | 0.234 | 1.000 |
| A2_pipeline_verif − A1_pipeline | q_resp_correta | 180 | -0.004 | -0.009 | 0.000 | -1.000 | 0.500 | 1.000 |
| A2_pipeline_verif − A1_pipeline | q_bloom_match | 180 | 0.006 | -0.009 | 0.022 | 0.143 | 0.807 | 1.000 |
| A1_pipeline − S0_gabarito | coerencia | 180 | 1.261 | 1.078 | 1.444 | 0.987 | 0.000 | 0.000 |
| A1_pipeline − S0_gabarito | correcao_conceitual | 180 | 0.744 | 0.556 | 0.944 | 0.970 | 0.000 | 0.000 |
| A1_pipeline − S0_gabarito | fidelidade_gabarito | 180 | 1.028 | 0.800 | 1.244 | 0.897 | 0.000 | 0.000 |
| A1_pipeline − S0_gabarito | foco_na_lacuna | 180 | 3.267 | 3.072 | 3.461 | 1.000 | 0.000 | 0.000 |
| A1_pipeline − S0_gabarito | utilidade_pedagogica | 180 | 2.983 | 2.817 | 3.139 | 1.000 | 0.000 | 0.000 |
| A1_pipeline − S0_gabarito | adequacao_nivel | 180 | 0.928 | 0.789 | 1.072 | 0.983 | 0.000 | 0.000 |
| A1_pipeline − S0_gabarito | afirmacoes_incorretas | 180 | -0.172 | -0.250 | -0.106 | -0.947 | 0.000 | 0.001 |
| A1_pipeline − S0_gabarito | q_alinhamento | 0 | nan | nan | nan | nan | nan | 1.000 |
| A1_pipeline − S0_gabarito | q_clareza | 0 | nan | nan | nan | nan | nan | 1.000 |
| A1_pipeline − S0_gabarito | q_relevancia | 0 | nan | nan | nan | nan | nan | 1.000 |
| A1_pipeline − S0_gabarito | q_resp_correta | 0 | nan | nan | nan | nan | nan | 1.000 |
| A1_pipeline − S0_gabarito | q_bloom_match | 0 | nan | nan | nan | nan | nan | 1.000 |

### Viés de verbosidade do juiz (coef. ≈ 0 e Spearman baixo indicam pouca influência do tamanho)
| dimensao | spearman(palavras,nota) | coef_log_palavras|condicao |
|---|---|---|
| coerencia | 0.315 | 0.185 |
| correcao_conceitual | 0.231 | -0.177 |
| fidelidade_gabarito | 0.134 | -0.307 |
| foco_na_lacuna | 0.296 | -0.152 |
| utilidade_pedagogica | 0.372 | 0.086 |
| adequacao_nivel | 0.285 | -0.111 |

### Efeito da adaptação por nota-ouro do aluno
| nota_ouro | A1−S foco_na_lacuna | A1−S utilidade | n |
|---|---|---|---|
| 0 | 0.417 | 0.217 | 60 |
| 1 | 1.133 | 0.733 | 60 |
| 2 | 0.850 | 0.600 | 60 |

### A2 — verificação ancorada no gabarito
afirmações/texto: 8.3; com problema (não suportada/incorreta): 1.21/texto; textos reescritos: 73.9%; afirmações incorretas/texto: 0.01

### Comparação par-a-par (duas ordens; 'robusta' = mesmo vencedor nas duas ordens)
x é o 1º item do par. `viés_posição`=0,5 e `mais_longo_vence`=0,5 indicam ausência de viés de posição e de verbosidade.
| par | itens | vitória robusta x | vitória robusta y | inconsistente/empate | p(sinal, robustas) | viés_posição(1º vence) | consistência_ordem | mais_longo_vence |
|---|---|---|---|---|---|---|---|---|
| A1_pipeline vs A0_direto | 180 | 0.189 | 0.078 | 0.733 | 0.006 | 0.134 | 0.267 | 0.560 |
| A1_pipeline vs S0_gabarito | 180 | 0.667 | 0.067 | 0.267 | 0.000 | 0.479 | 0.733 | 0.786 |
| A1_pipeline vs S_estatico | 180 | 0.133 | 0.094 | 0.772 | 0.349 | 0.115 | 0.233 | 0.513 |
| A2_pipeline_verif vs A1_pipeline | 180 | 0.072 | 0.217 | 0.711 | 0.000 | 0.314 | 0.633 | 0.627 |

## E3 (exploratório) — Ganho com aluno simulado
Sanidade do corretor: QWK(nota do corretor na resposta original, nota-ouro) = 0.597 (n=180)

| condicao | n | ganho_medio | ic_lo | ic_hi |
|---|---|---|---|---|
| A0_direto | 180 | 1.283 | 1.122 | 1.444 |
| A1_pipeline | 180 | 1.439 | 1.294 | 1.589 |
| A2_pipeline_verif | 180 | 1.394 | 1.244 | 1.544 |
| N_sem_material | 180 | 0.450 | 0.311 | 0.589 |
| S0_gabarito | 180 | 1.217 | 1.050 | 1.383 |
| S_estatico | 180 | 1.294 | 1.117 | 1.478 |

Contrastes de ganho (pareados por item):
| contraste | n | diff | lo | hi | r_rb | p | p_holm |
|---|---|---|---|---|---|---|---|
| A0_direto − N_sem_material | 180 | 0.833 | 0.678 | 0.972 | 0.836 | 0.000 | 0.000 |
| A1_pipeline − N_sem_material | 180 | 0.989 | 0.850 | 1.122 | 0.942 | 0.000 | 0.000 |
| A2_pipeline_verif − N_sem_material | 180 | 0.944 | 0.806 | 1.083 | 0.945 | 0.000 | 0.000 |
| S0_gabarito − N_sem_material | 180 | 0.767 | 0.611 | 0.928 | 0.763 | 0.000 | 0.000 |
| S_estatico − N_sem_material | 180 | 0.844 | 0.700 | 0.994 | 0.842 | 0.000 | 0.000 |
| A1_pipeline − S_estatico | 180 | 0.144 | 0.022 | 0.272 | 0.281 | 0.046 | 0.122 |
| A1_pipeline − A0_direto | 180 | 0.156 | 0.022 | 0.294 | 0.310 | 0.041 | 0.122 |
| A2_pipeline_verif − A1_pipeline | 180 | -0.044 | -0.144 | 0.050 | -0.112 | 0.501 | 0.501 |
| A1_pipeline − S0_gabarito | 180 | 0.222 | 0.089 | 0.356 | 0.448 | 0.002 | 0.009 |

Atenção: LLM simulando aluno tende a 'aprender' mais do que alunos reais e já conhece a matéria; interprete apenas o ganho RELATIVO a N_sem_material e as diferenças entre condições.