# Codex handoff — Scout v3 walk sources

## Mục tiêu và ranh giới

Bạn đang hỗ trợ tạo **ba source sprite AI độc lập** cho review-only pilot của MotionLoom. Đây là việc tạo **source bytes mới**, không phải post-process các file ChatGPT đã bị reject. Dùng capability tạo ảnh mà môi trường Codex thực sự có; nếu không có capability đó, hãy dừng và báo rõ blocker thay vì tạo placeholder, screenshot hoặc PNG giả.

Mọi output phải giữ `authority: ai_generated`. Không được gắn `artist_authored`, `production_eligible`, `production_approved`, license suy diễn hoặc runtime approval.

## Reference bắt buộc

Dùng file sau làm **khóa nhận diện**, không redesign:

```text
motionloom-ai-pilot-scout-v3-idle-alpha.png
```

Nếu file reference chưa có trong workspace Codex, yêu cầu người dùng upload/copy đúng file trước khi tạo bất kỳ pose nào.

## Cách thực hiện bắt buộc

1. Tạo **mỗi pose trong một request/image riêng**. Không làm contact sheet, sprite sheet hoặc ba nhân vật trong một canvas.
2. Mỗi lần tạo phải yêu cầu renderer trả **PNG RGBA gốc 1920 × 1920**. Đây là kích thước source, không được tạo 1254×1254 rồi resize/canvas-pad sau đó.
3. Lưu nguyên bytes gốc, không crop, resize, pad, alpha-isolate, flatten, screenshot hoặc tối ưu lại file để bypass gate.
4. Trả ba PNG và metadata có thể biết được: provider/tool, model (nếu UI hiển thị), request/task/conversation ID hoặc URL, timestamp và prompt cuối cùng. Nếu metadata không tồn tại, nói rõ là `not exported`; không bịa receipt.
5. Sau khi trả output, để MotionLoom chạy preflight độc lập. Codex không tự chạy Artifact Intake, không cấp runtime candidate, không mở PR và không tự phê duyệt.

> **Failure policy:** Nếu tool không bảo toàn canvas 1920×1920 RGBA với empty padding yêu cầu, trả `blocked` cùng thông tin tool đã dùng. Không sửa bytes có sẵn để làm pass.

## Capability preflight — bắt buộc trước ba pose

Chỉ tạo thử **`contact-right` trước**. Ngay sau khi công cụ trả file gốc, kiểm tra metadata/bytes thực tế trước khi tạo `passing` hoặc `contact-left`:

| Điều kiện | Kết quả cần có | Khi fail |
|---|---|---|
| Canvas | `1920 × 1920` | Dừng; không tạo hai pose còn lại. |
| Color mode | `RGBA` với alpha thật | Dừng nếu nhận `RGB` hoặc alpha bị flatten. |
| Background | Các pixel ngoài nhân vật trong suốt thật | Dừng nếu nền đen, trắng, caro hoặc grid bị rasterize. |
| Export semantics | File gốc, không screenshot hay preview | Dừng nếu tool chỉ cho preview không có PNG source. |

> Lần thử Codex `exec-6c962cac-7e7f-491b-b0a8-e7c4ee7d2412` đã trả 1254×1254 RGB với checkerboard rasterized. Đó là **giới hạn exporter đã quan sát**, không phải lỗi cần chữa bằng resize, alpha isolate hoặc canvas padding. Chỉ thử lại khi capability khác có thể xuất PNG RGBA 1920×1920 gốc.

## Prompt nền tảng cho image-generation capability

Gửi nguyên khối sau cùng master reference. Giữ nguyên tiếng Anh để công cụ tạo ảnh diễn giải hình học chính xác hơn.

```text
The attached file motionloom-ai-pilot-scout-v3-idle-alpha.png is the locked visual identity reference for one review-only MotionLoom pilot. Treat it as a source reference, not as a request to redesign the character.

Create exactly ONE separate, complete 2D pixel-art robot scout source sprite for the named walk pose. Preserve the same cream, orange, black, and cyan palette; head shape; antenna; face; shoulder pads; torso; hands; feet; pixel density; crisp outlines; apparent scale; camera; and left-to-right orientation. Only change the limb pose required by the named walk phase.

Mandatory source geometry:
- original transparent RGBA PNG, exactly 1920 × 1920 pixels;
- one isolated character only; no duplicate, no crop, no text, no caption, no UI, no frame, no prop;
- no black, white, checkerboard, coloured, textured or gradient background;
- no floor, contact shadow, cast shadow, glow, particles, smoke, dust, reflection or stray bands;
- hard crisp pixel-art edges; no blur, feathering or anti-aliased halo;
- approximately 800 px visible character width and 1450 px visible character height;
- centered near x=940; at least 120 px of fully transparent empty padding on every edge;
- lowest opaque sole pixels aligned near y=1626, with both feet fully inside the canvas.

Do not zoom, crop, mirror, rotate, recolor, restyle, add accessories, alter character scale or generate a pose sheet. If you cannot preserve the transparent 1920 × 1920 source canvas and required empty padding, report failure instead of silently changing requirements.
```

## Ba pose cần tạo

Sau khối nền tảng, tạo lần lượt từng pose bằng một request riêng.

| Pose | Prompt bổ sung | Tên file output bắt buộc |
|---|---|---|
| `contact-right` | `Create pose contact-right now. This is the forward contact phase of a left-to-right walk cycle: the RIGHT foot is planted forward on the shared footline near y=1626; the LEFT leg trails naturally behind; arms counter-swing; torso stays upright. Return one transparent PNG source only.` | `motionloom-ai-pilot-scout-v3-codex-contact-right.png` |
| `passing` | `Using the same locked reference and output geometry, create pose passing now. One leg passes beneath the upright body; stride is compact and balanced; both feet remain fully visible inside the canvas; arms counter-swing. Return one transparent PNG source only.` | `motionloom-ai-pilot-scout-v3-codex-passing.png` |
| `contact-left` | `Using the same locked reference and output geometry, create pose contact-left now. The LEFT foot is planted forward on the shared footline near y=1626; the RIGHT leg trails naturally behind; arms counter-swing. Do not mirror or redesign contact-right. Return one transparent PNG source only.` | `motionloom-ai-pilot-scout-v3-codex-contact-left.png` |

## Handoff lại MotionLoom

Gửi nguyên ba PNG theo đúng tên cùng metadata đã xuất được. MotionLoom sẽ ghi provider trung thực (ví dụ capability/tool thực tế mà Codex đã dùng), tính SHA-256 và đo alpha, canvas, subject bounds, padding, footline, contamination và identity. Chỉ khi bốn frame — master v3 và ba pose — pass, pipeline mới được phép chạy:

```text
build-ai-pilot → Artifact Intake → consistency → runtime candidate → runtime render → Dev Lab review-first
```
