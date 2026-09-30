# Segurança da autenticação e das dependências
## Credenciais e senhas
Defina DATABASE_URL e SECRET_KEY por variável de ambiente ou .env local. A aplicação falha na inicialização se estiverem ausentes. Ambos são mascarados na representação das configurações por SecretStr. O arquivo .env está ignorado pelo Git.
Gere SECRET_KEY com python -c "import secrets; print(secrets.token_hex(32))". Guarde a chave em um gerenciador de segredos na implantação. A troca dessa chave invalida os JWTs existentes.
Novas senhas usam Argon2id por pwdlib[argon2]. Hashes bcrypt antigos continuam verificáveis e são migrados para Argon2id no próximo login válido. Senhas antigas com mais de 72 bytes UTF-8 precisam de redefinição, pois o código anterior truncava o valor antes do hash.
JWTs são assinados com HS256 e exigem sub, iat e exp. O token é uma assinatura, não uma forma de criptografar dados: não coloque segredos no payload.
## Dependências e auditoria
requirements.txt contém as dependências diretas. requirements.lock contém também as transitivas, com versões fixas e hashes SHA-256. Atualize a trava sempre que mudar requirements.txt:
sh
uv pip compile requirements.txt --universal --generate-hashes --output-file requirements.lock
python -m pip install --require-hashes --only-binary :all: -r requirements.lock
Execute as verificações abaixo antes de publicar mudanças de autenticação ou dependências:
sh
uvx --from pip-audit==2.10.1 pip-audit --require-hashes -r requirements.lock --progress-spinner off
uvx --from bandit==1.9.4 bandit -r -ll app config core database models routes middlewares alembic
uvx --from semgrep==1.178.0 semgrep scan --config p/python --no-git-ignore --error app config core database models routes middlewares alembic
uvx --from flake8==7.4.1 --with flake8-bugbear==26.9.9 flake8 --select B core/security.py config/settings.py routes/auth.py routes/users.py
O security.py não executa comandos, não monta SQL por concatenação, não desserializa pickle e não usa eval ou exec. As consultas de autenticação usam expressões SQLAlchemy com parâmetros vinculados. Faça nova análise se essas práticas mudarem; scanners e auditorias de pacotes não garantem ausência de falhas.
Na análise de 30/09/2026: pip-audit não encontrou vulnerabilidades conhecidas na trava; Bandit não encontrou achados de severidade média ou alta; Semgrep executou 151 regras Python sem achados; Flake8-bugbear passou nos arquivos de autenticação alterados. Bandit sinalizou token_type="bearer" como senha fixa (B105), um falso positivo por ser o identificador OAuth2 do tipo de token. A varredura Flake8-bugbear no restante do backend ainda apresenta ocorrências anteriores em outras rotas.