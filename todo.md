# Audit checklist — animation-skill-kit

- [ ] Đọc skill-creator và xác định quy trình cập nhật skill an toàn.
- [ ] Kiểm tra cấu trúc repo, tài liệu, package/dependency và executable scripts.
- [ ] Trace end-to-end: analyze → spec → source → generate/rig → render → Dev Lab → quality → PR.
- [ ] Kiểm tra CLI help, đường dẫn tương đối, cwd, environment và lỗi dependency.
- [ ] Đối chiếu framework, Lottie/dotLottie, Rive, GSAP, Framer Motion, rigging và asset attribution với nguồn chuẩn.
- [ ] Kiểm tra project-context có thực sự được dùng xuyên suốt hay chỉ được tạo rồi bỏ qua.
- [ ] Kiểm tra render snapshot là render thật hay placeholder/fallback; phân biệt rõ trong quality gate.
- [ ] Kiểm tra Dev Lab có kết nối với scene output/spec/checklist thực tế hay chỉ là demo tĩnh.
- [ ] Sửa các lỗi xác nhận được; không che giấu lỗi bằng mock hoặc placeholder trong acceptance path.
- [ ] Bổ sung test cho happy path, failure path, path resolution, project binding và PR preflight.
- [ ] Chạy lại test, smoke test CLI, kiểm tra CI YAML và tạo báo cáo audit.
- [ ] Đóng gói bản repo đã audit và bàn giao changelog, rủi ro còn lại, hướng dẫn GitHub.
