import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Extrator de Consumo - Faturas de Energia",
    page_icon="☀️",
    layout="wide"
)


# ============================================================
# DICIONÁRIOS
# ============================================================

MESES = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12
}

NOME_MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

DIAS_PADRAO = {
    1: 31,
    2: 28,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31
}


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def normalizar(texto):
    if texto is None:
        return ""

    texto = str(texto)

    texto = texto.replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def converter_numero(valor):
    """
    Converte números brasileiros:

    291
    10,97
    1.234,56
    -16,28
    """

    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    valor = valor.replace("−", "-")
    valor = valor.replace("–", "-")

    # Remove espaços
    valor = valor.replace(" ", "")

    # Número brasileiro
    if "," in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    try:
        return float(valor)
    except Exception:
        return None


# ============================================================
# EXTRAÇÃO DO PDF
# ============================================================

def extrair_pdf(uploaded_file):

    paginas = []

    try:
        with pdfplumber.open(uploaded_file) as pdf:

            for numero_pagina, pagina in enumerate(pdf.pages, start=1):

                texto = pagina.extract_text()

                if texto:
                    paginas.append(
                        f"\n--- PÁGINA {numero_pagina} ---\n{texto}"
                    )

    except Exception as e:

        st.error(f"Erro ao abrir o PDF: {e}")
        return ""

    return "\n".join(paginas)


# ============================================================
# DETECTAR CONCESSIONÁRIA
# ============================================================

def detectar_concessionaria(texto):

    texto_upper = normalizar(texto).upper()

    # CEEE / Equatorial
    termos_ceee = [
        "CEEE",
        "EQUATORIAL",
        "ITAIPU",
        "CIP-ILUM",
        "CIP ILUM",
        "COMPANHIA ESTADUAL DE DISTRIBUIÇÃO DE ENERGIA ELÉTRICA"
    ]

    for termo in termos_ceee:
        if termo in texto_upper:
            return "CEEE"

    # RGE
    termos_rge = [
        "RGE",
        "RGE SUL",
        "RIO GRANDE ENERGIA"
    ]

    for termo in termos_rge:
        if termo in texto_upper:
            return "RGE"

    return "GENÉRICO"


# ============================================================
# CONVERSÃO DO ANO
# ============================================================

def converter_ano(ano):

    ano = str(ano).strip()

    if len(ano) == 4:
        return int(ano)

    if len(ano) == 2:

        numero = int(ano)

        if numero <= 50:
            return 2000 + numero
        else:
            return 1900 + numero

    return None


# ============================================================
# LOCALIZAR MÊS/ANO
# ============================================================

def encontrar_periodo(texto):

    texto_original = texto

    # Primeiro procura abreviações:
    #
    # JAN/26
    # JAN-26
    # JAN 26
    # JAN26
    #
    padrao = re.compile(
        r"\b("
        r"JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ"
        r")"
        r"(?:\s*[/\-]?\s*)"
        r"(\d{2}|\d{4})\b",
        re.IGNORECASE
    )

    encontrado = padrao.search(texto_original)

    if encontrado:

        mes_txt = encontrado.group(1).upper()
        ano_txt = encontrado.group(2)

        mes = MESES.get(mes_txt)
        ano = converter_ano(ano_txt)

        if mes and ano:

            return {
                "mes": mes,
                "ano": ano,
                "inicio_periodo": encontrado.start(),
                "fim_periodo": encontrado.end(),
                "texto_periodo": encontrado.group(0)
            }

    # Procura meses escritos por extenso
    meses_extenso = {
        "JANEIRO": 1,
        "FEVEREIRO": 2,
        "MARÇO": 3,
        "MARCO": 3,
        "ABRIL": 4,
        "MAIO": 5,
        "JUNHO": 6,
        "JULHO": 7,
        "AGOSTO": 8,
        "SETEMBRO": 9,
        "OUTUBRO": 10,
        "NOVEMBRO": 11,
        "DEZEMBRO": 12
    }

    padrao_extenso = re.compile(
        r"\b("
        + "|".join(meses_extenso.keys())
        + r")"
        r"(?:\s+|[/\-])"
        r"(\d{2}|\d{4})\b",
        re.IGNORECASE
    )

    encontrado = padrao_extenso.search(texto_original)

    if encontrado:

        mes_txt = encontrado.group(1).upper()
        ano_txt = encontrado.group(2)

        mes = meses_extenso.get(mes_txt)
        ano = converter_ano(ano_txt)

        if mes and ano:

            return {
                "mes": mes,
                "ano": ano,
                "inicio_periodo": encontrado.start(),
                "fim_periodo": encontrado.end(),
                "texto_periodo": encontrado.group(0)
            }

    return None


