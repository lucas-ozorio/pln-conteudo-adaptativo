# pln-conteudo-adaptativo

**Resultados do piloto: [RESULTADOS.md](RESULTADOS.md)** (com o que os dados sustentam e o que não). **Rascunho do artigo (formato ACL): [paper/main.pdf](paper/main.pdf)**; antes de submeter, leia [paper/VERIFICAR.md](paper/VERIFICAR.md).

Código dos experimentos iniciais do paper *Geração de Conteúdo Adaptativo com LLMs* (UFG, PLN). Desenho e justificativas: **[EXPERIMENTOS.md](EXPERIMENTOS.md)**.

## Passo a passo

```bash
pip install -r requirements.txt
python scripts/download_data.py            # baixa o PT-ASAG do Kaggle (não é redistribuído aqui)
python scripts/00_prepare_data.py          # amostras (sem LLM): 595 p/ E0, 180 p/ piloto
python scripts/estimate.py                  # nº de chamadas estimado
python scripts/run_all.py --mock           # teste do encanamento SEM chave (resultados sem valor científico)
python tests/test_basic.py                  # testes unitários rápidos
```

Para rodar de verdade:

1. Escolha o provedor em `config.yaml` (padrão: OpenRouter, uma chave para várias famílias de modelo) e **confira os nomes dos modelos**: eles são um ponto de partida e não foram verificados.
2. Defina a chave **na variável de ambiente** (ex.: `setx OPENROUTER_API_KEY ...` no Windows; nunca no código nem no repositório).
3. Regra metodológica: o `judge` deve ser de **família diferente** do `generator`.
4. Teste barato primeiro: `python scripts/run_all.py --limit 6`.
5. Piloto completo: `python scripts/run_all.py`. É retomável: o cache (`cache/`) e os `outputs/*.jsonl` evitam repetir chamadas.

Etapas individuais: `01_diagnosis.py` (E0) → `02_generate.py` → `03_judge.py` (E1) → `04_student_sim.py` (E3) → `05_analyze.py` (gera `results/summary.md` e CSVs).
Humanos (E2): `06_export_human_eval.py` gera a planilha cega em `human_eval/`; após o preenchimento (`planilha_<avaliador>.csv`), `07_judge_human_agreement.py`.

## Estrutura

```
config.yaml           modelos, tamanho da amostra, condições, pares comparados
src/pln/prompts.py    todos os prompts (PT-BR)
src/pln/pipeline.py   diagnóstico -> apoio -> questões; A0/A1/A2/S/S0
src/pln/judge.py      LLM-as-a-Judge (absoluto e par-a-par)
src/pln/llm.py        cliente OpenAI-compatível, cache, retentativas, mock
scripts/              00..09 + run_all + estimate (08: bootstrap por questão; 09: tabelas/figuras do artigo)
paper/                main.tex (ACL, [review]), references.bib, tables/ e figures/ gerados dos CSVs, main.pdf
data/raw/             PT-ASAG 2018 v2.0, baixado por scripts/download_data.py (CC BY-NC-SA 4.0: só uso acadêmico, citar Galhardi et al., 2018)
outputs/ results/     saídas reais do piloto (diagnóstico, materiais, julgamentos, aluno simulado) e tabelas
```

## Cuidados

- A nota-ouro não vai para nenhum prompt. O juiz não vê o nome da condição.
- `outputs_mock/` e `results_mock/` são de teste; não usar no artigo.
- `human_eval/CHAVE_condicoes_NAO_COMPARTILHAR.csv` não pode ir para os avaliadores.
- Os dados do PT-ASAG são de menores de idade, anonimizados pelo autor original; não republique respostas de alunos nos artigos além de exemplos curtos.

## Licenças

- Código: use livremente com citação (defina a licença final com o grupo antes de tornar o repositório público).
- `outputs/` e `cache/` contêm trechos de respostas de alunos do PT-ASAG citados pelos modelos (campos de evidência do diagnóstico). Esses trechos seguem a licença do dataset original, **CC BY-NC-SA 4.0** (uso não comercial, com atribuição a Galhardi et al., 2018, e mesma licença).

## Compilar o artigo

Envie `paper/` ao Overleaf ou compile com `tectonic -X compile main.tex`. Rode `python scripts/08_cluster_bootstrap.py && python scripts/09_make_paper_assets.py` para regenerar tabelas e figuras depois de novos resultados.
