# Use the Python 3.12 base image
FROM python:3.12

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Set up the working directory
ADD . /pyTincture/
WORKDIR /pyTincture

# Install build system and any necessary dependencies for using pyproject.toml
# You can use pip's build system or poetry depending on your setup
RUN pip install build

# Install the dependencies defined in pyproject.toml
RUN python -m build .

# Optional: If you're using Poetry
# RUN pip install poetry
# RUN poetry install --no-root

# Move to the example directory
WORKDIR /pyTincture/example

# Expose the application port
EXPOSE 8070

# Set the entrypoint to run your Python script
ENTRYPOINT ["python", "py_ui.py"]
