# Chiến lược khác biệt hóa Animation Skill Kit

**Trạng thái:** Đề xuất sau research và audit repo v1.1.0  
**Mục tiêu:** Biến repo từ một animation skill có helper scripts thành một **project-aware animation production system** có thể phối hợp an toàn với nhiều Agent và chứng minh được chất lượng đầu ra.

## 1. Kết luận điều hành

> **Không nên cạnh tranh bằng số lượng prompt, preset hoặc framework. Nên cạnh tranh bằng khả năng biến yêu cầu animation thành một artifact có ngữ cảnh, có provenance, có runtime evidence, có review state và có thể bàn giao cho Agent/PR khác mà không mất thông tin.**

Các kho skill phổ biến hiện nay thường rơi vào một trong bốn nhóm. Nhóm thứ nhất là prompt cookbook: dễ cài, dễ đọc nhưng thiếu thực thi và bằng chứng. Nhóm thứ hai là skill chuyên biệt, chẳng hạn logo-to-Lottie, đã có helper scripts, preview và validation nhưng thường gắn với một format hoặc một loại asset. Nhóm thứ ba là marketplace/awesome list, có độ phủ lớn nhưng bản thân việc được liệt kê không chứng minh an toàn hay production readiness. Nhóm thứ tư là tool/MCP wrapper: gọi được công cụ nhưng không tự cung cấp domain judgment, project binding hoặc review gate. Các skill chính thức và tài liệu Agent Skills hiện nhấn mạnh packaging, discovery, composition và progressive disclosure; đó là nền tảng cần tuân thủ, không phải lợi thế cạnh tranh cuối cùng [1] [2] [3].

Animation Skill Kit đã có phần lõi khác biệt đáng giá: analyzer ghi context vào project đích, motion spec có context hash, Lottie runtime evidence, SVG cutout rig, Dev Lab, quality gate và confirm-to-PR. Tuy nhiên, để trở thành một skill “thông minh hơn” theo nghĩa có thể đồng bộ cùng nhiều Agent, repo cần nâng cấp từ **CLI pipeline có tài liệu** thành **interoperability contract có schema và task/artifact lifecycle**.

## 2. Đối chiếu công bằng với các pattern hiện có

| Pattern trên thị trường | Điểm làm tốt | Điểm thường thiếu | Cơ hội riêng của Animation Skill Kit |
|---|---|---|---|
| Prompt-only skill | Discovery đơn giản, tải nhanh, dễ fork | Không có runtime, không có test, không có provenance | Giữ `SKILL.md` ngắn nhưng đẩy quyết định vào executable contract và evidence |
| Skill Lottie/logo chuyên biệt | Có preset, asset validation, preview frame, loop test và export helper | Ít hiểu host project, thường chỉ hỗ trợ logo/Lottie, chưa có handoff | Bọc helper bằng context binding, framework adapter, Dev Lab và PR artifact |
| Awesome/marketplace repo | Có nhiều Agent, skill, hook, workflow, plugin | Chất lượng không đồng đều; người dùng phải tự kiểm tra trust | Công bố capability level, dependency/permission inventory và benchmark thật |
| MCP tool server | Tool/resource/prompt có thể discover và gọi chuẩn | MCP không tự quyết định animation đúng hay sai | Tách resources, prompts, tools theo MCP semantics và thêm domain quality gate |
| A2A-style remote Agent | Có capability discovery, task lifecycle, artifact và message handoff | Không có semantic model cho motion/body/asset | Xuất Agent Card, task state và artifact bundle chuyên cho animation |
| Template framework | Bắt đầu nhanh, code quen thuộc | Dễ bị copy mà không khớp runtime, design system hoặc accessibility | Dùng template chỉ sau framework selection và context validation |

Một skill logo animation cộng đồng cho thấy mức tốt của pattern chuyên biệt: nó có workflow motion philosophy → asset preparation → Lottie → preview → render, cùng các script validate asset, test render và loop [4]. Vì vậy, lợi thế của repo này không thể chỉ là “có script render”. Lợi thế phải nằm ở **tính liên tục của ngữ cảnh và bằng chứng từ project đến PR**.

## 3. Sáu năng lực nên trở thành dấu ấn riêng

### 3.1. Project-aware Motion Compiler

