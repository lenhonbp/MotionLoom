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

## AI-generated scout pilot ingest

- [x] Xây builder portable tạo receipt, provenance, controls, measured consistency contracts và runtime candidate **chỉ** từ PNG alpha thực.
- [x] Thêm alpha-isolator deterministic cho background edge-connected, có hash report, residual-edge fail-closed và regression coverage.
- [x] Chạy builder trên bốn bytes ImageGen thật; dừng trước `controls.json` vì source RGBA có alpha `255` trên toàn canvas, nên không có candidate hay intake được phát hành.
- [x] Đưa blocker source/repair boundary vào Dev Lab ở `/lab?pilot=scout-alpha`; review staging bị khóa.
- [ ] Cung cấp bốn source PNG có alpha/padding thật hoặc có post-process được visually approved; sau đó chạy build → consistency → Artifact Intake → runtime candidate → Dev Lab review end-to-end.
- [ ] Chủ động tạo lại bốn source scout pixel-art có transparency/padding thật và clean edge; xác minh bytes trước khi đưa vào builder.
- [ ] Chạy ingest hash-bound, frame-geometry consistency và runtime candidate trên source đạt preflight; không bypass bất kỳ validator nào.
- [ ] Render candidate frame sequence, bind evidence vào Dev Lab và mở review-first handoff khi candidate ở trạng thái review_required.
- [ ] Tạo master scout từ nguồn mới có nền charcoal phẳng, không line/shadow/texture; visual-review và alpha-isolate thành RGBA source sạch trước khi sinh pose.
- [ ] Tạo riêng contact-right, passing và contact-left từ master mới; mỗi frame phải qua alpha-isolation report, clean-edge review và geometry measurement.
- [ ] Khi quota tạo ảnh khả dụng, tạo ba pose walk `contact-right`, `passing` và `contact-left` từ master v3 alpha; không dùng idle lặp làm frame action.
- [ ] Chỉ sau khi đủ bốn frame sạch mới tạo bundle Artifact Intake, consistency contract, runtime candidate, render evidence và Dev Lab handoff.
- [ ] Kiểm tra connector hoặc phiên browser Gemini mà người dùng đang dùng; không suy đoán quyền truy cập và không lưu hay yêu cầu lộ credential.
- [ ] Tạo `contact-right`, `passing` và `contact-left` bằng Gemini từ master scout v3; ghi nhận provider/model/task metadata là `ai_generated`.
- [ ] Chạy alpha/padding/contamination preflight từng pose trước khi cho phép Artifact Intake hoặc runtime candidate.
- [ ] Nếu browser Gemini không mở file input tự động, dùng đường Gemini có thể audit với master v3 làm reference; lưu request/output identifiers vào provenance thay vì suy diễn từ preview UI.
- [ ] Tạo ba pose độc lập bằng ChatGPT từ master Scout v3 và giữ lại metadata phiên/tên tệp để ghi provenance `ai_generated` trước khi ingest.
- [ ] Chuẩn hóa ba PNG ChatGPT đã nhận theo thứ tự contact-right, passing, contact-left; kiểm tra loại màu/alpha, padding, contamination và identity drift trước Artifact Intake.
- [ ] Tạo lại ba pose ChatGPT theo corrective prompt: xuất canvas 1920×1920, lock silhouette/scale master v3, không crop, duy trì padding và chỉ thay đổi chi/tư thế walk.
- [ ] Thêm provider contract ChatGPT vào builder/adapter registry để receipt và provenance không thể ghi sai nguồn là `internal-imagegen` khi bytes đến từ ChatGPT.
- [ ] Giữ ba pose ChatGPT v2 ở trạng thái `rejected_pre_ingest`: contact-right thiếu padding cạnh phải/đáy; không pad hoặc resize source để vượt geometry gate.

## Progressive onboarding and internal Dev Lab experience

