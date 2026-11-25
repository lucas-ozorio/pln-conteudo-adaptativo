# Preparação para a banca: perguntas prováveis, resposta e evidência

Cada resposta traz (1) a resposta curta, (2) a evidência com o arquivo de origem, (3) o que **admitir**. Regra de ouro: **não afirme mais do que a evidência sustenta**; os pontos fracos admitidos por escrito no artigo (Limitations) desarmam a maior parte das perguntas.

## O que o artigo afirma, e o que NÃO afirma

| Afirma (com evidência) | NÃO afirma |
|---|---|
| Material individualizado é julgado mais focado na lacuna (+0,6 a +0,8 com o gerador principal) e mais útil (+0,3 a +0,5) que material estático de mesmo tamanho. Replicou em 8 de 8 réplicas (2 juízes, 2 sementes, 2 geradores, diagnóstico v2). | Que o aluno **aprende mais**. Não há alunos reais; o aluno simulado não mostra vantagem de A1 sobre S (+0,05; IC −0,03 a 0,15). |
| O diagnóstico explícito não agrega valor mensurável (A1 ≈ A0; sem diagnóstico, A1ø é até melhor em foco). | Que o diagnóstico é inútil: pode servir ao professor (não avaliado). |
| A verificação reduz afirmações incorretas só com gerador fraco, ao custo de foco. | Que a verificação "elimina alucinação". |
| Há custos: menos completude (juiz cego) e mais sobre-remediação em respostas já corretas. | Que o material individualizado é "melhor" em geral. |

## Perguntas

**1. "O juiz é um LLM. Por que confiar nas notas?"**
- Resposta: não pedimos confiança cega. Usamos dois juízes de famílias distintas do gerador, cegos à condição, com comparação nas duas ordens. Eles concordam no que sustenta a conclusão principal (foco e utilidade: Spearman 0,52 e 0,58) e **discordam** em correção e fidelidade (0,10 e 0,06).
- Evidência: `results_robust/juizes_concordancia.csv`, `juizes_contrastes_J1_J2.csv` (mesmo sinal em 10 de 24 contrastes).
- Admitir: **não há validação humana ainda**. A planilha cega está pronta (`human_eval/`, 39 itens × 3 condições, com nota global). Se for possível, fazer antes da banca: é a maior defesa.

**2. "O 'foco na lacuna' foi definido por vocês e favorece seu método (circularidade)."**
- Resposta: concordamos que é a dimensão que o método visa. Por isso há (a) a dimensão **utilidade**, que não presume o método, (b) um juiz **cego à resposta do aluno** e (c) o teste de transferência.
- Evidência: `h5_juiz_cego.csv`: sem ver o aluno, o juiz acha A1 **menos** completo que S (−0,26 e −0,84) e de qualidade geral menor (−0,17; −0,80). Transferência: A1−S = +0,05, n.s.
- Admitir: o ganho é real na dimensão visada; o preço é cobertura. O artigo diz isso.

**3. "O ganho pode ser só de tamanho ou estilo do texto."**
- Resposta: todas as condições têm o mesmo orçamento; A1 e S têm 159 palavras. Medimos o viés de verbosidade do juiz.
- Evidência: Tabela de contrastes; regressão com efeito fixo de item e correlações Δpalavras × Δnota (apêndice, `results/herik_variants/`); `results/vies_*.csv`.
- Admitir: A0 é mais curto que A1 (média 120 vs 159), então A1 × A0 é pouco sobreposto em tamanho.

**4. "Uma geração só, um gerador só."**
- Resposta: replicado com 2 sementes extras e outro gerador (DeepSeek).
- Evidência: `h1_replicacao_A1_menos_S.csv` (8 de 8, IC sem zero).
- Admitir: "semente" aqui é reamostragem independente; as sementes extras foram julgadas só pelo juiz 1.

**5. "O diagnóstico explícito era a ideia central. Por que o resultado é negativo?"**
- Resposta: honestidade científica. Três evidências independentes: A1 ≈ A0 em 9 de 12 comparações (margem ±0,25); A1ø (mesmos prompts, diagnóstico vazio) tem foco **maior** (+0,16 e +0,42); e o diagnóstico calibrado (QWK 0,49→0,58) não muda o material.
- Evidência: `h2_A1_vs_A0.csv`, `h3_ablacao_sem_diagnostico.csv`, `h4_diagnostico_v2.csv`; análise qualitativa do Herik (lista fixa de 3 lacunas em 179/180 itens).
- Admitir: os prompts de A1 e A0 diferem em mais que o diagnóstico; a ablação A1ø é a comparação limpa.

