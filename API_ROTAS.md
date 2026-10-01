# API Til Marcon

Base URL local: `http://localhost:8000`. A documentação interativa também fica em `/docs` e `/redoc`; `/openapi.json` contém o schema gerado. Rotas protegidas usam `Authorization: Bearer <access_token>`. Erros de validação de request retornam HTTP 400 com `detail` e a lista `erros`; respostas de erro de domínio usam `detail` em português.

Perfis: `ADMIN`, `ALMOXARIFE`, `SOLICITANTE`, `GESTOR`. IDs precisam ser positivos. Quantidades usam decimal com até três casas.

## Auth

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| POST `/auth/login` | Público | JSON: `login`, `senha` | 200 token e usuário; 400 validação; 401 credenciais inválidas |
| POST `/auth/login/form` | Público | Form URL-encoded: `username`, `password` | 200 access token; 401 credenciais inválidas |
| GET `/auth/me` | Autenticado | Sem body | 200 usuário, setor e atendimento aberto do almoxarife; 401 token inválido/expirado |
| POST `/auth/logout` | Autenticado | Sem body | 200 mensagem para descartar token no cliente; 401 |
| POST `/auth/refresh` | Access token ainda válido | Sem body | 200 novo access token; 401 token expirado/inválido ou usuário inativo |

Logout é stateless: não existe blacklist nem refresh token persistido. Refresh aceita somente o access token atual ainda não expirado, revalida o usuário no banco e emite outro access token com a duração configurada.

## Usuários

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/usuarios` | Autenticado | `page`, `limit`, `apenas_ativos` (padrão `true`) | 200 lista sem `senha_hash`; 400, 401 |
| GET `/usuarios/{usuario_id}` | Autenticado | — | 200 usuário sem hash; 400, 401, 404 |
| POST `/usuarios` | ADMIN | `nome`, `login`, `senha` (mín. 6), `perfil`, `setor_id?` | 201 usuário sem hash; 400, 401, 403, 404 setor inválido, 409 login duplicado |
| PUT `/usuarios/{usuario_id}` | ADMIN | `nome?`, `login?`, `perfil?`, `setor_id?`, `ativo?`, `senha?` | 200 usuário sem hash; 400, 401, 403, 404, 409 login duplicado ou tentativa de auto-rebaixamento/desativação |
| DELETE `/usuarios/{usuario_id}` | ADMIN | — | 200 usuário desativado logicamente; 401, 403, 404, 409 auto-desativação |

## Setores

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/setores` | Autenticado | `page`, `limit`, `apenas_ativos` | 200 lista; 400, 401 |
| GET `/setores/{setor_id}` | Autenticado | — | 200 setor; 400, 401, 404 |
| POST `/setores` | ADMIN, GESTOR | `nome`, `codigo` | 201; 400, 401, 403, 409 duplicado |
| PUT `/setores/{setor_id}` | ADMIN, GESTOR | `nome?`, `codigo?`, `ativo?` | 200; 400, 401, 403, 404, 409 duplicado |
| DELETE `/setores/{setor_id}` | ADMIN, GESTOR | — | 200 desativação lógica; 401, 403, 404 |

