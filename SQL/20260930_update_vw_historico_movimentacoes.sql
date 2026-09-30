USE til_marcon_almoxarifado;

CREATE OR REPLACE VIEW vw_historico_movimentacoes AS
SELECT
    me.created_at AS data,
    u.nome         AS usuario,
    s.nome         AS setor,
    m.descricao    AS material,
    me.tipo,
    me.quantidade,
    me.estoque_anterior,
    me.estoque_posterior,
    me.id,
    me.material_id,
    me.usuario_id,
    me.requisicao_id,
    r.setor_id
FROM movimentacoes_estoque me
JOIN usuarios u  ON u.id = me.usuario_id
JOIN materiais m ON m.id = me.material_id
LEFT JOIN requisicoes r ON r.id = me.requisicao_id
LEFT JOIN setores s     ON s.id = r.setor_id;