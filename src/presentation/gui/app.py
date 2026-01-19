"""
BOTLink Main Application - Flet GUI with Real Backend Integration

Connects the UI with the actual bot automation.
"""

import flet as ft
import asyncio
import threading
from datetime import datetime
from pathlib import Path


# Colors
PRIMARY = "#6366f1"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
ERROR = "#ef4444"
DARK_BG = "#0f172a"
DARK_CARD = "#1e293b"
LIGHT_BG = "#f8fafc"
LIGHT_CARD = "#e2e8f0"


def build_app(page: ft.Page) -> None:
    """Build the main BOTLink application with real backend."""
    
    # === PAGE CONFIGURATION ===
    page.title = "BOTLink - Automação Cognitiva de Candidaturas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = DARK_BG
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    
    # === STATE ===
    state = {
        "keywords": [],
        "location": "",
        "remote_only": False,
        "name": "",
        "email": "",
        "phone": "",
        "resume": "",
        "skills": "",
        "bio": "",
        "is_running": False,
        "applications_today": 0,
        "bot_task": None,
        "applied_jobs": [],  # List of applied jobs for the jobs log
    }
    
    # === LOG SYSTEM ===
    log_column = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
    
    # === JOBS LOG SYSTEM (separate log for applied jobs) ===
    jobs_log_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
    
    def add_job_to_log(job_title: str, company: str, url: str, success: bool, message: str = ""):
        """Add a job application to the jobs log."""
        status_icon = "✅" if success else "❌"
        status_color = SUCCESS if success else ERROR
        
        job_entry = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(status_icon, size=14),
                    ft.Text(job_title[:40] + "..." if len(job_title) > 40 else job_title, 
                           size=12, weight=ft.FontWeight.BOLD, color=status_color),
                ], spacing=4),
                ft.Text(f"🏢 {company}", size=11, color=ft.Colors.GREY_400),
                ft.TextButton(
                    content=ft.Text(f"🔗 Abrir vaga", size=10, color=PRIMARY),
                    url=url,
                    tooltip=url,
                ),
                ft.Text(message, size=10, color=ft.Colors.GREY_500, italic=True) if message else ft.Container(),
            ], spacing=2),
            bgcolor=DARK_BG,
            border_radius=8,
            padding=8,
            margin=ft.margin.only(bottom=4),
        )
        
        jobs_log_column.controls.insert(0, job_entry)  # Add at the top
        
        # Store in state for persistence
        state["applied_jobs"].append({
            "title": job_title,
            "company": company,
            "url": url,
            "success": success,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        
        try:
            page.update()
        except:
            pass
    
    def add_log(message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {"info": ft.Colors.WHITE, "success": SUCCESS, "warning": WARNING, "error": ERROR}
        log_column.controls.append(
            ft.Text(f"[{timestamp}] {message}", size=11, color=color_map.get(level, ft.Colors.WHITE))
        )
        if len(log_column.controls) > 100:
            log_column.controls = log_column.controls[-100:]
        try:
            page.update()
        except Exception:
            pass
    
    # === BOT RUNNER ===
    async def run_bot_automation():
        """Run the actual bot automation with separate browser window."""
        browser = None
        try:
            add_log("🔧 Inicializando componentes...", "info")
            
            # Import here to avoid circular imports
            from src.config.settings import Settings
            from src.infrastructure.browser.camoufox_adapter import CamoufoxAdapter
            from src.infrastructure.browser.cookie_manager import CookieManager
            
            settings = Settings()
            auth_path = Path("debug_data/auth.json")
            cookie_manager = CookieManager(auth_path)
            browser = CamoufoxAdapter(settings, cookie_manager)
            
            add_log("🌐 Abrindo navegador...", "info")
            await browser.start()
            add_log("✅ Navegador aberto!", "success")
            
            # Check if logged in to LinkedIn (first check navigates to LinkedIn)
            add_log("🔍 Verificando login no LinkedIn...", "info")
            is_logged = await browser.check_linkedin_logged_in(navigate=True)
            
            if not is_logged:
                add_log("🔐 Você não está logado no LinkedIn.", "warning")
                add_log("👉 Faça login na janela que abriu!", "warning")
                add_log("⏳ Aguardando você fazer login...", "info")
                
                # Wait for user to login (check every 10 seconds, WITHOUT refreshing!)
                login_timeout = 180  # 3 minutes
                elapsed = 0
                while elapsed < login_timeout and state["is_running"]:
                    await asyncio.sleep(10)
                    elapsed += 10
                    # Use navigate=False to avoid refreshing the page while user is logging in!
                    is_logged = await browser.check_linkedin_logged_in(navigate=False)
                    if is_logged:
                        break
                    if elapsed % 30 == 0:  # Log every 30 seconds to reduce spam
                        add_log(f"⏳ Aguardando login... ({elapsed}s)", "info")
                
                if not is_logged:
                    add_log("❌ Tempo esgotado. Faça login e tente novamente.", "error")
                    await browser.stop()
                    return
            
            add_log("✅ LinkedIn logado! Sessão salva.", "success")
            add_log("💾 Próxima vez, o login será automático!", "success")
            
            # Search for jobs
            if state["keywords"]:
                keywords_str = ", ".join(state["keywords"])
                add_log(f"🔎 Buscando vagas: {keywords_str}", "info")
                
                search_url = await browser.search_jobs(
                    keywords=state["keywords"],
                    location=state["location"],
                    remote_only=state["remote_only"],
                )
                add_log("✅ Página de vagas carregada!", "success")
                
                # === JOB APPLICATION LOOP ===
                applied_count = 0
                skipped_count = 0
                failed_count = 0
                daily_limit = 50
                
                page_number = 1
                max_pages = 10
                
                while state["is_running"] and applied_count < daily_limit and page_number <= max_pages:
                    add_log(f"📄 Analisando página {page_number}...", "info")
                    
                    # Wait a bit more for page to fully load
                    await asyncio.sleep(3)
                    
                    # Get all jobs from current page
                    jobs = await browser.get_job_listings()
                    
                    if not jobs:
                        add_log("⚠️ Nenhuma vaga encontrada. Tentando recarregar...", "warning")
                        # Save screenshot for debug
                        try:
                            await browser.take_screenshot(Path("data/debug_screenshot.png"))
                            add_log("📸 Screenshot salvo em data/debug_screenshot.png", "info")
                        except:
                            pass
                        # Try scrolling the page to load content
                        await browser.scroll_job_list()
                        await asyncio.sleep(2)
                        jobs = await browser.get_job_listings()
                        
                        if not jobs:
                            add_log("⚠️ Ainda sem vagas. Verifique os filtros de busca.", "warning")
                            break
                    
                    add_log(f"📋 Encontradas {len(jobs)} vagas nesta página", "info")
                    
                    # Filter out already applied jobs
                    new_jobs = [j for j in jobs if not j['already_applied']]
                    already_applied_count = len(jobs) - len(new_jobs)
                    
                    if already_applied_count > 0:
                        add_log(f"⏭️ Pulando {already_applied_count} vagas já candidatadas", "info")
                    
                    if not new_jobs:
                        add_log("ℹ️ Todas as vagas desta página já foram aplicadas.", "info")
                        # Try next page
                        if await browser.go_to_next_page():
                            page_number += 1
                            continue
                        else:
                            break
                    
                    # Process each new job
                    for job in new_jobs:
                        if not state["is_running"]:
                            break
                        if applied_count >= daily_limit:
                            add_log(f"🎯 Limite diário atingido ({daily_limit} candidaturas)", "warning")
                            break
                        
                        job_title = job['title'][:35] + "..." if len(job['title']) > 35 else job['title']
                        job_company = job['company'][:25] + "..." if len(job['company']) > 25 else job['company']
                        job_url = job['url']
                        
                        add_log(f"👀 Vaga: {job_title} @ {job_company}", "info")
                        
                        # Click on the job to open details
                        if not await browser.click_job_card(job):
                            add_log(f"  ⚠️ Não foi possível abrir a vaga", "warning")
                            failed_count += 1
                            continue
                        
                        # Try to apply
                        result = await browser.apply_to_job(log_callback=add_log)
                        
                        if result['success']:
                            applied_count += 1
                            state["applications_today"] = applied_count
                            add_log(f"  ✅ SUCESSO! Candidatura enviada", "success")
                            # Add to jobs log
                            add_job_to_log(
                                job_title=job['title'],
                                company=job['company'],
                                url=job_url,
                                success=True,
                                message="Candidatura enviada com sucesso"
                            )
                            # Update progress
                            progress_bar.value = applied_count / daily_limit
                            progress_text.value = f"{applied_count} / {daily_limit} candidaturas hoje"
                            try:
                                page.update()
                            except:
                                pass
                        else:
                            if 'Já candidatado' in result['message']:
                                skipped_count += 1
                                add_log(f"  ⏭️ Já candidatado anteriormente", "info")
                            else:
                                failed_count += 1
                                add_log(f"  ❌ Falha: {result['message']}", "error")
                                # Add failed job to log
                                add_job_to_log(
                                    job_title=job['title'],
                                    company=job['company'],
                                    url=job_url,
                                    success=False,
                                    message=result['message']
                                )
                        
                        # Human-like delay between applications
                        await asyncio.sleep(3)
                    
                    # Try to go to next page
                    if state["is_running"] and applied_count < daily_limit:
                        if await browser.go_to_next_page():
                            page_number += 1
                            await asyncio.sleep(2)
                        else:
                            add_log("📄 Não há mais páginas de resultados.", "info")
                            break
                
                # Summary
                add_log("", "info")
                add_log("═══════════════════════════════════════", "info")
                add_log("📊 RESUMO DA SESSÃO", "info")
                add_log(f"  ✅ Candidaturas enviadas: {applied_count}", "success")
                add_log(f"  ⏭️ Vagas já aplicadas (puladas): {skipped_count}", "info")
                add_log(f"  ❌ Falhas: {failed_count}", "error" if failed_count > 0 else "info")
                add_log("═══════════════════════════════════════", "info")
            
            # Cleanup
            add_log("🔄 Fechando navegador...", "info")
            await browser.stop()
            add_log("✅ Navegador fechado.", "success")
            
        except Exception as e:
            add_log(f"❌ Erro: {str(e)}", "error")
            import traceback
            traceback.print_exc()
            if browser:
                try:
                    await browser.stop()
                except:
                    pass
    
    def run_bot_in_thread():
        """Run bot in a separate thread with its own event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_bot_automation())
        finally:
            loop.close()
        state["is_running"] = False
        status_indicator.bgcolor = ft.Colors.GREY
        status_text.value = "Parado"
        try:
            page.update()
        except Exception:
            pass
    
    # === FE-01: JOB PANEL ===
    keywords_row = ft.Row(wrap=True, spacing=4)
    keyword_field = ft.TextField(
        label="Cargo / Palavra-chave",
        hint_text="Ex: Python Developer",
        expand=True,
        border_radius=8,
    )
    
    def add_keyword_click(e):
        kw = keyword_field.value.strip() if keyword_field.value else ""
        if kw and kw not in state["keywords"]:
            state["keywords"].append(kw)
            update_keywords_display()
            keyword_field.value = ""
            add_log(f"➕ Keyword adicionada: {kw}", "success")
        page.update()
    
    def remove_keyword(kw):
        def handler(e):
            if kw in state["keywords"]:
                state["keywords"].remove(kw)
                update_keywords_display()
                add_log(f"➖ Keyword removida: {kw}", "info")
            page.update()
        return handler
    
    def update_keywords_display():
        keywords_row.controls = [
            ft.Container(
                content=ft.Row([
                    ft.Text(kw, size=12, color=ft.Colors.WHITE),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=14,
                        icon_color=ft.Colors.WHITE,
                        on_click=remove_keyword(kw),
                    ),
                ], tight=True, spacing=0),
                bgcolor=PRIMARY,
                border_radius=16,
                padding=ft.padding.only(left=12, right=2, top=2, bottom=2),
            )
            for kw in state["keywords"]
        ]
    
    location_field = ft.TextField(
        label="Localização",
        hint_text="Ex: São Paulo, Brasil",
        border_radius=8,
        on_change=lambda e: state.update({"location": e.control.value or ""}),
    )
    
    remote_switch = ft.Switch(
        label="Apenas Remoto",
        value=False,
        on_change=lambda e: state.update({"remote_only": e.control.value}),
    )
    
    job_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.WORK, color=PRIMARY),
                ft.Text("Configuração de Vagas", size=16, weight=ft.FontWeight.BOLD),
            ]),
            ft.Divider(height=1),
            ft.Row([
                keyword_field,
                ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=SUCCESS, on_click=add_keyword_click),
            ]),
            keywords_row,
            location_field,
            remote_switch,
        ], spacing=10),
        bgcolor=DARK_CARD,
        border_radius=12,
        padding=16,
    )
    
    # === INSTRUÇÃO (painel informativo) ===
    info_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=PRIMARY),
                ft.Text("Como Usar", size=16, weight=ft.FontWeight.BOLD),
            ]),
            ft.Divider(height=1),
            ft.Text("1️⃣ Preencha os campos de busca e perfil", size=13),
            ft.Text("2️⃣ Clique em 'Iniciar BOT'", size=13),
            ft.Text("3️⃣ Uma janela do navegador abrirá", size=13),
            ft.Text("4️⃣ Na primeira vez, faça login no LinkedIn", size=13),
            ft.Text("5️⃣ O login será salvo para próximas vezes!", size=13),
            ft.Divider(height=1),
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=SUCCESS, size=16),
                ft.Text("Navegador separado - não interfere no seu Chrome", size=12, color=SUCCESS),
            ], spacing=4),
            ft.Row([
                ft.Icon(ft.Icons.SECURITY, color=ft.Colors.GREY_400, size=16),
                ft.Text("Suas credenciais ficam apenas no LinkedIn", size=12, color=ft.Colors.GREY_400),
            ], spacing=4),
            ft.Row([
                ft.Icon(ft.Icons.SAVE, color=ft.Colors.GREY_400, size=16),
                ft.Text("Sessão salva em data/browser_profile/", size=12, color=ft.Colors.GREY_400),
            ], spacing=4),
        ], spacing=6),
        bgcolor=DARK_CARD,
        border_radius=12,
        padding=16,
    )
    
    # === FE-05: CONTROLS PANEL ===
    status_indicator = ft.Container(width=12, height=12, border_radius=6, bgcolor=ft.Colors.GREY)
    status_text = ft.Text("Parado", weight=ft.FontWeight.BOLD)
    progress_bar = ft.ProgressBar(value=0, color=PRIMARY, bgcolor=DARK_BG)
    progress_text = ft.Text("0 / 50 candidaturas hoje", size=12)
    
    def start_bot_click(e):
        if state["is_running"]:
            add_log("⚠️ Bot já está em execução!", "warning")
            return
            
        if not state["keywords"]:
            add_log("⚠️ Adicione ao menos uma keyword de vaga", "warning")
            return
        if not state["name"] or not state["resume"]:
            add_log("⚠️ Preencha seu perfil (nome e currículo)", "warning")
            return
        
        state["is_running"] = True
        status_indicator.bgcolor = SUCCESS
        status_text.value = "Em Execução"
        add_log("🚀 BOT Iniciado! Abrindo navegador...", "success")
        page.update()
        
        # Start bot in background thread
        bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
        bot_thread.start()
    
    def stop_bot_click(e):
        state["is_running"] = False
        status_indicator.bgcolor = ft.Colors.GREY
        status_text.value = "Parado"
        add_log("⏹️ BOT Parado - Aguardando fechamento do navegador...", "info")
        page.update()
    
    controls_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.SMART_TOY, color=PRIMARY),
                ft.Text("Controles do BOT", size=16, weight=ft.FontWeight.BOLD),
            ]),
            ft.Divider(height=1),
            ft.Row([
                ft.Button(
                    "Iniciar BOT",
                    icon=ft.Icons.PLAY_ARROW,
                    style=ft.ButtonStyle(bgcolor=SUCCESS, color=ft.Colors.WHITE),
                    on_click=start_bot_click,
                ),
                ft.Button(
                    "Parar BOT",
                    icon=ft.Icons.STOP,
                    style=ft.ButtonStyle(bgcolor=ERROR, color=ft.Colors.WHITE),
                    on_click=stop_bot_click,
                ),
            ], spacing=8),
            ft.Row([status_indicator, status_text], spacing=8),
            ft.Divider(height=1),
            ft.Text("Progresso Diário", size=12, color=ft.Colors.GREY_400),
            progress_bar,
            progress_text,
        ], spacing=10),
        bgcolor=DARK_CARD,
        border_radius=12,
        padding=16,
    )
    
    # === FE-03 & FE-04: PROFILE PANEL ===
    name_field = ft.TextField(
        label="Nome Completo",
        hint_text="Seu nome",
        border_radius=8,
        on_change=lambda e: state.update({"name": e.control.value or ""}),
    )
    
    email_field = ft.TextField(
        label="Email",
        hint_text="seu.email@exemplo.com",
        border_radius=8,
        expand=True,
        on_change=lambda e: state.update({"email": e.control.value or ""}),
    )
    
    phone_field = ft.TextField(
        label="Telefone",
        hint_text="(11) 99999-9999",
        border_radius=8,
        expand=True,
        on_change=lambda e: state.update({"phone": e.control.value or ""}),
    )
    
    resume_field = ft.TextField(
        label="Currículo (cole o texto aqui)",
        hint_text="Cole o conteúdo do seu currículo...",
        multiline=True,
        min_lines=5,
        max_lines=8,
        border_radius=8,
        on_change=lambda e: state.update({"resume": e.control.value or ""}),
    )
    
    skills_field = ft.TextField(
        label="Habilidades (separadas por vírgula)",
        hint_text="Python, JavaScript, SQL, AWS...",
        border_radius=8,
        on_change=lambda e: state.update({"skills": e.control.value or ""}),
    )
    
    profile_status = ft.Text("", size=12)
    
    def save_profile_click(e):
        if state["name"] and state["resume"]:
            profile_status.value = f"✅ Perfil salvo: {state['name']}"
            profile_status.color = SUCCESS
            add_log(f"📄 Perfil salvo: {state['name']}", "success")
        else:
            profile_status.value = "⚠️ Preencha nome e currículo"
            profile_status.color = WARNING
            add_log("⚠️ Preencha nome e currículo", "warning")
        page.update()
    
    profile_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.PERSON, color=PRIMARY),
                ft.Text("Perfil do Candidato", size=16, weight=ft.FontWeight.BOLD),
            ]),
            ft.Divider(height=1),
            name_field,
            ft.Row([email_field, phone_field], spacing=8),
            resume_field,
            skills_field,
            ft.Row([
                ft.Button(
                    "Salvar Perfil",
                    icon=ft.Icons.SAVE,
                    style=ft.ButtonStyle(bgcolor=SUCCESS, color=ft.Colors.WHITE),
                    on_click=save_profile_click,
                ),
                profile_status,
            ], spacing=8),
        ], spacing=10),
        bgcolor=DARK_CARD,
        border_radius=12,
        padding=16,
    )
    
    # === BIO PANEL ===
    bio_field = ft.TextField(
        label="Bio / Carta de Apresentação",
        hint_text="Descreva seu perfil profissional, motivações...",
        multiline=True,
        min_lines=3,
        max_lines=5,
        border_radius=8,
        on_change=lambda e: state.update({"bio": e.control.value or ""}),
    )
    
    bio_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE, color=PRIMARY),
                ft.Text("Perfil Estendido", size=16, weight=ft.FontWeight.BOLD),
            ]),
            ft.Divider(height=1),
            bio_field,
        ], spacing=10),
        bgcolor=DARK_CARD,
        border_radius=12,
        padding=16,
    )
    
    # === FE-06: LOG PANEL ===
    
    # Jobs log dialog
    jobs_log_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("📋 Vagas Processadas"),
        content=ft.Container(
            content=jobs_log_column,
            width=500,
            height=400,
        ),
        actions=[
            ft.TextButton("Fechar", on_click=lambda e: close_jobs_dialog()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    
    def open_jobs_dialog(e):
        jobs_log_dialog.open = True
        page.update()
    
    def close_jobs_dialog():
        jobs_log_dialog.open = False
        page.update()
    
    # Add dialog to page overlay
    page.overlay.append(jobs_log_dialog)
    
    log_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.TERMINAL, color=PRIMARY),
                ft.Text("Log de Atividades", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),  # Spacer
                ft.ElevatedButton(
                    "📋 Ver Vagas",
                    icon=ft.Icons.LIST_ALT,
                    bgcolor=PRIMARY,
                    color=ft.Colors.WHITE,
                    on_click=open_jobs_dialog,
                ),
            ]),
            ft.Divider(height=1),
            ft.Container(
                content=log_column,
                bgcolor=DARK_BG,
                border_radius=8,
                padding=8,
                height=150,
            ),
        ], spacing=10),
        bgcolor=DARK_CARD,
        border_radius=12,
        padding=16,
    )
    
    # Store panels for theme toggle
    all_panels = [job_panel, info_panel, controls_panel, profile_panel, bio_panel, log_panel]
    
    # === FE-07: HEADER WITH THEME TOGGLE ===
    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = LIGHT_BG
            for panel in all_panels:
                panel.bgcolor = LIGHT_CARD
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = DARK_BG
            for panel in all_panels:
                panel.bgcolor = DARK_CARD
        page.update()
    
    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.SMART_TOY, size=36, color=PRIMARY),
                ft.Text("BOTLink", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("v1.0", size=12, color=ft.Colors.GREY_500),
            ], spacing=8),
            ft.Row([
                ft.Icon(ft.Icons.LIGHT_MODE, color=WARNING, size=18),
                ft.Switch(value=True, on_change=toggle_theme),
                ft.Icon(ft.Icons.DARK_MODE, color=PRIMARY, size=18),
            ], spacing=4),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.only(bottom=16),
    )
    
    # === MAIN LAYOUT ===
    left_column = ft.Column(
        [job_panel, info_panel, controls_panel],
        spacing=16,
    )
    
    right_column = ft.Column(
        [profile_panel, bio_panel, log_panel],
        spacing=16,
    )
    
    main_content = ft.ResponsiveRow([
        ft.Container(content=left_column, col={"sm": 12, "md": 6}),
        ft.Container(content=right_column, col={"sm": 12, "md": 6}),
    ], spacing=24)
    
    # === BUILD PAGE ===
    page.add(
        header,
        ft.Divider(height=1),
        main_content,
    )
    
    # Welcome message
    add_log("👋 BOTLink iniciado!", "info")
    add_log("📋 Siga as instruções no painel 'Como Usar'", "info")
    add_log("🔒 Suas credenciais nunca são armazenadas!", "success")
