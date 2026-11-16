"""Todos os prompts (PT-BR). Marcadores <<CHAVE>> são substituídos por fill(); evita conflito com chaves JSON."""
from __future__ import annotations


def fill(tpl: str, **kw) -> str:
    for k, v in kw.items():
        tpl = tpl.replace(f"<<{k}>>", str(v))
    return tpl


def fmt_refs(refs: list[str]) -> str:
    return "\n".join(f"- {r}" for r in refs)


def fmt_concepts(cs: list[str]) -> str:
    return "; ".join(cs)


# --------------------------------------------------------------------------- ETAPA 1: DIAGNÓSTICO
DIAG_SYSTEM = (
    "Você é um professor experiente de Ciências/Biologia do ensino fundamental (8º e 9º anos) no Brasil. "
    "Sua tarefa é diagnosticar, de forma qualitativa e fiel ao gabarito, o que o aluno entendeu e o que não entendeu. "
    "Use SOMENTE o gabarito e os conceitos-chave como referência de correção. Responda apenas com JSON válido."
)

DIAG_USER = """PERGUNTA: <<PERGUNTA>>

GABARITO (respostas de referência escritas por professores):
<<REFS>>

CONCEITOS-CHAVE esperados: <<CONCEITOS>>

RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

Analise a resposta do aluno em relação ao gabarito e devolva JSON no formato:
{
  "conceitos": [
    {"conceito": "<conceito-chave ou ideia essencial do gabarito>", "status": "presente|parcial|ausente|incorreto", "evidencia": "<trecho literal da resposta do aluno ou null>"}
  ],
  "acertos": ["<o que o aluno acertou, em linguagem simples>"],
  "erros_conceituais": [{"descricao": "<concepção equivocada, explicada em 1 frase>", "trecho": "<trecho literal do aluno>"}],
  "lacunas_prioritarias": ["<até 3 ideias/conceitos mais importantes a remediar, em ordem de prioridade>"],
  "nota_estimada": <0, 1, 2 ou 3>
}
Escala de nota_estimada: 0 = errada; 1 = algo correto, mas majoritariamente errada ou incompleta; 2 = correta, mas com algum detalhe errado ou conteúdo importante faltando; 3 = majoritariamente correta, com os pontos importantes.
Inclua em "conceitos" todos os conceitos-chave listados e, se necessário, até 2 ideias essenciais adicionais presentes no gabarito. Não invente conteúdo que não esteja no gabarito."""

# --------------------------------------------------------------------------- ETAPA 2: TEXTO DE APOIO
SUPPORT_SYSTEM = (
    "Você é um professor de Ciências/Biologia que escreve explicações curtas, claras e corretas para alunos do 8º e 9º anos, "
    "em português do Brasil. Nunca afirme algo que contradiga o gabarito ou que você não tenha certeza que é correto."
)

SUPPORT_USER = """PERGUNTA: <<PERGUNTA>>

GABARITO (referência de correção):
<<REFS>>

RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

DIAGNÓSTICO DA RESPOSTA (JSON):
<<DIAG>>

Escreva um TEXTO DE APOIO explicativo para este aluno, com <<MIN>> a <<MAX>> palavras, que:
1. foque ESTRITAMENTE nas lacunas prioritárias e nos erros conceituais do diagnóstico (não revise o conteúdo que o aluno já domina);
2. corrija com delicadeza cada concepção equivocada, explicando o porquê;
3. use linguagem simples, um exemplo ou analogia do cotidiano quando ajudar, e tom encorajador;
4. seja fiel ao gabarito e não acrescente fatos que não possa sustentar;
5. NÃO entregue a resposta pronta nem copie o gabarito: ajude o aluno a reconstruí-la.
Devolva somente o texto (sem título, sem listas de tópicos longas, sem JSON)."""

# --------------------------------------------------------------------------- ETAPA 3: NOVAS QUESTÕES
QUESTIONS_SYSTEM = (
    "Você é um professor de Ciências/Biologia que elabora questões dissertativas curtas, claras e corretas, "
    "calibradas pela Taxonomia de Bloom revisada (Anderson e Krathwohl, 2001), para alunos do 8º e 9º anos. Responda apenas com JSON válido."
)

QUESTIONS_USER = """PERGUNTA ORIGINAL: <<PERGUNTA>>

GABARITO (referência de correção):
<<REFS>>

<<CONTEXTO>>

Elabore <<N>> novas questões dissertativas curtas, uma para cada nível da Taxonomia de Bloom abaixo, nesta ordem: <<NIVEIS>>.
Regras: (a) <<REGRA_FOCO>>; (b) cada questão deve poder ser respondida em 1 a 3 frases por um aluno do 8º/9º ano; (c) a resposta esperada deve ser consistente com o gabarito; (d) não repita a pergunta original; (e) o enunciado não pode conter a resposta.
Formato:
{"questoes": [{"nivel_bloom": "<nível>", "enunciado": "<texto>", "resposta_esperada": "<1 a 2 frases>"}]}"""