**6. "A verificação funciona contra alucinação?"**
- Resposta: com gerador forte não há o que corrigir (0,01 afirmação incorreta por texto); com gerador fraco reduz pela metade (0,22→0,11; Holm p = 0,022), mas custa foco (−0,33).
- Evidência: `rq4*.csv`, `rq4w_*.csv`, auditoria manual de 50 afirmações (só 2 de 30 marcadas eram erros reais).
- Admitir: auditoria com **um** anotador; verificador e gerador da mesma família.

**7. "Só 15 questões de Biologia."**
- Resposta: tratamos as questões como clusters (bootstrap por questão e modelo misto, que concordam). O efeito é heterogêneo: forte em células e sistemas do corpo, ≈ 0 em genética (2 questões).
- Evidência: `h10_modelo_misto.csv`, `por_topico.csv`.
- Admitir: não encontramos segundo conjunto público com gabarito e resposta de aluno em português; a generalização é uma limitação declarada.

**8. "Aluno simulado não mede aprendizado."**
- Resposta: concordamos, e por isso rotulamos como exploratório. O teste de transferência (anotações, depois questões novas, sem acesso ao material) remove a cópia.
- Evidência: `h7_transferencia_*.csv`: todos os materiais batem "sem material" (+0,48 a +0,59), inclusive o gabarito puro; A1−S ≈ 0.
- Admitir: 62 de 1.080 casos perdidos por saída ilegível; sem alunos reais.

**9. "E em respostas que o aluno já acertou?"**
- Resposta: medimos com 60 respostas nota 3. A1 sobre-remedia mais que S (+0,50 e +0,78), embora os juízes discordem sobre reconhecer os acertos.
- Evidência: `h6_nota3_sobre_remediacao.csv`.
- Admitir: é um risco de uso real; recomendamos professor no circuito.

**10. "Quantos testes vocês rodaram? Não é p-hacking?"**
- Resposta: o plano (hipóteses, margem de equivalência e famílias de Holm) foi commitado **antes** das rodadas de robustez (`PRE_REGISTRO.md`, commit `f6d0c37`, 2026-11-24). Reportamos todos os resultados, inclusive os que contrariam a hipótese.
- Admitir: o plano foi escrito **depois** do piloto exploratório; os desvios estão listados (custo US$ 6,3 > 5; modelo misto reespecificado; falha de leitura do corretor, recuperada do cache; sementes só no juiz 1). A margem de ±0,25 é uma escolha (5% da escala), sem teste de sensibilidade.

**11. "QWK 0,58 é bom?"**
- Resposta: é moderado. A concordância humana original (r = 0,58, Pearson, em subconjunto) não é diretamente comparável. O ganho de 0,49→0,58 é significativo (Holm p = 0,0004) e vem de corrigir artefatos do prompt, mas não melhora o material gerado.
- Evidência: `results/herik_h02/`.

**12. "Reprodutibilidade: modelos mudam."**
- Resposta: publicamos prompts, gerações, julgamentos e cache; fixamos o dia (2026-11-16 a 25). Um caso real: `gemini-2.0-flash` foi descontinuado no meio do projeto e trocamos por `gemini-2.5-flash`.
- Admitir: acesso via agregador (OpenRouter); rodar de novo pode não dar saídas idênticas. O juiz 2 foi usado com raciocínio desligado (sem teste de sensibilidade a isso).

**13. "Dados de menores e licença."**
- Resposta: PT-ASAG é CC BY-NC-SA 4.0, anonimizado; não coletamos dados. O dataset não é redistribuído (`scripts/download_data.py`); `outputs/` contém trechos curtos sob a mesma licença.
- Falta: confirmar com o professor a política de dados de menores da disciplina.

**14. "Uso de IA na escrita."**
- Resposta: declarado em Acknowledgments. O grupo é responsável por verificar números e referências (`paper/VERIFICAR.md`).

## Checklist antes da banca
- [ ] 2 a 3 pessoas preenchem a planilha humana → `python scripts/07_judge_human_agreement.py`; atualizar §5.5 e Limitations.
- [ ] Segundo anotador da auditoria → `scripts/24_kappa_auditoria.py`.
- [ ] Conferir referências com autores truncados e as citadas de memória (lista em `VERIFICAR.md`).
- [ ] Conferir nomes de modelos citados no artigo (Claude Haiku 5.5 e DeepSeek V4 Flash seguem os identificadores do OpenRouter; não foram confirmados em páginas dos fornecedores).
- [ ] Ensaiar a resposta 1 (juiz) e 5 (diagnóstico), que são as mais prováveis.
