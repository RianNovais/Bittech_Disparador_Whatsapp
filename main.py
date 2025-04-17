import flet as ft
import pandas as pd
import threading
import datetime
from web_interactor import execute_numbers


class WhatsAppSenderUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Disparador de WhatsApp Bittech"
        self.page.padding = 15
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 700
        self.page.window.height = 780
        self.page.window.center()
        self.page.window.maximizable = False
        self.page.update()

        self.df = None
        self.sender_name = ""

        # Template base com marcadores de gênero e saudação
        self.message_template = """$SAUDACAO$, *$NOME_PESSOA$*, tudo bem?

Meu nome é *$NOME_REMETENTE$*, sou $GENERO_ESTAGIARIO$ Jurídic$GENERO_O_A$ do *INSTITUTO ABRACE*, somos especializados na defesa do trabalhador, e temos como grande objetivo e propósito, poder dar a oportunidade aos trabalhadores a terem acesso à justiça e aos advogados de forma gratuita, sabemos o quão importante é fornecer esse primeiro atendimento.

Nosso contato é referente ao seu vínculo com a empresa *$EMPRESA$*, recebemos muitos formulários e indicações pelo site, e também, do Sindicato, quando há muitas demissões contestadas de certas empresas, e será um grande prazer, poder auxiliar.

Lembrando que é de forma *COMPLETAMENTE GRATUITA*, seria apenas para possibilitar um primeiro contato, e analisarmos se há necessidade de um direcionamento para escritórios trabalhistas e se as diretrizes das convenções coletivas foram respeitadas durante o seu vínculo. Caso tenha interesse, manda um *SIM* que entraremos em contato, muito obrigado e tenha um excelente dia."""

        # Componentes da interface
        self.file_picker = ft.FilePicker(on_result=self.on_file_selected)
        self.page.overlay.append(self.file_picker)

        self.sender_name_field = ft.TextField(
            label="Nome do Remetente",
            width=300,
            on_change=self.on_sender_name_change,  # Modificado aqui para usar um método específico
        )

        # Adicionar seleção de gênero com Radio Buttons
        self.gender_text = ft.Text("Gênero:", size=14)
        self.gender_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="M", label="Masculino"),
                ft.Radio(value="F", label="Feminino"),
            ]),
            value="F",  # Valor padrão (Feminino)
            on_change=self.update_message_preview
        )

        self.upload_button = ft.ElevatedButton(
            "Selecionar Planilha",
            icon=ft.icons.UPLOAD_FILE,
            on_click=lambda _: self.file_picker.pick_files(
                allowed_extensions=["xlsx"]
            )
        )

        self.file_path_text = ft.Text("Nenhum arquivo selecionado", size=12, color=ft.colors.GREY)
        self.file_stats_text = ft.Text("", size=12, color=ft.colors.BLACK)

        # Inicializar o template com o gênero padrão (feminino)
        self.update_message_preview_initial()

        self.message_preview = ft.TextField(
            label="Prévia da Mensagem",
            multiline=True,
            min_lines=8,
            max_lines=8,
            read_only=True,
            width=550,
            value=self.message_template
        )

        self.progress_bar = ft.ProgressBar(width=300, visible=False)
        self.status_text = ft.Text("", size=12)

        # Adicionando contador para mostrar progresso
        self.progress_counter = ft.Text("0/0", size=14, weight=ft.FontWeight.BOLD)

        self.send_button = ft.ElevatedButton(
            "Enviar Mensagens",
            icon=ft.icons.SEND,
            on_click=self.start_sending_messages,
            disabled=True
        )

        self.cancel_button = ft.ElevatedButton(
            "Cancelar",
            icon=ft.icons.CANCEL,
            on_click=self.cancel_sending,
            disabled=True,
            visible=False
        )

        # Flag para controlar o cancelamento
        self.cancel_requested = False

        # Thread para execução em segundo plano
        self.sending_thread = None

        # Layout da interface

        self.page.add(
            ft.Container(
                content=ft.Text("Disparador de WhatsApp Bittech", size=20, weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(bottom=5)
            ),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Text("1. Selecione uma planilha com colunas: Nome, Telefone e Empresa", size=14),
                margin=ft.margin.only(top=5, bottom=5)
            ),
            ft.Row([self.upload_button], wrap=True),
            self.file_path_text,
            self.file_stats_text,
            ft.Divider(height=1),
            ft.Container(
                content=ft.Text("2. Digite seu nome (remetente)", size=14),
                margin=ft.margin.only(top=5, bottom=5)
            ),
            ft.Row([
                ft.Container(
                    content=self.sender_name_field,
                    margin=ft.margin.only(right=20),
                    expand=True
                ),
                ft.Container(
                    content=ft.Column([
                        self.gender_text,
                        ft.Container(
                            content=self.gender_radio,
                            padding=ft.padding.only(top=0)  # Reduzi o padding para 0
                        ),
                    ]),
                    alignment=ft.alignment.center_left,
                    margin=ft.margin.only(top=-10)  # Adicionei uma margem negativa para mover para cima
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Text("3. Prévia da mensagem", size=14),
                margin=ft.margin.only(top=5, bottom=5)
            ),
            ft.Container(
                content=self.message_preview,
                margin=ft.margin.only(bottom=5)
            ),
            ft.Divider(height=1),
            ft.Row([self.send_button, self.cancel_button]),
            ft.Row([self.progress_bar, self.progress_counter], alignment=ft.MainAxisAlignment.CENTER),
            self.status_text
        )

    def get_time_greeting(self):
        """Retorna a saudação adequada com base na hora atual"""
        current_hour = datetime.datetime.now().hour

        if 5 <= current_hour < 12:
            return "Bom dia"
        elif 12 <= current_hour < 18:
            return "Boa tarde"
        else:  # 18-23 e 0-4
            return "Boa noite"

    def update_message_preview_initial(self):
        """Inicializa o template de mensagem com base no gênero padrão (feminino) e hora atual"""
        # Determinar as terminações de gênero apropriadas (feminino por padrão)
        replacements = {
            "$GENERO_ESTAGIARIO$": "Estagiária",
            "$GENERO_O_A$": "a",
            "$SAUDACAO$": self.get_time_greeting(),
            "$NOME_REMETENTE$": self.sender_name_field.value or "$NOME_REMETENTE$"  # Mantém o placeholder se vazio
        }

        # Substituir os marcadores no template
        message_updated = self.message_template
        for placeholder, value in replacements.items():
            message_updated = message_updated.replace(placeholder, value)

        self.message_template = message_updated

    def on_sender_name_change(self, e):
        """Método específico para lidar com mudanças no nome do remetente"""
        # Atualiza a variável de instância com o novo valor
        self.sender_name = self.sender_name_field.value

        # Atualiza a prévia da mensagem
        self.update_message_preview()

        # Verifica se o formulário está válido
        self.check_form_valid()

    def update_message_preview(self, e=None):
        """Atualiza a prévia da mensagem com base no gênero selecionado e hora atual"""
        # Template atualizado com quebras de linha preservadas, mas sem espaços extras
        base_message = """$SAUDACAO$, *$NOME_PESSOA$*, tudo bem?

Meu nome é *$NOME_REMETENTE$*, sou $GENERO_ESTAGIARIO$ Jurídic$GENERO_O_A$ do *INSTITUTO ABRACE*, somos especializados na defesa do trabalhador, e temos como grande objetivo e propósito, poder dar a oportunidade aos trabalhadores a terem acesso à justiça e aos advogados de forma gratuita, sabemos o quão importante é fornecer esse primeiro atendimento.

Nosso contato é referente ao seu vínculo com a empresa *$EMPRESA$*, recebemos muitos formulários e indicações pelo site, e também, do Sindicato, quando há muitas demissões contestadas de certas empresas, e será um grande prazer, poder auxiliar.

Lembrando que é de forma *COMPLETAMENTE GRATUITA*, seria apenas para possibilitar um primeiro contato, e analisarmos se há necessidade de um direcionamento para escritórios trabalhistas e se as diretrizes das convenções coletivas foram respeitadas durante o seu vínculo. Caso tenha interesse, manda um *SIM* que entraremos em contato, muito obrigado e tenha um excelente dia."""

        # Obtém o nome do remetente do campo de texto
        sender_name = self.sender_name_field.value

        # Determinar as terminações de gênero apropriadas
        if self.gender_radio.value == "M":
            replacements = {
                "$GENERO_ESTAGIARIO$": "Estagiário",
                "$GENERO_O_A$": "o",
                "$SAUDACAO$": self.get_time_greeting()
            }
        else:  # "F" ou vazio (default para feminino)
            replacements = {
                "$GENERO_ESTAGIARIO$": "Estagiária",
                "$GENERO_O_A$": "a",
                "$SAUDACAO$": self.get_time_greeting()
            }

        # Substituir os marcadores no template
        preview_message = base_message
        for placeholder, value in replacements.items():
            preview_message = preview_message.replace(placeholder, value)

        # Adicionar o nome do remetente se fornecido
        if sender_name and sender_name.strip():
            preview_message = preview_message.replace("$NOME_REMETENTE$", sender_name.strip().title())

        # Atualizar o template e a prévia
        self.message_template = base_message  # O template original permanece com os marcadores
        self.message_preview.value = preview_message  # A prévia mostra os placeholders
        self.page.update()

    def check_form_valid(self, e=None):
        """Verifica se o formulário está válido para habilitar o botão de envio"""
        is_valid = self.df is not None and self.sender_name_field.value and self.sender_name_field.value.strip() != ""
        self.send_button.disabled = not is_valid
        self.page.update()

    def on_file_selected(self, e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            self.file_path_text.value = f"Arquivo selecionado: {e.files[0].name}"

            # Carregando o arquivo
            try:
                self.df = pd.read_excel(file_path)
                self.df.columns = [col.strip().title() for col in self.df.columns]
                # Verificando se tem as colunas necessárias
                required_columns = ['Nome', 'Telefone', 'Empresa']
                if not all(col in self.df.columns for col in required_columns):
                    self.file_path_text.value = "Erro: A planilha não contém todas as colunas necessárias (Nome, Telefone, Empresa)"
                    self.file_path_text.color = ft.colors.RED
                    self.file_stats_text.value = ""
                    self.df = None  # Reseta o dataframe inválido
                    self.check_form_valid()  # Verifica o estado do formulário
                    self.page.update()
                    return

                # Mostrar estatísticas
                self.file_stats_text.value = f"Total de registros: {len(self.df)}"
                self.file_stats_text.color = ft.colors.BLACK

                # Verifica se o formulário está válido (arquivo e nome do remetente)
                self.check_form_valid()
            except Exception as ex:
                self.file_path_text.value = f"Erro ao ler o arquivo: {str(ex)}"
                self.file_path_text.color = ft.colors.RED
                self.file_stats_text.value = ""
                self.df = None  # Reseta o dataframe em caso de erro
                self.check_form_valid()  # Verifica o estado do formulário

        self.page.update()

    def replace_message_placeholders(self, message_template, replacements):
        personalized_message = message_template

        for placeholder, value in replacements.items():
            placeholder_tag = f"${placeholder}$"
            personalized_message = personalized_message.replace(placeholder_tag, str(value))

        return personalized_message

    def start_sending_messages(self, e):
        """Inicia o processo de envio em uma thread separada"""
        if self.df is None or len(self.df) == 0:
            self.status_text.value = "Nenhum dado para enviar!"
            self.status_text.color = ft.colors.RED
            self.page.update()
            return

        if not self.sender_name_field.value or self.sender_name_field.value.strip() == "":
            self.status_text.value = "Digite o nome do remetente!"
            self.status_text.color = ft.colors.RED
            self.page.update()
            return

        # Desativa o botão de enviar e ativa o botão de cancelar
        self.send_button.disabled = True
        self.cancel_button.visible = True
        self.cancel_button.disabled = False
        self.progress_bar.value = 0
        self.progress_bar.visible = True
        self.status_text.value = "Preparando para enviar mensagens..."
        self.status_text.color = ft.colors.BLUE
        self.progress_counter.value = f"0/{len(self.df)}"
        self.cancel_requested = False
        self.page.update()

        # Inicia o envio em uma thread separada
        self.sending_thread = threading.Thread(target=self.send_messages_thread)
        self.sending_thread.daemon = True
        self.sending_thread.start()

    def cancel_sending(self, e):
        """Cancela o envio das mensagens"""
        self.cancel_requested = True
        self.cancel_button.disabled = True
        self.status_text.value = "Cancelando... aguarde a finalização do envio atual."
        self.status_text.color = ft.colors.ORANGE
        self.page.update()

    def update_progress(self, atual, total, status, success=True):
        """Atualiza o progresso na interface usando threading.Timer"""
        # Calcula o progresso de 0 a 1
        progress = atual / total if total > 0 else 0

        # Atualiza a UI na thread principal
        self.progress_bar.value = progress
        self.progress_counter.value = f"{atual}/{total}"
        self.status_text.value = status
        self.status_text.color = ft.colors.GREEN if success else ft.colors.RED
        self.page.update()

    def send_messages_thread(self):
        """Função que executa o envio das mensagens em uma thread separada"""
        try:
            # Prepara os contatos e mensagens
            contatos = []

            # Obtém a saudação atual no momento do envio
            greeting = self.get_time_greeting()

            # Define os valores de gênero baseado na seleção do rádio
            if self.gender_radio.value == "M":
                genero_estagiario = "Estagiário"
                genero_o_a = "o"
            else:  # "F" ou vazio (default para feminino)
                genero_estagiario = "Estagiária"
                genero_o_a = "a"

            for index, row in self.df.iterrows():
                if self.cancel_requested:
                    self.reset_ui_after_sending()
                    break

                if all(field in row and not pd.isna(row[field]) for field in ['Nome', 'Telefone', 'Empresa']):
                    nome = row['Nome'].strip().title()
                    telefone = row['Telefone']
                    empresa = row['Empresa'].strip().title()

                    replacements = {
                        "NOME_PESSOA": nome,
                        "NOME_REMETENTE": self.sender_name_field.value.strip().title(),
                        "EMPRESA": empresa,
                        "SAUDACAO": greeting,
                        "GENERO_ESTAGIARIO": genero_estagiario,
                        "GENERO_O_A": genero_o_a
                    }

                    message = self.replace_message_placeholders(self.message_template, replacements)

                    contatos.append({
                        'nome': nome,
                        'telefone': telefone,
                        'mensagem': message
                    })

            if self.cancel_requested:
                self.reset_ui_after_sending()
                return

            # Executa o envio das mensagens
            resultado = execute_numbers(contatos, self.update_progress)

            # Atualiza a interface com o resultado final
            self.status_text.value = f"Envio concluído! Enviadas: {resultado['enviadas']}, Falhas: {resultado['falhas']}"
            self.status_text.color = ft.colors.GREEN
            self.reset_ui_after_sending()

        except Exception as ex:
            self.status_text.value = f"Erro durante o envio: {str(ex)}"
            self.status_text.color = ft.colors.RED
            self.reset_ui_after_sending()

    def reset_ui_after_sending(self):
        """Reset da UI após o envio"""
        self.send_button.disabled = False
        self.cancel_button.visible = False
        self.progress_bar.visible = False
        self.check_form_valid()  # Verifica novamente após concluir operação
        self.page.update()


def main(page: ft.Page):
    app = WhatsAppSenderUI(page)


# Executar a aplicação
if __name__ == "__main__":
    ft.app(target=main)