# ============================================================
# EXTRAIR NÚMEROS
# ============================================================

def extrair_numeros(texto):

    if not texto:
        return []

    padrao = re.compile(
        r"(?<![\w/])[-+]?\d{1,3}(?:\.\d{3})*(?:,\d+)?"
        r"(?![\w/])"
    )

    encontrados = padrao.findall(texto)

    numeros = []

    for item in encontrados:

        valor = converter_numero(item)

        if valor is not None:
            numeros.append(valor)

    return numeros


# ============================================================
# EXTRAIR NÚMEROS DEPOIS DO PERÍODO
# ============================================================

def extrair_numeros_depois_periodo(texto, periodo):

    if periodo is None:
        return []

    fim = periodo["fim_periodo"]

    # Tudo que vem depois de JAN/26, FEV/26 etc.
    texto_depois = texto[fim:]

    return extrair_numeros(texto_depois)


# ============================================================
# EXTRAIR NÚMEROS FORA DO PERÍODO
# ============================================================

def extrair_numeros_fora_periodo(texto, periodo):

    if periodo is None:
        return extrair_numeros(texto)

    inicio = periodo["inicio_periodo"]
    fim = periodo["fim_periodo"]

    texto_sem_periodo = (
        texto[:inicio]
        + " "
        + texto[fim:]
    )

    return extrair_numeros(texto_sem_periodo)


# ============================================================
# PARSER CEEE
# ============================================================

def extrair_ceee(texto):

    resultados = []

    linhas = texto.splitlines()

    for linha in linhas:

        linha_original = normalizar(linha)

        if not linha_original:
            continue

        periodo = encontrar_periodo(linha_original)

        if periodo is None:
            continue

        mes = periodo["mes"]
        ano = periodo["ano"]

        # ====================================================
        # REGRA PRINCIPAL CEEE
        #
        # O consumo é procurado SOMENTE depois do JAN/26,
        # FEV/26 etc.
        #
        # Isso evita pegar valores como:
        #
        # 10,97
        # 21
        # 02
        # 16,28
        #
        # que aparecem antes do período.
        # ====================================================

        numeros_depois = extrair_numeros_depois_periodo(
            linha_original,
            periodo
        )

        consumo = None
        dias = None

        if numeros_depois:

            # Primeiro número depois do período
            consumo = numeros_depois[0]

            # Se existir um segundo número plausível como dias,
            # utiliza-o.
            if len(numeros_depois) >= 2:

                candidatos_dias = [
                    n for n in numeros_depois[1:]
                    if 20 <= n <= 31
                ]

                if candidatos_dias:
                    dias = int(candidatos_dias[0])

        # Se não encontrou depois do período, tenta uma segunda
        # estratégia conservadora.
        if consumo is None:

            numeros = extrair_numeros_fora_periodo(
                linha_original,
                periodo
            )

            if numeros:

                # Retira possíveis valores de dias
                candidatos = [
                    n for n in numeros
                    if not (20 <= n <= 31)
                ]

                if candidatos:
                    consumo = candidatos[-1]

        if consumo is None:
            continue

        if dias is None:
            dias = DIAS_PADRAO.get(mes, 30)

        resultados.append({
            "Mes": NOME_MESES[mes],
            "Ano": ano,
            "Dias": dias,
            "Consumo_kWh": consumo,
            "Origem": "Extraído do PDF",
            "Confiança": "Alta",
            "PeriodoPDF": periodo["texto_periodo"],
            "NumerosDetectados": ", ".join(
                str(n).replace(".", ",")
                for n in numeros_depois
            ),
            "LinhaPDF": linha_original
        })

    return resultados


# ============================================================
# PARSER RGE
# ============================================================

