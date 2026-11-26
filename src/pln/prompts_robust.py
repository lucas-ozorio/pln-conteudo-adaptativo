"""Prompts novos da rodada de robustez (PRE_REGISTRO.md). Os prompts do piloto (prompts.py) NÃO são alterados."""
from __future__ import annotations

from .prompts import JUDGE_SYSTEM  # noqa: F401  (mesmo system do juiz do piloto)

# --------------------------------------------------------------------------- A1ø: ablação limpa do diagnóstico
# Mesmos prompts de texto e de questões do A1 (prompts.SUPPORT_USER / QUESTIONS_USER); só muda o conteúdo do campo
# de diagnóstico e o das lacunas: o modelo deve inferir sozinho, sem uma etapa de diagnóstico estruturada.
NODIAG_DIAG = ("(Nenhum diagnóstico disponível. Identifique você mesmo, comparando a resposta do aluno com o gabarito, "
               "quais conceitos o aluno acertou, errou ou omitiu, e foque nisso.)")
NODIAG_LACUNAS = "(não informadas: deduza-as a partir do texto de apoio acima)"

# --------------------------------------------------------------------------- Juiz CEGO à resposta do aluno
JUDGE_BLIND_USER = """PERGUNTA: <<PERGUNTA>>
GABARITO (referência de correção):
<<REFS>>

TEXTO DE APOIO (material de estudo sobre este tema):
\"\"\"<<TEXTO>>\"\"\"

Você NÃO conhece a resposta de nenhum aluno. Avalie o texto apenas como material de estudo sobre o tema da pergunta, de 1 a 5 (1 = muito ruim, 3 = aceitável, 5 = excelente), ignorando tamanho e estilo:
- coerencia: clareza, organização e fluidez em português;
- correcao_conceitual: ausência de erros científicos; 1 = há erro grave, 5 = totalmente correto;
- fidelidade_gabarito: alinhamento ao conteúdo do gabarito, sem contradizê-lo nem desviar do tema;
- completude: cobre os conceitos essenciais do gabarito (1 = omite quase tudo, 5 = cobre tudo que importa);
- adequacao_nivel: linguagem e profundidade adequadas ao 8º/9º ano;
- qualidade_geral: nota holística como material de estudo para um aluno típico do 8º/9º ano.
Conte também "afirmacoes_incorretas": número de afirmações cientificamente erradas ou contrárias ao gabarito.
Primeiro escreva "justificativa" (2 a 3 frases), depois as notas. Formato:
{"justificativa": "...", "coerencia": n, "correcao_conceitual": n, "fidelidade_gabarito": n, "completude": n, "adequacao_nivel": n, "qualidade_geral": n, "afirmacoes_incorretas": n}"""

# --------------------------------------------------------------------------- Sobre-remediação (respostas nota 3)
JUDGE_OVERREM_USER = """PERGUNTA: <<PERGUNTA>>
GABARITO (referência de correção):
<<REFS>>
RESPOSTA DO ALUNO (considerada MAJORITARIAMENTE CORRETA pelos professores): \"\"\"<<RESPOSTA>>\"\"\"

TEXTO DE APOIO ENTREGUE A ESTE ALUNO:
\"\"\"<<TEXTO>>\"\"\"

Como a resposta do aluno já é majoritariamente correta, o ideal é reconhecer o acerto e, no máximo, aprofundar ou refinar detalhes, sem tratar como erro o que o aluno acertou. Avalie de 1 a 5:
- reconhece_acertos: o texto reconhece explicitamente o que o aluno acertou (1 = ignora, 5 = reconhece com precisão);
- sobre_remediacao: o quanto o texto trata como erro, dúvida ou lacuna algo que o aluno já respondeu corretamente, ou o faz reaprender o que já sabe (1 = nenhuma, 5 = severa);
- coerencia, correcao_conceitual, fidelidade_gabarito, utilidade_pedagogica: como antes (1 = ruim, 5 = excelente).
Primeiro "justificativa" (2 a 3 frases), depois as notas. Formato:
{"justificativa": "...", "reconhece_acertos": n, "sobre_remediacao": n, "coerencia": n, "correcao_conceitual": n, "fidelidade_gabarito": n, "utilidade_pedagogica": n}"""

# --------------------------------------------------------------------------- Pós-teste de transferência (item 8)
POSTTEST_SYSTEM = ("Você é um professor de Ciências/Biologia do ensino fundamental. Elabora questões curtas e corretas "
                   "a partir de um gabarito. Responda apenas com JSON válido.")
POSTTEST_USER = """PERGUNTA ORIGINAL: <<PERGUNTA>>
GABARITO (respostas de referência):
<<REFS>>
CONCEITOS-CHAVE: <<CONCEITOS>>

Elabore 3 questões NOVAS e independentes, cada uma de resposta curta (1 a 2 frases), que testem entendimento de conceitos diferentes do gabarito, sem repetir a pergunta original nem conter a resposta no enunciado. Para cada uma dê a resposta esperada, consistente com o gabarito.
Formato: {"questoes": [{"enunciado": "...", "resposta_esperada": "..."}]}"""

NOTES_MATERIAL_USER = """Pergunta da prova: <<PERGUNTA>>
Sua resposta na prova foi: \"\"\"<<RESPOSTA>>\"\"\"

Depois da prova, você leu este material de estudo:
\"\"\"<<MATERIAL>>\"\"\"

Agora fecha o material. Escreva no seu caderno, com as suas palavras e em até 3 frases curtas, o que você aprendeu e quer lembrar. Devolva só as anotações."""

NOTES_NONE_USER = """Pergunta da prova: <<PERGUNTA>>
Sua resposta na prova foi: \"\"\"<<RESPOSTA>>\"\"\"

Você não recebeu nenhum material. Escreva no seu caderno, com as suas palavras e em até 3 frases curtas, o que você sabe sobre o assunto. Devolva só as anotações."""

ANSWERS_USER = """Pergunta da prova: <<PERGUNTA>>
Sua resposta na prova foi: \"\"\"<<RESPOSTA>>\"\"\"
Suas anotações do caderno: \"\"\"<<NOTAS>>\"\"\"

Sem consultar mais nada, responda cada uma das 3 questões abaixo como aluno de 13 anos (1 a 2 frases cada), usando só o que você sabe e suas anotações. Se não souber, responda o que acha.
<<QUESTOES>>
Formato JSON: {"respostas": ["...", "...", "..."]}"""

POSTGRADER_USER = """Corrija 3 respostas de um aluno do 8º ano. Para cada uma, compare com a resposta esperada e dê nota de 0 a 3 (0 = errada; 1 = algo correto, mas majoritariamente errada ou incompleta; 2 = correta, mas com algum detalhe errado ou faltando; 3 = majoritariamente correta, com os pontos importantes).
GABARITO DA PERGUNTA ORIGINAL (contexto):
<<REFS>>

<<ITENS>>
Formato: {"notas": [n1, n2, n3]}"""
