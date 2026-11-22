# Relatório H-02 — Calibração do Diagnóstico (`RQ1` / E0)

Comparação estritamente pareada sobre **`n = 595` itens** de `data/processed/diag_set.jsonl` contra `v0_baseline` (`outputs/diagnosis.jsonl`).

## 1. Comparação Global das Variantes

| variante | n | QWK | QWK_ic_lo | QWK_ic_hi | delta_QWK_vs_v0 | Spearman | MAE | bias_medio | acc_exata | pct_pred_1 | pct_ouro3_pred_le1 | pct_ouro2_pred1 | pct_ouro0_pred_ge1 | media_conceitos_extras | pct_ouro3_3_lacunas | pct_ouro3_com_erro_conceitual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0_baseline | 595 | 0.487 | 0.387 | 0.586 | +0.000 | 0.580 | 0.703 | -0.380 | 0.429 | 0.545 | 0.462 | 0.593 | 0.433 | +1.06 | 0.924 | 0.303 |
| v1_rubrica_calibrada | 595 | 0.548 | 0.450 | 0.639 | +0.061 | 0.591 | 0.671 | -0.166 | 0.430 | 0.481 | 0.297 | 0.480 | 0.533 | -0.54 | 0.062 | 0.028 |
| v2_fewshot_cross_q | 595 | 0.580 | 0.480 | 0.678 | +0.093 | 0.609 | 0.635 | -0.067 | 0.455 | 0.405 | 0.200 | 0.353 | 0.527 | -0.41 | 0.041 | 0.028 |

## 2. Matrizes de Confusão

### `v0_baseline`
```
        pred=0  pred=1  pred=2  pred=3
ouro=0      85      63       2       0
ouro=1      16     107      27       0
ouro=2       7      89      52       2
ouro=3       2      65      67      11
```

### `v1_rubrica_calibrada`
```
        pred=0  pred=1  pred=2  pred=3
ouro=0      70      73       7       0
ouro=1      10      99      35       6
ouro=2       3      72      59      16
ouro=3       1      42      74      28
```

### `v2_fewshot_cross_q`
```
        pred=0  pred=1  pred=2  pred=3
ouro=0      71      66      13       0
ouro=1       5      93      44       8
ouro=2       4      53      76      17
ouro=3       0      29      85      31
```

## 3. QWK por Questão

| question_id | v0_baseline | v1_rubrica_calibrada | v2_fewshot_cross_q |
| --- | --- | --- | --- |
| 36 | 0.179 | 0.225 | 0.303 |
| 37 | 0.394 | 0.489 | 0.422 |
| 38 | 0.551 | 0.637 | 0.605 |
| 39 | 0.537 | 0.671 | 0.667 |
| 40 | 0.586 | 0.515 | 0.545 |
| 41 | 0.462 | 0.528 | 0.488 |
| 42 | 0.443 | 0.578 | 0.590 |
| 43 | 0.780 | 0.833 | 0.859 |
| 44 | 0.361 | 0.500 | 0.500 |
| 45 | 0.784 | 0.791 | 0.883 |
| 46 | 0.542 | 0.577 | 0.700 |
| 47 | 0.351 | 0.417 | 0.419 |
| 48 | 0.234 | 0.266 | 0.274 |
| 49 | 0.278 | 0.265 | 0.412 |
| 50 | 0.756 | 0.793 | 0.826 |
