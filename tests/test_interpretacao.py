from painel_macro.interpretacao import SEM_DADOS, GeradorInterpretacao, _intensidade, _listar


def test_funcoes_auxiliares():
    assert _listar([]) == ""
    assert _listar(["a"]) == "a"
    assert _listar([2001, 2002, 2003]) == "2001, 2002 e 2003"
    assert [_intensidade(r) for r in (0.1, -0.45, 0.9)] == ["fraca", "moderada", "forte"]


def test_texto_reflete_os_numeros_do_periodo(analisador):
    gerador = GeradorInterpretacao(analisador)

    assert "12/2023" in gerador.inflacao_e_meta()
    assert "2021" in gerador.inflacao_anual()          # único ano acima do teto
    assert "**Educação**" in gerador.grupos()
    assert "12,00% ao ano" in gerador.juros()
    assert "subiu **25,0%**" in gerador.cambio()
    assert "r = " in gerador.dispersao("selic")
    assert "R$ 100,00" in gerador.poder_de_compra()


def test_texto_muda_com_o_filtro(analisador):
    completo = GeradorInterpretacao(analisador).como_markdown()
    recorte = GeradorInterpretacao(
        analisador.filtrar_periodo("2022-01-01", "2023-12-01")
    ).como_markdown()

    assert completo != recorte
    assert completo.count("**") >= 14


def test_periodos_curtos_ou_vazios_geram_avisos(analisador):
    curto = GeradorInterpretacao(analisador.filtrar_periodo("2023-01-01", "2023-06-01"))
    assert "nenhum ano completo" in curto.inflacao_anual()
    assert "dois anos completos" in curto.sazonalidade()

    vazio = GeradorInterpretacao(analisador.filtrar_periodo("1990-01-01", "1990-12-01"))
    assert vazio.secoes() == [("Sem dados", SEM_DADOS)]
