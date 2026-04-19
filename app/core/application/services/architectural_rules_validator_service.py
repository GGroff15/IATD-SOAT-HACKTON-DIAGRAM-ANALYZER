from dataclasses import dataclass
from enum import Enum

from app.core.domain.entities.architectural_validation import (
    ArchitecturalRuleViolation,
    ArchitecturalValidationResult,
    ViolationSeverity,
)
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.graph import GraphEdge


class ComponentRole(Enum):
    USER = "user"
    API_GATEWAY = "api_gateway"
    SERVICE = "service"
    DATABASE = "database"
    QUEUE = "queue"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ValidationContext:
    node_roles: dict[int, ComponentRole]
    incoming_edges: dict[int, tuple[GraphEdge, ...]]
    outgoing_edges: dict[int, tuple[GraphEdge, ...]]
    complete_edges: tuple[GraphEdge, ...]


class ArchitecturalRulesValidatorService:
    """Applies baseline architectural validation rules to a diagram graph."""

    def __init__(
        self,
        service_fan_out_warning_threshold: int = 4,
        database_fan_in_warning_threshold: int = 4,
    ) -> None:
        if service_fan_out_warning_threshold < 1:
            raise ValueError("service_fan_out_warning_threshold must be >= 1")
        if database_fan_in_warning_threshold < 1:
            raise ValueError("database_fan_in_warning_threshold must be >= 1")

        self.service_fan_out_warning_threshold = service_fan_out_warning_threshold
        self.database_fan_in_warning_threshold = database_fan_in_warning_threshold

    def validate(self, graph: Graph) -> ArchitecturalValidationResult:
        """Validate architectural rules and return all findings."""
        violations: list[ArchitecturalRuleViolation] = []
        seen_findings: set[tuple[str, int | None, int | None, ViolationSeverity]] = set()

        def add_violation(violation: ArchitecturalRuleViolation) -> None:
            key = (violation.code, violation.node_id, violation.edge_id, violation.severity)
            if key in seen_findings:
                return
            seen_findings.add(key)
            violations.append(violation)

        if graph.node_count == 0:
            add_violation(
                ArchitecturalRuleViolation(
                    code="GRAPH_WITHOUT_COMPONENTS",
                    message="Graph must include at least one component node",
                )
            )

        context = self._build_context(graph)

        self._validate_self_dependency_edges(context, add_violation)
        self._validate_required_roles(context, add_violation)
        self._validate_isolated_nodes(context, add_violation)
        self._validate_connection_rules(context, add_violation)
        self._validate_database_usage(context, add_violation)
        self._validate_queue_usage(context, add_violation)
        self._validate_fan_heuristics(context, add_violation)
        self._validate_bidirectional_dependencies(context, add_violation)
        self._validate_cycles(context, add_violation)

        has_errors = any(
            violation.severity == ViolationSeverity.ERROR
            for violation in violations
        )

        return ArchitecturalValidationResult(
            diagram_upload_id=graph.diagram_upload_id,
            is_valid=not has_errors,
            violations=tuple(violations),
        )

    def _build_context(self, graph: Graph) -> ValidationContext:
        node_roles = {
            node.node_id: self._infer_role(
                class_name=node.component.class_name,
                extracted_text=node.component.extracted_text,
            )
            for node in graph.nodes
        }

        incoming_edges: dict[int, list[GraphEdge]] = {node.node_id: [] for node in graph.nodes}
        outgoing_edges: dict[int, list[GraphEdge]] = {node.node_id: [] for node in graph.nodes}
        complete_edges: list[GraphEdge] = []

        for edge in graph.edges:
            if edge.source_node_id is not None and edge.source_node_id in outgoing_edges:
                outgoing_edges[edge.source_node_id].append(edge)

            if edge.target_node_id is not None and edge.target_node_id in incoming_edges:
                incoming_edges[edge.target_node_id].append(edge)

            if edge.source_node_id is not None and edge.target_node_id is not None:
                complete_edges.append(edge)

        return ValidationContext(
            node_roles=node_roles,
            incoming_edges={key: tuple(value) for key, value in incoming_edges.items()},
            outgoing_edges={key: tuple(value) for key, value in outgoing_edges.items()},
            complete_edges=tuple(complete_edges),
        )

    @staticmethod
    def _infer_role(class_name: str, extracted_text: str | None) -> ComponentRole:
        normalized = f"{class_name} {extracted_text or ''}".strip().lower()
        normalized = normalized.replace("_", " ").replace("-", " ")

        if any(token in normalized for token in ("api gateway", "gateway", "ingress")):
            return ComponentRole.API_GATEWAY
        if any(
            token in normalized
            for token in ("database", " db", "db ", "postgres", "mysql", "mongo", "dynamo", "rds")
        ):
            return ComponentRole.DATABASE
        if any(
            token in normalized
            for token in ("queue", "sqs", "kafka", "rabbit", "topic", "pubsub", "event bus")
        ):
            return ComponentRole.QUEUE
        if any(token in normalized for token in ("service", "microservice", "backend", "application")):
            return ComponentRole.SERVICE
        if any(token in normalized for token in ("user", "client", "actor", "customer", "person")):
            return ComponentRole.USER
        return ComponentRole.UNKNOWN

    def _validate_self_dependency_edges(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        for edge in context.complete_edges:
            if edge.source_node_id == edge.target_node_id:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="SELF_DEPENDENCY",
                        message="Components cannot depend on themselves",
                        edge_id=edge.edge_id,
                    )
                )

    def _validate_required_roles(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        if ComponentRole.API_GATEWAY not in context.node_roles.values():
            add_violation(
                ArchitecturalRuleViolation(
                    code="MISSING_API_GATEWAY",
                    message="Graph must include at least one API Gateway",
                )
            )

        if ComponentRole.SERVICE not in context.node_roles.values():
            add_violation(
                ArchitecturalRuleViolation(
                    code="MISSING_SERVICE",
                    message="Graph must include at least one service",
                )
            )

    def _validate_isolated_nodes(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        for node_id in context.node_roles:
            if not context.incoming_edges[node_id] and not context.outgoing_edges[node_id]:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="ISOLATED_NODE",
                        message="Every component must be connected",
                        node_id=node_id,
                    )
                )

    def _validate_connection_rules(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        allowed_connections = {
            (ComponentRole.USER, ComponentRole.API_GATEWAY),
            (ComponentRole.API_GATEWAY, ComponentRole.SERVICE),
            (ComponentRole.SERVICE, ComponentRole.SERVICE),
            (ComponentRole.SERVICE, ComponentRole.DATABASE),
            (ComponentRole.SERVICE, ComponentRole.QUEUE),
            (ComponentRole.QUEUE, ComponentRole.SERVICE),
        }

        for edge in context.complete_edges:
            assert edge.source_node_id is not None
            assert edge.target_node_id is not None

            source_role = context.node_roles[edge.source_node_id]
            target_role = context.node_roles[edge.target_node_id]

            if source_role == ComponentRole.UNKNOWN or target_role == ComponentRole.UNKNOWN:
                continue

            if source_role == ComponentRole.DATABASE:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="DATABASE_MUST_BE_SINK",
                        message="Database components must only receive connections",
                        edge_id=edge.edge_id,
                    )
                )

            if source_role == ComponentRole.QUEUE and target_role != ComponentRole.SERVICE:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="QUEUE_MUST_CONNECT_SERVICES",
                        message="Queue outbound connections must target services",
                        edge_id=edge.edge_id,
                    )
                )

            if target_role == ComponentRole.QUEUE and source_role != ComponentRole.SERVICE:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="QUEUE_MUST_CONNECT_SERVICES",
                        message="Queue inbound connections must originate from services",
                        edge_id=edge.edge_id,
                    )
                )

            if (
                source_role == ComponentRole.API_GATEWAY
                and target_role in {ComponentRole.DATABASE, ComponentRole.QUEUE}
            ):
                add_violation(
                    ArchitecturalRuleViolation(
                        code="API_GATEWAY_FORBIDDEN_TARGET",
                        message="API Gateway must not connect to database or queue",
                        edge_id=edge.edge_id,
                    )
                )

            if (source_role, target_role) not in allowed_connections:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="FORBIDDEN_CONNECTION",
                        message=(
                            f"Forbidden connection: {source_role.value} -> {target_role.value}"
                        ),
                        edge_id=edge.edge_id,
                    )
                )

    def _validate_database_usage(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        for node_id, role in context.node_roles.items():
            if role != ComponentRole.DATABASE:
                continue

            incoming_service_sources = {
                edge.source_node_id
                for edge in context.incoming_edges[node_id]
                if edge.source_node_id is not None
                and context.node_roles.get(edge.source_node_id) == ComponentRole.SERVICE
            }
            if not incoming_service_sources:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="DATABASE_WITHOUT_SERVICE_USAGE",
                        message="Each database should be used by at least one service",
                        node_id=node_id,
                        severity=ViolationSeverity.WARNING,
                    )
                )

    def _validate_queue_usage(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        for node_id, role in context.node_roles.items():
            if role != ComponentRole.QUEUE:
                continue

            producer_count = sum(
                1
                for edge in context.incoming_edges[node_id]
                if edge.source_node_id is not None
                and context.node_roles.get(edge.source_node_id) == ComponentRole.SERVICE
            )
            consumer_count = sum(
                1
                for edge in context.outgoing_edges[node_id]
                if edge.target_node_id is not None
                and context.node_roles.get(edge.target_node_id) == ComponentRole.SERVICE
            )

            if producer_count == 0:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="QUEUE_WITHOUT_PRODUCER",
                        message="Queue should have at least one producer service",
                        node_id=node_id,
                        severity=ViolationSeverity.WARNING,
                    )
                )

            if consumer_count == 0:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="QUEUE_WITHOUT_CONSUMER",
                        message="Queue should have at least one consumer service",
                        node_id=node_id,
                        severity=ViolationSeverity.WARNING,
                    )
                )

    def _validate_fan_heuristics(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        for node_id, role in context.node_roles.items():
            if role == ComponentRole.SERVICE:
                called_services = {
                    edge.target_node_id
                    for edge in context.outgoing_edges[node_id]
                    if edge.target_node_id is not None
                    and context.node_roles.get(edge.target_node_id) == ComponentRole.SERVICE
                }
                if len(called_services) > self.service_fan_out_warning_threshold:
                    add_violation(
                        ArchitecturalRuleViolation(
                            code="GOD_SERVICE_FAN_OUT",
                            message="Service calls too many peer services",
                            node_id=node_id,
                            severity=ViolationSeverity.WARNING,
                        )
                    )

            if role == ComponentRole.DATABASE:
                dependent_services = {
                    edge.source_node_id
                    for edge in context.incoming_edges[node_id]
                    if edge.source_node_id is not None
                    and context.node_roles.get(edge.source_node_id) == ComponentRole.SERVICE
                }
                if len(dependent_services) > self.database_fan_in_warning_threshold:
                    add_violation(
                        ArchitecturalRuleViolation(
                            code="DATABASE_TIGHT_COUPLING",
                            message="Database is depended on by too many services",
                            node_id=node_id,
                            severity=ViolationSeverity.WARNING,
                        )
                    )

    def _validate_bidirectional_dependencies(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        edge_by_pair: dict[tuple[int, int], list[GraphEdge]] = {}
        for edge in context.complete_edges:
            assert edge.source_node_id is not None
            assert edge.target_node_id is not None
            edge_by_pair.setdefault((edge.source_node_id, edge.target_node_id), []).append(edge)

        checked_pairs: set[tuple[int, int]] = set()
        for source_id, target_id in edge_by_pair:
            pair_key = tuple(sorted((source_id, target_id)))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            forward_edges = edge_by_pair.get((source_id, target_id), [])
            reverse_edges = edge_by_pair.get((target_id, source_id), [])
            if not forward_edges or not reverse_edges:
                continue

            has_sync_forward = any(self._is_sync_edge(edge) for edge in forward_edges)
            has_sync_reverse = any(self._is_sync_edge(edge) for edge in reverse_edges)
            if has_sync_forward and has_sync_reverse:
                add_violation(
                    ArchitecturalRuleViolation(
                        code="BIDIRECTIONAL_DEPENDENCY",
                        message="Bidirectional synchronous dependencies are an anti-pattern",
                        edge_id=forward_edges[0].edge_id,
                    )
                )

    def _validate_cycles(
        self,
        context: ValidationContext,
        add_violation,
    ) -> None:
        for strongly_connected_component in self._find_strongly_connected_components(context):
            if len(strongly_connected_component) < 2:
                continue

            component_nodes = set(strongly_connected_component)
            component_edges = [
                edge
                for edge in context.complete_edges
                if edge.source_node_id in component_nodes and edge.target_node_id in component_nodes
            ]
            if not component_edges:
                continue

            is_async_cycle = any(not self._is_sync_edge(edge) for edge in component_edges)
            violation_code = "ASYNC_CYCLE_DETECTED" if is_async_cycle else "SYNC_CYCLE_DETECTED"
            severity = ViolationSeverity.WARNING if is_async_cycle else ViolationSeverity.ERROR
            add_violation(
                ArchitecturalRuleViolation(
                    code=violation_code,
                    message=(
                        f"Cycle detected across nodes: {sorted(component_nodes)}"
                    ),
                    node_id=min(component_nodes),
                    severity=severity,
                )
            )

    @staticmethod
    def _is_sync_edge(edge: GraphEdge) -> bool:
        return edge.connection_type in {
            edge.connection_type.ARROW,
            edge.connection_type.STRAIGHT,
            edge.connection_type.CURVED,
        }

    @staticmethod
    def _find_strongly_connected_components(context: ValidationContext) -> tuple[tuple[int, ...], ...]:
        adjacency: dict[int, list[int]] = {node_id: [] for node_id in context.node_roles}
        for edge in context.complete_edges:
            assert edge.source_node_id is not None
            assert edge.target_node_id is not None
            adjacency[edge.source_node_id].append(edge.target_node_id)

        index = 0
        stack: list[int] = []
        on_stack: set[int] = set()
        indices: dict[int, int] = {}
        low_links: dict[int, int] = {}
        components: list[tuple[int, ...]] = []

        def strong_connect(node_id: int) -> None:
            nonlocal index
            indices[node_id] = index
            low_links[node_id] = index
            index += 1
            stack.append(node_id)
            on_stack.add(node_id)

            for neighbor in adjacency[node_id]:
                if neighbor not in indices:
                    strong_connect(neighbor)
                    low_links[node_id] = min(low_links[node_id], low_links[neighbor])
                elif neighbor in on_stack:
                    low_links[node_id] = min(low_links[node_id], indices[neighbor])

            if low_links[node_id] != indices[node_id]:
                return

            component_nodes: list[int] = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component_nodes.append(current)
                if current == node_id:
                    break
            components.append(tuple(component_nodes))

        for node_id in adjacency:
            if node_id not in indices:
                strong_connect(node_id)

        return tuple(components)
