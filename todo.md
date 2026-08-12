# Audit checklist — MotionLoom

- [x] Đọc skill-creator và xác định quy trình cập nhật skill an toàn.
- [x] Kiểm tra cấu trúc repo, tài liệu, package/dependency và executable scripts.
- [x] Trace end-to-end: analyze → spec → source → generate/rig → render → Dev Lab → quality → PR.
- [x] Kiểm tra CLI help, đường dẫn tương đối, cwd, environment và lỗi dependency.
- [x] Đối chiếu framework, Lottie/dotLottie, Rive, GSAP, Framer Motion, rigging và asset attribution với nguồn chuẩn.
- [x] Kiểm tra project-context có thực sự được dùng xuyên suốt hay chỉ được tạo rồi bỏ qua.
- [x] Kiểm tra render snapshot là render thật hay placeholder/fallback; phân biệt rõ trong quality gate.
- [x] Kiểm tra Dev Lab có kết nối với scene output/spec/checklist thực tế hay chỉ là demo tĩnh.
- [x] Sửa các lỗi xác nhận được; không che giấu lỗi bằng mock hoặc placeholder trong acceptance path.
- [x] Bổ sung test cho happy path, failure path, path resolution, project binding và PR preflight.
- [x] Chạy lại test, smoke test CLI, kiểm tra CI YAML và tạo báo cáo audit.
- [x] Đóng gói bản repo đã audit và bàn giao changelog, rủi ro còn lại, hướng dẫn GitHub.

## Confirmed findings fixed

- Renderer Node truyền local file path vào dotLottie runtime, gây `Failed to parse URL`; đã chuyển sang `data` bằng parsed JSON/bytes.
- dotLottie validator chọn JSON đầu tiên trong ZIP, bỏ qua `manifest.json`; đã chuyển sang chọn `initial.animation`/manifest entry dưới `a/`.
- Cutout rig parser nuốt cả group geometry và phát sinh SVG XML không hợp lệ; đã giới hạn mapping theo primitive/group có `data-part`.
- Placeholder snapshot có thể trông hợp lệ; quality gate hiện bắt buộc `.render-meta.json` với `mode: runtime`.
- `pr.sh` phụ thuộc cwd và có nguy cơ bỏ qua snapshot do `.gitignore`; đã chuyển về repo root, thêm Git guard và cho phép track PNG.
- CI thiếu dependency/browser và có bước YAML sai; đã bổ sung install/runtime preparation và context-aware gate.

## Strategy research

- [x] Đối chiếu các pattern skill/agent repo phổ biến và nguồn chính thức về interoperability.
- [x] So sánh Animation Skill Kit theo các chiều: context, contract, provenance, runtime evidence, feedback loop và PR.
- [x] Xác định năng lực khác biệt bền vững, tránh chỉ thêm prompt/template.
- [x] Thiết kế contract phối hợp Agent, capability discovery và handoff schema.
- [x] Đề xuất roadmap P0/P1/P2 cùng metric đo chất lượng và lợi ích thực tế.

## Depth and transparency roadmap

- [x] Xác định product north star và ranh giới giữa Skill, Agent, runtime adapter và Dev Lab.
- [x] Audit lại cấu trúc repo theo Agent Skills specification và phân loại P0/P1/P2.
- [x] Thiết kế task ledger với state machine, execution log và decision log.
- [x] Thiết kế execution report: done, not done, blocked, failed, risks, changed files và evidence.
- [x] Thiết kế artifact manifest, issue register, fix plan và Agent handoff contract.
- [x] Nghiên cứu skill công khai có thể reuse; ghi rõ license, trust, capability và giới hạn.
- [x] Chọn phần nên reuse, adapter hóa hoặc tự xây; không duplicate skill ecosystem.
- [x] Định nghĩa CI/release gate cho report completeness, schema validation và provenance.
- [x] Đề xuất roadmap triển khai và metrics theo dõi giá trị thực tế.

