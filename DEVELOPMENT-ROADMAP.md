# Animation Skill Kit — Development Roadmap

**Mục tiêu:** Phát triển Animation Skill Kit từ một pipeline animation có quality gate thành một **hệ thống production có thể quan sát, phối hợp nhiều Agent và bàn giao artifact có bằng chứng**.

**Baseline:** audit commit `89d40c4`; strategy commit `926c5db`.  
**Verified today:** Lottie JSON runtime render và SVG cutout rig.  
**Not yet runtime-verified:** Rive, GSAP, Framer Motion, Spine và Three.js.

## 1. Product north star

> Agent không chỉ trả lời “đã tạo animation”, mà phải trả lời được: **đã làm gì, dựa trên context nào, artifact nào đã tạo, bước nào đã pass, bước nào chưa làm, vấn đề nào đang block, vì sao chọn framework/asset/skill đó, và Agent tiếp theo có thể tiếp tục từ đâu.**

Animation Skill Kit nên là lớp trung gian giữa **ý định của người dùng**, **host project**, **runtime adapter** và **PR workflow**. Nó không thay thế Agent tổng quát, không thay thế Lottie/Rive/GSAP, và không nên cố đóng gói mọi capability vào một prompt khổng lồ.

## 2. Trạng thái hiện tại

| Hạng mục | Trạng thái | Bằng chứng | Ý nghĩa |
|---|---|---|---|
| Project analysis | Đã có | `analyzer.py`, `project-context.json` | Biết stack/brand/motion language của host project |
| Context binding | Đã có | SHA-256 trong motion spec | Phát hiện project drift |
| Motion spec | Đã có | `src/core/spec.py` | Có category/framework/timing/accessibility |
| SVG cutout rig | Đã verify | 25 assertions, XML validation | Có skeleton body cơ bản và parent-first hierarchy |
| Lottie runtime render | Đã verify | PNG runtime 512×512 RGBA | Có evidence thật, không chỉ kiểm tra JSON |
| Dev Lab | Đã có | snapshot harness 0/50/100 | Người dùng xem và scrub scene |
| Quality gate | Đã có | `scripts/quality-gate.py` | Reject context drift, placeholder, thiếu snapshot/checklist |
| Confirm-to-PR | Đã smoke-test | local Git fixture | Có preflight trước commit; chưa push remote thật |
| Task ledger | Đã có P0 | `scripts/report.py`, `schemas/task.schema.json` | Có lifecycle state và task identity; chưa có remote task store |
| Execution report | Đã có P0 | `execution-report.json`, `REPORT.md` | Có completed/verified/not-completed/problems/structure/next-agent |
| Artifact manifest | Đã có P0 | `scripts/report.py collect`, `artifact-manifest.json` | Có path/type/size/SHA-256 trong task bundle |
| Issue register | Có contract P0 | `issue-register.json`, `report.py add --section problems` | CLI đã ghi được issue; Dev Lab chưa tự đồng bộ issue vào bundle |
| Capability discovery | Đã có P0 | `agent-card.json` | Công bố verified/scaffold runtimes, side effects và public integrations |
| Skill structure validation | Đã có P0 | `scripts/skill-doctor.py`, CI step | Kiểm tra frontmatter, schemas, references; chưa thay thế validator chính thức của từng host Agent |

## 3. Bước tiếp theo có giá trị nhất: Observability Layer

Không nên bắt đầu bằng việc thêm hàng chục template. Bước P0 nên là **Observability Layer**: biến mỗi lần chạy Skill thành một task có trạng thái và bằng chứng.

Mỗi task cần có thư mục:

```text
artifacts/<task-id>/
├── task.json                  # lifecycle + owner + intent + current state
├── execution-report.json      # done/not-done/blocked/failed + evidence
├── decision-log.jsonl         # quyết định và lý do, append-only
├── project-context.json       # context đã dùng
├── motion-spec.json           # contract đã ký
├── artifact-manifest.json     # mọi file output và checksum
├── quality-report.json        # gate results theo rule
├── issue-register.json        # vấn đề, severity, owner, fix status
├── review.json                # feedback người dùng/Agent
└── handoff.json               # hướng dẫn cho Agent tiếp theo
```

