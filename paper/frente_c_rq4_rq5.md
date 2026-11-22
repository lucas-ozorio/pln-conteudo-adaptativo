# Frente C (João) — texto proposto para o artigo: RQ4, RQ5 e vieses do juiz

Entrega para quem consolida o `main.tex` (frente D). Tudo veio de análises offline (sem LLM):
`scripts/10_rq4_verificacao.py`, `11_rq5_copia.py` e `12_vieses_juiz.py` → `results/rq4_*`, `rq5_*`, `vies_*`.
Tabelas prontas em `paper/tables/`: `tab_rq4.tex`, `tab_rq5.tex`, `tab_bias.tex`, `tab_bias_pairwise.tex`.
Todos os IC são bootstrap por questão (15 clusters). Os testes daqui formam uma família **exploratória separada** e não alteram os 24 contrastes com Holm do artigo.

**Auditoria manual: feita** (50 afirmações, 1 anotador, cego ao veredito do verificador: 30 marcadas e 20 aceitas). Resultado em
`results/rq4_auditoria.csv` (`python scripts/10_rq4_verificacao.py --auditoria human_eval/auditoria_afirmacoes.csv`).

---

## Mudanças sugeridas (resumo)

1. **RQ4, no texto da Introdução:** reformular para *"Does reference-anchored, claim-level verification reduce incorrect content, and at what cost?"*.
2. **§5.4:** substituir pelo parágrafo abaixo e incluir `tab_rq4.tex` (A2−A1 em todos os itens e só nos reescritos).
3. **§5.5:** trocar a frase "Word count correlates positively with scores across conditions (Spearman 0.13–0.37)". Essa correlação vem da diferença **entre** condições (o S0 é curto e fraco); **dentro** de cada condição ela não aparece. Acrescentar o resultado de "mesmo texto, notas diferentes" e o teste dos pares idênticos. A `tab_bias_pairwise.tex` pode substituir a Tab. 6 (traz "Longer wins" e a concordância com o juiz absoluto); a `tab_bias.tex` vai no apêndice.
4. **§5.6:** acrescentar a medida de cópia e o contraste ajustado; incluir `tab_rq5.tex` no lugar da Tab. 4, que ela contém e amplia.
5. **Limitations:** atualizar os itens *Judge validity* e *Simulated student* (texto abaixo).
6. **Correção pontual em §5.4:** "+0.03 [0.01, 0.07]" deve ser "not significant after Holm correction" (o IC exclui zero).

---

## §5.4 Verification and hallucination (RQ4) — texto proposto

> The verifier decomposed each A1 text into 8.3 atomic claims on average: 46% *supported* by the reference, 39% *general-knowledge-correct*, 14% *unsupported* and only 0.1% *incorrect* (2 of 1,498 claims). Because any unsupported or incorrect claim triggered a rewrite, 133 of 180 texts (73.9%) were rewritten, almost always because of *unsupported* claims, which mainly reflect the brevity of the reference answers rather than errors. A blind manual audit of 50 sampled claims by one author shows what the flags capture: of 30 flagged claims, 67% [49, 81] were non-factual sentences (encouragement, transitions, analogies), 17% were scientifically correct, 10% were doubtful, and only 7% (2 of 30, both the same smoke-alarm analogy for CO$_2$) were incorrect. Of the verifier's own two "incorrect" verdicts, one was itself wrong (it flagged "the cell wall surrounds the plasma membrane"), and the other targeted a common simplification ("the testicles produce … semen") that the auditor accepted. Among 20 accepted claims, 80% were correct and none incorrect. The judge, in turn, found a single incorrect claim across all 180 A1 texts, and the verifier had flagged nothing in that text. Restricting the comparison to rewritten texts, where A2 actually differs from A1, A2−A1 differences remain small and not significant after Holm correction (Table X; correctness $+0.05$ [0.01, 0.10], gap focus $+0.10$ [−0.06, 0.26]), while rewriting removed 19 words per text (158 → 139). The pairwise judge prefers the unverified text: on rewritten items, A1 wins in both orders on 29% of items against 10% for A2. Incorrectness is near zero both for the verifier and for the judge, so this pilot cannot show a benefit of verification. What it does show is a cost: verification shortens texts and removes content, including pedagogically useful sentences, without measurable gains. The judge's own count of incorrect claims has a non-trivial false-positive floor: applied to the teachers' reference answers themselves (S0), it reports 0.18 [0.09, 0.28] incorrect claims per text, in 10 of the 15 questions.

## §5.5 Judge reliability and bias — texto proposto (substitui ou acrescenta)