## Browser review lifecycle

- [ ] Đưa `browser_review_required` vào lifecycle sau runtime render.
- [ ] Định nghĩa candidate manifest gồm scene URL/path, runtime, frame checkpoints, context hash và evidence.
- [ ] Định nghĩa Agent handoff action để kích hoạt hoặc đề xuất Web Agent mở Dev Lab nội bộ.
- [ ] Buộc Dev Lab nạp đúng candidate output, không dùng demo scene khác nguồn.
- [ ] Ghi review result, feedback, screenshot/evidence và user approval vào artifact bundle.
- [ ] Chặn `ready_for_pr`/`confirmed` nếu chưa có review approval hợp lệ.
- [ ] Thêm test flow generate → render → browser review → fix hoặc confirm.
- [ ] Cập nhật SKILL.md, Agent Card, README và báo cáo mẫu với browser-review contract.

## Runtime and provenance upgrade

- [x] Tạo `scripts/to-dotlottie.sh` với manifest/animation entry validation và checksum output.
- [x] Thêm test đóng gói `.lottie`, giải nén, kiểm tra `manifest.json`, `initial.animation` và round-trip runtime load.
- [x] Định nghĩa `source-binding` schema bắt buộc trong production `manifest.json` với source path, authority, license và checksum.
- [x] Cập nhật analyzer, report, quality gate và fixture để reject manifest thiếu hoặc sai source binding.
- [x] Xây runtime adapter test thật cho Rive: load `.riv`, state machine/input binding, reduced-motion và snapshot evidence.
- [x] Xây runtime adapter test thật cho GSAP: execute scene trong browser harness, scrub deterministic timeline và snapshot evidence.
- [x] Xây runtime adapter test thật cho Framer Motion: render React scene trong browser harness, reduced-motion và snapshot evidence.
- [x] Chỉ nâng capability declarations từ `scaffold_only` lên `verified` sau khi adapter evidence và CI gate pass.
- [x] Cập nhật SKILL.md, Agent Card, README, runtime capability reference và CI theo capability levels mới.

## GitHub MotionLoom release

- [x] Kiểm tra GitHub remote, branch hiện tại, working tree và authentication.
- [x] Chuẩn hóa public branding thành MotionLoom nếu cần, không làm mất lịch sử hoặc contract runtime.
- [x] Chạy lại quality checks và xác nhận archive/release files trước khi push.
- [x] Cấu hình `https://github.com/lenhonbp/MotionLoom.git` làm origin và push branch chính.
- [x] Xác minh commit, branch, remote URL và repository contents sau khi push.

## Deep audit and development pass

- [ ] Kiểm tra trạng thái GitHub Actions thực tế và khả năng tái lập CI từ clean checkout.
- [ ] Audit toàn bộ CLI theo nhiều working directory, missing dependency, malformed input và path traversal.
- [ ] Kiểm tra schema cross-reference, artifact provenance, checksum validation và các đường bypass quality gate.
- [ ] Kiểm tra runtime adapter evidence có chống stale output, framework mismatch và evidence giả hay không.
- [ ] Audit browser-review candidate identity, approval replay, expiry và transition state machine.
- [ ] Đánh giá Dev Lab có load candidate thật từ artifact bundle hay còn phụ thuộc catalog/demo data.
- [ ] Bổ sung các test hoặc hardening có giá trị sau audit, ưu tiên lỗi có thể làm PR gate sai.
- [ ] Tạo deep-audit report với mức độ rủi ro, bằng chứng, remediation và giới hạn còn lại.

## Approved end-to-end browser review execution

