# Resultados da rodada de robustez

Critérios, hipóteses e margens: ver `PRE_REGISTRO.md` (commit anterior às rodadas). Todos os IC são bootstrap por questão (15 clusters).

## H1. O efeito A1 > S replica? (foco na lacuna e utilidade; 1–5)
| replica                  | dim                  |   A1-S |    lo |    hi |   p_holm | replica_criterio   |
|:-------------------------|:---------------------|-------:|------:|------:|---------:|:-------------------|
| piloto, J1 (original)    | foco_na_lacuna       |  0.8   | 0.422 | 1.206 |        0 | sim                |
| piloto, J1 (original)    | utilidade_pedagogica |  0.517 | 0.261 | 0.789 |        0 | sim                |
| piloto, J2               | foco_na_lacuna       |  0.583 | 0.339 | 0.828 |        0 | sim                |
| piloto, J2               | utilidade_pedagogica |  0.311 | 0.161 | 0.456 |        0 | sim                |
| semente 1, J1            | foco_na_lacuna       |  0.75  | 0.467 | 1.05  |        0 | sim                |
| semente 1, J1            | utilidade_pedagogica |  0.478 | 0.25  | 0.706 |        0 | sim                |
| semente 2, J1            | foco_na_lacuna       |  0.628 | 0.322 | 0.961 |        0 | sim                |
| semente 2, J1            | utilidade_pedagogica |  0.378 | 0.156 | 0.617 |        0 | sim                |
| gerador 2 (DeepSeek), J1 | foco_na_lacuna       |  0.59  | 0.333 | 0.927 |        0 | sim                |
| gerador 2 (DeepSeek), J1 | utilidade_pedagogica |  0.315 | 0.135 | 0.581 |        0 | sim                |
| gerador 2 (DeepSeek), J2 | foco_na_lacuna       |  1.528 | 1.356 | 1.706 |        0 | sim                |
| gerador 2 (DeepSeek), J2 | utilidade_pedagogica |  0.781 | 0.67  | 0.905 |        0 | sim                |
| diagnóstico v2, J1       | foco_na_lacuna       |  0.817 | 0.506 | 1.15  |        0 | sim                |
| diagnóstico v2, J1       | utilidade_pedagogica |  0.528 | 0.322 | 0.75  |        0 | sim                |
| diagnóstico v2, J2       | foco_na_lacuna       |  0.606 | 0.45  | 0.761 |        0 | sim                |
| diagnóstico v2, J2       | utilidade_pedagogica |  0.289 | 0.15  | 0.422 |        0 | sim                |

**Critério do pré-registro** (diferença positiva e IC95% sem zero nas duas dimensões): replicou em 8 de 8 réplicas.

## H2. Diagnóstico explícito (A1) vs geração direta (A0)
| replica       | dim                  |   A1-A0 |     lo |     hi | veredito                         |
|:--------------|:---------------------|--------:|-------:|-------:|:---------------------------------|
| piloto, J1    | foco_na_lacuna       |   0.022 | -0.167 |  0.233 | equivalente (IC dentro de ±0,25) |
| piloto, J1    | utilidade_pedagogica |   0.122 | -0.028 |  0.283 | inconclusivo                     |
| piloto, J2    | foco_na_lacuna       |  -0.1   | -0.233 |  0.028 | equivalente (IC dentro de ±0,25) |
| piloto, J2    | utilidade_pedagogica |   0.172 |  0.083 |  0.261 | x melhor                         |
| semente 1, J1 | foco_na_lacuna       |   0.017 | -0.167 |  0.233 | equivalente (IC dentro de ±0,25) |
| semente 1, J1 | utilidade_pedagogica |   0.039 | -0.1   |  0.206 | equivalente (IC dentro de ±0,25) |
| semente 2, J1 | foco_na_lacuna       |   0     | -0.156 |  0.15  | equivalente (IC dentro de ±0,25) |
| semente 2, J1 | utilidade_pedagogica |   0.056 | -0.083 |  0.206 | equivalente (IC dentro de ±0,25) |
| gerador 2, J1 | foco_na_lacuna       |  -0.056 | -0.119 | -0.006 | equivalente (IC dentro de ±0,25) |
| gerador 2, J1 | utilidade_pedagogica |  -0.039 | -0.112 |  0.017 | equivalente (IC dentro de ±0,25) |
| gerador 2, J2 | foco_na_lacuna       |  -0.371 | -0.52  | -0.211 | y melhor                         |
| gerador 2, J2 | utilidade_pedagogica |  -0.017 | -0.119 |  0.079 | equivalente (IC dentro de ±0,25) |

