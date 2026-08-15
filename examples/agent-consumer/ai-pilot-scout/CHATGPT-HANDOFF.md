# ChatGPT handoff — Scout v3 walk sources

## Cách dùng

1. Mở một cuộc trò chuyện ChatGPT mới và upload file **`motionloom-ai-pilot-scout-v3-idle-alpha.png`**.
2. Gửi **khối nền tảng** bên dưới, sau đó gửi **mỗi pose ở một tin nhắn riêng**. Không yêu cầu ChatGPT làm contact sheet hoặc tạo cả ba trong cùng một ảnh.
3. Khi một pose đã hoàn tất, tải **file PNG gốc** do ChatGPT trả về. Không dùng screenshot, không flatten lên nền đen và không tự resize/crop/pad file.
4. Đổi tên file tải về đúng tên dưới từng pose, rồi gửi lại ba file PNG gốc cùng URL hoặc ID cuộc trò chuyện ChatGPT nếu hiển thị.

> Đây là source `ai_generated` cho pilot review. Nó không phải asset `artist_authored`, không được suy diễn license, và không thay thế human production approval.

## Khối nền tảng — gửi một lần trước pose đầu tiên

```text
The attached file motionloom-ai-pilot-scout-v3-idle-alpha.png is the locked visual identity reference for one review-only MotionLoom pilot. Treat it as a source reference, not as a request to redesign the character.

For every requested pose, produce exactly ONE separate, complete 2D pixel-art robot scout source sprite. Preserve the same cream, orange, black, and cyan palette; head shape; antenna; face; shoulder pads; torso; hands; feet; pixel density; crisp outlines; apparent scale; camera; and left-to-right orientation. Only change the limb pose required by the named walk phase.

Output requirements are mandatory:
- transparent RGBA PNG source, exactly 1920 × 1920 pixels;
- exactly one isolated character, no duplicate, no crop, no text, no caption, no UI, no frame, no prop;
- no black, white, checkerboard, coloured, textured, or gradient background;
- no floor, contact shadow, cast shadow, glow, particles, smoke, dust, reflection, or stray bands;
- hard crisp pixel-art edges: no blur, no feathering, no anti-aliased halo;
- approximately 800 px visible character width and 1450 px visible character height;
- centered near x=940; leave at least 120 px of fully transparent empty padding on each of the four edges;
- the lowest opaque sole pixels must align near y=1626, with both feet fully inside the canvas.

Do not zoom, crop, mirror, rotate, recolor, restyle, add accessories, alter the character scale, or generate a pose sheet. If you cannot preserve the transparent 1920 × 1920 source canvas and the required empty padding, say so instead of silently changing those requirements.
```

## Pose 1 — contact right

```text
Create pose `contact-right` now. This is the forward contact phase of a left-to-right walk cycle: the RIGHT foot is planted forward on the shared footline near y=1626; the LEFT leg trails naturally behind; arms counter-swing; torso stays upright. It must be a distinct walk action pose, not an idle variation. Return one transparent PNG source only.
```

Rename the downloaded original file to:

```text
motionloom-ai-pilot-scout-v3-chatgpt-contact-right.png
```

## Pose 2 — passing

```text
Using the same locked attached Scout v3 reference and the same output geometry, create pose `passing` now. This is the passing phase of the same left-to-right walk cycle: one leg passes beneath the upright body; stride is compact and balanced; both feet remain fully visible and inside the canvas; arms counter-swing. It must be a distinct walk action pose, not an idle variation. Return one transparent PNG source only.
```

Rename the downloaded original file to:

```text
motionloom-ai-pilot-scout-v3-chatgpt-passing.png
```

## Pose 3 — contact left

```text
Using the same locked attached Scout v3 reference and the same output geometry, create pose `contact-left` now. This is the complementary forward contact phase of the same left-to-right walk cycle: the LEFT foot is planted forward on the shared footline near y=1626; the RIGHT leg trails naturally behind; arms counter-swing. Do not mirror or redesign contact-right; preserve the locked visual identity and make this a distinct walk action pose. Return one transparent PNG source only.
```

Rename the downloaded original file to:

```text
motionloom-ai-pilot-scout-v3-chatgpt-contact-left.png
```

## Khi gửi output lại

Gửi ba file PNG nguyên gốc theo đúng tên, không zip nếu giao diện có thể upload trực tiếp. Nếu ChatGPT hiển thị một conversation URL, task ID, hoặc thời điểm tạo, gửi kèm thông tin đó. MotionLoom sẽ tự đo alpha, geometry, padding, footline, contamination, identity drift và SHA-256; prompt không tự cấp intake, runtime candidate hay approval.