CTX_ADAPTIVE = (
    "TEXTO DE APOIO JÁ ENTREGUE AO ALUNO:\n\"\"\"<<TEXTO>>\"\"\"\n\n"
    "LACUNAS PRIORITÁRIAS DO ALUNO: <<LACUNAS>>"
)
FOCO_ADAPTIVE = "as questões devem testar se o aluno superou ESPECIFICAMENTE as lacunas prioritárias listadas, usando o texto de apoio como base"
CTX_STATIC = "CONCEITOS-CHAVE da questão: <<CONCEITOS>>"
FOCO_STATIC = "as questões devem cobrir de forma geral os conceitos-chave, sem presumir o que um aluno específico errou"

# --------------------------------------------------------------------------- CONDIÇÃO A0: geração direta (sem diagnóstico explícito)
DIRECT_USER = """PERGUNTA: <<PERGUNTA>>

GABARITO (referência de correção):
<<REFS>>

CONCEITOS-CHAVE: <<CONCEITOS>>

RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

Com base na resposta deste aluno, produza em UMA única resposta:
(1) um TEXTO DE APOIO explicativo de <<MIN>> a <<MAX>> palavras focado estritamente no que este aluno errou ou deixou de dizer, em linguagem simples e encorajadora, fiel ao gabarito, sem entregar a resposta pronta;
(2) <<N>> novas questões dissertativas curtas, uma para cada nível da Taxonomia de Bloom: <<NIVEIS>>, que testem se o aluno superou a lacuna (enunciado sem a resposta; resposta esperada consistente com o gabarito).
Formato JSON:
{"texto_apoio": "<texto>", "questoes": [{"nivel_bloom": "<nível>", "enunciado": "<texto>", "resposta_esperada": "<1 a 2 frases>"}]}"""

# --------------------------------------------------------------------------- CONDIÇÃO ESTÁTICA (mesmo material para todos os alunos da questão)
STATIC_USER = """PERGUNTA: <<PERGUNTA>>

GABARITO (referência de correção):
<<REFS>>

CONCEITOS-CHAVE: <<CONCEITOS>>

Escreva um TEXTO DE REFORÇO com <<MIN>> a <<MAX>> palavras sobre o tema desta pergunta, que será entregue IGUALMENTE a todos os alunos da turma (você não conhece as respostas individuais). Deve explicar os conceitos-chave de forma clara, correta e fiel ao gabarito, em linguagem simples para o 8º/9º ano. Devolva somente o texto."""

# --------------------------------------------------------------------------- CONDIÇÃO A2: verificação ancorada no gabarito + reescrita
VERIFY_SYSTEM = (
    "Você é um revisor rigoroso de conteúdo de Ciências/Biologia do ensino fundamental. "
    "Verifica se cada afirmação de um texto didático é sustentada pelo gabarito ou é conhecimento escolar básico correto. Responda apenas com JSON válido."
)

VERIFY_USER = """GABARITO (referência):
<<REFS>>
CONCEITOS-CHAVE: <<CONCEITOS>>

TEXTO A VERIFICAR:
\"\"\"<<TEXTO>>\"\"\"

Decomponha o texto em afirmações factuais atômicas e classifique cada uma:
- "suportada": consta ou decorre diretamente do gabarito;
- "conhecimento_geral_correto": não está no gabarito, mas é conhecimento escolar básico inequivocamente correto;
- "nao_suportada": não pode ser verificada pelo gabarito e não é conhecimento básico seguro;
- "incorreta": contradiz o gabarito ou é cientificamente errada.
Formato: {"afirmacoes": [{"afirmacao": "<texto>", "veredito": "suportada|conhecimento_geral_correto|nao_suportada|incorreta", "motivo": "<curto>"}]}"""

REWRITE_USER = """GABARITO (referência):
<<REFS>>

TEXTO ORIGINAL:
\"\"\"<<TEXTO>>\"\"\"

PROBLEMAS ENCONTRADOS (afirmações a remover ou corrigir):
<<PROBLEMAS>>

Reescreva o texto removendo ou corrigindo SOMENTE essas afirmações, mantendo o tom, a fluência, a estrutura e o tamanho (<<MIN>> a <<MAX>> palavras). Não adicione conteúdo novo. Devolva somente o texto reescrito."""

# --------------------------------------------------------------------------- JUIZ (LLM-as-a-Judge)
JUDGE_SYSTEM = (
    "Você é um avaliador especialista em educação em Ciências/Biologia (ensino fundamental, Brasil). "
    "Avalie com rigor e independência do tamanho ou do estilo do texto: texto longo ou bem escrito NÃO é, por si só, melhor. "
    "Responda apenas com JSON válido."
)