## Materiais

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/materiais` | Autenticado | `page`, `limit`, `busca` (código/descrição), `categoria_id`, `ativo` | 200 lista; 400, 401 |
| GET `/materiais/{material_id}` | Autenticado | — | 200 material; 400, 401, 404 |
| POST `/materiais` | ADMIN, GESTOR | `codigo`, `descricao`, `categoria_id`, `unidade_medida_id`, `especificacao?`, `qr_code?`, `peso_unitario_g?` | 201; 400, 401, 403, 409 duplicado |
| PUT `/materiais/{material_id}` | ADMIN, GESTOR | Campos de POST opcionais, `ativo?`; `qr_code: null` e `peso_unitario_g: null` limpam os campos | 200; 400, 401, 403, 404, 409 duplicado |
| DELETE `/materiais/{material_id}` | ADMIN, GESTOR | — | 200 desativação lógica; 401, 403, 404 |
| GET `/materiais/{material_id}/movimentacoes` | ADMIN, GESTOR, ALMOXARIFE | `page`, `limit`, `usuario_id`, `setor_id`, `requisicao_id`, `tipo`, `data_de`, `data_ate` | 200 envelope paginado da view; 400, 401, 403, 404 |

`qr_code` identifica o material escaneado na devolução. `peso_unitario_g` é o peso de uma unidade em gramas; materiais sem peso cadastrado não podem gerar devoluções.

## Categorias e unidades

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/categorias` | Autenticado | `page`, `limit`, `busca`, `ativo` | 200 lista; 400, 401 |
| GET `/categorias/{categoria_id}` | Autenticado | — | 200; 400, 401, 404 |
| POST `/categorias` | ADMIN, GESTOR | `nome`, `codigo_prefixo`, `descricao?` | 201; 400, 401, 403, 409 duplicado |
| PUT `/categorias/{categoria_id}` | ADMIN, GESTOR | `nome?`, `codigo_prefixo?`, `descricao?`, `ativo?` | 200; 400, 401, 403, 404, 409 duplicado |
| DELETE `/categorias/{categoria_id}` | ADMIN, GESTOR | — | 200 desativação lógica; 401, 403, 404 |
| GET `/unidades-medida` | Autenticado | `page`, `limit`, `apenas_ativos` | 200 lista; 400, 401 |
| GET `/unidades-medida/{unidade_id}` | Autenticado | — | 200; 400, 401, 404 |
| POST `/unidades-medida` | ADMIN, GESTOR | `nome`, `sigla?` | 201; 400, 401, 403, 409 nome duplicado |
| PUT `/unidades-medida/{unidade_id}` | ADMIN, GESTOR | `nome?`, `sigla?`, `ativo?` | 200; 400, 401, 403, 404, 409 nome duplicado |
| DELETE `/unidades-medida/{unidade_id}` | ADMIN, GESTOR | — | 204 desativação lógica; 401, 403, 404 |

## Localizações

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/localizacoes` | Autenticado | `page`, `limit`, `busca` (código/descrição/corredor/estante), `ativo`, `corredor` | 200 `{dados,total,page,limit}`; 400, 401 |
| GET `/localizacoes/{localizacao_id}` | Autenticado | — | 200; 400, 401, 404 |
| POST `/localizacoes` | ADMIN, ALMOXARIFE | `codigo`, `descricao?`, `corredor?`, `estante?`, `prateleira?`, `posicao?` | 201; 400, 401, 403, 409 código duplicado |
| PUT `/localizacoes/{localizacao_id}` | ADMIN, ALMOXARIFE | Mesmos campos opcionais e `ativo?` | 200; 400, 401, 403, 404, 409 código duplicado |
| DELETE `/localizacoes/{localizacao_id}` | ADMIN, ALMOXARIFE | — | 200 desativação lógica; 401, 403, 404, 409 se houver estoque vinculado |

## Estoque

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/estoque` | Autenticado | `page`, `limit`, `busca`, `categoria_id`, `situacao`, `localizacao_id` | 200 `{dados,total,page,limit}`; 400 situação/filtros inválidos, 401 |
| GET `/estoque/{estoque_id}` | Autenticado | — | 200 detalhe completo; 400, 401, 404 |
| GET `/estoque/material/{material_id}` | Autenticado | — | 200 detalhe; 400, 401, 404 material ou saldo ausente |
| POST `/estoque` | ADMIN, ALMOXARIFE | `material_id`, `estoque_minimo`, `estoque_maximo?`, `localizacao_id?`, `lote?`, `quantidade_inicial?` | 201; 400, 401, 403, 404 material/localização, 409 registro existente |
| PUT `/estoque/{estoque_id}` | ADMIN, ALMOXARIFE | `estoque_minimo?`, `estoque_maximo?`, `localizacao_id?`, `lote?` | 200 detalhe; 400, 401, 403, 404, 409 limites inválidos. `quantidade_atual` retorna 400: saldo só muda por movimentação |
| DELETE `/estoque/{estoque_id}` | ADMIN | — | 200 exclusão física somente com saldo zero; 401, 403, 404, 409 saldo diferente de zero |

Valores de `situacao`: `NORMAL`, `ESTOQUE_BAIXO`, `SEM_ESTOQUE`. A criação com `quantidade_inicial > 0` grava `ENTRADA` na mesma transação. Nenhuma rota de cadastro altera saldo diretamente.