- [x] Thiết kế quick-start mặc định cho `motionloom setup`/`init`: chỉ tạo project memory, phát hiện framework và hỏi tối đa ba câu cơ bản.
- [x] Bảo đảm các contract/gate sâu không xuất hiện ở luồng cơ bản; chỉ được giải thích/kích hoạt khi người dùng chọn `ingest` hoặc `runtime`.
- [x] Cập nhật `motionloom doctor`, `status`, CLI help và README theo progressive disclosure cho người không rành code.
- [x] Nâng landing/workbench Dev Lab với trạng thái pipeline, quick actions và luồng review-first dễ hiểu khi Agent mở qua browser nội bộ.
- [x] Làm evidence rail trực quan: preview frame, badge trạng thái, hướng dẫn khắc phục inline và không thay thế artifact evidence bằng demo.
- [x] Nâng AI Scout preflight card với master-frame preview, geometry blocker rõ ràng và liên kết corrective prompt.
- [x] Chạy acceptance cho repo và Dev Lab, rồi lưu checkpoint Dev Lab `9ad54c8c`.
- [x] Tạo commit cục bộ cho repo MotionLoom và báo cáo phạm vi trước khi xin duyệt push.
- [x] Push hai commit onboarding đã được duyệt (`7876031`, `9794ce5`) lên `origin/main` và xác minh SHA remote.
- [x] Thiết kế deep link review mang candidate/task/artifact base từ Agent handoff sang Dev Lab mà không tin URL chưa được validate.
- [x] Triển khai parser, validation và fallback UI cho review URL để Dev Lab tự mở đúng candidate thật khi evidence hợp lệ.
- [x] Kiểm thử deep link với candidate hợp lệ, thiếu, foreign hoặc malformed; lưu checkpoint Dev Lab sau khi xác minh.
- [x] Chạy AI Scout preflight với ba pose hiện có; builder chặn contact-right ở 44px padding cạnh phải nên trạng thái vẫn `partial`, không ingest/candidate/runtime/Dev Lab review.
- [x] Tạo commit cục bộ cho review deep link và báo cáo phạm vi trước khi xin duyệt push.
- [x] Push hai commit deep-link đã được duyệt (`9b09fa8`, `d24f0ac`) lên `origin/main` và xác minh SHA remote `d24f0acb6a05a79962befb967995fae93ce0da16`.
- [ ] Tạo hoặc tiếp nhận ba pose Scout `contact-right`, `passing`, `contact-left` độc lập ở PNG RGBA 1920×1920 theo master v3; ghi provider/task provenance trung thực.
- [x] Stage ba PNG ChatGPT user-upload nguyên gốc cùng SHA-256 và provenance `chatgpt-user-import` trước khi chạy bất kỳ validator hoặc builder nào.
- [x] Bổ sung regression để `build-ai-pilot` phát hành `partial-handoff.json` hash-bound khi reject ở frame đầu tiên, không chỉ trả traceback.
- [x] Chạy preflight có evidence cho canvas, alpha, contamination và padding trên cả ba pose. Kết quả reject hash-bound: canvas 1254×1254, padding phải/đáy thấp hơn 63px; không resize/pad để bypass.
- [x] Ignore `/.motionloom/incoming/` và `/.motionloom/runs/` để ba bytes user-upload cùng copies validation cục bộ không thể bị commit hoặc đóng gói npm nhầm.
- [x] Tạo commit cục bộ cho partial handoff fail-closed, regression và bảo vệ user-upload bytes; báo cáo trước khi xin duyệt push.
- [ ] Khi cả bốn frame pass, chạy build-ai-pilot → Artifact Intake → consistency → runtime candidate → runtime render → review handoff Dev Lab; nếu bất kỳ gate fail, kết thúc `partial`.
- [x] Cung cấp prompt ChatGPT copy-paste, yêu cầu upload master v3, tạo ba pose độc lập và trả lại PNG gốc cùng metadata phiên để provenance `ai_generated` được ghi trung thực.
- [x] Push ba commit hardening đã được duyệt (`ad3bbb8`, `6620dde`, `a154d91`) lên `origin/main` và xác minh SHA remote `a154d9177ac1fc5276e2538b0ca72484bbf08ed9`.
- [x] Soạn handoff Codex dùng master v3, contract canvas/padding/footline, pose definitions và provenance `ai_generated`; yêu cầu trả ba PNG gốc độc lập, không post-process để bypass.
- [x] Stage receipt Codex `exec-6c962cac-7e7f-491b-b0a8-e7c4ee7d2412` cùng SHA-256, source mode và blocker geometry/background vào partial handoff mà không ingest bytes.
- [x] Cập nhật handoff Codex với capability preflight: dừng ngay nếu tool chỉ trả 1254×1254, RGB hoặc checkerboard rasterized; không cần tạo các pose còn lại.
- [x] Chạy regression evidence và tạo commit cục bộ `17dc3f4` cho tài liệu/partial handoff Codex bị reject; không push nếu chưa có duyệt riêng.
- [x] Push hai commit Codex đã được duyệt (`17dc3f4`, `fbd4aa1`) lên `origin/main`; SHA remote `fbd4aa1afa413b849d7ef9030aa2be4681f608c5`, chỉ gồm handoff Codex và ledger, không có user-upload hoặc partial evidence cục bộ.

