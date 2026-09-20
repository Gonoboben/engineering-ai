# Gate 025 — Non-authoritative image-generation worker evidence

## Gate identity
- Issue: #49 — Gate 025 — Non-authoritative image-generation worker
- PR: #50
- Branch: `gate-025-non-authoritative-image-generation-worker`
- Base: Gate 024 accepted squash merge `99a8e216dc2c8ec7b98c445f0e1909479bff6b52`
- Physical validation: `PHYSICAL_NOT_EXECUTED`

## Objective
Provide bounded local text-to-image generation for concept/visual ideation while
preserving the accepted Supervisor authority and evidence hierarchy.

Generated imagery is never accepted as an engineering drawing, CAD, schematic,
measurement, fabrication instruction or physical evidence by Gate 025.

## Implemented boundary

### Deterministic routing
- Added task class: `IMAGE_GENERATION`.
- Routing requires `supports_image_generation=true`.
- Route must carry explicit qualification evidence references.
- The accepted production registry intentionally contains no image-generation
  model/provider.
- Default accepted route: `NO_ROUTE`.
- No production capability is inferred from model/provider naming or advertised
  features.

### Provider contract
The provider-neutral contract accepts only:
- routed model identity;
- bounded text prompt;
- requested raster width/height;
- deterministic seed.

Gate 025 requires `local_only=true`.

The provider receives no:
- project filesystem path;
- arbitrary file/URL input;
- reference image;
- shell/Git/tool surface;
- Supervisor policy/approval authority;
- external/cloud disclosure path.

### Supervisor authority
Image publication maps only to the already accepted `propose_patch` action.

Current Supervisor/PolicyEngine is evaluated before the provider is called.

Verified:
- route unavailable -> provider calls: 0;
- policy denial -> provider calls: 0;
- no target artifact on denied path.

### Deterministic PNG validation
Accepted output is PNG only.

Validation checks:
- exact PNG signature;
- bounded payload size;
- chunk boundaries;
- CRC of every chunk;
- first chunk is exactly 13-byte IHDR;
- duplicate IHDR rejected;
- positive bounded dimensions;
- Gate 025 baseline accepts only 8-bit RGB/RGBA;
- standard compression/filter and non-interlaced raster;
- one or more IDAT chunks;
- zlib-decodable combined IDAT stream;
- exact decompressed raster byte length;
- valid per-scanline filter values;
- zero-length IEND;
- no trailing bytes after IEND;
- exact requested width/height.

### Publication boundary
- relative PNG path only;
- forward-slash path syntax only;
- no absolute path;
- no `.` / `..` traversal component;
- no path or parent symlink traversal;
- configured root containment;
- atomic temporary-file -> target replacement only after deterministic PNG PASS.

### Result authority
Every successful result is fixed to:
- `authority=ADVISORY_CONCEPT_ONLY`;
- `evidence_eligible=false`;
- `engineering_drawing=false`;
- `physical_validation=PHYSICAL_NOT_EXECUTED`.

Prompt identity and image-byte identity are SHA-256 recorded. Image SHA-256
proves byte identity only; it does not prove semantic or engineering correctness.

## Validation

### Full worker + smoke checkpoint
Head:
`a5bb614a430a0d5b00d3adab57c4a62fd1b41e7f`

Deterministic regression:
`301/301 PASS`

Generic workflow:
`35531846754 PASS`

Strict exact-head workflow:
`35531846777 PASS`

Smoke:
`PASS_NON_AUTHORITATIVE_IMAGE_GENERATION_BOUNDARY`

Smoke verified:
- unmeasured default image-generation route: `NO_ROUTE`;
- provider calls before qualified route: `0`;
- policy-denial provider calls: `0`;
- qualified synthetic provider calls: `1`;
- dimension mismatch: `BLOCKED`;
- dimension-mismatch artifact published: `false`;
- artifact authority: `ADVISORY_CONCEPT_ONLY`;
- evidence eligible: `false`;
- engineering drawing: `false`;
- external network: `false`;
- automatic evidence promotion: `false`;
- production image model qualified: `false`;
- fabrication authority: `false`;
- release authority: `false`;
- physical validation: `PHYSICAL_NOT_EXECUTED`.

### PNG hardening checkpoint
Head:
`93991af1b5b7505ce0546dd58297daf810d6409e`

Additional hardening:
- zlib raster decode required;
- exact raster length required;
- scanline filters validated;
- baseline narrowed to deterministic 8-bit RGB/RGBA non-interlaced PNG;
- ambiguous backslash target paths rejected.

Validation:
- generic workflow `35531878630`: `PASS`;
- strict exact-head workflow `35531878735`: `PASS`.

## Real production/runtime state
- production image-generation model/provider qualification:
  `NOT_RUN / NOT_QUALIFIED`;
- accepted production image-generation route: `NO_ROUTE`;
- real local image-generation provider call: `NOT_RUN`;
- external/cloud image-generation call: `NOT_RUN / OUT_OF_SCOPE`;
- reference-image editing: `NOT_IMPLEMENTED_GATE_025`;
- semantic image-quality engineering validation: `NOT_APPLICABLE_AS_DETERMINISTIC_EVIDENCE`.

Synthetic provider PASS validates the control/evidence/publication boundary only.
It does not qualify a production image model.

## Evidence semantics
Deterministically eligible narrow facts:
- exact prompt SHA-256;
- exact generated PNG SHA-256;
- PNG structural/raster validity;
- actual pixel dimensions;
- exact target artifact path inside configured root;
- exact routed synthetic capability evidence reference in acceptance tests.

Not engineering evidence:
- depicted dimensions;
- depicted topology;
- component values;
- safety;
- manufacturability;
- CAD geometry;
- schematic correctness;
- physical behaviour;
- design intent.

Any engineering use of generated imagery requires reconstruction in an
authoritative engineering representation followed by normal deterministic
validation.

## Runtime scope review
Confirmed absent:
- new autonomous image-generation/write permission;
- external/cloud provider implementation;
- model-supplied tool/shell/Git authority;
- arbitrary filesystem/URL/reference-image acquisition;
- automatic evidence promotion;
- engineering-drawing promotion;
- fabrication/release authorization;
- PHYSICAL_PASS synthesis;
- architecture/physics authority expansion.

## Decision state
ADR-0024 remains `PROPOSED_GATE_025` until explicit exact-SHA human
squash-merge approval and accepted merge of PR #50.
