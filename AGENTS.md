# AGENTS.md — Backend Til Marcon (Almoxarifado)

Este arquivo define como agentes de IA (Claude, Copilot, Cursor, etc.) devem atuar ao trabalhar no backend deste repositório. Ele é a fonte de verdade sobre papel, contexto, arquitetura, convenções e regras de segurança. Qualquer código gerado deve seguir estritamente o que está descrito aqui.

Este AGENTS.md cobre **apenas o backend**. O frontend (Next.js/TypeScript) e o app mobile têm suas próprias regras e consomem esta mesma API REST.

---

## 1. Papel do agente

Atue como um **desenvolvedor Full Stack Sênior**, com ampla experiência em arquitetura de software, APIs, segurança, bancos de dados e aplicações web/mobile industriais.

Ao desenvolver e estruturar o backend deste projeto, priorize, nesta ordem de importância:

1. Segurança
2. Consistência de dados (integridade do estoque é crítica — divergências de quantidade não podem passar despercebidas)
3. Escalabilidade
4. Eficiência / desempenho
5. Boas práticas de engenharia

Isso vale **mesmo que a implementação resultante seja mais complexa** do que uma alternativa rápida e simplificada. Nunca simplifique regras de segurança, validação, transações ou controle de concorrência em nome de "código mais enxuto" — este sistema movimenta estoque físico real de uma metalúrgica.

---

## 2. Contexto do projeto

**Cliente:** Til Marcon — metalúrgica desde 1988, ERP atual TOTVS (Estoque/Custos). Projeto desenvolvido para o Desafio de Ideias SENAI 2026.

**Problema que o sistema resolve:** o fluxo de requisição de materiais no almoxarifado é manual e em papel — seleção repetida de setor, impressão de lista, anotação manual de quantidades retiradas (com risco de divergência), redigitação no sistema ao voltar do galpão. Etiquetas com QR Code já existem nos produtos, mas não são usadas no processo. Não há rastreamento em tempo real do que está "em trânsito" com os operadores.

**Solução — dois fluxos principais:**

1. **Requisição (saída do almoxarifado):**
   - Setor selecionado **uma única vez por turno**, não a cada requisição.
   - Requisição acessada via **QR Code** no celular/tablet corporativo, sem papel.
   - Confirmação da separação gera **débito automático no estoque**, sem redigitação.
   - Sistema precisa tratar e registrar **divergências** entre quantidade solicitada e quantidade efetivamente entregue.
   - **Histórico completo** de movimentações (quem, quando, quanto, de qual setor).

2. **Devolução (entrada no depósito, fisicamente separado do almoxarifado):**
   - Almoxarifado só entrega fechado (ex.: caixa de 20 parafusos); operador devolve a sobra não utilizada.
   - Operador escaneia o **QR Code** do item numa esteira de devolução.
   - Item é pesado em **balança de precisão**; o sistema calcula a quantidade devolvida (`peso_total ÷ peso_unitário_do_item`).
   - Gera **crédito automático no estoque**, condicionado ao aceite do almoxarife antes de confirmar.

**Banco de dados:** já existe (MySQL/MariaDB) — o backend deve se integrar ao schema existente, não assumir banco vazio. Migrations devem ser feitas com cautela sobre tabelas/dados pré-existentes.

**Frontend:** quase pronto (Next.js/TypeScript, consumindo esta API). App mobile/tablet consome a mesma API REST, sem endpoints exclusivos.

---

## 3. Stack de backend

- **API:** FastAPI
- **Banco de dados:** MySQL / MariaDB (já existente — ver seção 2)
- **ORM:** SQLAlchemy 2.0 (estilo assíncrono)
- **Migrations:** Alembic (com atenção a schema pré-existente)
- **Autenticação:** JWT
- **Arquitetura inicial:** monólito modular, organizado por domínio
- **Comunicação:** API REST sobre HTTPS
- **Containers:** Docker

---

## 4. Dependências principais

Use exclusivamente (ou prioritariamente) as bibliotecas abaixo. Não adicione dependências apenas por conveniência — toda escolha de tecnologia deve ser justificada por desempenho, segurança, manutenção ou escalabilidade.

```
fastapi[standard]
uvicorn[standard]

pydantic
pydantic-settings
email-validator
python-dotenv

sqlalchemy
alembic
asyncmy

pyjwt
pwdlib[argon2]
cryptography

python-multipart
httpx

redis
celery

structlog

pytest
pytest-asyncio
pytest-cov
factory-boy
faker

ruff
mypy
```

**Uso do Redis:** cache de leitura (ex.: setor ativo do almoxarife na sessão/turno), controle auxiliar de concorrência em operações de débito/crédito de estoque, infraestrutura de filas.

**Uso do Celery:** tarefas assíncronas — notificações ao almoxarife (nova requisição, devolução pendente de aceite), geração de relatórios de histórico, processamento assíncrono de leituras de QR Code/balança quando aplicável.

---

## 5. Estrutura de pastas (obrigatória)

Organize o backend por **domínio**, seguindo exatamente esta estrutura:

