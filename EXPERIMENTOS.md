# Desenho dos experimentos iniciais

Projeto: *Geração de Conteúdo Adaptativo com LLMs* (UFG, PLN). Este documento descreve **o que será rodado, por quê, e como interpretar**. Tudo está parametrizado em `config.yaml`.

## 1. Conceito do paper (resumo do que foi lido)

- **Problema:** corrigir respostas dissertativas é caro; em turmas grandes o ciclo *diagnóstico → remediação* não fecha e o retorno é genérico e tardio (Bloom, 1984; Hattie & Timperley, 2007).
- **Gap (Related Work):** AES/ASAG em português só dão **nota**; geração de feedback em PT deriva da **rubrica**, sem diagnóstico conceitual, e compara com *nenhum feedback*; AQG gera questões de **texto estático**; Daheim et al. (2024) mostram que *diagnosticar antes de gerar* melhora a remediação e reduz alucinações, mas só em matemática, em inglês, em diálogo.
- **Proposta:** pipeline `resposta + gabarito → diagnóstico (acertos, erros, conceitos ausentes) → texto de apoio focado → novas questões (Bloom)`, com **protocolo de avaliação duplo** (LLM-as-a-Judge + humanos especialistas) comparando o material adaptativo com **material estático** (não só com "sem feedback").
- **Hipótese:** material individualizado > material estático, **desde que** sob controle de qualidade (coerência, correção conceitual, fidelidade ao gabarito).

## 2. Dados

**PT-ASAG 2018 v2.0** (Galhardi et al., SBIE 2018; Kaggle `lucasbgalhardi/pt-asag-2018`; licença CC BY-NC-SA 4.0, uso acadêmico): 15 questões de Biologia (8º/9º ano), 2–4 gabaritos de professores e 3–6 conceitos-chave por questão, respostas de alunos com nota 0–3 (rubrica de 4 níveis). Escolhido por já trazer **pergunta + gabarito + conceitos + resposta real + nota**, que é exatamente a entrada do pipeline (isto responde à pergunta do pitch sobre "montar a massa de teste": usar dados reais, sem sintéticos).

Amostra (seed fixa, `data.py`): respostas com 1–150 palavras, sem duplicatas.
- **E0 (`diag_set`)**: até 10 respostas por questão × nota (0–3) = **595**.
- **Piloto E1/E3 (`pilot_set`)**: 4 por questão × notas {0,1,2} = **180** (subconjunto do E0; nota 3 já está quase certa, não precisa de remediação).
- A nota-ouro **nunca** entra em prompts (só na análise).

## 3. Condições comparadas (E1)

| Cód. | O que é | Para que serve |
|---|---|---|
| `S0_gabarito` | o gabarito do professor como "material" (sem LLM) | piso de fidelidade: zero alucinação, zero personalização |
| `S_estatico` | texto de reforço + questões gerados **1× por pergunta**, iguais para todos | **linha de base realista da proposta** (reforço estático) |
| `A0_direto` | LLM gera apoio + questões em 1 chamada, **sem** diagnóstico explícito | ablação: mede o valor do diagnóstico |
| `A1_pipeline` | **proposta**: diagnóstico → apoio → questões | núcleo do paper |
| `A2_pipeline_verif` | A1 + verificação por afirmação ancorada no gabarito + reescrita | mitigação de alucinação (pergunta do pitch) |

Controles: mesmo orçamento de palavras (120–180) em todas as condições; mesmos modelos e temperatura; formatação neutra para o juiz; modelo do juiz de família diferente do gerador.
"Sem material" entra como condição `N_sem_material` no E3.

## 4. Experimentos

**E0 — Validade do diagnóstico.** O diagnóstico recupera a nota-ouro? Métricas: QWK, Spearman, MAE, acurácia exata/binária; matriz de confusão; proxy lexical de cobertura de conceitos. Referência: concordância humano–humano do PT-ASAG (r=0,581) e Mello et al. (2025). *Lê-se como*: o quão confiável é a "entrada" da geração (Daheim: o ganho depende da correção do diagnóstico).

**E1 — Qualidade do material (núcleo).**
- *Juiz absoluto* (1–5, cego): texto = coerência, correção conceitual, fidelidade ao gabarito, **foco na lacuna**, utilidade pedagógica, adequação ao nível, + nº de afirmações incorretas (proxy de alucinação); questões = alinhamento, clareza, relevância à lacuna, resposta esperada correta, **nível de Bloom pedido × percebido**.
- *Juiz par-a-par* nas **duas ordens** (A1×S, A1×A0, A2×A1, A1×S0).
- *Controle de vieses do juiz* (Zheng et al., 2023): posição (1º vence?), verbosidade (Spearman palavras×nota, coeficiente de log-palavras controlando condição, "o mais longo vence?"), autofavorecimento (juiz ≠ família do gerador).
- *Estatística*: pareada por item; IC95% bootstrap; Wilcoxon; efeito rank-biserial; correção de Holm.

**E2 — Julgamento humano (`06_export_human_eval.py`, `07_judge_human_agreement.py`).** Planilha **cega e embaralhada** (40 itens × 3 condições = 120 linhas), mesma rubrica do juiz, 2–3 avaliadores sobre as mesmas linhas. Saída: concordância humano×juiz (Spearman, QWK) por dimensão e humano×humano (teto). Valida (ou não) o juiz, em especial na utilidade pedagógica, onde Maurya et al. (2025) encontraram correlação baixa.
Potência (aprox., teste pareado, α=0,05, 80%): n=40 detecta d≈0,44; n=180 detecta d≈0,21. Se 120 linhas for inviável, reduza `human_eval.n_items` para 30 ou use só A1×S par-a-par.

**E3 — Redução da lacuna com aluno simulado (EXPLORATÓRIO).** Aluno-LLM relê a pergunta com/sem o material e reresponde; um corretor com gabarito dá nota 0–3; ganho = pós − pré (mesmo corretor). `N_sem_material` controla o conhecimento prévio do LLM. **Não substitui estudo com alunos reais**; é triagem barata para a pergunta "qual métrica mede se a lacuna fechou?". Sanidade: QWK do corretor × nota-ouro.

## 5. Ameaças à validade (já mapeadas)

1. Juiz LLM enviesado (posição, verbosidade, autofavorecimento) e fraco em dimensões pedagógicas → mitigações do E1 + validação humana do E2.
2. Aluno simulado ≠ aluno real (E3) → rotular como exploratório; só ler ganho **relativo**.
3. Um único domínio (Biologia, EF) e rubrica 0–3 → generalização limitada (decisão de escopo do pitch).
4. Os "conceitos-chave" do dataset são palavras-chave, não anotação de equívocos → E0 mede nota, e conceitos só por proxy lexical.
5. Uma só rodada de geração (temperatura 0,4) → para o artigo final, repetir com ≥3 sementes ou mais de um gerador.
6. Modelos/versões mudam: registrar nome e data de cada execução (`outputs/usage.jsonl` guarda modelo e tokens).
7. Licença do dataset é NC: uso acadêmico apenas, com citação.

## 6. Mapa pitch → experimento

| Pergunta aberta do pitch | Onde é tratada |
|---|---|
| Diagnóstico de misconceptions é viável ou simplificar para rubrica? | E0 |
| Montar massa de teste: real ou sintética? | PT-ASAG (real) |
| Tamanho da amostra para validação humana | E2 (n=40, potência acima) |
| Métrica robusta de redução da lacuna | E3 (+ par-a-par E1) |
| Pós-processamento simples contra alucinação | A2 (verificação + reescrita) vs A1 |
| Viés de verbosidade do juiz | E1 (controles) |