def extrair_rge(texto):

    resultados = []

    linhas = texto.splitlines()

    for linha in linhas:

        linha_original = normalizar(linha)

        if not linha_original:
            continue

        periodo = encontrar_periodo(linha_original)

        if periodo is None:
            continue

        mes = periodo["mes"]
        ano = periodo["ano"]

        # Remove o mês/ano antes de procurar números.
        numeros = extrair_numeros_fora_periodo(
            linha_original,
            periodo
        )

        if not numeros:
            continue

        # ====================================================
        # RGE normalmente aparece em estrutura semelhante a:
        #
        # AGO 26 127 30
        # JUL 26 127 33
        #
        # Depois da remoção de AGO 26:
        #
        # 127 30
        #
        # O último número entre 20 e 35 tende a ser o número
        # de dias.
        # ====================================================

        dias = None
        indice_dias = None

        for i in range(len(numeros) - 1, -1, -1):

            numero = numeros[i]

            if 20 <= numero <= 35:

                dias = int(numero)
                indice_dias = i
                break

        if dias is not None:

            candidatos_consumo = numeros[:indice_dias]

            # Se não houver nada antes dos dias, tenta números
            # posteriores ao período.
            if not candidatos_consumo:
                candidatos_consumo = numeros[indice_dias + 1:]

        else:

            candidatos_consumo = numeros

        if not candidatos_consumo:
            continue

        # O primeiro candidato é normalmente o consumo.
        consumo = candidatos_consumo[0]

        if consumo is None:
            continue

        if dias is None:
            dias = DIAS_PADRAO.get(mes, 30)

        resultados.append({
            "Mes": NOME_MESES[mes],
            "Ano": ano,
            "Dias": dias,
            "Consumo_kWh": consumo,
            "Origem": "Extraído do PDF",
            "Confiança": "Alta",
            "PeriodoPDF": periodo["texto_periodo"],
            "NumerosDetectados": ", ".join(
                str(n).replace(".", ",")
                for n in numeros
            ),
            "LinhaPDF": linha_original
        })

    return resultados


# ============================================================
# PARSER GENÉRICO
# ============================================================

def extrair_generico(texto):

    resultados = []

    linhas = texto.splitlines()

    for linha in linhas:

        linha_original = normalizar(linha)

        if not linha_original:
            continue

        periodo = encontrar_periodo(linha_original)

        if periodo is None:
            continue

        mes = periodo["mes"]
        ano = periodo["ano"]

        numeros = extrair_numeros_fora_periodo(
            linha_original,
            periodo
        )

        if not numeros:
            continue

        # Procura consumo eliminando valores que parecem dias.
        candidatos = [
            n for n in numeros
            if n > 0
        ]

        if not candidatos:
            continue

        consumo = candidatos[0]

        dias = DIAS_PADRAO.get(mes, 30)

        resultados.append({
            "Mes": NOME_MESES[mes],
            "Ano": ano,
            "Dias": dias,
            "Consumo_kWh": consumo,
            "Origem": "Extraído do PDF",
            "Confiança": "Média",
            "PeriodoPDF": periodo["texto_periodo"],
            "NumerosDetectados": ", ".join(
                str(n).replace(".", ",")
                for n in numeros
            ),
            "LinhaPDF": linha_original
        })

    return resultados


# ============================================================
# CONSOLIDAR
# ============================================================

def consolidar(resultados):

    if not resultados:
        return pd.DataFrame()

    df = pd.DataFrame(resultados)

    df["MesNumero"] = df["Mes"].map({
        "Janeiro": 1,
        "Fevereiro": 2,
        "Março": 3,
        "Abril": 4,
        "Maio": 5,
        "Junho": 6,
        "Julho": 7,
        "Agosto": 8,
        "Setembro": 9,
        "Outubro": 10,
        "Novembro": 11,
        "Dezembro": 12
    })

    df["Data"] = pd.to_datetime(
        dict(
            year=df["Ano"],
            month=df["MesNumero"],
            day=1
        ),
        errors="coerce"
    )

    df = df.dropna(subset=["Data"])

    df = df.sort_values("Data")

    # Se houver duas linhas para o mesmo mês/ano,
    # mantém a última ocorrência.
    df = df.drop_duplicates(
        subset=["Ano", "MesNumero"],
        keep="last"
    )

    df = df.sort_values("Data").reset_index(drop=True)

    return df


# ============================================================
# MONTAR OS 12 MESES
# ============================================================

def montar_12_meses(df):

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    df = df.sort_values("Data")

    ultima_data = df["Data"].max()

    # Últimos 12 meses incluindo o mês mais recente
    datas = pd.date_range(
        end=ultima_data,
        periods=12,
        freq="MS"
    )

    registros = []

    valores_reais = df[
        df["Consumo_kWh"].notna()
    ]["Consumo_kWh"]

    if len(valores_reais) > 0:
        media = valores_reais.mean()
    else:
        media = 0

    for data in datas:

        ano = data.year
        mes_numero = data.month

        encontrado = df[
            (df["Ano"] == ano)
            &
            (df["MesNumero"] == mes_numero)
        ]

        if not encontrado.empty:

            linha = encontrado.iloc[-1]

            registros.append({
                "Mes": NOME_MESES[mes_numero],
                "Ano": ano,
                "Dias": int(
                    linha["Dias"]
                    if pd.notna(linha["Dias"])
                    else DIAS_PADRAO[mes_numero]
                ),
                "Consumo_kWh": linha["Consumo_kWh"],
                "Origem": linha["Origem"],
                "Confiança": linha["Confiança"]
            })

        else:

            registros.append({
                "Mes": NOME_MESES[mes_numero],
                "Ano": ano,
                "Dias": DIAS_PADRAO[mes_numero],
                "Consumo_kWh": media,
                "Origem": "Imputado pela média",
                "Confiança": "Imputado"
            })

    return pd.DataFrame(registros)


