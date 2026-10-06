USE til_marcon_almoxarifado;

-- =====================================================================
-- 13. DADOS INICIAIS — CATEGORIAS
-- =====================================================================
INSERT INTO categorias (nome, codigo_prefixo, descricao) VALUES
('Matérias-primas, metais e perfis',                     'MP', 'Chapas, barras, perfis e vigas metálicas'),
('Consumíveis de solda e corte térmico',                  'CS', 'Arames, eletrodos, bicos e insumos de soldagem'),
('Abrasivos, corte e usinagem',                           'AB', 'Discos, brocas, fresas e ferramentas de corte'),
('Elementos de fixação',                                  'FX', 'Parafusos, porcas, arruelas e rebites'),
('Químicos, lubrificantes e MRO',                         'QM', 'Óleos, graxas, desengraxantes e produtos químicos'),
('Equipamentos de Proteção Individual',                   'EP', 'EPIs para uso operacional'),
('Utensílios de almoxarifado, manutenção e operação',     'UT', 'Materiais de apoio à manutenção e operação');

-- =====================================================================
-- 14. DADOS INICIAIS — UNIDADES DE MEDIDA
-- =====================================================================
INSERT INTO unidades_medida (nome) VALUES
('Unidade'), ('Chapa'), ('Barra'), ('Pedaço'), ('Rolo'), ('Caixa'),
('Kg'), ('M³'), ('Galão'), ('Frasco'), ('Lata'), ('Tubo'),
('Bombona'), ('Par'), ('Jogo'), ('Pacote'), ('Bisnaga'), ('Metro');

-- =====================================================================
-- 15. DADOS DE EXEMPLO — SETORES
-- Preparado para cadastro futuro; não representa necessariamente os
-- setores oficiais da Til Marcon.
-- =====================================================================
INSERT INTO setores (nome, codigo) VALUES
('Produção',   'PROD'),
('Manutenção', 'MANUT'),
('Solda',      'SOLDA'),
('Usinagem',   'USIN'),
('Montagem',   'MONT');

-- =====================================================================
-- 16. DADOS DE EXEMPLO — LOCALIZAÇÕES
-- =====================================================================
INSERT INTO localizacoes (codigo, descricao, corredor, estante, prateleira, posicao) VALUES
('A1-E1-P1', 'Corredor A, estante 1, prateleira 1', 'A1', 'E1', 'P1', '01'),
('A1-E2-P1', 'Corredor A, estante 2, prateleira 1', 'A1', 'E2', 'P1', '01'),
('B2-E1-P3', 'Corredor B, estante 1, prateleira 3', 'B2', 'E1', 'P3', '01');
-- =====================================================================
-- 17. DADOS DE EXEMPLO — LOCALIZAÇÕES ADICIONAIS
-- =====================================================================
INSERT INTO localizacoes (codigo, descricao, corredor, estante, prateleira, posicao) VALUES
('A1-E1-P2', 'Corredor A, estante 1, prateleira 2', 'A1', 'E1', 'P2', '01'),
('A1-E2-P2', 'Corredor A, estante 2, prateleira 2', 'A1', 'E2', 'P2', '01'),
('A2-E1-P1', 'Corredor A, estante 1, prateleira 1', 'A2', 'E1', 'P1', '01'),
('A2-E2-P1', 'Corredor A, estante 2, prateleira 1', 'A2', 'E2', 'P1', '01'),
('B1-E1-P1', 'Corredor B, estante 1, prateleira 1', 'B1', 'E1', 'P1', '01'),
('B1-E2-P1', 'Corredor B, estante 2, prateleira 1', 'B1', 'E2', 'P1', '01'),
('B2-E1-P1', 'Corredor B, estante 1, prateleira 1', 'B2', 'E1', 'P1', '01'),
('B2-E2-P3', 'Corredor B, estante 2, prateleira 3', 'B2', 'E2', 'P3', '01'),
('C1-E1-P1', 'Corredor C, estante 1, prateleira 1', 'C1', 'E1', 'P1', '01'),
('C1-E2-P2', 'Corredor C, estante 2, prateleira 2', 'C1', 'E2', 'P2', '01'),
('C2-E1-P3', 'Corredor C, estante 1, prateleira 3', 'C2', 'E1', 'P3', '01'),
('D1-E1-P1', 'Corredor D, estante 1, prateleira 1', 'D1', 'E1', 'P1', '01');