Hãy định vị Skill như một compiler có pipeline nhiều tầng, không phải một chatbot sinh JSON. Input là yêu cầu người dùng, host project, asset và policy. Intermediate representation là motion spec chuẩn hóa. Output là runtime artifact theo adapter Lottie, Rive, GSAP, Framer Motion, Spine hoặc Three.js.

Compiler phải thực hiện các bước sau:

| Tầng | Quyết định bắt buộc |
|---|---|
| Intent | Animation phục vụ UX, branding, storytelling, character hay data-viz nào |
| Context | Framework, package, brand token, motion language, target device và existing component |
| Semantics | Layer, bone, constraint, trigger, state, loop, reduced-motion fallback |
| Adapter | Chọn runtime có khả năng biểu đạt semantics đó |
| Evidence | Render bằng runtime thật, đo budget và lưu artifact có hash |

Điểm khác biệt là Agent không thể bỏ qua host project để lấy một preset có sẵn. Nếu không tìm thấy context đủ tin cậy, task phải ở trạng thái `needs_context`, không được tự động tạo output production.

### 3.2. Canonical Motion IR cho motion, body và asset

Hiện repo có motion spec nhưng chưa có một intermediate representation đủ sâu để cùng một ý tưởng chuyển động có thể target nhiều runtime. Nên bổ sung `schemas/motion-ir.schema.json`, trong đó mô tả:

- `nodes`: layer, shape, image, text, bone;
- `hierarchy`: parent, pivot, transform space;
- `tracks`: keyframes, interpolation, easing, spring hoặc constraint;
- `states`: idle, enter, active, exit, error và reduced-motion;
- `events`: click, hover, scroll, load, state-machine input;
- `constraints`: brand color, file size, FPS, duration, accessibility và device budget;
- `adapters`: khả năng biểu diễn và giới hạn của từng runtime.

Nhờ đó, Agent thiết kế chuyển động một lần ở tầng semantics rồi adapter mới biên dịch xuống Lottie JSON, Rive state machine, GSAP timeline hoặc Framer Motion variant. Đây là lợi thế bền vững hơn việc thêm nhiều template rời rạc.

### 3.3. Artifact-first và Agent handoff

Theo pattern A2A, Agent nên discovery capability bằng Agent Card, chạy task có lifecycle và nhận artifact có loại dữ liệu rõ ràng [5]. Theo MCP, resources, prompts và tools cũng nên tách biệt; thao tác tool có side effect phải nằm sau consent boundary [6].

Đề xuất artifact bundle:

```text
artifacts/<task-id>/
├── task.json
├── project-context.json
├── motion-spec.json
├── motion-ir.json
├── source/
├── runtime/
│   ├── animation.json|scene.riv|module.ts
│   └── render-meta.json
├── snapshots/
│   ├── frame-000.png
│   ├── frame-050.png
│   └── frame-100.png
├── review.json
├── quality-report.json
└── provenance.json
```

`task.json` nên có các state tối thiểu: `needs_context`, `planning`, `generating`, `rendering`, `review_required`, `blocked`, `validated`, `ready_for_pr`, `confirmed` và `failed`. Agent khác chỉ cần đọc `task.json` và `quality-report.json` là biết có thể tiếp tục, cần hỏi người dùng hay phải sửa.

### 3.4. Runtime Truth Boundary

Skill phải phân biệt ba cấp độ và hiển thị thẳng cho Agent lẫn người dùng:

| Capability level | Ý nghĩa | Có cho PR production không? |
|---|---|---|
| `scaffold` | Template hoặc code compile được | Không đủ |
| `static-validated` | JSON/XML/schema hợp lệ | Không đủ |
| `runtime-verified` | Runtime thật render được frame và metadata | Có, nếu các gate khác pass |
| `project-integrated` | Chạy trong host project thật, đúng route/component/device policy | Mức khuyến nghị |

Mỗi adapter phải công bố test matrix: browser/runtime version, frame range, render mode, reduced-motion behavior, performance budget và known limitations. Đây là nơi nhiều repo “ăn xổi” dễ phóng đại năng lực: một file JSON hợp lệ không đồng nghĩa với animation đã chạy đúng trong ứng dụng thật.

### 3.5. Asset provenance và license intelligence

Asset cần có `asset-manifest.json` với source URL, creator, license, retrieval date, checksum, modification history và allowed use. Agent phải biết asset nào được phép chỉnh sửa, asset nào chỉ được dùng demo, và asset nào không đủ provenance để đưa vào PR.

