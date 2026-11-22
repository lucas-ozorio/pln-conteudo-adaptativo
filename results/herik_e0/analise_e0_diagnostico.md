# Análise Offline do Conservadorismo em E0 (`H-01`, `RQ1`)

Relatório gerado por `scripts/analyze_e0_calibration.py` sobre os 595 itens reais de `outputs/diagnosis.jsonl` pareados com `data/processed/diag_set.jsonl` (100% offline, sem chamadas de API).

## 1. Resumo Executivo

- **Reprodutibilidade base (`n = 595`):** `QWK = 0.487`, `Spearman = 0.580`, `MAE = 0.703`, `acc_exata = 42.9%`, `acc_binaria(>=2) = 67.7%` (idêntico a `results/e0_diagnostico.csv`).
- **Assimetria forte do erro:** viés médio = `-0.380` pontos; **41.3%** dos itens são subavaliados (`pred < grade`) contra **15.8%** superavaliados (`pred > grade`). O erro concentra-se na compressão para `pred = 1` (324/595 = 54.5% das predições).
- **Não é só viés conservador nas notas altas, é colapso de extremos:** `ouro=3` cai para `<=1` em `67/145` (`46.2%`) e `ouro=2` cai para `1` em `89/150` (`59.3%`), mas ao mesmo tempo `ouro=0` sobe para `>=1` em `65/150` (`43.3%`).
- **Causa estrutural principal — penalização sem erro conceitual:** entre os `67` casos graves `ouro=3 -> pred<=1`, **53.7%** têm **zero erros conceituais** registrados; o mesmo ocorre em **51.7%** dos `89` casos `ouro=2 -> pred=1`. O diagnoser está usando a contagem de conceitos marcados como `ausente` após forçar a extração de *todos* os conceitos + extras (`tem_conceitos_extras` em `61.5%` de todo o E0).
- **Quanto é calibração pura vs. discriminação (LOGO 15-fold):** apenas remapear a escala de `nota_estimada` via Leave-One-Question-Out (`remap_nota_logo`) já eleva o QWK de `0.487` para **0.500** (sem novo custo de API). Usar as frações internas do JSON (`ordinal_thresholds_logo`) chega a **0.575** (Spearman `0.577`), aproximando o patamar do `grader` Gemini no subconjunto piloto.

### Matriz de confusão completa (`n = 595`)
```
        pred=0  pred=1  pred=2  pred=3
ouro=0      85      63       2       0
ouro=1      16     107      27       0
ouro=2       7      89      52       2
ouro=3       2      65      67      11
```

---

## 2. Desempenho por Questão (`QWK 0.18` a `0.78`)

- **Pior questão:** `q36` (`QWK = 0.179`, `Spearman = 0.328`, `bias = -0.775`, subavaliação `55.0%`, `ouro=3 -> pred<=1` = `90.0%`).
- **Melhor questão:** `q45` (`QWK = 0.784`, `Spearman = 0.807`, `bias = -0.175`, `acc_exata = 60.0%`).
- **Correlações entre atributos da questão e QWK/viés (`n = 15` questões):** Spearman(`n_refs`, `QWK`) = `-0.320`; Spearman(`n_conceitos_esperados`, `QWK`) = `-0.012`; Spearman(`palavras_aluno_media`, `QWK`) = `-0.036`; Spearman(`n_conceitos_esperados`, `bias_medio`) = `+0.218`.
- **Disponibilidade para holdout sem vazamento (`H-02`):** o PT-ASAG v2 possui **6501** respostas válidas únicas fora do `diag_set` (mínimo de `275` e máximo de `551` por questão).

