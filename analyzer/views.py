import os
import logging
import httpx
import asyncio
from git import Repo
from django.shortcuts import render
from .forms import RepositoryForm
import traceback


async def home(request):
    if request.method == "POST":
        form = RepositoryForm(request.POST)
        if form.is_valid():
            repository_url = form.cleaned_data['url']
            assignment_description = form.cleaned_data['assignment_description']
            candidate_level = form.cleaned_data['candidate_level']

            recommendations = await analyze_repository(repository_url, assignment_description, candidate_level)

            return render(request, 'analyzer/results.html', {'recommendations': recommendations})
    else:
        form = RepositoryForm()

    return render(request, 'analyzer/home.html', {'form': form})


async def analyze_repository(repo_url: str, assignment_description: str, candidate_level: str) -> str:
    """Clone the repository and analyze the code using OpenAI API asynchronously."""
    local_repo_path = clone_repository(repo_url)

    code_files = get_all_python_files(local_repo_path)

    analysis_results = []
    for code_file in code_files:
        code_content = await read_file(code_file)
        analysis = await get_code_analysis(code_content, assignment_description, candidate_level)
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


async def read_file(file_path: str) -> str:
    """Asynchronously read a file."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: open(file_path, 'r').read())


async def get_code_analysis(code: str, assignment_description: str, candidate_level: str) -> str:
    """Send the code to OpenAI for analysis and return the response asynchronously, with retries."""
    prompt = (
        f"Please review the following code in the context of a coding assignment:\n\n"
        f"Assignment Description: {assignment_description}\n"
        f"Candidate Level: {candidate_level}\n\n"
        f"Code:\n{code}\n"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(3):  # Retry up to 3 times
            try:
                response = await client.post(
                    'https://api.openai.com/v1/chat/completions',
                    json={
                        "model": "gpt-4-turbo",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.5
                    },
                    headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content'].strip()

            except httpx.ConnectTimeout:
                logging.warning(f"Connection timeout on attempt {attempt + 1}, retrying...")
                if attempt == 2:
                    return "Error analyzing code: connection timed out after 3 attempts."

            except httpx.HTTPStatusError as e:
                logging.error("HTTP error occurred: %s - Status: %d - Response: %s", 
                              e, e.response.status_code, e.response.text)
                return f"Error analyzing code: HTTP {e.response.status_code}"

            except Exception as e:
                logging.error("Error analyzing code: %s", str(e))
                logging.error("Traceback: %s", traceback.format_exc())
                return "Error analyzing code due to an unexpected error."

            await asyncio.sleep(2)

    return "Error analyzing code: request failed after 3 attempts."


def cleanup_repository(repo_path: str):
    """Delete the cloned repository to clean up."""
    if os.path.exists(repo_path):
        import shutil
        shutil.rmtree(repo_path)
