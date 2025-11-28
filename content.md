Of course. I will apply the fix based on the analysis.

The plan is to modify the application's CSS file to change the sizing behavior of the `Static` widget used for the raw text view. This will force it to report its full content height, which in turn will trigger its parent container's scrollbar, making its behavior consistent with the `Markdown` widget.

## [WIP] fix: Enable scrolling for raw text view in TUI

### 用户需求
The raw text view (`Static` widget) in the TUI is missing a scrollbar for oversized content, unlike the Markdown view. This needs to be fixed to allow users to see the entire content of a node in raw text mode.

### 错误分析
The issue stems from the default sizing behavior of Textual's `Static` widget. Unlike the `Markdown` widget, which reports a "virtual size" based on its entire content, the `Static` widget conforms to the space allocated by its parent container. Consequently, it never reports a size larger than its container, so the parent container never overflows and never displays a scrollbar.

### 评论
This is a crucial UX consistency fix. Ensuring both rendering modes are fully functional and behave predictably (i.e., both are scrollable) is essential for a polished and usable interface.

### 目标
1.  Modify the CSS file `packages/quipu-cli/src/quipu/cli/tui.css`.
2.  Add a new style rule for the `#content-placeholder` widget.
3.  Set the CSS property `shrink: false;` for this widget.

### 基本原理
By setting `shrink: false;` in the CSS, we instruct Textual's layout engine not to shrink the `Static` widget to fit its container. Instead, the widget will claim all the vertical space required to render its entire content. This larger size will correctly cause its parent container (`#content-view`) to overflow, which will then automatically trigger the appearance of the vertical scrollbar.

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/ui #task/object/tui-performance #task/action/optimization #task/state/continue

---

### Script

#### Acts 1: Update TUI stylesheet to fix scrolling

We will use `write_file` to establish the correct and complete CSS for the TUI, including the necessary styles for the split-view layout and the new rule for the placeholder widget.

~~~~~act
write_file
packages/quipu-cli/src/quipu/cli/tui.css
~~~~~
~~~~~css
/* Base layout for the main container */
#main-container {
    layout: horizontal;
}

/* The history table should take up all available space by default */
#history-table {
    width: 1fr;
}

/* The content view is hidden by default */
#content-view {
    display: none;
    width: 0;
    height: 100%;
    border-left: solid $accent;
}

/* When in split mode, the content view becomes visible */
#main-container.split-mode > #content-view {
    display: block;
    width: 1fr; /* Takes up 50% of the space with the table */
}

/*
 * THE FIX:
 * This ensures the Static placeholder widget reports its full content height,
 * which allows its parent container (#content-view) to become scrollable.
 * By default, Static widgets shrink to fit their container, hiding overflow.
 */
#content-placeholder {
    shrink: false;
    width: 100%;
    height: auto;
}

#content-header {
    text-align: center;
    text-style: bold;
    padding: 0 1;
    background: $surface-lighten-1;
}
~~~~~

### 下一步建议
This should resolve the missing scrollbar issue. Please run `qd ui --raw` to confirm that you can now scroll through long content in the raw text view. Once confirmed, we can bundle all these TUI improvements into a final `[COMMIT]`.
