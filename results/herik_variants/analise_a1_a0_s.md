# H-03 / H-04 — A1 (pipeline com diagnóstico) vs A0 (direto) vs S (estático)

> Gerado por `scripts/analyze_variants_a1_a0_s.py` (100% offline, sem chamadas de API). Fontes: `results/e1_juiz_absoluto_por_item.csv`, `outputs/materials.jsonl`, `outputs/judgments_pair.jsonl`, `outputs/diagnosis.jsonl`. n = 180 itens (15 questões × 12 respostas; nota-ouro 0/1/2 balanceada). Juiz: `gemini-2.5-flash`; gerador: `gpt-4o-mini`. Como os 180 itens vêm de 15 questões, os ICs principais são por **bootstrap de questão** (cluster, B=5000) e as regressões usam EP robusto por questão; resultados por estrato são exploratórios (n pequeno, sem correção de multiplicidade). A nota estimada embutida no A1 coincide com `diagnosis.jsonl` em 100% dos itens.

## Resumo executivo

1. **Tamanho não explica a vantagem nominal de A1 sobre A0 — mas essa vantagem já é pequena.** A1 é mais longo que A0 em 99.4% dos itens (Δ mediano 37 palavras), então condição e tamanho quase se confundem no contraste A1×A0. Três controles apontam na mesma direção: (a) o coeficiente de log(palavras) com efeito fixo de item não é significativo em nenhuma dimensão (e é negativo em 7 de 9); (b) Δnota(A1−A0) não varia com Δpalavras (Spearman |ρ| ≤ 0.11) e é igual nos três tercis de Δpalavras; (c) S tem o mesmo tamanho de A1 (~159) e fica **abaixo** do A0 (~120) em foco e utilidade. Com controle, a estimativa pontual de A1−A0 não encolhe, mas o IC alarga e nenhuma dimensão fica significativa.
2. **O que é robusto é A1/A0 > S (adaptação), não A1 > A0 (diagnóstico explícito).** Foco na lacuna: A1−S = +0.80 e A0−S = +0.78, contra A1−A0 = +0.02 (IC cluster [-0.17; 0.23]). As diferenças A1−A0 que sobrevivem ao bootstrap por questão são em dimensões de teto/estilo: coerência +0.13, adequação +0.10, relevância das questões +0.12 — e A1 perde em clareza das questões (-0.06; enunciados mais longos).
3. **Par-a-par:** A1 vence A0 de forma robusta em 34/180 itens vs 14/180 (p sinal = 0.006); 132 são inconsistentes entre ordens. As vitórias robustas de A1 quase nunca aparecem na nota absoluta (só 26% têm média absoluta maior) — o juiz absoluto está no teto; a preferência pareada capta organização/estilo. Δpalavras não distingue vitórias de A1 e de A0 (Mann-Whitney p = 0.15).
4. **Erro do diagnóstico não prejudica A1 em média.** Nos 49 itens subavaliados, A1−A0 (média do texto) = -0.02; nos 95 acertados = +0.08; nos 36 superavaliados = +0.17 (sub vs acerto: MW p = 0.71; ρ(erro, Δ) = 0.01). O ponto fraco é outro: **alunos com nota 2 e diagnóstico correto** — A0 vence par-a-par em 30% vs A1 em 5% (n=20).
5. **Mecanismo qualitativo (H-04):** o diagnóstico sempre devolve 3 lacunas (179/180), inclusive para quem já acertou; com a instrução de focar ESTRITAMENTE nelas, A1 (i) acerta quando as lacunas são reais, mas (ii) estreita ou deriva quando são forçadas e (iii) propaga erros do próprio diagnóstico (q42). O 'A0 sai do gabarito' existe mas é modesto e localizado (vacúolo em 4/12 itens da q36 vs 1/12 no A1; termos técnicos fora do gabarito: 61 ocorrências no A0 vs 44 no A1).

## 0. Visão geral (médias por condição)

| condicao | n | palavras_media | palavras_mediana | p10 | p90 | coerencia | correcao_conceitual | fidelidade_gabarito | foco_na_lacuna | utilidade_pedagogica | adequacao_nivel | q_alinhamento | q_clareza | q_relevancia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1_pipeline | 180 | 158.53 | 158.50 | 145.90 | 170.00 | 4.92 | 4.95 | 4.74 | 4.59 | 4.74 | 4.97 | 4.80 | 4.82 | 4.43 |
| A0_direto | 180 | 120.49 | 119.00 | 107.00 | 134.00 | 4.79 | 4.93 | 4.73 | 4.57 | 4.62 | 4.87 | 4.73 | 4.88 | 4.31 |
| S_estatico | 180 | 158.93 | 161.00 | 146.00 | 167.00 | 4.82 | 4.91 | 4.60 | 3.79 | 4.22 | 4.85 | 4.67 | 4.84 | 4.19 |

Contrastes pareados (média de diferenças por item; IC95% e p por bootstrap de questão; p Wilcoxon por item só como referência):

