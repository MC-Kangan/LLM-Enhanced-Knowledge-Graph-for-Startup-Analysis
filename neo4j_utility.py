import json
from edgar import Company

def escape_quotes_for_cypher(value):
    """Escape single quotes in a string for use in Cypher queries."""
    if isinstance(value, str):
        return value.replace("'", "\\'")
    return value


def dict_to_cypher_create_node(data, node_label):
    """
    Generates a Cypher CREATE statement for a node from a dictionary,
    converting nested structures to JSON strings.

    Args:
    data (dict): Dictionary containing the node properties.
    node_label (str): Label of the node in Neo4j.

    Returns:
    str: A Cypher CREATE statement.
    """
    properties = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            # Convert dictionaries and lists to JSON strings and escape single quotes
            json_value = json.dumps(value)
            escaped_value = escape_quotes_for_cypher(json_value)
            value = f"'{escaped_value}'"
        elif isinstance(value, bool):
            # Convert Python's True/False to Cypher's true/false
            value = str(value).lower()
        elif isinstance(value, str):
            # Escape single quotes in strings
            escaped_value = escape_quotes_for_cypher(value)
            value = f"'{escaped_value}'"
        else:
            value = str(value)

        properties.append(f"{key}: {value}")

    properties_str = ", ".join(properties)
    create_statement = f"CREATE (:{node_label} {{{properties_str}}})"
    return create_statement


def get_company_info_from_cik(cik):
    company = Company(cik)
    return company.to_dict(), company
