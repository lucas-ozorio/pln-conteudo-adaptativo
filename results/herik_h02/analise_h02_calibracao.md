# Análise H-02: testes e execução real das variantes calibradas do diagnóstico (RQ1 / E0)

Execução feita em 2026-11-22 na branch `herik/rq1-diagnostico-e-variantes`, a partir do commit `6ec7b9c`, com o harness `scripts/run_h02_calibration.py`. As variantes são v1 e v2, o padrão do script. A chave usada é a do OpenRouter do projeto, e o diagnosticador é o `openai/gpt-4o-mini`, com temperatura 0.

## 1. Resumo

- Todo o encanamento passou antes de gastar: testes, reprodução das análises offline, `--dry-run` e `--mock`.
- O piloto (60 itens) e a rodada completa (595 itens) não tiveram nenhuma falha: 1.190 chamadas, 0 erros, 0 notas nulas. O custo total foi **US$ 0,32**.
- Com os 595 itens, as duas variantes melhoram o QWK em relação ao baseline, e o ganho continua significativo depois de Holm:
  - **v1** (rubrica corrigida, zero-shot): 0,487 → **0,548** (Δ +0,061 [0,033; 0,086]).
  - **v2** (v1 + 4 âncoras de outra questão): 0,487 → **0,580** (Δ +0,093 [0,062; 0,121]).
- A v2 quase elimina o viés conservador, que vai de −0,38 para −0,07. Ela supera o baseline em 14 das 15 questões.
- A v2 empata no QWK com a melhor recalibração offline (`ordinal_thresholds_logo`, 0,575, em `results/herik_e0/`) e fica melhor em MAE, viés e Pearson.
- Há efeitos colaterais:
  - Mais respostas nota 0 recebem nota ≥ 1.
  - As variantes listam menos conceitos do que os esperados em 24–31% dos itens.
  - A maioria das notas 3 ainda é prevista como 2.

## 2. O que foi rodado

| Etapa | Comando | Chama a API? | Resultado |
|---|---|---|---|
| Testes do H-02 | `python tests/test_h02_calibration.py` | não | 3/3 ok (holdout = 6.501 sem vazamento; prompts sem nota-ouro; pilot60 determinístico) |
| Testes do projeto | `python tests/test_basic.py` | não | 4/4 ok |
| Reprodução do H-01 | `python scripts/analyze_e0_calibration.py` | não | `results/herik_e0/` idêntico ao commitado |
| Reprodução do H-03/H-04 | `python scripts/analyze_variants_a1_a0_s.py` | não | `results/herik_variants/` idêntico; 2 CSVs diferem só por ruído de float (~1e-16) |
| Estimativa | `run_h02_calibration.py --dry-run` | não | a chave é detectada; estimativa de US$ 0,04 (pilot60) e US$ 0,40 (full595) |
| Encanamento | `run_h02_calibration.py --mock --subset pilot60` (v1, v2, v3) | não | 180 chamadas sintéticas, 0 erros, relatório gerado em `results_mock/` |
| Piloto | `run_h02_calibration.py --subset pilot60` | sim | 120 chamadas, 0 erros |
| Completo | `run_h02_calibration.py --subset full595` | sim | 1.070 chamadas novas (os 60 do piloto vieram do cache), 0 erros |

Conferências feitas depois da rodada:

- Cada variante tem 595 `item_id` únicos, sem nenhum `nota_estimada` nulo e sem nenhum `_error`.
- O pareamento com `outputs/diagnosis.jsonl` é exato: 595/595.

## 3. Custo

| Rodada | Chamadas | Tokens in / out | Custo (saldo do OpenRouter) |
|---|---|---|---|
| Piloto (pilot60, v1 + v2) | 120 | 129.736 / 22.446 | US$ 0,033 |
| Completo (+535 itens × 2) | 1.070 | 1.155.464 / 196.042 | US$ 0,283 |
| **Total H-02** | **1.190** | **1.285.200 / 218.488** | **US$ 0,316** |

- O custo real ficou abaixo da estimativa do `--dry-run` (US$ 0,40). Os diagnósticos novos são mais curtos: em média 184 tokens de saída, contra 258 do baseline. Isso acontece porque eles têm menos lacunas e menos conceitos extras.
- Como o cache fica em `outputs/h02/cache_openrouter.jsonl`, rodar de novo os mesmos comandos não custa nada. O cache guarda só o hash do prompt e a resposta; as âncoras do holdout não ficam gravadas.

