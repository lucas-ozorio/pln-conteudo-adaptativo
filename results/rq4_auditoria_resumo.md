# Auditoria manual do verificador (RQ4) — resumo

Frente C (João) · feita em 2026-11-22 · prazo do artigo: 2026-11-23

## O que foi feito

- **Unidade avaliada:** 1 afirmação (uma frase) do texto de apoio A1. O verificador (GPT-4o mini) quebrou cada texto A1 em frases curtas e deu um veredito a cada uma. **A afirmação não é a resposta do modelo à pergunta.** Pergunta e gabarito servem só de contexto.
- **Critério:** "o que esta frase diz é verdade?" (nível 8º/9º ano). Não julga completude nem se responde à pergunta.
- **Rótulos:** `correta` · `incorreta` · `duvidosa` (imprecisa/ambígua) · `nao_factual` (encorajamento, transição, analogia, instrução).
- **Amostra:** 50 afirmações, espalhadas pelas 15 questões. São 30 que o verificador **marcou** (todas as 2 "incorretas" + 28 "não suportadas") e 20 que ele **aceitou** (10 "suportadas" + 10 "conhecimento geral correto").
- **Cego:** 1 anotador (João), sem ver o veredito. A chave só foi aberta depois de os 50 rótulos estarem preenchidos.
- **Comando:** `python scripts/10_rq4_verificacao.py --auditoria human_eval/auditoria_afirmacoes.csv` → `results/rq4_auditoria.csv` (IC de Wilson 95%).

## Resultados

**Afirmações marcadas pelo verificador (n = 30), que dispararam a reescrita:**

| Rótulo humano | n | % | IC 95% |
|---|---|---|---|
| não factual | 20 | **67%** | 49–81% |
| correta | 5 | 17% | 7–34% |
| duvidosa | 3 | 10% | 3–26% |
| incorreta | 2 | **7%** | 2–21% |

**Afirmações aceitas pelo verificador (n = 20):**

| Grupo | correta | duvidosa | não factual | incorreta |
|---|---|---|---|---|
| suportada (10) | 9 | 1 | 0 | 0 |
| conhecimento geral correto (10) | 7 | 1 | 2 | 0 |
| **total (20)** | **16 (80%, IC 58–92%)** | 2 | 2 | **0 (IC 0–16%)** |

**Conclusão:** de tudo que o verificador mandou reescrever, só 2 em 30 frases eram erros de verdade. Dois terços eram encorajamento, transição ou analogia. Isso reforça o que o artigo diz: a verificação tem custo (textos mais curtos, conteúdo removido) e não traz benefício mensurável.

## Casos que valem citar

- **As 2 frases rotuladas `incorreta`** são a mesma analogia (gás carbônico como "fumaça que dispara o alarme"), em dois textos diferentes. O verificador as marcou como "não suportadas".
- **Os 2 vereditos "incorreta" do próprio verificador:** o anotador marcou os dois como `correta`.
  - F74395, "a parede celular envolve a membrana plasmática": a frase está certa e o verificador errou. A justificativa dele se contradiz ("é externa à membrana, não a envolve").
  - F78148, "os testículos produzem testosterona e o sêmen": é uma simplificação, porque o sêmen vem em boa parte da vesícula seminal e da próstata. O rótulo **não foi alterado** depois de abrir a chave, para não enviesar a auditoria. O texto do artigo descreve o caso com transparência.

## Onde isso entrou

- **`paper/frente_c_rq4_rq5.md`:**
  - §5.4: frase da auditoria escrita, sem o placeholder.
  - Limitations: item *Verification* atualizado.
  - Tabela de números de referência: 2 linhas novas.
- **`CLAUDE.md`:** checklist da frente C marcado como feito.
- **`src/pln/stats.py`:** `wilson()` agora corta o IC em [0, 1]. Antes aparecia "-0.000".
- **`scripts/10_rq4_verificacao.py`:** a planilha gerada ganhou a coluna `texto_original`, com a frase marcada entre `>>> <<<`. As 50 afirmações, os IDs e os resultados `rq4_*` não mudaram.

## Arquivos

| Arquivo | O que é | Vai pro git? |
|---|---|---|
| `human_eval/auditoria_afirmacoes.csv` | Planilha preenchida (50 rótulos) | **Não** (gitignored) |
| `human_eval/CHAVE_auditoria_NAO_ABRIR.csv` | Veredito do verificador por ID | **Não** (gitignored) |
| `results/rq4_auditoria.csv` | Proporções + IC por grupo | Sim |
| `results/rq4_auditoria_resumo.md` | Este arquivo | Sim |

## Para amanhã

- [ ] Passar `paper/frente_c_rq4_rq5.md` e as 4 tabelas (`paper/tables/tab_rq4.tex`, `tab_rq5.tex`, `tab_bias.tex`, `tab_bias_pairwise.tex`) para quem consolida o `main.tex` (frente D).
- [ ] Decidir se commita os arquivos da frente C num branch separado. **Nada foi commitado ainda.** Fica tudo como arquivos novos, sem rastreio no git.
- [ ] Se precisar reconferir os números, `scripts/10`, `11` e `12` rodam offline (precisam de `data/processed`).
