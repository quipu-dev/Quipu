~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~

~~~~~
perf(engine): Implement git batch reading for history loading

The GitObjectHistoryReader previously suffered from an N+1 query problem, making multiple `git cat-file` calls for each commit in the history. This resulted in extremely slow loading times for repositories with many nodes.

This commit introduces a batching mechanism by leveraging `git cat-file --batch`. The reader now performs a constant number of batch calls to fetch all tree and metadata objects, significantly reducing process invocation overhead and improving performance.

Additionally, the TUI summary display logic was updated to use the pre-computed `node.summary` field, fixing a bug where summaries would not appear due to lazy-loaded content.
~~~~~