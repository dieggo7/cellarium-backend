# API Til Marcon — Almoxarifado

Backend REST para digitalizar requisições e movimentações do almoxarifado da Til Marcon. O sistema reduz o retrabalho com papel e redigitação, registra a separação de materiais e mantém o histórico de alterações de estoque.

Projeto do Desafio de Ideias SENAI 2026, integrado ao contexto operacional do ERP TOTVS Estoque/Custos.

## Funcionalidades principais

- Atendimento do almoxarife vinculado a um setor durante o turno.
- Requisições digitais e separação com baixa de estoque transacional.
- Registro de movimentações para auditoria e consulta de histórico.
- Registro de devoluções por QR Code e peso, com crédito somente após aceite do almoxarife.
- Perfis de acesso para administração, almoxarifado, solicitantes e gestores.

## Tecnologias

| Componente | Tecnologia confirmada no repositório |
|---|---|
| API | FastAPI `0.141.1` |
| Servidor ASGI | Uvicorn `0.53.0` |
| Validação e configuração | Pydantic `2.13.5`, pydantic-settings `2.15.0` |
| ORM e migrações | SQLAlchemy síncrono `2.0.54`, Alembic `1.20.0` |
| Driver MySQL | PyMySQL `1.2.3` |
| Autenticação | JWT com PyJWT `2.15.0`; senhas com pwdlib/Argon2id |
| Testes | pytest, pytest-asyncio e httpx |

As versões são as fixadas em `requirements.txt`. A API usa sessões síncronas do SQLAlchemy e conexão `mysql+pymysql`; não usa `asyncmy`.

## Pré-requisitos

- Python: **A CONFIRMAR** versão mínima suportada pelo projeto. O ambiente usado nesta conferência tem Python `3.14.7`.
- MySQL 8 com InnoDB e suporte a `utf8mb4`, conforme o DDL e o banco configurado no projeto. A versão exata do servidor validada é **A CONFIRMAR**.
- Git e acesso ao repositório.

## Instalação e execução local

### 1. Clonar e preparar o ambiente

```powershell
git clone https://github.com/dieggo7/cellarium-backend.git
cd cellarium-backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No macOS/Linux, crie/ative o ambiente com `python3 -m venv .venv` e `source .venv/bin/activate`.

### 2. Criar o banco local

`SQL/DDL.sql` cria o schema `til_marcon_almoxarifado`, tabelas, índices e views. Para um banco local novo, execute:

```powershell
Get-Content -Raw SQL/DDL.sql | mysql -u root -p
```

Opcionalmente, carregue dados de demonstração:

```powershell
Get-Content -Raw SQL/DML.sql | mysql -u root -p til_marcon_almoxarifado
```

O DDL é um script de criação inicial, não uma migração incremental segura para reaplicação em um banco existente. Antes de usá-lo em uma base com dados, faça backup e revise a diferença de schema. O projeto também contém revisões em `alembic/versions/`; confira-as e valide a configuração do ambiente antes de aplicar migrações. `Base.metadata.create_all()` na inicialização cria objetos ausentes, mas não atualiza estruturas já existentes.

### 3. Configurar as variáveis de ambiente

Crie `.env` na raiz (por exemplo, copiando `.env.example`) e ajuste os valores. O `.env.example` atual contém valores locais ilustrativos e aponta para outro nome de banco; use o schema `til_marcon_almoxarifado` do DDL.

| Variável | Descrição | Exemplo fictício/local |
|---|---|---|
| `APP_NAME` | Nome exibido pela API | `TilMarcon API` |
| `APP_VERSION` | Versão da aplicação | `0.1.0` |
| `DEBUG` | Modo de depuração | `false` |
| `DATABASE_URL` | URL SQLAlchemy do banco | `mysql+pymysql://usuario_demo:senha_demo@localhost:3306/til_marcon_almoxarifado` |
| `DATABASE_ECHO` | Registra SQL emitido pelo SQLAlchemy | `false` |
| `SECRET_KEY` | Chave de assinatura JWT; mínimo de 32 bytes, não pode conter `change-me` | Gere uma chave aleatória localmente; não use o exemplo do `.env.example` |
| `JWT_ALGORITHM` | Algoritmo aceito pela configuração | `HS256` |
| `JWT_EXPIRE_MINUTES` | Duração do access token | `60` |
| `ALLOWED_HOSTS` | Hosts aceitos pelo middleware | `["localhost", "127.0.0.1"]` |
| `FRONTEND_URL` | URL principal do frontend | `http://localhost:3000` |
| `ALLOWED_ORIGINS` | Origens liberadas no CORS | `["http://localhost:3000"]` |
| `FORCE_HTTPS_REDIRECT` | Ativa redirecionamento HTTPS | `false` |