### 3.1. State machine của task

```text
created
  → needs_context
  → planning
  → sourcing
  → generating
  → rendering
  → review_required
  → blocked       (thiếu input hoặc consent)
  → failed        (lỗi kỹ thuật)
  → validated
  → ready_for_pr
  → confirmed
```

State chỉ được tiến lên khi artifact tương ứng tồn tại. Ví dụ `validated` phải có quality report pass; `ready_for_pr` phải có review confirmation và runtime evidence; `confirmed` phải có commit SHA hoặc PR URL. Không cho phép Agent tự đặt state bằng prose.

### 3.2. Execution report bắt buộc

Báo cáo user-facing nên có năm phần cố định:

| Phần | Câu hỏi cần trả lời |
|---|---|
| Completed | Đã làm những gì, file nào thay đổi, command nào đã chạy |
| Verified | Điều gì pass, test/evidence nào chứng minh |
| Not completed | Điều gì chưa làm, vì sao chưa làm |
| Blocked / risks | Vấn đề đang block, severity, tác động và owner |
| Next action | Bước tiếp theo, Agent/skill cần gọi và điều kiện để tiếp tục |

Mọi mục nên có `status`, `evidence`, `confidence` và `next_action`. Report không được biến thành nhật ký chat dài; nó phải là artifact JSON có thể render thành Markdown.

## 4. Backlog ưu tiên

### P0 — Trust và observability

| Việc | Acceptance criteria |
|---|---|
| Chuẩn hóa `SKILL.md` bằng YAML frontmatter | `name` và `description` nằm trong frontmatter chuẩn; skill validator pass | **Đã pass** |
| Thêm `agent-card.json` | Khai báo capability, input/output, verified/scaffold runtime và side effects | **Đã pass** |
| Thêm schema task/report/handoff | JSON Schema files và deterministic schema JSON checks có trong test/doctor | **Đã pass P0**; cần validator JSON Schema đầy đủ ở P1 |
| Thêm `skill-doctor` | Phát hiện sai cấu trúc, thiếu file, broken references, missing executable và metadata mismatch | **Đã pass** |
| Thêm execution report generator | Một command tạo report từ task/artifact/quality output, không parse prose | **Đã pass** |
| Bắt buộc report trong CI | Scene có thay đổi nhưng thiếu report/handoff thì CI fail | **Đã pass contract**; cần chạy trên GitHub-hosted PR thật |
| Persist review từ Dev Lab | Dev Lab ghi `review.json` vào artifact thay vì chỉ localStorage/download | **Chưa xong**; CLI đã có, UI integration còn P1 |

### P1 — Domain intelligence

| Việc | Acceptance criteria |
|---|---|
| Canonical Motion IR | Một scene semantics có thể validate độc lập với runtime adapter |
| Adapter contract | Mỗi adapter khai báo supported features và runtime test matrix |
| Asset provenance manifest | Mỗi asset production có source/license/checksum/retrieval metadata |
| Body rig regression corpus | Idle/walk/wave/nod/bounce có visual diff và hierarchy assertions |
| Review-to-rule loop | Feedback được phân loại; chỉ feedback confirmed mới tạo regression rule |
| Accessibility/performance evidence | Có reduced-motion test và size/frame/budget report theo target |

### P2 — Ecosystem và scale

| Việc | Acceptance criteria |
|---|---|
| MCP facade | Resources/prompts/tools tách riêng; tool có side effect yêu cầu consent |
| Remote handoff | Agent khác có thể poll task và lấy artifact bằng task ID |
| Release trust | SBOM, dependency pinning, checksum/signing và permission inventory |
| Runtime adapters | Ít nhất một Rive hoặc GSAP adapter có runtime integration test trước khi mở rộng tiếp |
| Benchmark corpus | Có project fixtures và replay runs để đo context fidelity/handoff success |

## 5. Nên dùng skill công khai nào?

Không nên “gom tất cả skill” vào repo. Hãy dùng skill công khai theo mô hình **reference / adapter / optional dependency**, luôn ghi source, license, version và trust level.