| contraste | dimensao | diff | ic_cluster_lo | ic_cluster_hi | p_cluster | p_wilcoxon_item | frac_x_maior | frac_empate | frac_y_maior |
|---|---|---|---|---|---|---|---|---|---|
| A1_pipeline − A0_direto | coerencia | 0.128 | 0.033 | 0.233 | 0.006 | 0.005 | 0.133 | 0.822 | 0.044 |
| A1_pipeline − A0_direto | correcao_conceitual | 0.017 | -0.033 | 0.072 | 0.615 | 0.715 | 0.033 | 0.939 | 0.028 |
| A1_pipeline − A0_direto | fidelidade_gabarito | 0.017 | -0.072 | 0.111 | 0.768 | 0.577 | 0.133 | 0.750 | 0.117 |
| A1_pipeline − A0_direto | foco_na_lacuna | 0.022 | -0.167 | 0.233 | 0.861 | 0.779 | 0.139 | 0.722 | 0.139 |
| A1_pipeline − A0_direto | utilidade_pedagogica | 0.122 | -0.022 | 0.283 | 0.116 | 0.128 | 0.167 | 0.733 | 0.100 |
| A1_pipeline − A0_direto | adequacao_nivel | 0.100 | 0.022 | 0.194 | 0.009 | 0.006 | 0.089 | 0.894 | 0.017 |
| A1_pipeline − A0_direto | q_alinhamento | 0.074 | 0.004 | 0.146 | 0.043 | 0.014 | 0.311 | 0.500 | 0.189 |
| A1_pipeline − A0_direto | q_clareza | -0.057 | -0.096 | -0.020 | 0.002 | 0.045 | 0.167 | 0.606 | 0.228 |
| A1_pipeline − A0_direto | q_relevancia | 0.120 | 0.013 | 0.220 | 0.026 | 0.007 | 0.444 | 0.278 | 0.278 |
| A1_pipeline − A0_direto | abs_texto | 0.068 | -0.019 | 0.156 | 0.130 | 0.170 | 0.211 | 0.606 | 0.183 |
| A1_pipeline − S_estatico | coerencia | 0.106 | 0.033 | 0.183 | 0.003 | 0.017 | 0.128 | 0.817 | 0.056 |
| A1_pipeline − S_estatico | correcao_conceitual | 0.044 | -0.033 | 0.133 | 0.354 | 0.424 | 0.033 | 0.933 | 0.033 |
| A1_pipeline − S_estatico | fidelidade_gabarito | 0.144 | -0.028 | 0.306 | 0.109 | 0.045 | 0.200 | 0.639 | 0.161 |
| A1_pipeline − S_estatico | foco_na_lacuna | 0.800 | 0.422 | 1.211 | 0.000 | 0.000 | 0.456 | 0.433 | 0.111 |
| A1_pipeline − S_estatico | utilidade_pedagogica | 0.517 | 0.256 | 0.778 | 0.000 | 0.000 | 0.339 | 0.572 | 0.089 |
| A1_pipeline − S_estatico | adequacao_nivel | 0.117 | 0.061 | 0.178 | 0.000 | 0.002 | 0.117 | 0.861 | 0.022 |
| A1_pipeline − S_estatico | q_alinhamento | 0.131 | -0.007 | 0.300 | 0.072 | 0.001 | 0.356 | 0.483 | 0.161 |
| A1_pipeline − S_estatico | q_clareza | -0.015 | -0.122 | 0.106 | 0.754 | 0.561 | 0.200 | 0.606 | 0.194 |
| A1_pipeline − S_estatico | q_relevancia | 0.239 | 0.081 | 0.394 | 0.002 | 0.000 | 0.550 | 0.267 | 0.183 |
| A1_pipeline − S_estatico | abs_texto | 0.288 | 0.145 | 0.433 | 0.000 | 0.000 | 0.483 | 0.350 | 0.167 |
| A0_direto − S_estatico | coerencia | -0.022 | -0.161 | 0.106 | 0.814 | 0.656 | 0.111 | 0.761 | 0.128 |
| A0_direto − S_estatico | correcao_conceitual | 0.028 | -0.072 | 0.128 | 0.632 | 0.674 | 0.033 | 0.933 | 0.033 |
| A0_direto − S_estatico | fidelidade_gabarito | 0.128 | -0.006 | 0.256 | 0.062 | 0.148 | 0.183 | 0.667 | 0.150 |
| A0_direto − S_estatico | foco_na_lacuna | 0.778 | 0.378 | 1.172 | 0.000 | 0.000 | 0.450 | 0.444 | 0.106 |
| A0_direto − S_estatico | utilidade_pedagogica | 0.394 | 0.128 | 0.683 | 0.006 | 0.000 | 0.317 | 0.533 | 0.150 |
| A0_direto − S_estatico | adequacao_nivel | 0.017 | -0.106 | 0.122 | 0.778 | 0.676 | 0.106 | 0.794 | 0.100 |
| A0_direto − S_estatico | q_alinhamento | 0.057 | -0.056 | 0.196 | 0.376 | 0.104 | 0.289 | 0.533 | 0.178 |
| A0_direto − S_estatico | q_clareza | 0.043 | -0.052 | 0.150 | 0.422 | 0.073 | 0.222 | 0.644 | 0.133 |
| A0_direto − S_estatico | q_relevancia | 0.119 | 0.002 | 0.241 | 0.048 | 0.001 | 0.472 | 0.300 | 0.228 |
| A0_direto − S_estatico | abs_texto | 0.220 | 0.055 | 0.372 | 0.010 | 0.000 | 0.439 | 0.361 | 0.200 |

`abs_texto` = média das 6 dimensões de texto. A grande fração de empates (60–90%) reflete o teto do juiz (notas 4,6–5,0).

## H-03 a) Controle de tamanho

Todas as condições tinham o mesmo orçamento (120–180 palavras, `config.yaml`). Mesmo assim A0 fica no piso: 51% dos textos A0 têm < 120 palavras (A0 gera texto + questões num único JSON).

