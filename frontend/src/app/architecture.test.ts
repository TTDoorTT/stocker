/// <reference types="vite/client" />
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const sources = import.meta.glob<string>('/src/**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
});
const publicComponents = new Set(['research/components/Chat', 'portfolio/components/PositionsPreview']);

function violations(source: string, file: string): string[] {
  const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const owner = file.replace('/src/', '').split('/');
  const errors: string[] = [];
  for (const node of ast.statements) {
    if (!ts.isImportDeclaration(node) || !ts.isStringLiteral(node.moduleSpecifier)) continue;
    const specifier = node.moduleSpecifier.text;
    if (!specifier.startsWith('.')) continue;
    const target = new URL(specifier, `file://${file}`).pathname
      .replace('/src/', '')
      .replace(/\.tsx?$/, '')
      .split('/');
    if (owner[0] === 'shared' && ['features', 'app'].includes(target[0])) {
      errors.push('Shared code imports application/feature implementation');
    }
    if (target.join('/') === 'shared/api/client' && !file.endsWith('/api.ts')) {
      errors.push('Only endpoint modules may import generic HTTP');
    }
    if (owner[0] === 'features' && target[0] === 'app')
      errors.push('Feature imports application composition');
    if (owner[0] === 'features' && target[0] === 'features' && owner[1] !== target[1]) {
      if (!['api', 'types'].includes(target[2]) && !publicComponents.has(target.slice(1).join('/'))) {
        errors.push('Cross-feature import bypasses public API/types/components');
      }
    }
  }
  return errors;
}

describe('frontend module boundaries', () => {
  it('keeps shared code generic and feature imports public', () => {
    const errors = Object.entries(sources).flatMap(([file, source]) =>
      violations(source, file).map((message) => `${file}: ${message}`),
    );
    expect(errors).toEqual([]);
  });
  it('rejects shared-to-feature and page-to-HTTP imports, including aliases', () => {
    expect(
      violations("import {marketApi as api} from '../../features/market/api'", '/src/shared/ui/Bad.tsx'),
    ).not.toEqual([]);
    expect(
      violations(
        "import {request as get} from '../../../shared/api/client'",
        '/src/features/market/pages/Bad.tsx',
      ),
    ).not.toEqual([]);
  });
  it('permits explicit cross-feature public UI contracts', () => {
    expect(
      violations(
        "import {Chat} from '../../research/components/Chat'",
        '/src/features/market/pages/StockPage.tsx',
      ),
    ).toEqual([]);
    expect(
      violations(
        "import {PositionsPreview} from '../../portfolio/components/PositionsPreview'",
        '/src/features/market/pages/HomePage.tsx',
      ),
    ).toEqual([]);
  });
});