## 4. Resultado principal (595 itens)

IC de 95% por bootstrap por questão: 15 clusters, 5000 reamostras, `default_rng(0)`. Os números vêm de `h02_comparacao_variantes.csv`.

| Variante | QWK [IC] | Spearman | Pearson | MAE | Viés médio | Acurácia exata |
|---|---|---|---|---|---|---|
| v0 baseline | 0,487 [0,387; 0,586] | 0,580 | 0,581 | 0,703 | −0,380 | 0,429 |
| v1 rubrica calibrada | 0,548 [0,450; 0,639] | 0,591 | 0,583 | 0,671 | −0,166 | 0,430 |
| v2 few-shot cross-q | **0,580** [0,480; 0,678] | **0,609** | **0,606** | **0,635** | **−0,067** | **0,455** |
| *ref.: `ordinal_thresholds_logo` (H-01, offline)* | *0,575* | *0,577* | *0,582* | *0,711* | *+0,166* | *0,439* |

Contrastes pareados de QWK. Os p-valores são bootstrap bilaterais, e o Holm foi aplicado na família dos 2 contrastes contra o baseline:

| Contraste | Δ QWK | IC 95% | p bootstrap | p Holm |
|---|---|---|---|---|
| v1 − v0 | +0,061 | [0,033; 0,086] | 0,0004 | 0,0004 |
| v2 − v0 | +0,093 | [0,062; 0,121] | ≤ 0,0002 (nenhuma reamostra ≤ 0) | 0,0004 |
| v2 − v1 *(exploratório, fora da família)* | +0,032 | [0,001; 0,064] | 0,044 | — |

A v2 supera a v1, mas a diferença é marginal: o IC quase toca o zero.

## 5. Onde o diagnóstico mudou

| Indicador | v0 | v1 | v2 |
|---|---|---|---|
| Previsões iguais a 1 | 54,5% | 48,1% | 40,5% |
| Nota 3 prevista como 3 | 7,6% | 19,3% | 21,4% |
| Nota 3 prevista como ≤ 1 | 46,2% | 29,7% | **20,0%** |
| Nota 2 prevista como 1 | 59,3% | 48,0% | **35,3%** |
| Nota 0 prevista como ≥ 1 | 43,3% | 53,3% | 52,7% |
| Nota 3 com exatamente 3 lacunas | 92,4% | 6,2% | **4,1%** |
| Nota 3 com algum "erro conceitual" | 30,3% | 2,8% | **2,8%** |
| Alguma lacuna sem respaldo no gabarito | 2,5% | 0,2% | 0,3% |
| Conceitos listados − esperados (média) | +1,06 | −0,54 | −0,41 |
| Itens com **menos** conceitos que os esperados | 0% | 30,6% | 23,7% |

As matrizes de confusão completas estão em `h02_relatorio.md`. A linha da nota 3 resume bem a mudança:

| Variante | pred = 0 | pred = 1 | pred = 2 | pred = 3 |
|---|---|---|---|---|
| v0 | 2 | 65 | 67 | 11 |
| v2 | 0 | 29 | 85 | 31 |

Leitura:

- As regras novas atacam as três causas apontadas no H-01:
  - cobrar a combinação de todos os gabaritos;
  - tratar omissão como erro;
  - forçar 3 lacunas.
- Elas praticamente eliminam o "erro conceitual" inventado e as 3 lacunas automáticas nas respostas nota 3.
- O ganho de QWK vem sobretudo de tirar as notas 2 e 3 do "1".
- O preço é uma leve superestimação da nota 0, onde mais respostas recebem 1.

## 6. Por questão

| Questão | v0 | v1 | v2 | Δ v2 − v0 |
|---|---|---|---|---|
| 36 | 0,179 | 0,225 | 0,303 | +0,124 |
| 37 | 0,394 | 0,489 | 0,422 | +0,028 |
| 38 | 0,551 | 0,638 | 0,605 | +0,054 |
| 39 | 0,537 | 0,671 | 0,667 | +0,130 |
| 40 | 0,586 | 0,515 | 0,545 | **−0,041** |
| 41 | 0,462 | 0,528 | 0,488 | +0,026 |
| 42 | 0,443 | 0,578 | 0,590 | +0,147 |
| 43 | 0,780 | 0,833 | 0,859 | +0,079 |
| 44 | 0,361 | 0,500 | 0,500 | +0,139 |
| 45 | 0,784 | 0,791 | 0,883 | +0,099 |
| 46 | 0,542 | 0,577 | 0,700 | +0,158 |
| 47 | 0,351 | 0,417 | 0,419 | +0,068 |
| 48 | 0,234 | 0,266 | 0,274 | +0,040 |
| 49 | 0,278 | 0,265 | 0,412 | +0,134 |
| 50 | 0,756 | 0,793 | 0,826 | +0,070 |