| condicao | q5 | q25 | q50 | q75 | q95 | dp | frac_x_mais_longo |
|---|---|---|---|---|---|---|---|
| A1_pipeline | 141.9 | 153.0 | 158.5 | 165.0 | 172.0 | 10.3 | — |
| A0_direto | 103.0 | 114.0 | 119.0 | 128.0 | 138.0 | 10.7 | — |
| S_estatico | 143.0 | 154.0 | 161.0 | 163.0 | 178.0 | 8.4 | — |
| Δ A1_pipeline − A0_direto | 19.0 | 28.8 | 37.0 | 47.0 | 63.0 | 14.9 | 1.0 |
| Δ A1_pipeline − S_estatico | -18.0 | -7.0 | 0.0 | 6.0 | 18.0 | 11.6 | 0.5 |
| Δ A0_direto − S_estatico | -55.1 | -47.0 | -40.0 | -30.0 | -19.0 | 12.0 | 0.0 |

**a.1 Regressão com efeito fixo de item** (formato longo A1/A0/S, dentro do item; referência = A0; EP cluster por questão, gl=14):

| dimensao | controle_log_palavras | A1_menos_A0 | ep_A1_A0 | p_A1_A0 | S_menos_A0 | A1_menos_S | coef_log_palavras | ep_log_palavras | p_log_palavras |
|---|---|---|---|---|---|---|---|---|---|
| coerencia | 0 | 0.128 | 0.054 | 0.033 | 0.022 | 0.106 | — | — | — |
| coerencia | 1 | 0.205 | 0.170 | 0.246 | 0.101 | 0.105 | -0.281 | 0.513 | 0.592 |
| foco_na_lacuna | 0 | 0.022 | 0.106 | 0.836 | -0.778 | 0.800 | — | — | — |
| foco_na_lacuna | 1 | 0.224 | 0.229 | 0.345 | -0.573 | 0.798 | -0.732 | 0.793 | 0.371 |
| utilidade_pedagogica | 0 | 0.122 | 0.083 | 0.161 | -0.394 | 0.517 | — | — | — |
| utilidade_pedagogica | 1 | 0.251 | 0.228 | 0.289 | -0.264 | 0.515 | -0.468 | 0.749 | 0.543 |
| adequacao_nivel | 0 | 0.100 | 0.047 | 0.051 | -0.017 | 0.117 | — | — | — |
| adequacao_nivel | 1 | 0.142 | 0.151 | 0.364 | 0.025 | 0.116 | -0.151 | 0.437 | 0.735 |
| q_relevancia | 0 | 0.120 | 0.055 | 0.047 | -0.119 | 0.239 | — | — | — |
| q_relevancia | 1 | 0.040 | 0.136 | 0.774 | -0.200 | 0.240 | 0.291 | 0.395 | 0.473 |
| q_clareza | 0 | -0.057 | 0.020 | 0.013 | -0.043 | -0.015 | — | — | — |
| q_clareza | 1 | -0.061 | 0.055 | 0.285 | -0.046 | -0.015 | 0.013 | 0.193 | 0.948 |
| fidelidade_gabarito | 0 | 0.017 | 0.048 | 0.731 | -0.128 | 0.144 | — | — | — |
| fidelidade_gabarito | 1 | 0.065 | 0.156 | 0.682 | -0.078 | 0.144 | -0.177 | 0.518 | 0.738 |
| correcao_conceitual | 0 | 0.017 | 0.028 | 0.567 | -0.028 | 0.044 | — | — | — |
| correcao_conceitual | 1 | 0.065 | 0.130 | 0.626 | 0.021 | 0.044 | -0.174 | 0.403 | 0.673 |
| abs_texto | 0 | 0.068 | 0.046 | 0.166 | -0.220 | 0.288 | — | — | — |
| abs_texto | 1 | 0.159 | 0.153 | 0.315 | -0.128 | 0.287 | -0.330 | 0.497 | 0.517 |

Leitura: o coeficiente de log(palavras) nunca é significativo e é majoritariamente negativo (positivo só em questões); ao controlar o tamanho, A1−A0 **não cai** (ex.: utilidade +0.12 → +0.25), mas o EP triplica porque A1 e A0 quase não se sobrepõem em tamanho — o dado não permite separar bem as duas coisas só pelo contraste A1×A0. A âncora mais informativa é S: mesmo tamanho de A1, notas menores que A0 em foco e utilidade.

**a.2 Diferença pareada A1−A0: Δnota = α + β·Δlog(palavras)** (α = vantagem de A1 a tamanho igual; EP cluster):

| dimensao | diff_bruta | alfa_tamanho_igual | ep_alfa | p_alfa | beta_dlog | ep_beta | spearman_dpalavras_dnota | p_spearman |
|---|---|---|---|---|---|---|---|---|
| coerencia | 0.128 | 0.106 | 0.158 | 0.514 | 0.079 | 0.475 | 0.021 | 0.783 |
| foco_na_lacuna | 0.022 | -0.162 | 0.216 | 0.465 | 0.667 | 0.799 | -0.028 | 0.709 |
| utilidade_pedagogica | 0.122 | -0.054 | 0.223 | 0.811 | 0.640 | 0.777 | 0.003 | 0.965 |
| adequacao_nivel | 0.100 | 0.054 | 0.138 | 0.700 | 0.166 | 0.417 | 0.058 | 0.443 |
| q_relevancia | 0.120 | -0.015 | 0.117 | 0.901 | 0.489 | 0.328 | 0.112 | 0.133 |
| q_clareza | -0.057 | -0.031 | 0.058 | 0.607 | -0.097 | 0.203 | 0.029 | 0.697 |
| abs_texto | 0.068 | -0.029 | 0.140 | 0.841 | 0.348 | 0.461 | 0.008 | 0.912 |