## Requisições

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/requisicoes` | SOLICITANTE, ALMOXARIFE, GESTOR, ADMIN | `page`, `limit`, `status`, `setor_id`, `usuario_solicitante_id`, `numero`, `data_de`, `data_ate` | 200 `{dados,total,page,limit}`; 400, 401, 403 |
| GET `/requisicoes/pendentes` | SOLICITANTE, ALMOXARIFE, GESTOR, ADMIN | `page`, `limit`, `todos` (ALMOXARIFE) | 200 FIFO da view; ALMOXARIFE sem atendimento recebe 409; 400, 401, 403 |
| GET `/requisicoes/{requisicao_id}` | SOLICITANTE, ALMOXARIFE, GESTOR, ADMIN | — | 200 cabeçalho e itens; 400, 401, 403 SOLICITANTE alheio, 404 |
| POST `/requisicoes` | SOLICITANTE, ADMIN | `setor_id?`, `observacao?`, `itens: [{material_id, quantidade_solicitada, observacao?}]` | 201 completa; 400 dados/repetição, 401, 403, 404 setor/material, 409 conflito de número após 3 tentativas |
| PUT `/requisicoes/{requisicao_id}` | SOLICITANTE dono, ADMIN | `observacao` | 200; 400, 401, 403, 404, 409 estado inválido |
| PATCH `/requisicoes/{requisicao_id}/cancelar` | SOLICITANTE dono, ALMOXARIFE, ADMIN | Body opcional `motivo?` | 200 cancelada; devolve saldo separado e registra `DEVOLUCAO`; 401, 403, 404, 409 estado inválido |
| PATCH `/requisicoes/{requisicao_id}/iniciar-separacao` | ALMOXARIFE, ADMIN | — | 200 `EM_SEPARACAO`; almoxarife precisa de atendimento do setor; 401, 403, 404, 409 estado/atendimento |
| PATCH `/requisicoes/{requisicao_id}/concluir` | ALMOXARIFE, ADMIN | Body opcional `{ "permitir_parcial": true }` | 200 `ATENDIDA`; 409 estado ou itens pendentes sem permissão parcial; 401, 403, 404 |

A sequência numérica é `REQ-AAAA-NNNNNN`, baseada no ano local do servidor, com retry até três conflitos. O setor informado no body é ignorado para SOLICITANTE e obrigatório para ADMIN.

## Itens de requisição

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/requisicoes/{requisicao_id}/itens` | Autenticado | — | 200 itens ordenados por descrição; 400, 401, 404 |
| POST `/requisicoes/{requisicao_id}/itens` | SOLICITANTE dono, ADMIN | `material_id`, `quantidade_solicitada`, `observacao?` | 201; 400, 401, 403, 404, 409 estado/material duplicado |
| PUT `/requisicoes/{requisicao_id}/itens/{item_id}` | SOLICITANTE dono, ADMIN | `quantidade_solicitada?`, `observacao?` | 200; 400, 401, 403, 404, 409 estado/quantidade |
| DELETE `/requisicoes/{requisicao_id}/itens/{item_id}` | SOLICITANTE dono, ADMIN | — | 200 cancelamento lógico; 401, 403, 404, 409 último item/separação prévia |
| PATCH `/requisicoes/{requisicao_id}/itens/{item_id}/separar` | ALMOXARIFE, ADMIN | `quantidade?`; `Idempotency-Key` obrigatório se quantidade for parcial | 200 saldo e estados; 400, 401, 403, 404, 409 estado/estoque/retry |

A baixa bloqueia requisição, item e estoque com `FOR UPDATE`, escreve movimento `SAIDA` e atualiza status em uma transação. Chaves idempotentes são únicas em `movimentacoes_estoque`.