## H3. Ablação limpa: A1 com diagnóstico vazio (A1ø)
| juiz   | contraste                  | dim                  |   est |     lo |    hi | veredito                         |
|:-------|:---------------------------|:---------------------|------:|-------:|------:|:---------------------------------|
| J1     | A1ø (sem diagnóstico) − A1 | foco_na_lacuna       | 0.161 |  0.022 | 0.317 | x melhor                         |
| J1     | A1ø − A0                   | foco_na_lacuna       | 0.183 |  0.044 | 0.356 | x melhor                         |
| J1     | A1ø − S                    | foco_na_lacuna       | 0.961 |  0.633 | 1.311 | x melhor                         |
| J1     | A1ø (sem diagnóstico) − A1 | utilidade_pedagogica | 0.078 | -0.039 | 0.189 | equivalente (IC dentro de ±0,25) |
| J1     | A1ø − A0                   | utilidade_pedagogica | 0.2   |  0.072 | 0.344 | x melhor                         |
| J1     | A1ø − S                    | utilidade_pedagogica | 0.594 |  0.378 | 0.828 | x melhor                         |
| J2     | A1ø (sem diagnóstico) − A1 | foco_na_lacuna       | 0.417 |  0.289 | 0.533 | x melhor                         |
| J2     | A1ø − A0                   | foco_na_lacuna       | 0.317 |  0.2   | 0.428 | x melhor                         |
| J2     | A1ø − S                    | foco_na_lacuna       | 1     |  0.811 | 1.189 | x melhor                         |
| J2     | A1ø (sem diagnóstico) − A1 | utilidade_pedagogica | 0.194 |  0.117 | 0.261 | x melhor                         |
| J2     | A1ø − A0                   | utilidade_pedagogica | 0.367 |  0.306 | 0.433 | x melhor                         |
| J2     | A1ø − S                    | utilidade_pedagogica | 0.506 |  0.344 | 0.65  | x melhor                         |

## H4. Diagnóstico calibrado (v2) não é pior que o original (v0)?
| juiz   | dim                  |   A1v2-A1v0 |     lo |    hi | nao_pior(lo>-0,25)   | melhor(lo>0)   |
|:-------|:---------------------|------------:|-------:|------:|:---------------------|:---------------|
| J1     | foco_na_lacuna       |       0.017 | -0.128 | 0.156 | sim                  | não            |
| J1     | utilidade_pedagogica |       0.011 | -0.089 | 0.094 | sim                  | não            |
| J1     | coerencia            |      -0.022 | -0.089 | 0.044 | sim                  | não            |
| J1     | correcao_conceitual  |       0.022 | -0.006 | 0.061 | sim                  | não            |
| J1     | fidelidade_gabarito  |      -0.078 | -0.217 | 0.056 | sim                  | não            |
| J1     | adequacao_nivel      |      -0.056 | -0.117 | 0     | sim                  | não            |
| J1     | q_relevancia         |       0.05  | -0.037 | 0.139 | sim                  | não            |
| J2     | foco_na_lacuna       |       0.022 | -0.128 | 0.178 | sim                  | não            |
| J2     | utilidade_pedagogica |      -0.022 | -0.094 | 0.056 | sim                  | não            |
| J2     | coerencia            |      -0.067 | -0.139 | 0.011 | sim                  | não            |
| J2     | correcao_conceitual  |      -0.072 | -0.194 | 0.044 | sim                  | não            |
| J2     | fidelidade_gabarito  |      -0.078 | -0.178 | 0.017 | sim                  | não            |
| J2     | adequacao_nivel      |       0.006 | -0.067 | 0.078 | sim                  | não            |
| J2     | q_relevancia         |       0.017 | -0.094 | 0.133 | sim                  | não            |