**a.3 Faixas de Δpalavras (tercis) e subconjunto pareado (|Δ| ≤ 15% do A0):**

| faixa | n | Δpalavras_media | Δpalavras_min | Δpalavras_max | coerencia | foco_na_lacuna | utilidade_pedagogica | adequacao_nivel | q_relevancia | q_clareza | abs_texto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 (Δ menor) | 60 | 23.217 | -6.000 | 32.000 | 0.167 | 0.017 | 0.117 | 0.083 | 0.011 | -0.078 | 0.053 |
| T2 | 62 | 37.016 | 33.000 | 41.000 | 0.097 | 0.048 | 0.129 | 0.113 | 0.242 | -0.027 | 0.081 |
| T3 (Δ maior) | 58 | 54.466 | 42.000 | 93.000 | 0.121 | 0.000 | 0.121 | 0.103 | 0.103 | -0.069 | 0.069 |
| pareado |Δ|≤15% | 16 | 15.312 | -6.000 | 21.000 | 0.188 | 0.125 | 0.125 | 0.062 | -0.083 | -0.042 | 0.031 |

Conclusão a): A1−A0 é praticamente constante entre faixas de Δpalavras; não há indício de que a vantagem nominal de A1 seja efeito de verbosidade do juiz. Em contrapartida, essa vantagem já é pequena e só é estatisticamente distinguível em coerência, adequação ao nível e relevância das questões (bruto, cluster), e nenhuma delas resiste ao controle de tamanho por falta de sobreposição. O resultado pareado `mais_longo_vence = 0,56` do `summary.md` é coerente com isso.

## H-03 b) Estratificação por nota-ouro e por questão

| estrato | valor | n | Δpalavras_A1_A0 | A1_A0_abs_texto | A1_A0_foco_na_lacuna | A1_A0_utilidade_pedagogica | A1_A0_q_relevancia | A1_A0_par_vitA1 | A1_A0_par_vitOutro | A1_S_foco_na_lacuna | A1_S_utilidade_pedagogica | A1_S_par_vitA1 | A1_S_par_vitOutro |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nota_ouro | 0 | 60 | 37.20 | 0.05 | -0.07 | 0.05 | 0.11 | 0.23 | 0.05 | 0.42 | 0.22 | 0.18 | 0.03 |
| nota_ouro | 1 | 60 | 37.52 | 0.12 | 0.08 | 0.20 | 0.18 | 0.20 | 0.03 | 1.13 | 0.73 | 0.08 | 0.03 |
| nota_ouro | 2 | 60 | 39.40 | 0.03 | 0.05 | 0.12 | 0.07 | 0.13 | 0.15 | 0.85 | 0.60 | 0.13 | 0.22 |

`par_vitA1` / `par_vitOutro` = fração de itens com vitória robusta (mesmo vencedor nas duas ordens).

- A vantagem de A1 sobre A0 é maior na nota 1 (Δabs +0.12; utilidade +0.20) e desaparece na nota 2: no par-a-par, A0 vence 15% vs A1 13%. Contra S, a nota 2 também é onde S mais vence A1 (22%).
- Padrão consistente com o mecanismo do H-04: para quem já sabe quase tudo, o diagnóstico precisa 'achar' lacunas e o A1 foca nelas, enquanto A0/S cobrem o núcleo da pergunta.

**Por questão** (n=12 cada; classe: sinal concordante entre |Δabs| ≥ 0,15 e |saldo de vitórias robustas| ≥ 2):

| question_id | n | acc_diag | erro_diag_medio | Δabs_A1_A0 | par_saldo_A1_A0 | Δabs_A1_S | par_saldo_A1_S | Δfoco_A1_S | Δq_relev_A1_A0 | classe_A1_vs_A0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 36 | 12 | 0.50 | -0.42 | 0.24 | 0 | 0.57 | 3 | 1.75 | 0.36 | A1 > A0 |
| 37 | 12 | 0.42 | 0.25 | 0.19 | 3 | 0.71 | -4 | 1.58 | -0.19 | A1 > A0 |
| 38 | 12 | 0.58 | 0.08 | 0.00 | 0 | 0.85 | 3 | 2.58 | 0.14 | empate |
| 39 | 12 | 0.58 | -0.25 | -0.07 | 3 | 0.42 | 1 | 0.92 | 0.14 | A1 > A0 |
| 40 | 12 | 0.67 | 0.00 | 0.14 | 2 | 0.35 | 1 | 0.50 | 0.33 | A1 > A0 |
| 41 | 12 | 0.50 | -0.08 | 0.11 | 0 | -0.22 | -2 | -0.25 | 0.17 | empate |
| 42 | 12 | 0.50 | 0.25 | -0.08 | -2 | -0.08 | -2 | 0.00 | -0.28 | A0 > A1 |
| 43 | 12 | 0.58 | -0.08 | 0.17 | -1 | 0.31 | -1 | 0.42 | 0.47 | A1 > A0 |
| 44 | 12 | 0.25 | -0.25 | 0.15 | 2 | 0.01 | -1 | 0.08 | 0.17 | A1 > A0 |
| 45 | 12 | 0.75 | -0.08 | 0.47 | -1 | 0.11 | -2 | 0.25 | -0.17 | A1 > A0 |
| 46 | 12 | 0.67 | 0.17 | 0.15 | 1 | 0.43 | 0 | 1.42 | 0.08 | A1 > A0 |
| 47 | 12 | 0.33 | -0.50 | 0.00 | 6 | 0.44 | 5 | 1.33 | 0.33 | A1 > A0 |
| 48 | 12 | 0.50 | 0.00 | -0.24 | 0 | -0.03 | 1 | -0.17 | 0.19 | A0 > A1 |
| 49 | 12 | 0.42 | -0.08 | -0.08 | 4 | 0.25 | 2 | 0.67 | 0.00 | A1 > A0 |
| 50 | 12 | 0.67 | -0.17 | -0.14 | 3 | 0.21 | 3 | 0.92 | 0.06 | A1 > A0 |

