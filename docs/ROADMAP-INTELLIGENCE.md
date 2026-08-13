# MotionLoom Intelligence Roadmap

## Kết luận điều hành

MotionLoom hiện đã vượt qua mức “skill chứa prompt và template”. Repo đã có lifecycle, source binding, runtime evidence, browser review, quality gate, report contract và confirm-to-PR an toàn. Tuy nhiên, phần lớn “trí thông minh” hiện vẫn nằm trong **quy tắc kiểm tra và artifact rời**, chưa nằm trong một mô hình chung để Agent suy luận xuyên suốt dự án.

Định hướng đúng tiếp theo không phải là thêm thật nhiều framework animation. MotionLoom nên trở thành một **evidence-driven animation compiler cho Agent**: đọc dự án, chuyển intent thành motion specification có cấu trúc, chọn capability dựa trên evidence, tạo artifact, kiểm chứng runtime, giải thích sai lệch, đề xuất cách sửa và chỉ cho phép handoff khi toàn bộ chuỗi bằng chứng còn hợp lệ.

> **Mục tiêu:** Agent không chỉ tạo được animation; Agent phải chứng minh animation đó đúng với dự án, đúng nguồn, đúng runtime, đúng accessibility policy và đúng quyết định của reviewer.

## 0. Trạng thái triển khai v0.1

Milestone **Intelligence Core v0.1 đã được triển khai ở lớp trust core**. CLI `scripts/intelligence.py` hiện tạo và validate `project-graph.json`, `provenance.json`, `capability-registry.json`, `motion-ir.json` và `replay-bundle.json`. Quality gate có thể chạy strict với `--require-intelligence`; CI luôn validate capability registry và yêu cầu task bundle đầy đủ cho changed scene. Eval runner `scripts/eval-intelligence.py` hiện chạy bảy case deterministic/adversarial trên clean temporary root.

Phạm vi này chứng minh **artifact relationship, provenance, capability freshness/integrity và replay tamper detection**. Nó chưa phải semantic motion lint, chưa phải recommendation engine và chưa phải MCP server. Những phần đó được giữ ở P1/P2 để không biến heuristic thành acceptance truth trước khi có benchmark đủ mạnh.

### 0.2 Trust-boundary hardening — 1.8.0

Milestone **1.8.0 đã hoàn tất và được merge vào `main`**. Deep audit và regression coverage hiện bảo vệ browser-review lifecycle, report bundle selection, task-root/symlink boundaries, capability evidence paths, provenance attestation paths và deterministic replay binding. Dev Lab artifact intake cũng kiểm tra same-origin, task/scene/candidate identity và browser-review expiry trước khi cho phép staging review.

Audit này không tuyên bố hệ thống đã có cryptographic trust anchor bên ngoài repository. Các guard hiện tại là deterministic repository/runtime checks; approval vẫn chỉ đến từ review artifact hợp lệ và user consent.

### 0.3 Evidence interoperability và runtime observability — 1.9.0

Milestone **1.9.0 đã hoàn tất ở lớp internal evidence interoperability**. Runtime adapter thật ghi `runtime-telemetry.json` tại các scrub point với RAF timing, runtime state hashes và binding tới task, scene, source, manifest và Motion IR. `scripts/evidence-verifier.py` cung cấp verifier read-only với stable JSON result, age/path/symlink guards, cross-task identity checks, tamper detection và invariant `approval: false`.

CI và quality gate đã có capture/verify sequence cùng cờ `--require-telemetry`; report collection và handoff quảng bá verifier report, runtime evidence và telemetry. Dev Lab hiển thị telemetry/verifier/benchmark trong evidence rail và khóa confirm khi integrity hoặc identity binding chưa pass. Đây là integrity contract nội bộ, chưa phải signed DSSE/in-toto trust anchor bên ngoài repository.

## 1. Baseline hiện tại và khoảng trống cần giải quyết