| question_id | n | QWK | Spearman | MAE | bias_medio | acc_exata | taxa_subavaliacao | pct_ouro3_pred_le1 | pct_ouro2_pred1 | pct_ouro0_pred_ge1 | n_refs | n_conceitos_esperados | palavras_aluno_media | extra_holdout_fora_diag_set |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 40 | 0.179 | 0.328 | 0.975 | -0.775 | 0.350 | 0.550 | 0.900 | 0.800 | 0.400 | 3 | 4 | 15.7 | 551 |
| 48 | 40 | 0.234 | 0.405 | 0.825 | -0.425 | 0.375 | 0.425 | 0.800 | 0.700 | 0.800 | 3 | 3 | 16.3 | 463 |
| 49 | 40 | 0.278 | 0.517 | 0.850 | -0.600 | 0.375 | 0.500 | 0.900 | 0.900 | 0.500 | 3 | 4 | 13.6 | 498 |
| 47 | 40 | 0.351 | 0.639 | 0.975 | -0.875 | 0.300 | 0.650 | 0.800 | 0.700 | 0.200 | 3 | 3 | 11.4 | 405 |
| 44 | 40 | 0.361 | 0.531 | 0.900 | -0.500 | 0.225 | 0.575 | 0.500 | 0.900 | 0.800 | 3 | 3 | 17.9 | 360 |
| 37 | 40 | 0.394 | 0.439 | 0.800 | -0.050 | 0.300 | 0.325 | 0.400 | 0.400 | 0.800 | 3 | 3 | 28.2 | 533 |
| 42 | 35 | 0.443 | 0.518 | 0.629 | +0.000 | 0.457 | 0.257 | 0.400 | 0.300 | 0.800 | 4 | 8 | 19.4 | 422 |
| 41 | 40 | 0.462 | 0.532 | 0.700 | -0.350 | 0.475 | 0.375 | 0.500 | 0.400 | 0.300 | 3 | 3 | 12.2 | 456 |
| 39 | 40 | 0.537 | 0.754 | 0.650 | -0.600 | 0.500 | 0.475 | 0.600 | 0.800 | 0.000 | 3 | 3 | 15.9 | 328 |
| 46 | 40 | 0.542 | 0.642 | 0.625 | -0.325 | 0.475 | 0.375 | 0.400 | 0.500 | 0.400 | 2 | 4 | 19.3 | 517 |
| 38 | 40 | 0.551 | 0.608 | 0.625 | -0.325 | 0.500 | 0.350 | 0.400 | 0.300 | 0.200 | 3 | 3 | 15.6 | 465 |
| 40 | 40 | 0.586 | 0.699 | 0.625 | -0.275 | 0.425 | 0.400 | 0.200 | 0.600 | 0.500 | 3 | 4 | 15.9 | 392 |
| 50 | 40 | 0.756 | 0.850 | 0.475 | -0.325 | 0.525 | 0.400 | 0.000 | 0.600 | 0.100 | 3 | 3 | 11.4 | 361 |
| 43 | 40 | 0.780 | 0.805 | 0.450 | -0.050 | 0.550 | 0.250 | 0.000 | 0.500 | 0.600 | 2 | 3 | 29.0 | 475 |
| 45 | 40 | 0.784 | 0.807 | 0.425 | -0.175 | 0.600 | 0.275 | 0.100 | 0.500 | 0.100 | 3 | 4 | 12.4 | 275 |

---

## 3. Anatomia Interna do Diagnóstico e Taxonomia de Erros

### Por faixa de erro (`pred - grade`)
| grupo | n | n_conceitos_esperados | n_conceitos_listados | n_conceitos_extras | frac_presente | frac_coberto | n_acertos | n_erros_conceituais | pct_zero_erros_conceituais | palavras_aluno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| subavaliado | 246 | 3.52 | 4.55 | 1.03 | 0.324 | 0.438 | 0.90 | 0.46 | 0.581 | 18.7 |
| exato | 255 | 3.66 | 4.75 | 1.09 | 0.250 | 0.332 | 0.68 | 0.53 | 0.506 | 15.3 |
| superavaliado | 94 | 3.82 | 4.87 | 1.05 | 0.320 | 0.463 | 0.97 | 0.66 | 0.383 | 16.7 |

