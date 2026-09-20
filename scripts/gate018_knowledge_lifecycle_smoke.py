from __future__ import annotations

import json
import tempfile
from pathlib import Path

from engineering_ai.memory import (
    DecisionEvidenceMemory,
    KnowledgeLifecycle,
    KnowledgeLifecycleLedger,
    MemoryAuthority,
    MemoryKind,
    MemoryRecordDraft,
    MemoryValidationClass,
    PhysicalValidationState,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        memory = DecisionEvidenceMemory(root / "memory.sqlite3")
        ledger = KnowledgeLifecycleLedger(root / "knowledge.sqlite3")
        lifecycle = KnowledgeLifecycle(memory=memory, ledger=ledger)
        try:
            observation = memory.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="gate018-observation",
                    kind=MemoryKind.FAILURE_LESSON,
                    authority=MemoryAuthority.MODEL,
                    validation_class=MemoryValidationClass.ADVISORY,
                    title="Visual engineering observation",
                    summary="Model observation remains advisory.",
                    content={"observation": "inspect connector alignment"},
                    provenance=("model:vision-fixture",),
                )
            )
            source_v1 = memory.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="gate018-source",
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Connector source",
                    summary="Source revision one.",
                    content={"revision": 1},
                    provenance=("source:smoke",),
                    source_refs=("docs/connector-source.md",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                )
            )
            test = memory.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="gate018-validator",
                    kind=MemoryKind.TEST_RESULT,
                    authority=MemoryAuthority.DETERMINISTIC_TOOL,
                    validation_class=MemoryValidationClass.DETERMINISTIC_TEST,
                    title="Connector validator",
                    summary="Deterministic connector check passed.",
                    content={"state": "PASS"},
                    provenance=("tool:smoke",),
                    evidence_refs=("validator:connector:pass",),
                )
            )

            lifecycle.record_observation(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
                claim={"claim": "connector alignment matches accepted source"},
                observation_record_ids=(observation.record_id,),
                provenance=("supervisor:smoke:observation",),
            )
            lifecycle.promote_to_evidence(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
                evidence_record_ids=(source_v1.record_id, test.record_id),
                source_record_ids=(source_v1.record_id,),
                provenance=("supervisor:smoke:evidence",),
            )
            lifecycle.accept(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
                provenance=("supervisor:smoke:accept",),
            )
            accepted = lifecycle.assess(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
            )

            source_v2 = memory.append(
                MemoryRecordDraft(
                    project_id="engineering-ai",
                    memory_id="gate018-source",
                    kind=MemoryKind.SOURCE_REFERENCE,
                    authority=MemoryAuthority.IMPORTED_SOURCE,
                    validation_class=MemoryValidationClass.SOURCE,
                    title="Connector source",
                    summary="Source revision two.",
                    content={"revision": 2},
                    provenance=("source:smoke:update",),
                    source_refs=("docs/connector-source.md",),
                    physical_validation_state=PhysicalValidationState.NOT_APPLICABLE,
                ),
                supersedes_record_id=source_v1.record_id,
            )
            stale = lifecycle.assess(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
            )
            invalidated = lifecycle.invalidate_if_stale(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
                provenance=("supervisor:smoke:source-drift",),
            )
            final = lifecycle.assess(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
            )
            history = lifecycle.history(
                project_id="engineering-ai",
                knowledge_id="gate018-knowledge",
            )
            ledger_integrity = ledger.verify_integrity(
                project_id="engineering-ai"
            )
            memory_integrity = memory.verify_integrity(
                project_id="engineering-ai"
            )

            payload = {
                "gate": "018",
                "state": "PASS_APPEND_ONLY_KNOWLEDGE_LIFECYCLE",
                "observation_validation_class": observation.validation_class.value,
                "accepted_state_before_source_change": accepted.state.value,
                "source_revision_before": source_v1.revision,
                "source_revision_after": source_v2.revision,
                "stale_state": stale.state.value,
                "invalidated_revision": invalidated.revision,
                "final_state": final.state.value,
                "history_revisions": [record.revision for record in history],
                "history_stages": [record.stage.value for record in history],
                "memory_integrity": memory_integrity.ok,
                "lifecycle_integrity": ledger_integrity.ok,
                "automatic_context_injection": False,
                "semantic_vector_backend": "DEFERRED_NOT_JUSTIFIED",
                "physical_validation_inferred": final.physical_validation_inferred,
                "physical_validation": "PHYSICAL_NOT_EXECUTED",
            }
        finally:
            ledger.close()
            memory.close()

    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
