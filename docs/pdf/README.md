# PDFs

Printable versions of the docs:

- [User Manual (PDF)](passive-multiple-manual.pdf)
- [Assembly Guide (PDF)](passive-multiple-assembly-guide.pdf)

These are built from [`../manual.md`](../manual.md) and [`../assembly-guide.md`](../assembly-guide.md). **Don't edit the PDFs by hand.** Edit the Markdown instead.

## Automatic builds

A GitHub Action ([`.github/workflows/pdf.yml`](../../.github/workflows/pdf.yml)) rebuilds the PDFs whenever the docs, their images or the build files change on `master`, and commits the new PDFs back. After you push a docs change, wait a minute and then `git pull` to get the rebuilt PDFs. You can also start a build by hand from the repo's **Actions** tab.

## Building locally

To preview a PDF before pushing, you need Node.js 22.12 or newer:

```sh
cd docs/pdf
npm install     # first time only; downloads a copy of Chrome
npm run build
```

It's best not to commit locally built PDFs. The Action rebuilds them anyway, and different Chrome versions produce slightly different files.

## How it works

[`build.mjs`](build.mjs) converts each Markdown file to HTML with [marked](https://marked.js.org/), styles it with [`style.css`](style.css), and prints it to PDF with headless Chrome ([Puppeteer](https://pptr.dev/)). The font is Inter, bundled through npm, so the output looks the same on every machine.

- The page size is US Letter. To change it, edit `format` in `build.mjs`.
- The document's own H1 is replaced by a title block. The "Updated" date is the date the Markdown file was last committed.
- Links to other files in the repo point to GitHub, and every link prints its URL, because paper copies can't be clicked.
- To add a document, add it to the `DOCUMENTS` list in `build.mjs`, and add its Markdown file to the paths in the workflow if it isn't in `docs/`.