## H5. Qualidade como material de estudo SEM ver a resposta do aluno (A1 vs S)
| juiz   | contraste   | dim                 |    est |     lo |     hi | não_pior(lo>-0,25)   |
|:-------|:------------|:--------------------|-------:|-------:|-------:|:---------------------|
| J1     | A1 − S      | coerencia           | -0.078 | -0.161 | -0.017 | sim                  |
| J1     | A1 − S      | correcao_conceitual | -0.089 | -0.211 | -0.011 | sim                  |
| J1     | A1 − S      | fidelidade_gabarito | -0.161 | -0.317 | -0.039 | não                  |
| J1     | A1 − S      | completude          | -0.256 | -0.483 | -0.072 | não                  |
| J1     | A1 − S      | adequacao_nivel     | -0.056 | -0.122 | -0.011 | sim                  |
| J1     | A1 − S      | qualidade_geral     | -0.167 | -0.328 | -0.033 | não                  |
| J2     | A1 − S      | coerencia           | -0.522 | -0.65  | -0.4   | não                  |
| J2     | A1 − S      | correcao_conceitual | -0.428 | -0.6   | -0.272 | não                  |
| J2     | A1 − S      | fidelidade_gabarito | -0.683 | -0.9   | -0.472 | não                  |
| J2     | A1 − S      | completude          | -0.839 | -1.056 | -0.617 | não                  |
| J2     | A1 − S      | adequacao_nivel     | -0.167 | -0.25  | -0.089 | não                  |
| J2     | A1 − S      | qualidade_geral     | -0.8   | -1.022 | -0.589 | não                  |

## Concordância entre os dois juízes (piloto, notas absolutas, 5 condições × 180 itens)
| dim                  |   n |   spearman |    QWK |   J1 média |   J2 média |   J1 % nota 5 |   J2 % nota 5 |
|:---------------------|----:|-----------:|-------:|-----------:|-----------:|--------------:|--------------:|
| coerencia            | 900 |      0.398 |  0.443 |      4.624 |      4.426 |         0.79  |         0.569 |
| correcao_conceitual  | 900 |      0.101 |  0.081 |      4.796 |      4.598 |         0.917 |         0.663 |
| fidelidade_gabarito  | 900 |      0.056 | -0.029 |      4.517 |      4.426 |         0.747 |         0.511 |
| foco_na_lacuna       | 900 |      0.515 |  0.252 |      3.792 |      2.371 |         0.587 |         0.008 |
| utilidade_pedagogica | 900 |      0.58  |  0.288 |      4.024 |      2.854 |         0.642 |         0.001 |
| adequacao_nivel      | 900 |      0.402 |  0.358 |      4.738 |      4.573 |         0.831 |         0.637 |

Os dois juízes têm o **mesmo sinal** em 10 de 24 contrastes do piloto; ICs sem zero: J1 em 9, J2 em 15.

