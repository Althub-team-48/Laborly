import os

def create_structure(base_path, structure):
    for path in structure:
        full_path = os.path.join(base_path, path)
        if path.endswith("/"):
            os.makedirs(full_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write("")

def main():
    project_name = "Laborly"
    base_path = os.path.join(os.getcwd(), project_name)
    
    structure = [
        # Backend Structure (Updated to Package-Based Structure)
        "backend/app/users/routes.py", "backend/app/users/models.py", "backend/app/users/schemas.py", "backend/app/users/service.py",
        "backend/app/jobs/routes.py", "backend/app/jobs/models.py", "backend/app/jobs/schemas.py", "backend/app/jobs/service.py",
        "backend/app/reviews/routes.py", "backend/app/reviews/models.py", "backend/app/reviews/schemas.py", "backend/app/reviews/service.py",
        "backend/app/admin/routes.py", "backend/app/admin/models.py", "backend/app/admin/schemas.py", "backend/app/admin/service.py",
        "backend/app/core/config.py", "backend/app/core/security.py", "backend/app/core/dependencies.py",
        "backend/app/database/config.py", "backend/app/database/init_db.py", "backend/app/database/migrations/",
        "backend/app/utils/hash.py", "backend/app/utils/email.py", "backend/app/utils/logger.py",
        "backend/app/main.py", "backend/app/run.sh",
        "backend/tests/test_users.py", "backend/tests/test_jobs.py", "backend/tests/test_reviews.py", "backend/tests/test_admin.py",
        
        # Frontend Structure
        "frontend/public/", "frontend/src/components/Button.js", "frontend/src/components/Navbar.js",
        "frontend/src/pages/index.js", "frontend/src/pages/login.js", "frontend/src/pages/dashboard.js",
        "frontend/src/services/api.js", "frontend/src/services/auth.js", "frontend/src/services/jobs.js",
        "frontend/src/hooks/", "frontend/src/contexts/", "frontend/src/styles/globals.css",
        "frontend/package.json", "frontend/next.config.js",
        
        # Infrastructure & DevOps
        "infrastructure/docker/Dockerfile.backend", "infrastructure/docker/Dockerfile.frontend",
        "infrastructure/terraform/main.tf", "infrastructure/ci-cd/jenkinsfile", 
        "infrastructure/ci-cd/github-actions/",
        
        # Documentation
        "docs/README.md", "docs/api-docs.md", "docs/setup.md",
        
        # Root files
        ".gitignore", ".env", "docker-compose.yml"
    ]
    
    create_structure(base_path, structure)
    print(f"Project '{project_name}' structure created successfully!")

if __name__ == "__main__":
    main()