## Runtime-first end-to-end pilot

- [ ] Rà soát fixture GSAP/Framer Motion hiện có và chọn một source code-authored tối thiểu, có provenance/replay metadata rõ ràng.
- [ ] Tạo task bundle runtime-first với scene, source binding, runtime adapter evidence và candidate identity-bound; không dùng AI Scout source bị reject.
- [ ] Render candidate qua runtime thật, ghi snapshots/quality/execution evidence và tạo review URL Dev Lab.
- [ ] Mở candidate runtime-first trong Dev Lab, kiểm tra review-first và giữ `production_approved=false` cho đến human review.
- [ ] Chạy acceptance, lưu checkpoint Dev Lab, tạo commit cục bộ và báo cáo trước khi xin duyệt push.

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

## Project Memory and cross-platform execution

- [x] Thiết kế và thêm `project-memory.schema.json` với version, project identity, motion principles, asset/runtime policy, decisions, rejected patterns, remediation summary và freshness/invalidation fields.
- [x] Xây CLI `memory init`, `memory inspect`, `memory refresh`, `memory validate`, `memory record-decision` và `memory record-outcome` với path handling không phụ thuộc Bash/cwd.
- [x] Tích hợp Project Memory vào project context, graph, provenance, continuity, fix-plan và next-agent handoff; chặn dùng memory stale hoặc cross-project memory.
- [x] Thêm memory recovery test sau context compaction/phiên mới và test quyết định cũ, rejected approach, asset policy, runtime policy được khôi phục đúng.
- [x] Chuẩn hóa npm CLI wrapper cho Ubuntu, macOS và Windows; dùng Node `spawn`/`spawnSync` cross-platform, Python executable discovery và không phụ thuộc `bash`, `sed`, `grep` hoặc `/tmp` cố định.
- [x] Thêm CI matrix Ubuntu/macOS/Windows với Python/Node versions được hỗ trợ, path separator, Unicode path, spaces trong path, symlink/junction và missing dependency cases.
- [x] Cập nhật SKILL.md, Agent Card, README, references và release notes để mô tả lifecycle Project Memory, giới hạn persistence và cách Codex load/recover memory.
- [x] Chạy full acceptance, deep-stress memory recovery, cross-platform contract tests; tạo commit và chỉ push sau explicit confirmation.

> Acceptance note: relocation với Git remote, Unicode path và path có khoảng trắng pass; `project.root_path` được rebind khi `memory recover`, còn các chỉnh sửa nội dung trực tiếp vẫn bị integrity guard chặn.

## Public repository professionalism upgrade

- [x] Nâng README thành landing page của repo với positioning, badges, quick start, architecture, lifecycle, trust boundary, examples và links tài liệu.
- [x] Thêm bộ tài liệu cộng đồng chuẩn: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `ROADMAP.md` và `LICENSE` references.
- [x] Thêm GitHub issue/PR templates, CODEOWNERS và workflow hygiene để repo dễ đóng góp và review.
- [x] Cập nhật package metadata, npm/GitHub links, version badges và release navigation nhất quán với MotionLoom 2.1.0.
- [x] Chạy skill validation, docs link/structure checks, full regression, package dry-run và kiểm tra working tree trước commit.

> Public repository acceptance: docs audit pass, Skill Doctor pass with 0 warnings, regression/intelligence/runtime checks pass, and npm dry-run produced `motionloom@2.1.0` with 132 files.