| contraste                       | dim                  |     J1 |     J2 | J1_ic_sem_zero   | J2_ic_sem_zero   | mesmo_sinal   |
|:--------------------------------|:---------------------|-------:|-------:|:-----------------|:-----------------|:--------------|
| A1_pipeline − S_estatico        | coerencia            |  0.106 | -0.2   | True             | True             | False         |
| A1_pipeline − S_estatico        | correcao_conceitual  |  0.044 | -0.439 | False            | True             | False         |
| A1_pipeline − S_estatico        | fidelidade_gabarito  |  0.144 | -0.544 | False            | True             | False         |
| A1_pipeline − S_estatico        | foco_na_lacuna       |  0.8   |  0.583 | True             | True             | True          |
| A1_pipeline − S_estatico        | utilidade_pedagogica |  0.517 |  0.311 | True             | True             | True          |
| A1_pipeline − S_estatico        | adequacao_nivel      |  0.117 | -0.133 | True             | True             | False         |
| A0_direto − S_estatico          | coerencia            | -0.022 | -0.356 | False            | True             | True          |
| A0_direto − S_estatico          | correcao_conceitual  |  0.028 | -0.317 | False            | True             | False         |
| A0_direto − S_estatico          | fidelidade_gabarito  |  0.128 | -0.294 | False            | True             | False         |
| A0_direto − S_estatico          | foco_na_lacuna       |  0.778 |  0.683 | True             | True             | True          |
| A0_direto − S_estatico          | utilidade_pedagogica |  0.394 |  0.139 | True             | False            | True          |
| A0_direto − S_estatico          | adequacao_nivel      |  0.017 | -0.278 | False            | True             | False         |
| A1_pipeline − A0_direto         | coerencia            |  0.128 |  0.156 | True             | True             | True          |
| A1_pipeline − A0_direto         | correcao_conceitual  |  0.017 | -0.122 | False            | False            | False         |
| A1_pipeline − A0_direto         | fidelidade_gabarito  |  0.017 | -0.25  | False            | True             | False         |
| A1_pipeline − A0_direto         | foco_na_lacuna       |  0.022 | -0.1   | False            | False            | False         |
| A1_pipeline − A0_direto         | utilidade_pedagogica |  0.122 |  0.172 | False            | True             | True          |
| A1_pipeline − A0_direto         | adequacao_nivel      |  0.1   |  0.144 | True             | False            | True          |
| A2_pipeline_verif − A1_pipeline | coerencia            |  0.006 | -0.044 | False            | False            | False         |
| A2_pipeline_verif − A1_pipeline | correcao_conceitual  |  0.033 |  0.061 | True             | False            | True          |
| A2_pipeline_verif − A1_pipeline | fidelidade_gabarito  |  0.05  |  0.056 | False            | False            | True          |
| A2_pipeline_verif − A1_pipeline | foco_na_lacuna       |  0.078 | -0.011 | False            | False            | False         |
| A2_pipeline_verif − A1_pipeline | utilidade_pedagogica |  0.05  | -0.078 | False            | True             | False         |
| A2_pipeline_verif − A1_pipeline | adequacao_nivel      |  0     |  0.039 | False            | False            | False         |

## Juiz 2 par-a-par (duas ordens)
| par                           |   itens |   1º vence |   mesmo veredito nas 2 ordens |   x vence nas 2 |   y vence nas 2 |
|:------------------------------|--------:|-----------:|------------------------------:|----------------:|----------------:|
| A1_nodiag vs A1_pipeline      |     180 |      0.257 |                         0.411 |           0.222 |           0.189 |
| A1_pipeline vs A0_direto      |     180 |      0.346 |                         0.644 |           0.45  |           0.194 |
| A1_pipeline vs S_estatico     |     180 |      0.318 |                         0.544 |           0.261 |           0.283 |
| A1_pipeline@v2 vs A1_pipeline |     180 |      0.272 |                         0.461 |           0.217 |           0.244 |

