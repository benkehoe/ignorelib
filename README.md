# ignorelib
## Use the syntax and semantics of gitignore with custom ignore file names and locations

git has a comprehensive mechanism for selecting files to ignore inside repositories.
`ignorelib` lets you use the same system, customized to your own needs.

You can read about the semantics of gitignore here: https://git-scm.com/docs/gitignore

This library is a lightly-modified version of the [gitignore implementation](https://github.com/dulwich/dulwich/blob/master/dulwich/ignore.py) in [dulwich](https://www.dulwich.io/), a pure Python implementation of git.

# Installation
```
python -m pip install ignorelib
```

# Usage
## Setup
The primary entrypoint is the class factory method `IgnoreFilterManager.build()`, with the following inputs:
* `path`: the root path (required). All path checks you make are relative to this path.
* `global_ignore_file_paths`: an optional list of file paths to attempt to load global ignore patterns from.
  * Relative paths are relative to the root path (for git, this would be `.git/info/exclude`)
  * User expansion is performed, so paths like (for git) `~/.config/git/ignore` work.
  * Files that cannot be loaded are silently ignored, so you don't need to check if they exist or not.
  * Files earlier in the list take precedence, and these files take precendence over the patterns in `global_patterns`.
* `global_patterns`: an optional list of global ignore patterns. These are the things that should always be ignored (for git, this would be `.git` to exclude the repo directory)
* `ignore_file_name`: an optional file name for the per-directory ignore file (for git, this would be `.gitignore`).
* `ignore_case`: an optional boolean for specifying whether to ignore case, defaulting to false.

## Use
You check if a given path is ignored with the `is_ignored()` method of an `IgnoreFilterManager` object, which takes a (relative) path and returns `True` if it matches an ignore pattern.
It returns `False` if it is explicitly not ignored (using a pattern starting with `!`), or `None` if the file does not match any patterns.
Note that this allows you to distinguish between the default state (not ignoring) and actually matching a pattern that prevents it from being ignored.

To iterate over not-ignored files, `IgnoreFilterManager.walk()` has the same interface as `os.walk()` but without taking a root path, as this comes from the the `IgnoreFilterManager`.

After using an `IgnoreFilterManager` instance to get a number of paths, you can extract the state (i.e., all loaded patterns with their sources) in a JSON-serializable format with the `IgnoreFilterManager.to_dict()` method.

### Example

To replicate the behavior of git, you would do something like:
```python
import os.path

import ignorelib

def get_filter_manager_for_path(path):
  return ignorelib.IgnoreFilterManager(path,
      global_ignore_file_paths=[
          os.path.join('.git', 'info', 'exclude'), # relative to input path, so within the repo
          os.path.expanduser(os.path.join('~', '.config', 'git', 'ignore')) # absolute
      ],
      global_patterns=['.git'],
      ignore_file_name='.gitignore')
```
