# Industry RSS news sources — attribution and scope

Stocker's Industry Intelligence feed uses an edited source inventory derived from
[simonlin1212/investment-news](https://github.com/simonlin1212/investment-news),
pinned to upstream commit `8208dd1a406d4cfb861f72345d80f908787fb3d8`.
The upstream project is copyright (c) 2026 simonlin1212 and is licensed under MIT.
Eighteen Chinese-language publishers were excluded from the initial inventory;
88 sources in 12 categories remain. Each RSS feed belongs to its respective publisher.

The feed only stores headline metadata, dates, short feed-provided descriptions, and
links to the publishers' articles. This does not confer rights to republish full articles.
Source health, feed access and publishers' terms may change. A source catalog is not
proof that all sources work or authorize every downstream use.

**Language policy:** use curated English-language RSS feeds; reject entries with
explicit non-English language metadata or CJK headlines. This is a best-effort
English-first policy, not a comprehensive language detector for every possible language.

**AI policy:** fetching, filtering, caching, sorting and rendering RSS news never
invoke an LLM. AI is invoked only by the user-selected Industry Highlights button,
and the model receives sourced headlines, not full articles.

**Storage:** news articles and timestamps are stored in the existing SQLite database.
Each category shows items from the last three days; a successful refresh is scheduled
on opening when the last attempt is at least 45 minutes old. Manual refresh is available.

## MIT License (upstream investment-news)

Copyright (c) 2026 simonlin1212

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