## Robustez: modelo linear misto sobre as diferenças por item (efeito aleatório de questão) vs. bootstrap por questão
| juiz   | dim                  | contraste                    |   est_misto |   lo_misto |   hi_misto |   p_misto |   tau_questao |   est_bootstrap |   lo_boot |   hi_boot |
|:-------|:---------------------|:-----------------------------|------------:|-----------:|-----------:|----------:|--------------:|----------------:|----------:|----------:|
| J1     | foco_na_lacuna       | A1_pipeline − S_estatico     |       0.8   |      0.391 |      1.209 |     0     |         0.671 |           0.8   |     0.422 |     1.206 |
| J1     | foco_na_lacuna       | A1_pipeline − A0_direto      |       0.022 |     -0.228 |      0.273 |     0.862 |         0.368 |           0.022 |    -0.167 |     0.233 |
| J1     | foco_na_lacuna       | A1_nodiag − A1_pipeline      |       0.161 |     -0.003 |      0.325 |     0.055 |         0.071 |           0.161 |     0.022 |     0.317 |
| J1     | foco_na_lacuna       | A1_pipeline@v2 − A1_pipeline |       0.017 |     -0.155 |      0.188 |     0.849 |         0.086 |           0.017 |    -0.128 |     0.156 |
| J1     | utilidade_pedagogica | A1_pipeline − S_estatico     |       0.517 |      0.271 |      0.762 |     0     |         0.312 |           0.517 |     0.261 |     0.789 |
| J1     | utilidade_pedagogica | A1_pipeline − A0_direto      |       0.122 |     -0.039 |      0.284 |     0.138 |         0.131 |           0.122 |    -0.028 |     0.283 |
| J1     | utilidade_pedagogica | A1_nodiag − A1_pipeline      |       0.078 |     -0.055 |      0.211 |     0.252 |         0.062 |           0.078 |    -0.039 |     0.189 |
| J1     | utilidade_pedagogica | A1_pipeline@v2 − A1_pipeline |       0.011 |     -0.118 |      0.14  |     0.866 |         0.079 |           0.011 |    -0.089 |     0.094 |
| J2     | foco_na_lacuna       | A1_pipeline − S_estatico     |       0.583 |      0.329 |      0.837 |     0     |         0.446 |           0.583 |     0.339 |     0.828 |
| J2     | foco_na_lacuna       | A1_pipeline − A0_direto      |      -0.1   |     -0.274 |      0.074 |     0.26  |         0.26  |          -0.1   |    -0.233 |     0.028 |
| J2     | foco_na_lacuna       | A1_nodiag − A1_pipeline      |       0.417 |      0.292 |      0.541 |     0     |         0.038 |           0.417 |     0.289 |     0.533 |
| J2     | foco_na_lacuna       | A1_pipeline@v2 − A1_pipeline |       0.022 |     -0.152 |      0.196 |     0.802 |         0.246 |           0.022 |    -0.128 |     0.178 |
| J2     | utilidade_pedagogica | A1_pipeline − S_estatico     |       0.311 |      0.16  |      0.462 |     0     |         0.227 |           0.311 |     0.161 |     0.456 |
| J2     | utilidade_pedagogica | A1_pipeline − A0_direto      |       0.172 |      0.062 |      0.282 |     0.002 |         0.054 |           0.172 |     0.083 |     0.261 |
| J2     | utilidade_pedagogica | A1_nodiag − A1_pipeline      |       0.194 |      0.083 |      0.306 |     0.001 |         0.072 |           0.194 |     0.117 |     0.261 |
| J2     | utilidade_pedagogica | A1_pipeline@v2 − A1_pipeline |      -0.022 |     -0.134 |      0.089 |     0.697 |         0.072 |          -0.022 |    -0.094 |     0.056 |

## Consistência entre tópicos (substituto parcial de um 2º conjunto de dados; IC com poucas questões por tópico)
| tópico                   |   questões | dim                  |   J1 A1−S |   J1 lo |   J1 hi |   J2 A1−S |
|:-------------------------|-----------:|:---------------------|----------:|--------:|--------:|----------:|
| células e metabolismo    |          4 | foco_na_lacuna       |     1.708 |   1.125 |   2.333 |     0.938 |
| genética                 |          2 | foco_na_lacuna       |     0.125 |  -0.25  |   0.5   |     0.208 |
| sistemas do corpo humano |          9 | foco_na_lacuna       |     0.546 |   0.213 |   0.907 |     0.509 |
| células e metabolismo    |          4 | utilidade_pedagogica |     1.146 |   0.812 |   1.458 |     0.5   |
| genética                 |          2 | utilidade_pedagogica |     0.042 |  -0.25  |   0.333 |     0.042 |
| sistemas do corpo humano |          9 | utilidade_pedagogica |     0.343 |   0.12  |   0.583 |     0.287 |

