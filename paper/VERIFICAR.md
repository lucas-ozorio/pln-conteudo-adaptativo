# Checklist do grupo antes de submeter

O rascunho foi escrito com apoio de IA. Os números do texto vêm dos CSVs de `results/` (tabelas e figuras são geradas por `scripts/09_make_paper_assets.py`), mas **você precisa conferir tudo**.

## Dados e números
- [ ] Rode `python scripts/08_cluster_bootstrap.py` e `python scripts/09_make_paper_assets.py` se mudar qualquer resultado; as tabelas do artigo se atualizam sozinhas. Os números **no texto corrido** (ex.: "+0.80", "QWK 0.49") são digitados à mão e precisam ser conferidos contra `results/` depois de qualquer nova rodada.
- [ ] O E2 (avaliação humana) **não foi feito**. Quando houver, adicione concordância humano × juiz e humano × humano (`scripts/07_judge_human_agreement.py`) e reescreva a frase "No human validation ... has been completed yet" no §5.5, no resumo e na seção Limitations.

## Referências (conferir no site do editor)
- [ ] Entradas com `others` em `references.bib` têm lista de autores truncada (vinda da planilha de referências): Mello 2025, Steiss 2024, Meyer 2024, Anchiêta 2025, Kasneci 2023, Maurya 2025, Huang 2025, Zheng 2023, Grattafiori 2024, Comanici 2025. Complete antes da versão final.
- [ ] Não consegui abrir o Springer nem a ACM; os metadados de Scaria 2024 (AIED, LNCS 14830) e Oliveira 2026 (ACM CSUR 58(15)) vêm da sua planilha.
- [ ] Verificadas por mim na web: Shi et al. (AACL-IJCNLP 2025, arXiv 2406.07791), Daheim et al. (arXiv 2407.09136; EMNLP 2024 conforme sua proposta), Llama 3 (arXiv 2407.21783), Gemini 2.5 (arXiv 2507.06261), Sonkar (2410.12294), Maity e Deroy (2410.09576), Ehsan et al. (2508.19475), Mucciaccia (COLING 2025).
- [ ] Citadas de memória, **sem verificação**: Dror et al. 2018, Holm 1979, Cohen 1968, Efron e Tibshirani 1993, Field e Welsh 2007, e a URL do blog "GPT-4o mini" da OpenAI.
- [ ] No texto e na proposta o sobrenome aparece como "Mello"; no BibTeX está "Ferreira Mello" (conforme a planilha). Padronize.

## Formato ACL / ARR
- [ ] O template (`acl.sty`, `acl_natbib.bst`) é do repositório oficial `acl-org/acl-style-files`. Rode o `pubcheck` da ACL e confira no Overleaf com a opção `[review]`.
- [ ] Preencha o Responsible NLP Checklist do ARR (a política de uso de IA generativa exige divulgar a assistência na escrita; há um parágrafo em "Acknowledgments").
- [ ] Verifique as regras do evento-alvo (limite de páginas, língua, anonimato). Se for um evento brasileiro (STIL, PROPOR, BRACIS, SBIE), o template e o idioma podem ser outros.
- [ ] Anonimato: o repositório está privado e o texto omite a URL. Para a versão final, inclua o link.
- [ ] Adicionar e-mails dos autores na versão final (não os tenho).

## Ética
- [ ] Confirme com o professor/orientador o uso do PT-ASAG (CC BY-NC-SA 4.0) e a política de dados de menores da disciplina.
