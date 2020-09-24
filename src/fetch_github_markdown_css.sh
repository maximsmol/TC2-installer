#!/usr/bin/env bash

cd "$(dirname "${0}")" || exit
curl https://raw.githubusercontent.com/sindresorhus/github-markdown-css/gh-pages/github-markdown.css > gh_markdown.css
# sed -i 's/.markdown-body //g' gh_markdown.css