## H6. Respostas nota 3 (60 itens): sobre-remediação (1 = nenhuma, 5 = severa) e reconhecimento dos acertos
| juiz   | condition   |   sobre_remediacao |   reconhece_acertos |
|:-------|:------------|-------------------:|--------------------:|
| J1     | A0_direto   |              2.033 |               4.117 |
| J1     | A1_pipeline |              1.8   |               4.25  |
| J1     | S_estatico  |              1.3   |               4.583 |
| J2     | A0_direto   |              2.983 |               2.75  |
| J2     | A1_pipeline |              3.017 |               2.483 |
| J2     | S_estatico  |              2.233 |               1.233 |

| juiz   | contraste                    | dim                  |    est |     lo |     hi |
|:-------|:-----------------------------|:---------------------|-------:|-------:|-------:|
| J1     | A1 − S                       | sobre_remediacao     |  0.5   |  0.25  |  0.75  |
| J1     | A0 − S                       | sobre_remediacao     |  0.733 |  0.383 |  1.083 |
| J1     | A1 − A0                      | sobre_remediacao     | -0.233 | -0.55  |  0.1   |
| J1     | A1 − S                       | reconhece_acertos    | -0.333 | -0.617 | -0.017 |
| J1     | A0 − S                       | reconhece_acertos    | -0.467 | -0.767 | -0.133 |
| J1     | A1 − A0                      | reconhece_acertos    |  0.133 | -0.1   |  0.367 |
| J1     | A1 − S                       | utilidade_pedagogica | -0.417 | -0.717 | -0.067 |
| J1     | A0 − S                       | utilidade_pedagogica | -0.667 | -1.05  | -0.25  |
| J1     | A1 − A0                      | utilidade_pedagogica |  0.25  | -0.05  |  0.517 |
| J1     | A1 − S                       | coerencia            | -0.317 | -0.567 | -0.05  |
| J1     | A0 − S                       | coerencia            | -0.417 | -0.667 | -0.15  |
| J1     | A1 − A0                      | coerencia            |  0.1   | -0.167 |  0.334 |
| J1     | A1 − S                       | correcao_conceitual  |  0.1   | -0.083 |  0.333 |
| J1     | A0 − S                       | correcao_conceitual  |  0.033 | -0.183 |  0.25  |
| J1     | A1 − A0                      | correcao_conceitual  |  0.067 | -0.1   |  0.25  |
| J1     | A1 − S                       | fidelidade_gabarito  | -0.167 | -0.433 |  0.133 |
| J1     | A0 − S                       | fidelidade_gabarito  | -0.3   | -0.533 | -0.033 |
| J1     | A1 − A0                      | fidelidade_gabarito  |  0.133 | -0.05  |  0.317 |
| J1     | A1 − S (juiz padrão, nota 3) | foco_na_lacuna       |  0.883 |  0.483 |  1.367 |
| J1     | A1 − S (juiz padrão, nota 3) | utilidade_pedagogica |  0.433 |  0.117 |  0.75  |
| J2     | A1 − S                       | sobre_remediacao     |  0.783 |  0.4   |  1.167 |
| J2     | A0 − S                       | sobre_remediacao     |  0.75  |  0.467 |  1.033 |
| J2     | A1 − A0                      | sobre_remediacao     |  0.033 | -0.383 |  0.383 |
| J2     | A1 − S                       | reconhece_acertos    |  1.25  |  0.867 |  1.617 |
| J2     | A0 − S                       | reconhece_acertos    |  1.517 |  1.267 |  1.8   |
| J2     | A1 − A0                      | reconhece_acertos    | -0.267 | -0.733 |  0.2   |
| J2     | A1 − S                       | utilidade_pedagogica |  0.2   |  0     |  0.417 |
| J2     | A0 − S                       | utilidade_pedagogica |  0.133 |  0.05  |  0.233 |
| J2     | A1 − A0                      | utilidade_pedagogica |  0.067 | -0.117 |  0.283 |
| J2     | A1 − S                       | coerencia            | -0.317 | -0.483 | -0.15  |
| J2     | A0 − S                       | coerencia            | -0.317 | -0.467 | -0.167 |
| J2     | A1 − A0                      | coerencia            |  0     | -0.167 |  0.183 |
| J2     | A1 − S                       | correcao_conceitual  | -0.317 | -0.5   | -0.15  |
| J2     | A0 − S                       | correcao_conceitual  | -0.117 | -0.383 |  0.15  |
| J2     | A1 − A0                      | correcao_conceitual  | -0.2   | -0.4   |  0     |
| J2     | A1 − S                       | fidelidade_gabarito  | -0.3   | -0.467 | -0.133 |
| J2     | A0 − S                       | fidelidade_gabarito  | -0.117 | -0.267 |  0.05  |
| J2     | A1 − A0                      | fidelidade_gabarito  | -0.183 | -0.35  | -0.017 |
| J2     | A1 − S (juiz padrão, nota 3) | foco_na_lacuna       |  0.433 |  0.233 |  0.617 |
| J2     | A1 − S (juiz padrão, nota 3) | utilidade_pedagogica |  0.083 | -0.133 |  0.317 |

