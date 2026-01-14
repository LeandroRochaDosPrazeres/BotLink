"""
Unit tests for domain entities.
"""

import pytest
from datetime import datetime

from src.domain.entities import Job, Candidate, Application, ApplicationStatus
from src.domain.value_objects import Credentials, JobFilter


class TestJob:
    """Tests for Job entity."""
    
    def test_create_job(self):
        """Should create job with required fields."""
        job = Job(
            job_id="12345",
            title="Backend Developer",
            company="Tech Corp",
            location="São Paulo, SP",
        )
        
        assert job.job_id == "12345"
        assert job.title == "Backend Developer"
        assert job.company == "Tech Corp"
    
    def test_job_requires_job_id(self):
        """Should raise error without job_id."""
        with pytest.raises(ValueError, match="job_id is required"):
            Job(job_id="", title="Test", company="Test", location="Test")
    
    def test_display_name(self):
        """Should return formatted display name."""
        job = Job(
            job_id="123",
            title="Dev",
            company="Corp",
            location="SP",
        )
        assert job.display_name == "Dev @ Corp"
    
    def test_matches_filter_remote_only(self):
        """Should filter remote jobs."""
        remote_job = Job(
            job_id="1",
            title="Dev",
            company="Corp",
            location="Remote",
            is_remote=True,
        )
        office_job = Job(
            job_id="2",
            title="Dev",
            company="Corp",
            location="São Paulo",
            is_remote=False,
        )
        
        assert remote_job.matches_filter(remote_only=True) is True
        assert office_job.matches_filter(remote_only=True) is False


class TestCandidate:
    """Tests for Candidate entity."""
    
    def test_is_complete(self):
        """Should check completeness."""
        incomplete = Candidate()
        complete = Candidate(name="John", resume_text="My resume...")
        
        assert incomplete.is_complete is False
        assert complete.is_complete is True
    
    def test_context_for_ai(self):
        """Should generate AI context string."""
        candidate = Candidate(
            name="John Doe",
            email="john@example.com",
            skills=["Python", "SQL"],
            resume_text="Experience in backend development...",
        )
        
        context = candidate.context_for_ai
        
        assert "John Doe" in context
        assert "john@example.com" in context
        assert "Python, SQL" in context
        assert "Experience in backend" in context


class TestApplication:
    """Tests for Application entity."""
    
    def test_create_application(self):
        """Should create application with required fields."""
        app = Application(
            job_id="12345",
            empresa="Tech Corp",
            titulo="Developer",
            localizacao="SP",
            status=ApplicationStatus.SUCESSO,
        )
        
        assert app.job_id == "12345"
        assert app.status == ApplicationStatus.SUCESSO
    
    def test_status_from_string(self):
        """Should convert string status to enum."""
        app = Application(
            job_id="123",
            empresa="Corp",
            titulo="Dev",
            localizacao="SP",
            status="SUCESSO",  # type: ignore
        )
        
        assert app.status == ApplicationStatus.SUCESSO
    
    def test_display_status(self):
        """Should return emoji status."""
        app = Application(
            job_id="123",
            empresa="Corp",
            titulo="Dev",
            localizacao="SP",
            status=ApplicationStatus.SUCESSO,
        )
        
        assert "✅" in app.display_status
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        app = Application(
            job_id="123",
            empresa="Corp",
            titulo="Dev",
            localizacao="SP",
            status=ApplicationStatus.SUCESSO,
        )
        
        data = app.to_dict()
        
        assert data["job_id"] == "123"
        assert data["status"] == "SUCESSO"


class TestCredentials:
    """Tests for Credentials value object."""
    
    def test_credentials_immutable(self):
        """Credentials should be immutable."""
        creds = Credentials(username="user", password="pass")
        
        with pytest.raises(Exception):
            creds.username = "other"  # type: ignore
    
    def test_masked_password(self):
        """Should mask password for display."""
        creds = Credentials(username="user", password="secretpassword")
        masked = creds.masked()
        
        assert masked.password == "********"
        assert len(masked.password) == 8


class TestJobFilter:
    """Tests for JobFilter value object."""
    
    def test_filter_immutable(self):
        """JobFilter should be immutable."""
        filt = JobFilter(keywords=("Python", "Django"))
        
        with pytest.raises(Exception):
            filt.keywords = ("other",)  # type: ignore
    
    def test_search_query(self):
        """Should generate search query."""
        filt = JobFilter(keywords=("Python", "Django", "Backend"))
        assert filt.search_query == "Python OR Django OR Backend"
    
    def test_is_configured(self):
        """Should check if configured."""
        empty = JobFilter()
        configured = JobFilter(keywords=("Dev",))
        
        assert empty.is_configured is False
        assert configured.is_configured is True
