/**
 * A parameter annotated with a TypedDict that has required keys is never empty,
 * so testing it for truthiness (`if not x:`) always gives the same answer.
 *
 * This is the case the `sg` rule `always-truthy-typeddict` misses. In ty's own
 * example the annotation is `Bar`, `Bar` subclasses `Foo`, and only `Foo`
 * subclasses `TypedDict`. Answering that means following a chain of classes,
 * possibly across files, which a single-file pattern cannot do.
 *
 * Resolution follows the file's own imports, the way a reader would: a name
 * imported with `from module import Name` (or `as Alias`) resolves to the class
 * in that module's file, and any other name resolves to a class defined in the
 * same file. A name imported from outside the repository, a star import, or two
 * definitions that can't be told apart all resolve to nothing, and the check
 * says nothing. A wrong finding here costs more trust than a missed one.
 *
 * It imports nothing from `@taskless/*`. The harness contract is structural.
 */

/** One normalized ast-grep match, as the harness hands it over. */
interface Match {
  rule: string;
  file: string;
  line: number;
  column: number;
  text: string;
  captures: Record<string, string>;
}

interface Finding {
  file: string;
  line?: number;
  column?: number;
  message: string;
  severity?: "error" | "warning" | "info";
}

interface ClassDef {
  name: string;
  file: string;
  line: number;
  bases: string[];
  total: boolean;
  /** Keys declared in this class body, with whether each is required. */
  fields: Map<string, boolean>;
}

interface Imported {
  /** The module as written, e.g. `app.models` or `..models`. */
  module: string;
  /** The name in that module (differs from the local name under `as`). */
  original: string;
}

interface Resolved {
  isTypedDict: boolean;
  /** Required key name -> the class that declared it. */
  required: Map<string, ClassDef>;
}

