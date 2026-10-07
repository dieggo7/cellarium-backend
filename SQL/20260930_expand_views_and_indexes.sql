USE til_marcon_almoxarifado;

-- Report duplicates before adding the unique stock key. The ALTER below fails
-- safely if any are present; reconcile quantities and audit history manually.
SELECT material_id, COUNT(*) AS registros
FROM estoque
GROUP BY material_id
HAVING COUNT(*) > 1;

SET @has_stock_unique = (
    SELECT COUNT(*) FROM information_schema.statistics i
    WHERE table_schema = DATABASE() AND table_name = 'estoque'
      AND column_name = 'material_id' AND seq_in_index = 1 AND non_unique = 0
      AND (SELECT COUNT(*) FROM information_schema.statistics i2
           WHERE i2.table_schema = i.table_schema AND i2.table_name = i.table_name
             AND i2.index_name = i.index_name) = 1
);
SET @ddl = IF(@has_stock_unique > 0, 'SELECT 1',
    'ALTER TABLE estoque ADD CONSTRAINT uq_estoque_material UNIQUE (material_id)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_req_num_unique = (
    SELECT COUNT(*) FROM information_schema.statistics i
    WHERE table_schema = DATABASE() AND table_name = 'requisicoes'
      AND column_name = 'numero' AND seq_in_index = 1 AND non_unique = 0
      AND (SELECT COUNT(*) FROM information_schema.statistics i2
           WHERE i2.table_schema = i.table_schema AND i2.table_name = i.table_name
             AND i2.index_name = i.index_name) = 1
);
SET @ddl = IF(@has_req_num_unique > 0, 'SELECT 1',
    'ALTER TABLE requisicoes ADD CONSTRAINT uq_requisicoes_numero UNIQUE (numero)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_location_unique = (
    SELECT COUNT(*) FROM information_schema.statistics i
    WHERE table_schema = DATABASE() AND table_name = 'localizacoes'
      AND column_name = 'codigo' AND seq_in_index = 1 AND non_unique = 0
      AND (SELECT COUNT(*) FROM information_schema.statistics i2
           WHERE i2.table_schema = i.table_schema AND i2.table_name = i.table_name
             AND i2.index_name = i.index_name) = 1
);
SET @ddl = IF(@has_location_unique > 0, 'SELECT 1',
    'ALTER TABLE localizacoes ADD CONSTRAINT uq_localizacoes_codigo UNIQUE (codigo)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_login_unique = (
    SELECT COUNT(*) FROM information_schema.statistics i
    WHERE table_schema = DATABASE() AND table_name = 'usuarios'
      AND column_name = 'login' AND seq_in_index = 1 AND non_unique = 0
      AND (SELECT COUNT(*) FROM information_schema.statistics i2
           WHERE i2.table_schema = i.table_schema AND i2.table_name = i.table_name
             AND i2.index_name = i.index_name) = 1
);
SET @ddl = IF(@has_login_unique > 0, 'SELECT 1',
    'ALTER TABLE usuarios ADD CONSTRAINT uq_usuarios_login UNIQUE (login)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_idempotency_column = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'movimentacoes_estoque'
      AND column_name = 'idempotency_key'
);
SET @ddl = IF(@has_idempotency_column > 0, 'SELECT 1',
    'ALTER TABLE movimentacoes_estoque ADD COLUMN idempotency_key VARCHAR(128) NULL');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_idempotency_unique = (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'movimentacoes_estoque'
      AND index_name = 'uq_mov_idempotency_key' AND non_unique = 0
);
SET @ddl = IF(@has_idempotency_unique > 0, 'SELECT 1',
    'ALTER TABLE movimentacoes_estoque ADD CONSTRAINT uq_mov_idempotency_key UNIQUE (idempotency_key)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_item_req_index = (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'requisicao_itens'
      AND column_name = 'requisicao_id' AND seq_in_index = 1
);
SET @ddl = IF(@has_item_req_index > 0, 'SELECT 1',
    'CREATE INDEX idx_requisicao_itens_requisicao ON requisicao_itens (requisicao_id)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_req_status_sector_index = (
    SELECT COUNT(*) FROM information_schema.statistics i
    WHERE table_schema = DATABASE() AND table_name = 'requisicoes'
      AND column_name = 'status' AND seq_in_index = 1
      AND EXISTS (SELECT 1 FROM information_schema.statistics i2
                  WHERE i2.table_schema = i.table_schema AND i2.table_name = i.table_name
                    AND i2.index_name = i.index_name AND i2.column_name = 'setor_id'
                    AND i2.seq_in_index = 2)
);
SET @ddl = IF(@has_req_status_sector_index > 0, 'SELECT 1',
    'CREATE INDEX idx_requisicoes_status_setor ON requisicoes (status, setor_id)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @has_mov_material_created_index = (
    SELECT COUNT(*) FROM information_schema.statistics i
    WHERE table_schema = DATABASE() AND table_name = 'movimentacoes_estoque'
      AND column_name = 'material_id' AND seq_in_index = 1
      AND EXISTS (SELECT 1 FROM information_schema.statistics i2
                  WHERE i2.table_schema = i.table_schema AND i2.table_name = i.table_name
                    AND i2.index_name = i.index_name AND i2.column_name = 'created_at'
                    AND i2.seq_in_index = 2)
);
SET @ddl = IF(@has_mov_material_created_index > 0, 'SELECT 1',
    'CREATE INDEX idx_mov_material_created ON movimentacoes_estoque (material_id, created_at)');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

