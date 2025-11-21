
## [2025-11-21 22:47:52]
Implementation Logic:
1.  **Refactored `plugin_loader.py`**: Switched from `import_module` to `spec_from_file_location`. This is crucial because `import_module` relies on Python's `sys.path`. If we have multiple folders named `.axon/acts` in different locations (Home, Project), Python would treat them as the same package namespace or fail to distinguish them. Loading by file path isolates each plugin file as a unique module in memory.
2.  **Enhanced `main.py`**: Added `_find_project_root` to detect Git boundaries. Added `_load_extra_plugins` to build a list of plugin paths.
3.  **Loading Order**: The order `Home -> Env -> Project -> Local` ensures that a script in your current folder can override a project-wide script, and a project script can override a global user script. This follows the standard "Cascading Configuration" pattern (like CSS or Git config).
