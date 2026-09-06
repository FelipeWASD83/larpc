"""Testes do LarpC.

Roda com:  python -m unittest discover -s testes  (a partir da raiz do projeto)

Os testes de transpilacao nao precisam de compilador. Os de ponta a ponta
precisam do `cl` da Microsoft e sao pulados se ele nao estiver na maquina.
"""

import os
import subprocess
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from larpc.lexer import ErroDeLarp  # noqa: E402
from larpc.msvc import SemCompilador, achar_vcvars  # noqa: E402
from larpc.transpilador import (  # noqa: E402
    decodificar_identificador,
    transpilar,
)

PRELUDIO = "%appdata% stdio\n"


def c(fonte, alvo="exe"):
    return transpilar(fonte, arquivo="teste.larp", alvo=alvo).codigo_c


def corpo(miolo):
    """Enrola o miolo num programa completo, para o teste nao repetir molde."""
    return (
        PRELUDIO
        + "script mainframe sudo\n"
        + miolo
        + "\nexfiltrate 0 opsec\n--force\n"
    )


class TesteDecodificador(unittest.TestCase):
    def test_underscore_vira_espaco(self):
        self.assertEqual(
            decodificar_identificador("i_use_arch_btw"), "i use arch btw"
        )

    def test_dois_underscores_viram_quebra(self):
        self.assertEqual(decodificar_identificador("ola__"), "ola\\n")

    def test_tres_underscores_viram_duas_quebras(self):
        self.assertEqual(decodificar_identificador("ola___"), "ola\\n\\n")

    def test_formato_simples(self):
        self.assertEqual(decodificar_identificador("pct_d"), "%d")

    def test_formato_com_precisao(self):
        self.assertEqual(decodificar_identificador("pct_2f"), "%.2f")

    def test_formato_longo(self):
        self.assertEqual(decodificar_identificador("pct_lf"), "%lf")

    def test_porcento_literal(self):
        self.assertEqual(decodificar_identificador("pct_pct"), "%%")

    def test_formato_misturado_com_texto(self):
        self.assertEqual(
            decodificar_identificador("total_pct_d_itens__"),
            "total %d itens\\n",
        )

    def test_pct_no_meio_de_palavra_nao_conta(self):
        self.assertEqual(decodificar_identificador("expct_d"), "expct d")


class TesteSwap(unittest.TestCase):
    def test_swap_simples(self):
        saida = c(corpo('i_use_arch_btw("printf") opsec'))
        self.assertIn('printf("i use arch btw");', saida)

    def test_swap_com_argumentos(self):
        saida = c(corpo('valor_pct_d__("printf", x) opsec'))
        self.assertIn('printf("valor %d\\n", x);', saida)

    def test_keyword_no_swap_vira_texto(self):
        saida = c(corpo('based("printf") opsec'))
        self.assertIn('printf("based");', saida)

    def test_chamada_normal_nao_e_swap(self):
        saida = c(corpo("resultado = calcular(a, b) opsec"))
        self.assertIn("calcular(a, b)", saida)

    def test_condicao_com_parenteses_nao_e_swap(self):
        saida = c(corpo("probably (x == 5) sudo\nunplug opsec\n--force"))
        self.assertIn("if (x == 5) {", saida)

    def test_nome_invalido_entre_aspas_reclama(self):
        with self.assertRaises(ErroDeLarp):
            c(corpo('ola("nao e nome de funcao") opsec'))


class TesteVocabulario(unittest.TestCase):
    def test_include(self):
        self.assertIn("#include <stdio.h>", c(corpo("exfiltrate 0 opsec")))

    def test_include_local(self):
        fonte = '%appdata% "meu.h"\nscript mainframe sudo\n--force\n'
        self.assertIn('#include "meu.h"', c(fonte))

    def test_mainframe_ganha_void(self):
        self.assertIn("int main(void) {", c(corpo("exfiltrate 0 opsec")))

    def test_payload_vira_parametros(self):
        fonte = (
            PRELUDIO
            + "script somar payload(script a, script b) sudo\n"
            "exfiltrate a + b opsec\n--force\n"
            "script mainframe sudo\nexfiltrate 0 opsec\n--force\n"
        )
        self.assertIn("int somar(int a, int b) {", c(fonte))

    def test_funcao_com_payload_nao_ganha_void(self):
        fonte = (
            PRELUDIO
            + "zeroday nada payload(script a) sudo\n--force\n"
            "script mainframe sudo\nexfiltrate 0 opsec\n--force\n"
        )
        self.assertIn("void nada(int a) {", c(fonte))
        self.assertNotIn("(void)(int a)", c(fonte))

    def test_comentario(self):
        saida = c(
            PRELUDIO + "nullsec so um teste\nscript mainframe sudo\n--force\n"
        )
        self.assertIn("// so um teste", saida)

    def test_doxx_vira_endereco(self):
        saida = c(corpo('pct_d("scanf", doxx x) opsec'))
        self.assertIn('scanf("%d", &x);', saida)

    def test_based_e_cringe_fora_do_swap(self):
        saida = c(corpo("script x = based opsec\nscript y = cringe opsec"))
        self.assertIn("int x = 1;", saida)
        self.assertIn("int y = 0;", saida)

    def test_loops(self):
        saida = c(
            corpo(
                "doomscroll (based) sudo\nunplug opsec\n--force\n"
                "grindset (script i = 0; i < 3; i++) sudo\npersist opsec\n--force"
            )
        )
        self.assertIn("while (1) {", saida)
        self.assertIn("for (int i = 0; i < 3; i++) {", saida)
        self.assertIn("break;", saida)
        self.assertIn("continue;", saida)

    def test_ghost_e_trustmebro(self):
        saida = c(
            corpo(
                "ghost script contador = 0 opsec\ntrustmebro script t = 7 opsec"
            )
        )
        self.assertIn("static int contador = 0;", saida)
        self.assertIn("const int t = 7;", saida)


