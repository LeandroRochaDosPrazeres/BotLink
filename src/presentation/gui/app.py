"""
BOTLink Main Application - Flet GUI with Real Backend Integration

Connects the UI with the actual bot automation.
"""

import flet as ft
import asyncio
import threading
from datetime import datetime
from pathlib import Path


# === MODERN COLOR PALETTE ===
PRIMARY = "#8B5CF6"  # Purple
PRIMARY_DARK = "#7C3AED"
PRIMARY_LIGHT = "#A78BFA"
ACCENT = "#06B6D4"  # Cyan
SUCCESS = "#10B981"  # Emerald
WARNING = "#F59E0B"  # Amber
ERROR = "#EF4444"  # Red
DARK_BG = "#0F0F1A"  # Deep dark
DARK_CARD = "#1A1A2E"  # Card background
DARK_CARD_HOVER = "#252542"
DARK_BORDER = "#2D2D4A"
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"
LIGHT_BG = "#F1F5F9"
LIGHT_CARD = "#FFFFFF"


def build_app(page: ft.Page) -> None:
    """Build the main BOTLink application with real backend."""
    
    # === PAGE CONFIGURATION ===
    page.title = "BOTLink - Automação Inteligente de Candidaturas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = DARK_BG
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    }
    
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
        "extra_info": "",
        "is_running": False,
        "applications_today": 0,
        "bot_task": None,
        "applied_jobs": [],
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
    keywords_row = ft.Row(wrap=True, spacing=8)
    keyword_field = ft.TextField(
        label="Cargo / Palavra-chave",
        hint_text="Ex: Python Developer, Data Engineer...",
        expand=True,
        border_radius=12,
        border_color=DARK_BORDER,
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
        text_size=14,
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
                    ft.Text(kw, size=13, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        icon_size=16,
                        icon_color=ft.Colors.WHITE70,
                        on_click=remove_keyword(kw),
                        style=ft.ButtonStyle(padding=0),
                    ),
                ], tight=True, spacing=2),
                gradient=ft.LinearGradient(
                    colors=[PRIMARY, PRIMARY_DARK],
                ),
                border_radius=20,
                padding=ft.padding.only(left=14, right=6, top=6, bottom=6),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=8,
                    color=f"{PRIMARY}40",
                    offset=ft.Offset(0, 2),
                ),
            )
            for kw in state["keywords"]
        ]
    
    location_field = ft.TextField(
        label="Localização",
        hint_text="Ex: São Paulo, Brasil",
        border_radius=12,
        border_color=DARK_BORDER,
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
        text_size=14,
        on_change=lambda e: state.update({"location": e.control.value or ""}),
    )
    
    remote_switch = ft.Switch(
        label="Apenas Remoto",
        value=False,
        active_color=PRIMARY,
        on_change=lambda e: state.update({"remote_only": e.control.value}),
    )
    
    job_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.WORK_ROUNDED, color=ft.Colors.WHITE, size=20),
                    bgcolor=PRIMARY,
                    border_radius=10,
                    padding=10,
                ),
                ft.Column([
                    ft.Text("Configuração de Busca", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Defina os cargos e localização", size=12, color=TEXT_MUTED),
                ], spacing=2),
            ], spacing=12),
            ft.Container(height=8),
            ft.Row([
                keyword_field,
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.ADD_ROUNDED,
                        icon_color=ft.Colors.WHITE,
                        icon_size=24,
                        on_click=add_keyword_click,
                    ),
                    bgcolor=SUCCESS,
                    border_radius=12,
                ),
            ], spacing=8),
            keywords_row,
            location_field,
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.HOME_WORK_ROUNDED, color=TEXT_MUTED, size=20),
                    remote_switch,
                ], spacing=8),
                padding=ft.padding.only(top=4),
            ),
        ], spacing=12),
        bgcolor=DARK_CARD,
        border_radius=16,
        padding=20,
        border=ft.border.all(1, DARK_BORDER),
    )
    
    # === INSTRUÇÃO (painel informativo) ===
    info_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color=WARNING, size=20),
                    bgcolor=f"{WARNING}20",
                    border_radius=10,
                    padding=10,
                ),
                ft.Column([
                    ft.Text("Como Usar", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Guia rápido de início", size=12, color=TEXT_MUTED),
                ], spacing=2),
            ], spacing=12),
            ft.Container(height=4),
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("1", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD), ft.Text("Cole seu currículo no campo de contexto", size=13, color=TEXT_SECONDARY)], spacing=8),
                    ft.Row([ft.Text("2", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD), ft.Text("Adicione as keywords das vagas desejadas", size=13, color=TEXT_SECONDARY)], spacing=8),
                    ft.Row([ft.Text("3", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD), ft.Text("Clique em 'Iniciar BOT'", size=13, color=TEXT_SECONDARY)], spacing=8),
                    ft.Row([ft.Text("4", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD), ft.Text("Faça login no LinkedIn (apenas 1ª vez)", size=13, color=TEXT_SECONDARY)], spacing=8),
                    ft.Row([ft.Text("5", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD), ft.Text("A IA responde as perguntas automaticamente!", size=13, color=TEXT_SECONDARY)], spacing=8),
                ], spacing=8),
                bgcolor=DARK_BG,
                border_radius=12,
                padding=16,
            ),
            ft.Container(height=8),
            ft.Row([
                ft.Icon(ft.Icons.VERIFIED_USER_ROUNDED, color=SUCCESS, size=16),
                ft.Text("Navegador isolado • Sessão persistente", size=11, color=SUCCESS),
            ], spacing=6),
        ], spacing=12),
        bgcolor=DARK_CARD,
        border_radius=16,
        padding=20,
        border=ft.border.all(1, DARK_BORDER),
    )
    
    # === FE-05: CONTROLS PANEL ===
    status_indicator = ft.Container(width=14, height=14, border_radius=7, bgcolor=TEXT_MUTED)
    status_text = ft.Text("Parado", weight=ft.FontWeight.W_600, color=TEXT_SECONDARY, size=14)
    progress_bar = ft.ProgressBar(value=0, color=PRIMARY, bgcolor=DARK_BG, bar_height=8, border_radius=4)
    progress_text = ft.Text("0 / 50 candidaturas hoje", size=12, color=TEXT_MUTED)
    
    def start_bot_click(e):
        if state["is_running"]:
            add_log("⚠️ Bot já está em execução!", "warning")
            return
            
        if not state["keywords"]:
            add_log("⚠️ Adicione ao menos uma keyword de vaga", "warning")
            return
        if not state["resume"]:
            add_log("⚠️ Cole seu currículo no campo 'Contexto para IA'", "warning")
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
                ft.Container(
                    content=ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color=ft.Colors.WHITE, size=20),
                    bgcolor=PRIMARY,
                    border_radius=10,
                    padding=10,
                ),
                ft.Column([
                    ft.Text("Controles do BOT", size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Inicie ou pare a automação", size=12, color=TEXT_MUTED),
                ], spacing=2),
            ], spacing=12),
            ft.Container(height=8),
            ft.Row([
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color=ft.Colors.WHITE),
                        ft.Text("Iniciar BOT", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                    ], spacing=8),
                    bgcolor=SUCCESS,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.padding.symmetric(horizontal=20, vertical=14),
                        shadow_color=f"{SUCCESS}60",
                        elevation=4,
                    ),
                    on_click=start_bot_click,
                ),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.STOP_ROUNDED, color=ft.Colors.WHITE),
                        ft.Text("Parar", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                    ], spacing=8),
                    bgcolor=ERROR,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.padding.symmetric(horizontal=20, vertical=14),
                    ),
                    on_click=stop_bot_click,
                ),
            ], spacing=12),
            ft.Container(height=12),
            ft.Container(
                content=ft.Row([
                    status_indicator,
                    status_text,
                    ft.Container(expand=True),
                    ft.Text("|", color=DARK_BORDER),
                    ft.Container(expand=True),
                    progress_text,
                ], spacing=12),
                bgcolor=DARK_BG,
                border_radius=12,
                padding=16,
            ),
            progress_bar,
        ], spacing=8),
        bgcolor=DARK_CARD,
        border_radius=16,
        padding=20,
        border=ft.border.all(1, DARK_BORDER),
    )
    
    # === CONTEXT PANEL (único campo para IA) ===
    context_field = ft.TextField(
        hint_text="""Cole aqui TODAS as informações para a IA:

📄 Currículo completo
👤 Nome, email, telefone
💰 Pretensão salarial
📅 Disponibilidade de início
🏠 Aceita presencial/híbrido/remoto?
📊 Anos de experiência
🌍 Idiomas e níveis
📜 Certificações
💡 Outras informações relevantes""",
        multiline=True,
        min_lines=15,
        max_lines=25,
        border_radius=16,
        border_color=DARK_BORDER,
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
        text_size=14,
        content_padding=20,
        expand=True,
        on_change=lambda e: state.update({
            "resume": e.control.value or "",
            "extra_info": e.control.value or "",
            "name": "Candidato",
        }),
    )
    
    context_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.PSYCHOLOGY_ROUNDED, color=ft.Colors.WHITE, size=22),
                    gradient=ft.LinearGradient(
                        colors=[ACCENT, PRIMARY],
                    ),
                    border_radius=12,
                    padding=12,
                ),
                ft.Column([
                    ft.Text("Contexto para IA", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Suas informações para respostas automáticas", size=12, color=TEXT_MUTED),
                ], spacing=2, expand=True),
            ], spacing=14),
            ft.Container(height=4),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=PRIMARY, size=16),
                    ft.Text(
                        "A IA usará estas informações para preencher formulários automaticamente",
                        size=12,
                        color=TEXT_SECONDARY,
                    ),
                ], spacing=8),
                bgcolor=f"{PRIMARY}15",
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ),
            ft.Container(height=8),
            context_field,
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=TEXT_MUTED, size=14),
                ft.Text(
                    "Quanto mais detalhes, melhor a IA responde!",
                    size=11,
                    color=TEXT_MUTED,
                    italic=True,
                ),
            ], spacing=6),
        ], spacing=12),
        bgcolor=DARK_CARD,
        border_radius=16,
        padding=20,
        border=ft.border.all(1, DARK_BORDER),
    )
    
    # === FE-06: LOG PANEL ===
    
    # Jobs log dialog
    jobs_log_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.WORK_HISTORY_ROUNDED, color=PRIMARY),
            ft.Text("Vagas Processadas", weight=ft.FontWeight.BOLD),
        ], spacing=8),
        content=ft.Container(
            content=jobs_log_column,
            width=550,
            height=450,
            bgcolor=DARK_BG,
            border_radius=12,
            padding=12,
        ),
        actions=[
            ft.TextButton(
                content=ft.Text("Fechar", color=TEXT_SECONDARY),
                on_click=lambda e: close_jobs_dialog(),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=DARK_CARD,
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
                ft.Container(
                    content=ft.Icon(ft.Icons.TERMINAL_ROUNDED, color=ft.Colors.WHITE, size=18),
                    bgcolor=DARK_BG,
                    border_radius=8,
                    padding=8,
                ),
                ft.Text("Log de Atividades", size=16, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WORK_HISTORY_ROUNDED, size=16, color=ft.Colors.WHITE),
                        ft.Text("Ver Vagas", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
                    ], spacing=6),
                    bgcolor=PRIMARY,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    ),
                    on_click=open_jobs_dialog,
                ),
            ], spacing=10),
            ft.Container(height=4),
            ft.Container(
                content=log_column,
                bgcolor=DARK_BG,
                border_radius=12,
                padding=12,
                height=180,
            ),
        ], spacing=8),
        bgcolor=DARK_CARD,
        border_radius=16,
        padding=20,
        border=ft.border.all(1, DARK_BORDER),
    )
    
    # Store panels for theme toggle
    all_panels = [job_panel, info_panel, controls_panel, context_panel, log_panel]
    
    # === FE-07: HEADER ===
    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, size=28, color=ft.Colors.WHITE),
                    gradient=ft.LinearGradient(
                        colors=[PRIMARY, ACCENT],
                    ),
                    border_radius=14,
                    padding=12,
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=20,
                        color=f"{PRIMARY}50",
                        offset=ft.Offset(0, 4),
                    ),
                ),
                ft.Column([
                    ft.Text("BOTLink", size=28, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Automação Inteligente de Candidaturas", size=12, color=TEXT_MUTED),
                ], spacing=0),
            ], spacing=16),
            ft.Container(
                content=ft.Row([
                    ft.Container(width=8, height=8, border_radius=4, bgcolor=SUCCESS),
                    ft.Text("v2.0", size=12, color=TEXT_MUTED, weight=ft.FontWeight.W_500),
                ], spacing=6),
                bgcolor=DARK_CARD,
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                border=ft.border.all(1, DARK_BORDER),
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        bgcolor=DARK_BG,
    )
    
    # === MAIN LAYOUT ===
    left_column = ft.Column(
        [job_panel, info_panel, controls_panel],
        spacing=20,
    )
    
    right_column = ft.Column(
        [context_panel, log_panel],
        spacing=20,
    )
    
    main_content = ft.Container(
        content=ft.ResponsiveRow([
            ft.Container(content=left_column, col={"sm": 12, "md": 6, "lg": 5}),
            ft.Container(content=right_column, col={"sm": 12, "md": 6, "lg": 7}),
        ], spacing=24),
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
    )
    
    # === BUILD PAGE ===
    page.add(
        header,
        ft.Container(
            width=float("inf"),
            height=1,
            bgcolor=DARK_BORDER,
        ),
        main_content,
    )
    
    # Welcome message
    add_log("🚀 BOTLink v2.0 iniciado!", "success")
    add_log("📋 Cole seu currículo no campo 'Contexto para IA'", "info")
    add_log("🤖 A IA responderá perguntas automaticamente!", "success")