| Lớp | Đã có | Khoảng trống chính | Hậu quả nếu chưa xử lý |
| --- | --- | --- | --- |
| Skill discovery | `SKILL.md`, `agent-card.json`, capability registry v0.1 | Chưa có refresh service và compatibility matrix theo từng browser/library release | Registry tốt hơn flat flags nhưng cần CI refresh có policy và diff review |
| Project awareness | `project-context.json`, context hash, task binding, `project-graph.json` | Graph chưa có semantic constraint nodes và multi-scene supersedes đầy đủ | Agent đã có index quan hệ nhưng chưa suy luận continuity sâu |
| Motion reasoning | `motion-spec.json`, `motion-ir.json`, analyzer/spec pipeline | Semantic lint và compiler intent → adapter plan chưa hoàn chỉnh | Intent phức tạp vẫn cần policy/profile và human review |
| Provenance | Source binding, artifact manifest, `provenance.json`, hash chain, read-only evidence verifier | Chưa có signed attestation/DSSE và external trust anchor | Chuỗi bằng chứng đã verify được nội bộ nhưng chưa chống được repo compromise bằng chữ ký độc lập |
| Runtime | Adapter thật cho Rive, GSAP, Framer Motion; runtime evidence và scrub-point telemetry | Chưa có adapter interface chung và compatibility matrix theo browser/library/version | Telemetry đã so sánh được integrity/runtime state, nhưng compatibility history vẫn cần chuẩn hóa |
| Quality | Schema validation, quality gate, browser review | Semantic lint và continuity checks còn mỏng | File hợp lệ về cấu trúc nhưng vẫn sai nhịp, sai intent hoặc phá UX |
| Review loop | Dev Lab, checklist, `review.json`, expiry/replay protection | Feedback chưa được chuyển thành root-cause/fix-plan có thể chạy lại | Agent thường rerender toàn scene thay vì sửa đúng nguyên nhân |
| Evaluation | Regression scripts, E2E contract và bảy adversarial eval cases | Chưa có benchmark prompt/context đa dạng và aggregate historical metrics | Chưa đủ dữ liệu để khẳng định capability selection trên nhiều dự án |
| Agent integration | CLI, `SKILL.md`, stable JSON errors và side-effect metadata | Chưa có typed resources/tools qua MCP | Host Agent vẫn cần gọi CLI trực tiếp thay vì discover protocol |

## 2. Kiến trúc đích: Motion Graph + Evidence Chain

### 2.1 Canonical Project Motion Graph

Tạo một representation duy nhất, ví dụ `project-graph.json`, thay vì để Agent suy luận từ những file không liên kết. Graph nên có các node `project`, `intent`, `constraint`, `asset`, `source`, `scene`, `motion_spec`, `runtime`, `artifact`, `evidence`, `review` và `decision`. Các edge quan trọng gồm `derived_from`, `uses`, `constrained_by`, `rendered_by`, `verified_by`, `reviewed_as`, `supersedes` và `blocked_by`.

Graph không thay thế các artifact hiện có. Nó là **index có hash và quan hệ**, giúp Agent trả lời được những câu hỏi có tính quyết định: scene này phục vụ intent nào, dùng asset nào, source authority là gì, runtime evidence được tạo bởi adapter/version nào, review nào đã phê duyệt và artifact nào đã trở nên stale sau khi context đổi.

### 2.2 Provenance chain theo từng bước

`artifact-manifest.json` hiện đã là inventory checksum tốt, nhưng chưa phải provenance attestation hoàn chỉnh. Nên bổ sung `provenance.json` theo hướng tương thích với các khái niệm `subject`, `materials`, `build definition`, `builder` và `resolved dependencies` của SLSA [1], đồng thời mô hình hóa chuỗi step/actor/material/product theo in-toto [2].

Mỗi step phải ghi tối thiểu:

| Trường | Ý nghĩa |
| --- | --- |
| `step_id`, `step_type` | Ví dụ `analyze`, `spec`, `source-bind`, `render`, `runtime-test`, `browser-review`, `quality-gate` |
| `actor` | Agent, user, CI hoặc runtime adapter đã thực hiện step |
| `builder` | Toolchain, version, browser và môi trường thực thi |
| `materials[]` | Input path/URI, resolved version và SHA-256 |
| `products[]` | Output path, type và SHA-256 |
| `policy` | Rule set/schema/quality policy được áp dụng |
| `started_at`, `finished_at` | Khoảng thời gian của step |
| `result` | `pass`, `fail`, `blocked` hoặc `needs_review` |
| `parent_attestation` | Liên kết step trước để tạo chain, không chỉ danh sách file |