```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   ├── database/
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/            # usuários (almoxarifes, operadores, gestores)
│   │   ├── setores/          # setores da fábrica
│   │   ├── itens/            # materiais/itens do almoxarifado (inclui peso unitário, QR Code)
│   │   ├── estoque/          # saldo de estoque, débitos e créditos
│   │   ├── requisicoes/      # fluxo de saída (requisição → separação → débito)
│   │   ├── devolucoes/       # fluxo de entrada (QR Code + balança → crédito)
│   │   ├── movimentacoes/    # histórico consolidado de todas as operações
│   │   └── notifications/
│   ├── integrations/         # leitura de QR Code, integração com balança de precisão
│   └── workers/              # tarefas Celery
├── migrations/
├── tests/
├── alembic.ini
├── pyproject.toml
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

### Regra de separação por módulo

Cada módulo dentro de `app/modules/<dominio>/` deve separar claramente:

- `routes` — apenas roteamento HTTP, sem lógica de negócio
- `schemas` — modelos Pydantic de entrada/saída
- `models` — modelos SQLAlchemy (ORM)
- `repositories` — acesso a dados (queries, persistência)
- `services` — regras de negócio
- `exceptions` — exceções específicas do domínio

**Nunca** coloque regra de negócio diretamente nas rotas. As rotas apenas orquestram: recebem request → chamam service → retornam response.

---

## 6. Regras de negócio críticas

Estas regras nascem diretamente do problema real da Til Marcon e devem ser respeitadas por qualquer código gerado:

- **Setor por turno, não por requisição:** o setor do almoxarife deve ser fixado no início do turno (sessão) e reutilizado automaticamente em todas as requisições seguintes daquele turno, sem nova seleção manual.
- **Débito automático e atômico:** a confirmação da separação de uma requisição deve debitar o estoque em uma única transação — nunca deixar estado intermediário onde a requisição está "confirmada" mas o estoque não foi atualizado (ou vice-versa).
- **Divergência é dado de primeira classe:** quando a quantidade separada/entregue difere da quantidade solicitada, isso deve ser registrado explicitamente (não apenas sobrescrito), pois alimenta indicadores de gestão.
- **Cálculo de devolução por peso:** a quantidade devolvida é derivada (`peso_lido ÷ peso_unitário_do_item`), nunca digitada manualmente pelo operador. O `peso_unitário` de cada item é um dado de cadastro sensível a erros — validar consistência.
- **Crédito de devolução exige aceite do almoxarife:** o crédito no estoque só é efetivado após confirmação humana, nunca automaticamente a partir da leitura da balança.
- **Rastreamento "em trânsito":** enquanto uma requisição foi separada mas ainda não foi confirmada/devolvida, o sistema deve saber que aquela quantidade está fora do almoxarifado e não disponível, mas também não perdida.
- **Concorrência no estoque:** múltiplos almoxarifes/operadores podem interagir com o mesmo item simultaneamente — usar transações e lock (otimista ou pessimista) para evitar débitos/créditos inconsistentes.

---

## 7. Segurança e qualidade (checklist obrigatório)

Todo código gerado para este backend deve implementar ou respeitar:

- [ ] JWT com **access token** e **refresh token**
- [ ] Hash de senhas com **Argon2id** (via `pwdlib[argon2]`)
- [ ] Controle de autorização e permissões por papel (almoxarife, operador de setor, gestor)
- [ ] Validação de entrada/saída com **Pydantic**
- [ ] CORS configurado corretamente (sem `*` em produção)
- [ ] Rate limiting quando necessário (ex.: login, endpoints sensíveis)
- [ ] Proteção contra brute force (ex.: bloqueio/backoff em tentativas de login)
- [ ] Logs estruturados e auditoria (via `structlog`) — essencial para o histórico de movimentações
- [ ] Variáveis sensíveis **fora do repositório** (usar `.env`, nunca commitar segredos; manter `.env.example` atualizado)
- [ ] Transações e controle de concorrência em toda operação que altera saldo de estoque
- [ ] Prevenção explícita de débito/crédito duplicado (idempotência em confirmações de requisição/devolução)
- [ ] Testes unitários, de integração e de API (`pytest`, `pytest-asyncio`, `pytest-cov`, `factory-boy`, `faker`)
- [ ] `ruff` e `mypy` limpos, e `pytest` passando, antes de considerar qualquer entrega concluída

---

## 8. Restrições explícitas

- **Não** utilizar microserviços nesta fase. Manter monólito modular, mas preparado para futura separação de serviços (baixo acoplamento entre módulos, contratos claros entre camadas).
- **Não** adicionar bibliotecas fora da lista da seção 4 sem justificativa técnica explícita.
- **Não** implementar regra de negócio em `routes`, `schemas` ou `models`.
- **Não** expor segredos, chaves ou credenciais em código, testes ou exemplos.
- **Não** assumir que o banco de dados está vazio — o MySQL/MariaDB já existe; migrations devem considerar dados e schema pré-existentes.
- **Não** efetivar crédito de devolução sem passo explícito de aceite do almoxarife.

---

## 9. Fluxo de trabalho esperado do agente

1. Antes de gerar código, identificar a qual módulo de domínio a tarefa pertence (seção 5).
2. Seguir a separação routes → schemas → models → repositories → services → exceptions.
3. Escrever (ou atualizar) migrations via Alembic para qualquer mudança de schema, considerando o banco já existente.
4. Escrever testes cobrindo o comportamento novo/alterado, incluindo casos de divergência e concorrência quando aplicável.
5. Rodar mentalmente (ou via instrução) `ruff`, `mypy` e `pytest` como critério de "pronto".
6. Documentar decisões de arquitetura relevantes no próprio código (docstrings) quando a lógica não for óbvia — especialmente regras da seção 6.

---

## 10. Definição de "pronto" (Definition of Done)

Uma tarefa de backend só é considerada concluída quando:

- O código está no módulo correto, respeitando a separação de camadas.
- Regras de segurança da seção 7 aplicáveis à tarefa foram implementadas.
- As regras de negócio críticas da seção 6 relevantes à tarefa foram respeitadas.
- Existem testes cobrindo o caso feliz e pelo menos um caso de erro/borda (incluindo divergência de quantidade ou concorrência, quando aplicável).
- Não há segredos hardcoded.
- `ruff`, `mypy` e `pytest` passam sem erros.
