DROP DATABASE IF EXISTS til_marcon_almoxarifado;

CREATE DATABASE IF NOT EXISTS til_marcon_almoxarifado
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE til_marcon_almoxarifado;

-- =====================================================================
-- 1. CATEGORIAS
-- =====================================================================
CREATE TABLE categorias (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL,
    codigo_prefixo  VARCHAR(5)   NOT NULL,
    descricao       VARCHAR(255) NULL,
    ativo           TINYINT(1)   NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_categorias_prefixo UNIQUE (codigo_prefixo),
    CONSTRAINT uq_categorias_nome    UNIQUE (nome)
) ENGINE=InnoDB;

-- =====================================================================
-- 2. UNIDADES DE MEDIDA
-- =====================================================================
CREATE TABLE unidades_medida (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(50) NOT NULL,
    sigla       VARCHAR(10) NULL,
    ativo       TINYINT(1)  NOT NULL DEFAULT 1,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_unidades_nome UNIQUE (nome)
) ENGINE=InnoDB;

-- =====================================================================
-- 3. LOCALIZAÇÕES FÍSICAS
-- =====================================================================
CREATE TABLE localizacoes (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo      VARCHAR(20)  NOT NULL,
    descricao   VARCHAR(150) NULL,
    corredor    VARCHAR(20)  NULL,
    estante     VARCHAR(20)  NULL,
    prateleira  VARCHAR(20)  NULL,
    posicao     VARCHAR(20)  NULL,
    ativo       TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_localizacoes_codigo UNIQUE (codigo)
) ENGINE=InnoDB;

-- =====================================================================
-- 4. SETORES
-- =====================================================================
CREATE TABLE setores (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    codigo      VARCHAR(20)  NOT NULL,
    ativo       TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_setores_codigo UNIQUE (codigo),
    CONSTRAINT uq_setores_nome   UNIQUE (nome)
) ENGINE=InnoDB;

