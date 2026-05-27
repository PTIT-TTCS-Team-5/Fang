# Antigravity Understand Manual

Ghi chú tạm thời cho việc dùng `lum1104/Understand-Anything` với Antigravity và Antigravity IDE trong FANG.

## Kết luận hiện tại

Antigravity 2.x đã đọc được skill nếu chỉ đích danh file `SKILL.md`, nhưng chưa đáng tin để tự liệt kê hoặc register thành slash command trong menu `/`.

Vì vậy, khi cần dùng Understand trong Anti/Anti IDE, dùng prompt bắt buộc agent đọc skill file cụ thể thay vì chỉ gõ `/understand`.

## Prompt dùng ngay

Dùng prompt này trong project FANG:

```text
Use the workspace skill named understand.

First read and follow this exact file:
C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand\SKILL.md

In your first response, state the exact SKILL.md path you loaded, then execute the workflow for this workspace.
```

Nếu cần rebuild đầy đủ:

```text
Use the workspace skill named understand.

First read and follow this exact file:
C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand\SKILL.md

Run it with --full for this workspace. In your first response, state the exact SKILL.md path you loaded.
```

Nếu cần output tiếng Việt:

```text
Use the workspace skill named understand.

First read and follow this exact file:
C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand\SKILL.md

Run it with --language vi for this workspace. In your first response, state the exact SKILL.md path you loaded.
```

## Dấu hiệu agent đã dùng đúng skill

- Agent nói rõ đã đọc `C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand\SKILL.md`.
- Agent chạy workflow theo phase, ví dụ `[Phase 1/7]`, `[Phase 2/7]`.
- Kết quả tạo hoặc cập nhật `.understand-anything/knowledge-graph.json`.
- Nếu cần xem UI, dùng tiếp skill `understand-dashboard` bằng cách chỉ rõ file:

```text
Use the workspace skill named understand-dashboard.

First read and follow this exact file:
C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand-dashboard\SKILL.md

Open the dashboard for the current Understand-Anything graph.
```

## Đường dẫn skill đã cài

Project-local, ưu tiên cho FANG:

- `C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand\SKILL.md`
- `C:\Users\os\Desktop\cur_prj\Fang\.agent\skills\understand\SKILL.md`

Global, dùng cho Anti/Anti IDE nếu bản mới:

- `C:\Users\os\.gemini\antigravity\skills\understand\SKILL.md`
- `C:\Users\os\.gemini\antigravity-ide\skills\understand\SKILL.md`

Hiện tại project-local đang ẩn khỏi Git bằng `.git/info/exclude`, không cần commit `.agents/` hoặc `.agent/`.

## Cập nhật Understand-Anything

Chạy trong PowerShell:

```powershell
cd C:\Users\os\.understand-anything\repo
git pull
```

Nếu upstream có thay đổi package/dependency, chạy thêm:

```powershell
pnpm install
```

Sau khi update, verify các path project-local vẫn tồn tại:

```powershell
Test-Path C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand\SKILL.md
Test-Path C:\Users\os\Desktop\cur_prj\Fang\.agents\skills\understand-dashboard\SKILL.md
```

Nếu path bị mất, tạo lại junction từng skill:

```powershell
$srcRoot = 'C:\Users\os\.understand-anything\repo\understand-anything-plugin\skills'
$targets = @(
  'C:\Users\os\.gemini\antigravity\skills',
  'C:\Users\os\.gemini\antigravity-ide\skills',
  'C:\Users\os\Desktop\cur_prj\Fang\.agents\skills',
  'C:\Users\os\Desktop\cur_prj\Fang\.agent\skills'
)
$skills = Get-ChildItem -LiteralPath $srcRoot -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') }
foreach ($target in $targets) {
  New-Item -ItemType Directory -Path $target -Force | Out-Null
  foreach ($skill in $skills) {
    $link = Join-Path $target $skill.Name
    if (-not (Test-Path -LiteralPath $link)) {
      New-Item -ItemType Junction -Path $link -Target $skill.FullName | Out-Null
    }
  }
}
```

Restart Antigravity/Antigravity IDE sau khi update nếu đang mở.

## Ghi chú vận hành

- Nếu `/understand` bắt đầu hiện trong menu `/`, có thể dùng trực tiếp. Nếu không hiện, dùng prompt bắt đọc `SKILL.md`.
- Khi hỏi agent "list skills", có thể nó chỉ liệt kê tool/MCP/subagent thay vì agent skills. Test chắc hơn là bắt nó đọc file skill và yêu cầu lặp lại path đã đọc.
- Khi agent nói "có thể làm" nhưng chưa tạo `.understand-anything/knowledge-graph.json`, coi như mới đọc instruction, chưa thực thi workflow.
