# Godot Deploy

This GitHub action builds Godot projects for Windows, macOS, Linux, Web, and also optionally deploy to itch.io.

> [!NOTE]  
> this action is currently designed to run inside of GitHub Actions `macos-latest` containers, assumes builds use GDScript and does not require compilation and linking of source plugins.

## Inputs

| Key               | Default                     | Description                                                       |
| ----------------- | --------------------------- | ----------------------------------------------------------------- |
| `godot-version`   | `"4.4"`                     | **Required** The version of Godot to build with                   |
| `godot-channel`   | `"stable"`                  | The release channel (stable, beta1, rc1, etc.)                    |
| `build-dir`       | `"build"`                   | The chosen build directory                                        |
| `platforms`       | `"macos,windows,linux,web"` | Platforms to build for (comma-separated: macos,windows,linux,web) |
| `itch-io-api-key` |                             | Itch.io API key for publishing (required for itch.io upload)      |
| `itch-io-user`    |                             | Itch.io username (required for itch.io upload)                    |
| `itch-io-game`    |                             | Itch.io game name (required for itch.io upload)                   |

## Example usage

Simplest usage (builds all platforms with defaults):

```yaml
- uses: Daniel-Griffiths/godot-deploy@master
  with:
    godot-version: "4.4"
```

Only build specific platforms:

```yaml
- uses: Daniel-Griffiths/godot-deploy@master
  with:
    godot-version: "4.4"
    platforms: "macos,windows,linux"
```

Use beta/rc versions:

```yaml
- uses: Daniel-Griffiths/godot-deploy@master
  with:
    godot-version: "4.5"
    godot-channel: "beta1"
    build-dir: "build"
    platforms: "macos,windows,linux"
```

With web export and itch.io upload:

```yaml
- uses: Daniel-Griffiths/godot-deploy@master
  with:
    godot-version: "4.4"
    godot-channel: "stable"
    build-dir: "build"
    platforms: "macos,windows,linux,web"
    itch-io-api-key: ${{ secrets.ITCH_IO_API_KEY }}
    itch-io-user: "your-username"
    itch-io-game: "your-game-name"
```

Build only web version:

```yaml
- uses: Daniel-Griffiths/godot-deploy@master
  with:
    godot-version: "4.4"
    platforms: "web"
    itch-io-api-key: ${{ secrets.ITCH_IO_API_KEY }}
    itch-io-user: "your-username"
    itch-io-game: "your-game-name"
```

## Github release example

If you want to upload your builds as a Github release you can use this to add the builds:

```yaml
- name: Create GitHub Release
  uses: softprops/action-gh-release@v1
  if: github.ref == 'refs/heads/master'
  with:
    tag_name: latest
    name: Latest Build
    files: |
      build/windows/windows.zip
      build/linux/linux.tar
      build/macos/macos.tar
    draft: false
    prerelease: false
    token: ${{ secrets.GITHUB_TOKEN }}
```