-- =====================================================================
-- 5. USUÁRIOS
-- =====================================================================
CREATE TABLE usuarios (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome         VARCHAR(150) NOT NULL,
    login        VARCHAR(50)  NOT NULL,
    senha_hash   VARCHAR(255) NOT NULL COMMENT 'Hash bcrypt/argon2 gerado pela aplicação. Nunca texto puro.',
    perfil       ENUM('ADMIN','ALMOXARIFE','SOLICITANTE','GESTOR') NOT NULL,
    setor_id     INT UNSIGNED NULL,
    ativo        TINYINT(1)   NOT NULL DEFAULT 1,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuarios_login UNIQUE (login),
    CONSTRAINT fk_usuarios_setor FOREIGN KEY (setor_id) REFERENCES setores(id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================================================================
-- 6. MATERIAIS (dados de catálogo — não guarda níveis de estoque)
-- =====================================================================
CREATE TABLE materiais (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo              VARCHAR(20)  NOT NULL,
    descricao           VARCHAR(255) NOT NULL,
    categoria_id        INT UNSIGNED NOT NULL,
    unidade_medida_id   INT UNSIGNED NOT NULL,
    especificacao       VARCHAR(255) NULL,
    qr_code             CHAR(36)     NOT NULL COMMENT 'Identificador único (UUID) usado no QR Code, não depende da descrição.',
    ativo               TINYINT(1)   NOT NULL DEFAULT 1,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_materiais_codigo  UNIQUE (codigo),
    CONSTRAINT uq_materiais_qrcode  UNIQUE (qr_code),
    CONSTRAINT fk_materiais_categoria FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_materiais_unidade FOREIGN KEY (unidade_medida_id) REFERENCES unidades_medida(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =====================================================================
-- 7. ESTOQUE (dados operacionais — separado de materiais por natureza
--    de escrita distinta: catálogo muda pouco, estoque muda o tempo todo)
-- =====================================================================
CREATE TABLE estoque (
    id                        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    material_id               INT UNSIGNED NOT NULL,
    quantidade_atual          DECIMAL(12,3) NOT NULL DEFAULT 0,
    estoque_minimo            DECIMAL(12,3) NOT NULL DEFAULT 0,
    estoque_maximo            DECIMAL(12,3) NULL,
    localizacao_id            INT UNSIGNED NULL,
    lote                      VARCHAR(50) NULL,
    data_ultima_movimentacao  DATETIME NULL,
    created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_estoque_material UNIQUE (material_id),
    CONSTRAINT fk_estoque_material FOREIGN KEY (material_id) REFERENCES materiais(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_estoque_localizacao FOREIGN KEY (localizacao_id) REFERENCES localizacoes(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_estoque_atual_nao_negativo  CHECK (quantidade_atual >= 0),
    CONSTRAINT chk_estoque_minimo_nao_negativo CHECK (estoque_minimo >= 0),
    CONSTRAINT chk_estoque_maximo_valido       CHECK (estoque_maximo IS NULL OR estoque_maximo >= estoque_minimo)
) ENGINE=InnoDB;

-- =====================================================================
-- 8. REQUISIÇÕES
-- =====================================================================
CREATE TABLE requisicoes (
    id                       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    numero                   VARCHAR(30) NOT NULL,
    setor_id                 INT UNSIGNED NOT NULL,
    usuario_solicitante_id   INT UNSIGNED NOT NULL,
    usuario_separador_id     INT UNSIGNED NULL,
    status                   ENUM('PENDENTE','EM_SEPARACAO','SEPARADA','ATENDIDA','CANCELADA')
                                NOT NULL DEFAULT 'PENDENTE',
    data_solicitacao         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_inicio_separacao    DATETIME NULL,
    data_conclusao           DATETIME NULL,
    observacao               VARCHAR(500) NULL,
    created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_requisicoes_numero UNIQUE (numero),
    CONSTRAINT fk_requisicoes_setor FOREIGN KEY (setor_id) REFERENCES setores(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_requisicoes_solicitante FOREIGN KEY (usuario_solicitante_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_requisicoes_separador FOREIGN KEY (usuario_separador_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================================================================
-- 9. ITENS DA REQUISIÇÃO
-- =====================================================================
CREATE TABLE requisicao_itens (
    id                       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    requisicao_id            INT UNSIGNED NOT NULL,
    material_id              INT UNSIGNED NOT NULL,
    quantidade_solicitada    DECIMAL(12,3) NOT NULL,
    quantidade_separada      DECIMAL(12,3) NOT NULL DEFAULT 0,
    quantidade_atendida      DECIMAL(12,3) NOT NULL DEFAULT 0,
    status                   ENUM('PENDENTE','SEPARADO','ATENDIDO','CANCELADO')
                                NOT NULL DEFAULT 'PENDENTE',
    observacao               VARCHAR(500) NULL,
    created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_requisicao_material UNIQUE (requisicao_id, material_id),
    CONSTRAINT fk_itens_requisicao FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_itens_material FOREIGN KEY (material_id) REFERENCES materiais(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_item_solicitada_positiva CHECK (quantidade_solicitada > 0),
    CONSTRAINT chk_item_separada_nao_negativa CHECK (quantidade_separada >= 0),
    CONSTRAINT chk_item_atendida_nao_negativa CHECK (quantidade_atendida >= 0),
    CONSTRAINT chk_item_separada_max CHECK (quantidade_separada <= quantidade_solicitada),
    CONSTRAINT chk_item_atendida_max CHECK (quantidade_atendida <= quantidade_solicitada)
) ENGINE=InnoDB;

-- =====================================================================
-- 10. MOVIMENTAÇÕES DE ESTOQUE (log de auditoria — somente inserção)
-- =====================================================================
CREATE TABLE movimentacoes_estoque (
    id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    material_id        INT UNSIGNED NOT NULL,
    usuario_id         INT UNSIGNED NOT NULL,
    requisicao_id      INT UNSIGNED NULL,
    tipo               ENUM('ENTRADA','SAIDA','AJUSTE','DEVOLUCAO') NOT NULL,
    quantidade         DECIMAL(12,3) NOT NULL,
    estoque_anterior   DECIMAL(12,3) NOT NULL,
    estoque_posterior  DECIMAL(12,3) NOT NULL,
    observacao         VARCHAR(500) NULL,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mov_material FOREIGN KEY (material_id) REFERENCES materiais(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_mov_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_mov_requisicao FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_mov_quantidade_positiva CHECK (quantidade > 0),
    CONSTRAINT chk_mov_anterior_nao_negativo  CHECK (estoque_anterior >= 0),
    CONSTRAINT chk_mov_posterior_nao_negativo CHECK (estoque_posterior >= 0)
) ENGINE=InnoDB;

-- =====================================================================
-- 11. ATENDIMENTOS DO ALMOXARIFE (sessão de turno/setor)
-- =====================================================================
CREATE TABLE atendimentos_almoxarifado (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id  INT UNSIGNED NOT NULL,
    setor_id    INT UNSIGNED NOT NULL,
    data_inicio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_fim    DATETIME NULL,
    status      ENUM('ABERTO','ENCERRADO') NOT NULL DEFAULT 'ABERTO',
    CONSTRAINT fk_atend_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_atend_setor FOREIGN KEY (setor_id) REFERENCES setores(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =====================================================================
-- 12. ÍNDICES ADICIONAIS
-- (codigo, qr_code, categoria_id, setor_id, requisicao_id, material_id
--  já são indexados automaticamente pelas restrições UNIQUE/FOREIGN KEY
--  do InnoDB — não recriados aqui para evitar índices redundantes)
-- =====================================================================
CREATE INDEX idx_requisicoes_status           ON requisicoes(status);
CREATE INDEX idx_requisicoes_data_solicitacao ON requisicoes(data_solicitacao);
CREATE INDEX idx_mov_created_at               ON movimentacoes_estoque(created_at);

-- =====================================================================
-- 21. VIEWS
-- =====================================================================

-- Situação atual do estoque de cada material ativo
CREATE VIEW vw_estoque_atual AS
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
    END AS situacao
FROM materiais m
JOIN categorias c       ON c.id = m.categoria_id
JOIN unidades_medida um ON um.id = m.unidade_medida_id
JOIN estoque e          ON e.material_id = m.id
WHERE m.ativo = 1;

-- Requisições ainda não concluídas
CREATE VIEW vw_requisicoes_pendentes AS
SELECT
    r.numero,
    s.nome AS setor,
    r.data_solicitacao AS data,
    r.status,
    COUNT(ri.id) AS quantidade_itens
FROM requisicoes r
JOIN setores s ON s.id = r.setor_id
LEFT JOIN requisicao_itens ri ON ri.requisicao_id = r.id
WHERE r.status IN ('PENDENTE','EM_SEPARACAO','SEPARADA')
GROUP BY r.id, r.numero, s.nome, r.data_solicitacao, r.status;

-- Histórico completo de movimentações, com setor de origem quando houver requisição
CREATE VIEW vw_historico_movimentacoes AS
SELECT
    me.created_at AS data,
    u.nome         AS usuario,
    s.nome         AS setor,
    m.descricao    AS material,
    me.tipo,
    me.quantidade,
    me.estoque_anterior,
    me.estoque_posterior
FROM movimentacoes_estoque me
JOIN usuarios u  ON u.id = me.usuario_id
JOIN materiais m ON m.id = me.material_id
LEFT JOIN requisicoes r ON r.id = me.requisicao_id
LEFT JOIN setores s     ON s.id = r.setor_id;

-- =====================================================================
-- 22. PROCEDURE — sp_registrar_saida_estoque
-- Transação atômica para confirmação de separação/saída de material.
-- Usa SELECT ... FOR UPDATE para bloquear a linha de estoque e, se
-- vinculada a uma requisição, a linha do item correspondente,
-- evitando condição de corrida entre saídas concorrentes do mesmo
-- material.
-- =====================================================================
DELIMITER $$

CREATE PROCEDURE sp_registrar_saida_estoque (
    IN p_material_id   INT UNSIGNED,
    IN p_quantidade    DECIMAL(12,3),
    IN p_usuario_id    INT UNSIGNED,
    IN p_requisicao_id INT UNSIGNED,
    IN p_observacao    VARCHAR(500)
)
BEGIN
    DECLARE v_estoque_id     INT UNSIGNED;
    DECLARE v_estoque_atual  DECIMAL(12,3);
    DECLARE v_novo_estoque   DECIMAL(12,3);
    DECLARE v_item_id        INT UNSIGNED;
    DECLARE v_qtd_atendida   DECIMAL(12,3);
    DECLARE v_itens_pendentes INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_quantidade IS NULL OR p_quantidade <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Quantidade deve ser maior que zero.';
    END IF;
    IF p_material_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Material é obrigatório.';
    END IF;
    IF p_usuario_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Usuário é obrigatório.';
    END IF;

    START TRANSACTION;

    -- Bloqueia a linha de estoque do material até o fim da transação
    SELECT id, quantidade_atual INTO v_estoque_id, v_estoque_atual
    FROM estoque
    WHERE material_id = p_material_id
    FOR UPDATE;

    IF v_estoque_id IS NULL THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Registro de estoque não encontrado para o material informado.';
    END IF;

    IF v_estoque_atual < p_quantidade THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Estoque insuficiente para realizar a saída.';
    END IF;

    SET v_novo_estoque = v_estoque_atual - p_quantidade;

    INSERT INTO movimentacoes_estoque (
        material_id, usuario_id, requisicao_id, tipo,
        quantidade, estoque_anterior, estoque_posterior, observacao
    ) VALUES (
        p_material_id, p_usuario_id, p_requisicao_id, 'SAIDA',
        p_quantidade, v_estoque_atual, v_novo_estoque, p_observacao
    );

    UPDATE estoque
    SET quantidade_atual = v_novo_estoque,
        data_ultima_movimentacao = NOW()
    WHERE id = v_estoque_id;

    IF p_requisicao_id IS NOT NULL THEN
        -- Bloqueia a linha do item da requisição correspondente
        SELECT id, quantidade_atendida INTO v_item_id, v_qtd_atendida
        FROM requisicao_itens
        WHERE requisicao_id = p_requisicao_id AND material_id = p_material_id
        FOR UPDATE;

        IF v_item_id IS NOT NULL THEN
            UPDATE requisicao_itens
            SET quantidade_separada = quantidade_separada + p_quantidade,
                quantidade_atendida = quantidade_atendida + p_quantidade,
                status = CASE
                    WHEN (quantidade_atendida + p_quantidade) >= quantidade_solicitada THEN 'ATENDIDO'
                    ELSE 'SEPARADO'
                END
            WHERE id = v_item_id;
        END IF;

        SELECT COUNT(*) INTO v_itens_pendentes
        FROM requisicao_itens
        WHERE requisicao_id = p_requisicao_id
          AND status NOT IN ('ATENDIDO','CANCELADO');

        IF v_itens_pendentes = 0 THEN
            UPDATE requisicoes
            SET status = 'ATENDIDA', data_conclusao = NOW()
            WHERE id = p_requisicao_id;
        ELSE
            UPDATE requisicoes
            SET status = 'EM_SEPARACAO',
                data_inicio_separacao = COALESCE(data_inicio_separacao, NOW())
            WHERE id = p_requisicao_id AND status = 'PENDENTE';
        END IF;
    END IF;

    COMMIT;
END$$

DELIMITER ;