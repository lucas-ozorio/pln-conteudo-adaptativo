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

## Integração da equipe (2026-11-22, branch `artigo-integrado`)
Incorporado ao `main.tex` a partir do grupo de WhatsApp "NLP" e das branches do repositório:
- **Herik** (`herik/rq1-diagnostico-e-variantes`): RQ1 (diagnóstico calibrado v1/v2, QWK 0,49 -> 0,58) em §5.1, resumo, Limitations e apêndice; RQ2/RQ3 (A1 x A0 x S, controle de tamanho, estratos, análise qualitativa) em §5.2, §5.3, Discussão, Limitations e apêndice. Textos colados sem alteração de conteúdo; só tabelas largas foram movidas ao apêndice para respeitar as 8 páginas.
- **João** (`joao`): RQ4 (auditoria manual de 50 afirmações), vieses do juiz (mesmo texto, posição, comprimento) e RQ5 (cópia, estilo, teto) em §5.4 a §5.6 e Limitations; tabelas `tab_rq4/rq5/bias/bias_pairwise`. Aplicada a correção que ele pediu: a correção conceitual +0,03 [0,01; 0,07] de A2-A1 **não** é significativa após Holm.

Pontos que **vocês precisam confirmar**:
- [ ] O parágrafo "Weak generator" (§5.4) e a tabela `tab_rq4w` foram escritos por mim a partir de `results/rq4w_*.csv` (experimento do João com Llama 3.1 8B, que o texto `frente_c_rq4_rq5.md` não menciona). O João deve conferir a redação e se o experimento é para entrar. Essa seção muda a conclusão: a verificação ajuda o gerador fraco (incorretas -0,11, Holm p=0,022) mas custa foco (-0,33).
- [ ] No WhatsApp o Herik cita "a branch `paizao`" do João; ela **não existe** no GitHub. O que existe é `joao` (RQ4/RQ5) e os commits do `Joao-IA` dentro da branch do Herik (execução v1/v2).
- [ ] Os ICs de A1-S e A1-A0 do E3 vêm de sementes de bootstrap diferentes (meu `cluster_e3_contrastes.csv` x o `stats.py` do João): no texto, a versão sem ajuste usa a minha (-0,05; 0,33) e a ajustada usa a dele. Diferença só na 2a casa.
- [ ] A auditoria do RQ4 tem **um** anotador (João). Se possível, um segundo anotador e um kappa.
- [ ] Custo: cerca de US$ 3 no total (piloto 2,4 + calibração 0,32 + gerador fraco ~0,35, este estimado pelos tokens).
- [ ] O experimento v2 (diagnóstico calibrado) **não** alimentou a geração; o artigo diz isso. Se rodarem a geração com v2, atualizem §5.2 a §5.6.