## GitHub Actions CI/CD automation

- [x] Tách workflow CI đa nền tảng, docs/metadata, security hygiene, package verification và release workflow có trigger rõ ràng.
- [x] Giới hạn permissions theo job, tránh secret exposure trên fork và giữ release/npm publish sau environment approval.
- [x] Bổ sung cache/dependency setup, artifact upload, concurrency và path filters để CI nhanh nhưng có kiểm chứng.
- [x] Kiểm tra YAML/schema/workflow semantics, chạy local acceptance tương ứng và cập nhật README/CONTRIBUTING/release docs.
- [ ] Tạo commit local; chỉ push sau explicit user confirmation.

> CI/CD acceptance: docs/workflow audit, Skill Doctor, Project Memory contract, full regression, runtime adapters, browser-review snapshot harness, npm dry-run and diff hygiene pass. The release workflow remains manual-only and environment-protected.

## Independent audit follow-up

- [x] Đối chiếu trạng thái CI hiện tại trên GitHub với audit đính kèm, đặc biệt quality/devlab workflows và check runs.
- [x] Kiểm tra claim về runtime fixture, cross-platform matrix, analyzer scalability, documentation authority và release traceability.
- [x] Xác định P0 stabilization items trước khi thêm subsystem mới.
- [x] Thiết kế real-project corpus và paired product study để đo product-value evidence.

## Audit implementation roadmap

- [x] Sửa duplicate workflow name và xác nhận Quality workflow tạo jobs, chạy matrix thành công trên main.
- [x] Làm Dev Lab snapshot observable: health check, page/console error capture, diagnostic artifact và fixture identity không phụ thuộc candidate production expiry.
- [x] Thêm authority/status documentation, phân biệt normative, historical và external-project evidence; cập nhật runtime verification levels.
- [x] Bổ sung bounded scanner cho analyzer với ignore rules, file/byte/time budgets và `scan_truncated` signal.
- [x] Tạo labeled external-project corpus manifest và paired evaluation harness; không seed review/testimonial claims.
- [x] Thêm release verifier cho version–changelog–release-note chain và chạy full acceptance trước checkpoint; tag/GitHub Release/npm publish thật vẫn cần manual approved release.
- [ ] Tạo commit local; chỉ push sau explicit user confirmation.

## README and public-claims audit

- [x] Đối chiếu README trên GitHub với local HEAD, package metadata, npm CLI, workflows, schemas và current status.
- [x] Kiểm tra toàn bộ internal/external links, command snippets, version badges, workflow names, runtime capability claims và release instructions.
- [x] Sửa README cùng tài liệu liên quan khi phát hiện documentation drift hoặc claim vượt evidence.
- [x] Chạy docs audit, release verifier, Skill Doctor, regression và package dry-run sau chỉnh sửa.
- [ ] Tạo commit local; chỉ push sau explicit user confirmation.

## Release synchronization 2.1.0

- [x] Xác minh `origin/main`, package version, changelog, release note và npm registry.
- [x] Chạy release verifier và kiểm tra tarball `motionloom@2.1.0`.
- [x] Tạo tag và GitHub Release 2.1.0 nếu mọi metadata khớp; release đang ở trạng thái draft cho tới khi npm 2.1.0 được publish.
- [ ] Hướng dẫn publish npm 2.1.0 từ workstation của user; không giả định sandbox có npm credentials.

## Related repository research
- [x] Thu thập dữ liệu hiện tại từ các repo animation/runtime nổi tiếng và các repo Agent/skill có liên quan.
- [x] Đọc README, architecture, governance, license và release posture của corpus đại diện.
- [x] So sánh với MotionLoom theo capability, maturity, evidence, ecosystem fit và developer experience.
- [x] Đề xuất roadmap học hỏi có thứ tự ưu tiên, không đồng nhất số sao với chất lượng sản phẩm.

