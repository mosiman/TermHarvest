# CRUSH.md - SpaceApps 2025 Project

## Build & Development Commands
- `uv run main.py` - Run the main application
- `uv run basedpyright main.py` - Type check with strict settings
- `uv run basedpyright --level warning main.py` - Type check with warnings only
- `uv sync` - Install dependencies
- `uv add <package>` - Add new dependency

## Code Style Guidelines
- **Python Version**: 3.12+
- **Type Annotations**: Full type hints required (BasedPyright enforced)
- **Imports**: Standard library first, then third-party, then local
- **Formatting**: Follow PEP 8, use 4-space indentation
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use proper exception handling with specific exceptions

## Textual Framework Conventions
- Use proper generic typing for Textual components: `Screen[object]`, `App[object]`
- Mark override methods with `@override` decorator
- Annotate all class attributes with type hints
- Initialize all instance variables in `__init__`

## Project Structure
- Main entry: `main.py`
- CSS files: `*.tcss`
- Data exploration: `explore_aquacrop.py`
- Dependencies managed by `uv` with `pyproject.toml`

## Key Libraries
- Textual: GUI framework
- AquaCrop: Agricultural modeling
- Polars/DuckDB: Data processing
- Matplotlib: Visualization