`ALLOWED_HOSTS`, `FRONTEND_URL`, `ALLOWED_ORIGINS` e `FORCE_HTTPS_REDIRECT` têm valores padrão em `config/settings.py`, embora não estejam listadas no `.env.example`. Use uma chave JWT aleatória fora do repositório e não reutilize credenciais fictícias em produção.

Gere localmente uma chave válida com:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie a saída para `SECRET_KEY` no `.env`; não publique essa chave.

### 4. Preparar a primeira conta e iniciar a API

O `SQL/DML.sql` inclui hashes de exemplo que não permitem login. Crie o primeiro administrador pelo prompt seguro do script:

```powershell
python .\bootstrap_admin.py
```

Depois, inicie o servidor de desenvolvimento:

```powershell
python -m uvicorn app.main:app --reload
```

Base URL local: `http://localhost:8000`.

- Swagger UI: [`/docs`](http://localhost:8000/docs)
- ReDoc: [`/redoc`](http://localhost:8000/redoc)
- Schema OpenAPI: [`/openapi.json`](http://localhost:8000/openapi.json)
- Verificação de saúde: [`/health`](http://localhost:8000/health)

## Estrutura do projeto

```text
.
├── app/main.py                 # Criação da aplicação, middlewares e registro de rotas
├── config/                     # Configurações e variáveis de ambiente
├── core/                       # Segurança e operações compartilhadas de estoque
├── database/                   # Base ORM, engine, sessões e inicialização
├── middlewares/                # CORS, hosts, HTTPS e tratamento de erros
├── models/                     # Modelos SQLAlchemy
├── routes/                     # Endpoints REST por recurso
├── SQL/                        # DDL, dados de demonstração e atualizações SQL
├── alembic/versions/           # Revisões de schema
├── tests/                      # Testes de autenticação, rotas e middlewares
├── API_ROTAS.md                # Referência detalhada de endpoints, perfis e respostas
├── security.md                 # Notas de segurança e bootstrap do primeiro ADMIN
├── requirements.txt            # Dependências diretas com versões fixadas
├── requirements.lock           # Dependências travadas com hashes
└── bootstrap_admin.py          # Criação/preparação interativa da conta ADMIN
```

## Modelo de dados

O schema é `til_marcon_almoxarifado`. As entidades centrais são:

| Tabela | Papel e relações principais |
|---|---|
| `categorias` | Classifica materiais; uma categoria pode ter vários materiais. |
| `unidades_medida` | Unidades de cadastro dos materiais. |
| `localizacoes` | Endereços físicos opcionais associados ao estoque. |
| `setores` | Setores atendidos; referenciados por usuários, requisições e atendimentos. |
| `usuarios` | Contas, perfis e setor padrão opcional; relacionados a requisições, movimentos, devoluções e atendimentos. |
| `materiais` | Catálogo, QR Code opcional e peso unitário para cálculo de devoluções. |
| `estoque` | Saldo e parâmetros por material; um registro por material. |
| `requisicoes` | Cabeçalho, setor, solicitante, separador e estado do atendimento. |
| `requisicao_itens` | Materiais e quantidades solicitadas, separadas e atendidas. |
| `devolucoes` | Peso, quantidade calculada, chave idempotente e análise/decisão do almoxarife. |
| `movimentacoes_estoque` | Registro de auditoria com tipo, quantidade e saldos anterior/posterior. |
| `atendimentos_almoxarifado` | Setor do almoxarife durante o atendimento/turno e seu estado. |

Views de consulta: `vw_estoque_atual`, `vw_requisicoes_pendentes` e `vw_historico_movimentacoes`.

```mermaid
erDiagram
    CATEGORIAS ||--o{ MATERIAIS : classifica
    UNIDADES_MEDIDA ||--o{ MATERIAIS : mede
    MATERIAIS ||--o| ESTOQUE : possui
    LOCALIZACOES ||--o{ ESTOQUE : armazena
    SETORES ||--o{ USUARIOS : associa
    SETORES ||--o{ REQUISICOES : recebe
    USUARIOS ||--o{ REQUISICOES : solicita
    REQUISICOES ||--|{ REQUISICAO_ITENS : contem
    MATERIAIS ||--o{ REQUISICAO_ITENS : requisitado
    REQUISICAO_ITENS ||--o{ DEVOLUCOES : pode_gerar
    MATERIAIS ||--o{ MOVIMENTACOES_ESTOQUE : movimentado
    USUARIOS ||--o{ MOVIMENTACOES_ESTOQUE : registra
    REQUISICOES ||--o{ MOVIMENTACOES_ESTOQUE : referencia
    USUARIOS ||--o{ ATENDIMENTOS_ALMOXARIFADO : inicia
    SETORES ||--o{ ATENDIMENTOS_ALMOXARIFADO : define
```

## Autenticação e perfis

O login retorna um JWT `access_token`, enviado nas rotas protegidas como `Authorization: Bearer <token>`. Novas senhas são armazenadas com Argon2id; hashes bcrypt legados são aceitos e atualizados após login válido.

O logout é stateless: responde para o cliente descartar o token, sem blacklist no servidor. Não existe refresh token separado ou persistido. `POST /auth/refresh` exige o access token atual ainda válido e emite outro access token.

| Perfil | Ações principais |
|---|---|
| `ADMIN` | Administração de usuários e acesso operacional ampliado; pode criar requisições e operar separações/devoluções. |
| `ALMOXARIFE` | Abre atendimento de setor, separa requisições, movimenta estoque, analisa devoluções e consulta histórico. |
| `SOLICITANTE` | Cria e acompanha suas requisições e registra devoluções de itens atendidos das próprias requisições. |
| `GESTOR` | Mantém cadastros de catálogo/setores conforme permissões e consulta requisições, atendimentos e histórico. |

As permissões específicas por rota estão em [`API_ROTAS.md`](API_ROTAS.md).

## Visão geral da API

| Grupo | Prefixo(s) | Descrição |
|---|---|---|
| Autenticação | `/auth` | Login, identidade atual, logout e renovação de access token. |
| Cadastros | `/usuarios`, `/setores`, `/categorias`, `/unidades-medida`, `/materiais`, `/localizacoes` | Usuários, setores e catálogo do almoxarifado. |
| Estoque | `/estoque`, `/movimentacoes` | Consulta de saldo e entradas/ajustes auditados. |
| Requisições | `/requisicoes` | Criação, consulta, separação, cancelamento e conclusão. |
| Atendimentos | `/atendimentos` | Abertura, consulta e encerramento do atendimento por setor. |
| Devoluções | `/devolucoes` | Registro por QR/peso, consulta e aceite/rejeição. |
| Consultas auxiliares | `/dashboard`, `/health`, `/` | Resumo demonstrativo, saúde e metadados da API. |
| Demonstrações | `/orders`, `/projects` | Recursos demonstrativos mantidos em memória. |

A referência completa de métodos, parâmetros, perfis e respostas está em [`API_ROTAS.md`](API_ROTAS.md); a especificação OpenAPI é publicada em `/openapi.json`.

## Fluxos principais

### Requisição e separação

1. O almoxarife abre o turno/setor com `POST /atendimentos/iniciar`.
2. O solicitante cria uma requisição em `POST /requisicoes`.
3. O almoxarife inicia a separação com `PATCH /requisicoes/{id}/iniciar-separacao`.
4. Cada item separado gera uma baixa de estoque e uma movimentação `SAIDA` na mesma transação.
5. O almoxarife conclui a requisição; diferenças entre solicitado e atendido permanecem registradas nas quantidades e estados dos itens.
6. Usuários autorizados consultam o histórico em `GET /movimentacoes`.

Exemplo de login (substitua as credenciais fictícias por uma conta criada no banco):

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"admin_demo","senha":"senha-ficticia-local"}'
```

Exemplo de separação parcial do item fictício `456`, da requisição `123`. A requisição deve estar em separação; para uma separação parcial a chave de idempotência é obrigatória.

```bash
curl -X PATCH http://localhost:8000/requisicoes/123/itens/456/separar \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-separacao-req-123-item-456-01' \
  -d '{"quantidade":"2"}'
```

### Devolução

1. O solicitante registra a leitura com QR Code, peso total e `Idempotency-Key` em `POST /devolucoes`.
2. A API calcula a quantidade e cria a devolução como `PENDENTE`; essa quantidade fica reservada contra devoluções excedentes.
3. O almoxarife consulta a fila e aceita ou rejeita a devolução.
4. Só o aceite gera crédito e movimento `DEVOLUCAO`; rejeição não altera o saldo.

## Regras de negócio importantes

- O saldo atual não pode ser editado pelo cadastro de estoque. Mudanças passam por movimentações; criar estoque com saldo inicial positivo gera `ENTRADA`.
- `SAIDA` é criada pela separação. `DEVOLUCAO` é criada pelo aceite de devolução; o cancelamento de uma requisição com quantidade já separada também registra a reversão correspondente como `DEVOLUCAO`.
- Em `AJUSTE`, `quantidade` representa o saldo final absoluto; a movimentação armazena a diferença em relação ao saldo anterior.
- O número de requisição segue `REQ-AAAA-NNNNNN`; há nova tentativa em caso de colisão.
- `Idempotency-Key` é obrigatória para separação parcial e para registrar devolução. A chave impede que a mesma operação produza mais de uma movimentação/registro.
- Exclusões de cadastros são lógicas (`ativo = 0`) quando aplicável. Um registro de estoque só pode ser removido fisicamente com saldo zero.
- Devolução calcula `peso_total_g / peso_unitario_g`, arredondado para três casas. Material sem peso unitário válido não pode ser devolvido por peso.
- Quantidades de devolução pendentes e aceitas são consideradas na reserva da quantidade atendida. O estoque só recebe crédito quando o almoxarife aceita.
- Erros de validação de request retornam HTTP 400 com `detail` e `erros`; erros de domínio retornam `detail` em português.

## Testes

Execute a suíte com:

```powershell
python -m pytest -q
```

Os testes existentes cobrem autenticação e hashes de senha, autorização por perfil, middlewares, operações de estoque, fluxo de requisições e separação, idempotência, devoluções com aceite/rejeição e filtros/validações das rotas.

Na conferência deste README, `python -m pytest -q` **não passou da coleta**: o ambiente não tem `pwdlib` instalado (`ModuleNotFoundError`). Instale as dependências com `python -m pip install -r requirements.txt` antes de repetir. Não foi possível validar a conexão, a criação do banco ou a execução da API: o comando cliente `mysql` não está instalado/disponível neste ambiente.

## Decisões de projeto e limitações conhecidas

- `movimentacoes_estoque` é histórico de auditoria e não oferece `PUT`/`DELETE`. Atendimentos também não oferecem `PUT`/`DELETE`; suas transições usam ações explícitas.
- `/orders`, `/projects` e `/dashboard` são demonstrativos e mantidos em memória, fora do domínio de estoque.
- Integração automática com TOTVS não está implementada. A próxima fase prevista é importar materiais e exportar baixas.
- Não existe endpoint de consulta individual para `/requisicoes/{id}/itens/{item_id}`; a API lista itens por requisição. `API_ROTAS.md` também registra a ausência de atualização e remoção em `/orders`.
- O schema já contém dados em alguns ambientes: revise `SQL/DDL.sql` e as revisões Alembic antes de aplicar mudanças em uma base existente.

## Equipe e contexto

Desafio de Ideias SENAI 2026 — Til Marcon.

- Equipe: **A PREENCHER**
- Repositório: https://github.com/dieggo7/cellarium-backend
- Frontend: **A PREENCHER**
- Vídeo de demonstração: **A PREENCHER**

## Itens a confirmar ou preencher

- **A CONFIRMAR:** versão mínima de Python suportada pelo projeto e compatibilidade oficialmente validada.
- **A CONFIRMAR:** versão exata de MySQL usada nos ambientes do projeto; a conferência local não tinha cliente MySQL instalado.
- **A PREENCHER:** nomes dos integrantes da equipe.
- **A PREENCHER:** link do frontend.
- **A PREENCHER:** link do vídeo de demonstração.
