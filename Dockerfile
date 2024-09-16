# Use the Python 3.12 base image
FROM python:3.12

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Set up the working directory
ADD . /pyTincture/
WORKDIR /pyTincture

# Install the build system dependencies for pyproject.toml
RUN pip install setuptools wheel

# Install the dependencies from pyproject.toml
# Ensure pyproject.toml supports PEP 517/518 with [build-system] defined
RUN pip install .

# Move to the example directory
WORKDIR /pyTincture/example

# Expose the application port
EXPOSE 8070

# Set the entrypoint to run your Python script
ENTRYPOINT ["python", "py_ui.py"]