### Por nota-ouro (`grade`)
| grupo | n | n_conceitos_listados | n_conceitos_extras | n_presente | n_parcial | n_ausente | n_incorreto | frac_coberto | n_erros_conceituais | pct_zero_erros_conceituais | n_lacunas | pct_3_lacunas | pct_alguma_lacuna_sem_respaldo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ouro=0 | 150 | 4.77 | 1.11 | 0.48 | 0.33 | 3.92 | 0.04 | 0.172 | 0.69 | 0.320 | 3.00 | 1.000 | 0.027 |
| ouro=1 | 150 | 4.68 | 1.01 | 1.16 | 0.50 | 2.99 | 0.03 | 0.368 | 0.57 | 0.473 | 3.00 | 1.000 | 0.027 |
| ouro=2 | 150 | 4.74 | 1.07 | 1.69 | 0.50 | 2.53 | 0.02 | 0.479 | 0.45 | 0.587 | 2.97 | 0.987 | 0.033 |
| ouro=3 | 145 | 4.55 | 1.03 | 2.10 | 0.43 | 2.02 | 0.00 | 0.572 | 0.35 | 0.697 | 2.79 | 0.924 | 0.014 |

### Modos de falha quantificados (subavaliação, múltiplos gabaritos e indulgência em 0)
| modo_erro | n | pct_zero_erros_conceituais | pct_tem_conceitos_extras | media_presente | media_parcial | media_ausente | media_incorreto | max_ref_overlap_medio | all_refs_overlap_medio | pct_alta_sobreposicao_1ref_baixa_uniao | media_palavras_aluno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ouro=3 -> pred<=1 (grave) | 67 | 0.537 | 0.612 | 1.22 | 0.55 | 2.75 | 0.00 | 0.219 | 0.093 | 0.030 | 18.8 |
| ouro=3 -> pred=2 (leve) | 67 | 0.806 | 0.597 | 2.58 | 0.39 | 1.63 | 0.00 | 0.392 | 0.183 | 0.209 | 24.8 |
| ouro=3 -> pred=3 (acerto ref) | 11 | 1.000 | 0.545 | 4.45 | 0.00 | 0.00 | 0.00 | 0.558 | 0.314 | 0.273 | 41.1 |
| ouro=2 -> pred=1 (subavaliado) | 89 | 0.517 | 0.562 | 1.09 | 0.60 | 2.82 | 0.01 | 0.224 | 0.101 | 0.022 | 16.4 |
| ouro=2 -> pred=2 (acerto ref) | 52 | 0.731 | 0.692 | 2.83 | 0.42 | 1.87 | 0.04 | 0.344 | 0.151 | 0.096 | 24.5 |
| ouro=1 -> pred=1 (acerto ref) | 107 | 0.421 | 0.607 | 0.93 | 0.61 | 3.13 | 0.04 | 0.159 | 0.069 | 0.000 | 14.5 |
| ouro=0 -> pred>=1 (indulgente) | 65 | 0.200 | 0.692 | 0.91 | 0.75 | 3.28 | 0.06 | 0.158 | 0.068 | 0.000 | 16.0 |
| ouro=0 -> pred=1 (indulgente) | 63 | 0.175 | 0.683 | 0.86 | 0.75 | 3.29 | 0.06 | 0.154 | 0.067 | 0.000 | 16.1 |
| ouro=0 -> pred=0 (acerto ref) | 85 | 0.412 | 0.588 | 0.15 | 0.01 | 4.41 | 0.02 | 0.060 | 0.027 | 0.000 | 7.2 |

