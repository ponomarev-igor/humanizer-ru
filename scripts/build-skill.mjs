#!/usr/bin/env node
// Вшивает core/humanizer-ru.md в SKILL.md между маркерами.
// Источник правды это core/. SKILL.md между BEGIN/END core редактировать руками нельзя.
// Запуск: node scripts/build-skill.mjs

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const skillPath = join(root, "SKILL.md");
const corePath = join(root, "core", "humanizer-ru.md");

const BEGIN = "<!-- BEGIN core -->";
const END = "<!-- END core -->";

const skill = readFileSync(skillPath, "utf8");
const core = readFileSync(corePath, "utf8").trim();

const start = skill.indexOf(BEGIN);
const end = skill.indexOf(END);
if (start === -1 || end === -1 || end < start) {
  console.error("Не нашёл маркеры BEGIN core / END core в SKILL.md");
  process.exit(1);
}

const before = skill.slice(0, start + BEGIN.length);
const after = skill.slice(end);
const out = `${before}\n\n${core}\n\n${after}`;

writeFileSync(skillPath, out);
console.log("SKILL.md собран из core/humanizer-ru.md");
