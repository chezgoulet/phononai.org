# phononai.org

The project site for Phonon — old phones as inference servers.

The page is **generated**, not hand-written. Every fact on it is read from
[`chezgoulet/phonon`](https://github.com/chezgoulet/phonon) at a release tag, or
from that release's GitHub metadata, when the site is built. Nothing is copied
by hand, so nothing can drift from the app.

## One-time setup: switch Pages to GitHub Actions

**The repository must serve Pages from GitHub Actions, not from a branch.**
`Settings → Pages → Build and deployment → Source: GitHub Actions`. There is no
`index.html` in this repository any more — the page is built into `dist/` on
every run — so a Pages source still set to "Deploy from a branch" would serve a
404. This is a one-time change and cannot be made by a workflow.

## Layout

```
template/index.html        the page, with Jinja2 placeholders
build/generate.py          reads the app repo, writes dist/
build/linkcheck.py         checks the generated output
build/requirements.txt     PyYAML and Jinja2
.github/workflows/site.yml the build and deploy pipeline
CNAME logo.svg robots.txt  static files, copied into dist/ verbatim
assets/badge_obtainium.png the Obtainium badge
dist/                      output; generated, never committed
```

`assets/screens/` no longer exists: screenshots come from the app's
`fastlane/metadata/android/en-US/images/phoneScreenshots/` at the tag, so there
is no second copy to fall out of date.

## Building it locally

```sh
pip install -r build/requirements.txt
git -C ../phonon fetch --tags
python3 build/generate.py --app-repo ../phonon --ref v0.1.13 --out dist
python3 build/linkcheck.py dist --app-repo ../phonon --ref v0.1.13 --offline
```

`--release-json FILE` takes a saved `GET /repos/chezgoulet/phonon/releases/tags/<tag>`
payload, so the generator can run without a token:

```sh
gh api repos/chezgoulet/phonon/releases/tags/v0.1.13 > /tmp/release.json
python3 build/generate.py --app-repo ../phonon --ref v0.1.13 --out dist \
  --release-json /tmp/release.json
```

The generator reads with `git show <ref>:<path>`, so **only committed content
counts** — an uncommitted edit in the app checkout will not change the page.
Any ref works (tag, branch, sha), which is also how you preview an unreleased
tag before cutting it.

## Changing a fact on the page

Change it in the app repository, then either publish a release or wait for the
daily rebuild. The usual cases:

- a rate, context or licence → `app/app/src/main/assets/catalog.json`
- a device's numbers → `devices/<codename>.yaml`
- the app's minimum Android version → `minSdk` in `app/app/build.gradle.kts`
- release notes → `fastlane/metadata/android/en-US/changelogs/<versionCode>.txt`
- the tagline or description → `fastlane/metadata/android/en-US/*_description.txt`

The template holds layout and prose. It holds no numbers.

## What fails the build

Loudly, with the file named, rather than emitting a page with a hole in it:

- a required source missing at the tag — the catalog, a device manifest, the
  changelog for the current `versionCode`, the screenshots, the licence
- a `minSdk` with no Android version name to print
- a template field the generator does not provide
- a template placeholder surviving into `dist/`
- a link into the app repo that names a path which does not exist at the tag,
  an internal anchor with no target, a missing asset, or an APK URL whose size
  disagrees with the page

## What the page will not do

It will not print a number that is not in a file at the tag. When something has
not been measured — sustained throughput on the current build, an agent turn,
power draw — the page says so, or omits the line, because a plausible figure and
a measured one look identical once rendered.