- [x] Tạo task bundle có scene, context, source binding, runtime snapshots và execution report đầy đủ.
- [x] Chạy `review-hook.py prepare` để tạo candidate identity-bound, expiry-bound và URL có artifact/task base.
- [x] Mở đúng candidate URL bằng Dev Lab browser nội bộ, kiểm tra frame 0/50/100, checklist và task evidence rail.
- [x] Ghi `review.json` với reviewer, decision, timestamp, feedback và candidate/task identity khớp.
- [x] Chạy `review-hook.py validate --require-approved` và `quality-gate.py --require-browser-review` trên cùng task bundle.
- [x] Chạy `pr.sh` với `OPEN_PR=0`, xác nhận commit local-only và chứng minh không mở/push PR ngoài ý muốn.
- [x] Lưu execution evidence, cập nhật report/handoff và bổ sung test tái lập flow từ clean task bundle.

## Next-depth architecture roadmap

- [ ] Xây canonical project graph từ context, source, scene, runtime, artifact và review để Agent reasoning trên quan hệ thay vì file rời.
- [ ] Bổ sung uncertainty/confidence contract và provenance chain cho mọi quyết định generate, chọn framework, chọn asset và quality gate.
- [ ] Tạo capability registry có version, adapter health, evidence age và compatibility matrix thay cho capability flag tĩnh.
- [ ] Xây semantic animation linting: kiểm tra intent, timing, accessibility, continuity và anti-pattern trước runtime render.
- [ ] Chuẩn hóa deterministic replay bundle để tái hiện cùng scene từ clean checkout, lockfile, browser/runtime version và input hashes.
- [ ] Thêm mutation/adversarial tests cho stale evidence, context drift, manifest tampering, replay approval và cross-task contamination.
- [ ] Xây feedback loop từ Dev Lab thành structured fix plan để Agent sửa đúng nguyên nhân thay vì chỉ rerender toàn scene.
- [ ] Định nghĩa benchmark suite và metrics: acceptance precision, false approval rate, provenance completeness, replay success và time-to-fix.
- [ ] Tách release channels/compatibility policy cho core contracts, runtime adapters, Dev Lab protocol và Agent-facing SKILL.md.

## Intelligence Core v0.1 implementation

- [x] Thêm schema `project-graph`, `provenance`, `capability-registry` và `motion-ir` với version/policy rõ ràng.
- [x] Xây CLI tạo/validate project graph từ task context, scene manifest, motion spec, runtime evidence và review.
- [x] Xây provenance emitter/validator cho từng step và liên kết parent attestation, materials, products, actor và builder.
- [x] Nâng capability discovery từ flat flags thành registry có adapter version, evidence age, browser matrix, fallback và risk.
- [x] Thêm deterministic replay command ghi environment, input hashes, output hashes và tolerance policy.
- [x] Tạo eval corpus và adversarial fixtures cho context drift, stale evidence, tampering, unsupported runtime và cross-task contamination.
- [x] Tích hợp các contract mới vào report lifecycle, quality gate, Skill Doctor, CI và smoke fixtures.
- [x] Cập nhật SKILL.md/agent-card/references theo progressive disclosure và chạy full validation trước milestone commit.

## Intelligence Core P1 implementation

- [x] Thêm schema `semantic-lint-report`, `continuity-report` và `fix-plan` với severity, confidence, evidence và rerun scope.
- [x] Xây semantic linter kiểm tra intent, timing, easing, accessibility, performance và anti-pattern nhưng không tự approve.
- [x] Xây continuity analyzer cho nhiều scene với transition contract, shared context, asset identity và handoff constraints.
- [x] Sinh `fix-plan.json` từ lint/continuity findings, có root cause, affected artifacts, patch scope, rerun scope và verification commands.
- [x] Nối feedback Dev Lab/review vào structured issue register, fix plan và execution handoff.
- [x] Tích hợp P1 reports vào quality gate, report lifecycle, Dev Lab task bundle và CI.
- [x] Tạo eval corpus cho false positive/negative, severity stability, multi-scene drift và selective rerun.
- [x] Cập nhật tài liệu/agent discovery và chạy full validation trước P1 milestone commit.