## Atendimentos

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| POST `/atendimentos/iniciar` | ALMOXARIFE, ADMIN | `setor_id` | 201 aberto; 400, 401, 403, 404 setor, 409 atendimento já aberto |
| GET `/atendimentos/ativo` | Autenticado | — | 200 atendimento e setor; 401, 404 nenhum aberto |
| GET `/atendimentos` | ALMOXARIFE, ADMIN, GESTOR | `page`, `limit`, `usuario_id`, `setor_id`, `status`, `data_inicio_de`, `data_inicio_ate` | 200 envelope paginado; 400, 401, 403 |
| GET `/atendimentos/{atendimento_id}` | ALMOXARIFE, ADMIN, GESTOR | — | 200 com usuário/setor; 400, 401, 403, 404 |
| PATCH `/atendimentos/{atendimento_id}/encerrar` | ALMOXARIFE dono, ADMIN | — | 200 encerrado; 401, 403, 404, 409 estado inválido |

## Movimentações

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/movimentacoes` | ADMIN, GESTOR, ALMOXARIFE | `page`, `limit` (padrão 20, máximo 100), `material_id`, `usuario_id`, `setor_id`, `requisicao_id`, `tipo`, `data_de`, `data_ate` | 200 envelope paginado da view; 400, 401, 403 |
| GET `/movimentacoes/{movimentacao_id}` | ADMIN, GESTOR, ALMOXARIFE | — | 200; 400, 401, 403, 404 |
| POST `/movimentacoes` | ADMIN, ALMOXARIFE | `material_id`, `tipo` (`ENTRADA` ou `AJUSTE`), `quantidade`, `observacao?` | 201; 400, 401, 403, 404, 409 estoque/conflito |

`SAIDA` é exclusiva da separação e `DEVOLUCAO` é exclusiva do fluxo de aceite abaixo. Em `AJUSTE`, `quantidade` é o saldo absoluto e a movimentação grava a diferença absoluta. A data final `data_ate` é inclusiva.

## Devoluções

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| POST `/devolucoes` | SOLICITANTE dono, ADMIN | `requisicao_item_id`, `qr_code`, `peso_total_g`, `Idempotency-Key` | 201 pendente com quantidade calculada; 400 validação, 401, 403, 404 QR/item, 409 item não atendido, peso inválido ou saldo já reservado |
| GET `/devolucoes` | SOLICITANTE, ALMOXARIFE, GESTOR, ADMIN | `page`, `limit` (padrão 20, máximo 100), `status`, `requisicao_id`, `requisicao_item_id`, `usuario_solicitante_id`, `usuario_operador_id`, `data_de`, `data_ate` | 200 `{dados,total,page,limit}`; 400 validação/filtros inválidos, 401, 403 |
| GET `/devolucoes/pendentes` | ALMOXARIFE, ADMIN | `page`, `limit` | 200 fila paginada; 401, 403 |
| GET `/devolucoes/{devolucao_id}` | SOLICITANTE, ALMOXARIFE, GESTOR, ADMIN | — | 200 detalhe; 400 ID inválido, 401, 403 solicitante alheio, 404 |
| PATCH `/devolucoes/{devolucao_id}/aceitar` | ALMOXARIFE, ADMIN | — | 200 crédito em estoque e movimento `DEVOLUCAO`; 401, 403, 404, 409 já analisada/conflito |
| PATCH `/devolucoes/{devolucao_id}/rejeitar` | ALMOXARIFE, ADMIN | `motivo` obrigatório | 200 rejeitada sem crédito; 400, 401, 403, 404, 409 já analisada |

A quantidade é calculada por `peso_total_g / peso_unitario_g`, arredondada a três casas. Devoluções pendentes reservam parte da quantidade atendida para impedir devolução excedente; apenas o aceite, em transação idempotente, credita o estoque. A visibilidade de SOLICITANTE é determinada pelo solicitante da requisição associada ao item, nunca por `usuario_operador_id`; filtros de solicitante e operador enviados por esse perfil são ignorados.

## Auditoria CRUD das rotas

Inventário conferido pelos decorators em `routes/*.py` e pelos routers registrados em `app/main.py`. `GET` indica leitura de coleção e/ou detalhe; `PATCH` aparece separado de `PUT`, pois representa ação parcial ou transição de estado e não foi contado como substituto de CRUD.

| Grupo | CRUD implementado | Métodos/rotas ausentes | Observação |
|---|---|---|---|
| Auth | GET `/auth/me`; POST `/auth/login`, `/auth/login/form`, `/auth/logout`, `/auth/refresh` | PUT e DELETE não se aplicam | Autenticação e sessão, não cadastro CRUD. |
| Usuários | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo; DELETE desativa logicamente. |
| Setores | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo; DELETE desativa logicamente. |
| Categorias | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo; DELETE desativa logicamente. |
| Unidades de medida | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo; DELETE desativa logicamente (204). |
| Materiais | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo; há também GET `/materiais/{material_id}/movimentacoes`. |
| Localizações | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo; DELETE desativa logicamente. |
| Estoque | GET coleção, detalhe e por material; POST; PUT; DELETE | Nenhuma | CRUD completo para o cadastro do saldo; quantidade atual só muda por movimentação. |
| Requisições | GET coleção e detalhe; POST; PUT | DELETE `/requisicoes/{requisicao_id}` | Cancelamento existe via PATCH `/requisicoes/{requisicao_id}/cancelar`; não há exclusão da requisição. |
| Itens de requisição | GET da coleção de itens; POST; PUT; DELETE | GET individual `/requisicoes/{requisicao_id}/itens/{item_id}` | O GET existente lista os itens do pedido; DELETE cancela logicamente o item e tem restrições de estado. |
| Atendimentos | GET coleção, detalhe e ativo; POST `/atendimentos/iniciar` | PUT e DELETE não existem | Fluxo de turno; alteração de estado é PATCH `/atendimentos/{atendimento_id}/encerrar`. Não é um cadastro CRUD genérico. |
| Devoluções | GET coleção, fila pendente e detalhe; POST | PUT e DELETE não se aplicam ao fluxo | SOLICITANTE só consulta devoluções das próprias requisições; a análise ocorre por PATCH aceitar/rejeitar e o crédito exige aceite. Não há edição/exclusão após registro. |
| Movimentações | GET coleção e detalhe; POST | PUT e DELETE | Não implementados intencionalmente: histórico de auditoria deve permanecer imutável. |
| Dashboard e health | GET | POST, PUT e DELETE não se aplicam | Endpoints de consulta/saúde, não recursos CRUD. |
| Projects (demo) | GET coleção e detalhe; POST; PUT; DELETE | Nenhuma | CRUD completo em memória; recurso demonstrativo. |
| Orders (demo) | GET coleção e detalhe; POST | PUT `/orders/{order_id}` e DELETE `/orders/{order_id}` | CRUD incompleto; recurso demonstrativo mantido em memória. |

**Lacunas funcionais identificadas:** adicionar GET de detalhe de item de requisição se o cliente precisar consultar um item isoladamente; completar PUT e DELETE de `orders` somente se esse recurso demonstrativo for mantido. A falta de PUT/DELETE em atendimentos e movimentações é coerente com seus fluxos e não foi classificada como falha de CRUD.

## Rotas auxiliares existentes

| Método e caminho | Perfis | Body / filtros | Sucesso e erros principais |
|---|---|---|---|
| GET `/` | Público | — | 200 metadados e grupos da API |
| GET `/health` | Público | — | 200 status |
| GET `/dashboard` | Autenticado | — | 200 resumo demonstrativo |
| GET `/projects` | Autenticado | `page`, `limit`, `status` | 200 lista em memória; 400, 401 |
| GET `/projects/{project_id}` | Autenticado | — | 200; 400, 401, 404 |
| POST `/projects` | ADMIN, GESTOR | `name`, `description`, `status?`, `owner_id` | 201; 400, 401, 403 |
| PUT `/projects/{project_id}` | ADMIN, GESTOR | Campos de criação | 200; 400, 401, 403, 404 |
| DELETE `/projects/{project_id}` | ADMIN | — | 200 remoção do registro demonstrativo em memória; 401, 403, 404 |
| GET `/orders` | Autenticado | `page`, `limit`, `status` | 200 lista em memória; 400, 401 |
| GET `/orders/{order_id}` | Autenticado | — | 200; 400, 401, 404 |
| POST `/orders` | ADMIN, GESTOR | `code`, `customer`, `total`, `status?` | 201; 400, 401, 403 |

`/projects`, `/orders` e `/dashboard` são endpoints demonstrativos em memória, não integram o domínio de estoque. O framework também publica `/docs`, `/redoc`, `/openapi.json` e `/docs/oauth2-redirect`.
