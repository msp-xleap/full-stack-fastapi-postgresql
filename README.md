
---
**_NOTE:_** This file is based on the original README.md file from the FastAPI template. It has been modified to
reflect the changes made to the project.
---

# Exploring Generative AI for Brainstorming Sessions
This project follows a microservices architecture and extends the facilitation software of XLeap. 
The microservice allows to include an autonomous AI agent in the brainstorming session. The AI agent 
is based on generative large language model (GLM) and can be configured using the API. The AI agent
can generate ideas based on the configurations and input of the participants. 

## Technology Stack and Features
- ⚡ [**FastAPI**](https://fastapi.tiangolo.com) for the Python backend API with...
  - 🛠  [Alembic](https://alembic.sqlalchemy.org) for the database migrations.
  - 💬 [AutoGen](https://github.com/microsoft/autogen) for multi-agent orchestration.
  - 🎼 [**LangChain**](https://www.langchain.com/) for LLM orchestration.
  - 🔍 [Pydantic](https://docs.pydantic.dev), used by FastAPI, for the data validation and settings management.
  - 🧰 [SQLModel](https://sqlmodel.tiangolo.com) for the Python SQL database interactions (ORM).
- 🎯 [**Langfuse**](https://www.langfuse.com/) as LLM engineering platform 
- 💾 [PostgreSQL](https://www.postgresql.org) as the SQL database.
- 📲 [Adminer](https://www.adminer.org) as a web interface for the database.
- 📦️ [Poetry](https://python-poetry.org) for dependency management and packaging.
- 🚨 [Ruff](https://github.com/astral-sh/ruff) for code linting and formatting.
- 🐋 [Docker Compose](https://www.docker.com) for development and production. 
- 📝 Interactive API documentation with Swagger UI.
- ✅ Tests with [Pytest](https://pytest.org).
- 🔒 Secure password hashing by default.
- 🔑 JWT token authentication. 


### Configure

You can then update configs in the `.env` files to customize your configurations.

Before deploying it, make sure you change at least the values for:

- `SECRET_KEY`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_USER_ID`

You can (and should) pass these as environment variables from secrets.

### Generate Secret Keys

Some environment variables in the `.env` file have a default value of `changethis`.

You have to change them with a secret key, to generate secret keys you can run the following command:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the content and use that as password / secret key. And run that again to generate another secure key.


## Development
### Starting the project 

* Start the stack with Docker Compose:

```bash
docker compose up -d
```

* Now you can open your browser and interact with these URLs:

Automatic interactive documentation with Swagger UI (from the OpenAPI backend): http://localhost/docs

Adminer, database web administration: http://localhost:8080

Langfuse, LLM engineering platform: http://localhost:3000

**Note**: The first time you start your stack, it might take a minute for it to be ready. While the backend waits for
the database to be ready and configures everything. You can check the logs to monitor it.
In addition, the first time you start the application, you will need to set up an account in Langfuse and update
the `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_USER_ID` environment variables in the `.env` file.


To check the logs, run:

```bash
docker compose logs
```

To check the logs of a specific service, add the name of the service, e.g.:

```bash
docker compose logs backend
```


### Local development, additional details

By default, the dependencies are managed with [Poetry](https://python-poetry.org/), go there and install it.

From `./backend/` you can install all the dependencies with:

```console
$ poetry install
```

Then you can start a shell session with the new environment with:

```console
$ poetry shell
```

Make sure your editor is using the correct Python virtual environment.

Modify or add SQLModel models for data and SQL tables in `./backend/app/models.py`, API endpoints in `./backend/app/api/`, CRUD (Create, Read, Update, Delete) utils in `./backend/app/crud.py`.

After modifying the environment variables, restart the Docker containers to apply the changes. You can do this by running:

```console
$ docker compose up -d
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
We identify the following areas for contributions:
- Improving the AI agent
- Extending the API to configure multi-AI discussions 
- Refactor the code by moving CRUD-related functions to dedicated CRUD files.
- Implement a more efficient and robust task manager, such as Celery, to handle asynchronous tasks from mutltiple concurrently running brainstorming sessions.

## License

The Full Stack FastAPI Template is licensed under the terms of the MIT license.
