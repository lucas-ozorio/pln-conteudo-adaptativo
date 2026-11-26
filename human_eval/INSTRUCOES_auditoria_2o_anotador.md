# Auditoria do verificador: instruções para o 2º anotador

Objetivo: medir a concordância entre dois anotadores sobre as mesmas 50 afirmações (kappa de Cohen). O 2º anotador **não deve ver** as respostas do 1º (João) nem o veredito do verificador.

1. Peça a planilha `human_eval/auditoria_afirmacoes.csv` (gerada por `python scripts/10_rq4_verificacao.py`; é a mesma amostra do João, com a mesma semente). **Não abra** `CHAVE_auditoria_NAO_ABRIR.csv`.
2. Unidade: **uma frase** (coluna `afirmacao`), do texto de apoio de um aluno. A pergunta e o gabarito são só contexto. A coluna `texto_original` mostra a frase entre `>>> <<<`.
3. Critério: "o que esta frase diz é verdade?" (nível 8º/9º ano). Não julgue completude nem se responde à pergunta.
4. Preencha a coluna `rotulo` com um destes valores:
   - `correta`: cientificamente correta;
   - `incorreta`: cientificamente errada;
   - `duvidosa`: imprecisa ou ambígua;
   - `nao_factual`: sem conteúdo científico (encorajamento, transição, analogia, instrução).
5. Salve como `human_eval/auditoria_anotador2.csv` e peça ao João o arquivo dele (`auditoria_afirmacoes.csv` preenchido).
6. Calcule: `python scripts/24_kappa_auditoria.py human_eval/auditoria_afirmacoes.csv human_eval/auditoria_anotador2.csv`
7. Se o kappa for baixo (< 0,6), reúnam-se, discutam os casos discordantes e relatem os dois números (antes e depois da discussão).
