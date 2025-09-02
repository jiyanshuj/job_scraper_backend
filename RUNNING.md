# Running the Job Scraper Backend FastAPI Application

To avoid import errors such as "No module named 'app'", please follow these instructions to run the FastAPI app correctly.

## Prerequisites

- Python 3.8 or higher installed
- All dependencies installed (e.g., using `pip install -r requirements.txt`)

## Recommended way to run the app

1. Open a terminal and navigate to the project root directory (where `app/` and `requirements.txt` are located).

2. Run the FastAPI app using the module syntax:

```bash
python -m app.main
```

This ensures that the `app` package is correctly recognized and imports work as expected.

## Alternative: Using Uvicorn

You can also run the app with Uvicorn from the project root:

```bash
uvicorn app.main:app --reload
```

This will start the development server with auto-reload enabled.

## Notes

- Make sure you have `__init__.py` files in the `app/`, `app/api/`, and `app/api/v1/` directories to mark them as Python packages.
- Do not run the app by executing `app/main.py` directly, as this can cause import errors.
- If you use an IDE, configure the working directory to the project root when running the app.

Following these steps should resolve the "No module named 'app'" import error.
