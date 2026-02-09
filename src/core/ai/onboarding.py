import json
from rich.console import Console
from rich.markdown import Markdown
from src.core.ai.router import Router
from src.core.ai.settings import SettingsManager

console = Console()

BASE_SYSTEM_PROMPT = "You are the IronClaw Architect. Your goal is to conduct a step-by-step onboarding to set up the AI system. Wait for user input after each question. Do not finish a phase until you have all the necessary information."

PHASES = [
    {
        "name": "AI Identity",
        "instruction": "PHASE 1: AI Identity. Introduce yourself and propose your name and persona. Ask the user if they agree or want to change anything. Focus ONLY on this. When the user is satisfied, output '###PHASE_DONE###'."
    },
    {
        "name": "User Persona",
        "instruction": "PHASE 2: User Persona. Ask for the user's name and what they want to achieve with this system. Focus ONLY on this. When you have the info, output '###PHASE_DONE###'."
    },
    {
        "name": "System Preferences",
        "instruction": "PHASE 3: System Preferences. Ask for the user's Timezone and any specific behavioral preferences (e.g. brevity, tone). When done, output '###PHASE_DONE###'."
    }
]

def run_onboarding_session():
    settings_manager = SettingsManager()
    if not settings_manager.is_provider_configured():
        settings_manager.run_full_setup()

    router = Router()
    console.rule("[bold blue]Conversational Onboarding[/bold blue]")
    
    messages = []

    for phase in PHASES:
        console.print(f"\n[bold yellow]>>> {phase['name']}[/bold yellow]")
        phase_active = True
        is_start_of_phase = True
        
        while phase_active:
            try:
                # Формируем системный промпт для текущей фазы
                current_system = f"{BASE_SYSTEM_PROMPT}\n\n{phase['instruction']}"
                
                # Если это НЕ начало фазы, сначала ждем ответа пользователя на предыдущий вопрос ИИ
                if not is_start_of_phase:
                    user_input = console.input("\nYou > ")
                    if user_input.lower() in ["exit", "quit"]: return
                    messages.append({"role": "user", "content": user_input})
                
                response = router.provider.chat(
                    model=router.model_name,
                    messages=messages,
                    system_prompt=current_system
                )
                
                # Проверяем завершение фазы, но не позволяем выйти в самом первом сообщении фазы,
                # чтобы у пользователя всегда была возможность ответить.
                if "###PHASE_DONE###" in response:
                    if not is_start_of_phase:
                        phase_active = False
                    response = response.replace("###PHASE_DONE###", "").strip()

                is_start_of_phase = False

                if response:
                    console.print(Markdown(response))
                    messages.append({"role": "assistant", "content": response})

            except KeyboardInterrupt:
                return

    # Финальный этап: Генерация JSON
    console.print("\n[bold green]Finishing onboarding and saving your identity...[/bold green]")
    final_prompt = (
        "Onboarding complete. Create a single Markdown string containing ALL information we discussed "
        "(AI identity, User persona, Timezone, Preferences). Output it as: ###SAVE_IDENTITY### | {\"bio\": \"# Markdown content...\"}"
    )
    
    final_response = router.provider.chat(
        model=router.model_name,
        messages=messages,
        system_prompt=final_prompt
    )

    if "###SAVE_IDENTITY###" in final_response:
        try:
            data_str = final_response.split("###SAVE_IDENTITY### |", 1)[1].strip()
            data = json.loads(data_str)
            router.memory.update_config(data)
            console.print("[bold green]✔ Identity saved successfully! Use 'ironclaw talk' to start.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error parsing final identity: {e}[/bold red]")
    else:
        console.print("[bold red]Failed to generate final identity format.[/bold red]")