## Approved roadmap implementation: Agent interoperability, visual truth and remediation learning
- [x] Khóa baseline local/remote, đọc contract hiện tại và xác định file/schema cần mở rộng; không thay đổi release version nếu chưa có release plan.
- [x] Thêm canonical Agent discovery surfaces cho `.agents/skills`, `.claude` và `.codex`, cùng một nguồn instruction chuẩn và guard chống drift.
- [x] Thêm installation/discovery contract cho npm, GitHub checkout và local source; ghi nhận source, version và capability compatibility.
- [x] Bổ sung consumer examples/fixtures cho Lottie, GSAP, Framer Motion, Rive, body rig và continuity multi-scene.
- [x] Bổ sung installation matrix và portability tests cho Ubuntu, macOS, Windows; lưu diagnostics/artifacts khi failure.
- [x] Thiết kế và triển khai Visual Truth Contract với asset/frame hash, runtime provenance, perceptual metrics và region-level explanation.
- [x] Nối Visual Truth Contract vào candidate manifest, Dev Lab evidence rail và review-first quality gate; không tự cấp approval.
- [x] Thiết kế và triển khai benchmark history append-only với aggregate metrics, outlier detection và run provenance.
- [x] Triển khai Remediation Learning cho correction count, first-pass acceptance, issue class và selective rerun scope.
- [x] Cập nhật SKILL.md, Agent Card, README, schemas, references, CHANGELOG/ROADMAP và report contracts theo progressive disclosure.
- [x] Chạy skill validation, docs/workflow audit, full regression, runtime/browser smoke, package dry-run và cross-platform-compatible checks.
- [x] Kiểm tra GitHub Actions mainline mới nhất; tạo commit local và chỉ push/merge/open PR sau explicit user confirmation là bước handoff còn lại.

## CI replay remediation after d148f21
- [x] Phân tích đầy đủ 11 replay mismatches trên GitHub Quality run và xác định artifact nào bị stale.
- [x] Tái tạo replay bundle cùng các provenance-bound artifacts bằng pipeline canonical, không nới lỏng verifier hoặc quality gate.
- [x] Bổ sung regression để thay đổi artifact/manifest/runtime evidence phải buộc replay rebuild trước khi Quality pass.
- [x] Chạy full local validation, kiểm tra diff hygiene và tạo commit fix local.
- [ ] Chỉ push commit fix sau explicit user confirmation; theo dõi lại Quality, Documentation/Package và Security trên commit fix.

## Approved release candidate 2.2.0
- [x] Khóa scope release gồm Agent interoperability, consumer fixtures, Visual Truth, Remediation Learning và CI replay remediation.
- [x] Kiểm kê và đồng bộ version 2.2.0 trong package metadata, Agent Card, SKILL contract, schemas và release metadata.
- [x] Cập nhật CHANGELOG, release note và ROADMAP; giữ ranh giới rõ giữa Unreleased/release candidate và bản đã publish.
- [x] Chạy release verifier, full regression, docs/Skill validation, runtime/quality checks và npm tarball audit.
- [x] Tạo commit `61edd2c` và local tag `v2.2.0-rc.1`; kiểm tra review boundary và working tree sạch.
- [x] Push/tag remote sau explicit user confirmation; publish npm sau confirmation release/publish riêng.

## Approved official publication: 2.2.0

- [x] Kiểm tra tag `v2.2.0-rc.1`, commit, ba CI workflow và registry trước publication.
- [x] Tạo GitHub Release chính thức `v2.2.0` với release note đã kiểm chứng.
- [x] Publish `motionloom@2.2.0` lên npm với dist-tag `latest`.
- [x] Xác minh GitHub Release, npm metadata, tarball contents và release traceability end-to-end.

## Approved Agent-created Asset Provenance Contract
- [x] Audit production-hero preflight gate và khóa các authority/origin/readiness states mới.
- [x] Thêm schema provenance đa tầng cho `ai_generated`, `ai_assisted`, `ai_assisted_human_reviewed`, `artist_authored` và `unknown`.
- [x] Tách `runtime_ready`, `review_required`, `production_eligible` và `production_approved`; không để Agent tự cấp approval.
- [x] Nối `ai_generated_pilot` vào hero preflight để cho phép runtime ingest/test nhưng fail-closed ở production gate.
- [x] Bổ sung generator/model/task/source/license/SHA-256/derivation-chain và human-review metadata.
- [x] Thêm fixture AI-generated pilot, report contract và regression chống self-asserted artist authority.
- [x] Cập nhật SKILL.md, Agent Card, README, schema references và docs về AI-first human-governed asset workflow.
- [x] Chạy full validation; commit local và chỉ push sau explicit user confirmation.