Điểm này vừa khác biệt vừa thiết thực cho production: animation không chỉ là chuyển động đúng, mà còn phải ship được về mặt pháp lý, reproducibility và bảo trì. Các repo marketplace hiện cũng nhấn mạnh người dùng phải kiểm tra third-party agent/documentation trước khi cài; với asset animation, trust boundary cần áp dụng tương tự [2] [3].

### 3.6. Review loop có bộ nhớ nhưng không tự học mù

Dev Lab nên lưu `review.json`, không chỉ cho nút Confirm. Mỗi feedback cần phân loại là `timing`, `easing`, `pose`, `composition`, `brand`, `accessibility`, `performance` hoặc `asset`. Agent lần sau có thể dùng review history để đề xuất tốt hơn, nhưng chỉ được đưa thành rule mới sau khi có người duyệt.

Đề xuất ba lớp memory:

1. **Project preference:** motion language đã được chủ dự án xác nhận.
2. **Scene decision:** quyết định riêng của scene hiện tại.
3. **Regression rule:** lỗi đã từng xảy ra và phải được test tự động.

Như vậy Skill “thông minh hơn” nhờ học từ quyết định có cấu trúc, không phải nhờ lưu toàn bộ chat hoặc tự sửa quy tắc production một cách không kiểm soát.

## 4. Contract để đồng bộ với nhiều Agent

### 4.1. Discovery boundary

`SKILL.md` nên tuân thủ Agent Skills specification với YAML frontmatter thật ở đầu file, tối thiểu là `name` và `description`, còn tài liệu sâu đặt trong `references/` hoặc tài nguyên tương ứng [1] [2] [3]. Bản hiện tại đang đặt các trường name/description dạng Markdown ở đầu file; con người đọc được nhưng không phải frontmatter YAML chuẩn.

Nên thêm `agent-card.json`:

```json
{
  "name": "motionloom",
  "version": "2.0.0",
  "description": "Project-aware animation production and verification",
  "capabilities": [
    "project.analyze",
    "motion.plan",
    "asset.provenance",
    "rig.cutout",
    "runtime.render.lottie",
    "devlab.review",
    "quality.gate",
    "pr.prepare"
  ],
  "input_artifacts": ["host-project", "asset", "animation-request"],
  "output_artifacts": ["motion-spec", "runtime-scene", "evidence-bundle", "pr-patch"],
  "side_effects": {
    "read_files": true,
    "write_files": true,
    "network": "optional",
    "git_commit": "explicit-confirmation",
    "git_push": "explicit-confirmation"
  },
  "verified_runtimes": ["lottie-json", "svg-cutout-rig"],
  "scaffold_only_runtimes": ["rive", "gsap", "framer-motion", "spine", "threejs"]
}
```

### 4.2. Machine-readable I/O

Mọi CLI cần hỗ trợ `--json` hoặc JSON Lines, exit code ổn định và không bắt Agent parse prose. Một Agent planner sẽ gọi analyzer; Agent animation sẽ đọc context và spec; Agent reviewer sẽ đọc snapshots và quality report; Agent release mới được gọi `pr.prepare`. Đây là composition rõ ràng hơn việc một Agent phải đọc toàn bộ README rồi đoán command.

### 4.3. MCP mapping

Nếu sau này expose qua MCP, mapping tự nhiên là:

| MCP capability | Animation Skill resource |
|---|---|
| Resources | project context, manifest, asset catalog, motion spec, snapshots, quality report |
| Prompts | analyze-project, plan-motion, diagnose-render-failure, prepare-review |
| Tools | analyze, generate-spec, rig, render, validate, quality-gate, prepare-pr |

Các tool `commit`, `push` và `open-pr` phải yêu cầu explicit confirmation. MCP guidance coi tool execution là vùng có rủi ro và yêu cầu consent, privacy và access control [6].

## 5. Khoảng trống cụ thể của repo hiện tại

