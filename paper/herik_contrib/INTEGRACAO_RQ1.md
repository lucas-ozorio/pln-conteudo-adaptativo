# Guia de Integração — Contribuição `RQ1` (Herik)

Este pacote reúne todos os insumos prontos de **`H-01` + `H-02`** para integração direta no `paper/main.tex` sem conflito de merge (nenhum arquivo de `paper/main.tex` foi editado aqui).

## Arquivos deste pacote (`RQ1`)

- `paper/herik_contrib/rq1_draft.tex`: blocos LaTeX prontos em inglês (Abstract, §5.1, Limitations e Apêndice).
- `paper/herik_contrib/tab_rq1_calibration.tex`: tabela principal `v0` vs. `v1` vs. `v2` + linha de referência `LOGO` (`n = 595`).
- `paper/herik_contrib/tab_rq1_confusion_v2.tex`: matriz de confusão `4×4` de `v2`.
- `paper/herik_contrib/fig_rq1_per_question.pdf`: gráfico QWK por questão (`v0`, `v1`, `v2`).
- Script gerador (reprodutível sem API e sem `data/raw/`): `scripts/make_herik_rq1_assets.py`.

## Onde colar em `paper/main.tex`

1. **Abstract (linha 32):** substituir a frase *"Diagnoses correlate with gold grades..."* pelo **BLOCO 1** de `rq1_draft.tex`.
2. **Seção 5.1 — `Diagnosis (RQ1)` (linhas 132–140):** substituir pela seção completa do **BLOCO 2** (`\input{herik_contrib/tab_rq1_calibration.tex}` incluído; os caminhos relativos funcionam porque `main.tex` compila a partir de `paper/`).
   - *Nota de escopo científico:* o **BLOCO 2** mantém explícito que os materiais de E1/E3 (§§5.2–5.6) usam o diagnóstico `v0`, evitando inconsistência numérica no restante do artigo.
3. **Seção `Limitations` (linha 196):** substituir o parágrafo `\textbf{Diagnosis.}` pelo **BLOCO 3**.
4. **Apêndice (linhas 215+):** incluir os snippets do **BLOCO 4** (`tab_rq1_confusion_v2.tex`, `fig_rq1_per_question.pdf` e nota sobre `src/pln/prompts_h02.py`) se houver espaço de página; se precisar economizar espaço no corpo, `tab_rq1_calibration.tex` pode ir para o corpo ou apêndice mantendo `tab_confusion.tex` no apêndice.

## Como regenerar os assets de `RQ1`

```powershell
python scripts/make_herik_rq1_assets.py
```

## Origem auditada dos números

- `results/herik_h02/h02_comparacao_variantes.csv` (`v0 = 0.487`, `v1 = 0.548`, `v2 = 0.580`, ICs bootstrap por questão)
- `results/herik_h02/analise_h02_calibracao.md` (`p_holm = 0.0004`, custo US\$ 0,316 em 1.190 chamadas)
- `results/herik_e0/e0_recalibracao_logo.csv` (`ordinal_thresholds_logo = 0.575`)
- `results/herik_e0/e0_taxonomia_erros.csv` (`53.7%` e `51.7%` com zero erros conceituais)