**Leitura dos mecanismos de erro:**
1. **Checklist rigorosa inflada por conceitos extras:** o prompt pede incluir todos os conceitos-chave + *até 2 ideias essenciais adicionais* do gabarito. Em `61.5%` dos 595 diagnósticos o modelo adiciona conceitos extras (média `+1.06` conceito). Mesmo quando a resposta é `ouro=3` e cai para `pred<=1` (`n=67`), a média de conceitos `ausente` sobe para `2.75` enquanto `erros_conceituais` é zero em `53.7%` dos casos.
2. **Armadilha de múltiplos gabaritos alternativos:** respostas curtas `ouro=3 -> pred<=1` atingem em média `21.9%` dos termos de *um* gabarito específico contra apenas `9.3%` da *união* de todos os gabaritos (`3.0%` têm alta sobreposição com 1 gabarito e baixa com a união). O `DIAG_USER` apresenta `GABARITO` como lista única de respostas de professores sem explicitar que **basta atender a uma formulação equivalente**.
3. **Indulgência na nota 0 (`ouro=0 -> pred>=1`, `n=65`):** em `96.9%` desses casos o diagnoser marcou ao menos 1 conceito como `presente` ou `parcial`, e em `93.8%` listou ao menos 1 `acerto` positivo (puxando a nota para `1`), mesmo quando a rubrica humana deu `0`. Como resultado, há sobreposição de sinal entre respostas `ouro=0` mal-rejeitadas e `ouro=2` excessivamente penalizadas na classe `pred=1`.
4. **Saturação em 3 lacunas e falsos erros conceituais (cruzamento com `H-03`/`H-04`):** em `97.8%` de todo o E0 (`582/595`), o modelo preenche o teto de 3 `lacunas_prioritarias` — incluindo `92.4%` (`134/145`) dos itens `ouro=3` e `98.7%` (`148/150`) dos `ouro=2` — enquanto `30.3%` dos `ouro=3` recebem ao menos 1 `erro_conceitual`. Em `15/1750` lacunas (`2.5%` dos itens) não há sequer respaldo lexical mínimo (`>=4` chars) nos gabaritos/conceitos (além de casos qualitativos documentados em `H-04` onde o diagnóstico rejeita sinônimos ou confunde omissão com erro conceitual).

---

## 4. `diagnoser` (`gpt-4o-mini` + `DIAG_USER`) vs. `grader` (`gemini-2.5-flash` + `GRADER_USER`) em `n = 180`

| comparacao | n | QWK | Spearman | MAE | bias_medio | acc_exata | taxa_subavaliacao | taxa_superavaliacao |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diagnoser_vs_ouro | 180 | 0.539 | 0.557 | 0.489 | -0.078 | 0.528 | 0.272 | 0.200 |
| grader_vs_ouro | 180 | 0.597 | 0.653 | 0.572 | +0.328 | 0.489 | 0.122 | 0.389 |
| diagnoser_vs_grader | 180 | 0.629 | 0.749 | 0.494 | -0.406 | 0.550 | 0.406 | 0.044 |

Matrizes de confusão lado a lado (`n = 180`, onde `grade ∈ {0, 1, 2}`):
```
DIAGNOSER (gpt-4o-mini, DIAG_USER) vs Ouro:
       pred=0  pred=1  pred=2  pred=3
ref=0      36      23       1       0
ref=1      10      39      11       0
ref=2       2      37      20       1

GRADER (gemini-2.5-flash, GRADER_USER) vs Ouro:
       pred=0  pred=1  pred=2  pred=3
ref=0      36      19       4       1
ref=1       6      28      21       5
ref=2       0      16      24      20
```

- **Conclusão desta comparação:** no subconjunto piloto de `180` itens (`grade ∈ {0,1,2}`), o `grader` supera o `diagnoser` em QWK (`0.597` vs `0.539`), Spearman (`0.653` vs `0.557`) e acurácia binária `>=2` (`73.9%` vs `71.7%`), enquanto o `diagnoser` mantém maior `acc_exata` (`52.8%` vs `48.9%`) e menor MAE (`0.489` vs `0.572`). O motivo é a assimetria oposta dos dois prompts: o `diagnoser` ainda derruba `37/60` (`61.7%`) dos `ouro=2` para `pred=1` (`bias = -0.078`), enquanto o `grader` tem viés positivo (`bias = +0.328`), acertando `24/60` (`40.0%`) em `ouro=2` mas promovendo `20/60` (`33.3%`) para `3` e superavaliando `38.9%` dos itens. Além disso, o `diagnoser` sobe de QWK = `0.487` (`n=595`) para `0.539` (`n=180`) simplesmente porque o piloto exclui `grade=3` (onde ocorre o pior colapso conservador). Entre si, os dois modelos têm forte correlação de ordem (`Spearman = 0.749`, `QWK = 0.629`), confirmando que o gargalo central em `DIAG_USER` é de **calibração e rigidez da checklist**, não ausência total de sinal.

---