Contagem: A1 > A0: 11, empate: 2, A0 > A1: 2. A q42 (aparelho reprodutor masculino) concentra 7 das 14 vitórias robustas de A0; A1 abre vantagem mais clara em q37, q47, q49 e q50 no par-a-par e em q36/q45 na nota absoluta. A acurácia do diagnóstico por questão não prediz essa classe (q44 tem a pior acurácia, 25%, e A1 ainda vence). Cautela: com n=12, limiares baixos e muitos sinais 'A1 > A0' vindo de um único critério (ex.: q36 e q45 só pela nota absoluta; q45 tem saldo par-a-par negativo), a contagem superestima a consistência; o sinal mais firme é o A0 > A1 na q42.

## H-03 c) Cruzamento com o erro do diagnóstico (nota_estimada − ouro)

| grupo_diag | n | dimensao | A1_menos_A0 | ic_lo | ic_hi | A1_menos_S | A1_nivel | A0_nivel |
|---|---|---|---|---|---|---|---|---|
| acertou (pred=ouro) | 95 | abs_texto | 0.075 | -0.028 | 0.189 | 0.267 | 4.867 | 4.791 |
| acertou (pred=ouro) | 95 | foco_na_lacuna | 0.032 | -0.200 | 0.263 | 0.758 | 4.674 | 4.642 |
| acertou (pred=ouro) | 95 | utilidade_pedagogica | 0.137 | -0.063 | 0.326 | 0.484 | 4.811 | 4.674 |
| acertou (pred=ouro) | 95 | coerencia | 0.158 | 0.042 | 0.284 | 0.095 | 4.947 | 4.789 |
| acertou (pred=ouro) | 95 | fidelidade_gabarito | 0.042 | -0.074 | 0.158 | 0.084 | 4.800 | 4.758 |
| acertou (pred=ouro) | 95 | q_relevancia | 0.095 | -0.014 | 0.200 | 0.196 | 4.425 | 4.330 |
| subavaliou (pred<ouro) | 49 | abs_texto | -0.024 | -0.228 | 0.156 | 0.361 | 4.776 | 4.799 |
| subavaliou (pred<ouro) | 49 | foco_na_lacuna | 0.000 | -0.347 | 0.388 | 0.980 | 4.571 | 4.571 |
| subavaliou (pred<ouro) | 49 | utilidade_pedagogica | 0.020 | -0.286 | 0.327 | 0.653 | 4.694 | 4.673 |
| subavaliou (pred<ouro) | 49 | coerencia | 0.000 | -0.122 | 0.122 | 0.102 | 4.898 | 4.898 |
| subavaliou (pred<ouro) | 49 | fidelidade_gabarito | -0.082 | -0.347 | 0.143 | 0.347 | 4.694 | 4.776 |
| subavaliou (pred<ouro) | 49 | q_relevancia | 0.259 | 0.109 | 0.408 | 0.354 | 4.497 | 4.238 |
| superavaliou (pred>ouro) | 36 | abs_texto | 0.171 | -0.042 | 0.412 | 0.245 | 4.755 | 4.583 |
| superavaliou (pred>ouro) | 36 | foco_na_lacuna | 0.028 | -0.278 | 0.361 | 0.667 | 4.417 | 4.389 |
| superavaliou (pred>ouro) | 36 | utilidade_pedagogica | 0.222 | -0.111 | 0.556 | 0.417 | 4.611 | 4.389 |
| superavaliou (pred>ouro) | 36 | coerencia | 0.222 | 0.028 | 0.472 | 0.139 | 4.889 | 4.667 |
| superavaliou (pred>ouro) | 36 | fidelidade_gabarito | 0.083 | -0.139 | 0.306 | 0.028 | 4.667 | 4.583 |
| superavaliou (pred>ouro) | 36 | q_relevancia | -0.000 | -0.158 | 0.157 | 0.194 | 4.370 | 4.370 |

IC por bootstrap de item (exploratório). Cruzamento com a nota-ouro:

| grade | grupo_diag | n | Δabs_A1_A0 | Δfoco_A1_A0 | vit_A1 | vit_A0 |
|---|---|---|---|---|---|---|
| 0 | acertou (pred=ouro) | 36 | 0.065 | -0.056 | 0.194 | 0.028 |
| 0 | superavaliou (pred>ouro) | 24 | 0.035 | -0.083 | 0.292 | 0.083 |
| 1 | acertou (pred=ouro) | 39 | 0.034 | 0.051 | 0.128 | 0.051 |
| 1 | subavaliou (pred<ouro) | 10 | 0.000 | -0.100 | 0.400 | 0.000 |
| 1 | superavaliou (pred>ouro) | 11 | 0.515 | 0.364 | 0.273 | 0.000 |
| 2 | acertou (pred=ouro) | 20 | 0.175 | 0.150 | 0.050 | 0.300 |
| 2 | subavaliou (pred<ouro) | 39 | -0.030 | 0.026 | 0.179 | 0.077 |
| 2 | superavaliou (pred>ouro) | 1 | -0.333 | -1.000 | 0.000 | 0.000 |

