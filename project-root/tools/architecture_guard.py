def validate_imports(codebase_graph, rules):
    violations = []

    for edge in codebase_graph.edges:
        if edge in rules["forbidden_edges"]:
            violations.append(edge)

    if violations:
        raise ArchitectureViolation(violations)

    return True