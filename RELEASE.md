# Release Process

This document outlines the process for creating new releases of censys-toolkit.

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backwards compatible manner  
- **PATCH** version for backwards compatible bug fixes

## Release Checklist

### Pre-Release
1. **Update Version Number**
   - Update `version` in `pyproject.toml`
   - Ensure version follows semantic versioning

2. **Update Documentation**
   - Update `CHANGELOG.md` with new version and changes
   - Review and update `README.md` if needed
   - Ensure help messages are current

3. **Testing**
   - Run full test suite: `pytest`
   - Test real API integration manually with a test domain
   - Verify CLI commands work correctly
   - Test package installation: `pip install -e .`

4. **Code Quality**
   - Run linters and formatters
   - Check type annotations with mypy
   - Review code for any TODOs or FIXMEs

### Release Steps
1. **Commit Changes**
   ```bash
   git add .
   git commit -m "Release v{version}"
   ```

2. **Create Git Tag**
   ```bash
   git tag -a v{version} -m "Release v{version}"
   ```

3. **Push to Repository**
   ```bash
   git push origin main
   git push origin v{version}
   ```

4. **Create GitHub Release**
   - Go to GitHub repository
   - Create new release from tag
   - Copy changelog entry for release notes
   - Attach any relevant files if needed

### Post-Release
1. **Update Unreleased Section**
   - Add placeholder sections in `CHANGELOG.md` for next release

2. **Announce Release**
   - Update project documentation
   - Notify users if applicable

## Example Release Commands

```bash
# For version 1.1.0
# 1. Update pyproject.toml version to "1.1.0"
# 2. Update CHANGELOG.md with new version
# 3. Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "Release v1.1.0"
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main
git push origin v1.1.0
```

## Hotfix Process

For critical bug fixes:

1. Create hotfix branch from main
2. Apply minimal fix
3. Test thoroughly
4. Update version (patch increment)
5. Update changelog
6. Follow normal release process
7. Merge back to main

## Rollback Process

If a release has critical issues:

1. Revert the problematic commit
2. Create new patch release
3. Update changelog with rollback information
4. Follow normal release process