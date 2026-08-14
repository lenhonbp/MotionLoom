# Ghi chú evidence: kỹ năng nội bộ và Agent Skills đa nền tảng

**Ngày khảo sát:** 15 tháng 8 năm 2026

## ImageGen nội bộ

Skill `imagegen` hiện có của Agent là một bộ hướng dẫn routing/production cho visual deliverable. Với game asset, skill đặt tiêu chí là silhouette tái sử dụng, perspective nhất quán và clean edges; với transparent asset, tiêu chí gồm alpha sạch, subject đầy đủ, không colored fringe hoặc background/shadow không mong muốn. Skill yêu cầu phân biệt creation/editing mang tính semantic với image processing thuần deterministic, và yêu cầu lightweight validation trước delivery.

Điều này tạo một boundary rõ cho MotionLoom: ImageGen có thể là **nguồn tạo hoặc chỉnh visual asset**, còn MotionLoom nhận output cùng metadata, đo alpha/geometry/atlas/runtime và quản lý evidence/review. Không được giả định ImageGen tự phát hành seed, model version, license, rig map hoặc production approval. Vì không có API/credential contract trong core MotionLoom, adapter ban đầu phải là `scaffold` receipt importer, không phải provider invoker.

## Codex Skills

OpenAI mô tả Skill là bundle có version gồm file và `SKILL.md`, hỗ trợ local shell hoặc hosted container, và tương thích Agent Skills standard. Khi skill được mount, model nhìn metadata rồi quyết định kích hoạt; tài liệu cũng yêu cầu xem Skill là code/instruction đặc quyền, kiểm tra trước khi tích hợp và đặt approval cho high-impact action. [1]

MotionLoom cần tiếp tục giữ `SKILL.md`, artifacts và local-only default, đồng thời chỉ nhận generator metadata từ một skill đã được user/project cài đặt. Một skill descriptor không phải bằng chứng rằng output asset đã được tạo đúng hoặc được người dùng phê duyệt.

## Claude Code Skills

Claude Code mô tả Skill là thư mục có `SKILL.md`, có thể được load khi relevant hoặc gọi trực tiếp; built-in skills như `/debug`, `/code-review` và `/verify` cũng là prompt-based orchestration. Tài liệu đặc biệt có giá trị với MotionLoom ở ý tưởng ghi lại run/verify recipe trong project skill để agent sau đó lặp lại workflow đã thành công thay vì suy đoán lại environment. [2]

MotionLoom đã đi theo cùng hướng với Project Memory và `setup/status/repair`. Adapter registry sẽ chỉ lưu provider capability/evidence, không tự động chạy một external skill hay mở PR.

## Gemini CLI Skills

Gemini CLI cũng dùng Agent Skills standard với lifecycle discovery → activation → consent → injection → execution. Tài liệu nêu built-in, extension, user và workspace tiers; `.agents/skills/` được dùng làm alias interoperable. Activation cần consent và skill folder trở thành permitted path sau approval. [3]

Điều này củng cố hai yêu cầu cho MotionLoom: registry phải mô tả **capability** thay vì vendor prompt; và skill/adapter có side effect phải có explicit user approval. MotionLoom nên phát hành artifacts portable tại workspace/package level, nhưng không được trở thành một catalog tải/chạy skills tùy ý.

## Contract decision

Adapter registry sẽ dùng các giá trị sau:

| Field | Quyết định |
|---|---|
| `adapter_id` | Tên capability ổn định, ví dụ `local-fixture` hoặc `internal-imagegen`, không phải claim về ownership/model quality. |
| `kind` | `fixture`, `internal_skill`, `external_provider` hoặc `manual_import`. |
| `status` | `verified`, `scaffold` hoặc `blocked`, chỉ `verified` khi có regression và runtime evidence đúng phạm vi. |
| `invocation_mode` | `none`, `manual`, `agent-mediated` hoặc `api`; core validator không thực thi invocation. |
| `cost_class` | `included`, `metered`, `external`, `unknown`; informational only, không phải billing proof. |
| `evidence_requirements` | Receipt, output hashes, source/provenance reference và runtime evidence tùy output kind. |
| `approval` | Luôn external/user; registry/receipt không chứa quyền mở PR hay production approval. |

## References

[1]: https://developers.openai.com/api/docs/guides/tools-skills "OpenAI API — Skills"
[2]: https://code.claude.com/docs/en/skills "Claude Code — Skills"
[3]: https://geminicli.com/docs/cli/skills/ "Gemini CLI — Agent Skills"
