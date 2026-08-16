# AI Repository Benchmark — research ledger

**Ngày bắt đầu:** 2026-08-16
**Phạm vi:** Các repository/tool AI công khai có bài học workflow, packaging hoặc runtime verification có thể đánh giá cho MotionLoom. Đây không phải là danh sách khuyến nghị tích hợp dependency.

## Phương pháp

Mỗi candidate được kiểm tra qua nguồn chính thức, README/license, yêu cầu triển khai, bề mặt security và mức độ phù hợp với invariant MotionLoom. Star count chỉ là tín hiệu phụ; không dùng làm bằng chứng chất lượng hay an toàn. Không thực thi code bên thứ ba trong đợt nghiên cứu này.

## Phát hiện ban đầu

| Candidate | Nhóm | Điều nguồn chính thức xác nhận | Bài học tiềm năng cho MotionLoom | Rủi ro/không sao chép |
|---|---|---|---|---|
| [Coze Studio](https://github.com/coze-dev/coze-studio) | Agent workflow | Công cụ phát triển agent all-in-one với prompt, RAG, plugin, workflow; có templates, low/no-code canvas, API/SDK và self-host qua Docker Compose. README cảnh báo rõ public deployment có bề mặt registration, Python workflow execution, SSRF và API privilege risks. License Apache-2.0. | Progressive disclosure: quick setup, sau đó mới model/plugin/workflow configuration. Hiển thị explicit security posture bên cạnh workflow launch. | Không áp dụng visual canvas như authority; MotionLoom phải giữ artifact identity, runtime evidence và user review là nguồn truth. Không gọi code execution node tùy ý từ app/Dev Lab. |
| [Dify](https://github.com/langgenius/dify) | Agent workflow | Nền tảng app LLM có workflow, RAG, agents, model management, observability và APIs; quick start rõ ràng qua Docker Compose; mô tả environment/config separation. License là Dify Open Source License dựa trên Apache-2.0 với điều kiện bổ sung. | Onboarding theo tầng: cài nhanh, dashboard init, cấu hình môi trường rõ; observability là bề mặt sản phẩm chứ không phải log ẩn. | Không sao chép license/model hosting approach; không dùng dashboard telemetry làm bằng chứng production approval. Không mở mơ hồ các provider credential vào repository. |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) và [workflow templates](https://github.com/Comfy-Org/workflow_templates) | Visual workflow | Node graph cho image/video/audio/3D/text; JSON save/load workflows, reusable subgraphs, templates, local API, App Mode và khả năng recover workflow/seed từ media được hỗ trợ. Repo template dùng manifest regenerated với SHA-256 mismatch gate; production chỉ deploy workflow có `status: approved`, preview có thể hiển thị trạng thái khác. | Đưa `approved/rejected/deprecated` vào index workflow/template, bắt buộc manifest hash và expose một review surface giản lược cho end user thay vì tất cả graph controls. | Không xem JSON graph/seed là provenance hoặc runtime evidence. Không nhận custom-node metadata như source tin cậy; mọi external template phải qua intake và identity binding của MotionLoom. |
| [Wan2.1](https://github.com/Wan-Video/Wan2.1) | Video generation | Model suite hỗ trợ T2V, I2V, FLF2V, editing/VACE; README công bố rõ task/resolution/model và links checkpoint. Có integration Diffusers/ComfyUI và nêu ràng buộc VRAM, resolution stability, model-specific prompt guidance. | `generation-profile` phải tách task/model/resolution/frames/provider; lấy capability, hardware expectation và model/checkpoint identity thành evidence thay vì claim chung chung “AI video generated”. | Không tích hợp model runtime vào MotionLoom core và không suy diễn quality từ model name. Kết quả video/pose từ bất kỳ provider nào vẫn là `ai_generated`, cần geometry/consistency/runtime review. |
| [HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) | Video/human animation | Cung cấp inference/weights, I2V, Avatar, custom generation, benchmark và các integration. README ghi rõ dependency CUDA/Linux, memory requirement cao và phạm vi environment đã test. | Cần consumer-facing capability card: platform, runtime, GPU/memory, tested environment, source model/version và failure mode trước khi Agent đề xuất một generation route. | Không hứa “one-click” nếu phần cứng/OS không đáp ứng. Không dùng self-reported benchmark để thay runtime verification hay human approval. |
| [Xinference](https://github.com/xorbitsai/inference) | Local model serving | Model server self-hosted cho language, speech và multimodal; có OpenAI-compatible REST, RPC, CLI, WebUI, Docker/Kubernetes examples và thể hiện rõ CPU/Metal/GPU/distributed capabilities. README có migration notes cho breaking change. | Đăng ký **capability card** và compatibility/migration note theo adapter version; Agent chỉ đề xuất provider/runtime đã thỏa platform, hardware, credential và health-check profile. | MotionLoom không trở thành model server, không mở endpoint model nội bộ ra artifact/Dev Lab, không tự chạy Docker/model download từ brief người dùng. |
| [ModelScope](https://github.com/modelscope/modelscope) | Model registry / MaaS | Unified abstraction cho inference, training, evaluation, export, deployment; model/dataset hub, version/cache management, modular task pipeline và Docker images theo CPU/GPU. README cũng nêu dependency/OS incompatibilities của một số model. | Tách **identity** (provider/model/checkpoint/version/license) khỏi **capability** (task, input constraints, platform, hardware, known limitations), và fail closed khi metadata tối thiểu thiếu. | Không coi registry listing là license/provenance đã xác minh, không nhận “few lines to run” là bằng chứng reproducibility hoặc cross-platform support. |
| [CogVideo](https://github.com/zai-org/CogVideo) | Video generation | README công bố task T2V/I2V/continuation, model task matrix, resolution/frame divisibility, precision, VRAM/timing benchmark, requirement Python và model-specific license notes. Nó cũng nêu prompt optimization và external model dependence. | Mở rộng `generation-profile` thành matrix bắt buộc: task, model/checkpoint, resolution, frame formula, precision, expected VRAM/time, prompt-transform provider và source URLs. | Không chuyển benchmark tự công bố thành SLA; không biến prompt enhancement bởi external LLM thành `artist_authored` hoặc ẩn provider ở provenance. |

## Metadata GitHub tại thời điểm khảo sát

Snapshot dưới đây được lấy bằng GitHub CLI lúc **2026-08-16**. Nó chỉ là tín hiệu maintenance/community, không phải chứng nhận security, chất lượng hay tính phù hợp để tích hợp.

| Repository | Stars / forks | License GitHub nhận diện | Cập nhật gần nhất lúc khảo sát | Kết luận sàng lọc |
|---|---:|---|---|---|
| `coze-dev/coze-studio` | 21,453 / 3,117 | Apache-2.0 | 2026-08-16 | Mature reference cho progressive onboarding và self-host security posture. Không là dependency candidate. |
| `langgenius/dify` | 152,585 / 24,091 | Other (Dify Open Source License) | 2026-08-16 | Reference tốt cho product observability; cần tránh mọi code/license reuse. |
| `Comfy-Org/ComfyUI` | 127,883 / 15,057 | GPL-3.0 | 2026-08-16 | Reference tốt cho workflow packaging/manifest; không phù hợp để import code vào package MotionLoom. |
| `Wan-Video/Wan2.1` | 16,833 / 3,364 | Apache-2.0 | 2026-08-16 | Reference cho generation task/capability matrix và điều kiện runtime. |
| `Tencent-Hunyuan/HunyuanVideo` | 12,429 / 1,312 | Other | 2026-08-16 | Reference cho disclosure GPU/environment; license và model terms cần review theo từng checkpoint. |
| `zai-org/CogVideo` | 12,956 / 1,326 | Apache-2.0 | 2026-08-16 | Reference cho matrix resolution/frames/precision/VRAM; không coi benchmark là SLA. |
| `xorbitsai/inference` | 9,500 / 858 | Apache-2.0 | 2026-08-16 | Reference cho adapter capability/health-check/migration policy; không biến MotionLoom thành model server. |
| `modelscope/modelscope` | 9,091 / 961 | Apache-2.0 | 2026-08-16 | Reference cho tách model identity khỏi capability; registry listing không thay provenance. |

## Decision log sơ bộ

| Pattern | Quyết định | Lý do và guardrail MotionLoom |
|---|---|---|
| Quick start theo tầng, chỉ mở gate chuyên sâu khi cần | **Áp dụng ngay** | Phù hợp onboarding một-lệnh hiện có; deep gates vẫn fail-closed và không bị ẩn khỏi artifact. |
| Runtime capability card có adapter/platform/constraint/evidence | **Đã triển khai** | `motionloom capability card --format json` xuất projection chỉ đọc từ registry đã validate; không làm thay provenance, runtime evidence hoặc selection. |
| Generation profile có model/checkpoint/platform/hardware/constraint | **Hoãn có gate** | Bổ sung thông tin quyết định cho Agent trước khi gọi provider chỉ sau khi có schema, validator, provenance binding và regression; không mở provider credential trong core. |
| Hash-bound workflow/template manifest và trạng thái `approved/rejected/deprecated` | **Thí nghiệm có gate** | Chỉ áp dụng cho profile/template nội bộ sau khi có schema, validator và regression; không đồng nhất template approval với `production_approved`. |
| Visual node canvas hoặc dashboard như execution authority | **Từ chối** | Làm mờ artifact identity và mở khả năng thực thi node tùy ý, trái mô hình deterministic review-first. |
| Nhúng model server, tự tải model, hoặc provider credential vào MotionLoom core | **Từ chối** | Tăng bề mặt attack, chi phí vận hành và rủi ro secret; chỉ dùng adapter capability/card và explicit user setup. |
| Tuyên bố generated asset “artist-authored” vì prompt/model tốt | **Từ chối** | Vi phạm provider-truthful provenance và human-governed production boundary. |

## Cải tiến đã áp dụng

Capability card được triển khai như một **projection chỉ đọc** trên `capability-registry.json`, không phải registry hay policy thứ hai. Lệnh `motionloom capability card --format json` xác thực hash evidence trước khi xuất `id`, declared status, adapter version, compatibility, thời điểm kiểm chứng, inputs/outputs, evidence reference, limitations, fallback, risk và side-effect level. Card luôn nhắc Agent gọi selection trước execution; selection mới áp dụng evidence freshness/integrity.

| Hạng mục | Trạng thái | Cách kiểm chứng | Guardrail giữ nguyên |
|---|---|---|---|
| `motionloom capability card --format json` | Hoàn thành | Thử bằng registry repository thật và npm shortcut `pnpm intelligence:card` | Không chọn runtime, không refresh evidence, không tạo commit/PR. |
| Validation registry trước export | Hoàn thành | Regression cố ý sửa SHA-256 evidence; card trả lỗi non-zero | Fail-closed khi evidence thiếu, sai hash hoặc thoát repository. |
| Agent-facing CLI/help, npm script, agent-card, README | Hoàn thành | `pnpm docs:check`, CLI help và regression alias | Chỉ công bố discovery; không nâng `scaffold_only` thành `verified`. |
| Generation profile model/checkpoint/hardware | Chưa triển khai | Chưa có schema hay validator | Không suy diễn provider/model identity; tiếp tục dùng provenance/intake hiện hữu. |
| Hash-bound workflow/template recipe | Chưa triển khai | Cần schema riêng, approval-state vocabulary và test | Không đồng nhất template approval với `production_approved`. |

Kết quả regression: `pnpm test` pass toàn bộ suite, bao gồm export card, alias CLI và rejection với evidence bị sửa. `pnpm docs:check` và `git diff --check` cũng pass. Không có dependency hay code bên thứ ba nào được thêm từ các repository khảo sát.

## Nguồn

1. [Coze Studio README và self-host/security guidance](https://github.com/coze-dev/coze-studio)
2. [Dify README, self-hosting, observability và license notice](https://github.com/langgenius/dify)
3. [Dify Cloud product overview](https://dify.ai/)
4. [ComfyUI README: workflow JSON, API, App Mode và offline posture](https://github.com/Comfy-Org/ComfyUI)
5. [ComfyUI workflow templates: manifest, SHA-256 validation và release filtering](https://github.com/Comfy-Org/workflow_templates)
6. [Wan2.1 README: task matrix, integration và inference requirements](https://github.com/Wan-Video/Wan2.1)
7. [HunyuanVideo README: model scope, hardware requirements và test environment](https://github.com/Tencent-Hunyuan/HunyuanVideo)
8. [Xinference README: local serving, APIs, deployment và migration](https://github.com/xorbitsai/inference)
9. [ModelScope README: MaaS abstraction, registry, pipeline và platform constraints](https://github.com/modelscope/modelscope)
10. [CogVideo README: video task/memory matrix, precision, model scope và prompt guidance](https://github.com/zai-org/CogVideo)