SET @qr_not_nullable = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'materiais'
      AND column_name = 'qr_code' AND is_nullable = 'NO'
);
SET @ddl = IF(@qr_not_nullable = 0, 'SELECT 1',
    'ALTER TABLE materiais MODIFY qr_code CHAR(36) NULL COMMENT ''Identificador legado opcional; não utilizado no fluxo.''');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

CREATE OR REPLACE VIEW vw_estoque_atual AS
SELECT
    m.codigo,
    m.descricao AS material,
    c.nome      AS categoria,
    um.nome     AS unidade,
    e.quantidade_atual AS estoque_atual,
    e.estoque_minimo,
    CASE
        WHEN e.quantidade_atual <= 0 THEN 'SEM_ESTOQUE'
        WHEN e.quantidade_atual <= e.estoque_minimo THEN 'ESTOQUE_BAIXO'
        ELSE 'NORMAL'
    END AS situacao,
    e.id AS estoque_id,
    m.id AS material_id,
    m.categoria_id,
    e.estoque_maximo,
    e.lote,
    e.localizacao_id,
    COALESCE(
        NULLIF(l.descricao, ''),
        NULLIF(CONCAT_WS(' - ', l.corredor, l.estante, l.prateleira, l.posicao), ''),
        l.codigo
    ) AS localizacao_descricao
FROM materiais m
JOIN categorias c       ON c.id = m.categoria_id
JOIN unidades_medida um ON um.id = m.unidade_medida_id
JOIN estoque e          ON e.material_id = m.id
LEFT JOIN localizacoes l ON l.id = e.localizacao_id
WHERE m.ativo = 1;

CREATE OR REPLACE VIEW vw_requisicoes_pendentes AS
SELECT
    r.numero,
    s.nome AS setor,
    r.data_solicitacao AS data,
    r.status,
    COUNT(ri.id) AS quantidade_itens,
    r.id AS requisicao_id,
    r.setor_id,
    r.usuario_solicitante_id,
    r.usuario_separador_id,
    r.data_inicio_separacao
FROM requisicoes r
JOIN setores s ON s.id = r.setor_id
LEFT JOIN requisicao_itens ri ON ri.requisicao_id = r.id
WHERE r.status IN ('PENDENTE','EM_SEPARACAO','SEPARADA')
GROUP BY r.id, r.numero, s.nome, r.data_solicitacao, r.status,
         r.setor_id, r.usuario_solicitante_id, r.usuario_separador_id,
         r.data_inicio_separacao;

CREATE OR REPLACE VIEW vw_historico_movimentacoes AS
SELECT
    me.created_at AS data,
    u.nome         AS usuario,
    s.nome         AS setor,
    m.descricao    AS material,
    um.sigla       AS unidade,
    me.tipo,
    me.quantidade,
    me.estoque_anterior,
    me.estoque_posterior,
    me.id,
    me.material_id,
    me.usuario_id,
    me.requisicao_id,
    r.setor_id,
    r.numero       AS requisicao_numero,
    r.data_solicitacao AS requisicao_data,
    solicitante.nome AS solicitante,
    separador.nome AS separador
FROM movimentacoes_estoque me
JOIN usuarios u  ON u.id = me.usuario_id
JOIN materiais m ON m.id = me.material_id
JOIN unidades_medida um ON um.id = m.unidade_medida_id
LEFT JOIN requisicoes r ON r.id = me.requisicao_id
LEFT JOIN setores s     ON s.id = r.setor_id
LEFT JOIN usuarios solicitante ON solicitante.id = r.usuario_solicitante_id
LEFT JOIN usuarios separador ON separador.id = r.usuario_separador_id;

DROP PROCEDURE IF EXISTS sp_registrar_saida_estoque;
