import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://qfhlhyqagrogvhhkpzns.supabase.co"
SUPABASE_KEY = "sb_publishable_KczM4KqIBHHf-K4Chsgbyg_ojJnNW-J"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- LISTA DE MESTRES ---
MESTRES_AUTORIZADOS = ["controletg06009@gmail.com", "outro-mestre@aqui.com", "chefe@aqui.com"] 

st.set_page_config(page_title="Relação dos Convidados", layout="wide")

if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# --- TELA DE ACESSO (LOGIN/CADASTRO) ---
if not st.session_state.usuario:
    st.title("Relação dos Convidados")
    
    aba_login, aba_cadastro = st.tabs(["Login", "Criar Conta"])

    with aba_login:
        email_log = st.text_input("E-mail", key="email_log")
        senha_log = st.text_input("Senha", type="password", key="senha_log")
        
        col_entrar, col_esqueci = st.columns(2)
        
        if col_entrar.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email_log, "password": senha_log})
                st.session_state.usuario = res.user.email
                st.success("Autenticado! Carregando...")
                st.rerun()
            except Exception as e:
                st.error("E-mail ou senha incorretos.")

        if col_esqueci.button("Esqueci a senha"):
            if email_log:
                try:
                    supabase.auth.reset_password_for_email(email_log)
                    st.info(f"Um link de redefinição foi enviado para {email_log}")
                except Exception as e:
                    st.error(f"Erro ao enviar e-mail: {e}")
            else:
                st.warning("Digite seu e-mail acima para recuperar a senha.")

    with aba_cadastro:
        email_cad = st.text_input("Novo E-mail", key="email_cad")
        senha_cad = st.text_input("Nova Senha (mín. 6 caracteres)", type="password", key="senha_cad")
        if st.button("Cadastrar Novo Usuário"):
            try:
                supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                st.success("Conta criada com sucesso! Agora você pode fazer o login na aba ao lado.")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

# --- ÁREA LOGADA (SISTEMA PRINCIPAL) ---
else:
    # Barra lateral com botão de sair
    st.sidebar.write(f"👤 Logado como: **{st.session_state.usuario}**")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.usuario = None
        st.rerun()

    st.title("Relação dos Convidados")
    
    # Verificação de nível de acesso para as abas
    if st.session_state.usuario in MESTRES_AUTORIZADOS:
        aba1, aba2, aba3 = st.tabs(["📥 Entrada", "📤 Saída", "📊 Relatório Mestre"])
    else:
        aba1, aba2 = st.tabs(["📥 Entrada", "📤 Saída"])
        aba3 = None

    # --- ABA 1: REGISTRAR ENTRADA ---
    with aba1:
        st.header("Registrar Novo Convidado")
        with st.form("form_entrada", clear_on_submit=True):
            nome = st.text_input("Nome do Convidado")
            cpf = st.text_input("CPF")
            if st.form_submit_button("Confirmar Entrada"):
                if nome and cpf:
                    dados = {
                        "nome_convidado": nome,
                        "cpf": cpf,
                        "guardadodia_email": st.session_state.usuario
                    }
                    supabase.table("registros").insert(dados).execute()
                    st.success(f"✅ Entrada de {nome} registrada!")
                else:
                    st.warning("Preencha todos os campos!")

    # --- ABA 2: REGISTRAR SAÍDA ---
    with aba2:
        st.header("Pessoas no Alojamento")
        try:
            query = supabase.table("registros").select("*").is_("data_saida", "null").execute()
            df_presentes = pd.DataFrame(query.data)

            if not df_presentes.empty:
                for index, row in df_presentes.iterrows():
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        col1.write(f"📌 **{row['nome_convidado']}** | CPF: {row['cpf']}")
                        if col2.button("Dar Saída", key=row['id']):
                            hora_atual = datetime.now().isoformat()
                            supabase.table("registros").update({"data_saida": hora_atual}).eq("id", row['id']).execute()
                            st.toast(f"Saída de {row['nome_convidado']} confirmada!")
                            st.rerun()
            else:
                st.info("Não há convidados no alojamento no momento.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    # --- ABA 3: RELATÓRIOS (APENAS MESTRE) ---
    if aba3:
        with aba3:
            st.header("Histórico de Movimentação")
            try:
                todos = supabase.table("registros").select("*").order("data_entrada", desc=True).execute()
                df_total = pd.DataFrame(todos.data)

                if not df_total.empty:
                    # Formatação das datas para o padrão brasileiro
                    df_total['data_entrada'] = pd.to_datetime(df_total['data_entrada']).dt.strftime('%d/%m/%Y %H:%M')
                    df_total['data_saida'] = pd.to_datetime(df_total['data_saida']).dt.strftime('%d/%m/%Y %H:%M')
                    
                    st.dataframe(df_total, use_container_width=True)
                    
                    # Botão de exportar para Excel (CSV formatado)
                    csv = df_total.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                    
                    st.download_button(
                        label="📥 Baixar Relatório para Excel",
                        data=csv,
                        file_name=f'relatorio_{datetime.now().strftime("%d_%m_%Y")}.csv',
                        mime='text/csv',
                    )
                else:
                    st.write("Nenhum dado encontrado no banco de dados.")
            except Exception as e:
                st.error(f"Erro ao carregar relatório: {e}")