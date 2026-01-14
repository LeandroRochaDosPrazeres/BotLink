"""
Prompt Builder - Context-aware prompt construction.

Implements BE-05: Build prompts with candidate context and constraints.
"""

from dataclasses import dataclass
from typing import Optional

from src.domain.entities import Candidate, Job
from src.infrastructure.parsers.job_parser import FormField


@dataclass
class PromptResult:
    """Result of prompt construction."""
    system_prompt: str
    user_prompt: str


class PromptBuilder:
    """
    Builds prompts for the AI to answer application questions.
    
    Constructs context-aware prompts including:
    - Candidate resume and bio
    - Job description
    - Specific question with options
    - Output constraints (JSON format)
    """
    
    SYSTEM_PROMPT_BASE = """Você é um assistente especializado em ajudar candidatos a responder perguntas de formulários de candidatura a vagas de emprego.

Você receberá:
1. O perfil do candidato (currículo, bio, habilidades)
2. A descrição da vaga
3. Uma pergunta específica do formulário

Suas responsabilidades:
- Responder de forma profissional e concisa
- Usar informações reais do perfil do candidato
- Adaptar o tom para contexto profissional brasileiro
- Seguir as restrições de formato especificadas

IMPORTANTE:
- Nunca invente informações que não estão no perfil
- Se não souber uma resposta, use o valor padrão fornecido
- Respostas devem ser diretas e objetivas"""

    SYSTEM_PROMPT_JSON = """

Você DEVE responder APENAS em formato JSON válido, sem texto adicional.
O JSON deve seguir exatamente o schema especificado na pergunta."""

    def __init__(self, candidate: Candidate) -> None:
        """
        Initialize with candidate context.
        
        Args:
            candidate: Candidate profile for context.
        """
        self.candidate = candidate

    def build_for_text_question(
        self,
        question: str,
        job: Optional[Job] = None,
        max_length: Optional[int] = None,
    ) -> PromptResult:
        """
        Build prompt for a text/textarea question.
        
        Args:
            question: The question text.
            job: Optional job context.
            max_length: Optional character limit.
            
        Returns:
            PromptResult with system and user prompts.
        """
        system = self.SYSTEM_PROMPT_BASE
        
        user_parts = [
            "## PERFIL DO CANDIDATO",
            self.candidate.context_for_ai,
        ]
        
        if job:
            user_parts.extend([
                "\n## VAGA",
                f"**Empresa:** {job.company}",
                f"**Cargo:** {job.title}",
                f"**Local:** {job.location}",
            ])
            if job.description:
                user_parts.append(f"\n**Descrição:**\n{job.description[:2000]}")
        
        user_parts.extend([
            "\n## PERGUNTA",
            question,
        ])
        
        if max_length:
            user_parts.append(f"\n**Limite:** máximo {max_length} caracteres")
        
        user_parts.append(
            "\n## INSTRUÇÕES\n"
            "Responda a pergunta acima de forma profissional e concisa, "
            "baseando-se no perfil do candidato."
        )
        
        return PromptResult(
            system_prompt=system,
            user_prompt="\n".join(user_parts),
        )

    def build_for_select_question(
        self,
        question: str,
        options: list[str],
        job: Optional[Job] = None,
    ) -> PromptResult:
        """
        Build prompt for a select/dropdown question.
        
        Args:
            question: The question text.
            options: Available options to choose from.
            job: Optional job context.
            
        Returns:
            PromptResult with system and user prompts.
        """
        system = self.SYSTEM_PROMPT_BASE + self.SYSTEM_PROMPT_JSON
        
        options_str = "\n".join(f"- {opt}" for opt in options)
        
        user_parts = [
            "## PERFIL DO CANDIDATO",
            self.candidate.context_for_ai,
        ]
        
        if job:
            user_parts.extend([
                "\n## VAGA",
                f"**Empresa:** {job.company}",
                f"**Cargo:** {job.title}",
            ])
        
        user_parts.extend([
            "\n## PERGUNTA",
            question,
            "\n## OPÇÕES DISPONÍVEIS",
            options_str,
            '\n## FORMATO DE RESPOSTA',
            'Responda APENAS com JSON no formato:',
            '{"selected_option": "opção escolhida exatamente como listada acima"}',
        ])
        
        return PromptResult(
            system_prompt=system,
            user_prompt="\n".join(user_parts),
        )

    def build_for_radio_question(
        self,
        question: str,
        options: list[str],
        job: Optional[Job] = None,
    ) -> PromptResult:
        """
        Build prompt for a radio button question.
        
        Same as select, but for radio buttons.
        """
        return self.build_for_select_question(question, options, job)

    def build_for_form_field(
        self,
        field: FormField,
        job: Optional[Job] = None,
    ) -> PromptResult:
        """
        Build prompt for any form field type.
        
        Args:
            field: The form field to answer.
            job: Optional job context.
            
        Returns:
            PromptResult with system and user prompts.
        """
        if field.field_type in ("select", "radio"):
            return self.build_for_select_question(
                field.label,
                field.options,
                job,
            )
        else:
            return self.build_for_text_question(
                field.label,
                job,
            )

    def build_for_cover_letter(
        self,
        job: Job,
        max_words: int = 200,
    ) -> PromptResult:
        """
        Build prompt for generating a cover letter.
        
        Args:
            job: The job to apply to.
            max_words: Word limit.
            
        Returns:
            PromptResult with system and user prompts.
        """
        system = self.SYSTEM_PROMPT_BASE
        
        user_parts = [
            "## PERFIL DO CANDIDATO",
            self.candidate.context_for_ai,
            "\n## VAGA",
            f"**Empresa:** {job.company}",
            f"**Cargo:** {job.title}",
            f"**Local:** {job.location}",
        ]
        
        if job.description:
            user_parts.append(f"\n**Descrição:**\n{job.description[:2000]}")
        
        user_parts.extend([
            "\n## TAREFA",
            f"Escreva uma carta de apresentação concisa (máximo {max_words} palavras) "
            "para esta vaga, destacando:",
            "1. Por que você é um bom candidato",
            "2. Experiências relevantes do seu currículo",
            "3. Motivação para a vaga",
            "\nTom: profissional mas caloroso. Evite clichês.",
        ])
        
        return PromptResult(
            system_prompt=system,
            user_prompt="\n".join(user_parts),
        )