Ban đầu có thể dùng hash chain và manifest verification. Khi contract ổn định, mới thêm DSSE/signature hoặc SLSA-compatible attestation; không nên ký một format còn thay đổi liên tục.

### 2.3 Capability Registry v2

`agent-card.json` nên chuyển từ danh sách capability sang registry có dữ liệu vận hành. Mỗi capability cần có `id`, `kind`, `status`, `adapter_version`, `supported_inputs`, `supported_outputs`, `browser_matrix`, `evidence`, `last_verified_at`, `limitations`, `fallback` và `risk_level`.

Agent chỉ được chọn capability nếu capability đó thỏa ba điều kiện: input/intent tương thích, evidence chưa quá cũ và runtime/browser hiện tại nằm trong compatibility matrix. `scaffold-only` phải là trạng thái không được dùng cho production trừ khi user chủ động chấp thuận một exception được ghi trong report.

### 2.4 Motion IR và semantic lint

Giữa project intent và framework adapter cần có một **Motion Intermediate Representation** độc lập framework. Motion IR nên mô tả target, property, keyframes hoặc spring, duration, delay, easing, loop, interaction trigger, reduced-motion behavior, performance budget, continuity reference và acceptance assertions.

Semantic lint phải kiểm tra ít nhất bốn lớp:

| Lớp lint | Ví dụ rule |
| --- | --- |
| Intent | Motion emphasis phải có target và reason; “subtle” không được map thành scale quá lớn |
| UX/accessibility | Có reduced-motion fallback; keyboard/assistive action không bị khóa bởi animation |
| Continuity | ID, state, asset anchor và initial pose không đứt giữa các scene liên quan |
| Runtime/performance | Không animate layout khi transform/opacity đủ dùng; duration và layer count nằm trong budget |

Lint không được giả vờ hiểu thẩm mỹ tuyệt đối. Mỗi rule phải phân loại `deterministic`, `heuristic` hoặc `human_required`, kèm confidence và evidence. Đây là ranh giới để MotionLoom không biến một phán đoán xác suất thành quality truth.

### 2.5 Unified Runtime Adapter API

Chuẩn hóa adapter interface thành các hook: `capabilities()`, `prepare()`, `render()`, `capture()`, `assert()`, `collect_evidence()` và `cleanup()`. Rive, GSAP và Framer Motion là các adapter đầu tiên; các runtime khác chỉ được gắn nhãn verified sau khi thực hiện cùng contract.

Evidence nên chứa `adapter_id`, `adapter_version`, `browser_version`, `os`, `source_sha256`, `manifest_sha256`, `motion_ir_sha256`, `frames`, `assertions`, `status` và `replay_command`. Khi render fail, output cần trả về failure class và bước self-correction thay vì chỉ exit code.

### 2.6 Structured review feedback loop

Dev Lab nên ghi feedback thành `fix-plan.json`, không chỉ `notes` tự do. Một fix plan tối thiểu gồm `issue_id`, `category`, `severity`, `observed_at`, `evidence`, `root_cause_hypotheses`, `recommended_patch`, `affected_nodes`, `rerun_scope`, `expected_delta` và `requires_user_decision`.

Ví dụ, “nhịp vào quá gấp” cần được chuyển thành `timing/easing`, trỏ tới keyframe hoặc transition cụ thể, đề xuất giảm acceleration, rerun scene + runtime evidence, và không yêu cầu rerender asset nếu source hash không đổi. Đây là điểm biến Dev Lab từ viewer thành **debugging instrument**.

## 3. Roadmap theo thứ tự ưu tiên

### P0 — Trust core, 0–2 tuần — **Đã hoàn thành v0.1**

P0 đã làm cho MotionLoom **khó báo PASS sai** bằng bốn schema mới: `project-graph.schema.json`, `provenance.schema.json`, `capability-registry.schema.json` và `motion-ir.schema.json`. Các command deterministic được gom trong `scripts/intelligence.py` để giữ một entrypoint ổn định cho Agent và CI.

Eval corpus v0.1 nằm ở `tests/evals/intelligence-cases.json` và runner `scripts/eval-intelligence.py`, bao phủ verified selection, scaffold-only block, stale/tampered capability evidence, graph corruption, replay tamper và foreign-task candidate. P1 cần mở rộng corpus lên prompt/context đa dạng, multi-scene và semantic intent.

