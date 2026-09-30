USE til_marcon_almoxarifado;

SET @has_peso_unitario = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'materiais'
      AND column_name = 'peso_unitario_g'
);
SET @ddl = IF(@has_peso_unitario > 0, 'SELECT 1',
    'ALTER TABLE materiais ADD COLUMN peso_unitario_g DECIMAL(12,6) NULL COMMENT ''Peso unitário em gramas para cálculo de devoluções.''');
PREPARE migration_stmt FROM @ddl;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

CREATE TABLE IF NOT EXISTS devolucoes (
    id                    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    requisicao_item_id    INT UNSIGNED NOT NULL,
    usuario_operador_id   INT UNSIGNED NOT NULL,
    usuario_analise_id    INT UNSIGNED NULL,
    idempotency_key       VARCHAR(128) NOT NULL,
    peso_total_g          DECIMAL(12,3) NOT NULL,
    peso_unitario_g       DECIMAL(12,6) NOT NULL,
    quantidade_calculada  DECIMAL(12,3) NOT NULL,
    status                ENUM('PENDENTE','ACEITA','REJEITADA') NOT NULL DEFAULT 'PENDENTE',
    observacao            VARCHAR(500) NULL,
    observacao_analise    VARCHAR(500) NULL,
    created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    analisada_at          DATETIME NULL,
    CONSTRAINT uq_devolucoes_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT fk_devolucoes_item FOREIGN KEY (requisicao_item_id) REFERENCES requisicao_itens(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_devolucoes_operador FOREIGN KEY (usuario_operador_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_devolucoes_analise FOREIGN KEY (usuario_analise_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_devolucoes_peso_positivo CHECK (peso_total_g > 0),
    CONSTRAINT chk_devolucoes_unidade_positiva CHECK (peso_unitario_g > 0),
    CONSTRAINT chk_devolucoes_quantidade_positiva CHECK (quantidade_calculada > 0),
    INDEX idx_devolucoes_status_created (status, created_at),
    INDEX idx_devolucoes_item (requisicao_item_id)
) ENGINE=InnoDB;
