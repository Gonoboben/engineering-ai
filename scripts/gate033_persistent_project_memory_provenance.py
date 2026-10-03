from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from engineering_ai.memory import (
    DecisionEvidenceMemory,
    KnowledgeAssessmentState,
    KnowledgeLifecycle,
    KnowledgeLifecycleLedger,
    KnowledgeLifecyclePolicyError,
    MemoryAuthority,
    MemoryKind,
    MemoryRecordDraft,
    MemoryValidationClass,
    PhysicalValidationState,
    PolicyControlledMemoryRetriever,
    RetrievalRequest,
)
from engineering_ai.validation import validate_instance


ROOT = Path(__file__).resolve().parents[1]


class IdFactory:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._counter = itertools.count(1)

    def __call__(self) -> str:
        return f"{self._prefix}-{next(self._counter):04d}"


def fixed_clock() -> datetime:
    return datetime(2026, 9, 27, 9, 30, 0, tzinfo=timezone.utc)


def run_checked(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "no output"
        raise RuntimeError(f"command failed: {args!r}\n{detail}")
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    for pattern in (
        "test_memory.py",
        "test_retrieval.py",
        "test_knowledge_lifecycle.py",
    ):
        run_checked(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                pattern,
            ]
        )

    head = run_checked(["git", "rev-parse", "HEAD"]).stdout.strip()
    require(len(head) == 40, "exact source revision was not resolved")

    project_a = "engineering-ai"
    project_b = "buoycalc"
    source_memory_id = "gate033-shared-source"
    source_knowledge_id = "gate033-source-bound-knowledge"
    evidence_knowledge_id = "gate033-evidence-bound-knowledge"

    with tempfile.TemporaryDirectory(
        prefix="engineering-ai-gate033-project-memory-"
    ) as tmp:
        root = Path(tmp)
        memory_path = root / "memory.sqlite3"
        lifecycle_path = root / "knowledge-lifecycle.sqlite3"

        memory = DecisionEvidenceMemory(
            memory_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("memrec-gate033-initial"),
        )
        ledger = KnowledgeLifecycleLedger(
            lifecycle_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("knowrec-gate033-initial"),
        )
        lifecycle = KnowledgeLifecycle(memory=memory, ledger=ledger)

        try:
            observation = memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id="gate033-model-observation",
                    kind=MemoryKind.FAILURE_LESSON,
                    authority=MemoryAuthority.MODEL,
                    validation_class=MemoryValidationClass.ADVISORY,
                    title="Gate 033 model observation",
                    summary="Advisory observation retained without evidence authority.",
                    content={"observation": "persistent memory requires provenance"},
                    provenance=("model:gate033-fixture",),
                    physical_validation_state=(
                        PhysicalValidationState.PHYSICAL_NOT_EXECUTED
                    ),
                )
            )
            source_a_v1 = memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id=source_memory_id,
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Gate 033 persistent provenance source",
                    summary="Persistent project memory provenance source revision one.",
                    content={
                        "repository": "Gonoboben/engineering-ai",
                        "revision": head,
                        "phase": "initial",
                    },
                    provenance=(f"gate033:repo@{head}",),
                    source_refs=(f"repo:Gonoboben/engineering-ai@{head}:STATUS.md",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                )
            )
            test_a_v1 = memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id="gate033-validator-result",
                    kind=MemoryKind.TEST_RESULT,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                    title="Gate 033 deterministic memory validator",
                    summary="Persistent project memory acceptance fixture passed.",
                    content={"result": "PASS", "revision": head},
                    provenance=("script:gate033_persistent_project_memory_provenance.py",),
                    evidence_refs=(f"validator:gate033:{head}",),
                    physical_validation_state=(
                        PhysicalValidationState.PHYSICAL_NOT_EXECUTED
                    ),
                )
            )
            source_b = memory.append(
                MemoryRecordDraft(
                    project_id=project_b,
                    memory_id=source_memory_id,
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Gate 033 BuoyCalc isolated source",
                    summary="Same memory identity is isolated by project_id.",
                    content={"project": project_b},
                    provenance=("gate033:cross-project-fixture",),
                    source_refs=("repo:Gonoboben/buoycalc-windows@fixture:RELEASE.md",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                )
            )
            source_evidence_v1 = memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id="gate033-evidence-source",
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Gate 033 evidence drift source",
                    summary="Stable source for independent evidence revision drift.",
                    content={"source": "stable"},
                    provenance=("gate033:evidence-drift-source",),
                    source_refs=("docs/evidence/gate033/fixture-source.md",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                )
            )
            test_evidence_v1 = memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id="gate033-evidence-result",
                    kind=MemoryKind.TEST_RESULT,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                    title="Gate 033 evidence revision validator",
                    summary="Initial deterministic evidence revision.",
                    content={"result": "PASS", "phase": 1},
                    provenance=("gate033:evidence-revision-one",),
                    evidence_refs=("validator:gate033:evidence:v1",),
                    physical_validation_state=(
                        PhysicalValidationState.PHYSICAL_NOT_EXECUTED
                    ),
                )
            )

            for record in (
                observation,
                source_a_v1,
                test_a_v1,
                source_b,
                source_evidence_v1,
                test_evidence_v1,
            ):
                validate_instance("memory-record.schema.json", record.as_dict())

            lifecycle.record_observation(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
                claim={"claim": "project memory remains provenance-bound"},
                observation_record_ids=(observation.record_id,),
                provenance=("supervisor:gate033-source-observation",),
            )
            lifecycle.promote_to_evidence(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
                evidence_record_ids=(source_a_v1.record_id, test_a_v1.record_id),
                source_record_ids=(source_a_v1.record_id,),
                provenance=("supervisor:gate033-source-evidence",),
            )
            accepted_source = lifecycle.accept(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
                provenance=("supervisor:gate033-source-accepted",),
            )

            lifecycle.record_observation(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
                claim={"claim": "evidence revision remains provenance-bound"},
                observation_record_ids=(observation.record_id,),
                provenance=("supervisor:gate033-evidence-observation",),
            )
            lifecycle.promote_to_evidence(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
                evidence_record_ids=(
                    source_evidence_v1.record_id,
                    test_evidence_v1.record_id,
                ),
                source_record_ids=(source_evidence_v1.record_id,),
                provenance=("supervisor:gate033-evidence-qualified",),
            )
            accepted_evidence = lifecycle.accept(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
                provenance=("supervisor:gate033-evidence-accepted",),
            )

            validate_instance(
                "knowledge-lifecycle-record.schema.json",
                accepted_source.as_dict(),
            )
            validate_instance(
                "knowledge-lifecycle-record.schema.json",
                accepted_evidence.as_dict(),
            )

            initial_memory_integrity = memory.verify_integrity(project_id=project_a)
            initial_lifecycle_integrity = ledger.verify_integrity(
                project_id=project_a
            )
            source_history_before = tuple(
                (item.lifecycle_record_id, item.content_sha256)
                for item in lifecycle.history(
                    project_id=project_a,
                    knowledge_id=source_knowledge_id,
                )
            )
            evidence_history_before = tuple(
                (item.lifecycle_record_id, item.content_sha256)
                for item in lifecycle.history(
                    project_id=project_a,
                    knowledge_id=evidence_knowledge_id,
                )
            )
        finally:
            ledger.close()
            memory.close()

        reopened_memory = DecisionEvidenceMemory(
            memory_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("memrec-gate033-reopen"),
        )
        reopened_ledger = KnowledgeLifecycleLedger(
            lifecycle_path,
            clock=fixed_clock,
            record_id_factory=IdFactory("knowrec-gate033-reopen"),
        )
        reopened_lifecycle = KnowledgeLifecycle(
            memory=reopened_memory,
            ledger=reopened_ledger,
        )

        try:
            loaded_source = reopened_memory.get_record(
                project_id=project_a,
                record_id=source_a_v1.record_id,
            )
            require(
                loaded_source.content_sha256 == source_a_v1.content_sha256,
                "source hash changed across close/reopen",
            )
            require(
                loaded_source.revision == source_a_v1.revision
                and loaded_source.provenance == source_a_v1.provenance
                and loaded_source.source_refs == source_a_v1.source_refs,
                "source provenance changed across close/reopen",
            )

            project_a_latest = reopened_memory.latest(
                project_id=project_a,
                memory_id=source_memory_id,
            )
            project_b_latest = reopened_memory.latest(
                project_id=project_b,
                memory_id=source_memory_id,
            )
            require(
                project_a_latest.record_id == source_a_v1.record_id,
                "project A same-memory-id lookup changed",
            )
            require(
                project_b_latest.record_id == source_b.record_id,
                "project B same-memory-id lookup changed",
            )
            require(
                project_a_latest.record_id != project_b_latest.record_id,
                "same memory_id leaked across projects",
            )

            cross_project_get_rejected = False
            try:
                reopened_memory.get_record(
                    project_id=project_a,
                    record_id=source_b.record_id,
                )
            except KeyError:
                cross_project_get_rejected = True
            require(
                cross_project_get_rejected,
                "cross-project record access did not fail closed",
            )

            retriever = PolicyControlledMemoryRetriever(reopened_memory)
            PolicyControlledMemoryRetriever.assert_read_only_surface(retriever)
            package = retriever.retrieve(
                RetrievalRequest(
                    project_id=project_a,
                    query_text="persistent provenance source",
                    max_results=8,
                    max_context_chars=12_000,
                )
            )
            validate_instance("retrieval-context.schema.json", package.as_dict())
            retrieved = tuple(
                item for item in package.items
                if item.record_id == source_a_v1.record_id
            )
            require(len(retrieved) == 1, "reopened source was not retrieved exactly once")
            item = retrieved[0]
            require(
                item.memory_id == source_a_v1.memory_id
                and item.revision == source_a_v1.revision
                and item.provenance == source_a_v1.provenance
                and item.source_refs == source_a_v1.source_refs
                and item.evidence_refs == source_a_v1.evidence_refs
                and item.content_sha256 == source_a_v1.content_sha256,
                "retrieval did not preserve exact source provenance",
            )
            require(
                all(entry.record_id != source_b.record_id for entry in package.items),
                "cross-project record leaked into retrieval",
            )
            require(
                package.as_dict()["automatic_context_injection"] is False,
                "retrieval silently enabled automatic context injection",
            )

            source_current = reopened_lifecycle.assess(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
            )
            evidence_current = reopened_lifecycle.assess(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
            )
            require(
                source_current.state is KnowledgeAssessmentState.ACCEPTED_CURRENT,
                "source-bound knowledge was not current after reopen",
            )
            require(
                evidence_current.state is KnowledgeAssessmentState.ACCEPTED_CURRENT,
                "evidence-bound knowledge was not current after reopen",
            )
            require(
                not source_current.physical_validation_inferred
                and not evidence_current.physical_validation_inferred,
                "knowledge lifecycle inferred physical validation",
            )

            reopened_accepted_source = reopened_ledger.latest(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
            )
            source_bindings = {
                binding.record_id: binding
                for binding in reopened_accepted_source.evidence_bindings
            }
            require(
                source_a_v1.record_id in source_bindings
                and source_bindings[source_a_v1.record_id].revision
                == source_a_v1.revision
                and source_bindings[source_a_v1.record_id].content_sha256
                == source_a_v1.content_sha256,
                "accepted lifecycle lost exact source revision/hash binding",
            )
            require(
                test_a_v1.record_id in source_bindings
                and source_bindings[test_a_v1.record_id].revision
                == test_a_v1.revision
                and source_bindings[test_a_v1.record_id].content_sha256
                == test_a_v1.content_sha256,
                "accepted lifecycle lost exact evidence revision/hash binding",
            )

            reopened_lifecycle.record_observation(
                project_id=project_a,
                knowledge_id="gate033-model-promotion-guard",
                claim={"claim": "model advisory must not become evidence"},
                observation_record_ids=(observation.record_id,),
                provenance=("supervisor:gate033-model-guard",),
            )
            model_promotion_rejected = False
            try:
                reopened_lifecycle.promote_to_evidence(
                    project_id=project_a,
                    knowledge_id="gate033-model-promotion-guard",
                    evidence_record_ids=(observation.record_id,),
                    provenance=("supervisor:gate033-forbidden-model-promotion",),
                )
            except KnowledgeLifecyclePolicyError:
                model_promotion_rejected = True
            require(
                model_promotion_rejected,
                "MODEL/ADVISORY record was promoted to evidence",
            )

            cross_project_lifecycle_rejected = False
            try:
                reopened_lifecycle.record_observation(
                    project_id=project_a,
                    knowledge_id="gate033-cross-project-guard",
                    claim={"claim": "cross-project record must fail closed"},
                    observation_record_ids=(source_b.record_id,),
                    provenance=("supervisor:gate033-cross-project-guard",),
                )
            except KeyError:
                cross_project_lifecycle_rejected = True
            require(
                cross_project_lifecycle_rejected,
                "cross-project lifecycle binding did not fail closed",
            )

            source_a_v2 = reopened_memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id=source_memory_id,
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Gate 033 persistent provenance source",
                    summary="Persistent project memory provenance source revision two.",
                    content={
                        "repository": "Gonoboben/engineering-ai",
                        "revision": head,
                        "phase": "revised",
                    },
                    provenance=(f"gate033:repo@{head}:revised",),
                    source_refs=(f"repo:Gonoboben/engineering-ai@{head}:STATUS.md#revised",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                ),
                supersedes_record_id=source_a_v1.record_id,
            )
            require(
                source_a_v2.revision == 2
                and source_a_v2.supersedes_record_id == source_a_v1.record_id,
                "source supersession identity is not exact",
            )
            source_stale = reopened_lifecycle.assess(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
            )
            require(
                source_stale.state
                is KnowledgeAssessmentState.STALE_SOURCE_REVISION,
                "source revision drift did not produce STALE_SOURCE_REVISION",
            )
            require(
                source_a_v1.record_id in source_stale.stale_source_record_ids,
                "stale source record identity was not preserved",
            )

            test_evidence_v2 = reopened_memory.append(
                MemoryRecordDraft(
                    project_id=project_a,
                    memory_id="gate033-evidence-result",
                    kind=MemoryKind.TEST_RESULT,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                    title="Gate 033 evidence revision validator",
                    summary="Revised deterministic evidence revision.",
                    content={"result": "FAIL", "phase": 2},
                    provenance=("gate033:evidence-revision-two",),
                    evidence_refs=("validator:gate033:evidence:v2",),
                    physical_validation_state=(
                        PhysicalValidationState.PHYSICAL_NOT_EXECUTED
                    ),
                ),
                supersedes_record_id=test_evidence_v1.record_id,
            )
            require(
                test_evidence_v2.revision == 2
                and test_evidence_v2.supersedes_record_id
                == test_evidence_v1.record_id,
                "evidence supersession identity is not exact",
            )
            evidence_stale = reopened_lifecycle.assess(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
            )
            require(
                evidence_stale.state
                is KnowledgeAssessmentState.STALE_EVIDENCE_REVISION,
                "evidence revision drift did not produce STALE_EVIDENCE_REVISION",
            )
            require(
                test_evidence_v1.record_id
                in evidence_stale.stale_evidence_record_ids,
                "stale evidence record identity was not preserved",
            )

            source_history_after_drift = tuple(
                (entry.lifecycle_record_id, entry.content_sha256)
                for entry in reopened_lifecycle.history(
                    project_id=project_a,
                    knowledge_id=source_knowledge_id,
                )
            )
            evidence_history_after_drift = tuple(
                (entry.lifecycle_record_id, entry.content_sha256)
                for entry in reopened_lifecycle.history(
                    project_id=project_a,
                    knowledge_id=evidence_knowledge_id,
                )
            )
            require(
                source_history_after_drift == source_history_before,
                "source drift rewrote lifecycle history",
            )
            require(
                evidence_history_after_drift == evidence_history_before,
                "evidence drift rewrote lifecycle history",
            )

            source_invalidated = reopened_lifecycle.invalidate_if_stale(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
                provenance=("supervisor:gate033-source-drift",),
            )
            evidence_invalidated = reopened_lifecycle.invalidate_if_stale(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
                provenance=("supervisor:gate033-evidence-drift",),
            )
            source_history_final = reopened_lifecycle.history(
                project_id=project_a,
                knowledge_id=source_knowledge_id,
            )
            evidence_history_final = reopened_lifecycle.history(
                project_id=project_a,
                knowledge_id=evidence_knowledge_id,
            )
            require(
                tuple(
                    (entry.lifecycle_record_id, entry.content_sha256)
                    for entry in source_history_final[:3]
                )
                == source_history_before,
                "source invalidation rewrote accepted history",
            )
            require(
                tuple(
                    (entry.lifecycle_record_id, entry.content_sha256)
                    for entry in evidence_history_final[:3]
                )
                == evidence_history_before,
                "evidence invalidation rewrote accepted history",
            )
            require(
                source_invalidated.revision == 4
                and evidence_invalidated.revision == 4,
                "stale invalidation did not append the next lifecycle revision",
            )

            final_memory_integrity = reopened_memory.verify_integrity(
                project_id=project_a
            )
            final_lifecycle_integrity = reopened_ledger.verify_integrity(
                project_id=project_a
            )
            validate_instance(
                "knowledge-assessment.schema.json",
                source_stale.as_dict(),
            )
            validate_instance(
                "knowledge-assessment.schema.json",
                evidence_stale.as_dict(),
            )

            result = {
                "gate": "033",
                "state": "PASS_V1_0_PERSISTENT_PROJECT_MEMORY_PROVENANCE",
                "source_revision": head,
                "persistence": {
                    "memory_database_reopened": True,
                    "lifecycle_database_reopened": True,
                    "source_record_id": source_a_v1.record_id,
                    "source_revision": source_a_v1.revision,
                    "source_content_sha256": source_a_v1.content_sha256,
                    "loaded_source_hash_preserved": (
                        loaded_source.content_sha256 == source_a_v1.content_sha256
                    ),
                    "initial_memory_integrity": initial_memory_integrity.ok,
                    "initial_lifecycle_integrity": initial_lifecycle_integrity.ok,
                    "final_memory_integrity": final_memory_integrity.ok,
                    "final_lifecycle_integrity": final_lifecycle_integrity.ok,
                },
                "retrieval": {
                    "status": package.status.value,
                    "project_id": package.project_id,
                    "record_id": item.record_id,
                    "memory_id": item.memory_id,
                    "revision": item.revision,
                    "content_sha256": item.content_sha256,
                    "provenance": list(item.provenance),
                    "source_refs": list(item.source_refs),
                    "evidence_refs": list(item.evidence_refs),
                    "automatic_context_injection": package.as_dict()[
                        "automatic_context_injection"
                    ],
                },
                "lifecycle": {
                    "source_state_before_drift": source_current.state.value,
                    "source_stale_state": source_stale.state.value,
                    "evidence_state_before_drift": evidence_current.state.value,
                    "evidence_stale_state": evidence_stale.state.value,
                    "source_history_revisions": [
                        entry.revision for entry in source_history_final
                    ],
                    "evidence_history_revisions": [
                        entry.revision for entry in evidence_history_final
                    ],
                    "source_old_history_preserved": True,
                    "evidence_old_history_preserved": True,
                },
                "assertions": {
                    "same_memory_id_project_isolation": True,
                    "cross_project_get_rejected": cross_project_get_rejected,
                    "cross_project_retrieval_rejected": True,
                    "cross_project_lifecycle_rejected": (
                        cross_project_lifecycle_rejected
                    ),
                    "exact_source_revision_sha_binding": True,
                    "exact_evidence_revision_sha_binding": True,
                    "source_revision_drift_detected": True,
                    "evidence_revision_drift_detected": True,
                    "model_advisory_promotion_rejected": model_promotion_rejected,
                    "automatic_model_or_blackboard_injection": False,
                    "semantic_vector_backend": "DEFERRED_NOT_JUSTIFIED",
                    "new_memory_architecture": False,
                    "new_model_qualification": False,
                    "new_tool_authority": False,
                    "new_git_authority": False,
                    "new_network_authority": False,
                    "release_authority": False,
                    "fabrication_authority": False,
                },
                "physical_validation": "PHYSICAL_NOT_EXECUTED",
            }
        finally:
            reopened_ledger.close()
            reopened_memory.close()

    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