## Approved installation UX simplification
- [x] Audit toàn bộ install guide, npm scripts, CLI help và Agent integration để xác định điểm gây khó tiếp cận.
- [x] Thiết kế safe defaults cho one-command install, project detection, dry-run và local-only behavior.
- [x] Triển khai lệnh setup/init cross-platform để cài MotionLoom vào dự án thật mà không cần người dùng tự sao chép nhiều file.
- [x] Thêm doctor/repair/status output thân thiện, giải thích lỗi bằng ngôn ngữ dễ hiểu và không tự mở PR/push.
- [x] Cập nhật README, installation guide, Agent integration và regression cho luồng cài đặt rút gọn.
- [x] Chạy full validation; commit local và chỉ push sau explicit user confirmation.

## Approved release 2.3.0: one-command onboarding
- [x] Khóa release scope gồm setup/status/repair, Agent discovery recipe, docs và cross-platform regression.
- [x] Cập nhật package version, changelog, release note và các metadata liên quan lên `2.3.0`.
- [x] Chạy release verifier, full regression, docs/Skill validation và npm tarball audit.
- [x] Push commit onboarding `6568b2d` cùng release commit lên `origin/main` sau xác nhận của user.
- [x] Tạo tag và GitHub Release `v2.3.0` với release note đã kiểm chứng.
- [x] Publish `motionloom@2.3.0` lên npm và xác minh dist-tag, tarball contents và traceability. Workstation initially hit invalid auth (`E401`/masked `E404`), then succeeded after re-login as `lenhonbp` without `--provenance`.

## Release 2.3.0 npm E404 follow-up
- [x] Xác minh npm identity, registry và package ownership bằng các lệnh read-only trên workstation.
- [x] Phân biệt lỗi authentication, publish permission, package ownership và registry configuration; không đổi package name hoặc version khi chưa có bằng chứng.
- [x] Cập nhật publication troubleshooting và release checklist với hướng xử lý E404/E401 đã xác minh.
- [x] Hướng dẫn user sửa quyền npm trên workstation nếu cần; không lấy hoặc yêu cầu npm token trong chat.
- [x] Xác minh `motionloom@2.3.0`, `latest`, tarball URL/hash và traceability sau publish thành công.

## Proposed AI asset consistency and layered-map pipeline
- [x] Audit các contract hiện tại cho asset identity, frame/atlas, runtime evidence, collision/socket và map/background layers.
- [x] Thiết kế asset identity manifest cho character/style/camera/pivot/scale/palette/lighting và derivation chain qua nhiều frame.
- [x] Thiết kế frame geometry contract với canvas, trim, transparent padding, pivot, bbox, safe rect, bleed và frame-to-frame invariants.
- [x] Triển khai analyzer đo alpha bounds, phát hiện frame overlap/contamination, crop lệch, scale drift, pivot drift và atlas UV sai.
- [x] Triển khai layered-map schema/validator cho z-order, parallax, anchor, tileability, seam/overlap, occlusion và camera-safe bounds.
- [x] Thêm fixture nhiều frame hành động và map nhiều lớp; nối CLI, quality gate, report và regression evidence.
- [x] Cập nhật SKILL.md, Agent Card, README, references và docs về AI-generated asset consistency.
- [x] Chạy full validation và chuẩn bị commit local; push vẫn chờ explicit user confirmation.

## Research AI animation and asset tools
- [x] Xác định nhóm công cụ cần khảo sát: AI pixel/game asset, image-to-video, text-to-video, 2D rig/character, motion capture/body animation và runtime/vector animation.
- [x] Thu thập nguồn chính thức cho PixelLab AI và các công cụ đại diện; ghi lại chức năng, input/output, export, consistency controls, API/automation và giới hạn license/provenance.
- [x] Phân tích pipeline tạo animation/asset của từng công cụ theo các lớp: concept, reference, generation, temporal consistency, rig/action, export, runtime preview và human review.
- [x] Đối chiếu bài học với MotionLoom contracts: project memory, identity, action-set, frame geometry, atlas, layered map, provenance, runtime evidence và Dev Lab.
- [x] Xác định khoảng trống, rủi ro và đề xuất roadmap có acceptance criteria; không biến khả năng marketing hoặc heuristic thành production approval.
- [x] Viết báo cáo nghiên cứu có trích dẫn nguồn chính thức và lưu URL/evidence để có thể audit lại trong `docs/research/ai-animation-tools-2026-{notes,report}.md`.

