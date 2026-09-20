"""Supervisor-controlled non-authoritative image-generation worker for Gate 025."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from engineering_ai.models import (
    DeterministicModelRouter,
    ImageGenerationProvider,
    ImageGenerationProviderRequest,
    ModelTaskClass,
    RouteRequest,
    RouteStatus,
)
from engineering_ai.supervisor.core import ProposalExecutionResult, Supervisor, ToolOutcome
from engineering_ai.supervisor.policy import PolicyDecision
from engineering_ai.tools.image_artifact import (
    PngArtifactPublisher,
    PngValidationError,
    PublishedImageArtifact,
)
from engineering_ai.tools.common import ToolAccessError


class ImageGenerationWorkerError(RuntimeError):
    """Base fail-closed image-generation worker error."""


class ImageGenerationRoutingError(ImageGenerationWorkerError):
    """Raised when no evidence-qualified image-generation route exists."""


class ImageGenerationProtocolError(ImageGenerationWorkerError):
    """Raised when provider identity or response contract is violated."""


@dataclass(frozen=True)
class ImageGenerationWorkerRequest:
    project_id: str
    task_id: str
    prompt: str
    width: int
    height: int
    seed: int
    output_relative_path: str
    context_tokens: int = 8192
    max_output_tokens: int = 2048
    timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        project_id = self.project_id.strip()
        task_id = self.task_id.strip()
        prompt = self.prompt.strip()
        output = self.output_relative_path.strip()
        if not project_id or len(project_id) > 128:
            raise ValueError("project_id must contain 1..128 characters")
        if not task_id or len(task_id) > 128:
            raise ValueError("task_id must contain 1..128 characters")
        if not prompt or len(prompt) > 12000:
            raise ValueError("prompt must contain 1..12000 characters")
        if self.width < 64 or self.width > 2048 or self.width % 8:
            raise ValueError("width must be 64..2048 and divisible by 8")
        if self.height < 64 or self.height > 2048 or self.height % 8:
            raise ValueError("height must be 64..2048 and divisible by 8")
        if self.seed < 0 or self.seed > 2**31 - 1:
            raise ValueError("seed must be in [0, 2^31-1]")
        if not output or len(output) > 512:
            raise ValueError("output_relative_path must contain 1..512 characters")
        if self.context_tokens <= 0 or self.max_output_tokens <= 0:
            raise ValueError("routing token budgets must be positive")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise ValueError("timeout_seconds must be in (0, 300]")
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "prompt", prompt)
        object.__setattr__(self, "output_relative_path", output)

    @property
    def prompt_sha256(self) -> str:
        return hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ImageGenerationWorkerResult:
    project_id: str
    task_id: str
    decision: PolicyDecision
    tool_called: bool
    outcome_ok: bool
    route_evidence_refs: tuple[str, ...]
    prompt_sha256: str
    artifact: PublishedImageArtifact | None
    failure_class: str | None
    authority: str = "ADVISORY_CONCEPT_ONLY"
    evidence_eligible: bool = False
    engineering_drawing: bool = False
    physical_validation: str = "PHYSICAL_NOT_EXECUTED"


class ImageGenerationWorker:
    """Generate one bounded local concept image as a proposed patch only."""

    ACTION = "propose_patch"

    def __init__(
        self,
        *,
        provider: ImageGenerationProvider,
        router: DeterministicModelRouter,
        publisher: PngArtifactPublisher,
    ) -> None:
        if not getattr(provider, "local_only", False):
            raise ValueError("Gate 025 accepts local-only image-generation providers")
        self._provider = provider
        self._router = router
        self._publisher = publisher

    def generate_proposal(
        self,
        request: ImageGenerationWorkerRequest,
        *,
        supervisor: Supervisor,
        job: dict,
    ) -> ImageGenerationWorkerResult:
        if job.get("project_id") != request.project_id:
            raise ValueError("image-generation request project_id must match job project_id")

        route = self._router.route(
            RouteRequest(
                task_class=ModelTaskClass.IMAGE_GENERATION,
                context_tokens=request.context_tokens,
                max_output_tokens=request.max_output_tokens,
                requires_image_generation=True,
            )
        )
        if route.status is not RouteStatus.ROUTE or route.model is None or route.provider is None:
            raise ImageGenerationRoutingError(
                f"no evidence-qualified image-generation route: {route.reason}"
            )
        if not route.evidence_refs:
            raise ImageGenerationRoutingError(
                "image-generation route must carry qualification evidence refs"
            )
        if route.provider != self._provider.provider_name:
            raise ImageGenerationRoutingError(
                "routed provider does not match configured image-generation provider"
            )

        holder: dict[str, object] = {}

        def tool(action: str) -> ToolOutcome:
            if action != self.ACTION:
                return ToolOutcome(False, "unexpected image-generation action")
            try:
                provider_response = self._provider.generate(
                    ImageGenerationProviderRequest(
                        model=route.model,
                        prompt=request.prompt,
                        width=request.width,
                        height=request.height,
                        seed=request.seed,
                    ),
                    timeout_seconds=request.timeout_seconds,
                )
                if provider_response.provider != route.provider:
                    raise ImageGenerationProtocolError(
                        "image-generation response provider does not match routed provider"
                    )
                if provider_response.model != route.model:
                    raise ImageGenerationProtocolError(
                        "image-generation response model does not match routed model"
                    )
                if provider_response.media_type != "image/png":
                    raise ImageGenerationProtocolError(
                        "Gate 025 accepts image/png provider output only"
                    )
                artifact = self._publisher.publish(
                    data=provider_response.data,
                    relative_path=request.output_relative_path,
                    expected_width=request.width,
                    expected_height=request.height,
                )
            except ToolAccessError:
                holder["failure_class"] = "IMAGE_ARTIFACT_ACCESS_REJECTED"
                return ToolOutcome(
                    False,
                    "image artifact access boundary rejected the proposal",
                    (
                        f"image-prompt-sha256:{request.prompt_sha256}",
                        *tuple(f"route-evidence:{ref}" for ref in route.evidence_refs),
                    ),
                )
            except PngValidationError:
                holder["failure_class"] = "IMAGE_PNG_VALIDATION_REJECTED"
                return ToolOutcome(
                    False,
                    "generated PNG failed deterministic validation",
                    (
                        f"image-prompt-sha256:{request.prompt_sha256}",
                        *tuple(f"route-evidence:{ref}" for ref in route.evidence_refs),
                    ),
                )
            except ImageGenerationProtocolError:
                holder["failure_class"] = "IMAGE_PROVIDER_PROTOCOL_REJECTED"
                return ToolOutcome(
                    False,
                    "image-generation provider response violated the routed contract",
                    (
                        f"image-prompt-sha256:{request.prompt_sha256}",
                        *tuple(f"route-evidence:{ref}" for ref in route.evidence_refs),
                    ),
                )
            except Exception:
                holder["failure_class"] = "IMAGE_PROVIDER_EXECUTION_FAILED"
                return ToolOutcome(
                    False,
                    "image-generation provider failed closed",
                    (
                        f"image-prompt-sha256:{request.prompt_sha256}",
                        *tuple(f"route-evidence:{ref}" for ref in route.evidence_refs),
                    ),
                )

            holder["artifact"] = artifact
            return ToolOutcome(
                True,
                "non-authoritative concept PNG generated and validated",
                (
                    f"image-prompt-sha256:{request.prompt_sha256}",
                    f"image-artifact-sha256:{artifact.sha256}",
                    *tuple(f"route-evidence:{ref}" for ref in route.evidence_refs),
                ),
            )

        proposal: ProposalExecutionResult = supervisor.evaluate_tool_proposal(
            job=job,
            action=self.ACTION,
            tool=tool,
        )
        artifact = holder.get("artifact")
        if artifact is not None and not isinstance(artifact, PublishedImageArtifact):
            raise TypeError("internal image artifact capture is invalid")
        failure_class = holder.get("failure_class")
        if failure_class is not None and not isinstance(failure_class, str):
            raise TypeError("internal image failure classification is invalid")
        outcome_ok = bool(proposal.outcome is not None and proposal.outcome.ok)

        return ImageGenerationWorkerResult(
            project_id=request.project_id,
            task_id=request.task_id,
            decision=proposal.decision,
            tool_called=proposal.tool_called,
            outcome_ok=outcome_ok,
            route_evidence_refs=route.evidence_refs,
            prompt_sha256=request.prompt_sha256,
            artifact=artifact,
            failure_class=failure_class,
        )
