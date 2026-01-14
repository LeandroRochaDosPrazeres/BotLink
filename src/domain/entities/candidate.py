"""
Candidate Entity - Represents the job seeker's profile.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Candidate:
    """
    Candidate entity representing the job seeker's profile.
    
    This is the knowledge base used by the AI to answer application questions.
    
    Attributes:
        name: Full name
        email: Contact email
        phone: Contact phone
        resume_text: Extracted text from resume PDF/DOCX
        resume_path: Path to the uploaded resume file
        bio: Extended bio/cover letter text
        skills: List of skills
        experience_years: Total years of experience
        attachments: Paths to additional files (portfolio, certificates)
    """
    
    name: str = ""
    email: str = ""
    phone: str = ""
    resume_text: str = ""
    resume_path: Optional[Path] = None
    bio: str = ""
    skills: list[str] = field(default_factory=list)
    experience_years: int = 0
    attachments: list[Path] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if candidate profile has minimum required information."""
        return bool(self.name and self.resume_text)

    @property
    def context_for_ai(self) -> str:
        """
        Generate context string for AI prompt construction.
        
        Returns:
            Formatted string with all candidate information for AI context.
        """
        parts = []
        
        if self.name:
            parts.append(f"Name: {self.name}")
        if self.email:
            parts.append(f"Email: {self.email}")
        if self.phone:
            parts.append(f"Phone: {self.phone}")
        if self.experience_years:
            parts.append(f"Years of Experience: {self.experience_years}")
        if self.skills:
            parts.append(f"Skills: {', '.join(self.skills)}")
        
        if self.resume_text:
            parts.append(f"\n--- RESUME ---\n{self.resume_text}")
            
        if self.bio:
            parts.append(f"\n--- BIO/COVER LETTER ---\n{self.bio}")
            
        return "\n".join(parts)

    def add_attachment(self, path: Path) -> None:
        """Add an attachment file path."""
        if path not in self.attachments:
            self.attachments.append(path)

    def remove_attachment(self, path: Path) -> None:
        """Remove an attachment file path."""
        if path in self.attachments:
            self.attachments.remove(path)
