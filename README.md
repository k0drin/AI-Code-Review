# AI Code Review on Django

## Installation and launch

1. Clone repositories:

   With HTTP
   ```bash
   git clone https://github.com/k0drin/AI-Code-Review.git
   ```

   With SSH
   ```bash
   git clone git@github.com:k0drin/AI-Code-Review.git
   ```
2. Install the virtual environment and activate it:
   ```bash
    python3 -m venv venv
    source venv/bin/activate  # For Windows, use `venv\Scripts\activate`
    ```
3. Install all dependencies:
   ```bash
    pip install -r requirements.txt
    ```
4. Perform migrations:
   ```bash
    python manage.py migrate
    ```

5. Start the development server:
   ```bash
    daphne code_analyzer.asgi:application
    ```
8. Now just open it in your browser this address `http://127.0.0.1:8000/` and fill in the fields

   ![alt text](image.png)
   
### About project scaling if we take into account 100 requests per minute and if there are more than 100 files in the repository 


<details>
<summary>Sulutions №1 - Microservices Architecture</summary>
Microservices architecture is a design pattern that structures an application as a collection of small, independently deployable services, each focusing on a specific business capability and communicating over well-defined APIs. This approach allows for scalability, as each microservice can be scaled independently based on its load. Teams can choose the best technology for each service, improving flexibility. Fault isolation ensures that if one microservice fails, the entire application remains operational. Additionally, it allows for faster development and deployment, enabling teams to iterate and innovate more rapidly. Key steps include identifying services based on business capabilities, using RESTful APIs or messaging systems for communication, and deploying services using containers like Docker managed by Kubernetes.
</details>

<details>
<summary>Solutions №2 - Batch Processing for Large Repositories</summary>
Batch processing involves processing a group of data together, which is especially beneficial for analyzing large repositories with many files. This approach enhances efficiency by reducing overhead associated with initiating multiple independent tasks and minimizes context switching. It also improves resource utilization, leading to faster overall processing times. Implementation can include modifying the task queue to support batch processing, grouping files by criteria like type or size, and using asynchronous programming techniques to process batches concurrently. The analysis service should compile results from each batch into a single response, providing a comprehensive overview of all files analyzed.
</details>

<details>
<summary>Sulutions №3 - Caching Layer</summary>
A caching layer temporarily stores data for quick retrieval, significantly enhancing performance by reducing database load and speeding up response times. Caching improves performance by serving frequently requested information from memory instead of querying the database, thereby reducing latency. It also lowers the database load during peak times. Implementation involves choosing caching solutions like Redis or Memcached, employing strategies such as time-based expiry or cache invalidation, and determining what data to cache, including results of common analyses and repository metadata. Integrating the caching mechanism within the analysis and review services ensures they check the cache before making direct queries.
</details>