# ChatGPT handoff — Scout v3 walk poses

## Mục tiêu

Tạo **ba file PNG riêng biệt** cho walk cycle của Scout v3: `contact-right`, `passing`, và `contact-left`. Đây là **source asset** cho MotionLoom, không phải ảnh minh họa. Vì vậy, mỗi output phải có duy nhất một robot, kích thước canvas cố định, padding đo được, và không có chi tiết nền hay hiệu ứng có thể làm sai phép đo alpha/geometry.

> **Trust boundary:** Mọi output từ ChatGPT là `ai_generated`. Prompt không cấp `artist_authored`, `production_eligible`, `production_approved`, hoặc runtime approval. MotionLoom sẽ đo lại bytes PNG, alpha, padding, contamination và hash trước khi ingest.

## Chuẩn bị trong ChatGPT

Tải **một ảnh tham chiếu duy nhất**: `motionloom-ai-pilot-scout-v3-idle-alpha.png`. Hãy gửi **từng prompt một**, tải file PNG nguyên gốc của từng kết quả, và không dùng screenshot hay ảnh đã nén lại.

| Pose | Tên file khi tải về | Mục đích |
|---|---|---|
| Contact right | `motionloom-ai-pilot-scout-v3-chatgpt-contact-right.png` | Chân phải chạm đất ở phía trước. |
| Passing | `motionloom-ai-pilot-scout-v3-chatgpt-passing.png` | Hai chân đi qua nhau dưới thân. |
| Contact left | `motionloom-ai-pilot-scout-v3-chatgpt-contact-left.png` | Chân trái chạm đất ở phía trước. |

## Prompt chung — dán kèm từng pose

```text
Use the uploaded image only as the identity reference for one game-ready pixel-art sprite frame.

Create exactly ONE 1920 × 1920 PNG image of the same small cream-and-orange scout robot. Preserve the reference’s 3/4 front-facing camera angle, silhouette, palette, pixel density, head antenna, torso emblem, limbs, and apparent scale. The robot must be centered horizontally and fully visible.

POSE INSTRUCTION: [REPLACE THIS LINE WITH ONE POSE BLOCK BELOW]

SOURCE-ASSET CONTRACT:
- Use a genuinely transparent background if supported. Otherwise use one perfectly flat solid #00FF00 green background only.
- Keep at least 180 px completely empty padding on all four canvas edges.
- Keep the robot’s feet on an invisible common baseline; do not crop any body part.
- Produce only the robot. Do not add a floor, cast shadow, reflection, glow, scenery, props, text, watermark, label, checkerboard, frame border, gradient, texture, noise, line, disconnected pixel cluster, or any second object.
- Use crisp pixel-art edges; do not add an anti-aliased halo or motion blur.
- Return the image only, not a collage, animation sheet, UI mockup, explanation, or multiple alternatives.

This is a deterministic animation source asset, not a concept-art request.
```

## Ba pose block

### 1. `contact-right`

```text
Walk-cycle contact-right: the right foot is forward and flat on the baseline, while the left foot trails behind. Both feet are fully visible. The body leans only slightly forward in a natural walk rhythm; do not change the robot design.
```

### 2. `passing`

```text
Walk-cycle passing pose: the legs pass beneath the body; one knee is slightly forward and one foot passes the planted leg. Both feet remain fully visible and the torso stays centered over the same baseline. Do not change the robot design.
```

### 3. `contact-left`

```text
Walk-cycle contact-left: the left foot is forward and flat on the baseline, while the right foot trails behind. Both feet are fully visible. The body leans only slightly forward in a natural walk rhythm; do not change the robot design.
```

## Cách bàn giao

Sau khi tải về, đặt ba PNG ở một thư mục và cung cấp cho MotionLoom. Kèm theo một note tối thiểu như sau; nếu ChatGPT UI không hiển thị model/version, ghi `not_exposed_by_ui` thay vì suy đoán.

```json
{
  "provider": "chatgpt",
  "authority": "ai_generated",
  "master_reference": "motionloom-ai-pilot-scout-v3-idle-alpha.png",
  "model": "not_exposed_by_ui",
  "task_id": "motionloom-scout-v3-chatgpt-walk-YYYYMMDD",
  "outputs": [
    "motionloom-ai-pilot-scout-v3-chatgpt-contact-right.png",
    "motionloom-ai-pilot-scout-v3-chatgpt-passing.png",
    "motionloom-ai-pilot-scout-v3-chatgpt-contact-left.png"
  ]
}
```

MotionLoom sẽ dùng bytes thật để tính SHA-256, kiểm tra alpha/padding/contamination, đo geometry, xây provenance và chỉ sau đó chạy Artifact Intake. Một frame không đạt sẽ chặn toàn bộ cycle; không thay frame lỗi bằng idle lặp hoặc cấp approval thủ công.
