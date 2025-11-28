You are absolutely correct. My apologies. I made a mistake by suggesting a CSS property that does not exist in Textual's CSS dialect. The traceback confirms it: `shrink` is not a valid property. Thank you for catching this and providing the precise error.

My reasoning was correct (we need to stop the widget from shrinking), but the specific implementation I provided was wrong.

**Correct Analysis and Solution**:

The correct way to achieve this in Textual is to control the layout properties of both the child widget (`#content-placeholder`) and its parent container (`#content-view`).

1.  **Child Widget (`#content-placeholder`):** We need to tell it to determine its own height based on its content. The `height: auto;` property is the correct way to do this.
2.  **Parent Container (`#content-view`):** This is the key part I missed. We must explicitly tell this container what to do when its content (the child widget) becomes taller than the container itself. The CSS property for this is `overflow-y`. By setting `overflow-y: scroll;`, we command the container to always show a vertical scrollbar if its content overflows.

The combination of the child demanding its full height (`height: auto`) and the parent being configured to scroll when overflow happens (`overflow-y: scroll`) is the correct and robust solution.

I will now generate a corrected plan that implements this proper CSS.

## [WIP] fix: Correctly enable scrolling in TUI raw text view

### 错误分析
The previously suggested CSS fix used an invalid property, `shrink`, which caused the TUI's CSS parser to fail. The correct approach requires modifying the parent container to handle overflow, rather than trying to modify a non-existent property on the child widget.

### 用户需求
The raw text view must be scrollable, just like the Markdown view.

### 评论
This fix correctly applies standard CSS principles for overflow handling within the Textual framework. It's a more fundamental and correct solution that ensures the UI behaves as expected.

### 目标
1.  Modify `packages/quipu-cli/src/quipu/cli/tui.css`.
2.  Add the `overflow-y: scroll;` property to the `#content-view` rule.
3.  Remove the invalid `shrink` property from the `#content-placeholder` rule, ensuring `height: auto;` remains.

### 基本原理
We are creating a classic scrollable container. The child element (`#content-placeholder`) is configured with `height: auto;`, which makes its height expand to fit all of its text content. The parent element (`#content-view`) is configured with `overflow-y: scroll;`. When the child's auto-sized height exceeds the parent's fixed height, the parent's `overflow-y` rule is triggered, causing the scrollbar to appear.

### 标签
#intent/fix #flow/ready #priority/critical #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/ui #task/object/tui-performance #task/action/optimization #task/state/continue

---

### Script

#### Acts 1: Apply the correct CSS to enable scrolling

We will replace the entire `tui.css` file to ensure it contains the correct and final version of the styles.

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
    /* THE FIX PART 1: Enable vertical scrolling when content overflows */
    overflow-y: scroll;
}

/* When in split mode, the content view becomes visible */
#main-container.split-mode > #content-view {
    display: block;
    width: 1fr; /* Takes up 50% of the space with the table */
}

/*
 * THE FIX PART 2:
 * This ensures the Static placeholder widget reports its full content height,
 * which will trigger the overflow on its parent container.
 */
#content-placeholder {
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
This corrected CSS should now work as intended. Please restart the TUI (`qd ui --raw`) and confirm that the scrollbar is present and functional for the raw text view. This should be the final fix for this issue. Once you confirm, we can proceed to commit all the TUI improvements.
