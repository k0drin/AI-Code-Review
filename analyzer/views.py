import os
import logging
import asyncio
import traceback

import httpx
from git import Repo
from django.shortcuts import render

from .forms import RepositoryForm



async def home(request):
    """
    Handle the home page view for submitting a repository URL and analyzing it.

    This view processes both GET and POST requests:
    - For GET requests, it renders a form for users to input a repository URL, 
      assignment description, and candidate level.
    - For POST requests, it validates the form input, retrieves the data, 
      and asynchronously calls the repository analysis function.

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.

    Returns:
        HttpResponse: Renders the results template with the analysis recommendations if the form is valid.
        Otherwise, it renders the home page with the form.
    """
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
    """
    Asynchronously clone a repository, analyze the code files, and return analysis results.

    This function performs the following steps:
    1. Clones the GitHub repository from the provided URL to a local temporary directory.
    2. Retrieves all relevant code files from the repository.
    3. Reads each file asynchronously, sending the code to the OpenAI API for analysis.
    4. Gathers the analysis results for each file.
    5. Cleans up by deleting the cloned repository from the local filesystem.

    Args:
        repo_url (str): The URL of the GitHub repository to be cloned and analyzed.
        assignment_description (str): A description of the coding assignment for context.
        candidate_level (str): The experience level of the candidate (e.g., Junior, Middle, Senior).

    Returns:
        str: A list of dictionaries where each dictionary contains the file path and its corresponding analysis result.
    """
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
    """
    Clone a GitHub repository to a temporary local directory.

    This function takes a GitHub repository URL, clones it to the `/tmp/` directory,
    and returns the path to the local clone. If the repository has already been cloned
    to the specified location, it skips the cloning step and logs that the repository
    already exists.

    Args:
        repo_url (str): The URL of the GitHub repository to be cloned.

    Returns:
        str: The local file system path where the repository has been cloned.
    """
    repo_name = repo_url.split("/")[-1].replace('.git', '')
    local_path = f"/tmp/{repo_name}"

    if not os.path.exists(local_path):
        logging.info(f"Cloning repository to {local_path}")
        Repo.clone_from(repo_url, local_path)
    else:
        logging.info(f"Repository already exists at {local_path}")

    return local_path


def get_all_python_files(repo_path: str) -> list[str]:
    """
    Retrieve all relevant code files from a cloned repository.

    This function walks through the file system tree of the cloned repository 
    and collects all files with specific extensions (e.g., Python, JavaScript, 
    Java, C++). The collected files are added to a list, which is then returned.

    Args:
        repo_path (str): The local file system path to the cloned repository.

    Returns:
        list[str]: A list of file paths for the relevant code files within the repository.
    """
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
    """
    Asynchronously read the content of a file.

    This function reads the file at the specified `file_path` asynchronously by using the event loop to 
    execute the file reading operation in a non-blocking way.

    Args:
        file_path (str): The path to the file to be read.

    Returns:
        str: The content of the file as a string.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: open(file_path, 'r').read())


async def get_code_analysis(code: str, assignment_description: str, candidate_level: str) -> str:
    """
    Analyze the given code by sending it to the OpenAI API asynchronously, with retry logic.

    This function constructs a prompt using the provided code, assignment description, and candidate level.
    It then sends the prompt to the OpenAI GPT-4 API for code analysis. The request is made asynchronously 
    using `httpx` with a retry mechanism that attempts the request up to 3 times in case of a timeout.

    Args:
        code (str): The code to be analyzed.
        assignment_description (str): A description of the coding assignment to provide context for the analysis.
        candidate_level (str): The experience level of the candidate (e.g., beginner, intermediate, expert).

    Returns:
        str: The analysis result from the OpenAI API, or an error message if the request fails.

    Raises:
        httpx.ConnectTimeout: If the request times out after 3 attempts.
        httpx.HTTPStatusError: If an HTTP error occurs, the status code and error response are logged.
        Exception: For any unexpected errors, the exception and traceback are logged.
    
    Notes:
        - Retries the request up to 3 times in case of a connection timeout.
        - Uses GPT-4 model ("gpt-4-turbo") with a token limit and temperature settings for the response.
        - Logs detailed error messages and tracebacks for easier debugging.
    """
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
    """
    Delete the cloned repository to clean up temporary files.

    This function removes the directory at `repo_path` if it exists, effectively cleaning up 
    any temporary files created during the repository analysis process.

    Args:
        repo_path (str): The path to the repository directory to be deleted.
    """
    if os.path.exists(repo_path):
        import shutil
        shutil.rmtree(repo_path)