## 5. Recalibração Pós-Hoc em Leave-One-Question-Out (15 folds LOGO)

Todos os métodos abaixo foram ajustados **exclusivamente nos 14 folds de treino** e avaliados na questão retida (sem vazamento). O ajuste de limiares ordinais usou escores *out-of-fold* internos nos 14 folds de treino.

| metodo | n | QWK | Spearman | Pearson | MAE | bias_medio | acc_exata | acc_tol1 | acc_binaria_ge2 | taxa_subavaliacao | taxa_superavaliacao |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_raw | 595 | 0.487 | 0.580 | 0.581 | 0.703 | -0.380 | 0.429 | 0.872 | 0.677 | 0.413 | 0.158 |
| shift_constante_logo | 595 | 0.487 | 0.580 | 0.581 | 0.703 | -0.380 | 0.429 | 0.872 | 0.677 | 0.413 | 0.158 |
| remap_nota_logo | 595 | 0.500 | 0.504 | 0.500 | 0.768 | -0.002 | 0.442 | 0.797 | 0.635 | 0.271 | 0.287 |
| linear_diag_features_logo | 595 | 0.510 | 0.549 | 0.543 | 0.706 | -0.044 | 0.393 | 0.903 | 0.729 | 0.316 | 0.291 |
| ordinal_thresholds_logo | 595 | 0.575 | 0.577 | 0.582 | 0.711 | +0.166 | 0.439 | 0.862 | 0.703 | 0.217 | 0.345 |

- **Parâmetros aprendidos nos 15 folds LOGO:**
  - `shift_constante_logo`: deltas selecionados = `{0: 15}` (um deslocamento uniforme `+1` melhora `ouro=2/3` mas estraga `ouro=0`, levando QWK para `0.487`).
  - `remap_nota_logo`: mapeamentos `{(0, 1, 3, 3): 11, (0, 2, 3, 3): 4}` (ou seja, manter `0->0`, subir `1->2` ou `2->3` conforme o fold já elimina boa parte do viés conservador com QWK = `0.500`).
  - `ordinal_thresholds_logo`: média dos limiares nos 15 folds = `(0.71, 1.45, 1.91)` (em vez de `0.50, 1.50, 2.50`), atingindo **QWK = `0.575`** e `acc_binaria(>=2) = 70.3%`.

### Impacto da recalibração LOGO por questão (QWK antes vs. depois)
| question_id | baseline_raw | shift_constante_logo | remap_nota_logo | linear_diag_features_logo | ordinal_thresholds_logo | ganho_remap | ganho_ordinal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 0.179 | 0.179 | 0.209 | 0.412 | 0.326 | +0.031 | +0.148 |
| 37 | 0.394 | 0.394 | 0.284 | 0.344 | 0.269 | -0.110 | -0.125 |
| 38 | 0.551 | 0.551 | 0.573 | 0.634 | 0.636 | +0.021 | +0.085 |
| 39 | 0.537 | 0.537 | 0.594 | 0.528 | 0.740 | +0.057 | +0.203 |
| 40 | 0.586 | 0.586 | 0.571 | 0.618 | 0.724 | -0.014 | +0.139 |
| 41 | 0.462 | 0.462 | 0.490 | 0.471 | 0.538 | +0.029 | +0.076 |
| 42 | 0.443 | 0.443 | 0.311 | 0.302 | 0.421 | -0.132 | -0.022 |
| 43 | 0.780 | 0.780 | 0.567 | 0.695 | 0.712 | -0.213 | -0.069 |
| 44 | 0.361 | 0.361 | 0.500 | 0.353 | 0.442 | +0.139 | +0.081 |
| 45 | 0.784 | 0.784 | 0.759 | 0.684 | 0.746 | -0.025 | -0.038 |
| 46 | 0.542 | 0.542 | 0.612 | 0.348 | 0.561 | +0.071 | +0.020 |
| 47 | 0.351 | 0.351 | 0.398 | 0.468 | 0.541 | +0.047 | +0.190 |
| 48 | 0.234 | 0.234 | 0.324 | 0.419 | 0.432 | +0.090 | +0.198 |
| 49 | 0.278 | 0.278 | 0.316 | 0.583 | 0.579 | +0.038 | +0.301 |
| 50 | 0.756 | 0.756 | 0.827 | 0.716 | 0.827 | +0.071 | +0.071 |