| Mức | Khoảng trống | Tác động |
|---|---|---|
| P0 | `SKILL.md` chưa dùng YAML frontmatter chuẩn | Một số Agent discovery có thể không nhận metadata |
| P0 | Chưa có `agent-card.json`, task state hoặc artifact schema | Agent khác khó handoff mà không đọc implementation |
| P0 | Chưa có `skills-ref validate` trong CI | Không có gate format chuẩn mở |
| P1 | Chưa có `motion-ir.schema.json` và adapter contract | Nhiều template nhưng chưa có semantic portability |
| P1 | `references/` và progressive disclosure chưa được tổ chức theo skill spec | Context loading còn phụ thuộc Agent đọc docs thủ công |
| P1 | Runtime verification chủ yếu đã chứng minh cho Lottie/SVG rig | Rive, GSAP, Framer Motion, Spine, Three.js cần ghi là scaffold-only cho đến khi có adapter test |
| P1 | Asset provenance còn là attribution README, chưa phải manifest/checksum machine-readable | Khó audit license và reproducibility |
| P2 | Chưa có visual regression, performance benchmark và reduced-motion browser test đầy đủ | Có thể lọt lỗi hiển thị hoặc budget |
| P2 | Chưa có release signing/SBOM/dependency permission inventory | Trust khi cài từ GitHub còn yếu |

## 6. Roadmap ưu tiên

### P0 — Interoperability minimum

Chuẩn hóa `SKILL.md` frontmatter; thêm `agent-card.json`; thêm schema cho `project-context`, `motion-spec`, `task`, `artifact-manifest`, `review` và `quality-report`; chuyển docs chuyên sâu về `references/`; thêm `skills-ref validate` vào CI; bổ sung `--json`, stable exit codes và capability levels.

### P1 — Animation intelligence

Xây `motion-ir`; viết adapter contract; thêm asset provenance manifest; kết nối Dev Lab với `task.json` và `review.json`; tạo regression corpus cho body pose, easing, reduced-motion và frame snapshots; mở rộng runtime verification ít nhất cho một adapter Rive hoặc GSAP trước khi tuyên bố đa framework.

### P2 — Production trust và multi-Agent scale

Thêm visual diff theo ngưỡng, performance benchmark trên target device, accessibility browser tests, SBOM, dependency pinning, release checksum/signing, remote task polling và MCP/A2A facade tùy host. Chỉ cần thêm remote protocol khi local artifact contract đã ổn định.

## 7. Metrics để chứng minh Skill tốt hơn

Không nên đo bằng số lượng template hoặc số sao GitHub. Nên đo bằng các chỉ số sau:

| Metric | Cách đo | Mục tiêu định hướng |
|---|---|---|
| Context fidelity | Tỷ lệ scene pass context/hash/brand gate ngay lần đầu | Tăng dần theo project |
| Runtime verification rate | Tỷ lệ artifact đạt `runtime-verified` trên tổng artifact | Không trộn với scaffold |
| Reproducibility | Cùng input/context tạo cùng manifest/hash/evidence | 100% cho deterministic path |
| Defect escape rate | Lỗi phát hiện sau PR / tổng lỗi | Giảm theo regression corpus |
| Handoff success | Agent tiếp theo tiếp tục task chỉ từ artifact bundle | Đo bằng replay test |
| Review efficiency | Số vòng sửa từ preview đến confirm | Giảm nhưng không hy sinh chất lượng |
| Provenance coverage | Tỷ lệ asset có URL/license/checksum | 100% cho production asset |
| Human override safety | Tỷ lệ destructive actions có explicit confirmation | 100% |

## 8. Định vị nên dùng

> **Animation Skill Kit là lớp compiler và evidence cho Agent làm animation: hiểu host project, chuyển intent thành motion semantics, biên dịch sang runtime phù hợp, chứng minh bằng render thật, và bàn giao artifact có thể review/PR.**

Nó không nên tự quảng cáo là “AI tạo mọi loại animation”. Cách định vị đáng tin hơn là:

> **Project-aware, runtime-verified, agent-composable animation workflow.**

Đây là khác biệt có thể kiểm chứng bằng file, schema, test và artifact. Prompt hay có thể bị sao chép trong một ngày; nhưng context compiler, motion IR, evidence corpus, adapter test matrix, provenance và regression history mới là tài sản khó sao chép và tạo giá trị dài hạn.

## References

[1]: https://agentskills.io/specification "Agent Skills specification"

[2]: https://github.com/anthropics/skills "Anthropic Agent Skills repository"

[3]: https://code.visualstudio.com/docs/agent-customization/agent-skills "VS Code Agent Skills documentation"

[4]: https://github.com/talknerdytome-labs/wiggle-claude-skill "Wiggle logo animation skill"

[5]: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/ "Google Agent2Agent protocol announcement"

[6]: https://modelcontextprotocol.io/specification/2026-07-28 "Model Context Protocol specification"