- A v2 é melhor em 14 de 15 questões, e a v1 em 13 de 15 (cai na 40 e, por pouco, na 49).
- A questão 40 é a doadora das âncoras da v2 para as outras 14. Mas ela piora também na v1, que não tem exemplos, então a queda não vem do few-shot.

## 7. Piloto × completo

| Variante | QWK pilot60 | Δ vs. v0 [IC] | QWK full595 | Δ vs. v0 [IC] |
|---|---|---|---|---|
| v0 | 0,518 | — | 0,487 | — |
| v1 | 0,524 | +0,006 [−0,055; 0,068] | 0,548 | +0,061 [0,033; 0,086] |
| v2 | 0,598 | +0,080 [−0,038; 0,195] | 0,580 | +0,093 [0,062; 0,121] |

- O piloto acertou a direção, mas, com 4 respostas por questão, não conseguia separar o efeito do zero.
- O efeito da v1 só aparece no conjunto completo.

## 8. Limitações e pontos de atenção

1. **Conceitos omitidos.** Em 24–31% dos itens, as variantes listam menos conceitos-chave do que os esperados. Antes, o baseline adicionava conceitos extras em 62% dos itens. Isso pode ser fusão de conceitos ou omissão real. Vale uma inspeção manual antes de usar esse diagnóstico para gerar material, porque o A1 depende da lista de conceitos e lacunas.
2. **Superestimação da nota 0.** De 43% para cerca de 53% das respostas nota 0 recebem nota ≥ 1.
3. **A nota 3 ainda é rara.** Só 21% das respostas nota 3 são previstas como 3, e a maioria vira 2. O viés conservador diminuiu, mas não sumiu.
4. **Só a nota é validada.** O PT-ASAG não anota equívocos, então a qualidade de `erros_conceituais` e `lacunas_prioritarias` não é medida diretamente. A queda de erros inventados é um indicador indireto.
5. **Não muda a RQ2/RQ3.** Os materiais do E1 (A1/A2) do artigo foram gerados com o diagnóstico v0. Esse resultado reforça a RQ1, mas não altera os números de E1/E3. Usar v2 no pipeline exigiria gerar e julgar de novo.
6. **A v3 não foi rodada com API.** A v3 (âncoras da mesma questão) só passou pelos testes e pelo mock. O `--dry-run` estima cerca de US$ 0,20 para o full595; pela taxa real do v1/v2, o custo deve ficar em torno de US$ 0,16.
7. **Um único modelo e uma única execução.** Os resultados valem para o gpt-4o-mini com temperatura 0, sem repetições.

## 9. Como reproduzir

```powershell
# a chave fica na variável de usuário OPENROUTER_API_KEY (ou num .env, que é gitignored)
$env:OPENROUTER_API_KEY = [Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','User')
python scripts/run_h02_calibration.py --subset full595 --analyze-only   # só recalcula as métricas, sem API
python scripts/run_h02_calibration.py --subset full595                  # sai do cache, custo zero
```

Pré-requisito: `data/processed/` gerado por `python scripts/00_prepare_data.py`, além de `data/raw/PT_ASAG_2018_v2.0/` para o holdout da v2.

## 10. Arquivos

- `outputs/h02/diagnosis_v1_rubrica_calibrada.jsonl` e `diagnosis_v2_fewshot_cross_q.jsonl`: 595 diagnósticos por variante.
- `outputs/h02/cache_openrouter.jsonl`: cache das 1.190 respostas.
- `outputs/h02/usage_openrouter.jsonl`: tokens por chamada.
- `results/herik_h02/h02_relatorio.md`: relatório gerado pelo harness.
- `results/herik_h02/h02_comparacao_variantes.csv`, `h02_por_questao.csv` e `h02_matrizes_confusao.csv`: métricas do harness.
- `results/herik_h02/analise_h02_calibracao.md`: este relatório. Os p-valores, o v2 − v1, o Pearson e a contagem de conceitos foram calculados à parte, sobre os mesmos arquivos e com o mesmo bootstrap.