**Diagnóstico final calibração vs. discriminação:**
- **Questões recuperadas por calibração pós-hoc (`ganho_ordinal >= +0.13`):** `q49` (`0.278` → `0.579`), `q39` (`0.537` → `0.740`), `q48` (`0.234` → `0.432`), `q47` (`0.351` → `0.541`), `q36` (`0.179` → `0.326`), `q40` (`0.586` → `0.724`). Nelas, a ordenação já existia (`Spearman` entre `0.52` e `0.75`, salvo `q36` e `q48` mais ruidosas), e o erro vinha de deslocamento de escala.
- **Questões que permanecem difíceis mesmo após recalibração (`QWK_ordinal < 0.45`):** `q37` (`0.394` → `0.269`), `q36` (`0.179` → `0.326`), `q42` (`0.443` → `0.421`), `q48` (`0.234` → `0.432`), `q44` (`0.361` → `0.442`). Essas concentram o verdadeiro erro de *discriminação* semântica/rubrica (em `q37`, `q42`, `q44` e `q48`, `80%` dos `ouro=0` sobem para `>=1`, enquanto em `q36`, `q44` e `q48` há forte compressão de `ouro=2/3`, e `q42` soma `8` conceitos esperados e `4` gabaritos), exigindo revisão de prompt/few-shot em `H-02`.

---

## 6. Recomendações Diretas para `H-02` (Calibração do Prompt `DIAG_USER`)

1. **Remover a obrigação de extrair conceitos extras além dos conceitos-chave** no `DIAG_USER` (ou separar explicitamente conceitos obrigatórios vs. complementares para não inflar `ausente`).
2. **Explicitar regra de gabaritos alternativos e equivalência semântica:** instruir que as respostas em `GABARITO` são *exemplos independentes/equivalentes* de professores, que sinônimos/variações corretas de nomenclatura devem ser aceitos (cf. achado de `H-04` na `q42`), e que o aluno **não precisa combinar detalhes exclusivos de todos os gabaritos** para receber `nota_estimada = 2` ou `3`.
3. **Permitir `0–3` lacunas reais e separar omissão de erro conceitual (handoff `H-03`/`H-04`):** trocar `"<até 3 ideias...>"` por permissão explícita de lista vazia (`[]`) quando não houver lacuna relevante (`ouro=2/3`), evitando que `A1` sobre-remedie ou invente lacunas fora do gabarito; instruir explicitamente que **omissão não é erro conceitual** e proibir inventar erros não respaldados pelo gabarito.
4. **Calibrar as âncoras da escala `0–3` com critério explícito de corte entre `1` e `2` e entre `0` e `1`:**
   - `0`: não apresenta nenhum conceito-chave correto ou responde algo errado/fora do núcleo da pergunta (não promover chute vago ou repetição do enunciado para `1`);
   - `1`: acerta apenas parte secundária ou com erro conceitual importante;
   - `2`: acerta o núcleo da pergunta de forma compatível com um gabarito, faltando só um conceito específico ou precisão;
   - `3`: cobre as ideias essenciais de um gabarito completo (mesmo em linguagem simples/curta de 8º/9º ano, sem exigência de jargão extra).
5. **Few-shot sem vazamento usando o holdout do PT-ASAG:** selecionar 2–4 exemplos âncora (ex.: notas `0, 1, 2, 3`) exclusivamente dentre as **`6501` respostas fora do `diag_set`** (nunca usar itens do próprio `diag_set` nem vazar nota-ouro em inferência; o texto-exemplo ilustra apenas critérios públicos de rubrica).
6. **Protocolo barato de validação em `H-02`:** validar primeiro em um subconjunto estratificado (ex.: `60` itens = 4 por questão × 4 notas, priorizando as questões críticas `q36`, `q37`, `q42`, `q44`, `q47`, `q48`, `q49` + questões de referência alta) antes de re-executar os `595` itens de E0.