-- =====================================================================
-- 18. DADOS DOS MATERIAIS

-- =====================================================================
-- 18. DADOS DOS MATERIAIS
-- Código, descrição e prefixo de categoria preservados exatamente como
-- fornecidos no arquivo de origem. Unidade e especificação inferidas
-- tecnicamente.
-- =====================================================================

-- ---- MP — Matérias-primas, metais e perfis ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('MP-001', 'Chapa de Aço Carbono SAE 1020 - 1/8" (3.17mm)',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Espessura 1/8" (3,17mm) — uso em estruturas e componentes metálicos gerais', UUID()),
('MP-002', 'Chapa de Aço Carbono SAE 1020 - 1/4" (6.35mm)',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Espessura 1/4" (6,35mm) — uso em estruturas e componentes metálicos gerais', UUID()),
('MP-003', 'Chapa de Aço Inox AISI 304 - Escovada 1.5mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Inox AISI 304, acabamento escovado, espessura 1,5mm', UUID()),
('MP-004', 'Chapa de Alumínio Naval 5052 H32 - 2.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Chapa'),
    'Liga 5052 H32, espessura 2,0mm, aplicação naval/estrutural', UUID()),
('MP-005', 'Viga U de Aço Carbono - 3"',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Perfil U 3", aço carbono', UUID()),
('MP-007', 'Perfil Tubular Quadrado Aço Carbono 40x40x2.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Seção 40x40mm, parede 2,0mm', UUID()),
('MP-012', 'Barra Redonda de Aço SAE 1045 - Diâmetro 1"',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Diâmetro 1", aço SAE 1045', UUID()),
('MP-013', 'Barra Redonda de Aço SAE 4140 - Diâmetro 2"',
    (SELECT id FROM categorias WHERE codigo_prefixo='MP'), (SELECT id FROM unidades_medida WHERE nome='Barra'),
    'Diâmetro 2", aço SAE 4140', UUID());

-- ---- CS — Consumíveis de solda e corte térmico ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('CS-001', 'Arame de Solda MIG/MAG Solid ER70S-6 - 1.2mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Rolo'),
    'Bitola 1,2mm, processo MIG/MAG', UUID()),
('CS-004', 'Eletrodo Revestido AWS E6013 - 2.50mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Bitola 2,50mm, uso geral', UUID()),
('CS-005', 'Eletrodo Revestido AWS E7018 - 3.25mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Bitola 3,25mm, alta resistência mecânica', UUID()),
('CS-012', 'Bico de Contato MIG M6 x 28 x 1.2mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Rosca M6, comprimento 28mm, para arame 1,2mm', UUID()),
('CS-017', 'Antirrespingo de Solda em Spray',
    (SELECT id FROM categorias WHERE codigo_prefixo='CS'), (SELECT id FROM unidades_medida WHERE nome='Lata'),
    'Uso em processos de solda MIG/MAG', UUID());

-- ---- AB — Abrasivos, corte e usinagem ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('AB-001', 'Disco de Corte para Aço Carbono 4.1/2" x 1.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Diâmetro 4.1/2", espessura 1,0mm', UUID()),
('AB-004', 'Disco Flap Grão 40 - Zircônio 4.1/2"',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Grão 40, zircônio, diâmetro 4.1/2"', UUID()),
('AB-010', 'Broca helicoidal HSS DIN 338 - 3.0mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Diâmetro 3,0mm, aço rápido HSS', UUID()),
('AB-014', 'Inserto de Metal Duro WNMG 080408',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Geometria WNMG 080408, uso em torneamento', UUID()),
('AB-019', 'Fresa Metal Duro Topo Reto 4 Facas - Ø 10mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='AB'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    '4 facas, diâmetro 10mm', UUID());

-- ---- FX — Elementos de fixação ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('FX-001', 'Parafuso Sextavado RI Grau 5 - 1/4" x 1" UNC',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Rosca inteira, grau 5, 1/4" x 1" UNC', UUID()),
('FX-002', 'Parafuso Sextavado RP Classe 8.8 - M10 x 50mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Rosca parcial, classe 8.8, M10 x 50mm', UUID()),
('FX-004', 'Parafuso Allen Cabeça Cilíndrica M6 x 20mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Sextavado interno, M6 x 20mm', UUID()),
('FX-008', 'Porca Sextavada Leve Zincada 1/4" UNC',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Zincada, rosca 1/4" UNC', UUID()),
('FX-012', 'Arruela Lisa Zincada DIN 125 - M8',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'DIN 125, M8, zincada', UUID()),
('FX-017', 'Rebite de Repuxo Alumínio/Aço 4.0 x 12mm',
    (SELECT id FROM categorias WHERE codigo_prefixo='FX'), (SELECT id FROM unidades_medida WHERE nome='Caixa'),
    'Diâmetro 4,0mm, comprimento 12mm', UUID());

-- ---- QM — Químicos, lubrificantes e MRO ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('QM-001', 'Óleo Solúvel Semi-Sintético para Usinagem',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Galão'),
    'Uso em processos de usinagem', UUID()),
('QM-003', 'Graxa de Lítio NLGI 2',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Bisnaga'),
    'Consistência NLGI 2, lubrificação geral', UUID()),
('QM-004', 'Óleo Lubrificante Industrial ISO VG 68',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Galão'),
    'Viscosidade ISO VG 68', UUID()),
('QM-007', 'Desengraxante Industrial Alcalino',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Bombona'),
    'Limpeza de peças e superfícies metálicas', UUID()),
('QM-013', 'Trava Química de Alta Torque',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Frasco'),
    'Fixação roscada de alta resistência', UUID()),
('QM-017', 'Desengripante e Lubrificante em Spray',
    (SELECT id FROM categorias WHERE codigo_prefixo='QM'), (SELECT id FROM unidades_medida WHERE nome='Lata'),
    'Uso geral em manutenção', UUID());

-- ---- EP — Equipamentos de Proteção Individual ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('EP-001', 'Máscara de Solda Eletrônica de Escurecimento Automático',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Escurecimento automático, uso em soldagem', UUID()),
('EP-004', 'Avental de Raspa de Couro',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Proteção térmica para soldagem', UUID()),
('EP-008', 'Luva de Raspa Cano Longo',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Par'),
    'Proteção térmica e mecânica', UUID()),
('EP-012', 'Óculos de Proteção Incolor',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Lente incolor, proteção ocular', UUID()),
('EP-016', 'Respirador Semifacial PFF2',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Filtro PFF2, proteção respiratória', UUID()),
('EP-018', 'Botina de Segurança',
    (SELECT id FROM categorias WHERE codigo_prefixo='EP'), (SELECT id FROM unidades_medida WHERE nome='Par'),
    'Uso industrial, com biqueira de proteção', UUID());

-- ---- UT — Utensílios de almoxarifado, manutenção e operação ----
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('UT-001', 'Estopa Branca para Limpeza Mecânica',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Kg'),
    'Limpeza geral de máquinas e equipamentos', UUID()),
('UT-005', 'Fita Veda Rosca PTFE',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Rolo'),
    'Vedação de roscas hidráulicas/pneumáticas', UUID()),
('UT-009', 'Abraçadeira de Nylon',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Pacote'),
    'Fixação de cabos e mangueiras', UUID()),
('UT-011', 'Engate Rápido Pneumático Macho',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Conexão pneumática rápida', UUID()),
('UT-018', 'Trena Métrica Manual com Trava - 5 Metros',
    (SELECT id FROM categorias WHERE codigo_prefixo='UT'), (SELECT id FROM unidades_medida WHERE nome='Unidade'),
    'Medição manual, trava automática, 5 metros', UUID());

-- Catálogo ampliado de materiais para dados de demonstração.
-- Todos os registros são fictícios; ajuste saldos e especificações à operação real.
INSERT INTO materiais (codigo, descricao, categoria_id, unidade_medida_id, especificacao, qr_code) VALUES
('MP-006','Cantoneira de aço carbono 1.1/2 x 1/8 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Barra'),'Perfil laminado para estruturas leves',UUID()),
('MP-008','Tubo de aço carbono redondo 1 pol. schedule 40',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Barra'),'Diâmetro nominal 1 pol.',UUID()),
('MP-009','Tubo de aço carbono quadrado 30 x 30 x 1,5 mm',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Barra'),'Seção quadrada, parede 1,5 mm',UUID()),
('MP-010','Barra chata de aço carbono 1 x 3/16 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Barra'),'Aço carbono para fabricação geral',UUID()),
('MP-011','Chapa galvanizada 1,5 mm',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Chapa'),'Aço galvanizado para proteção e fechamento',UUID()),
('MP-014','Barra redonda de aço SAE 1020 3/4 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Barra'),'Diâmetro 3/4 pol.',UUID()),
('MP-015','Chapa de aço carbono SAE 1020 3/16 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='MP'),(SELECT id FROM unidades_medida WHERE nome='Chapa'),'Espessura aproximada 4,76 mm',UUID()),
('CS-002','Arame tubular para soldagem E71T-1 1,2 mm',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Rolo'),'Processo MIG/MAG com proteção gasosa',UUID()),
('CS-003','Arame MIG inox ER308LSi 1,0 mm',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Rolo'),'Consumível para aço inoxidável',UUID()),
('CS-006','Eletrodo revestido AWS E6013 3,25 mm',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Uso geral em aço carbono',UUID()),
('CS-007','Eletrodo revestido AWS E7018 2,50 mm',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Baixo hidrogênio, aço carbono',UUID()),
('CS-008','Eletrodo inox AWS E308L-16 2,50 mm',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Soldagem de aço inoxidável',UUID()),
('CS-009','Bocal cerâmico para tocha TIG nº 7',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Compatível com tocha TIG padrão',UUID()),
('CS-010','Vareta TIG ER70S-2 2,4 mm',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Kg'),'Aço carbono, vareta para soldagem TIG',UUID()),
('CS-011','Bico de corte para maçarico nº 2',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Para corte oxicombustível',UUID()),
('CS-013','Difusor de gás para tocha MIG',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Peça de reposição para tocha MIG',UUID()),
('CS-014','Lente protetora para máscara de solda',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Lente externa de reposição',UUID()),
('CS-015','Spray antirrespingo sem silicone',(SELECT id FROM categorias WHERE codigo_prefixo='CS'),(SELECT id FROM unidades_medida WHERE nome='Lata'),'Proteção de bocal e peças durante soldagem',UUID()),
('AB-002','Disco de corte inox 4.1/2 x 1,0 mm',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Abrasivo para aço inoxidável',UUID()),
('AB-003','Disco de desbaste aço 4.1/2 x 6,4 mm',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Uso em esmerilhadeira angular',UUID()),
('AB-005','Disco flap grão 80 - zircônio 4.1/2 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Acabamento fino em aço',UUID()),
('AB-006','Escova circular de aço trançado 4 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Remoção de carepa e oxidação',UUID()),
('AB-007','Lixa em folha grão 120',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Pacote'),'Folha para acabamento manual',UUID()),
('AB-008','Broca HSS DIN 338 6,0 mm',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Aço rápido para metais',UUID()),
('AB-009','Broca HSS DIN 338 10,0 mm',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Aço rápido para metais',UUID()),
('AB-011','Macho manual M8 x 1,25 mm',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Jogo'),'Jogo para abertura de rosca métrica',UUID()),
('AB-012','Lima chata bastarda 10 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Ferramenta para ajuste manual',UUID()),
('AB-013','Serra copo bimetálica 32 mm',(SELECT id FROM categorias WHERE codigo_prefixo='AB'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Corte de chapas e tubos',UUID()),
('FX-003','Parafuso sextavado classe 8.8 M8 x 30 mm',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Acabamento zincado',UUID()),
('FX-005','Parafuso Allen cabeça cilíndrica M8 x 30 mm',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Aço classe 12.9',UUID()),
('FX-006','Porca sextavada classe 8 M10',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Rosca métrica, acabamento zincado',UUID()),
('FX-007','Porca travante nylon M8',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Inserto de poliamida',UUID()),
('FX-009','Arruela lisa zincada DIN 125 M10',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Aço zincado',UUID()),
('FX-010','Arruela de pressão DIN 127 M8',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Caixa'),'Aço mola zincado',UUID()),
('FX-011','Chumbador mecânico 3/8 x 3 pol.',(SELECT id FROM categorias WHERE codigo_prefixo='FX'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Fixação em concreto',UUID()),
('QM-002','Óleo hidráulico ISO VG 46',(SELECT id FROM categorias WHERE codigo_prefixo='QM'),(SELECT id FROM unidades_medida WHERE nome='Galão'),'Lubrificante para sistemas hidráulicos',UUID()),
('QM-005','Fluido de corte integral',(SELECT id FROM categorias WHERE codigo_prefixo='QM'),(SELECT id FROM unidades_medida WHERE nome='Galão'),'Aplicação em operações de usinagem',UUID()),
('QM-006','Graxa de lítio EP2',(SELECT id FROM categorias WHERE codigo_prefixo='QM'),(SELECT id FROM unidades_medida WHERE nome='Kg'),'Lubrificação de rolamentos e mancais',UUID()),
('QM-008','Desengripante aerosol 300 ml',(SELECT id FROM categorias WHERE codigo_prefixo='QM'),(SELECT id FROM unidades_medida WHERE nome='Lata'),'Soltura de componentes oxidados',UUID()),
('QM-009','Desengraxante biodegradável concentrado',(SELECT id FROM categorias WHERE codigo_prefixo='QM'),(SELECT id FROM unidades_medida WHERE nome='Bombona'),'Limpeza pesada de peças',UUID()),
('QM-010','Trava rosca média resistência',(SELECT id FROM categorias WHERE codigo_prefixo='QM'),(SELECT id FROM unidades_medida WHERE nome='Frasco'),'Fixação e vedação de roscas',UUID()),
('EP-002','Máscara de solda passiva',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Visor articulado para soldagem',UUID()),
('EP-003','Protetor facial incolor',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Proteção facial contra partículas',UUID()),
('EP-005','Mangote de raspa para soldador',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Par'),'Proteção térmica de antebraço',UUID()),
('EP-006','Luva de vaqueta para proteção mecânica',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Par'),'Uso em movimentação e manutenção',UUID()),
('EP-007','Protetor auricular tipo plug',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Par'),'Proteção auditiva reutilizável',UUID()),
('EP-009','Capacete de segurança classe B',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Com suspensão ajustável',UUID()),
('EP-010','Respirador descartável PFF2 com válvula',(SELECT id FROM categorias WHERE codigo_prefixo='EP'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Proteção respiratória para particulados',UUID()),
('UT-002','Pano industrial para limpeza',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Kg'),'Panos reutilizáveis para manutenção',UUID()),
('UT-003','Fita isolante preta 19 mm',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Rolo'),'Fita isolante elétrica',UUID()),
('UT-004','Fita adesiva crepe 24 mm',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Rolo'),'Uso geral em identificação e mascaramento',UUID()),
('UT-006','Abraçadeira de nylon 200 mm',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Pacote'),'Pacote para organização de cabos',UUID()),
('UT-007','Disco de lixa para politriz 5 pol. grão 80',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Lixamento de superfícies',UUID()),
('UT-008','Chave combinada 13 mm',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Unidade'),'Aço cromo vanádio',UUID()),
('UT-010','Jogo de chave Allen métrica',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Jogo'),'Medidas métricas variadas',UUID()),
('UT-012','Mangueira pneumática PU 8 mm',(SELECT id FROM categorias WHERE codigo_prefixo='UT'),(SELECT id FROM unidades_medida WHERE nome='Metro'),'Mangueira flexível para ar comprimido',UUID());

-- =====================================================================
-- 19. ESTOQUE — um registro por material (níveis ilustrativos de
-- exemplo; devem ser substituídos pela contagem real do almoxarifado)
-- =====================================================================
INSERT INTO estoque (material_id, quantidade_atual, estoque_minimo, estoque_maximo, localizacao_id)
SELECT m.id,
       CASE WHEN m.codigo = 'AB-014' THEN 3      -- exemplo de item com estoque baixo
            WHEN m.codigo = 'CS-012' THEN 0       -- exemplo de item sem estoque
            ELSE 50 END,
       10, 200,
       (SELECT id FROM localizacoes ORDER BY id LIMIT 1)
FROM materiais m;