| Skill/repo hoặc nguồn | Nên dùng cho | Không nên giao cho nó | Quyết định |
|---|---|---|---|
| [`LottieFiles/dotlottie-web`](https://github.com/LottieFiles/dotlottie-web/blob/main/SKILL.md) | Runtime API, dotLottie React/vanilla, worker, state machine, slots, exact-frame capture | Project-wide planning, provenance, PR acceptance | **Reuse as official runtime reference**; pin version và adapter-test lại |
| [`diffusionstudio/lottie`](https://github.com/diffusionstudio/lottie) | Text-to-Lottie workflow, scene/player live preview, prompt conventions | Thay thế context binding hoặc quality gate | **Reuse ideas and optional scaffold**; không coi live preview là production verification |
| [`b1rdmania/claude-lottie-skill`](https://github.com/b1rdmania/claude-lottie-skill/blob/main/SKILL.md) | Brand-aware asset search, Lottie/Rive routing, series coherence | License authority, runtime truth, cross-Agent contract | **Use as optional asset-discovery adapter** sau khi audit source/license |
| [`anthropics/skills`](https://github.com/anthropics/skills) | Skill packaging, frontmatter, progressive disclosure và resource layout | Animation domain logic | **Use as format/reference authority** |
| [`github/awesome-copilot`](https://github.com/github/awesome-copilot) | Discover code review, testing, documentation và domain skills | Quality/security authority | **Use as catalog only**; review từng repo trước khi cài |
| [GitHub Agent Skills docs](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) | Portability giữa Copilot cloud, CLI, VS Code, JetBrains và project/personal skill locations | Runtime animation implementation | **Use for distribution compatibility** |
| [Agent Skills specification](https://agentskills.io/specification) | Metadata, discovery và progressive disclosure contract | Domain-specific acceptance | **Use as required packaging contract** |
| [MCP specification](https://modelcontextprotocol.io/specification/2026-07-28) | Tách resources/prompts/tools và consent boundary | Tự quyết định animation có đẹp/đúng hay không | **Use later as transport layer**, after local contract is stable |

### 5.1. Skill nào không nên tự xây lại?

Không nên tự xây lại Lottie runtime, Rive runtime, GSAP timeline engine, MCP transport, Agent Skills discovery hoặc GitHub authentication. Đây là infrastructure đã có nguồn chính thức hoặc ecosystem mạnh. Skill của chúng ta nên xây **context orchestration, motion semantics, evidence, provenance, review memory và quality policy** ở phía trên.

### 5.2. Skill nào nên tự xây?

Nên tự xây các phần gắn với giá trị riêng: `project-context` analyzer, Motion IR, adapter capability matrix, task/report schemas, `skill-doctor`, artifact/handoff bundle, asset provenance policy, runtime evidence gate và review-to-regression workflow.

## 6. Sai cấu trúc và điểm cần fix trước khi quảng bá

| Vấn đề | Mức | Cách fix |
|---|---:|---|
| `SKILL.md` hiện dùng các dòng `name:`/`description:` như Markdown, chưa phải YAML frontmatter chuẩn | P0 | Chuyển thành block `---` đầu file; giữ body dưới 500 dòng |
| Chưa có `references/` để progressive disclosure | P0 | Di chuyển framework-specific guidance vào references và thêm điều kiện đọc |
| Chưa có Agent Card/capability levels | P0 | Thêm `agent-card.json` với `verified_runtimes` và `scaffold_only_runtimes` |
| Chưa có task/report/handoff schemas | P0 | Thêm JSON Schema và validator trong CI |
| Review của Dev Lab mới có localStorage/download | P1 | Nối UI Dev Lab với `report.py review` hoặc một artifact API; có reviewer identity, timestamp, decision và issue list |
| Lottie đã verify nhưng các runtime khác chưa tương đương | P1 | Ghi rõ capability level; chỉ nâng claim sau adapter integration test |
| Attribution chưa phải machine-readable provenance | P1 | Thêm URL/license/checksum/retrieval metadata cho từng asset |
| Chưa có visual regression/performance/a11y corpus | P1 | Tạo fixtures và threshold theo target runtime/device |
| Chưa có release SBOM/signing/permission inventory | P2 | Thêm khi chuẩn bị public marketplace/distribution |

## 7. Quy tắc báo cáo user-facing

Agent dùng Skill phải kết thúc mỗi task bằng một báo cáo ngắn và một artifact đầy đủ. Mẫu Markdown:

```markdown
# Animation Task Report — <task-id>

## Status
- Overall: validated | review_required | blocked | failed | ready_for_pr
- Confidence: high | medium | low
- Context: <project-name> @ <context-hash-short>

## Completed
| Item | Evidence | Status |
|---|---|---|
| ... | file/command/test | pass |

## Not completed
| Item | Reason | Impact |
|---|---|---|
| ... | ... | low/medium/high |

## Problems to fix
| ID | Severity | Problem | Suggested owner | Next action |
|---|---|---|---|---|
| ... | P0/P1/P2 | ... | analyzer/rig/runtime/reviewer | ... |

## Structure review
- Missing files:
- Broken references:
- Untracked artifacts:
- Runtime capability level:

## Recommended next Agent / Skill
1. <skill or Agent> — <why>
2. <skill or Agent> — <why>

## Approval
- Human review: pending | approved | changes_requested
- PR readiness: blocked | ready
```

Báo cáo phải nói rõ khi chưa làm, không được dùng “completed” để che một bước scaffold-only. Khi thiếu context, Agent nên dừng ở `needs_context`; khi runtime chưa verify, nên dừng ở `review_required` hoặc `blocked`; khi chỉ có template, phải ghi `scaffold`, không ghi `production-ready`.

## 8. Metrics cần theo dõi

| Metric | Ý nghĩa |
|---|---|
| Context fidelity | Scene có đúng framework/brand/motion language của host project không |
| Runtime verification rate | Bao nhiêu artifact thực sự chạy qua runtime |
| Report completeness | Bao nhiêu task có đủ completed/not-completed/problems/evidence/handoff |
| Handoff success | Agent tiếp theo có tiếp tục được chỉ bằng artifact bundle không |
| Defect escape rate | Bao nhiêu lỗi chỉ lộ ra sau PR |
| Provenance coverage | Bao nhiêu asset có source/license/checksum |
| Review cycles | Số vòng sửa từ preview đến approval |
| False confidence rate | Tỷ lệ task báo pass nhưng bị reject bởi gate sau đó |

## 9. Kế hoạch hành động khuyến nghị

**Đã triển khai trong worktree:** P0 Observability Layer gồm `agent-card.json`, chuẩn frontmatter, task/report/handoff schemas, `skill-doctor`, execution report generator, structure review, semantic report check và sample `examples/report-demo/`. P0 chưa được xem là hoàn tất tuyệt đối cho tới khi Dev Lab persist review trực tiếp và workflow chạy thành công trên một PR GitHub thật.

**Sau khi P0 pass:** xây Motion IR và adapter contract; chỉ sau đó mở rộng runtime Rive/GSAP. Làm ngược thứ tự sẽ tạo nhiều template nhưng không tăng năng lực suy luận hay độ tin cậy.

**Trước khi công khai rộng:** thêm provenance/attestation, SBOM, runtime matrix, benchmark fixtures và một bộ public example có cả success case lẫn blocked/failure case. Một repo có thể hiện rõ lúc nó **không làm được** thường đáng tin hơn repo chỉ trưng bày demo thành công.

## References

[1]: https://agentskills.io/specification "Agent Skills specification"

[2]: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills "GitHub Agent Skills documentation"

[3]: https://github.com/anthropics/skills "Anthropic skills repository"

[4]: https://github.com/LottieFiles/dotlottie-web/blob/main/SKILL.md "LottieFiles dotLottie Web skill"

[5]: https://github.com/diffusionstudio/lottie "Diffusion Studio text-to-lottie repository"

[6]: https://github.com/b1rdmania/claude-lottie-skill/blob/main/SKILL.md "Claude Lottie animation design skill"

[7]: https://modelcontextprotocol.io/specification/2026-07-28 "Model Context Protocol specification"