- Subavaliação (conservadorismo, n=49, quase toda em ouro=2) **não** derruba A1 frente a A0 na média (Δabs ≈ 0) e até melhora a relevância das questões (+0.26, IC exclui 0): mais lacunas declaradas → questões mais 'mirando' algo.
- A célula problemática é **ouro=2 com diagnóstico correto** (n=20): A0 vence par-a-par 30% vs A1 5%. Ou seja, o risco não é o diagnóstico errar a nota, e sim as lacunas listadas para alunos fortes serem periféricas ou incorretas (ver q42, q45).
- Superavaliação (n=36) tende a favorecer A1 (Δabs +0,17, utilidade +0,22), mas o IC inclui 0.

## H-03 d) Par-a-par detalhado

| par | resultado | n | Δpalavras_media | Δpalavras_mediana | Δabs_texto | Δfoco | Δutilidade | frac_abs_concorda |
|---|---|---|---|---|---|---|---|---|
| A1_pipeline vs A0_direto | A0 robusta | 14 | 31.50 | 26.50 | -0.02 | -0.14 | 0.07 | 0.36 |
| A1_pipeline vs A0_direto | A1 robusta | 34 | 41.18 | 39.00 | 0.17 | 0.21 | 0.21 | 0.26 |
| A1_pipeline vs A0_direto | inconsistente | 132 | 37.92 | 36.50 | 0.05 | -0.01 | 0.11 | — |
| A1_pipeline vs S_estatico | A1 robusta | 24 | 0.00 | 1.00 | 0.63 | 1.83 | 1.17 | 0.71 |
| A1_pipeline vs S_estatico | S robusta | 17 | -3.71 | -3.00 | 0.22 | 0.88 | 0.65 | 0.35 |
| A1_pipeline vs S_estatico | empate | 1 | -8.00 | -8.00 | 1.00 | 4.00 | 2.00 | — |
| A1_pipeline vs S_estatico | inconsistente | 138 | -0.01 | 0.00 | 0.23 | 0.59 | 0.38 | — |

- A1×A0: 34 vitórias robustas de A1, 14 de A0 (p = 0.006). A1×S: 24 vs 17 (p = 0.349).
- Δpalavras médio nas vitórias de A1 (41) é próximo do das vitórias de A0 (32) e dos inconsistentes; MW p = 0.15. A1 é mais longo em praticamente todos os pares, inclusive nos que perde.
- Concordância absoluto×par baixa: nas vitórias robustas de A1 sobre A0, só 26% têm média absoluta maior (o resto é empate no teto). Contra S, 71% — aí a diferença é de conteúdo (foco +1.8).
- Lista completa por item: `h03_10_par_a_par_por_item.csv`.

## H-04 — Análise qualitativa pareada

Seleção: a partir de `h04_03_painel_itens.csv`, foram filtrados (i) vitórias robustas de A1 sobre A0 **e** S, (ii) vitórias robustas de A0 sobre A1, (iii) itens com termos fora do gabarito, (iv) maiores |Δ q_relevância|; dentro de cada grupo, escolhidos itens com diagnóstico certo e errado e de questões diferentes. Os textos foram lidos integralmente; abaixo só há resumos (nenhuma resposta de aluno é reproduzida).

| item_id | tipo | ouro | diag | palavras A1/A0/S | foco A1/A0/S | util A1/A0/S | q_relev A1/A0/S | par A1×A0 | par A1×S |
|---|---|---|---|---|---|---|---|---|---|
| q36_3b0258ff | (i)+(iii) A1 > A0 e S; A0 sai do gabarito | 1 | 0 | 166/131/161 | 5/5/1 | 5/5/3 | 5.00/3.67/4.33 | A1 | A1 |
| q39_524585dd | (i) A1 > A0 e S com diagnóstico conservador | 2 | 1 | 154/115/146 | 5/5/2 | 5/5/3 | 4.67/4.00/4.00 | A1 | A1 |
| q40_19368b9f | (ii) A0 > A1 com diagnóstico correto | 0 | 0 | 170/118/165 | 2/5/5 | 3/5/5 | 5.00/4.67/5.00 | A0 | incons. |
| q37_4f1cecfe | (ii) sobre-remediação/estreitamento com diagnóstico conservador | 2 | 1 | 146/152/178 | 4/4/4 | 5/5/4 | 4.33/5.00/5.00 | A0 | S |
| q42_9260e885 | (ii)+(iii invertido) erro do diagnóstico propagado pelo A1 | 2 | 2 | 149/135/158 | 5/5/5 | 4/5/5 | 3.33/4.67/4.33 | A0 | S |
| q45_2a7cf00f | (iv) questões: lacunas 'forçadas' em aluno que já acertou | 2 | 2 | 150/96/143 | 5/5/5 | 5/5/5 | 3.67/5.00/4.00 | A0 | incons. |
| q43_da5a83a4 | (iv) questões: A1 mira as lacunas | 2 | 1 | 159/114/158 | 5/5/5 | 5/5/5 | 5.00/3.67/3.67 | incons. | incons. |

