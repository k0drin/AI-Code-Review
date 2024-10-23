import os
import logging
import openai
from git import Repo
from django.shortcuts import render
from .forms import RepositoryForm
from .utils import analyze_repository


def home(request):
    if request.method == "POST":
        form = RepositoryForm(request.POST)
        if form.is_valid():
            repository_url = form.cleaned_data['url']
            assignment_description = form.cleaned_data['assignment_description']
            candidate_level = form.cleaned_data['candidate_level']

            recommendations = analyze_repository(repository_url, assignment_description, candidate_level)

            return render(request, 'analyzer/results.html', {'recommendations': recommendations})
    else:
        form = RepositoryForm()

    return render(request, 'analyzer/home.html', {'form': form})


def analyze_repository(repo_url: str, assignment_description: str, candidate_level: str) -> str:
    """Clone the repository and analyze the code using OpenAI API."""
    local_repo_path = clone_repository(repo_url)

    code_files = get_all_python_files(local_repo_path)

    analysis_results = []
    for code_file in code_files:
        with open(code_file, 'r') as f:
            code_content = f.read()
            analysis = get_code_analysis(code_content, assignment_description, candidate_level)
            analysis_results.append({code_file: analysis})

    cleanup_repository(local_repo_path)

    return analysis_results


def clone_repository(repo_url: str) -> str:
    """Clone a GitHub repository to a temporary location."""
    repo_name = repo_url.split("/")[-1].replace('.git', '')
    local_path = f"/tmp/{repo_name}"

    if not os.path.exists(local_path):
        logging.info(f"Cloning repository to {local_path}")
        Repo.clone_from(repo_url, local_path)
    else:
        logging.info(f"Repository already exists at {local_path}")

    return local_path


def get_all_python_files(repo_path: str) -> list[str]:
    """Get all relevant code files in the cloned repository."""
    code_files = []
    extensions = ('.py', '.js', '.vim', '.java', '.cpp', '.c')  # Add more as needed
    for root, _, filenames in os.walk(repo_path):
        for filename in filenames:
            if filename.endswith(extensions):
                file_path = os.path.join(root, filename)
                if os.path.exists(file_path):
                    code_files.append(file_path)
                else:
                    logging.error(f"File not found: {file_path}")
    return code_files


def get_code_analysis(code: str, assignment_description: str, candidate_level: str) -> str:
    """Send the code to OpenAI for analysis and return the response."""
    prompt = (
        f"Please review the following Python code in the context of a coding assignment:\n\n"
        f"Assignment Description: {assignment_description}\n"
        f"Candidate Level: {candidate_level}\n\n"
        f"Code:\n{code}\n"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.5
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error("Error analyzing code: %s", e)
        return "Error analyzing code."


def cleanup_repository(repo_path: str):
    """Delete the cloned repository to clean up."""
    if os.path.exists(repo_path):
        import shutil
        shutil.rmtree(repo_path)