**Definition of done P0:** Đạt trong suite hiện tại: candidate/task binding bị reject khi sai; scaffold-only không được chọn; capability evidence stale/tampered bị reject; graph edge hỏng bị reject; replay artifact bị sửa bị reject; quality gate strict kiểm tra graph/provenance/Motion IR/replay cùng browser evidence.

### P1 — Reasoning core, 2–6 tuần

P1 xây compiler từ project graph + intent → Motion IR → adapter plan. Agent phải xuất ra `decision-log.jsonl` với lý do chọn runtime, nguồn asset, trade-off, confidence và câu hỏi cần user quyết định. Thêm semantic lint và policy profiles theo loại sản phẩm: `ui`, `character`, `marketing`, `game`, `accessibility-first`.

Tại giai đoạn này nên đưa `fix-plan.json` vào Dev Lab. Khi reviewer request changes, Agent nhận issue có thể định vị và chạy lại một phần pipeline. Không cần thêm runtime mới nếu ba adapter hiện tại chưa đạt replay/compatibility matrix ổn định.

**Definition of done P1:** với cùng một context, Agent chọn capability đúng trong benchmark; mọi quyết định heuristic có confidence và evidence; reviewer feedback có thể chuyển thành patch plan; rerun scope không làm stale artifact ngoài phạm vi.

### P2 — Protocol and ecosystem, 6–10 tuần

Sau khi core contracts ổn định, expose MotionLoom qua typed CLI trước, sau đó thêm MCP adapter nếu cần interoperability. Theo MCP, resources nên đại diện cho context/task/artifact; prompts hoặc workflow resources đại diện cho playbook; tools đại diện cho prepare, render, inspect, validate và confirm với output schema rõ ràng [4]. Tool execution errors phải actionable để Agent tự sửa, nhưng các side effect như remote push/open PR vẫn phải giữ human-in-the-loop [4].

Mỗi tool cần khai báo `side_effect_level`: `read`, `local_write`, `user_review_required`, `remote_write`. `confirm-to-PR` chỉ được gọi khi có approval authority còn hạn, task identity khớp và quality gate đã pass. Không mở quyền remote write chỉ vì Agent đã nhìn thấy một artifact `approved` cũ.

**Definition of done P2:** host Agent có thể discover capability, lấy resource đúng task, gọi tool typed, nhận lỗi có hướng tự sửa, và không thể gọi remote write khi thiếu approval authority.

### P3 — Scale and learning, sau 10 tuần

P3 thu thập aggregate metrics từ eval và các task thực tế đã được user cho phép. Feedback phải dùng để cải thiện rule, adapter và prompt contract theo phiên bản; không tự động dùng reviewer feedback làm “training truth” nếu chưa được normalize và kiểm duyệt.

Có thể thêm recommendation engine cho runtime/asset, nhưng recommendation phải trả về alternatives, reason, confidence, evidence age và cost/risk. Không nên biến một score nội bộ thành quyết định tự động không thể giải thích.

## 4. Metrics phải đo từ đầu

| Metric | Cách đo | Mục tiêu ban đầu |
| --- | --- | --- |
| Acceptance precision | Tỷ lệ artifact được gate PASS và thực sự không có blocker khi reviewer kiểm tra | ≥ 95% trên eval set có nhãn |
| False approval rate | Tỷ lệ artifact bị quality/review gate cho PASS dù adversarial case phải fail | 0% cho P0 safety rules |
| Provenance completeness | Tỷ lệ node/step có materials, products, actor, policy và hash hợp lệ | ≥ 98% |
| Context retention | Tỷ lệ case Agent giữ đúng project constraints và source authority | ≥ 95% |
| Capability selection accuracy | Tỷ lệ chọn đúng adapter theo intent/input/browser matrix | ≥ 95% |
| Replay success | Tỷ lệ clean replay đạt cùng hashes hoặc trong tolerance đã khai báo | ≥ 98% |
| Fix localization | Tỷ lệ review issue dẫn đến rerun đúng subset thay vì rerender toàn bộ | ≥ 80% ở P1 |
| Handoff completeness | Agent mới chạy được từ `handoff.json` + artifacts mà không đọc chat cũ | 100% trong CI |
| Reviewer burden | Số thao tác/checklist và thời gian từ candidate đến quyết định | Giảm dần, không đánh đổi safety |
| Time-to-fix | Thời gian từ `changes_requested` đến evidence pass tiếp theo | Đo baseline trước, tối ưu sau |