- **`q36_3b0258ff` — (i)+(iii) A1 > A0 e S; A0 sai do gabarito.** Caso do apêndice do `main.tex`. O diagnóstico subestimou (nota 0 vs ouro 1) e não registrou o acerto do aluno (cloroplasto), mas o A1 também recebe a resposta e abre reconhecendo esse acerto; depois cobre exatamente as 3 lacunas (formato, parede celular, celulose) com analogia. O A0 cobre o mesmo núcleo, porém acrescenta vacúolo (ausente do gabarito e não citado pelo aluno). Questões: A1 testa as 3 lacunas (q_relevância 5,0); A0 inclui uma questão sobre membrana plasmática, fora das lacunas (3,67). Subavaliação aqui NÃO gerou sobre-remediação nociva.
- **`q39_524585dd` — (i) A1 > A0 e S com diagnóstico conservador.** Ouro 2, diagnóstico 1. Ambos (A1 e A0) corrigem corretamente a concepção errada (metabolismo dependente de impulsos nervosos). A1 organiza a explicação em síntese/degradação → energia → funções e fecha com analogia; A0 diz o mesmo de forma mais compacta. Notas absolutas quase iguais (Δ≈0,17); a preferência par-a-par reflete organização/estilo, não conteúdo diferente. S (genérico) não toca a concepção errada (foco 2).
- **`q40_19368b9f` — (ii) A0 > A1 com diagnóstico correto.** Ouro 0 = diagnóstico 0. O diagnóstico identificou o erro central (o aluno associa fenótipo/genótipo a partes do corpo), mas o texto A1 vira uma explicação genérica de fenótipo×genótipo e não confronta esse erro; o A0 abre exatamente por ele (foco 5 vs 2; utilidade 5 vs 3). A1 ainda generaliza que o genótipo 'define as características da espécie'. Mostra que ter o erro no diagnóstico não garante que o gerador o use.
- **`q37_4f1cecfe` — (ii) sobre-remediação/estreitamento com diagnóstico conservador.** Ouro 2, diagnóstico 1. O diagnóstico tratou como 'erro' a omissão do citoplasma e reduziu as lacunas a citoplasma/núcleo. Seguindo a instrução de focar ESTRITAMENTE nas lacunas, o A1 ignora as organelas que o aluno discutiu; o A0 dialoga com tudo o que o aluno escreveu (retículo liso/rugoso, golgiense, ribossomos). A0 e S vencem A1 nas duas ordens. Observação: o A0 afirma que um termo usado pelo aluno não existe, quando parece ser grafia incorreta de um termo real (cariolinfa) — a 'correção' do A0 também é imprecisa.
- **`q42_9260e885` — (ii)+(iii invertido) erro do diagnóstico propagado pelo A1.** Ouro 2 = diagnóstico 2. O diagnóstico inventa um erro: diz que 'ducto deferente' e 'vasos deferentes' são estruturas diferentes — o próprio gabarito usa 'ductos deferentes'. O A1 transmite essa correção falsa ao aluno e, por seguir a lacuna 'espermatogênese/espermiogênese' (ausente do gabarito), recomenda estudá-la e cria uma questão sobre ela (q_relevância 3,33 vs 4,67). O A0 não tem nenhum dos dois problemas. Na q42, 'espermatogênese' aparece em 3/12 textos A1 e 0/12 A0 — aqui é o A1 que sai do gabarito, via diagnóstico.
- **`q45_2a7cf00f` — (iv) questões: lacunas 'forçadas' em aluno que já acertou.** Ouro 2 = diagnóstico 2; o aluno já dá a resposta central (leucócitos têm núcleo; hemácias não). O diagnóstico ainda assim precisa listar 3 lacunas (o formato pede 'até 3', e na prática são 3 em 179/180 itens) e escolhe tangentes. As questões A1 derivam para transporte de oxigênio e importância genérica dos cromossomos (q_relevância 3,67); as do A0 e do S testam o raciocínio central da pergunta (5,0 e 4,0). A0 vence nas duas ordens.
- **`q43_da5a83a4` — (iv) questões: A1 mira as lacunas.** Ouro 2, diagnóstico 1. As lacunas (inspiração completa, diafragma, intercostais) viram três questões diretamente sobre elas (q_relevância 5,0); o A0 inclui uma questão de aplicação sobre 'situação em que a respiração fica difícil', menos ligada à lacuna (3,67). Exemplo do mecanismo pelo qual A1 ganha em q_relevância (+0,12 em média).

### (iii) A0 introduz conteúdo fora do gabarito? (checagem de recorrência)

Termos técnicos de uma lista curada que aparecem no texto mas não no gabarito nem no S da questão; `sem_rastro_no_diag` = o termo também não aparece no diagnóstico (que inclui trechos literais do aluno), ou seja, provável acréscimo do gerador e não resposta ao que o aluno escreveu.

| condicao | ocorrencias | itens | ocorr_sem_rastro_no_diag |
|---|---|---|---|
| A0_direto | 61 | 43 | 17 |
| A1_pipeline | 44 | 36 | 13 |

| question_id | A0_direto | A1_pipeline |
|---|---|---|
| 36 | 12 | 7 |
| 37 | 19 | 8 |
| 39 | 8 | 7 |
| 40 | 3 | 1 |
| 42 | 0 | 6 |
| 45 | 6 | 4 |
| 47 | 3 | 3 |
| 48 | 2 | 3 |
| 49 | 4 | 4 |
| 50 | 2 | 1 |

| condicao | itens_q36 | q36_com_vacuolo | q36_com_vacuolo_e_aluno_citou | total_com_vacuolo |
|---|---|---|---|---|
| S0_gabarito | 12 | 0 | 0 | 0 |
| S_estatico | 12 | 0 | 0 | 0 |
| A0_direto | 12 | 4 | 2 | 4 |
| A1_pipeline | 12 | 1 | 0 | 1 |

