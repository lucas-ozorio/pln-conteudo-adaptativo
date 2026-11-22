# Guia de Integração — Contribuição `RQ2`/`RQ3` (Herik)

Pacote com os resultados de **`H-03` (quantitativa) + `H-04` (qualitativa)** sobre A1 × A0 × S, pronto para entrar no `paper/main.tex` sem conflito de merge (nenhum arquivo existente do artigo foi editado).

## Arquivos deste pacote

- `paper/herik_contrib/rq2_rq3_draft.tex`: 5 blocos de texto em inglês (§5.2, §5.3, Discussion, Limitations, Apêndice). **É gerado pelo script**: não edite à mão, ou o próximo `python ...` sobrescreve.
- `paper/herik_contrib/tab_rq3_length_and_strat.tex`: tabela (`table*`) com (a) controle de tamanho A1−A0, (b) estratos por nota-ouro e (c) estratos por erro de nota do diagnóstico.
- `paper/herik_contrib/tab_rq3_qualitative_summary.tex`: tabela (`table*`, apêndice) com os mecanismos qualitativos e a evidência numérica de cada um.
- Script gerador: `scripts/make_herik_variants_assets.py`. Ele lê só `results/herik_variants/` e não usa API nem `data/`.

Os dois `.tex` de tabela têm só o `tabular`. O `\begin{table*}`, o `\caption` e o `\label` estão no `rq2_rq3_draft.tex`, no mesmo padrão do pacote RQ1. Pacotes LaTeX usados: só `booktabs` (já carregado no `main.tex`).

## Onde colar no `paper/main.tex`

Os números de linha abaixo valem para o `main.tex` **atual (243 linhas, antes do pacote RQ1)**. O pacote RQ1 (`INTEGRACAO_RQ1.md`) mexe nas linhas 32, 132–140, 196 e 215+, o que desloca as linhas. **Aplique de baixo para cima** ou localize pelo texto-âncora entre aspas. RQ1 e RQ2/RQ3 não editam o mesmo parágrafo: RQ1 usa `\textbf{Diagnosis.}` (L196), e este pacote usa `\textbf{Scope.}` (L194) e `\textbf{Generation.}` (L197).

| Bloco | Onde (`main.tex` atual) | Ação |
| :--- | :--- | :--- |
| **BLOCO 5** (tabela) | Fim de `\subsection{Additional tables}`, depois da tabela `tab:pairwise` (após L238) | Inserir o `table*` com `tab_rq3_qualitative_summary.tex` |
| **BLOCO 5** (texto) | `\subsection{Qualitative example}`, L241: última frase *"A0 also acknowledges chloroplasts, but adds content not in the reference answers (vacuoles)."* | Substituir essa frase pelo parágrafo do bloco (que a repete e acrescenta a recorrência real) |
| **BLOCO 4** | `\section*{Limitations}`, L194 (`\textbf{Scope.}`) e L197 (`\textbf{Generation.}`) | Substituir os dois parágrafos |
| **BLOCO 3** | `\paragraph{What it does not support.}`, L185: trecho do item *"(i)~That an explicit diagnosis stage is needed: ... which we did not evaluate."* | Substituir só o item (i); manter (ii) e (iii) |
| **BLOCO 2** | `\subsection{Questions}`, L169: frase *"Gap relevance is higher for adaptive conditions (A1: $4.43$ vs. S: $4.19$; ...)."* | Substituir essa frase |
| **BLOCO 1** | `\paragraph{Does the explicit diagnosis help?}`, L166 | Substituir o parágrafo inteiro pelos 3 parágrafos + o `table*` com `tab_rq3_length_and_strat.tex` |

Se faltar espaço no corpo, a tabela `tab:rq3_length` pode ir para o apêndice; o texto do BLOCO 1 continua válido porque cita a tabela por `\ref`.

## Pontos de atenção na integração

1. **ICs:** o BLOCO 1 cita só estimativas pontuais para A1−A0 em foco e utilidade e remete à `tab:contrasts` para os ICs. Motivo: os ICs de `results/herik_variants/` vêm de outra semente de bootstrap e diferem do `cluster_e1_contrastes.csv` na 2ª casa (utilidade `[-0.02, 0.28]` aqui vs `[-0.03, 0.28]` no artigo). As estimativas pontuais são idênticas. A legenda da `tab:rq3_length` avisa disso.
2. **Exemplo qualitativo:** o BLOCO 5 mantém o exemplo do vacúolo, mas mostra que ele é ocasional: em 4/12 itens da q36 o A0 cita vacúolo, e em 2 deles o próprio aluno tinha mencionado. Não generalize para "A0 sai do gabarito".
3. **Confundidor de desenho:** o BLOCO 3 registra que os prompts de A1 e A0 diferem em mais que o diagnóstico (analogia, tom, chamadas separadas, conceitos-chave). Isso enfraquece qualquer afirmação causal do tipo "o diagnóstico melhora a coerência".
4. **Diagnóstico usado:** todos os números de RQ2/RQ3 vêm dos materiais gerados com o diagnóstico **v0** (sem a calibração de H-02). Isso é coerente com a nota de escopo do BLOCO 2 de `rq1_draft.tex`.
5. **CC BY-NC-SA 4.0:** nenhum bloco novo reproduz resposta de aluno. Os casos são citados por `item_id` e por resumo; o único trecho de aluno continua sendo o que já está no `main.tex` (L241).

## Como regenerar

```powershell
python scripts/analyze_variants_a1_a0_s.py      # (opcional) recalcula results/herik_variants/ a partir de outputs/
python scripts/make_herik_variants_assets.py    # regenera as 2 tabelas e o rq2_rq3_draft.tex
```

O segundo script falha (`AssertionError`) se algum número-chave divergir de `results/herik_variants/analise_a1_a0_s.md`.

## Origem dos números

| Afirmação | Fonte |
| :--- | :--- |
| A1−A0, A1−S, A0−S por dimensão | `h03_01_contrastes_brutos.csv` |
| A1 mais longo em 99,4%; Δ mediano 37 | `h03_02_distribuicao_palavras.csv` |
| Regressão com efeito fixo de item e `log(palavras)` | `h03_03_regressao_efeito_fixo_item.csv` |
| α a tamanho igual, Spearman Δpalavras×Δnota | `h03_04_delta_palavras_vs_delta_nota.csv` |
| Tercis de Δpalavras | `h03_05_faixas_delta_palavras.csv` |
| Estratos por nota-ouro | `h03_06_estratificacao.csv` |
| Erro de nota do diagnóstico | `h03_08_erro_diagnostico.csv`, `h03_09_erro_diag_x_nota_ouro.csv` |
| Vitórias robustas 34×14, p de sinal, Mann-Whitney | recalculados de `h03_10_par_a_par_por_item.csv` |
| 26% de concordância absoluto×par | `h03_11_par_a_par_resumo.csv` |
| Termos fora do gabarito, espermatogênese na q42 | `h04_01_termos_tecnicos_fora_do_gabarito.csv` |
| Vacúolo | `h04_02_vacuolo.csv` |
| 51% de A0 < 120 palavras | `h04_03_painel_itens.csv` |
| Tamanho dos enunciados | `h04_04_tamanho_enunciados.csv` |
| 3 lacunas em 179/180 | `h04_05_lacunas_por_nota_ouro.csv` |
| Casos (`q36_3b0258ff`, `q37_4f1cecfe`, `q39_524585dd`, `q40_19368b9f`, `q42_9260e885`, `q43_da5a83a4`, `q45_2a7cf00f`) | `h04_06_casos_selecionados.csv` + seção H-04 de `analise_a1_a0_s.md` |
