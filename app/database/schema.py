"""
Database schema introspection module.
Extracts live schema details (tables, columns, data types, foreign keys, primary keys)
from PostgreSQL to give the LLM accurate context for SQL generation.
"""

from typing import Dict, List, Any
from sqlalchemy import inspect
from app.database.connection import engine


_schema_cache: str | None = None


def inspect_schema() -> Dict[str, Any]:
    """
    Introspect the PostgreSQL database and return structured schema dictionary.
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    schema_info = {}
    
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys = pk_constraint.get("constrained_columns", [])
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        fk_map = {}
        for fk in foreign_keys:
            referred_table = fk.get("referred_table")
            referred_columns = fk.get("referred_columns", [])
            for col, ref_col in zip(fk.get("constrained_columns", []), referred_columns):
                fk_map[col] = f"{referred_table}.{ref_col}"
        
        col_list = []
        for col in columns:
            col_name = col["name"]
            col_type = str(col["type"])
            is_pk = col_name in primary_keys
            fk_target = fk_map.get(col_name)
            
            col_list.append({
                "name": col_name,
                "type": col_type,
                "is_pk": is_pk,
                "foreign_key": fk_target,
            })
            
        schema_info[table_name] = col_list
        
    return schema_info


def format_schema_for_llm(schema_info: Dict[str, Any]) -> str:
    """
    Format structured schema dictionary into a readable text prompt for LLM SQL generation.
    """
    lines: List[str] = []
    
    for table_name, columns in schema_info.items():
        lines.append(f"Table: {table_name}")
        lines.append("Columns:")
        for col in columns:
            col_str = f"  - {col['name']} ({col['type']}"
            if col["is_pk"]:
                col_str += ", PRIMARY KEY"
            if col["foreign_key"]:
                col_str += f", REFERENCES {col['foreign_key']}"
            col_str += ")"
            lines.append(col_str)
        lines.append("")  # Blank line between tables
        
    return "\n".join(lines).strip()


def get_database_schema(force_refresh: bool = False) -> str:
    """
    Get formatted schema string for LLM prompts, with simple in-memory caching.
    """
    global _schema_cache
    if _schema_cache is None or force_refresh:
        schema_dict = inspect_schema()
        _schema_cache = format_schema_for_llm(schema_dict)
    return _schema_cache


if __name__ == "__main__":
    print("Introspecting database schema...")
    print(get_database_schema(force_refresh=True))