Không dùng một “quality score” tổng hợp làm acceptance truth. Deterministic checks, runtime assertions và human review phải tách riêng; score chỉ dùng để ưu tiên điều tra.

## 5. Cấu trúc repo nên hướng tới

```text
MotionLoom/
├── SKILL.md                         # Activation contract ngắn, progressive disclosure
├── agent-card.json                  # Discovery metadata và capability index
├── schemas/
│   ├── project-graph.schema.json
│   ├── provenance.schema.json
│   ├── capability-registry.schema.json
│   ├── motion-ir.schema.json
│   ├── fix-plan.schema.json
│   └── ...
├── scripts/
│   ├── intelligence.py              # graph/provenance/capability/Motion IR/replay
│   ├── eval-intelligence.py          # deterministic adversarial eval runner
│   ├── lint-motion.py                # P1 semantic lint placeholder
│   └── ...
├── references/
│   ├── motion-ir.md
│   ├── capability-policy.md
│   ├── provenance-policy.md
│   └── runtime-adapter-contract.md
├── tests/evals/
│   ├── intelligence-cases.json
│   └── ...
├── artifacts/
│   └── <task-id>/
│       ├── project-graph.json
│       ├── provenance.json
│       ├── decision-log.jsonl
│       ├── fix-plan.json
│       └── ...
└── dev-lab/
    └── ...
```

## 6. Những việc không nên làm ngay

Không nên thêm Spine, Three.js hoặc nhiều AI generation backend trước khi adapter contract, replay và capability registry đã ổn định. Một danh sách framework dài không tạo ra intelligence nếu Agent không biết runtime nào đã được verify trong môi trường hiện tại.

Không nên dùng LLM judge làm quality gate duy nhất. Judge có thể hỗ trợ triage hoặc gợi ý, nhưng acceptance phải dựa trên schema, hash, runtime assertion, policy và human review có bằng chứng.

Không nên ký provenance vội khi field semantics còn thay đổi. Hãy version schema, chạy migration và xác định trust boundary trước; chữ ký trên metadata không chính xác chỉ tạo cảm giác an toàn giả.

Không nên đưa toàn bộ runbook vào `SKILL.md`. Agent Skills khuyến nghị progressive disclosure và giới hạn phần body chính dưới khoảng 500 dòng [5]. MotionLoom nên giữ activation contract ngắn, còn framework rules và long-form references để trong `references/`.

## 7. Việc nên làm ngay ở milestone kế tiếp

Milestone 1.9.0 đã hoàn tất phần **internal evidence interoperability và runtime observability**. Phase kế tiếp nên chuyển từ integrity checks nội bộ sang **signed attestation và external trust anchor**, không nên thêm framework theo số lượng. Ưu tiên tiếp theo là DSSE/in-toto-compatible attestation, key rotation/revocation policy, external verifier độc lập với repository, asset-level visual comparison có dataset được gắn nhãn và aggregate benchmark history theo project/context/framework.

Trình tự triển khai cụ thể là: version trust-anchor schema trước; tạo clean-room fixtures cho signed attestation; thêm adversarial cases về signature forgery, key substitution, replay và revocation; sau đó mới nâng capability trong `agent-card.json`. Mỗi milestone phải giữ nguyên nguyên tắc: evidence có hash và identity, failure có stable exit code, heuristic không tự thành approval, và side effect GitHub luôn cần explicit confirmation.

### References

[1]: <https://slsa.dev/spec/v1.0/provenance> — SLSA Provenance v1.0.

[2]: <https://github.com/in-toto/docs/blob/master/in-toto-spec.md> — in-toto Specification 1.0.0.

[3]: <https://agentskills.io/skill-creation/evaluating-skills> — Agent Skills: Evaluating skill output quality.

[4]: <https://modelcontextprotocol.io/specification/2026-07-28/server/tools> — Model Context Protocol: Tools.

[5]: <https://agentskills.io/specification> — Agent Skills Specification.