## H7 (exploratório). Pós-teste de transferência: o aluno simulado perde acesso ao material e responde a 3 questões novas
| condição          |   n |   nota média (0-3) no pós-teste |    lo |    hi |
|:------------------|----:|--------------------------------:|------:|------:|
| A0_direto         | 172 |                           1.953 | 1.797 | 2.11  |
| A1_pipeline       | 171 |                           2.053 | 1.913 | 2.185 |
| A2_pipeline_verif | 171 |                           2.051 | 1.925 | 2.18  |
| N_sem_material    | 163 |                           1.47  | 1.286 | 1.644 |
| S0_gabarito       | 173 |                           1.961 | 1.784 | 2.129 |
| S_estatico        | 168 |                           1.992 | 1.841 | 2.143 |

| contraste                          |   est |     lo |    hi |   p_boot |   n |   p_holm |
|:-----------------------------------|------:|-------:|------:|---------:|----:|---------:|
| S_estatico − N_sem_material        | 0.55  |  0.425 | 0.667 |    0     | 154 |    0     |
| A0_direto − N_sem_material         | 0.504 |  0.388 | 0.609 |    0     | 156 |    0     |
| A1_pipeline − N_sem_material       | 0.591 |  0.487 | 0.684 |    0     | 154 |    0     |
| A2_pipeline_verif − N_sem_material | 0.593 |  0.451 | 0.737 |    0     | 154 |    0     |
| S0_gabarito − N_sem_material       | 0.482 |  0.346 | 0.642 |    0     | 157 |    0     |
| A1_pipeline − S_estatico           | 0.048 | -0.032 | 0.152 |    0.295 | 161 |    0.59  |
| A1_pipeline − A0_direto            | 0.112 |  0.057 | 0.173 |    0     | 163 |    0     |
| A2_pipeline_verif − A1_pipeline    | 0.002 | -0.071 | 0.084 |    0.995 | 164 |    0.995 |

Cópia literal (trigramas) das anotações do aluno em relação ao material lido:
| condição          |   copia_3g |
|:------------------|-----------:|
| A0_direto         |      0.119 |
| A1_pipeline       |      0.158 |
| A2_pipeline_verif |      0.161 |
| S0_gabarito       |      0.118 |
| S_estatico        |      0.11  |

## Custo desta rodada (estimado pelos tokens e preços de lista)
US$ 6.27
