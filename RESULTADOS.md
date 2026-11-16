# Resultados iniciais (piloto, 2026-11-16)

Execução real: 595 respostas no E0 e 180 no piloto (15 questões × notas {0,1,2} × 4), 5 condições. 0 erros de API. Tabelas completas: [`results/summary.md`](results/summary.md) e CSVs em `results/`.

**Modelos** (via OpenRouter): diagnóstico, geração e verificação = `openai/gpt-4o-mini`; juiz e corretor = `google/gemini-2.5-flash` (família diferente); aluno simulado = `meta-llama/llama-3.1-8b-instruct`. Custo total ≈ US$ 2,4 (≈ 4,4 M tokens de entrada e 1,0 M de saída).

## O que os dados sustentam

1. **E0 – diagnóstico.** QWK = 0,487, Spearman = 0,580, MAE = 0,70, acerto binário (nota ≥ 2) = 67,7%. O diagnóstico é **conservador**: das respostas nota 3, só 11 de 145 foram classificadas como 3 (a maioria ficou em 1 ou 2), e das nota 2, 89 de 150 ficaram em 1. Para comparação, a concordância entre humanos no PT-ASAG original foi r = 0,581 (Pearson, só nas respostas dupla-avaliadas), então o diagnóstico está perto do teto humano em correlação, mas erra a calibração.
2. **Adaptação > estático, onde é esperado.** A1 − S_estático: `foco_na_lacuna` +0,80 [0,56; 1,03] e `utilidade_pedagogica` +0,52 [0,33; 0,69], ambos significativos após Holm; questões com `relevância à lacuna` +0,24. Coerência, correção conceitual e fidelidade ao gabarito **não diferem** (sem perda de qualidade). O texto de A1 e S tem o mesmo tamanho (≈ 159 palavras), então a diferença **não** vem de verbosidade. O efeito é maior nas notas 1 e 2 (foco +1,13 e +0,85) do que na nota 0 (+0,42).
3. **Texto de apoio vs só o gabarito (S0).** A1 vence com folga em todas as dimensões (p < 0,001), mas S0 é bem mais curto (84 palavras) e não foi escrito como material didático, então este contraste é um piso, não evidência forte.
4. **E3 (exploratório).** Todos os materiais elevam a nota do aluno simulado em relação a "sem material" (ganho 0,45 → 1,2–1,4). A1 − S_estático = +0,14 [0,02; 0,27], p = 0,046, **não significativo após Holm** (p = 0,122). Não se sustenta uma vantagem de ganho de A1 nesta amostra.

## O que os dados NÃO sustentam (ou pedem cautela)

- **O diagnóstico explícito (A1 vs A0) não mostrou ganho claro.** Nenhuma dimensão passa em Holm; `foco_na_lacuna` é praticamente igual (+0,02). Só `utilidade` tem tendência (+0,12, n.s.). Portanto, nesta rodada, a hipótese "o diagnóstico explícito melhora o material" **não foi confirmada**.
- **A verificação anti-alucinação (A2) não trouxe benefício mensurável.** O verificador reescreveu 73,9% dos textos (1,21 afirmações "não suportadas" por texto), mas as afirmações realmente incorretas já eram quase nulas em A1 (0,01 por texto, segundo o juiz). Efeito de teto: com gpt-4o-mini neste domínio escolar, há pouca alucinação para mitigar. O verificador é do mesmo modelo que o gerador, o que limita o que ele detecta.
- **O juiz par-a-par é pouco confiável.** O 1º material vence só 11–13% das vezes nos pares com A1 (forte viés de posição) e a consistência entre as duas ordens é de 23–27% em A1×S e A1×A0. Por isso o par-a-par só vale pelas vitórias "robustas" (mesmo vencedor nas duas ordens), e mesmo essas conflitam com o juiz absoluto: no par A2×A1, A1 vence mais (21,7% × 7,2%), enquanto na nota absoluta A2 é ligeiramente melhor. Recomendo reportar o juiz absoluto como principal e o par-a-par como análise de viés.
- **Efeito de teto no juiz absoluto.** As notas ficam em 4,6–4,9 de 5; há pouca margem para separar condições boas. A correlação entre tamanho e nota é positiva (Spearman 0,13–0,37), o que confirma o viés de verbosidade documentado por Zheng et al. (2023), embora A1 e S tenham o mesmo tamanho.
- **Itens agrupados por questão.** Só 15 questões; os testes pareados tratam os 180 itens como independentes, o que **subestima a incerteza**. Para o artigo, use bootstrap por questão ou modelo misto.
- **Sem humanos ainda.** Todos os números de qualidade vêm do juiz LLM; a validação humana (E2) está preparada em `human_eval/` mas não foi preenchida.

## Próximos passos sugeridos

1. Rodar o E2 com 2–3 avaliadores e medir a concordância humano × juiz (`scripts/07_judge_human_agreement.py`).
2. Tornar o juiz mais discriminante (âncoras de rubrica mais estritas, ou nota de 1–10) e usar um 2º juiz de outra família.
3. Calibrar o diagnóstico (few-shot com exemplos nota 2 e 3 do PT-ASAG) e repetir o E0.
4. Para testar A2, usar um gerador mais fraco (ex.: Llama 8B), que alucina mais, ou um verificador de família diferente.
5. Repetir com mais de uma semente de geração e análise com cluster por questão.
