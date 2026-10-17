---
layout: default
title: "GitHub and Jekyll publishing"
---

# GitHub and Jekyll publishing


## Package installation

Extract this overlay into the complete project root, beside run.py and app/. It adds README.md, CONTRIBUTING.md, .gitignore, and docs/. It contains no replacement runtime files, dependency manifest, launcher, license or dataset.

If these files already exist, merge them rather than replacing valuable existing content. Jekyll's `_config.yml` and `_layouts` must keep their leading underscores. Git ignores local state; ignore rules do not remove files already committed.

## Configure the documentation URL

In docs/_config.yml replace:

```yaml
url: "https://YOUR-USERNAME.github.io"
baseurl: "/YOUR-REPOSITORY"
```

For example, a repository named AI4SH-Backbone uses /AI4SH-Backbone. Use the repository name exactly. For the special USERNAME.github.io repository, baseurl is empty. No remote theme, plugin download or custom Pages workflow is required for this layout.

## Upload with GitHub Desktop

1. Create an empty GitHub repository. If using a free personal account and publishing Pages, choose a public repository. Do not auto-create a conflicting README.
2. Clone it using GitHub Desktop into a new folder.
3. Copy the complete application source and this overlay into that folder. Include your existing run.py and requirements.txt or installable pyproject.toml.
4. Review Desktop's Changes list. Ensure .venv, instance, keys, credentials and __pycache__ are absent. Do not copy your local datasets as part of a source upload.
5. Commit with a clear message such as Add backbone and Jekyll documentation.
6. Push origin. Make sure the published branch is named main, or select its actual name in Pages settings.

## Enable GitHub Pages

On the repository:

1. Settings → Pages.
2. Build and deployment → Source → Deploy from a branch.
3. Branch → main; folder → /docs; Save.
4. Check the Pages build under Actions and wait for success.
5. Open the URL displayed in Settings → Pages. A project site normally lives at https://USERNAME.github.io/REPOSITORY/.

GitHub's branch publishing uses Jekyll. Do not add a .nojekyll file to docs/: it bypasses Jekyll processing. The website publishes documentation only; it does not execute Flask or connect to databases.

## Update documentation

Edit the relevant docs/*.md file, commit and push to the publishing branch. GitHub rebuilds the site. Add new pages with front matter:

```yaml
---
layout: default
title: New feature
---
```

Then add the page to docs/_data/navigation.yml. Use the existing relative_url filter for layout asset/navigation URLs so repository subpaths work.

## Optional local preview

Ruby and Bundler are needed only for local documentation preview, not for Python execution or GitHub's hosted build. With them installed:

```shell
cd docs
bundle install
bundle exec jekyll serve --baseurl ""
```

Open the local URL shown by Jekyll. Keep a generated Gemfile.lock if you maintain Ruby dependencies. The Jekyll bundle is independent of requirements.txt.

## Official references

- [Configure the publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Create a Jekyll site](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll)
- [What GitHub Pages hosts](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

The owner should choose the project's license separately. This overlay does not assign one.
