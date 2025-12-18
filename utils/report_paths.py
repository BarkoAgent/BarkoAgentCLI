from pathlib import Path
import re

class ReportPathManager:    
    def __init__(self, base_dir: str = "Reports"):

        self.base_dir = Path(base_dir)
    
    def sanitize_name(self, name: str, max_length: int = 50) -> str:
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = sanitized.strip()
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()
        if not sanitized:
            sanitized = "unnamed"
        return sanitized
    
    def get_single_report_path(self, project_name: str, test_title: str, batch_id: str = None) -> Path:
        safe_project = self.sanitize_name(project_name)
        safe_title = self.sanitize_name(test_title)
        
        return self.base_dir / safe_project / "html" / "single" / f"{safe_title}.html"
    
    def get_folder_report_path(self, project_name: str, folder_name: str, batch_id: str = None) -> Path:
        safe_project = self.sanitize_name(project_name)
        safe_folder = self.sanitize_name(folder_name)
        
        return self.base_dir / safe_project / "html" / "folder" / f"{safe_folder}.html"
    
    def get_all_reports_path(self, project_name: str, batch_id: str = None) -> Path:
        safe_project = self.sanitize_name(project_name)
        
        return self.base_dir / safe_project / "html" / "all.html"
    
    def get_single_xml_path(self, project_name: str, test_title: str, batch_id: str = None) -> Path:
        safe_project = self.sanitize_name(project_name)
        safe_title = self.sanitize_name(test_title)
        
        return self.base_dir / safe_project / "junit" / "single" / f"{safe_title}.xml"
    
    def get_folder_xml_path(self, project_name: str, folder_name: str, batch_id: str = None) -> Path:
        safe_project = self.sanitize_name(project_name)
        safe_folder = self.sanitize_name(folder_name)
        
        return self.base_dir / safe_project / "junit" / "folder" / f"{safe_folder}.xml"
    
    def get_all_reports_xml_path(self, project_name: str, batch_id: str = None) -> Path:
        safe_project = self.sanitize_name(project_name)
        
        return self.base_dir / safe_project / "junit" / "all.xml"
    
    def ensure_report_dirs(self, project_name: str) -> None:
        safe_project = self.sanitize_name(project_name)
        (self.base_dir / safe_project / "html" / "single").mkdir(parents=True, exist_ok=True)
        (self.base_dir / safe_project / "html" / "folder").mkdir(parents=True, exist_ok=True)
        (self.base_dir / safe_project / "junit" / "single").mkdir(parents=True, exist_ok=True)
        (self.base_dir / safe_project / "junit" / "folder").mkdir(parents=True, exist_ok=True)