## Phase A — Provider-neutral artifact intake and internal-skill adapters
- [x] Rà soát skill/công cụ nội bộ miễn phí của Agent có thể tạo hoặc biến đổi asset, bắt đầu với ImageGen; ghi rõ capability, artifact output và giới hạn provenance.
- [x] Thiết kế `generation-receipt`, `control-track` và `export-manifest` schemas để bind provider/source controls với output hashes mà không lưu secrets hoặc tạo approval.
- [x] Thiết kế registry adapter provider-neutral, với adapter `local-fixture` static-validated và adapter `internal-imagegen` scaffold; không gọi provider API hoặc yêu cầu credential trong core path.
- [x] Triển khai validator/CLI fail-closed cho receipt, control track, export manifest và adapter registry; định nghĩa trạng thái evidence, `scaffold`, `blocked` theo evidence.
- [x] Tạo fixtures/regression bao phủ hash tampering, missing controls/output, unknown adapter, self-asserted approval và ImageGen-style receipt metadata.
- [x] Nối optional artifact intake evidence vào quality gate/report mà không làm scene cũ fail và không thay user review/production approval.
- [x] Cập nhật SKILL.md, Agent Card, README, references, docs/research và npm whitelist; chạy full validation, commit local và chỉ push sau explicit user confirmation.

## Post-Artifact Intake hardening phases
- [x] Xây cầu nối từ control track/export manifest sang asset identity, action-set, frame geometry, atlas và layered-map evidence; chỉ tạo runtime candidate khi tất cả ref/hash tương thích.
- [x] Thiết kế và triển khai rig compatibility contract cho runtime adapters, sockets/events/action coverage và export-to-runtime compatibility; không giả lập rig production khi không có source hợp lệ.
- [x] Nối artifact intake và runtime/rig evidence vào Dev Lab handoff để user thấy adapter status, controls, hashes, kiểm tra pass/block và lý do review-required trước confirm.
- [x] Chạy regression mở rộng cho toàn bộ contracts, CLI cross-platform smoke, quality/report/Dev Lab integration, package tarball và CI workflows.
- [x] Audit toàn repo về schema drift, unsafe paths, hash/evidence binding, approval bypass, docs/version drift, CLI/package surface, dependency và workflow mistakes; chủ động sửa lỗi an toàn được xác nhận bằng evidence. `pnpm audit --prod` báo 0 advisory; `npm audit` không áp dụng vì repo chỉ có `pnpm-lock.yaml`.
- [x] Thực hiện full validation sau mỗi đợt sửa, lưu audit report và commit local cuối; không push, open PR hoặc publish nếu không có xác nhận riêng.

## Runtime adapter and AI pilot review follow-up
- [x] Push commit `0a69192` đã được user duyệt lên `origin/main`; xác nhận remote SHA `0a691923a149084a000635b644b702f54d58d4c7`.
- [x] Chọn adapter Rive dựa trên support/runtime contract hiện có; thêm package gate chỉ nhận `.riv` thật kèm metadata, provenance, adapter evidence và runtime proof, không tạo placeholder production package.
- [ ] Tạo AI-generated pilot bằng capability nội bộ, lưu generation receipt, output hash, source/reference/control metadata và provenance `ai_generated`; không tự gán `artist_authored`, `production_eligible` hoặc `production_approved`.
- [ ] Ingest pilot qua Artifact Intake, asset consistency, runtime candidate và rig compatibility; render runtime evidence và bind Dev Lab handoff trước human review.
- [ ] Chạy validation, lưu commit local cho adapter/pilot artifacts (nếu có thay đổi), công bố pass/block/review-required và không mở PR khi chưa có user review.
