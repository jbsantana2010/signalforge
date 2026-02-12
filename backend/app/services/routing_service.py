"""
Routing service: applies funnel routing rules to lead answers.
"""


def apply_routing_rules(
    routing_rules: dict | None, answers: dict
) -> tuple[list[str], str | None]:
    """
    Input: funnel.routing_rules (JSON), lead.answers_json
    Output: (tags[], priority)

    Rule format:
    {
      "rules": [
        {
          "when": {"field": "service", "equals": "solar"},
          "then": {"tag": "solar", "priority": "high"}
        }
      ]
    }

    First match wins for priority; tags accumulate.
    """
    if not routing_rules:
        return [], None

    rules = routing_rules.get("rules", [])
    tags: list[str] = []
    priority: str | None = None

    for rule in rules:
        condition = rule.get("when", {})
        action = rule.get("then", {})

        field = condition.get("field")
        equals = condition.get("equals")

        if field and equals and answers.get(field) == equals:
            tag = action.get("tag")
            if tag:
                tags.append(tag)
            if priority is None:
                rule_priority = action.get("priority")
                if rule_priority:
                    priority = rule_priority

    return tags, priority