JUDGE_TEXT_USER = """PERGUNTA: <<PERGUNTA>>
GABARITO (referência de correção):
<<REFS>>
RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

TEXTO DE APOIO ENTREGUE A ESTE ALUNO:
\"\"\"<<TEXTO>>\"\"\"

Avalie o texto de 1 a 5 em cada dimensão (âncoras: 1 = muito ruim, 3 = aceitável, 5 = excelente):
- coerencia: clareza, organização e fluidez em português;
- correcao_conceitual: ausência de erros científicos; 1 = há erro grave, 5 = totalmente correto;
- fidelidade_gabarito: alinhamento ao conteúdo do gabarito, sem contradizê-lo nem desviar do tema;
- foco_na_lacuna: o quanto o texto trata ESPECIFICAMENTE do que ESTE aluno errou ou omitiu (1 = genérico, ignora o erro dele; 5 = ataca exatamente as lacunas dele sem repetir o que ele já sabe);
- utilidade_pedagogica: o quanto ajudaria este aluno a entender e corrigir seu erro (sem entregar a resposta pronta);
- adequacao_nivel: linguagem e profundidade adequadas ao 8º/9º ano.
Conte também "afirmacoes_incorretas": número de afirmações cientificamente erradas ou contrárias ao gabarito.
Primeiro escreva "justificativa" (2 a 4 frases), depois as notas. Formato:
{"justificativa": "...", "coerencia": n, "correcao_conceitual": n, "fidelidade_gabarito": n, "foco_na_lacuna": n, "utilidade_pedagogica": n, "adequacao_nivel": n, "afirmacoes_incorretas": n}"""

JUDGE_Q_USER = """PERGUNTA ORIGINAL: <<PERGUNTA>>
GABARITO (referência de correção):
<<REFS>>
RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

NOVAS QUESTÕES GERADAS PARA ESTE ALUNO:
<<QUESTOES>>

Para CADA questão, avalie:
- nivel_bloom_percebido: nível cognitivo que a questão realmente exige (lembrar|entender|aplicar|analisar|avaliar|criar), independente do rótulo dado;
- alinhamento_gabarito (1-5): a questão e sua resposta esperada são coerentes com o gabarito;
- clareza (1-5): enunciado claro, sem ambiguidade, respondível em 1 a 3 frases;
- relevancia_lacuna (1-5): testa o que ESTE aluno errou ou omitiu (1 = genérica);
- resposta_esperada_correta: true/false.
Formato: {"questoes": [{"nivel_bloom_percebido": "...", "alinhamento_gabarito": n, "clareza": n, "relevancia_lacuna": n, "resposta_esperada_correta": true}]}  (um objeto por questão, na mesma ordem)"""

JUDGE_PAIR_USER = """PERGUNTA: <<PERGUNTA>>
GABARITO (referência de correção):
<<REFS>>
RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

MATERIAL A:
\"\"\"<<A>>\"\"\"

MATERIAL B:
\"\"\"<<B>>\"\"\"

Qual material ajudaria MAIS este aluno a superar a lacuna conceitual específica dele, sendo ao mesmo tempo correto e fiel ao gabarito? Ignore o tamanho e o estilo; não prefira o mais longo. Responda JSON:
{"justificativa": "<2 a 3 frases>", "vencedor": "A|B|empate"}"""

# --------------------------------------------------------------------------- ALUNO SIMULADO + CORRETOR (E3, exploratório)
SIM_SYSTEM = (
    "Você interpreta um aluno brasileiro do 8º ano (13 anos). Você escreve do jeito de um aluno, com frases curtas e vocabulário simples. "
    "Você só consegue usar o que realmente entendeu do material que leu e do que já sabia antes."
)

SIM_USER_MATERIAL = """Pergunta da prova: <<PERGUNTA>>

Sua resposta anterior foi: \"\"\"<<RESPOSTA>>\"\"\"

Depois da prova, você leu este material de estudo:
\"\"\"<<MATERIAL>>\"\"\"

Agora responda a pergunta de novo, com suas palavras, como um aluno de 13 anos (1 a 3 frases). Se algo do material não ficou claro para você, mantenha sua ideia anterior nessa parte. Devolva só a resposta."""

SIM_USER_NONE = """Pergunta da prova: <<PERGUNTA>>

Sua resposta anterior foi: \"\"\"<<RESPOSTA>>\"\"\"

Você não recebeu nenhum material nem feedback. Responda a pergunta de novo, com suas palavras, como um aluno de 13 anos (1 a 3 frases). Devolva só a resposta."""

GRADER_SYSTEM = (
    "Você é um corretor de Biologia do ensino fundamental. Atribui nota de 0 a 3 comparando a resposta do aluno ao gabarito. Responda apenas com JSON válido."
)

GRADER_USER = """PERGUNTA: <<PERGUNTA>>
GABARITO (respostas de referência):
<<REFS>>
CONCEITOS-CHAVE: <<CONCEITOS>>
RESPOSTA DO ALUNO: \"\"\"<<RESPOSTA>>\"\"\"

Escala: 0 = a resposta está errada; 1 = tem algo correto, mas ainda está majoritariamente errada ou incompleta; 2 = está correta, mas com algum detalhe errado ou faltando conteúdo importante; 3 = está majoritariamente correta, com os pontos importantes apresentados.
Formato: {"nota": <0|1|2|3>}"""
