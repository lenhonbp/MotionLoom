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

## P1 extension: multi-scene continuity and perceptual benchmark

- [x] Tạo task fixture nhiều scene với shared context, asset identity, transition contract và một case drift có chủ đích.
- [x] Thêm continuity assertions cho asset reuse, timing handoff, context hash và selective rerun ở cấp scene.
- [x] Bổ sung semantic lint rules đo frame budget, duration/easing risk, reduced-motion impact và runtime cost.
- [x] Bổ sung perceptual proxy lint với evidence rõ ràng; không gọi proxy score là human visual approval.
- [x] Xây benchmark runner có case manifest, expected severity, confidence band, false-positive/negative và report version.
- [x] Tích hợp fixture/benchmark vào regression, eval, strict quality gate, report contract và CI.
- [x] Chạy full acceptance, cập nhật tài liệu/release note và tạo commit release local trước khi push.
- [x] Xác nhận remote target, branch và commit SHA lần cuối trước thao tác push GitHub.

## Merge completion: fix/browser-review-smoke

- [x] Kiểm tra branch feature không có thay đổi chưa commit và không xung đột với `origin/main`.
- [x] Mở Pull Request từ `fix/browser-review-smoke` vào `main` với mô tả đầy đủ và acceptance evidence.
- [x] Chờ GitHub Actions/checks chạy và xử lý mọi blocker trước merge.
- [x] Merge Pull Request vào `main` theo chính sách review/CI của repository.
- [x] Xác minh `origin/main`, PR merge SHA, branch state và các artifact chính sau merge.

## Roadmap hardening execution

- [x] Tạo deep-audit report cho browser-review lifecycle, Dev Lab candidate binding, CLI/path safety, provenance/replay và quality-gate bypass.
- [x] Bổ sung regression/adversarial tests cho candidate identity, approval replay/expiry, malformed input, path traversal, stale evidence và framework mismatch.
- [x] Hardening các đường bypass có bằng chứng từ audit, ưu tiên các lỗi có thể biến heuristic hoặc artifact giả thành approval.
- [x] Cập nhật SKILL.md, Agent Card, README và release note với audit findings, trust boundaries và remediation status.
- [x] Chạy clean-checkout/CI/full acceptance, commit milestone roadmap và cập nhật trạng thái checklist sau khi xác minh.

## Roadmap phase: evidence interoperability and runtime observability

- [x] Chốt threat model và ranh giới tin cậy cho runtime frame telemetry và external verifier.
- [x] Thiết kế schema/versioned contract cho telemetry, verifier result và identity binding.
- [x] Triển khai telemetry capture/validate và verifier CLI với stable exit codes, root/path guards và không tự cấp approval.
- [x] Bổ sung adversarial eval, regression, quality gate và CI coverage cho telemetry/verifier tamper, replay, cross-task và stale evidence.
- [x] Cập nhật Dev Lab handoff, Agent Card, SKILL.md, roadmap, audit report và release metadata.
- [x] Chạy full acceptance, commit milestone, push sau explicit confirmation và xác minh CI trên main.

## Roadmap phase: production-grade trust, visual quality and benchmark history

- [x] Kiểm kê roadmap, baseline hiện tại và threat model tổng thể cho các phase còn mở.
- [x] Thiết kế schema/versioned contract cho signed attestation, trust anchor, key rotation và revocation.
- [x] Triển khai attestation builder với canonical payload, domain separation và không tự cấp approval.
- [x] Triển khai key policy, rotation/revocation checks và fixture cho expired/revoked/unknown signer.
- [x] Xây external verifier độc lập khỏi repository runtime, có stable exit codes và fail-closed semantics.
- [ ] Thiết kế visual-comparison contract theo asset/frame hash, perceptual metrics và dataset fixture có nhãn nguồn gốc rõ ràng.
- [ ] Bổ sung benchmark history schema, append-only run records, aggregate metrics và outlier detection.
- [ ] Tích hợp attestation, visual comparison và benchmark history vào Dev Lab theo review-first flow.
- [x] Bổ sung adversarial eval, regression, quality gate và CI cho attestation tamper, replay, signer revocation, binding mismatch và approval invariant.
- [x] Cập nhật SKILL.md, Agent Card, README, Intelligence reference, roadmap, audit report, release note và handoff contracts cho attestation.
- [ ] Thiết kế visual-comparison contract theo asset/frame hash, perceptual metrics và dataset fixture có nhãn nguồn gốc rõ ràng.
- [ ] Bổ sung benchmark history schema, append-only run records, aggregate metrics và outlier detection.
- [ ] Tích hợp visual comparison và benchmark history vào Dev Lab theo review-first flow.
- [ ] Chạy full acceptance, tạo checkpoint/commit, push sau explicit confirmation và xác minh CI trên main.

## npm package release via user workstation

- [x] Chuyển package từ private repo metadata sang public npm package `motionloom@2.0.0`.
- [x] Thêm `bin/motionloom.mjs`, explicit `files`, npm metadata, MIT license và install instructions.
- [x] Thêm prepack cleanup để loại Python bytecode/local runtime state khỏi tarball.
- [x] Chạy `npm publish --dry-run --access public`; tarball sạch, 260.3 kB, 111 files.
- [x] Commit và push npm packaging changes lên `origin/main` sau explicit confirmation.
- [x] Đăng nhập npm từ máy người dùng và chạy `npm publish --access public`.
- [x] Xác minh `npm view motionloom@2.0.0` và cài thử CLI từ registry.

## Deep stress/evaluation audit

- [x] Thiết kế ma trận 5.000+ vòng cho context binding, provenance, Motion IR, semantic lint, replay, continuity, telemetry, attestation, quality gate và handoff.
- [x] Xây deterministic stress harness với fault injection, metamorphic variants và per-case result ledger.
- [x] Chạy tối thiểu 5.000 vòng, ghi latency/error/false-positive/false-negative và phân loại theo contract.
- [x] Đo tỷ lệ chặn stale/cross-task/tampered evidence và tỷ lệ giữ nguyên `approval=false`.
- [x] Đo baseline khả năng bảo toàn fix-plan/handoff binding và xác định chưa có historical rerender-reduction metric.
- [x] Phân tích failure cluster, race/flake, resource leak, non-determinism và blind spots chưa được test; harden semantic/continuity schema gap.
- [x] Chạy full regression sau hardening, cập nhật audit report và đề xuất roadmap giảm vòng chỉnh sửa animation sai.
- [ ] Thêm visual-comparison contract có fixture/frame provenance và pixel/perceptual diff.
- [ ] Thêm multi-project/browser/device corpus và remediation ledger để đo first-pass acceptance, correction count và rerender avoidance.