const TYPED_DICT = /^(?:typing\.|typing_extensions\.|te\.)?TypedDict$/;
/** Wrappers that don't change whether a key is required. */
const TRANSPARENT = /^(?:[A-Za-z_]\w*\.)*(?:ReadOnly|Annotated)\[/;
const REQUIRED = /^(?:[A-Za-z_]\w*\.)*Required\[/;
const NOT_REQUIRED = /^(?:[A-Za-z_]\w*\.)*NotRequired\[/;

/** Split on commas that aren't nested inside brackets or parens. */
function splitTopLevel(text: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  for (const ch of text) {
    if ("([{".includes(ch)) depth++;
    if (")]}".includes(ch)) depth--;
    if (ch === "," && depth === 0) {
      parts.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  if (current.trim()) parts.push(current.trim());
  return parts;
}

/** The text between the brackets of `Wrapper[...]`, first argument only. */
function firstArgument(annotation: string): string {
  const open = annotation.indexOf("[");
  const inner = annotation.slice(open + 1, annotation.lastIndexOf("]"));
  return splitTopLevel(inner)[0] ?? inner;
}

function isRequired(annotation: string, total: boolean): boolean {
  // A quoted annotation (`"NotRequired[str]"`) means the same as an unquoted one.
  let a = annotation.trim().replace(/^(['"])(.*)\1$/s, "$2").trim();
  while (TRANSPARENT.test(a)) a = firstArgument(a).trim();
  if (NOT_REQUIRED.test(a)) return false;
  if (REQUIRED.test(a)) return true;
  return total;
}

/** Parse a captured class definition's source text. */
function parseClass(match: Match): ClassDef | undefined {
  const name = match.captures.N;
  const text = match.text;
  const open = text.indexOf("(");
  if (!name || open === -1) return undefined;

  // The base list ends at the paren that closes the one after the class name.
  let depth = 0;
  let close = -1;
  for (let i = open; i < text.length; i++) {
    if (text[i] === "(") depth++;
    if (text[i] === ")" && --depth === 0) {
      close = i;
      break;
    }
  }
  if (close === -1) return undefined;

  const bases: string[] = [];
  let total = true;
  for (const argument of splitTopLevel(text.slice(open + 1, close))) {
    const keyword = /^(\w+)\s*=\s*(.+)$/.exec(argument);
    if (keyword) {
      if (keyword[1] === "total") total = keyword[2].trim() !== "False";
      continue;
    }
    // `Foo[T]` is still `Foo` for this purpose.
    bases.push(argument.replace(/\[.*$/s, "").trim());
  }

  // Body fields are `name: annotation` lines at the body's own indentation.
  const fields = new Map<string, boolean>();
  const lines = text.slice(close).split("\n").slice(1);
  const first = lines.find((l) => l.trim() && !l.trim().startsWith("#"));
  const indent = first ? (/^\s*/.exec(first)?.[0] ?? "") : "";
  for (const line of lines) {
    if (!line.startsWith(indent) || /^\s/.test(line.slice(indent.length))) continue;
    const field = /^([A-Za-z_]\w*)\s*:\s*([^=#]+?)\s*(?:#.*)?$/.exec(line.slice(indent.length));
    if (field) fields.set(field[1], isRequired(field[2], total));
  }

  return { name, file: match.file, line: match.line, bases, total, fields };
}

export default async function check(_root: string, matches: Match[]): Promise<Finding[]> {
  const classes = new Map<string, ClassDef[]>();
  const imports = new Map<string, Map<string, Imported>>();

  for (const m of matches) {
    if (m.rule === "class-def") {
      const def = parseClass(m);
      if (def) classes.set(def.name, [...(classes.get(def.name) ?? []), def]);
    } else if (m.rule === "from-import") {
      const module = m.captures.M;
      const names = /\bimport\s+\(?([\s\S]*?)\)?\s*$/.exec(m.text)?.[1];
      if (!module || !names) continue;
      const fileImports = imports.get(m.file) ?? new Map<string, Imported>();
      for (const part of splitTopLevel(names.replace(/#.*$/gm, ""))) {
        const [original, alias] = part.split(/\s+as\s+/).map((p) => p.trim());
        if (original && original !== "*") fileImports.set(alias ?? original, { module, original });
      }
      imports.set(m.file, fileImports);
    }
  }

  /** Whether `file` is the source of `module`, imported from `fromFile`. */
  function isModuleFile(file: string, module: string, fromFile: string): boolean {
    const dots = /^\.*/.exec(module)?.[0].length ?? 0;
    const path = module.slice(dots).replaceAll(".", "/");
    const candidates = [`${path}.py`, `${path}/__init__.py`].map((p) => p.replace(/^\//, ""));
    if (dots > 0) {
      // Relative: `.models` is a sibling of the importing file, `..models` one level up.
      const base = fromFile.split("/").slice(0, -dots).join("/");
      return candidates.some((c) => file === (base ? `${base}/${c}` : c));
    }
    // Absolute: match on the path suffix, so `src/` layouts and nested packages work.
    return candidates.some((c) => file === c || file.endsWith(`/${c}`));
  }

  /** The one class a name refers to from `file`, or undefined when unsure. */
  function resolve(name: string, file: string): ClassDef | undefined {
    if (name.includes(".")) return undefined;
    const imported = imports.get(file)?.get(name);
    const candidates = imported
      ? (classes.get(imported.original) ?? []).filter((c) => isModuleFile(c.file, imported.module, file))
      : (classes.get(name) ?? []).filter((c) => c.file === file);
    return candidates.length === 1 ? candidates[0] : undefined;
  }

  const cache = new Map<ClassDef, Resolved>();
  function walk(cls: ClassDef, seen: Set<ClassDef>): Resolved {
    const cached = cache.get(cls);
    if (cached) return cached;
    const result: Resolved = { isTypedDict: false, required: new Map() };
    if (seen.has(cls)) return result;
    seen.add(cls);

    for (const base of cls.bases) {
      const imported = imports.get(cls.file)?.get(base);
      const viaImport = imported && /^(typing|typing_extensions)$/.test(imported.module);
      if (TYPED_DICT.test(base) || (viaImport && imported.original === "TypedDict")) {
        result.isTypedDict = true;
        continue;
      }
      const parent = resolve(base, cls.file);
      if (!parent) continue;
      const inherited = walk(parent, seen);
      if (inherited.isTypedDict) result.isTypedDict = true;
      for (const [key, owner] of inherited.required) result.required.set(key, owner);
    }
    if (result.isTypedDict) {
      for (const [key, required] of cls.fields) {
        if (required) result.required.set(key, cls);
        else result.required.delete(key);
      }
    }
    cache.set(cls, result);
    return result;
  }

  const findings: Finding[] = [];
  for (const m of matches) {
    if (m.rule !== "truthiness-test") continue;
    const { X: variable, T: annotation } = m.captures;
    if (!variable || !annotation) continue;
    const cls = resolve(annotation, m.file);
    if (!cls) continue;
    const { isTypedDict, required } = walk(cls, new Set());
    if (!isTypedDict || required.size === 0) continue;

    const [key, owner] = [...required][0];
    const where = owner.file === m.file ? `line ${owner.line}` : `${owner.file}:${owner.line}`;
    findings.push({
      file: m.file,
      line: m.line,
      column: m.column,
      severity: "warning",
      message:
        `\`${variable}\` is annotated \`${cls.name}\`, a TypedDict with ${required.size} required ` +
        `key${required.size === 1 ? "" : "s"}, so it is never empty and this condition ` +
        `always has the same value. \`${key}\` is required by \`${owner.name}\` (${where}).`,
    });
  }
  return findings;
}