> Judge scores saturate: for the generated conditions, 96–98% of texts receive the maximum correctness score, and 85–97% the maximum for coherence and level (Table Y). A stronger reliability problem appears when the judge evaluates the *same* text: the static material S and the reference answers S0 are identical for all students of a question, so student-independent dimensions should not vary across them. They do. For S, faithfulness receives the same score for all students of a question in only 20% of questions (mean within-question range 2.0 points on the 1–5 scale), and it correlates with the student's gold grade ($\rho=-0.18$ [−0.32, −0.04]). The student's answer, which the judge sees, therefore leaks into ratings of a text that does not depend on it. Position bias is strong when candidates are close: the first-presented material wins only 11–13% of non-tied verdicts in A1 vs. S and A1 vs. A0, and only 23–27% of items receive the same verdict in both orders. The judge is not simply random, however: on the 47 pairs where A2 and A1 are identical (no rewrite), it returns a tie in 100% of judgments. The longer material wins 51–63% of non-tied verdicts between close conditions and 79% against the short S0. In absolute scores, by contrast, length shows no reliable association with quality *within* a condition (the within-condition Spearman CI includes 0 in 17 of 18 condition×dimension pairs, the exception being A2 level adequacy, ρ = 0.20; the length coefficient controlling for condition has CIs including 0 for all six dimensions). The positive across-condition correlation therefore reflects differences between conditions rather than a verbosity effect. Robust pairwise winners agree with the sign of the absolute usefulness difference in 60–76% of items for close pairs (n = 10–21) and 91% for A1 vs. S0.

## §5.6 Simulated student (RQ5, exploratory) — texto proposto

> Every material raises the simulated student's score above the no-material control ($+0.45$), by $+1.2$ to $+1.4$ (Table Z), but three confounds limit what this proxy can show. (i) *Copying*: 20–30% of the distinct word trigrams in post-reading answers occur verbatim in the material just read; A1 is copied the most (30% vs. 22% for S), and gain increases with copying (+1.08 [0.35, 1.81] per unit of trigram containment). Controlling for copying, A1 minus S shrinks from $+0.14$ [−0.03, 0.33] to $+0.06$ [−0.09, 0.20], and A1 minus A0 from $+0.16$ to $+0.12$ [0.00, 0.24]. (ii) *Style shift*: the pre-test is the real student's answer (14 words on average), whereas every post-test is written by the LLM (29–43 words); re-answering without any material already gains $+0.45$. (iii) *Ceiling*: 74–82% of post-reading answers reach the maximum grade under every material. The proxy thus mostly measures whether the material can be paraphrased back, not learning.

## Limitations — texto proposto (substituir os itens correspondentes)

> **Judge validity.** All quality results use one LLM judge (Gemini 2.5 Flash), whose scores saturate, show position and length biases in pairwise mode, and vary for identical texts depending on the student answer shown. Its incorrect-claim count also has a false-positive floor on the reference answers themselves. GPT-4o mini generated, diagnosed and verified, so verification is same-family. **Verification.** With near-zero base incorrectness, A2 can only show costs (shorter texts), not benefits, and most of what the verifier flags are non-factual sentences rather than errors (manual audit of 50 claims by a single annotator); testing it requires a weaker generator or an open domain. **Simulated student.** The proxy is confounded by verbatim copying, by the style shift from human to LLM-written answers, and by a ceiling at the maximum grade; it is not evidence of learning.

---

## Números de referência (para conferência)

| Afirmação | Valor | Fonte |
|---|---|---|
| afirmações por texto; problemas por texto | 8.32; 1.21 | `results/rq4_resumo.csv` |
| vereditos (sup/cg/nao_sup/inc) | 46.1% / 39.3% / 14.4% / 0.13% | `results/rq4_vereditos.csv` |
| reescritos | 133/180 (73.9%) | `rq4_resumo.csv` |
| auditoria, marcadas (n=30): não factual / correta / duvidosa / incorreta | 67% [49, 81] / 17% [7, 34] / 10% / 7% [2, 21] | `rq4_auditoria.csv` |
| auditoria, aceitas (n=20, suportada + conhecimento geral): correta / incorreta | 80% [58, 92] / 0% [0, 16] (16/20; 0/20) | `rq4_auditoria.csv` (soma dos 2 grupos aceitos) |
| A2−A1 nos reescritos (correção, foco) | +0.05 [0.01, 0.10]; +0.10 [−0.06, 0.26]; Holm p = 0.115 / 1.0 | `rq4_a2_vs_a1.csv` |
| palavras removidas nos reescritos | −18.9 [−21.0, −16.9] (158.4 → 139.5) | `rq4_a2_vs_a1.csv` |
| par-a-par nos reescritos (A1 / A2 vencem nas duas ordens) | 29.3% / 9.8% | `rq4_pareado_reescritos.csv` |
| pares idênticos: empate | 100% (47 itens) | `rq4_pareado_reescritos.csv`, `vies_pareado.csv` |
| juiz: incorretas no S0 | 0.18 [0.09, 0.28]; 10/15 questões | `rq4_resumo.csv` |
| % de notas 5 (correção, gerados) | 96–98% | `vies_saturacao.csv` |
| S, fidelidade constante na questão; amplitude; ρ com nota-ouro | 20%; 2.0; −0.18 [−0.32, −0.04] | `vies_mesmo_texto.csv` |
| 1º vence; mais longo vence; mesma decisão | ver tabela | `vies_pareado.csv` |
| cópia de 3-gramas (S0/S/A0/A1/A2) | 20/22/26/30/30% | `rq5_resumo_condicoes.csv` |
| coef. da cópia sobre o ganho | +1.08 [0.35, 1.81] | `rq5_contrastes_ajustados.csv` |
| A1−S sem / com ajuste | +0.14 [−0.03, 0.33] / +0.06 [−0.09, 0.20] | `rq5_contrastes_ajustados.csv` |
| palavras da resposta (original / pós) | 14 / 29–43 | `rq5_resumo_condicoes.csv` |
| chega a 3 | 74–82% com material | `rq5_resumo_condicoes.csv` |
