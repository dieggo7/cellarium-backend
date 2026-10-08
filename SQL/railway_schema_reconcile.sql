-- Consolidated, idempotent SQL equivalent for Alembic revisions dated 2026-09-30 onward.
-- The base tables (categorias, unidades_medida, localizacoes, setores, usuarios,
-- materiais, estoque, requisicoes, requisicao_itens and movimentacoes_estoque)
-- must already exist. This file is for review/manual application; it does not run Alembic.
USE til_marcon_almoxarifado;

-- 20260930_expand_views_and_indexes: add nullable idempotency key.
SET @has_column = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'movimentacoes_estoque' AND column_name = 'idempotency_key');
SET @ddl = IF(@has_column > 0, 'SELECT 1',
  'ALTER TABLE movimentacoes_estoque ADD COLUMN idempotency_key VARCHAR(128) NULL');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

-- 20260930_expand_views_and_indexes: add optional QR code and make an existing one nullable.
SET @has_column = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'materiais' AND column_name = 'qr_code');
SET @ddl = IF(@has_column > 0, 'SELECT 1',
  'ALTER TABLE materiais ADD COLUMN qr_code CHAR(36) NULL');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;
SET @qr_not_nullable = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'materiais' AND column_name = 'qr_code' AND is_nullable = 'NO');
SET @ddl = IF(@qr_not_nullable = 0, 'SELECT 1',
  'ALTER TABLE materiais MODIFY qr_code CHAR(36) NULL');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

-- 20260930_create_devolucoes: optional unit weight.
SET @has_column = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'materiais' AND column_name = 'peso_unitario_g');
SET @ddl = IF(@has_column > 0, 'SELECT 1',
  'ALTER TABLE materiais ADD COLUMN peso_unitario_g DECIMAL(12,6) NULL');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

-- 20260930 unique constraints. Existing equivalent single-column unique indexes also satisfy each check.
SET @has_unique = (SELECT COUNT(DISTINCT s.index_name) FROM information_schema.statistics s
  WHERE s.table_schema = DATABASE() AND s.table_name = 'movimentacoes_estoque'
    AND s.non_unique = 0 AND s.column_name = 'idempotency_key' AND s.seq_in_index = 1
    AND (SELECT COUNT(*) FROM information_schema.statistics x WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)=1);
SET @ddl = IF(@has_unique > 0, 'SELECT 1',
  'ALTER TABLE movimentacoes_estoque ADD CONSTRAINT uq_mov_idempotency_key UNIQUE (idempotency_key)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_unique = (SELECT COUNT(DISTINCT s.index_name) FROM information_schema.statistics s
  WHERE s.table_schema = DATABASE() AND s.table_name = 'materiais'
    AND s.non_unique = 0 AND s.column_name = 'qr_code' AND s.seq_in_index = 1
    AND (SELECT COUNT(*) FROM information_schema.statistics x WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)=1);
SET @ddl = IF(@has_unique > 0, 'SELECT 1',
  'ALTER TABLE materiais ADD CONSTRAINT uq_materiais_qrcode UNIQUE (qr_code)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_unique = (SELECT COUNT(DISTINCT s.index_name) FROM information_schema.statistics s
  WHERE s.table_schema = DATABASE() AND s.table_name = 'estoque'
    AND s.non_unique = 0 AND s.column_name = 'material_id' AND s.seq_in_index = 1
    AND (SELECT COUNT(*) FROM information_schema.statistics x WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)=1);
SET @ddl = IF(@has_unique > 0, 'SELECT 1',
  'ALTER TABLE estoque ADD CONSTRAINT uq_estoque_material UNIQUE (material_id)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_unique = (SELECT COUNT(DISTINCT s.index_name) FROM information_schema.statistics s
  WHERE s.table_schema = DATABASE() AND s.table_name = 'requisicoes'
    AND s.non_unique = 0 AND s.column_name = 'numero' AND s.seq_in_index = 1
    AND (SELECT COUNT(*) FROM information_schema.statistics x WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)=1);
SET @ddl = IF(@has_unique > 0, 'SELECT 1',
  'ALTER TABLE requisicoes ADD CONSTRAINT uq_requisicoes_numero UNIQUE (numero)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_unique = (SELECT COUNT(DISTINCT s.index_name) FROM information_schema.statistics s
  WHERE s.table_schema = DATABASE() AND s.table_name = 'localizacoes'
    AND s.non_unique = 0 AND s.column_name = 'codigo' AND s.seq_in_index = 1
    AND (SELECT COUNT(*) FROM information_schema.statistics x WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)=1);
