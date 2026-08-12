# Audit checklist — animation-skill-kit

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
