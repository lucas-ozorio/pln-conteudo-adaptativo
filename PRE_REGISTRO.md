# Pré-registro das análises de robustez (escrito ANTES das novas rodadas)

Data: 2026-11-24. Este arquivo foi commitado no git antes de executar qualquer um dos experimentos descritos abaixo; o hash do commit prova a ordem. O piloto original (RESULTADOS.md) foi **exploratório**; este documento só cobre as rodadas novas.

## Pergunta
As conclusões do piloto resistem a (a) outro juiz, (b) outras sementes e outro gerador, (c) diagnóstico calibrado, (d) ablação limpa do diagnóstico, (e) respostas nota 3, (f) um pós-teste sem cópia?

## Dados e materiais
- Piloto: os mesmos 180 itens (15 questões × notas {0,1,2} × 4). Nota 3: 60 itens novos (15 × 4; q42 tem 5 respostas nota 3 no sorteio). Mesma semente (42).
- Juízes: J1 = `google/gemini-2.5-flash` (o do piloto), J2 = `anthropic/claude-haiku-5.5` (outra família, nem do gerador nem de J1). Temperatura 0.
- Geradores: G1 = `openai/gpt-4o-mini` (piloto), G2 = `deepseek/deepseek-v4-flash` (outra família). Sementes extras: 2 (G1).
- Os prompts do piloto não mudam; novos prompts estão em `src/pln/prompts_robust.py`.

## Hipóteses confirmatórias (direção e critério)
Escala de 1 a 5. "Replica" = diferença média A1−S **positiva** e IC95% bootstrap por questão (5.000 reamostras) **excluindo zero**, nas duas dimensões primárias.

- **H1 (efeito principal):** A1 > S em `foco_na_lacuna` e `utilidade_pedagogica`.
  Deve replicar em: J2; sementes extras (G1); G2; diagnóstico v2.
- **H2 (diagnóstico explícito):** A1 ≈ A0. Afirmamos "sem diferença" **apenas** se o IC95% de A1−A0 estiver dentro de ±0,25 em foco e utilidade (margem de equivalência); caso contrário, dizemos "inconclusivo".
- **H3 (ablação limpa):** A1 vs A1ø (mesmos prompts, diagnóstico vazio). Se IC de A1−A1ø excluir zero em foco ou utilidade, o diagnóstico tem valor próprio; se dentro de ±0,25, não tem.
- **H4 (diagnóstico calibrado):** A1(v2) não pior que A1(v0): IC de A1v2−A1v0 sem limite inferior abaixo de −0,25 em foco e utilidade.
- **H5 (qualidade sem ver o aluno):** juiz cego à resposta do aluno: A1 não pior que S em coerência, correção, fidelidade (limite inferior do IC > −0,25).
- **H6 (nota 3):** exploratória: sem direção declarada. Medimos "sobre-remediação" (o texto trata como erro algo que o aluno acertou).
- **H7 (pós-teste de transferência, aluno simulado):** exploratória; sem hipótese direcional. Reportamos A1−S e cada material vs "sem material".

## Estatística
- Pareado por item; IC por bootstrap que reamostra **questões** (15 clusters). Modelo linear misto (efeitos aleatórios de questão e item) como análise de robustez.
- Correção de Holm **dentro de cada réplica** sobre as 2 dimensões primárias de H1.
- Concordância entre juízes: Spearman e QWK por dimensão, e se as direções de todos os contrastes coincidem.
- Relatar todos os resultados, incluindo os negativos. Desvios do protocolo serão listados em RESULTADOS_ROBUSTEZ.md.

## O que NÃO fazemos
- Não trocamos de juiz, prompt ou dimensão depois de ver os resultados. Se um prompt novo falhar por erro técnico (não por resultado), corrigimos o erro e registramos.
- Orçamento: até ~US$ 5 em chamadas à API; paramos se o saldo cair abaixo de US$ 0,50.

## Fora do escopo (precisam de pessoas)
Avaliação humana do juiz (item 1), segundo anotador da auditoria (item 9) e alunos reais. Deixamos o material pronto.
