import json

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph


class MistralArchitecturePromptBuilder:
    """Builds an instruction prompt optimized for Mistral 7B JSON output."""

    def build_messages(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
    ) -> tuple[dict[str, str], ...]:
        graph_payload = {
            "diagram_upload_id": str(graph.diagram_upload_id),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "class_name": node.component.class_name,
                    "label": node.component.extracted_text or "",
                }
                for node in graph.nodes
            ],
            "edges": [
                {
                    "edge_id": edge.edge_id,
                    "connection_type": edge.connection_type.value,
                    "source_node_id": edge.source_node_id,
                    "target_node_id": edge.target_node_id,
                }
                for edge in graph.edges
            ],
        }
        violations_payload = [
            {
                "code": violation.code,
                "message": violation.message,
                "severity": violation.severity.value,
                "node_id": violation.node_id,
                "edge_id": violation.edge_id,
            }
            for violation in validation_result.violations
        ]

        system_prompt = (
            "As an architect or developer, analyze a graph structure representing a software system, "
            "where nodes denote components and directional edges indicate data/control flow. "
            "These graphs come from previously identified architectural violations. "
            "Your goal is to assess risks, generate recommendations, and prepare a summary report for stakeholders.\n\n"
            "Use this approach:\n"
            "1. Load graph data preserving node identities, edges, and violations linked to nodes.\n"
            "2. Analyze structure with focus on highly interconnected clusters and nodes with high fan-in/fan-out.\n"
            "3. For each violation, assess severity considering performance impact, error/security potential, and fix complexity/cost.\n"
            "4. Assign a risk score per node based on violation severity and component criticality.\n"
            "5. Identify systemic patterns/trends such as recurring violations or violation clusters.\n"
            "6. Prioritize improvements by risk, impact, and implementation effort.\n"
            "7. Prepare a report covering: architecture overview, prioritized risks, detailed recommendations "
            "with expected benefits and estimated effort, and clear next steps.\n\n"
            "Return ONLY valid JSON with this schema: "
            "{"
            '"risks": ["..."], '
            '"recommendations": ["summary first", "recommendation 2", "recommendation 3"]'
            "}. "
            "The first recommendations item MUST be the concise overall summary. "
            "Do not include markdown, comments, or extra fields."
        )
        user_prompt = (
            "Analyze the architecture graph and rule violations below.\n\n"
            f"graph={json.dumps(graph_payload, ensure_ascii=True)}\n"
            f"violations={json.dumps(violations_payload, ensure_ascii=True)}\n\n"
            "Focus on practical architectural risks and concrete recommendations."
        )

        return (
            {"role": "user", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        )
