# MotionLoom Apple alpha — implementation status

**Ngày kiểm tra:** 16-08-2026  
**Phạm vi:** macOS Studio alpha, iOS/iPadOS Review companion, review contracts, local-first sync foundation và native CI.  
**Trạng thái source:** hoàn thành và đã kiểm thử local; chưa commit, push, ký hoặc phát hành.

## Kết luận

MotionLoom hiện có một lớp app Apple native-first bám đúng mô hình **artifact-first, runtime-evidence và human-governed** của repository. Lớp mới không thay thế CLI Node/Python, runtime adapters hoặc Dev Lab; nó biến evidence đã có thành Project Inspector, Timeline Desk và review surface native cho macOS/iOS.

> App không có khả năng cấp `production_approved`, tự chạy shell tùy ý, tự tạo PR, push Git, publish npm hay submit App Store. Các hành động này tiếp tục nằm ngoài native surface và phải qua cơ chế review/quyền hiện hữu.

| Thành phần | Đầu ra đã tạo | Trạng thái |
| --- | --- | --- |
| Canonical contracts | `contracts/apple/review-launch-descriptor.schema.json`, `review-decision.schema.json` và fixture hash-bound runtime-pilot | Đã hoàn thành; reject unknown fields và không biểu diễn production approval. |
| Contract runtime | `apps/apple/Packages/MotionLoomContracts` | Đã hoàn thành; Swift decoder fail-closed, migration version và identity binding. |
| Review core | `apps/apple/Packages/MotionLoomReview` | Đã hoàn thành; timeline, annotation, ba human review decisions và export review JSON deterministic. |
| Project bridge | `apps/apple/Packages/MotionLoomMacBridge` | Đã hoàn thành; security-scoped folder access, allow-list inspection commands, chặn path/URL không tin cậy. |
| macOS Studio | `apps/apple/MotionLoomStudio` và target `MotionLoomStudio` | Đã build và launch unsigned; có Project Inspector, Timeline Desk và native web surface mở Dev Lab review URL. |
| iOS/iPadOS companion | `apps/apple/MotionLoomReviewApp`, `MotionLoomReviewUI` và target `MotionLoomReview` | Đã build unsigned cho iPhone Simulator SDK; chỉ đọc evidence, scrub timeline, annotate và tạo review decision. |
| Đồng bộ review | `apps/apple/Packages/MotionLoomReviewSync` | Đã hoàn thành local-first outbox; chỉ đưa metadata review identity-bound vào sync adapter. |
| CI và hướng dẫn | `.github/workflows/apple.yml`, `apps/apple/scripts/emit-ios-simulator-destination.sh`, các tài liệu Apple | Đã hoàn thành; CI không ký, không publish và dùng dynamic simulator SDK destination. |

## Trust boundary giữ nguyên

Các package Swift dùng canonical contract và fixture từ repository thay vì sao chép policy validator sang Swift. `MotionLoomContracts` giới hạn review decision ở các trạng thái review của con người; `MotionLoomReview` chỉ export review record; `MotionLoomMacBridge` chỉ có lệnh inspection trong allow-list. CloudKit adapter cũng chỉ nhận review metadata đã identity-bound, không nhận source asset, repository, secret, production authority hoặc capability nâng quyền.

Mac app có thể mở project folder và xuất handoff review; iOS app có thể đọc candidate/evidence và ghi note theo timeline. Cả hai app không làm thay nhiệm vụ của Agent: Agent tiếp tục tạo/sửa artifact, chạy validator và render runtime thật; người dùng review trên native app rồi tạo data để Agent tiếp tục xử lý.

## Kiểm thử đã chạy trên Mac

| Kiểm tra | Kết quả |
| --- | --- |
| `pnpm test` từ repository root | **PASS** — toàn bộ regression suite, gồm Apple contract và signed attestation. |
| `pnpm run docs:check` | **PASS**. |
| `swift test` cho Contracts, Review, MacBridge, ReviewUI và ReviewSync | **PASS**. |
| `xcodebuild` unsigned target `MotionLoomStudio` với SDK macOS | **PASS**; Studio đã launch local. |
| `xcodebuild` unsigned target `MotionLoomReview` với SDK iPhone Simulator | **PASS**. |
| `git diff --check` | **PASS**. |

Trong quá trình acceptance trên macOS, regression cũ phát hiện giả định path không phù hợp với alias hệ thống `/var -> /private/var`. Các chỉnh sửa giới hạn trong `scripts/evidence-verifier.py`, `scripts/intelligence.py` và `scripts/attestation.py`: chỉ parent alias hệ thống này được xử lý đúng trên macOS; symlink tại hoặc bên trong scene, task, evidence, repository và replay roots vẫn bị reject. Toàn bộ regression suite đã pass sau thay đổi này.

## Blocker còn lại ngoài source code

| Hạng mục | Lý do chưa thực hiện | Điều kiện để hoàn thành |
| --- | --- | --- |
| iOS UI smoke trên simulator | Xcode đang có iPhone Simulator SDK để compile nhưng chưa có device runtime khả dụng để boot. | Cài một iOS Simulator runtime trong Xcode Settings, sau đó boot device và chạy UI smoke. |
| CloudKit sync live | Cần container thuộc Apple Developer account và entitlement có quyền của chủ sở hữu. | Chủ sở hữu tạo/chọn CloudKit container, quyết định retention/privacy và bật entitlement trong Xcode. |
| Ký/TestFlight/App Store | Cần Apple Developer Team, App IDs, bundle identifiers, signing và quyết định submit của chủ sở hữu. | Cấu hình signing, tạo archive, rồi chủ sở hữu duyệt upload TestFlight. |

Các blocker trên không làm source alpha bị lỗi; chúng là quyền tài khoản và hạ tầng bên ngoài mà MotionLoom không tự tạo hoặc tự chấp nhận thay người dùng.

## Bước tiếp theo sau khi commit/push được duyệt

Sau khi source được commit và push riêng, công việc hợp lý tiếp theo là cài iOS Simulator runtime, chạy UI smoke của Review companion, thiết kế CloudKit container review-only và chỉ sau đó mới cân nhắc beta TestFlight. Không nên thêm production approval, Git push hay asset upload capability vào app trước khi vòng review iOS đã được kiểm chứng trên device/simulator.