# ============================================================
# INTERFACE
# ============================================================

st.title("☀️ Extrator de Consumo de Energia - Faturas CEEE")

st.markdown(
    """
Envie uma ou mais faturas de energia em PDF para extrair
o histórico mensal de consumo em kWh.
"""
)

arquivo = st.file_uploader(
    "Selecione o arquivo PDF da fatura",
    type=["pdf"]
)


if arquivo is not None:

    st.success(f"Arquivo carregado: {arquivo.name}")

    # ========================================================
    # EXTRAÇÃO
    # ========================================================

    texto = extrair_pdf(arquivo)

    if not texto:

        st.error(
            "Não foi possível extrair texto do PDF."
        )

        st.stop()

    # ========================================================
    # DETECTAR CONCESSIONÁRIA
    # ========================================================

    concessionaria = detectar_concessionaria(texto)

    st.info(
        f"Concessionária identificada: **{concessionaria}**"
    )

    # ========================================================
    # PARSER
    # ========================================================

    if concessionaria == "CEEE":

        resultados = extrair_ceee(texto)

    elif concessionaria == "RGE":

        resultados = extrair_rge(texto)

    else:

        resultados = extrair_generico(texto)

    # ========================================================
    # CONSOLIDAR
    # ========================================================

    df_extraido = consolidar(resultados)

    if df_extraido.empty:

        st.warning(
            "Nenhum período mensal de consumo foi identificado."
        )

    else:

        # ====================================================
        # MOSTRAR DIAGNÓSTICO DA EXTRAÇÃO
        # ====================================================

        with st.expander(
            "🔎 Diagnóstico detalhado da extração"
        ):

            colunas_diag = [
                "Ano",
                "Mes",
                "PeriodoPDF",
                "Consumo_kWh",
                "Dias",
                "NumerosDetectados",
                "LinhaPDF"
            ]

            st.dataframe(
                df_extraido[colunas_diag],
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # ÚLTIMOS 12 MESES
        # ====================================================

        df_12 = montar_12_meses(
            df_extraido
        )

        st.subheader(
            "📊 Consumo dos últimos 12 meses"
        )

        # ====================================================
        # EDIÇÃO MANUAL
        # ====================================================

        df_editado = st.data_editor(
            df_12,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Consumo_kWh": st.column_config.NumberColumn(
                    "Consumo (kWh)",
                    min_value=0,
                    format="%.2f"
                ),
                "Dias": st.column_config.NumberColumn(
                    "Dias",
                    min_value=1,
                    max_value=31,
                    step=1
                )
            }
        )

        # ====================================================
        # ESTATÍSTICAS
        # ====================================================

        consumo_total = df_editado[
            "Consumo_kWh"
        ].sum()

        consumo_medio = df_editado[
            "Consumo_kWh"
        ].mean()

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Consumo anual",
                f"{consumo_total:,.2f} kWh".replace(
                    ",", "X"
                ).replace(
                    ".", ","
                ).replace(
                    "X", "."
                )
            )

        with col2:

            st.metric(
                "Consumo médio mensal",
                f"{consumo_medio:,.2f} kWh".replace(
                    ",", "X"
                ).replace(
                    ".", ","
                ).replace(
                    "X", "."
                )
            )

        # ====================================================
        # CSV
        # ====================================================

        csv_bytes = df_editado.to_csv(
            index=False,
            decimal=","
        ).encode("utf-8-sig")

        st.download_button(
            label="⬇️ Baixar CSV para Power BI",
            data=csv_bytes,
            file_name="consumo_12_meses.csv",
            mime="text/csv"
        )

        # ====================================================
        # TEXTO BRUTO
        # ====================================================

        with st.expander(
            "📄 Texto bruto extraído do PDF"
        ):

            st.text_area(
                "Texto",
                texto,
                height=500
            )