- O padrão existe, mas é **modesto e localizado** nas questões de citologia (q36/q37) e em 'DNA' (q40/q45). Parte relevante dos termos do A0 responde ao que o aluno escreveu (só 17/61 sem rastro no diagnóstico vs 13/44 no A1). A fidelidade ao gabarito medida pelo juiz é igual (A1−A0 = +0.02).
- O vacúolo do apêndice é recorrente na q36 (4/12 no A0), mas em 2 desses itens o aluno citou vacúolos (o A0 respondeu ao aluno); só os demais, como o `q36_3b0258ff` do apêndice, são acréscimo do gerador. Recomenda-se descrever no artigo como 'ocasional', não como padrão sistemático do A0.
- Simetricamente, o A1 também sai do gabarito quando o **diagnóstico** sai (espermatogênese na q42; correção falsa 'ducto ≠ vasos deferentes'). O vocabulário extra do A1 é sobretudo de **analogias** (receita, alarme de fumaça, detergente, soldados), que o prompt do A1 pede e o do A0 não.

### (iv) Questões geradas

| condicao | mean | median |
|---|---|---|
| A0_direto | 14.4 | 14.2 |
| A1_pipeline | 17.7 | 17.7 |
| S_estatico | 15.8 | 16.0 |

- A1 ganha em relevância das questões (+0.12 vs A0; +0.24 vs S) porque as questões recebem explicitamente a lista de lacunas (q43). Perde em clareza (-0.06) com enunciados mais longos/compostos ('Compare X e discorra sobre Y').
- Quando as lacunas são forçadas (aluno forte), a mesma ligação direta transforma lacunas periféricas em questões periféricas (q45, q42).

| grade | n | lacunas_media | frac_3_lacunas | acertos_diag_media | erros_diag_media |
|---|---|---|---|---|---|
| 0.00 | 60.00 | 3.00 | 1.00 | 0.37 | 0.70 |
| 1.00 | 60.00 | 3.00 | 1.00 | 0.80 | 0.48 |
| 2.00 | 60.00 | 2.98 | 0.98 | 0.98 | 0.45 |

## Implicações para RQ2/RQ3 (papel real da etapa explícita de diagnóstico)

1. **RQ2 (adaptação ajuda?)** — Sim, e de forma robusta: A1 e A0 superam S em foco na lacuna (~+0,8) e utilidade (+0,4/+0,5), com tamanho igual entre A1 e S. A vantagem vem de **condicionar na resposta do aluno**, presente em ambas.
2. **RQ3 (diagnóstico explícito agrega?)** — Pouco, e não por causa de tamanho. A1 > A0 aparece em coerência, adequação e relevância das questões e na preferência par-a-par (34×14), mas não em foco/utilidade/fidelidade. Sugestão de redação: 'o diagnóstico explícito estrutura e direciona o material (sobretudo as questões), mas não aumenta de forma mensurável o foco nas lacunas em relação à geração direta condicionada na resposta'.
3. **O diagnóstico é um ponto de falha também, não só de ganho.** Ele sempre produz 3 lacunas, e o A1 segue-as estritamente: ajuda alunos de nota 1, mas para alunos de nota 2 estreita o texto (q37), gera questões periféricas (q45) e pode propagar erros do próprio diagnóstico (q42). Isso é mais relevante que o conservadorismo de nota (RQ1): errar a nota não piorou A1 em média.
4. **Ressalva de desenho (importante para o texto do artigo):** A1 e A0 não diferem só no diagnóstico. O prompt do A1 pede analogia do cotidiano e tom encorajador e gera texto e questões em chamadas separadas (questões recebem as lacunas); o A0 gera tudo num único JSON e recebe os conceitos-chave. Parte da vantagem de estilo do A1 (coerência, analogias, preferência par-a-par) pode vir dessas diferenças de prompt, não do diagnóstico em si.
5. **Sugestões acionáveis:** (a) permitir 0–3 lacunas no diagnóstico ("nenhuma lacuna relevante" para respostas completas) — conecta com H-02; (b) verificar as lacunas/erros do diagnóstico contra o gabarito antes da geração (o A2 já faz isso no texto, mas não no diagnóstico); (c) para uma ablação limpa de RQ3, usar o prompt do A1 com o diagnóstico vazio/omitido.
6. **Limitações:** juiz único no teto (empates de 60–90%), n=12 por questão, estratos sem correção de multiplicidade; a checagem de termos técnicos é um proxy lexical curado, não anotação humana.

## Arquivos gerados (`results/herik_variants/`)

- `h03_00_visao_geral.csv`
- `h03_01_contrastes_brutos.csv`
- `h03_02_distribuicao_palavras.csv`
- `h03_03_regressao_efeito_fixo_item.csv`
- `h03_04_delta_palavras_vs_delta_nota.csv`
- `h03_05_faixas_delta_palavras.csv`
- `h03_06_estratificacao.csv`
- `h03_07_por_questao.csv`
- `h03_08_erro_diagnostico.csv`
- `h03_09_erro_diag_x_nota_ouro.csv`
- `h03_10_par_a_par_por_item.csv`
- `h03_11_par_a_par_resumo.csv`
- `h04_01_termos_tecnicos_fora_do_gabarito.csv`
- `h04_02_vacuolo.csv`
- `h04_03_painel_itens.csv`
- `h04_04_tamanho_enunciados.csv`
- `h04_05_lacunas_por_nota_ouro.csv`
- `h04_06_casos_selecionados.csv`
