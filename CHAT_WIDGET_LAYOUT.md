# Chat Widget Layout Diagram

## State 1: Closed (Initial)
```
┌─────────────────────┐
│                     │
│  Robo Animation     │  ← PNG frame animation (320x320)
│  (spinning dots)    │
│                     │
├─────────────────────┤
│  💬                 │  ← Chat toggle button (bright green)
└─────────────────────┘
Size: 320 x 362 pixels
```

## State 2: Open (After clicking 💬)
```
┌─────────────────────┐
│                     │
│  Robo Animation     │  ← PNG frame animation (320x320)
│  (spinning dots)    │
│                     │
├─────────────────────┤
│  💬                 │  ← Chat toggle button
├─────────────────────┤
│                     │
│ 💬 RAG Knowledge Chat│  ← Header
│                     │
├─────────────────────┤
│  You: What...       │  ← Message history (blue for user, green for RAG)
│  FRIDAY: From...    │
│                     │
│  (scroll area)      │
│                     │
│                     │
├─────────────────────┤
│ [Type here...] [Send]│ ← Input field with button
└─────────────────────┘
Size: 320 x 450 pixels (window expands)
```

## Behavior
1. **Button Color**: Bright green (#00ff00) on dark background (#0d0d0d)
2. **Click behavior**: 
   - First click: Window expands, chat panel appears, input field focused
   - Second click: Chat collapses, back to small size
3. **Without RAG setup** (no chromadb):
   - Warning message appears in orange/red
   - Input field disabled (greyed out)
   - Explains how to install chromadb

## Chat Colors
- **You**: Cyan (#00ffff) 
- **FRIDAY (RAG response)**: Green (#00ff00)
- **System messages**: Red (#ff6b6b)
- **Thinking...**: Yellow (#ffff00)
