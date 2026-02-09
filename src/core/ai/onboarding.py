import json
from rich.console import Console
from rich.markdown import Markdown
from src.core.ai.router import Router
from src.core.ai.settings import SettingsManager

console = Console()

BASE_SYSTEM_PROMPT = "You are the IronClaw Architect. Your goal is to conduct a step-by-step onboarding to set up the AI system."

PHASES = [
    {
        "name": "AI Identity",
        "instruction": "PHASE 1: AI Identity. Interview the user to define your (the AI's) name and core content (persona, tone, style). Focus ONLY on this. When you have both name and content, output '###PHASE_DONE###' at the end of your message."
    },
    {
        "name": "User Persona",
        "instruction": "PHASE 2: User Persona. Now ask the user for their name and their primary goals. Focus ONLY on this. When you have both, output '###PHASE_DONE###' at the end of your message."
    },
    {
        "name": "System Preferences",
        "instruction": "PHASE 3: System Preferences. Ask for the user's Timezone (mandatory) and any other text-based preferences they want you to remember. When finished, output '###PHASE_DONE###' at the end of your message."
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
        
        while phase_active:
            try:
                # Формируем системный промпт для текущей фазы
                current_system = f"{BASE_SYSTEM_PROMPT}\n\n{phase['instruction']}"
                
                # Если это начало фазы и сообщений еще нет, получаем приветствие от ИИ
                if not messages or messages[-1]["role"] == "assistant":
                    # Ждем ввода пользователя, если это не самый первый запуск
                    if messages:
                        user_input = console.input("\nYou > ")
                        if user_input.lower() in ["exit", "quit"]: return
                        messages.append({"role": "user", "content": user_input})
                
                response = router.provider.chat(
                    model=router.model_name,
                    messages=messages,
                    system_prompt=current_system
                )
                
                # Проверяем, завершил ли ИИ фазу
                if "###PHASE_DONE###" in response:
                    phase_active = False
                    clean_response = response.replace("###PHASE_DONE###", "").strip()
                    if clean_response:
                        console.print(Markdown(clean_response))
                        messages.append({"role": "assistant", "content": clean_response})
                else:
                    console.print(Markdown(response))
                    messages.append({"role": "assistant", "content": response})
                    
                    # Если ИИ задал вопрос, нам нужно получить ответ пользователя в следующей итерации
                    user_input = console.input("\nYou > ")
                    if user_input.lower() in ["exit", "quit"]: return
                    messages.append({"role": "user", "content": user_input})

            except KeyboardInterrupt:
                return

    # Финальный этап: Генерация JSON
    console.print("\n[bold green]Finishing onboarding and saving your identity...[/bold green]")
    final_prompt = (
        "Onboarding complete. Now, based on our conversation, output the final configuration JSON. "
        "Use this EXACT format: ###SAVE_IDENTITY### | {\"name\": \"...\", \"content\": \"...\", \"user_name\": \"...\", \"user_goals\": \"...\", \"timezone\": \"...\", \"preferences\": {}}"
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