SET @ddl = IF(@has_unique > 0, 'SELECT 1',
  'ALTER TABLE localizacoes ADD CONSTRAINT uq_localizacoes_codigo UNIQUE (codigo)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_unique = (SELECT COUNT(DISTINCT s.index_name) FROM information_schema.statistics s
  WHERE s.table_schema = DATABASE() AND s.table_name = 'usuarios'
    AND s.non_unique = 0 AND s.column_name = 'login' AND s.seq_in_index = 1
    AND (SELECT COUNT(*) FROM information_schema.statistics x WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)=1);
SET @ddl = IF(@has_unique > 0, 'SELECT 1',
  'ALTER TABLE usuarios ADD CONSTRAINT uq_usuarios_login UNIQUE (login)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

-- 20260930 indexes, guarded by ordered columns in information_schema.
SET @has_index = (SELECT COUNT(*) FROM information_schema.statistics s
  WHERE s.table_schema=DATABASE() AND s.table_name='movimentacoes_estoque' AND s.seq_in_index=1 AND s.column_name='material_id'
    AND (SELECT GROUP_CONCAT(x.column_name ORDER BY x.seq_in_index SEPARATOR ',') FROM information_schema.statistics x
      WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)='material_id,created_at');
SET @ddl = IF(@has_index > 0, 'SELECT 1', 'CREATE INDEX idx_mov_material_created ON movimentacoes_estoque (material_id, created_at)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_index = (SELECT COUNT(*) FROM information_schema.statistics s
  WHERE s.table_schema=DATABASE() AND s.table_name='requisicoes' AND s.seq_in_index=1 AND s.column_name='status'
    AND (SELECT GROUP_CONCAT(x.column_name ORDER BY x.seq_in_index SEPARATOR ',') FROM information_schema.statistics x
      WHERE x.table_schema=s.table_schema AND x.table_name=s.table_name AND x.index_name=s.index_name)='status,setor_id');
SET @ddl = IF(@has_index > 0, 'SELECT 1', 'CREATE INDEX idx_requisicoes_status_setor ON requisicoes (status, setor_id)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_index = (SELECT COUNT(*) FROM information_schema.statistics s
  WHERE s.table_schema=DATABASE() AND s.table_name='requisicao_itens' AND s.seq_in_index=1 AND s.column_name='requisicao_id');
SET @ddl = IF(@has_index > 0, 'SELECT 1', 'CREATE INDEX idx_requisicao_itens_requisicao ON requisicao_itens (requisicao_id)');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

-- 20260930_create_devolucoes. The migration creates this table only when absent.
CREATE TABLE IF NOT EXISTS devolucoes (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    requisicao_item_id INT UNSIGNED NOT NULL,
    usuario_operador_id INT UNSIGNED NOT NULL,
    usuario_analise_id INT UNSIGNED NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    peso_total_g DECIMAL(12,3) NOT NULL,
    peso_unitario_g DECIMAL(12,6) NOT NULL,
    quantidade_calculada DECIMAL(12,3) NOT NULL,
    status ENUM('PENDENTE','ACEITA','REJEITADA') NOT NULL DEFAULT 'PENDENTE',
    observacao VARCHAR(500) NULL,
    observacao_analise VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    analisada_at DATETIME NULL,
    CONSTRAINT uq_devolucoes_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT fk_devolucoes_item FOREIGN KEY (requisicao_item_id) REFERENCES requisicao_itens(id),
    CONSTRAINT fk_devolucoes_operador FOREIGN KEY (usuario_operador_id) REFERENCES usuarios(id),
    CONSTRAINT fk_devolucoes_analise FOREIGN KEY (usuario_analise_id) REFERENCES usuarios(id),
    CONSTRAINT chk_devolucoes_peso_positivo CHECK (peso_total_g > 0),
    CONSTRAINT chk_devolucoes_unidade_positiva CHECK (peso_unitario_g > 0),
    CONSTRAINT chk_devolucoes_quantidade_positiva CHECK (quantidade_calculada > 0),
    INDEX idx_devolucoes_status_created (status, created_at),
    INDEX idx_devolucoes_item (requisicao_item_id)
) ENGINE=InnoDB;

-- 20261006_live_requester_tabs: tables and indexes.
CREATE TABLE IF NOT EXISTS estoque_setor (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    setor_id INT UNSIGNED NOT NULL,
    material_id INT UNSIGNED NOT NULL,
    quantidade_atual DECIMAL(12,3) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_estoque_setor_material UNIQUE (setor_id, material_id),
    CONSTRAINT fk_estoque_setor_setor FOREIGN KEY (setor_id) REFERENCES setores(id),
    CONSTRAINT fk_estoque_setor_material FOREIGN KEY (material_id) REFERENCES materiais(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimentacoes_estoque_setor (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    setor_id INT UNSIGNED NOT NULL,
    material_id INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NULL,
    requisicao_id INT UNSIGNED NULL,
    tipo VARCHAR(30) NOT NULL,
    quantidade DECIMAL(12,3) NOT NULL,
    saldo_anterior DECIMAL(12,3) NOT NULL,
    saldo_posterior DECIMAL(12,3) NOT NULL,
    idempotency_key VARCHAR(160) NOT NULL,
    observacao VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_movimentacoes_estoque_setor_idempotency (idempotency_key),
    CONSTRAINT fk_mov_setor_setor FOREIGN KEY (setor_id) REFERENCES setores(id),
    CONSTRAINT fk_mov_setor_material FOREIGN KEY (material_id) REFERENCES materiais(id),
    CONSTRAINT fk_mov_setor_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_mov_setor_requisicao FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS mensagens_requisicao (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    requisicao_id INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NOT NULL,
    texto TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensagens_requisicao FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id),
    CONSTRAINT fk_mensagens_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX ix_mensagens_requisicao_requisicao_id (requisicao_id),
    INDEX ix_mensagens_requisicao_created_at (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notificacoes (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT UNSIGNED NOT NULL,
    requisicao_id INT UNSIGNED NULL,
    event_key VARCHAR(160) NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    mensagem TEXT NOT NULL,
    lida TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_notificacao_usuario_evento UNIQUE (usuario_id, event_key),
    CONSTRAINT fk_notificacoes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_notificacoes_requisicao FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id)
) ENGINE=InnoDB;

-- 20261006_live_requester_tabs data backfill: opening balances from fulfilled requests,
-- net of accepted returns. A temporary candidate set plus a transaction makes reruns safe.
DROP TEMPORARY TABLE IF EXISTS tmp_estoque_setor_backfill;
CREATE TEMPORARY TABLE tmp_estoque_setor_backfill AS
SELECT r.setor_id, i.material_id,
       SUM(i.quantidade_atendida - COALESCE(d.quantidade_devolvida, 0)) AS quantidade,
       MIN(r.usuario_separador_id) AS usuario_id,
       MIN(r.id) AS requisicao_id
FROM requisicoes r
JOIN requisicao_itens i ON i.requisicao_id = r.id
LEFT JOIN (
    SELECT requisicao_item_id, SUM(quantidade_calculada) AS quantidade_devolvida
    FROM devolucoes WHERE status = 'ACEITA' GROUP BY requisicao_item_id
) d ON d.requisicao_item_id = i.id
WHERE r.status = 'ATENDIDA'
  AND i.quantidade_atendida > 0
  AND NOT EXISTS (
      SELECT 1 FROM estoque_setor es
      WHERE es.setor_id = r.setor_id AND es.material_id = i.material_id
  )
GROUP BY r.setor_id, i.material_id
HAVING SUM(i.quantidade_atendida - COALESCE(d.quantidade_devolvida, 0)) > 0;

START TRANSACTION;
INSERT INTO estoque_setor (setor_id, material_id, quantidade_atual, updated_at)
SELECT setor_id, material_id, quantidade, CURRENT_TIMESTAMP
FROM tmp_estoque_setor_backfill;

INSERT INTO movimentacoes_estoque_setor
    (setor_id, material_id, usuario_id, requisicao_id, tipo, quantidade,
     saldo_anterior, saldo_posterior, idempotency_key, observacao, created_at)
SELECT b.setor_id, b.material_id, b.usuario_id, b.requisicao_id,
       'SALDO_INICIAL_HISTORICO', b.quantidade, 0, b.quantidade,
       CONCAT('historico:', b.setor_id, ':', b.material_id),
       'Saldo recomposto a partir de requisições atendidas antes da ativação do estoque por setor',
       CURRENT_TIMESTAMP
FROM tmp_estoque_setor_backfill b
WHERE NOT EXISTS (
    SELECT 1 FROM movimentacoes_estoque_setor m
    WHERE m.idempotency_key = CONCAT('historico:', b.setor_id, ':', b.material_id)
);
COMMIT;
DROP TEMPORARY TABLE IF EXISTS tmp_estoque_setor_backfill;

-- 20261006_history_request_details: latest history view definition.
CREATE OR REPLACE VIEW vw_estoque_atual AS
SELECT m.codigo, m.descricao AS material, c.nome AS categoria, um.nome AS unidade,
       e.quantidade_atual AS estoque_atual, e.estoque_minimo,
       CASE WHEN e.quantidade_atual <= 0 THEN 'SEM_ESTOQUE'
            WHEN e.quantidade_atual <= e.estoque_minimo THEN 'ESTOQUE_BAIXO'
            ELSE 'NORMAL' END AS situacao,
       e.id AS estoque_id, m.id AS material_id, m.categoria_id, e.estoque_maximo,
       e.lote, e.localizacao_id,
       COALESCE(NULLIF(l.descricao, ''),
                NULLIF(CONCAT_WS(' - ', l.corredor, l.estante, l.prateleira, l.posicao), ''),
                l.codigo) AS localizacao_descricao
FROM materiais m
JOIN categorias c ON c.id = m.categoria_id
JOIN unidades_medida um ON um.id = m.unidade_medida_id
JOIN estoque e ON e.material_id = m.id
LEFT JOIN localizacoes l ON l.id = e.localizacao_id
WHERE m.ativo = 1;

CREATE OR REPLACE VIEW vw_requisicoes_pendentes AS
SELECT r.numero, s.nome AS setor, r.data_solicitacao AS data, r.status,
       COUNT(ri.id) AS quantidade_itens, r.id AS requisicao_id, r.setor_id,
       r.usuario_solicitante_id, r.usuario_separador_id, r.data_inicio_separacao
FROM requisicoes r
JOIN setores s ON s.id = r.setor_id
LEFT JOIN requisicao_itens ri ON ri.requisicao_id = r.id
WHERE r.status IN ('PENDENTE','EM_SEPARACAO','SEPARADA')
GROUP BY r.id, r.numero, s.nome, r.data_solicitacao, r.status,
         r.setor_id, r.usuario_solicitante_id, r.usuario_separador_id,
         r.data_inicio_separacao;

CREATE OR REPLACE VIEW vw_historico_movimentacoes AS
SELECT me.created_at AS data, u.nome AS usuario, s.nome AS setor,
       m.descricao AS material, um.sigla AS unidade, me.tipo, me.quantidade,
       me.estoque_anterior, me.estoque_posterior, me.id, me.material_id,
       me.usuario_id, me.requisicao_id, r.setor_id, r.numero AS requisicao_numero,
       r.data_solicitacao AS requisicao_data, solicitante.nome AS solicitante,
       separador.nome AS separador
FROM movimentacoes_estoque me
JOIN usuarios u ON u.id = me.usuario_id
JOIN materiais m ON m.id = me.material_id
JOIN unidades_medida um ON um.id = m.unidade_medida_id
LEFT JOIN requisicoes r ON r.id = me.requisicao_id
LEFT JOIN setores s ON s.id = r.setor_id
LEFT JOIN usuarios solicitante ON solicitante.id = r.usuario_solicitante_id
LEFT JOIN usuarios separador ON separador.id = r.usuario_separador_id;

-- 20261007_close_service_orders: columns absent from the local model/database comparison.
SET @has_column = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'requisicoes' AND column_name = 'os_encerrada_at');
SET @ddl = IF(@has_column > 0, 'SELECT 1',
  'ALTER TABLE requisicoes ADD COLUMN os_encerrada_at DATETIME NULL AFTER data_conclusao');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;

SET @has_column = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'requisicao_itens' AND column_name = 'quantidade_sobrante');
SET @ddl = IF(@has_column > 0, 'SELECT 1',
  'ALTER TABLE requisicao_itens ADD COLUMN quantidade_sobrante DECIMAL(12,3) NULL AFTER quantidade_atendida');
PREPARE migration_stmt FROM @ddl; EXECUTE migration_stmt; DEALLOCATE PREPARE migration_stmt;