class TesteRecusas(unittest.TestCase):
    def test_c_cru_e_recusado(self):
        with self.assertRaises(ErroDeLarp) as caso:
            c(PRELUDIO + "int mainframe sudo\n--force\n")
        self.assertIn("script", str(caso.exception))

    def test_sem_mainframe_reclama(self):
        with self.assertRaises(ErroDeLarp):
            c(PRELUDIO + "script somar payload(script a) sudo\n--force\n")

    def test_sem_include_avisa_mas_deixa_passar(self):
        resultado = transpilar(
            "script mainframe sudo\nexfiltrate 0 opsec\n--force\n",
            arquivo="teste.larp",
        )
        self.assertTrue(resultado.avisos)
        self.assertIn("include", resultado.avisos[0])

    def test_appdata_no_meio_da_linha_reclama(self):
        with self.assertRaises(ErroDeLarp):
            c(
                "script x = 1 opsec %appdata% stdio\n"
                "script mainframe sudo\n--force\n"
            )

    def test_payload_solto_reclama(self):
        with self.assertRaises(ErroDeLarp):
            c(corpo("payload opsec"))


class TesteFormatoDaSaida(unittest.TestCase):
    def test_c_tem_as_mesmas_linhas_do_larp(self):
        fonte = corpo('ola__("printf") opsec')
        gerado = c(fonte)
        self.assertEqual(len(fonte.split("\n")), len(gerado.split("\n")))

    def test_erro_do_compilador_cai_na_linha_certa(self):
        fonte = (
            PRELUDIO + "\nscript mainframe sudo\n    exfiltrate y opsec\n--force\n"
        )
        linhas = c(fonte).split("\n")
        self.assertEqual(linhas[3].strip(), "return y;")

    def test_indentacao_preservada(self):
        saida = c(corpo('    ola("printf") opsec'))
        self.assertIn('    printf("ola");', saida)

    def test_alvo_dll_troca_o_main(self):
        saida = c(corpo("exfiltrate 0 opsec"), alvo="dll")
        self.assertIn("int larpc_main_real(void) {", saida)
        self.assertIn("__declspec(dllexport) int larpc_mainframe(void)", saida)
        self.assertNotIn("int main(void)", saida)


def tem_compilador():
    try:
        achar_vcvars()
        return True
    except SemCompilador:
        return False


@unittest.skipUnless(tem_compilador(), "sem cl.exe nesta maquina")
class TesteDePontaAPonta(unittest.TestCase):
    def rodar_larp(self, nome, entrada=""):
        return subprocess.run(
            [sys.executable, "-m", "larpc", "rodar", os.path.join("exemplos", nome)],
            cwd=RAIZ,
            input=entrada,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def test_ola_roda(self):
        saida = self.rodar_larp("ola.larp")
        self.assertEqual(saida.returncode, 0, saida.stderr)
        self.assertIn("i use arch btw", saida.stdout)
        self.assertIn("based", saida.stdout)
        self.assertNotIn("cringe", saida.stdout)

    def test_calculadora_faz_conta(self):
        saida = self.rodar_larp(
            "calculadora.larp", "12 + 30\n7 * 6\n10 / 4\nsair\n"
        )
        self.assertEqual(saida.returncode, 0, saida.stderr)
        self.assertIn("42.00", saida.stdout)
        self.assertIn("2.50", saida.stdout)
        self.assertIn("ate mais bro", saida.stdout)

    def test_calculadora_barra_divisao_por_zero(self):
        saida = self.rodar_larp("calculadora.larp", "5 / 0\nsair\n")
        self.assertEqual(saida.returncode, 0, saida.stderr)
        self.assertIn("dividir por zero", saida.stdout)


if __name__ == "__main__":
    unittest.main()
